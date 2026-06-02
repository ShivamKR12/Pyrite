.. _meshes:

Mesh Systems and Vertex Packing
================================

This document provides a complete, replicable guide to Pyrite's mesh architecture, including data structures, vertex packing, the greedy meshing algorithm, and ambient occlusion (AO) calculation.

Overview
--------

Pyrite renders millions of voxels using a multi-stage mesh pipeline:

1. **Greedy Meshing:** CPU-side algorithm groups adjacent coplanar faces into large rectangular polygons.
2. **Vertex Packing:** Vertex attributes compressed into 32-bit integers to minimize GPU memory.
3. **Lighting:** Per-vertex smoothed light values sampled from adjacent blocks.
4. **AO Calculation:** Corner darkness determined by surrounding block density.
5. **GPU Upload:** Main thread creates VAO/VBO objects from packed data.
6. **Rendering:** Draw calls per mesh (opaque + transparent passes).

Mesh Classes Hierarchy
----------------------

**BaseMesh** (Core Abstract Class)

Base class for all mesh types. Defines the interface:

.. code-block:: text

    class BaseMesh:
        __init__(self, ctx, program):
            ctx: ModernGL context
            program: Shader program to bind during render
            self.vao: Vertex Array Object (initially None)
            self.vbo: Vertex Buffer Object (initially None)
            self.vertex_count: int
            self.index_count: int
            self.render_mode: GLenum (GL_TRIANGLES default)
        
        render():
            # Bind program, VAO, draw (implementation varies)
        
        render_instanced():
            # Render multiple instances
        
        destroy():
            # Release GPU resources

**ChunkMesh** (Per-Chunk Geometry)

Represents a single 48x48x48 chunk. Created during chunk building.

.. code-block:: text

    class ChunkMesh(BaseMesh):
        __init__(self, chunk_voxels, chunk_lightmap, chunk_pos, ctx, program, world_data):
            # Greedy mesh the chunk and store vertex data
            self.chunk_pos: (int, int, int)  # Chunk coordinates in world
            self.vertex_data: np.ndarray (uint32, packed vertices)
            self.light_data: np.ndarray (uint32, packed light)
            self.opaque_count, self.water_count: Face counts
        
        render():
            # Render opaque faces, then water faces with separate passes

**CloudMesh, CubeMesh, ItemMesh, ObjMesh** (Specialized)

- **CloudMesh:** Fixed 2D procedural clouds (sky)
- **CubeMesh:** Renders static cubes (UI, debugging)
- **ItemMesh:** Item entities dropped in world
- **ObjMesh:** Wavefront .obj models (trees, items)

Vertex Packing: 32-Bit Format
------------------------------

To minimize GPU bandwidth and memory, each vertex attribute is bit-packed into a single 32-bit unsigned integer.

**Packed Vertex Layout:**

.. code-block:: text

    Bits 31-26 (6 bits): X coordinate (0-47)
    Bits 25-20 (6 bits): Y coordinate (0-47)
    Bits 19-14 (6 bits): Z coordinate (0-47)
    Bits 13-6  (8 bits): Voxel ID (0-255)
    Bits 5-3   (3 bits): Face ID (0-5, one of 6 faces)
    Bits 2-1   (2 bits): AO ID (0-3, ambient occlusion level)
    Bit  0     (1 bit):  Flip ID (0 or 1, diagonal flip flag)

**Total:** 32 bits = 4 bytes per vertex (vs. 16 bytes for traditional (x, y, z, id, face, ao, flip, light))

**Packing Formula:**

.. code-block:: python

    packed_data = (x & 0x3F) << 26 \
                | (y & 0x3F) << 20 \
                | (z & 0x3F) << 14 \
                | (voxel_id & 0xFF) << 6 \
                | (face_id & 0x7) << 3 \
                | (ao_id & 0x3) << 1 \
                | (flip_id & 0x1)

**Unpacking (in Vertex Shader):**

.. code-block:: glsl

    void unpack(uint packed_data) {
        x = int((packed_data >> 26) & 0x3F);
        y = int((packed_data >> 20) & 0x3F);
        z = int((packed_data >> 14) & 0x3F);
        voxel_id = int((packed_data >> 6) & 0xFF);
        face_id = int((packed_data >> 3) & 0x7);
        ao_id = int((packed_data >> 1) & 0x3);
        flip_id = int(packed_data & 0x1);
    }

**Light Data (Separate uint32):**

.. code-block:: text

    Bits 7-4 (4 bits): Sunlight (0-15)
    Bits 3-0 (4 bits): Blocklight (0-15)

Greedy Meshing Algorithm
------------------------

Greedy meshing reduces face count by grouping coplanar, identical-ID faces into rectangles. Executed on CPU; results are packed and uploaded to GPU.

**High-Level Steps:**

1. For each of 3 orthogonal planes (XY, XZ, YZ):

   a. Iterate through all slices perpendicular to that plane
   b. Build 2D mask of solid vs. transparent voxels
   c. For each solid voxel with exposed face:
      
      - Calculate AO and light for all 4 corners
      - Find greedy horizontal rectangle width
      - Find greedy vertical rectangle height
      - Emit quad vertices
      
   d. Mark processed faces to avoid double-processing

2. Separate opaque and water faces into independent buffers

**Detailed Algorithm: X-Plane Scanning**

Processing YZ-plane slices (X varying):

.. code-block:: python

    for x_slice in 0 to CHUNK_SIZE-1:
        # Build 2D mask of YZ values (which are solid and exposed on +X face)
        mask = np.zeros((CHUNK_SIZE, CHUNK_SIZE), dtype=bool)
        
        for y in 0 to CHUNK_SIZE-1:
            for z in 0 to CHUNK_SIZE-1:
                voxel_id = chunk_voxels[x_slice, y, z]
                
                # Check if solid and has exposed +X face
                if is_solid(voxel_id):
                    if x_slice == CHUNK_SIZE-1 or not is_solid(chunk_voxels[x_slice+1, y, z]):
                        mask[y, z] = True
        
        # Greedy rectangle extraction from mask
        for y in 0 to CHUNK_SIZE-1:
            for z in 0 to CHUNK_SIZE-1:
                if not mask[y, z]:
                    continue
                
                # Find greedy width (extend along z-axis)
                width = 1
                while z + width < CHUNK_SIZE and mask[y, z + width]:
                    width += 1
                
                # Find greedy height (extend along y-axis)
                height = 1
                valid = True
                while y + height < CHUNK_SIZE and valid:
                    for z_check in z to z + width - 1:
                        if not mask[y + height, z_check]:
                            valid = False
                            break
                    if valid:
                        height += 1
                
                # Mark processed to avoid overlap
                for dy in 0 to height-1:
                    for dz in 0 to width-1:
                        mask[y + dy, z + dz] = False
                
                # Get 4 corner light/AO values
                l0 = get_vertex_light(x_slice, y, z)
                l1 = get_vertex_light(x_slice, y+height, z)
                l2 = get_vertex_light(x_slice, y+height, z+width)
                l3 = get_vertex_light(x_slice, y, z+width)
                
                ao0 = get_ao((x_slice, y, z))
                ao1 = get_ao((x_slice, y+height, z))
                ao2 = get_ao((x_slice, y+height, z+width))
                ao3 = get_ao((x_slice, y, z+width))
                
                # Flip detection (see section below)
                flip_id = should_flip_diagonal(l0, l1, l2, l3, ao0, ao1, ao2, ao3)
                
                # Emit 2 triangles (6 indices)
                emit_quad(x_slice, y, z, width, height, flip_id, l0, l1, l2, l3)

**Y and Z Plane Scanning** work similarly, iterating through XZ and XY slices respectively.

**Performance Note:** This is a hot loop executed once per chunk load. Implemented in Numba with ``@njit(cache=True, nogil=True)`` for 500x+ speedup.

Vertex Light Smoothing
----------------------

Light values are interpolated to vertices for smooth shading. Each vertex is shared by up to 8 blocks; we sample light from the 4 (on a plane) or 8 blocks surrounding that vertex.

**For X-Plane Face (perpendicular normal = +X):**

Four corners of the quad correspond to YZ positions. For each corner, sample from 4 blocks:

.. code-block:: python

    def get_vertex_light(x, y, z, plane='X'):
        # plane='X' means YZ quad; sample from 4 blocks around corner
        
        if plane == 'X':
            # Corner at (x, y, z) in YZ space samples:
            l1 = get_light(x, y, z)           # Lower-left
            l2 = get_light(x, y+1, z)         # Upper-left
            l3 = get_light(x, y+1, z+1)       # Upper-right
            l4 = get_light(x, y, z+1)         # Lower-right
        elif plane == 'Y':
            # Similar for XZ plane
            l1 = get_light(x, y, z)
            l2 = get_light(x+1, y, z)
            l3 = get_light(x+1, y, z+1)
            l4 = get_light(x, y, z+1)
        # ... etc for Z plane
        
        # Average light (simple mean, or weighted by AO)
        avg_sun = (l1 >> 4 + l2 >> 4 + l3 >> 4 + l4 >> 4) / 4
        avg_block = ((l1 & 15) + (l2 & 15) + (l3 & 15) + (l4 & 15)) / 4
        
        return (avg_sun << 4) | avg_block

Ambient Occlusion (AO) Calculation
-----------------------------------

AO darkens corners where multiple solid blocks converge, simulating soft shadows.

**Corner Occlusion (for X-plane, Y-Z corner):**

For each of the 4 corners of a quad, check 2x2 adjacent blocks:

.. code-block:: python

    def get_ao(corner_y, corner_z, plane='X'):
        # plane='X': Check blocks in YZ plane around corner
        
        # Top-left, Top-right, Bottom-left, Bottom-right (relative to corner)
        ao_count = 0
        
        if not is_transparent(voxel_at(corner_y-1, corner_z-1)):
            ao_count += 1
        if not is_transparent(voxel_at(corner_y, corner_z-1)):
            ao_count += 1
        if not is_transparent(voxel_at(corner_y-1, corner_z)):
            ao_count += 1
        if not is_transparent(voxel_at(corner_y, corner_z)):
            ao_count += 1
        
        # ao_count ranges 0-4, but we store only 0-3
        # 0 = bright, 1 = slightly dark, 2 = moderately dark, 3 = very dark
        return min(ao_count, 3)

**Transparency Check:**

Transparent blocks (AIR, WATER, GLASS, LEAVES) do not cast AO shadows:

.. code-block:: python

    def is_transparent(voxel_id):
        return voxel_id in [AIR, WATER, GLASS, LEAVES]

**GPU Application (in Vertex Shader):**

.. code-block:: glsl

    const float ao_values[4] = float[4](0.1, 0.25, 0.5, 1.0);
    
    // Unpack ao_id (2 bits)
    int ao_id = int((packed_data >> 1) & 0x3);
    
    // Apply to shading
    shading = base_light * ao_values[ao_id];

Flip Detection (Diagonal Flip for Lighting)
--------------------------------------------

When lighting is uneven across a quad, flipping the diagonal can improve visual appearance. This is determined by comparing lighting sums across the two diagonals.

**Algorithm:**

.. code-block:: python

    def should_flip_diagonal(l0, l1, l2, l3, ao0, ao1, ao2, ao3):
        # l0, l1, l2, l3 = light at 4 corners (packed uint32)
        # ao0, ao1, ao2, ao3 = AO at 4 corners
        
        # Extract sun and block light
        def extract_light(l):
            return (l >> 4) + (l & 15)  # sun + block (simplified)
        
        # Diagonal 1: (0,2) and Diagonal 2: (1,3)
        diag1_brightness = extract_light(l0) + extract_light(l2) + (ao0 + ao2)
        diag2_brightness = extract_light(l1) + extract_light(l3) + (ao1 + ao3)
        
        # Flip if diagonal 1 is brighter (optimization: break ties toward standard diagonal)
        return diag1_brightness > diag2_brightness

**GPU Application:**

During rendering, the vertex shader uses ``flip_id`` to adjust vertex positions or UV coordinates accordingly.

Water Faces Handling
--------------------

Water is rendered separately to allow transparency blending without depth-test complications.

**Algorithm:**

1. During greedy meshing, water faces (voxel_id == WATER) are marked separately
2. Opaque faces emitted first, water faces appended to same buffer
3. Render call splits: draw opaque faces first (full depth test), then draw water faces (transparency blending enabled)

**Separate render call (in Shader Program):**

.. code-block:: python

    # Opaque pass
    ctx.enable(moderngl.DEPTH_TEST)
    ctx.disable(moderngl.BLEND)
    vao.render(mode=moderngl.TRIANGLES, vertices=opaque_count)

    # Water pass
    ctx.enable(moderngl.BLEND)
    ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
    vao.render(mode=moderngl.TRIANGLES, vertices=water_count, first=opaque_count)

Mesh Building Pipeline (CPU to GPU)
-----------------------------------

**Sequential Process:**

1. **Chunk Load (Background Thread):**

   - Generate or fetch voxel data from database
   - Place in ``load_queue``

2. **Mesh Build (Background Thread via ThreadPoolExecutor):**

   - Pop chunk from ``load_queue``
   - Run greedy meshing: ``build_chunk_mesh(chunk_voxels, chunk_lightmap, format_size, chunk_pos, world_voxels, world_lightmaps, chunk_positions)``
   - Output: ``vertex_data`` (flat uint32 array), ``light_data`` (flat uint32 array)
   - Place in ``build_queue``

3. **GPU Upload (Main Thread):**

   - Pop from ``mesh_queue`` (result of lighting stitching in ``build_queue``)
   - Create VAO/VBO: ``ctx.vertex_array(program, vbo, vao)``
   - Store in ``chunk.mesh`` object
   - If VBO pool available, reuse; else allocate new

4. **Rendering (Main Thread, per frame):**

   - Frustum cull active chunks
   - Occlusion query invisible chunks
   - Bind shader, draw visible chunk meshes

**VBO Pool (Memory Recycling):**

.. code-block:: python

    vbo_pool = []  # List of unused VBOs
    VBO_POOL_CAP = 150
    
    def get_or_create_vbo(ctx, data):
        if vbo_pool:
            vbo = vbo_pool.pop()
            vbo.write(data)  # Overwrite with new data
        else:
            vbo = ctx.buffer(data)
        return vbo
    
    def release_vbo(vbo):
        if len(vbo_pool) < VBO_POOL_CAP:
            vbo_pool.append(vbo)
        else:
            vbo.release()  # Destroy GPU memory

Data Flow Example
-----------------

.. code-block:: text

    Raw Chunk Voxels (1D array, 110,592 elements)
             ↓
    [Greedy Meshing: CPU]
             ↓
    Packed Vertex Data (e.g., 10,000 vertices for a grass chunk)
             ↓
    [Lighting Stitching: CPU]
             ↓
    Light Data (10,000 light values)
             ↓
    [GPU Upload: Main Thread]
             ↓
    VBO/VAO allocated on GPU
             ↓
    [Rendering: per frame]
             ↓
    Vertices unpacked in Vertex Shader → Position + Attributes
             ↓
    Fragment Shader colors pixels

Custom Mesh Variants
--------------------

**CloudMesh:**

Fixed procedural clouds (no greedy meshing). Uses 2D Simplex noise to determine cloud density at each point. Emits simplified geometry.

**ItemMesh:**

Dropped items (pickaxe, stick, etc.) use simplified meshes. No greedy meshing; pre-defined vertex data per item type.

**ObjMesh:**

Loads Wavefront .obj files (trees, decorative structures). Parses vertices, UVs, normals. Stores as-is; no meshing.

Replication Guide
-----------------

**To reimplement greedy meshing from scratch:**

1. Load voxel data into 3D array or flattened 1D array
2. For each of 3 planes:
   a. Build 2D solid/empty mask (iterate through slice)
   b. Extract rectangles greedily (nested loop with width/height expansion)
   c. For each rectangle, calculate 4 corner lights and AO values
   d. Pack into 32-bit integers
   e. Emit 2 triangles (6 indices) for the quad
3. Separate water faces from opaque
4. Upload to GPU as VBO
5. Render with phased passes (opaque → transparent)

**Pseudocode:**

.. code-block:: python

    def build_mesh(chunk_voxels):
        vertex_data = []
        light_data = []
        
        # Process each plane
        for plane in ['X', 'Y', 'Z']:
            for slice_idx in range(CHUNK_SIZE):
                mask = build_mask(chunk_voxels, plane, slice_idx)
                
                processed = set()
                for start_y, start_z in iterate_mask(mask):
                    if (start_y, start_z) in processed:
                        continue
                    
                    width, height = greedy_expand(mask, start_y, start_z, processed)
                    
                    corners_light = sample_4_corners(start_y, start_z)
                    corners_ao = sample_4_corners_ao(start_y, start_z)
                    flip = compute_flip(corners_light, corners_ao)
                    
                    packed = pack_vertices(slice_idx, start_y, start_z, width, height, flip)
                    vertex_data.extend(packed)
        
        return np.array(vertex_data, dtype=np.uint32), np.array(light_data, dtype=np.uint32)


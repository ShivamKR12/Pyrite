.. _lighting:

Lighting System:
================

This document provides a detailed replication guide for Pyrite's dynamic voxel lighting system, including sunlight propagation, blocklight spreading, queue-based BFS, and lightmap packing.

Overview
--------

Pyrite uses a Breadth-First Search (BFS) algorithm to propagate light from sources and sunlight downward. The system handles two types of light:

- **Sunlight:** From top of world, level 15 at surface, dims through water/leaves
- **Blocklight:** From torches/glowstone, spreads spherically, diminishes by 1 per block

Both are packed into a single byte (4 bits each) for memory efficiency.

Lightmap Data Structure
-----------------------

**Packing Format:**

.. code-block:: python

    # Reference packing (actual engine uses compiled Numba for speed)
    # sunlight: 0-15 (upper 4 bits)
    # blocklight: 0-15 (lower 4 bits)
    packed = (sunlight << 4) | blocklight
    
    # Unpacking
    sunlight = (packed >> 4) & 0xF
    blocklight = packed & 0xF

**Storage:**

- **1D array per chunk:** (110592), uint8 array
- **Index calculation:** `index = x + z * 48 + y * 48²`
- **Typical size:** ~108 KB per chunk (uncompressed), ~27 KB (compressed)

Sunlight Propagation Algorithm
-------------------------------

**Initialization (new or unloaded chunk):**

1. Cast sunlight downward from top
2. Maintain level 15 through air until hitting solid blocks
3. Reduce by 2 through water/leaves, by 1 through other transparent blocks

.. code-block:: python

    def init_chunk_sunlight(chunk_voxels, chunk_lightmap):
        """Initialize sunlight for freshly loaded chunk"""
        
        # Constants
        LIGHT_LEVEL_MAX = 15
        SUNLIGHT_QUEUE = []  # BFS queue
        
        # Step 1: Cast sunlight downward
        for x in range(CHUNK_SIZE):
            for z in range(CHUNK_SIZE):
                current_level = LIGHT_LEVEL_MAX
                
                for y in range(CHUNK_SIZE - 1, -1, -1):  # Top to bottom
                    voxel_id = chunk_voxels[x + z * 48 + y * 48**2]
                    
                    if not is_transparent(voxel_id):
                        # Hit solid block, light propagates no further down this column
                        break
                    
                    # Set sunlight for this air block
                    lightmap_index = x + z * 48 + y * 48**2
                    packed = chunk_lightmap[lightmap_index]
                    blocklight = packed & 0xF
                    # Pack into single byte: (sunlight << 4) | blocklight
                    chunk_lightmap[lightmap_index] = (current_level << 4) | blocklight
                    
                    # Queue for horizontal spread
                    SUNLIGHT_QUEUE.append((x, y, z, current_level, SUNLIGHT))
                    
                    # Reduce level through certain blocks
                    if voxel_id == WATER or voxel_id == LEAVES:
                        current_level = max(0, current_level - 2)
                    elif voxel_id in [GLASS]:
                        current_level = max(0, current_level - 1)
        
        # Step 2: Propagate horizontally (BFS)
        propagate_light_bfs(chunk_voxels, chunk_lightmap, SUNLIGHT_QUEUE, SUNLIGHT)

**O(1) Vertical Raycast Optimization:**

When a block is mined exposing a hole to sunlight, instead of expensive 3D BFS:

Vertical Raycast Optimization:

When a block is mined exposing a hole to sunlight, an O(1) downward fill is more efficient than 3D BFS:

.. code-block:: python

    # Pseudo-code: how vertical sunlight filling optimizes block breaking
    # (Actual implementation is inside update_light_remove_block in src/lighting.py)
    
    def quick_sunlight_fill(x, y, z, chunk_voxels, chunk_lightmap):
        """Quick downward fill for exposed blocks"""
        
        LIGHT_LEVEL_MAX = 15
        current_level = LIGHT_LEVEL_MAX
        
        for dy in range(y, CHUNK_SIZE):  # Downward
            voxel_id = chunk_voxels[x + z * 48 + dy * 48**2]
            
            if not is_transparent(voxel_id):
                break  # Hit solid, propagation stops
            
            # Set light: (current_level << 4) | blocklight
            lightmap_index = x + z * 48 + dy * 48**2
            packed = chunk_lightmap[lightmap_index]
            blocklight = packed & 0xF
            chunk_lightmap[lightmap_index] = (current_level << 4) | blocklight
            
            # Apply diminishment
            if voxel_id == WATER or voxel_id == LEAVES:
                current_level = max(0, current_level - 2)
        
        # Queue neighboring blocks for BFS expansion

BFS Light Propagation
---------------------

**Queue-Based Approach (CPU-efficient):**

Instead of Python lists (slow), use preallocated NumPy arrays as ring buffers:

**Queue-Based Approach (Actual Implementation):**

The engine uses global pre-allocated NumPy arrays as ring buffers for efficiency:

.. code-block:: python

    # Actual implementation in src/lighting.py uses:
    # - GLOBAL_QUEUE_A: numpy array storing (x, y, z, level) tuples
    # - GLOBAL_QUEUE_B: numpy array for secondary queue
    # - Head/tail pointers for ring buffer management
    #
    # See propagate_light_queue(queue, tail, is_sun, ...) in src/lighting.py

**Main BFS Loop:**

.. code-block:: python

    # Pseudo-code for light propagation (actual: propagate_light_queue in src/lighting.py)
    def propagate_light_queue(queue, tail, is_sun, world_voxels, world_lightmaps, chunk_positions):
        """Propagate light using BFS queue.
        
        Args:
            queue: Pre-allocated array of light nodes
            tail: Current position in ring buffer
            is_sun: True for sunlight, False for blocklight
            world_voxels: All loaded chunk voxels
            world_lightmaps: All loaded chunk lightmaps
            chunk_positions: Chunk position lookup table
        """
        
        DIRECTIONS = [
        When a torch is removed or a block is broken, light must be recalculated. The algorithm uses a **Removal Pass** followed by a **Refill Pass**:

        .. code-block:: python

            # Pseudo-code for light source removal (actual: update_light_remove_block in src/lighting.py)
            def remove_block_light_update(broken_x, broken_y, broken_z, world_voxels, world_lightmaps, chunk_positions):
                """Recalculate lighting after a block is broken.
        
                Two-pass algorithm:
                1. Removal pass: Scan neighbors and decrement light if it came from broken light source
                2. Refill pass: Propagate light from unaffected sources to refill dark areas
                """
            node = queue.dequeue()
            if node is None:
                break
            
            x, y, z, level = node
            
            # Skip if at lowest possible light level
            if level <= 0:
                continue
            
            # Check all 6 neighbors
            for dx, dy, dz in DIRECTIONS:
                neighbor_x = x + dx
                neighbor_y = y + dy
                neighbor_z = z + dz
                
                # Skip out-of-bounds
                if neighbor_y < 0 or neighbor_y >= WORLD_HEIGHT:
                    continue
                
                # Get neighbor voxel and light
                neighbor_voxel = get_voxel_fast(neighbor_x, neighbor_y, neighbor_z, world_voxels)
                neighbor_light = get_light_fast(neighbor_x, neighbor_y, neighbor_z, world_lightmaps, light_type)
                
                # Skip if solid
                if not is_transparent(neighbor_voxel):
                    continue
                
                # Calculate diminished light
                if light_type == SUNLIGHT and dy == 1 and neighbor_voxel == AIR:
                    # Special case: downward through air keeps full level 15
                    new_level = level
                else:
                    # Standard: diminish by 1 (or 2 for water/leaves)
                    diminish = 1
                    if neighbor_voxel in [WATER, LEAVES]:
                        diminish = 2
                    new_level = max(0, level - diminish)
                
                # Update if brighter
                if new_level > neighbor_light:
                    set_light_fast(neighbor_x, neighbor_y, neighbor_z, world_lightmaps, light_type, new_level)
                    queue.enqueue(neighbor_x, neighbor_y, neighbor_z, new_level)

**Fast Voxel Access Helper:**

.. code-block:: python

    def get_voxel_fast(world_x, world_y, world_z, world_voxels):
        """Get voxel ID with chunk boundary handling"""
        chunk_x = world_x // CHUNK_SIZE
        chunk_y = world_y // CHUNK_SIZE
        chunk_z = world_z // CHUNK_SIZE
        
        # Check if chunk loaded
        key = (chunk_x, chunk_y, chunk_z)
        if key not in world_voxels:
            return STONE  # Unloaded = solid
        
        # Get local index
        local_x = world_x % CHUNK_SIZE
        local_y = world_y % CHUNK_SIZE
        local_z = world_z % CHUNK_SIZE
        local_index = local_x + local_z * CHUNK_SIZE + local_y * CHUNK_SIZE ** 2
        
        return world_voxels[key][local_index]

Blocklight (Torch) Propagation
-------------------------------

**Torch Placement:**

.. code-block:: python

    def place_torch(world_x, world_y, world_z, world_lightmaps, queue):
        """Place torch and start light propagation"""
        
        set_light_fast(world_x, world_y, world_z, world_lightmaps, BLOCKLIGHT, 14)
        queue.enqueue(world_x, world_y, world_z, 14)  # Torch emits level 14
        
        # Start BFS propagation
        propagate_light_bfs(world_voxels, world_lightmaps, chunk_positions, queue, BLOCKLIGHT)

**Breaking a Torch (Removal Pass + Refill):**

.. code-block:: python

    def remove_light_source(broken_x, broken_y, broken_z, world_voxels, world_lightmaps, queue):
        """Remove light from broken torch"""
        
        # Step 1: REMOVAL PASS - drain dependent light
        removal_queue = LightQueue()
        removal_queue.enqueue(broken_x, broken_y, broken_z, 14)
        
        while True:
            node = removal_queue.dequeue()
            if node is None:
                break
            
            x, y, z, level = node
            
            # Check all 6 neighbors
            for dx, dy, dz in [(-1,0,0), (1,0,0), (0,-1,0), (0,1,0), (0,0,-1), (0,0,1)]:
                neighbor_x, neighbor_y, neighbor_z = x + dx, y + dy, z + dz
                
                neighbor_voxel = get_voxel_fast(neighbor_x, neighbor_y, neighbor_z, world_voxels)
                if not is_transparent(neighbor_voxel):
                    continue
                
                neighbor_light = get_light_fast(neighbor_x, neighbor_y, neighbor_z, world_lightmaps, BLOCKLIGHT)
                
                # If neighbor was lit by broken torch, reduce its light
                if neighbor_light > 0 and neighbor_light < level:
                    # This light was dependent on broken torch
                    set_light_fast(neighbor_x, neighbor_y, neighbor_z, world_lightmaps, BLOCKLIGHT, 0)
                    removal_queue.enqueue(neighbor_x, neighbor_y, neighbor_z, neighbor_light)
                elif neighbor_light >= level:
                    # This light is from another source (brighter neighbor)
                    # Capture for refill pass
                    refill_queue.enqueue(neighbor_x, neighbor_y, neighbor_z, neighbor_light)
        
        # Step 2: REFILL PASS - propagate light from surviving sources
        propagate_light_bfs(world_voxels, world_lightmaps, chunk_positions, refill_queue, BLOCKLIGHT)

Chunk Boundary Stitching
------------------------

When chunks load/unload, light must be synchronized across boundaries:

.. code-block:: python

    def stitch_chunk_lighting(chunk_x, chunk_y, chunk_z, world_voxels, world_lightmaps):
        """Ensure light propagates correctly across chunk edges"""
        
        # Check 6 neighbors of chunk
        neighbors = [
            (chunk_x - 1, chunk_y, chunk_z),
            (chunk_x + 1, chunk_y, chunk_z),
            (chunk_x, chunk_y - 1, chunk_z),
            (chunk_x, chunk_y + 1, chunk_z),
            (chunk_x, chunk_y, chunk_z - 1),
            (chunk_x, chunk_y, chunk_z + 1),
        ]
        
        light_queue = LightQueue()
        
        for neighbor_chunk in neighbors:
            if neighbor_chunk not in world_lightmaps:
                continue
            
            # For each edge voxel of current chunk
            # Check if neighbor has brighter light
            # If so, start propagation from boundary
            
            # Example: check +X boundary
            if neighbor_chunk[0] == chunk_x + 1:
                for y in range(CHUNK_SIZE):
                    for z in range(CHUNK_SIZE):
                        # Current chunk edge (x = 47)
                        current_light = get_light(chunk_x, 47, y, z, world_lightmaps, SUNLIGHT)
                        
                        # Neighbor edge (x = 0 in neighbor chunk)
                        neighbor_light = get_light(neighbor_chunk[0], 0, y, z, world_lightmaps, SUNLIGHT)
                        
                        if neighbor_light > current_light:
                            # Neighbor is brighter, propagate inward
                            light_queue.enqueue(chunk_x * 48 + 47, chunk_y * 48 + y, chunk_z * 48 + z, neighbor_light)
        
        # Run BFS from boundaries
        if light_queue.head != light_queue.tail:
            propagate_light_bfs(world_voxels, world_lightmaps, chunk_positions, light_queue, SUNLIGHT)

Integration with Rendering
---------------------------

**Shader Light Application:**

.. code-block:: glsl

    // In chunk.frag
    in float sun_light;    // Interpolated sunlight (0.0-1.0)
    in float block_light;  // Interpolated blocklight (0.0-1.0)
    
    void main() {
        // Sample base color
        vec3 color = texture(u_texture_array, vec3(uv, texLayer)).rgb;
        
        // Apply day/night cycle to sunlight
        float day_night = 0.5 + 0.5 * u_sun_direction.y;  // -1 (night) to 1 (day)
        float adjusted_sun = sun_light * day_night;
        
        float adjusted_block = block_light;
        
        // Combine lights (take maximum for natural look)
        float final_light = max(adjusted_sun, adjusted_block);
        
        // Apply to final color
        vec3 lit_color = color * final_light;
        fragColor = vec4(lit_color, 1.0);
    }

Replication Checklist
---------------------

1. ✓ Implement lightmap packing/unpacking
2. ✓ Create sunlight initialization (downward raycast)
3. ✓ Implement BFS light propagation with queue
4. ✓ Add blocklight support (torches)
5. ✓ Implement removal pass + refill logic
6. ✓ Add chunk boundary stitching
7. ✓ Integrate with mesh building (per-vertex light sampling)
8. ✓ Connect to shader (lighting application)

Performance Considerations
--------------------------

- **Queue size:** 200K nodes typical max (prevents explosion of propagation)
- **Diminishment:** Constants prevent infinite propagation
- **Optimization:** O(1) downward raycasts for common case
- **Threading:** Entire BFS can run on background thread (no GIL issues with Numba)


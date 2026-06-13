.. _lighting:

===============
Lighting System
===============

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

    packed = (sunlight << 4) | blocklight
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

    for y in range(CHUNK_SIZE - 1, -1, -1):
        voxel_id = chunk_voxels[x + z * 48 + y * 48**2]

* **Downward Raycast:** The initialization loop scans from the top of the chunk to the bottom, checking the voxel ID at each height layer.

.. code-block:: python

    if not is_transparent(voxel_id):
        break

* **Collision Halting:** If the downward ray encounters a solid, non-transparent block, sunlight is immediately stopped for that column.

.. code-block:: python

    chunk_lightmap[lightmap_index] = (current_level << 4) | blocklight

* **Data Packing:** The active sunlight level is bitshifted left by 4 to occupy the upper 4 bits, then merged securely with the existing blocklight via bitwise OR.

**O(1) Vertical Raycast Optimization:**

When a block is mined exposing a hole to sunlight, instead of expensive 3D BFS:

Vertical Raycast Optimization:

When a block is mined exposing a hole to sunlight, an O(1) downward fill is more efficient than 3D BFS:

.. code-block:: python

    for dy in range(y, CHUNK_SIZE):
        voxel_id = chunk_voxels[x + z * 48 + dy * 48**2]

* **O(1) Downward Fill:** When a block is broken, the engine casts a simple ray downwards from the broken block to instantly fill exposed air rather than launching an expensive 3D BFS.

.. code-block:: python

    if voxel_id == WATER or voxel_id == LEAVES:
        current_level = max(0, current_level - 2)

* **Light Diminishment:** Even during quick fills, light is strictly reduced by 2 levels if it passes through semi-transparent blocks.

BFS Light Propagation
---------------------

**Queue-Based Approach (CPU-efficient):**

Instead of Python lists (slow), use preallocated NumPy arrays as ring buffers:

**Queue-Based Approach:**

The engine uses global pre-allocated NumPy arrays directly as ring buffers for efficiency:

.. code-block:: python

    GLOBAL_QUEUE = np.zeros(MAX_QUEUE_SIZE, dtype=np.uint32)
    head, tail = 0, 0

**Main BFS Loop:**

.. code-block:: python

    while True:
        node = queue.dequeue()
        if node is None: break

* **BFS Ring Buffer Loop:** A memory-efficient array dequeues active light nodes dynamically without instantiating slow Python lists.

.. code-block:: python

    if new_level > neighbor_light:
        queue.enqueue(neighbor_x, neighbor_y, neighbor_z, new_level)

* **Neighbor Expansion:** For each of the 6 neighboring blocks, if the newly propagated light is brighter than the neighbor's current light, it overwrites it and pushes the neighbor into the queue for further expansion.

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

    set_light_fast(world_x, world_y, world_z, world_lightmaps, BLOCKLIGHT, 14)
    queue.enqueue(world_x, world_y, world_z, 14)

* **Blocklight Seeding:** A newly placed torch injects a maximum blocklight value of `14` directly into the chunk lightmap and starts expanding immediately.

**Breaking a Torch (Removal Pass + Refill):**

When a torch is removed or a block is broken, light must be recalculated. The algorithm uses a **Removal Pass** followed by a **Refill Pass**:

.. code-block:: python

    if neighbor_light > 0 and neighbor_light < level:
        set_light_fast(neighbor_x, neighbor_y, neighbor_z, world_lightmaps, BLOCKLIGHT, 0)
        removal_queue.enqueue(neighbor_x, neighbor_y, neighbor_z, neighbor_light)

* **Removal Pass:** When a light source is destroyed, a negative BFS sweeps outward, aggressively setting all dependent light levels back to `0`.

.. code-block:: python

    elif neighbor_light >= level:
        refill_queue.enqueue(neighbor_x, neighbor_y, neighbor_z, neighbor_light)

* **Refill Pass:** If the removal pass hits a light level equal to or brighter than what it's trying to erase, it stops and marks that border block as a seed to immediately refill the empty space.

Chunk Boundary Stitching
------------------------

When chunks load/unload, light must be synchronized across boundaries:

.. code-block:: python

    if neighbor_light > current_light:
        light_queue.enqueue(chunk_x * 48 + 47, chunk_y * 48 + y, chunk_z * 48 + z, neighbor_light)

* **Chunk Seams:** When adjacent chunks load, they sample the immediate edge boundaries of their neighbors. Brighter light is naturally enqueued to bleed seamlessly across the chunk boundaries.

Integration with Rendering
---------------------------

**Shader Light Application:**

.. code-block:: glsl

    float final_light = max(sun_light * day_night, block_light);
    vec3 lit_color = color * final_light;

* **Maximum Blending:** To prevent blowouts, the fragment shader computes the final lighting multiplier by taking the maximum (not the sum) of the dynamically scaled sunlight and static blocklight.

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

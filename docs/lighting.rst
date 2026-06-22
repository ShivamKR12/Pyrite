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

This lighting system uses two different update paths:

* **Initialization / chunk load:** compute sunlight with a vertical raycast for the newly loaded chunk.
* **Dynamic updates (mining/building):** when the player changes a block, propagate changes with a targeted downward fill when a hole opens, otherwise use BFS.


**1) Sunlight initialization (new or unloaded chunk)**

**Rules for transparency / attenuation**

Sunlight starts at **level 15** at the top of the world (per column) and then walks downward.

* A voxel is considered **opaque** if it blocks light.
* A voxel is considered **transparent** if light passes through.

Attenuation is applied only when light passes through transparent voxels:

* Through **water or leaves**: reduce by **2** levels
* Through **other transparent blocks**: reduce by **1** level
* Through **opaque** voxels: stop immediately (no further sunlight)

.. code-block:: python

    for y in range(CHUNK_SIZE - 1, -1, -1):
        voxel_id = chunk_voxels[x + z * 48 + y * 48**2]

        if not is_transparent(voxel_id):
            break

        # apply reduction based on voxel type
        if voxel_id == WATER or voxel_id == LEAVES:
            current_level = max(0, current_level - 2)
        else:
            current_level = max(0, current_level - 1)

        chunk_lightmap[lightmap_index] = (current_level << 4) | blocklight


**Downward raycast / collision halting**

.. code-block:: python

    if not is_transparent(voxel_id):
        break

**Data packing into the lightmap**

Sunlight is stored in the **upper 4 bits** of the 8-bit packed lightmap value, blocklight in the lower 4 bits.

.. code-block:: python

    chunk_lightmap[lightmap_index] = (current_level << 4) | blocklight

That is:

* ``(current_level << 4)`` places sunlight into bits 4..7
* ``| blocklight`` preserves the existing blocklight bits 0..3

**2) O(1) vertical raycast optimization (when a hole opens)**

When a block is broken and exposes a path to the sky, the engine avoids a full 3D BFS and instead performs a **vertical downward fill** from the opened block.


* scan downward from the broken location until you hit an opaque voxel
* update ``current_level`` as you pass through semi-transparent voxels


.. code-block:: python

    for dy in range(y, CHUNK_SIZE):
        voxel_id = chunk_voxels[x + z * 48 + dy * 48**2]

    if voxel_id == WATER or voxel_id == LEAVES:
        current_level = max(0, current_level - 2)
    elif is_transparent(voxel_id):
        current_level = max(0, current_level - 1)

**Which path is used when?**

* **Hole to sky appears** → use the downward fill path.
* **Torch placed/removed** → use BFS for the affected region.


BFS Light Propagation
---------------------

**Queue representation (what a BFS node contains)**

The BFS queue stores *nodes* describing **where** the light should propagate and **what brightness level** to apply.

A practical packed node format is:

.. code-block:: text

    node = (x, y, z, level)

Internally this is backed by a preallocated NumPy array and treated as a **ring buffer** (two indices: ``head`` and ``tail``) to avoid Python object allocations.

.. code-block:: python

    GLOBAL_QUEUE = np.zeros(MAX_QUEUE_SIZE, dtype=np.uint32)
    head, tail = 0, 0

**Main BFS loop**

.. code-block:: python

    while True:
        node = queue.dequeue()
        if node is None: break

For each dequeued node, expand to the **6 axis neighbors** (+X/-X/+Y/-Y/+Z/-Z). Light only updates a neighbor if it can improve it:

.. code-block:: python

    if new_level > neighbor_light:
        queue.enqueue(neighbor_x, neighbor_y, neighbor_z, new_level)

**Transparent / opaque rule inside BFS**

During BFS:

* If the neighbor voxel is **opaque**, the neighbor does not receive propagated light.
* If it is **transparent**, the propagation continues with attenuation:

  * water/leaves: ``new_level - 2``
  * other transparent: ``new_level - 1``

Blocklight (Torch) Propagation
-------------------------------

**Torch placement (seeding BFS)**

A newly placed torch injects blocklight at the maximum value (14) into the lightmap and enqueues it as the BFS seed.

.. code-block:: python

    set_light_fast(world_x, world_y, world_z, world_lightmaps, BLOCKLIGHT, 14)
    queue.enqueue(world_x, world_y, world_z, 14)

**Torch removal / recalculation (Removal pass + Refill pass)**

Removing a torch is harder than adding: simply stopping the new light will often leave “stale” light behind. The algorithm therefore performs:

1) **Removal pass:** walk outward and erase only regions that depended on the removed source.
2) **Refill pass:** stop erasing when reaching cells that are still supported by *other* sources (or brighter equal levels), and seed refill where needed.

**Removal pass behavior**

.. code-block:: python

    if neighbor_light > 0 and neighbor_light < level:
        set_light_fast(neighbor_x, neighbor_y, neighbor_z, world_lightmaps, BLOCKLIGHT, 0)
        removal_queue.enqueue(neighbor_x, neighbor_y, neighbor_z, neighbor_light)

**Refill pass behavior**

.. code-block:: python

    elif neighbor_light >= level:
        refill_queue.enqueue(neighbor_x, neighbor_y, neighbor_z, neighbor_light)

Chunk Boundary Stitching
------------------------

**Correctness across chunk boundaries**

Light propagation must remain consistent when neighboring chunks are loaded/unloaded.

The doc rule of thumb used by the engine is:

* Treat **unloaded chunks as opaque** for propagation decisions (so BFS does not propagate through missing geometry).
* When a neighbor chunk becomes loaded, resample the boundary and enqueue any boundary cells whose light level can improve the newly loaded chunk.


**Edge sampling / seam enqueue**

.. code-block:: python

    if neighbor_light > current_light:
        light_queue.enqueue(chunk_x * 48 + 47, chunk_y * 48 + y, chunk_z * 48 + z, neighbor_light)

This ensures:

* If the neighbor is brighter, the newly loaded chunk receives that brightness at the seam.
* If the neighbor is not brighter, the seam remains unchanged.

Integration with Rendering
---------------------------


**Shader Light Application:**

.. code-block:: glsl

    float final_light = max(sun_light * day_night, block_light);
    vec3 lit_color = color * final_light;

* **Maximum Blending:** To prevent blowouts, the fragment shader computes the final lighting multiplier by taking the maximum (not the sum) of the dynamically scaled sunlight and static blocklight.

Next Steps
----------

With the lighting maps generated, proceed to the :doc:`meshes` guide.

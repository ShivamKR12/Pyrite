Volumetric Lighting Engine
==========================

Pyrite implements a dynamic, voxel-based lighting engine capable of real-time shadow updates. It utilizes a Numba-optimized Breadth-First Search (BFS) algorithm that traverses chunk boundaries seamlessly. 

Memory-Packed Lightmaps
-----------------------
To save memory, every chunk stores a 1D `uint8` array containing the light levels for all 110,592 blocks in the chunk. Because light levels only go from 0 to 15 (requiring only 4 bits), both Sunlight and Blocklight are packed into a single byte:

`light_value = (sun_light << 4) | block_light`

Bit-Packed Propagation Queues
-----------------------------
Standard Python `collections.deque` objects are too slow for an engine making millions of iterations per second. Instead, the lighting engine pre-allocates massive, flat `uint64` Numpy arrays (`queue = np.empty(200000, dtype=np.uint64)`) to act as C-style ring buffers managed by a `head` and `tail` pointer.

To fit a block's 3D coordinate and light-level into the queue without instantiating a Python Tuple, the data is bit-shifted into a single 64-bit integer:

* **Adding Light:** `(x << 32) | (y << 16) | z`
* **Removing Light:** `(x << 40) | (y << 24) | (z << 8) | light_level`

Sunlight Propagation
--------------------
When a chunk is first generated, sunlight is cast straight down from the top of the world. It maintains a power of 15 until it hits a solid block. Water and Leaves diminish the light by 2 levels per block, while opaque blocks block it entirely.

**The O(1) Vertical Raycast Optimization:**
If the player mines a block that is directly exposed to sunlight from above, the engine avoids an expensive 3D volumetric BFS expansion. Instead, it performs an `O(1)` vertical linear raycast downward, instantly flooding the newly created hole with level-15 light until it hits the next solid surface, before queueing horizontal expansion.

Blocklight (Glowstone / Torches)
--------------------------------
Blocklight spreads spherically, diminishing by 1 level per block. When a light source is broken:

1. **Removal Pass:** The engine recursively strips the existing light values from the area, pushing dark nodes outward as long as the neighbor's light level is lower than the current node's previous light level.
2. **Refill Capture:** If the removal pass hits a light node that is *equal to or brighter* than what it expects, it means that light is coming from a completely different surviving light source. That bright node is captured and placed into a `refill_queue`.
3. **Refill Pass:** The `refill_queue` is passed back into standard BFS propagation to flood light back into the newly darkened room.

Shader Integration
------------------
The OpenGL Fragment Shader reads the interpolated sunlight and blocklight values. The final fragment color is derived by taking the `max()` of the two light channels.

* **Day/Night Cycle:** The sunlight channel is multiplied by a trigonometric time uniform (`u_sun_direction.y`), naturally dimming the sun-lit areas as the world turns to night.
* **Dynamic Flicker:** A trigonometric noise formula (`1.0 + 0.05 * sin(u_time * 10.0) * cos(u_time * 23.0)`) is applied exclusively to the blocklight channel to simulate the natural, organic flicker of torches and glowstone.

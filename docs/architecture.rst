Engine Architecture
===================

Pyrite is built on a hybrid architecture combining Pygame (for windowing and events), ModernGL (for hardware-accelerated OpenGL rendering), and Numba (for high-performance mathematics).

The Main Loop & Asynchronous Processing
---------------------------------------
The core game loop runs strictly on the main thread, handling player inputs, camera updates, and issuing draw calls to the GPU. Because Python's Global Interpreter Lock (GIL) prevents true multi-threading for standard Python objects, heavy engine tasks are offloaded using two specific techniques:

1. **The ThreadPoolExecutor:** Background Python threads are used strictly for I/O operations (reading/writing to the SQLite database) and executing pre-compiled Numba functions.
2. **Numba nogil=True:** The heaviest tasks (Procedural Noise, Greedy Meshing, and BFS Lighting) are compiled to raw LLVM machine code. By passing the `nogil=True` flag, these functions completely detach from the Python interpreter, allowing them to utilize 100% of all available physical CPU cores simultaneously without freezing the Pygame render loop.

The Queue System
----------------
To manage the flow of asynchronous data back to the synchronous main thread (which is required for OpenGL calls), Pyrite uses a robust queue pipeline:

* **load_queue:** Contains background futures fetching or generating raw voxel data. Once complete, the chunks are passed to the `build_queue`.
* **build_queue:** A list of chunks awaiting greedy meshing. To prioritize player experience, this queue is dynamically re-sorted every frame so that chunks closest to the player are processed first.
* **mesh_queue:** Contains the final step. The main thread safely pops from this queue to allocate OpenGL Vertex Buffer Objects (VBOs) and Vertex Array Objects (VAOs) without risking cross-thread OpenGL context crashes. To prevent memory leaks, Pyrite utilizes a **VBO Pool** that recycles released buffers for new meshes.

World & Data Persistence
------------------------
Pyrite handles infinite terrain through a chunk-based streaming system. Each chunk is a 48x48x48 (`CHUNK_SIZE`) grid.

To prevent RAM exhaustion, active chunks are stored in a centralized dictionary (`world.active_chunks`). As the player moves, a 2D grid distance check determines which chunks fall out of the configured `render_distance`. Unloaded chunks are serialized and saved to disk.

SQLite Write-Ahead Logging (WAL)
--------------------------------
Because Python's standard file handling can be slow for millions of blocks, Pyrite uses a local SQLite `.db` file configured with `PRAGMA journal_mode = WAL`. This provides async-like, high-performance disk writes.

The database caches three primary states:

1. **The chunks Table:** 
   Stores the absolute `x, y, z` chunk coordinates as the Primary Key. The chunk's 1D `uint8` Numpy arrays for Voxels and Lightmaps are compressed using `zlib.compress()` and stored as raw `BLOB` data.
2. **The player_data Table:**
   Stores a serialized JSON string containing the player's exact `[x, y, z]` coordinates, camera angles (Yaw, Pitch), survival stats (Health, Hunger, Oxygen), and the exact state of the 41-slot inventory arrays.
3. **The world_meta Table:**
   Stores high-level data like the Seed, World Name, Game Mode, and timestamps.

Memory Management (1D vs 3D Arrays)
-----------------------------------
Instead of storing chunks as slow, nested Python lists (e.g., `chunk[x][y][z]`), Pyrite flattens all volumetric data into 1D Numpy arrays. 

A block's specific index in the array is calculated using: 
`index = x + z * CHUNK_SIZE + y * CHUNK_AREA`. 

This guarantees contiguous memory alignment, ensuring maximum CPU Cache utilization during Numba JIT execution.

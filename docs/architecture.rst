.. _architecture:

World Architecture and Multithreading Breakdown
===============================================

This document provides detailed explanations of Pyrite's core architectural loop, multithreaded chunk streaming, queue systems, and SQLite disk persistence. All core architectural logic is primarily located in ``src/world.py`` and ``src/main.py``.

Architecture Overview
---------------------

Pyrite is built on a hybrid architecture combining Pygame, ModernGL, and Numba:

.. code-block:: text

    1. The Main Loop         → Synchronous Pygame events and rendering.
    2. ThreadPoolExecutor    → Asynchronous Numba compilation and DB reads.
    3. The Queue System      → Safely syncing background data to the main thread.
    4. SQLite WAL            → High-performance disk persistence.
    5. 1D Array Flattening   → Cache-optimized memory layout.

The Main Loop & Asynchronous Processing
---------------------------------------

``src/main.py`` - The Core Execution Loop

Purpose: Maintain a stutter-free render loop while offloading heavy tasks.

.. code-block:: python

    self.delta_time = min(self.clock.tick(), 50)

* **Tick Control:** The main game loop runs strictly on the main thread. We cap the delta time at 50ms to prevent massive physics lag spikes (like falling through the floor) if the engine momentarily hangs.

``src/world.py`` - The ThreadPool

Purpose: Execute Python functions in the background.

.. code-block:: python

    self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max(4, (os.cpu_count() or 5) - 1))

* **Thread Allocation:** We allocate background worker threads based on the user's CPU core count (leaving one core free for the OS/Main Thread). These threads handle I/O operations and execute Numba functions.

.. code-block:: python

    future = self.executor.submit(self._fetch_or_generate_voxels, x, y, z)

* **Non-Blocking Dispatch:** Instead of pausing the game to load terrain, we submit the chunk coordinates to the ThreadPool. The main thread immediately continues rendering the next frame.

The Queue System
----------------

``src/world.py`` - Safe Thread Synchronization

Purpose: Manage the flow of asynchronous data back to the synchronous main thread.

.. code-block:: python

    self.load_queue: List[Tuple[Optional[Chunk], concurrent.futures.Future[Any]]] = []

* **Load Queue:** Contains background futures fetching or generating raw voxel data. Once a future resolves, the main thread extracts the 1D arrays and initializes the Chunk object.

.. code-block:: python

    self.build_queue.sort(key=lambda c: (c.position[0] - player_cx) ** 2 + (c.position[2] - player_cz) ** 2, reverse=True)

* **Build Queue Prioritization:** Contains chunks awaiting greedy meshing. To prioritize player experience, this queue is dynamically re-sorted using squared distances so chunks closest to the player generate their meshes first.

.. code-block:: python

    self.vbo_pool.append((chunk.mesh.vbo, chunk.mesh.vao))

* **Mesh Queue & VBO Pooling:** The main thread pops completed meshes to allocate OpenGL VBOs/VAOs safely. To prevent VRAM exhaustion during fast movement, Pyrite recycles old buffer objects into a ``vbo_pool`` instead of constantly creating new ones.

SQLite Write-Ahead Logging (WAL)
--------------------------------

``src/world.py`` - Database Initialization

Purpose: Provide async-like, high-performance disk writes for massive voxel datasets.

.. code-block:: python

    self.cursor.execute('PRAGMA journal_mode = WAL')
    self.cursor.execute('PRAGMA synchronous = NORMAL')

* **WAL Configuration:** Python's standard file handling is too slow for millions of blocks. Enabling Write-Ahead Logging allows SQLite to append writes to a separate log file, drastically reducing I/O blocking.

.. code-block:: python

    self.cursor.execute('INSERT OR REPLACE INTO chunks (x, y, z, data, lightmap) VALUES (?, ?, ?, ?, ?)', (x, y, z, data, l_data))

* **Chunk Serialization:** When a chunk unloads, its 1D ``uint8`` Numpy arrays for Voxels and Lightmaps are compressed using ``zlib.compress()`` and stored as raw binary ``BLOB`` data mapped to its XYZ coordinate.

.. code-block:: python

    self.thread_local.cursor.execute('SELECT data, lightmap FROM chunks WHERE x=? AND y=? AND z=?', (x, y, z))

* **Thread-Local Reads:** SQLite cursors cannot be safely shared across background threads. We attach independent cursors to ``threading.local()`` to prevent connection overlap crashes while the ThreadPool fetches chunks.

Memory Management (1D vs 3D Arrays)
-----------------------------------

``src/terrain_gen.py`` - Array Flattening

Purpose: Maximize CPU cache hits during Numba JIT execution.

.. code-block:: python

    def get_index(x: int, y: int, z: int) -> int:
        return x + CHUNK_SIZE * z + CHUNK_AREA * y

* **Row-Major Layout:** Instead of using slow, nested Python lists (``chunk[x][y][z]``), all chunk data is flattened into a single contiguous 1D Numpy array.
* **Cache Optimization:** X advances fastest, then Z, and Y last. This contiguous alignment allows the CPU prefetcher to load adjacent blocks efficiently, which is critical for Numba's vectorization speeds.

Next Steps
----------

With a solid grasp of the asynchronous thread pool and engine queues, continue to :doc:`persistence` to see how Pyrite permanently saves terrain and player data directly to the disk.

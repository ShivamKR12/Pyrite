.. _profiling:

Telemetry Systems and Profiling Breakdown
=========================================

This document provides detailed explanations of Pyrite's custom-built, lock-free telemetry engine. The profiler is designed to aggressively track CPU performance across background worker threads without introducing GIL (Global Interpreter Lock) contention. All core profiling logic is located in ``src/profiler.py``.

Architecture Overview
---------------------

Pyrite utilizes a Thread-Local approach to telemetry:

.. code-block:: text

    1. Thread Initialization → Each background thread receives an isolated buffer.
    2. Lock-Free Recording   → Data is appended to CPython thread-safe deques.
    3. API Wrappers          → Decorators and Context Managers track elapsed time.
    4. Synchronous Exit      → Threads are locked and data is aggregated on shutdown.
    5. NumPy Math            → Calculates P99, Max, and Avg execution times.

Lock-Free Buffering (Thread Safety)
-----------------------------------

``src/profiler.py`` - Thread Isolation

Purpose: Prevent standard Python locks from freezing the Pygame render thread while background tasks report metrics.

.. code-block:: python

    self.thread_buffers: Dict[int, ThreadSampleBuffer] = {}

* **Thread Mapping:** The global profiler maps the specific OS thread ID (via ``threading.get_ident()``) to an isolated ``ThreadSampleBuffer`` class.

.. code-block:: python

    self.categories[category] = deque(maxlen=self.max_samples)

* **Bounded Memory:** Each category (e.g., "Chunk_BuildMesh") creates a ``collections.deque``. By enforcing a strict ``maxlen`` (default 10,000), Pyrite ensures the profiler cannot infinitely leak RAM during extended play sessions.

.. code-block:: python

    self.categories[category].append(elapsed_time)

* **Lock-Free Appends:** In CPython, the ``deque.append()`` operation is natively atomic. Because each thread owns its specific deque, we can append timing data thousands of times per second completely lock-free.

API Wrappers & Integration
--------------------------

``src/profiler.py`` - Execution Tracking

Purpose: Provide clean, un-intrusive syntax for measuring engine subsystems.

.. code-block:: python

    @global_profiler.profile_func('World_Update')
    def update(self) -> None:

* **Decorator Syntax:** Almost all primary class methods (like those in ``chunk.py`` or ``player.py``) utilize the ``@profile_func()`` decorator. It automatically intercepts the function call, starts a timer, executes the underlying logic, and records the duration under the specified string.

.. code-block:: python

    with global_profiler.measure('Frustum_Culling'):
        frustum_cull_fast(...)

* **Context Manager:** For granular profiling inside massive functions (like isolating the Numba array culler inside the broader ``World_Render`` loop), the ``measure()`` context manager is used.

.. code-block:: python

    global_profiler.start_frame()
    self.update()
    self.render()
    global_profiler.end_frame()

* **Frame Timing:** The ``run()`` loop inside ``main.py`` explicitly wraps the update/render cycle with ``start_frame`` and ``end_frame`` to track the absolute macro performance of the engine, filed under the ``Frame_Total`` category.

Aggregation and Reporting
-------------------------

``src/profiler.py`` - Data Compilation

Purpose: Safely merge the isolated thread data into a readable format on application exit.

.. code-block:: python

    global_profiler.save_report('profiling_results.json')

* **Synchronous Trigger:** Called at the very end of the engine shutdown sequence. Because the game is already closing, blocking the main thread to process data is entirely acceptable.

.. code-block:: python

    with self.registry_lock:
        for thread_id, buf in self.thread_buffers.items():
            master_records[category].extend(list(samples))

* **Data Consolidation:** The engine securely locks the registry and iterates through every active and dead background worker pool thread, copying out their localized sample deques into a massive flat ``master_records`` dictionary.

.. code-block:: python

    arr = np.array(times, dtype=np.float64) * 1000.0

* **Unit Conversion:** Time arrays are converted to NumPy float64 types and multiplied by 1,000 to output milliseconds (ms).

.. code-block:: python

    'Avg_ms': round(float(np.mean(arr)), 3)
    'Max_ms': round(float(np.max(arr)), 3)
    'P99_ms': round(float(np.percentile(arr, 99)), 3)

* **Numpy Telemetry Math:**
    * **Avg_ms:** The standard mean execution time.
    * **Max_ms:** The absolute longest a single call took (usually indicating an initial cold-boot compile or DB load).
    * **P99_ms:** The 99th Percentile. This is the most crucial engine metric. It isolates the worst 1% of execution times. If your average frame is 16ms (60 FPS), but your P99 is 150ms, it indicates the game is experiencing severe, localized micro-stutters during heavy loads!

.. _profiling:

Profiling & Performance Diagnostics
===================================

This document describes how to use Pyrite's profiling and telemetry tools to find performance hotspots and interpret runtime metrics.

Overview
--------

Pyrite includes a lightweight, lock-free profiler designed to collect per-frame timing information with minimal impact on the main thread. Heavy subsystems (Numba-compiled functions) are already optimized; profiling helps locate remaining Python-level bottlenecks and I/O stalls.

Primary implementation
----------------------

- `src/profiler.py` — profiler implementation and API.
- Generated API docs (`docs/_build` / Sphinx) include function/class references for the profiler.

How to enable
-------------

1. The profiler is typically instantiated at application startup (see `src/main.py`).
2. If disabled by default, enable it by setting the config flag in `config.json` or by constructing `Profiler(enabled=True)` in the initialization code.

Basic usage
-----------

Typical patterns:

- Context timing:

  .. code-block:: python

      from profiler import Profiler
      profiler = Profiler()

      with profiler.measure('mesh_build'):
          build_chunk_mesh(...)

- Manual marks:

  .. code-block:: python

      profiler.start('frame')
      # ... frame work ...
      profiler.end('frame')

Exporting reports
-----------------

- The profiler can export JSON or CSV traces for offline analysis. Use the profiler API to call `profiler.export_json(path)` at program end or on demand.
- Report fields typically include: timestamp, category, elapsed_ms, thread_id, and optional metadata.

Interpreting results
--------------------

- Look for long-running categories that appear every frame (e.g., >2 ms on a 60 FPS budget).
- Check background thread I/O bursts (DB writes) that may cause occasional frame stalls if not fully async.
- For CPU hotspots in Python code, consider moving the logic into Numba-compiled functions or batching work into background threads.

Best practices
--------------

- Profile at real-world settings (render distance, active entities) to capture realistic behaviour.
- Use repeated runs to distinguish outlier spikes from consistent hotspots.
- Combine profiler traces with a sampling profiler (e.g., py-spy) for native-level insights.

See also
--------

- `docs/architecture.rst` (discussion of async queues and Numba offloading)
- `src/profiler.py` (API and internals)

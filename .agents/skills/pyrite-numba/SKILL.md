---
name: pyrite-numba
description: Strict guidelines for writing and optimizing Numba JIT functions in Pyrite.
---

# Pyrite Numba & Optimization

Pyrite relies heavily on Numba to achieve C-like performance in Python. When modifying engine core loops (like terrain generation or lighting), follow these rules:

## 1. The Numba Decorator
Always use the following signature for critical inner loops:
`@njit(cache=True, nogil=True)`
- **nogil=True:** Absolutely mandatory. This allows Pyrite's `ThreadPoolExecutor` to achieve true multithreading across CPU cores. Without it, the background workers will choke the main thread.
- **cache=True:** Mandatory to prevent massive compilation delays on every startup.

## 2. 64-bit Integer Packing
To optimize memory and cache locality during BFS algorithms (like lighting), Pyrite packs spatial data.
- Do not use classes or nested tuples inside Numba loops.
- Pack `(x, y, z, data)` into a single `uint64`.
- Example: `(x & 0xFF) << 56 | (y & 0xFF) << 48 | (z & 0xFF) << 40 | (light_level & 0x0F)`

## 3. Thread Safety
Numba background workers MUST NOT touch OpenGL state.
- All results from a Numba function must be purely mathematical/data-driven.
- Pass the resulting numpy arrays back to the main thread via `mesh_queue` or `load_queue`.
- See `docs/ARCHITECTURE.md` for the exact thread boundary flowchart.

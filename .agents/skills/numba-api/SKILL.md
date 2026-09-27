---
name: numba-api
description: API reference for numba 0.61.2
---

# Numba 0.61.2 API Reference

This document provides the exact, verified API specification for **Numba 0.61.2** (`numba`), covering core decorators, threading controls, compilation caching, dispatcher introspection, and the complete type system (`numba.types`).

---

## 1. Core Compilation Decorators

### 1.1 `@numba.jit`

```python
numba.jit(
    signature_or_function=None,
    locals={},
    cache=False,
    pipeline_class=None,
    boundscheck=None,
    **options
) -> Callable | Dispatcher
```

Compiles a Python function into native machine code using the LLVM compiler infrastructure. Can be used with or without explicit type signatures, and as a bare decorator `@jit` or parameterized decorator `@jit(...)`.

#### Parameters:
- `signature_or_function` (`str | Signature | list[str | Signature] | Callable | None`):
  - If a function is passed (e.g. `@jit`), returns a lazy `Dispatcher` that compiles on first call based on argument types.
  - If a single signature string or object is passed (e.g. `"int32(int32, int32)"`), eagerly compiles that specific signature.
  - If a list of signatures is passed, compiles overloads for each specified signature.
- `locals` (`dict[str, Type]`): Mapping of local variable names to Numba types, overriding type inference for specific local variables inside the function body.
- `cache` (`bool`, default `False`): If `True`, enables file-based compilation caching to disk (`.nbi` index and `.nbc` code files), avoiding re-compilation on subsequent runs.
- `pipeline_class` (`type[CompilerBase] | None`, default `None`): Custom compiler pipeline class subclassing `numba.core.compiler.CompilerBase` to customize compilation stages.
- `boundscheck` (`bool | None`, default `None`): If `True`, array index bounds checking is enabled (raises `IndexError` on out-of-bounds access). If `False`, bounds checking is omitted for speed. If `None`, defaults to `False` unless `debug=True` or `NUMBA_BOUNDSCHECK=1`.

#### CPU Target Options (`**options`):
- `nopython` (`bool`, default `False`): If `True`, operates in *nopython mode* (pure native code without Python C-API calls or fallback to object mode). If native compilation fails, raises `TypingError`. If `False`, allows object mode and loop-lifting.
- `nogil` (`bool`, default `False`): If `True`, releases the Python Global Interpreter Lock (GIL) upon entering the compiled function and re-acquires it upon exit. Requires `nopython=True`.
- `parallel` (`bool`, default `False`): If `True`, enables Numba's automatic parallelization transformation for array operations, reductions, and `prange` loops. Requires `nopython=True`.
- `fastmath` (`bool | dict | set`, default `False`): If `True`, enables LLVM fast-math optimizations relaxing IEEE 754 compliance (enables `nnan`, `ninf`, `nsz`, `arcp`, `contract`, `afn`, `reassoc`). Can also be a set/dict of individual optimization flags.
- `error_model` (`str`, default `'python'`): Floating-point division-by-zero behavior:
  - `'python'`: Raises `ZeroDivisionError`.
  - `'numpy'`: Returns `+/-inf` or `nan` without raising exceptions.
- `inline` (`str | Callable`, default `'never'`): Inlining policy at Numba IR level:
  - `'never'`: Never inline.
  - `'always'`: Always inline into calling Numba functions.
  - `Callable`: Custom heuristic function `(caller_ir, callee_ir) -> bool`.
- `forceinline` (`bool`, default `False`): Forces inlining at LLVM level.
- `looplift` (`bool`, default `True`): In object mode (`nopython=False`), extracts loops into standalone nopython-compiled functions while keeping outer code in object mode.
- `forceobj` (`bool`, default `False`): Forces compilation in object mode (PyObject manipulation), disabling nopython mode attempts.
- `debug` (`bool`, default `False`): Emits DWARF debugging information and enables bounds checking if `boundscheck=None`.
- `writable_args` (`tuple[int, ...]`, optional): Tuple of argument indices marked as writable.
- `no_rewrites` (`bool`, default `False`): Disables Numba IR rewrite passes.
- `no_cpython_wrapper` (`bool`, default `False`): Skips generating CPython calling wrappers.
- `no_cfunc_wrapper` (`bool`, default `False`): Skips generating C-level function wrappers.

---

### 1.2 `@numba.njit`

```python
numba.njit(*args, **kws) -> Callable | Dispatcher
```

Convenience alias strictly equivalent to `numba.jit(*args, nopython=True, **kws)`. All arguments and options accepted by `jit` (except `nopython` which is permanently `True`) are valid.

#### Recommended Engine Pattern:
```python
import numba

@numba.njit(cache=True, nogil=True)
def compute_mesh(voxels, width, height, length):
    # Pure native C-speed execution, multi-threaded capable, persistent disk caching
    ...
```

---

### 1.3 `@numba.vectorize`

```python
numba.vectorize(
    ftylist_or_function=(),
    target='cpu',
    identity=None,
    cache=False,
    **kws
) -> DUFunc | Callable
```

Compiles an element-wise scalar function into a NumPy Universal Function (`ufunc`).

#### Parameters:
- `ftylist_or_function`: Iterable of signatures (e.g. `["float32(float32, float32)", "float64(float64, float64)"]`) or the Python function itself for dynamic call-time compilation (`DUFunc`).
- `target` (`str`, default `'cpu'`): Execution target:
  - `'cpu'`: Single-threaded native CPU ufunc.
  - `'parallel'`: Multi-threaded CPU ufunc leveraging the configured threading layer.
  - `'cuda'`: CUDA GPU kernel ufunc (requires CUDA toolkit).
- `identity` (`int | float | str | None`, default `None`): Identity element for reductions (`.reduce()`):
  - `0`: Zero identity (addition/bitwise OR).
  - `1`: One identity (multiplication).
  - `"reorderable"`: Permits reordered reduction.
  - `None`: No identity (reduction requires non-empty array).
- `cache` (`bool`, default `False`): Enables compilation caching to disk.
- `**kws`: Additional compiler options (e.g. `fastmath=True`, `nopython=True`).

#### Example:
```python
import numpy as np
from numba import vectorize, float32, float64

@vectorize([float32(float32, float32), float64(float64, float64)], target='parallel', cache=True)
def fast_add(x, y):
    return x + y
```

---

### 1.4 `@numba.guvectorize`

```python
numba.guvectorize(
    ftylist,
    signature,
    target='cpu',
    identity=None,
    cache=False,
    writable_args=(),
    **kws
) -> Callable
```

Creates a NumPy Generalized Universal Function (`gufunc`), operating on sub-arrays of arbitrary dimensions rather than individual scalar elements.

#### Parameters:
- `ftylist` (`Iterable[str | Signature]`): List of signatures. In `guvectorize`, the function returns `void` and outputs are passed as trailing arguments (e.g. `['void(float32[:,:], float32[:,:], float32[:,:])']`).
- `signature` (`str`): Symbolic layout signature specifying array dimensions according to NumPy gufunc specification (e.g. `"(m,n),(n,p)->(m,p)"`).
- `target` (`str`, default `'cpu'`): `'cpu'`, `'parallel'`, or `'cuda'`.
- `identity` (`int | str | None`, default `None`): Reduction identity value.
- `cache` (`bool`, default `False`): Enables compilation caching.
- `writable_args` (`tuple[int, ...]`, default `()`): Indices of input arrays allowed to be mutated.
- `**kws`: Extra compiler flags (e.g. `fastmath=True`, `nopython=True`).

#### Example:
```python
from numba import guvectorize, float64

@guvectorize([(float64[:, :], float64[:, :], float64[:, :])], '(m,n),(n,p)->(m,p)', target='parallel')
def matmul_gufunc(A, B, C):
    m, n = A.shape
    p = B.shape[1]
    for i in range(m):
        for j in range(p):
            total = 0.0
            for k in range(n):
                total += A[i, k] * B[k, j]
            C[i, j] = total
```

---

### 1.5 `@generated_jit` Deprecation & Modern Replacement (`@overload`)

> [!WARNING]
> `numba.generated_jit` was **deprecated in Numba 0.59.0** and **completely removed** in modern Numba versions (including **0.61.2**). Calling `from numba import generated_jit` will raise an `ImportError`.

#### Modern Replacement: `numba.extending.overload`
To implement polymorphic dispatch based on argument types, use `@overload` from `numba.extending`.

```python
numba.extending.overload(
    func,
    jit_options={},
    strict=True,
    inline='never',
    prefer_literal=False,
    **kwargs
) -> Callable
```

#### Migration Pattern:
```python
# Old / Removed approach (numba <= 0.58):
# @generated_jit(nopython=True)
# def bar(x): ...

# Modern approach in Numba 0.61.2:
from numba import njit, types
from numba.extending import overload

def bar(x):
    """External Python function entry point."""
    raise NotImplementedError

@overload(bar, jit_options={'nogil': True, 'cache': True})
def overload_bar(x):
    if isinstance(x, types.Integer):
        def impl(x):
            return x * 2
        return impl
    elif isinstance(x, types.Float):
        def impl(x):
            return x * 0.5
        return impl
    else:
        raise TypeError(f"Unsupported type {x}")

@njit
def caller(v):
    return bar(v)
```

---

### 1.6 Additional Decorators

#### `@numba.cfunc`
Compiles a Python function into an unmanaged C callback function pointer usable with `ctypes`, C libraries, or external foreign function interfaces.
```python
numba.cfunc(sig, locals={}, cache=False, pipeline_class=None, **options) -> CFunc
```
- Example:
  ```python
  from numba import cfunc, types

  @cfunc("float64(float64, float64)", cache=True)
  def callback(a, b):
      return a + b

  # Access native function pointer
  c_ptr = callback.address
  ctypes_fn = callback.ctypes
  ```

#### `@numba.stencil`
Creates a fast neighborhood/stencil computation kernel.
```python
numba.stencil(func_or_mode='constant', **options) -> StencilFunc
```

#### `@numba.experimental.jitclass`
Compiles an entire Python class into native struct representation in memory with C-speed methods.
```python
numba.experimental.jitclass(spec)
```
- Example:
  ```python
  from numba import int32, float32
  from numba.experimental import jitclass

  spec = [
      ('x', int32),
      ('y', float32),
  ]

  @jitclass(spec)
  def Point:
      def __init__(self, x, y):
          self.x = x
          self.y = y
  ```

---

## 2. Threading Controls & Parallelism

### 2.1 `nogil=True`
Releases Python's Global Interpreter Lock (GIL) during function execution.
- **Mechanism**: The thread yields the GIL immediately upon entering native machine code and reacquires it when execution returns to Python.
- **Multithreading**: Allows external Python threading pools (e.g. `concurrent.futures.ThreadPoolExecutor`) to execute multiple Numba functions concurrently across separate OS threads without lock contention.
- **Safety**: Pure computation only. Do not invoke Python C-API calls or interact with OpenGL / windowing state from within a `nogil` function.

---

### 2.2 `parallel=True` & `numba.prange`

#### `parallel=True` Target Option
Activates the `ParallelAccelerator` optimization pass inside the Numba compiler pipeline:
1. Detects parallelizable array operations (`a + b`, `a * 2`).
2. Fuses adjacent loops into single parallel passes.
3. Automatically parallelizes explicit `numba.prange` loops.
4. Identifies parallel reduction variables (`sum += x[i]`).

#### `numba.prange(*args)`
```python
numba.prange([start,] stop[, step]) -> Iterable[int]
```
A parallel 1D iterator distributing loop iterations across the active worker thread pool.
- Inside `@njit(parallel=True)`: Iterations are partitioned across worker threads.
- Inside non-parallel code or regular Python: Operates identically to Python's built-in `range`.
- **Thread Safety**: Loop iterations must be independent. Writing to the same index across iterations causes race conditions. Supported associative reductions (`+=`, `*=`, `-=`, `&=`, `|=`, `^=`) are automatically protected with thread-local accumulators.

```python
import numba
import numpy as np

@numba.njit(parallel=True, nogil=True)
def parallel_sum(arr):
    acc = 0.0
    for i in numba.prange(arr.shape[0]):
        acc += arr[i]
    return acc
```

---

### 2.3 Threading Runtime Management APIs

```python
# Query active thread count used for parallel regions
numba.get_num_threads() -> int

# Set the active thread count (1 <= n <= NUMBA_NUM_THREADS)
# Can be called from standard Python or inside JIT-compiled functions
numba.set_num_threads(n: int) -> None

# Return name of active threading backend: 'tbb', 'omp', or 'workqueue'
numba.threading_layer() -> str

# Query or adjust chunk size for parallel loop partitioning
numba.get_parallel_chunksize() -> int
numba.set_parallel_chunksize(n: int) -> None
```

#### Threading Layers & Priority:
Numba selects the threading layer at startup according to `THREADING_LAYER_PRIORITY = ['tbb', 'omp', 'workqueue']`:
1. **`tbb`** (Intel Threading Building Blocks): Most scalable, thread-safe, composable with other TBB processes.
2. **`omp`** (OpenMP): High performance for numerical loops via GNU or Intel OpenMP runtime (caution: not fork-safe).
3. **`workqueue`**: Numba's built-in, lightweight thread pool. Zero external dependencies, safe fallback.

#### Threading Environment Variables:
- `NUMBA_NUM_THREADS`: Integer setting total worker threads spawned at launch (defaults to physical CPU core count).
- `NUMBA_THREADING_LAYER`: Selects backend (`'default'`, `'tbb'`, `'omp'`, `'workqueue'`).
- `NUMBA_PARALLEL_DIAGNOSTICS`: Set `1` to `4` to print parallel transformation diagnostics during compilation.

#### Programmatic Parallel Diagnostics:
```python
# Inspect loop parallelization and fusion report on a compiled Dispatcher
parallel_sum.parallel_diagnostics(signature=None, level=1)
```

---

## 3. Compilation Caching

### 3.1 Cache Operation (`cache=True`)
When `cache=True` is enabled on `@jit`, `@njit`, `@vectorize`, or `@cfunc`, Numba persists compiled machine code and LLVM bitcode to disk to bypass compilation overhead on future application runs.

#### Generated Cache Files:
- **Index File (`.nbi`)**: `<module>.<function>-<line>.py<version><abi>.nbi`
  Contains metadata, timestamp, file size, AST hashes, signatures, target CPU architecture flags, and pointers to data files.
- **Data File (`.nbc`)**: `<module>.<function>-<line>.py<version><abi>.<id>.nbc`
  Contains serialized LLVM bitcode, relocation data, and native object code.

---

### 3.2 Cache Directory Resolution Hierarchy
Numba determines cache file locations using a tiered search:
1. **`NUMBA_CACHE_DIR` / `numba.config.CACHE_DIR`**: If set, all cache files are directed here.
2. **In-Tree `__pycache__`**: If the source code directory is writable, saves into `__pycache__/` directly alongside the Python file.
3. **User-Wide Application Cache**: If source directory is read-only (e.g. system site-packages), falls back to:
   - Windows: `%LOCALAPPDATA%\numba\Cache`
   - Linux: `~/.cache/numba`
   - macOS: `~/Library/Caches/numba`

---

### 3.3 Cache Invalidation Criteria
A cache entry is invalidated and recompiled when any of the following change:
- Source file modification timestamp (`mtime`) or file size.
- Function bytecode or abstract syntax tree.
- Python major or minor version (e.g. `py311` vs `py312` vs `py313`).
- Target CPU architecture or vector extension flags (e.g. running on CPU without AVX2).
- Function argument or return types.

#### Caching Limitations & Constraints:
- **Global Variables**: Values of globals captured at compile time are baked into native code. Changes to global state across executions will NOT invalidate the cache automatically.
- **Closures**: Functions capturing outer non-primitive objects cannot be cached.
- **File Requirement**: Functions must reside in an inspectable `.py` file on disk. Functions generated dynamically in REPL or `eval` cannot use in-tree caching.

---

## 4. Type System (`numba.types` & Top-Level Types)

All primitive types are accessible directly from `numba` or `numba.types`.

### 4.1 Scalar Types

| Type Name | Bit Width | Description | Numba Aliases |
| :--- | :--- | :--- | :--- |
| `boolean` | 8-bit | Boolean `True` or `False` | `bool_`, `bool` |
| `int8` | 8-bit | Signed 8-bit integer | `char` |
| `int16` | 16-bit | Signed 16-bit integer | `short` |
| `int32` | 32-bit | Signed 32-bit integer | `intc` |
| `int64` | 64-bit | Signed 64-bit integer | `int_`, `intp`, `long_`, `longlong` |
| `uint8` | 8-bit | Unsigned 8-bit integer | `uchar` |
| `uint16` | 16-bit | Unsigned 16-bit integer | `ushort` |
| `uint32` | 32-bit | Unsigned 32-bit integer | `uintc` |
| `uint64` | 64-bit | Unsigned 64-bit integer | `uint`, `uintp`, `ulong`, `ulonglong` |
| `float16` | 16-bit | Half-precision float | - |
| `float32` | 32-bit | Single-precision float | - |
| `float64` | 64-bit | Double-precision float | `float_`, `double` |
| `complex64` | 64-bit | Complex with two 32-bit floats | - |
| `complex128` | 128-bit | Complex with two 64-bit floats | - |
| `void` / `none` | 0-bit | No return value (`None`) | `NoneType` |
| `unicode_type` | Variable | Python UTF-8 unicode string | - |

---

### 4.2 Array Types (`numba.types.Array`)

```python
numba.types.Array(
    dtype: Type,
    ndim: int,
    layout: str,
    readonly: bool = False,
    name: str | None = None,
    aligned: bool = True
) -> Array
```

#### Layout Specifiers:
- `'C'`: C-contiguous (row-major). Fast row iteration.
- `'F'`: Fortran-contiguous (column-major). Fast column iteration.
- `'A'`: Any layout / arbitrary striding.

#### Array Slice Syntax Notation:
Numba types support Python slice subscription syntax to define arrays concisely:
```python
from numba import int32, float64

# 1D array, arbitrary layout ('A')
arr_1d = int32[:]

# 1D array, contiguous ('C')
arr_1d_c = int32[::1]

# 2D array, arbitrary layout ('A')
arr_2d = float64[:, :]

# 2D array, C-contiguous row-major ('C')
arr_2d_c = float64[:, ::1]

# 2D array, Fortran-contiguous column-major ('F')
arr_2d_f = float64[::1, :]

# 3D array, C-contiguous
arr_3d_c = int32[:, :, ::1]
```

---

### 4.3 Container Types

#### Tuples:
- Heterogeneous Tuple: `numba.types.Tuple((types.int32, types.float64))`
- Homogeneous UniTuple: `numba.types.UniTuple(dtype=types.int32, count=3)` (e.g. 3D integer coordinates)

#### Typed Containers (`numba.typed`):
High-performance native mutable containers usable inside and outside JIT functions:

```python
from numba.typed import List, Dict
from numba import types

# 1. Typed List:
my_list = List.empty_list(types.int64, allocated=16)
my_list.append(42)

# 2. Typed Dict:
my_dict = Dict.empty(
    key_type=types.unicode_type,
    value_type=types.int64,
    n_keys=32
)
my_dict["score"] = 100
```

#### Structured Records (`numba.types.Record`):
Represents NumPy structured arrays with named fields:
```python
from numba import types
import numpy as np

dtype = np.dtype([('pos', np.float32, (3,)), ('color', np.uint32)])
record_type = types.Record.from_struct_dtype(dtype)
```

---

### 4.4 Type Modifiers & Helpers

- **`types.Optional(underlying_type)`**: Represents a value that can be either the given type or `None`.
- **`types.literal(value)`**: Constructs a compile-time constant literal type (e.g. `types.literal("C")`).
- **`numba.typeof(val)`**: Returns the inferred Numba type for any Python runtime value.
- **`numba.from_dtype(np_dtype)`**: Converts a NumPy `dtype` instance into its equivalent Numba type.
- **`types.as_numba_type(py_type)`**: Translates a standard Python type (`int`, `float`, `tuple`) to a Numba type.

---

## 5. Compiled Dispatcher Inspection API

Functions decorated with `@jit` or `@njit` return a `Dispatcher` instance providing low-level compilation inspection methods:

```python
dispatcher = my_jitted_func

# Return dict of compiled signatures mapped to LLVM IR string
dispatcher.inspect_llvm(signature=None) -> dict[Signature, str]

# Return dict of compiled signatures mapped to native assembly string
dispatcher.inspect_asm(signature=None) -> dict[Signature, str]

# Print annotated type deduction report for each line of Python source
dispatcher.inspect_types(file=None, pretty=False) -> None

# Return dict of control flow graphs for each signature
dispatcher.inspect_cfg(signature=None) -> dict[Signature, CFG]

# Tuple of all compiled signatures
dispatcher.signatures -> list[Signature]

# Tuple of all nopython-compiled signatures
dispatcher.nopython_signatures -> list[Signature]

# Access underlying uncompiled Python function
dispatcher.py_func -> Callable

# Recompile the dispatcher, clearing caches
dispatcher.recompile() -> None
```

---

## 6. Pyrite Engine Numba Conventions

When authoring or modifying performance-critical loops in Pyrite:
1. **Always release the GIL**: `@njit(cache=True, nogil=True)` is mandatory for background worker pipelines.
2. **Bit-Packing Over Structs**: Use `uint64` integer packing for spatial 3D coordinates and lighting BFS propagation instead of objects or tuples to maximize cache locality and minimize memory allocations.
3. **Array Arguments**: Explicitly specify C-contiguous arrays using `[::1]` or `[:, ::1]` in signatures where known to assist LLVM autovectorization.
4. **OpenGL Boundary**: Never call OpenGL or Pygame functions inside Numba code; populate numpy buffers and pass them back via queue to the main thread.

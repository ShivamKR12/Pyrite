---
name: numpy-api
description: API reference for numpy 2.2.6
---

# NumPy 2.2.6 API Reference

This document provides the exact, verified API specification for **NumPy 2.2.6** (`numpy`), tailored for high-performance 3D voxel game engines (such as Pyrite), Numba JIT kernels, ModernGL buffer uploads, chunk generation, and spatial math. All signatures, parameter types, defaults, and return values reflect the tested NumPy 2.2.6 runtime.

---

## 1. NumPy 2.2.6 Runtime Specification & Voxel Context

### Key NumPy 2.x Architecture Highlights
- **NumPy 2.0+ `copy` Semantics**: In `np.array(..., copy=True)` the default is `True`. In `np.asarray(..., copy=None)`, `copy=None` means "copy only if needed". `copy=False` will raise a `ValueError` if a copy cannot be avoided.
- **Array API Standard Alignment**: Standardized keywords like `device=None` have been introduced across creation routines (`ones`, `empty`, `full`, `arange`, `linspace`, etc.).
- **New Vector-Matrix Routines**: NumPy 2.2 introduces `np.matvec` and `np.vecmat` for matrix-vector and vector-matrix products across batches.
- **Removal of Deprecated Type Aliases**: Old aliases such as `np.int_`, `np.float_`, `np.bool8` are removed or deprecated; explicit standard types (`np.int32`, `np.int64`, `np.float32`, `np.float64`, `np.uint8`, `np.uint16`, `np.uint32`, `np.uint64`, `np.bool_`) must be used.
- **Zero-Element Truthiness**: Evaluating boolean truthiness on empty arrays (e.g., `bool(np.array([]))`) strictly raises `ValueError`. Always use `arr.size > 0`.

### Voxel Engine Context in Pyrite
- **Chunk Geometry**: 3D voxel density arrays typically sized `(16, 256, 16)` or `(32, 32, 32)` stored in C-contiguous order.
- **Linear Indexing**: `index = x + z * CHUNK_X + y * (CHUNK_X * CHUNK_Z)` to match Numba 1D flat access.
- **Bit-Packed Voxel Data**: 64-bit integer packing (`np.uint64`) or 32-bit integer packing (`np.uint32`) encoding voxel ID, light values (sunlight + torchlight), face normal indices, and ambient occlusion levels.
- **Graphics Pipeline Integration**: Vertex data arrays are packed into contiguous numpy arrays and converted via `arr.tobytes()` or directly uploaded to ModernGL buffers (`ctx.buffer(arr)`).

---

## 2. Core Data Types (`np.dtype`)

NumPy provides explicit fixed-width scalar dtypes used across chunk storage and GPU vertex attributes.

### Fixed-Width Integer Types
| Type | Byte Size | Description | Typical Engine Use Case |
| :--- | :--- | :--- | :--- |
| `np.uint8` | 1 byte | Unsigned 8-bit integer (0 to 255) | Face index, AO level (0-3), light levels (0-15), block palette IDs |
| `np.uint16` | 2 bytes | Unsigned 16-bit integer (0 to 65,535) | Extended block IDs, packed light masks, index buffers (EBO) |
| `np.uint32` | 4 bytes | Unsigned 32-bit integer (0 to 4,294,967,295) | Packed vertex attributes, large EBOs, random seeds |
| `np.uint64` | 8 bytes | Unsigned 64-bit integer | Pyrite 64-bit packed vertex format (`src/lighting.py`) |
| `np.int8` | 1 byte | Signed 8-bit integer (-128 to 127) | Neighbor chunk offset deltas, signed normal components |
| `np.int16` | 2 bytes | Signed 16-bit integer (-32,768 to 32,767) | Chunk coordinate offsets, heightmap offsets |
| `np.int32` | 4 bytes | Signed 32-bit integer | World voxel coordinates (X, Y, Z), chunk grid coordinates |
| `np.int64` | 8 bytes | Signed 64-bit integer | Global entity IDs, cycle tick counters |

### Floating-Point & Boolean Types
| Type | Byte Size | Description | Typical Engine Use Case |
| :--- | :--- | :--- | :--- |
| `np.float16` | 2 bytes | Half-precision float | Compressed GPU texture data, low-precision UVs |
| `np.float32` | 4 bytes | Single-precision float | Vertex positions, UV texture coordinates, ModernGL uniform data |
| `np.float64` | 8 bytes | Double-precision float | High-precision player coordinates, noise generator math |
| `np.bool_` | 1 byte | Boolean (`True` or `False`) | Voxel occlusion masks, chunk dirty flags |

### Structured Data Types (Vertex Formats)
Used to construct structured arrays for zero-copy vertex buffer layouts:
```python
vertex_dtype = np.dtype([
    ('position', np.float32, 3),   # 3x float32 (12 bytes)
    ('uv',       np.float32, 2),   # 2x float32 (8 bytes)
    ('normal',   np.int8,    4),   # 4x int8 (4 bytes)
    ('lighting', np.uint8,   2),   # 2x uint8 (2 bytes)
])
```

---

## 3. Class `ndarray` & Memory Layout

```python
class numpy.ndarray(shape, dtype=float, buffer=None, offset=0, strides=None, order=None)
```

### Essential Attributes
- **`arr.shape: tuple[int, ...]`**: Dimensions of the array (e.g., `(16, 256, 16)`).
- **`arr.dtype: np.dtype`**: Data type of the elements.
- **`arr.strides: tuple[int, ...]`**: Bytes to step in each dimension when traversing the array.
- **`arr.ndim: int`**: Number of array dimensions (`len(arr.shape)`).
- **`arr.size: int`**: Total number of elements in the array (`prod(arr.shape)`).
- **`arr.itemsize: int`**: Length of one array element in bytes.
- **`arr.nbytes: int`**: Total bytes consumed by elements (`arr.size * arr.itemsize`).
- **`arr.data: memoryview`**: Python buffer pointing to the start of array data.
- **`arr.flags: flagsobj`**: Memory information object:
  - `flags.c_contiguous` (`C`): True if data is in a single C-style contiguous segment.
  - `flags.f_contiguous` (`F`): True if data is in a Fortran-style contiguous segment.
  - `flags.writeable` (`W`): True if array data can be modified.
  - `flags.owndata` (`OWNDATA`): True if array owns memory (not a view from another array).
  - `flags.aligned` (`ALIGNED`): True if data is aligned for hardware access.

### Essential Methods
- **`arr.astype(dtype, order='K', casting='unsafe', subok=True, copy=True) -> ndarray`**: Cast elements to specified dtype.
- **`arr.tobytes(order='C') -> bytes`**: Construct Python bytes containing raw array memory. Essential for uploading data to ModernGL buffers (`ctx.buffer(arr.tobytes())`).
- **`arr.view([dtype][, type]) -> ndarray`**: Zero-copy new view of array with same data buffer, optionally with different dtype.
- **`arr.fill(value) -> None`**: In-place fill array with a scalar value.
- **`arr.copy(order='C') -> ndarray`**: Return a contiguous copy of the array.
- **`arr.reshape(shape, /, *, order='C', copy=None) -> ndarray`**: Returns array with new shape without changing data.
- **`arr.flatten(order='C') -> ndarray`**: Return a 1D copy of the array.
- **`arr.ravel(order='C') -> ndarray`**: Return a contiguous 1D flattened array (view if possible, copy only if necessary).
- **`arr.transpose(*axes) -> ndarray`**: Returns a view with axes permuted.
- **`arr.nonzero() -> tuple[ndarray, ...]`**: Return tuple of arrays containing indices of non-zero elements.

---

## 4. Array Creation Functions

### `np.array(object, dtype=None, *, copy=True, order='K', subok=False, ndmin=0, like=None) -> ndarray`
> Creates an array from an existing sequence, buffer, or array-like object.
- **Parameters:**
  - `object` (`array_like`): Input data (list, tuple, buffer, or existing array).
  - `dtype` (`dtype_like`, optional): Desired data-type. If `None`, inferred from data.
  - `copy` (`bool`, optional): In NumPy 2.x, default is `True`. Set `copy=False` only if avoiding copies when possible.
  - `order` (`{'K', 'A', 'C', 'F'}`, optional): Memory layout. Default `'K'` preserves existing layout.
  - `subok` (`bool`, optional): If `True`, subclasses are passed through; otherwise returned as base `ndarray`.
  - `ndmin` (`int`, optional): Minimum number of dimensions in result.
  - `like` (`array_like`, optional): Reference object for NEP 35 array creation.
- **Returns:** `ndarray`

### `np.zeros(shape, dtype=float, order='C', *, like=None) -> ndarray`
> Returns a new array of given shape and type, filled with zeros.
- **Parameters:**
  - `shape` (`int | tuple[int, ...]`): Shape of the new array (e.g., `(16, 256, 16)`).
  - `dtype` (`dtype_like`, optional): Desired data-type (default `float64`). For voxel grids, typically `np.uint8` or `np.uint32`.
  - `order` (`{'C', 'F'}`, optional): Memory layout. Default `'C'` (row-major).
  - `like` (`array_like`, optional): Reference array.
- **Returns:** `ndarray`

### `np.ones(shape, dtype=None, order='C', *, device=None, like=None) -> ndarray`
> Returns a new array of given shape and type, filled with ones.
- **Parameters:**
  - `shape` (`int | tuple[int, ...]`): Shape of the new array.
  - `dtype` (`dtype_like`, optional): Desired data-type (default `float64`).
  - `order` (`{'C', 'F'}`, optional): Memory layout. Default `'C'`.
  - `device` (`str`, optional): Target device (standard Array API parameter). Default `None`.
- **Returns:** `ndarray`

### `np.empty(shape, dtype=float, order='C', *, device=None, like=None) -> ndarray`
> Returns a new uninitialized array of given shape and type. Fastest allocation for arrays that will be immediately populated (e.g., mesh vertex caches).
- **Parameters:**
  - `shape` (`int | tuple[int, ...]`): Shape of the new array.
  - `dtype` (`dtype_like`, optional): Desired data-type (default `float64`).
  - `order` (`{'C', 'F'}`, optional): Memory layout. Default `'C'`.
  - `device` (`str`, optional): Target device. Default `None`.
- **Returns:** `ndarray`

### `np.full(shape, fill_value, dtype=None, order='C', *, device=None, like=None) -> ndarray`
> Returns a new array of given shape and type, filled with `fill_value`.
- **Parameters:**
  - `shape` (`int | tuple[int, ...]`): Shape of the new array.
  - `fill_value` (`scalar`): Fill value.
  - `dtype` (`dtype_like`, optional): Desired data-type.
  - `order` (`{'C', 'F'}`, optional): Memory layout. Default `'C'`.
  - `device` (`str`, optional): Target device. Default `None`.
- **Returns:** `ndarray`

### `np.zeros_like(a, dtype=None, order='K', subok=True, shape=None, *, device=None) -> ndarray`
> Returns an array of zeros with the same shape and type as a given prototype array `a`.
- **Parameters:**
  - `a` (`array_like`): Prototype array.
  - `dtype` (`dtype_like`, optional): Overrides data-type.
  - `order` (`{'C', 'F', 'A', 'K'}`, optional): Overrides memory layout.
  - `shape` (`int | tuple[int, ...]`, optional): Overrides shape.
  - `device` (`str`, optional): Target device.
- **Returns:** `ndarray`

### `np.ones_like(a, dtype=None, order='K', subok=True, shape=None, *, device=None) -> ndarray`
> Returns an array of ones with the same shape and type as a given prototype array `a`.

### `np.empty_like(prototype, dtype=None, order='K', subok=True, shape=None, *, device=None) -> ndarray`
> Returns a new uninitialized array with the same shape and type as `prototype`.

### `np.full_like(a, fill_value, dtype=None, order='K', subok=True, shape=None, *, device=None) -> ndarray`
> Returns a full array with the same shape and type as `a`, filled with `fill_value`.

### `np.arange([start,] stop[, step,], dtype=None, *, device=None, like=None) -> ndarray`
> Returns evenly spaced values within a given interval `[start, stop)` with spacing `step`.
- **Parameters:**
  - `start` (`number`, optional): Start of interval (default 0).
  - `stop` (`number`): End of interval.
  - `step` (`number`, optional): Spacing between values (default 1).
  - `dtype` (`dtype_like`, optional): Type of output array.
  - `device` (`str`, optional): Target device.
- **Returns:** `ndarray`

### `np.linspace(start, stop, num=50, endpoint=True, retstep=False, dtype=None, axis=0, *, device=None) -> ndarray | tuple[ndarray, float]`
> Returns `num` evenly spaced samples calculated over the interval `[start, stop]`. Useful for sampling noise maps, LOD blending, and gradient generation.
- **Parameters:**
  - `start` (`array_like`): Starting value.
  - `stop` (`array_like`): Ending value.
  - `num` (`int`, optional): Number of samples to generate (default 50).
  - `endpoint` (`bool`, optional): If `True`, `stop` is the last sample.
  - `retstep` (`bool`, optional): If `True`, return `(samples, step)`.
  - `dtype` (`dtype_like`, optional): Type of output.
  - `axis` (`int`, optional): Axis along which samples are stored.
  - `device` (`str`, optional): Target device.
- **Returns:** `ndarray` (or `tuple[ndarray, float]` if `retstep=True`).

### `np.frombuffer(buffer, dtype=float, count=-1, offset=0, *, like=None) -> ndarray`
> Interprets an existing Python buffer (bytes, bytearray, memoryview) as a 1-dimensional array without copying memory.
- **Parameters:**
  - `buffer` (`buffer_like`): Buffer object exposing buffer interface.
  - `dtype` (`dtype_like`, optional): Data-type of returned array (default `float64`).
  - `count` (`int`, optional): Number of items to read. `-1` reads all data.
  - `offset` (`int`, optional): Start reading buffer from this offset in bytes (default 0).
- **Returns:** `ndarray` (1D view).

### `np.asarray(a, dtype=None, order=None, *, device=None, copy=None, like=None) -> ndarray`
> Converts input to an `ndarray`. Unlike `np.array`, does not copy if input is already an `ndarray` matching `dtype` and `order`.
- **Parameters:**
  - `a` (`array_like`): Input data.
  - `dtype` (`dtype_like`, optional): Target data-type.
  - `order` (`{'C', 'F', 'A', 'K'}`, optional): Memory layout.
  - `copy` (`bool | None`, optional): In NumPy 2.x:
    - `copy=None` (default): Copy only if needed.
    - `copy=True`: Always copy.
    - `copy=False`: Never copy (raises `ValueError` if a copy is required).
  - `device` (`str`, optional): Target device.
- **Returns:** `ndarray`

### `np.ascontiguousarray(a, dtype=None, *, like=None) -> ndarray`
> Returns a C-contiguous array in memory (`C_CONTIGUOUS = True`). **Crucial** before passing arrays to Numba `@njit` kernels or ModernGL buffer writes.
- **Parameters:**
  - `a` (`array_like`): Input array.
  - `dtype` (`dtype_like`, optional): Target data-type.
- **Returns:** `ndarray` (contiguous view or newly allocated copy).

### `np.copy(a, order='K', subok=False) -> ndarray`
> Returns an array copy of the given object.
- **Parameters:**
  - `a` (`array_like`): Input array.
  - `order` (`{'C', 'F', 'A', 'K'}`, optional): Memory layout (default `'K'`).
  - `subok` (`bool`, optional): Pass through subclasses if `True`.
- **Returns:** `ndarray`

---

## 5. Shape Manipulation, Reshaping & Joining

### `np.reshape(a, /, shape=None, order='C', *, newshape=None, copy=None) -> ndarray`
> Gives a new shape to an array without changing its data.
- **Parameters:**
  - `a` (`array_like`): Array to be reshaped.
  - `shape` (`int | tuple[int, ...]`, optional): New shape (e.g. `(16, 256, 16)`). Can contain one dimension as `-1` to infer length.
  - `order` (`{'C', 'F', 'A'}`, optional): Read elements using this index order (default `'C'`).
  - `copy` (`bool | None`, optional): In NumPy 2.x, controls whether to copy data.
- **Returns:** `ndarray`

### `np.ravel(a, order='C') -> ndarray`
> Returns a contiguous 1D flattened array.
- **Parameters:**
  - `a` (`array_like`): Input array.
  - `order` (`{'C', 'F', 'A', 'K'}`, optional): Flattening order (default `'C'`).
- **Returns:** `ndarray` (view when possible, copy otherwise).

### `np.transpose(a, axes=None) -> ndarray`
> Permutes the dimensions of an array.
- **Parameters:**
  - `a` (`array_like`): Input array.
  - `axes` (`tuple[int, ...]`, optional): Permutation of dimensions (default reverses axes).
- **Returns:** `ndarray` (view).

### `np.swapaxes(a, axis1, axis2) -> ndarray`
> Interchange two axes of an array.
- **Parameters:**
  - `a` (`array_like`): Input array.
  - `axis1` (`int`): First axis.
  - `axis2` (`int`): Second axis.
- **Returns:** `ndarray` (view).

### `np.expand_dims(a, axis) -> ndarray`
> Expands the shape of an array by inserting a new axis at position `axis`.
- **Parameters:**
  - `a` (`array_like`): Input array.
  - `axis` (`int | tuple[int, ...]`): Position in expanded axes where new axis is placed.
- **Returns:** `ndarray` (view).

### `np.squeeze(a, axis=None) -> ndarray`
> Removes single-dimensional entries (dimensions of size 1) from the shape of an array.
- **Parameters:**
  - `a` (`array_like`): Input array.
  - `axis` (`int | tuple[int, ...]`, optional): Specific subset of 1-sized axes to drop.
- **Returns:** `ndarray` (view).

### `np.concatenate((a1, a2, ...), axis=0, out=None, dtype=None, casting="same_kind") -> ndarray`
> Joins a sequence of arrays along an existing axis.
- **Parameters:**
  - `(a1, a2, ...)` (`sequence of array_like`): Arrays to join. Must match shapes except in `axis`.
  - `axis` (`int`, optional): Axis along which arrays will be joined (default 0).
  - `out` (`ndarray`, optional): Destination array.
  - `dtype` (`dtype_like`, optional): Resulting array dtype.
  - `casting` (`str`, optional): Casting rule (default `"same_kind"`).
- **Returns:** `ndarray`

### `np.stack(arrays, axis=0, out=None, *, dtype=None, casting='same_kind') -> ndarray`
> Joins a sequence of arrays along a **new** axis.
- **Parameters:**
  - `arrays` (`sequence of array_like`): Arrays to stack. All must have identical shapes.
  - `axis` (`int`, optional): Axis in the result array along which input arrays are stacked (default 0).
  - `out` (`ndarray`, optional): Destination array.
- **Returns:** `ndarray`

### `np.vstack(tup, *, dtype=None, casting='same_kind') -> ndarray`
> Stacks arrays in sequence vertically (row wise / along axis 0). Rebuilds 1D arrays of shape `(N,)` into `(1, N)`.
- **Parameters:**
  - `tup` (`sequence of array_like`): Arrays to stack.
- **Returns:** `ndarray`

### `np.hstack(tup, *, dtype=None, casting='same_kind') -> ndarray`
> Stacks arrays in sequence horizontally (column wise / along axis 1). Extensively used in Pyrite for concatenating vertex columns: `np.hstack((positions, texcoords, normals))`.
- **Parameters:**
  - `tup` (`sequence of array_like`): Arrays to stack.
- **Returns:** `ndarray`

### `np.dstack(tup) -> ndarray`
> Stacks arrays in sequence along the third axis (depth-wise).
- **Parameters:**
  - `tup` (`sequence of array_like`): Arrays to stack.
- **Returns:** `ndarray`

### `np.pad(array, pad_width, mode='constant', **kwargs) -> ndarray`
> Pads an array. Highly useful in voxel engines for generating 1-block neighbor borders around chunks to compute seamless ambient occlusion and lighting propagation across borders without chunk queries.
- **Parameters:**
  - `array` (`array_like`): Input array.
  - `pad_width` (`int | sequence[tuple[int, int]]`): Number of values padded to edges of each axis.
  - `mode` (`str`, optional): Padding method (`'constant'`, `'edge'`, `'reflect'`). Default `'constant'`.
  - `constant_values` (scalar, optional): Value to set padding to (default 0).
- **Returns:** `ndarray`

### `np.split(ary, indices_or_sections, axis=0) -> list[ndarray]`
> Splits an array into multiple sub-arrays along `axis`.
- **Parameters:**
  - `ary` (`ndarray`): Array to split.
  - `indices_or_sections` (`int | 1D array_like`): If integer $N$, splits into $N$ equal sections. If 1D list, indicates split slice indices.
  - `axis` (`int`, optional): Axis to split along (default 0).
- **Returns:** `list[ndarray]`

### `np.tile(A, reps) -> ndarray`
> Constructs an array by repeating `A` the number of times given by `reps`.
- **Parameters:**
  - `A` (`array_like`): Input array.
  - `reps` (`array_like`): Repetitions along each axis.
- **Returns:** `ndarray`

### `np.repeat(a, repeats, axis=None) -> ndarray`
> Repeats elements of an array.
- **Parameters:**
  - `a` (`array_like`): Input array.
  - `repeats` (`int | array_like`): Number of repetitions for each element.
  - `axis` (`int`, optional): Axis along which to repeat values (default flattens array).
- **Returns:** `ndarray`

---

## 6. Indexing, Slicing & Boolean Masking

### Indexing Rules
1. **Basic Slicing**: Slicing with integer ranges (`a[1:15, :, 0:16]`) returns a **view** without copying memory. Modifying a slice directly modifies the underlying chunk voxel buffer.
2. **Advanced Indexing**: Indexing using integer arrays or boolean masks (`a[a > 0]`) creates a **copy** of the selected data.
3. **Flat 1D Voxel Coordinates**:
   - In Pyrite, chunks use the convention:
     - `index = x + z * CHUNK_SIZE_X + y * (CHUNK_SIZE_X * CHUNK_SIZE_Z)`
     - To extract coordinates back from flat index:
       - `x = index % CHUNK_SIZE_X`
       - `z = (index // CHUNK_SIZE_X) % CHUNK_SIZE_Z`
       - `y = index // (CHUNK_SIZE_X * CHUNK_SIZE_Z)`

### `np.where(condition, [x, y], /) -> ndarray | tuple[ndarray, ...]`
> Returns elements chosen from `x` or `y` depending on `condition`. When called with only `condition` (1 argument), acts as shorthand for `np.nonzero(condition)`.
- **Parameters:**
  - `condition` (`array_like, bool`): Boolean condition array.
  - `x, y` (`array_like`, optional): Values from which to choose. `x` where `condition` is True, `y` where False.
- **Returns:** `ndarray` (if `x` and `y` given) or `tuple[ndarray, ...]` (indices if only `condition` given).

### `np.nonzero(a) -> tuple[ndarray, ...]`
> Returns a tuple of arrays containing the indices of elements that are non-zero.
- **Parameters:**
  - `a` (`array_like`): Input array.
- **Returns:** `tuple[ndarray, ...]`: One array per dimension in `a`.
- **Example:**
  ```python
  # Find all solid voxel coordinates in a 3D chunk
  x_coords, y_coords, z_coords = np.nonzero(chunk_voxels)
  ```

### `np.argwhere(a) -> ndarray`
> Finds the indices of array elements that are non-zero, grouped by element.
- **Parameters:**
  - `a` (`array_like`): Input array.
- **Returns:** `ndarray` of shape `(N, a.ndim)`.

### `np.take(a, indices, axis=None, out=None, mode='raise') -> ndarray`
> Takes elements from an array along an axis.
- **Parameters:**
  - `a` (`array_like`): Source array.
  - `indices` (`array_like`): Indices of values to extract.
  - `axis` (`int`, optional): Axis over which to select values. Default flattens array.
  - `mode` (`{'raise', 'wrap', 'clip'}`, optional): Boundary behavior.
- **Returns:** `ndarray`

### `np.put(a, ind, v, mode='raise') -> None`
> Replaces specified elements of an array with given values. In-place mutation.
- **Parameters:**
  - `a` (`ndarray`): Target array.
  - `ind` (`array_like`): Target 1D indices.
  - `v` (`array_like`): Values to place at indices.
  - `mode` (`{'raise', 'wrap', 'clip'}`, optional): Boundary behavior.

### `np.clip(a, a_min=<no value>, a_max=<no value>, out=None, *, min=<no value>, max=<no value>, **kwargs) -> ndarray`
> Clips (limits) the values in an array to interval `[min, max]`. Essential for bounding light levels `[0, 15]`, coordinate bounds, and health values.
- **Parameters:**
  - `a` (`array_like`): Input array.
  - `a_min` / `min` (`scalar | array_like`, optional): Minimum value.
  - `a_max` / `max` (`scalar | array_like`, optional): Maximum value.
  - `out` (`ndarray`, optional): Results destination.
- **Returns:** `ndarray`

---

## 7. Bitwise Operations (Pyrite Voxel & Lighting Packing)

Bitwise ufuncs operate element-wise on underlying binary representations of integer arrays. These are fundamental in Pyrite's meshing and lighting pipeline to pack/unpack voxel IDs, sunlight levels, torchlight levels, and normal face flags into single 32-bit or 64-bit integers.

### Universal Signature Pattern
```python
ufunc(x1, x2, /, out=None, *, where=True, casting='same_kind', order='K', dtype=None, subok=True) -> ndarray
```

### Bitwise Functions
- **`np.bitwise_and(x1, x2, /, out=None, ...) -> ndarray`**: Element-wise bitwise AND (`x1 & x2`). Used to mask out specific bit fields:
  ```python
  # Extract 4-bit torchlight (bits 0..3)
  torch_light = np.bitwise_and(packed_light, 0x0F)
  ```
- **`np.bitwise_or(x1, x2, /, out=None, ...) -> ndarray`**: Element-wise bitwise OR (`x1 | x2`). Used to pack distinct bit fields:
  ```python
  # Pack sunlight (4 bits shifted by 4) and torchlight (4 bits)
  packed_light = np.bitwise_or(np.left_shift(sun_light, 4), torch_light)
  ```
- **`np.bitwise_xor(x1, x2, /, out=None, ...) -> ndarray`**: Element-wise bitwise XOR (`x1 ^ x2`).
- **`np.invert(x, /, out=None, ...) -> ndarray`**: Element-wise bitwise NOT (`~x`).
- **`np.left_shift(x1, x2, /, out=None, ...) -> ndarray`**: Element-wise left shift (`x1 << x2`).
- **`np.right_shift(x1, x2, /, out=None, ...) -> ndarray`**: Element-wise right shift (`x1 >> x2`).

### Bit-Packing Example for Pyrite Vertices
```python
# 64-bit vertex packing in Pyrite:
# Bits 0-5: X (6 bits, 0-63)
# Bits 6-14: Y (9 bits, 0-511)
# Bits 15-20: Z (6 bits, 0-63)
# Bits 21-23: Normal Face ID (3 bits, 0-5)
# Bits 24-25: AO (2 bits, 0-3)
# Bits 26-29: Torchlight (4 bits, 0-15)
# Bits 30-33: Sunlight (4 bits, 0-15)
# Bits 34-49: Texture / Material ID (16 bits)
packed_v = (
    np.uint64(x)
    | (np.uint64(y) << np.uint64(6))
    | (np.uint64(z) << np.uint64(15))
    | (np.uint64(face_id) << np.uint64(21))
    | (np.uint64(ao) << np.uint64(24))
    | (np.uint64(torch) << np.uint64(26))
    | (np.uint64(sun) << np.uint64(30))
    | (np.uint64(tex_id) << np.uint64(34))
)
```

---

## 8. Core Mathematical & Rounding Operations

### Arithmetic Ufuncs
All arithmetic ufuncs support broadcasting, in-place evaluation via `out=...`, and optional `where=...` condition masking:
- **`np.add(x1, x2, /, out=None, ...)`**: $x_1 + x_2$
- **`np.subtract(x1, x2, /, out=None, ...)`**: $x_1 - x_2$
- **`np.multiply(x1, x2, /, out=None, ...)`**: $x_1 \times x_2$
- **`np.divide(x1, x2, /, out=None, ...)`**: $x_1 / x_2$ (floating-point division)
- **`np.floor_divide(x1, x2, /, out=None, ...)`**: $\lfloor x_1 / x_2 \rfloor$ (integer division, essential for world-to-chunk coordinate translation: `chunk_x = np.floor_divide(world_x, 16)`)
- **`np.mod(x1, x2, /, out=None, ...)`**: $x_1 \pmod{x_2}$ (modulo, essential for chunk-local coordinates: `local_x = np.mod(world_x, 16)`)
- **`np.negative(x, /, out=None, ...)`**: $-x$
- **`np.power(x1, x2, /, out=None, ...)`**: $x_1^{x_2}$

### Coordinate & Grid Rounding Ufuncs
Used for converting continuous floating-point camera positions, raycast intersections, and AABBs to integer voxel grid coordinates:
- **`np.floor(x, /, out=None, ...) -> ndarray`**: Returns $\lfloor x \rfloor$ element-wise.
  ```python
  voxel_pos = np.floor(hit_point).astype(np.int32)
  ```
- **`np.ceil(x, /, out=None, ...) -> ndarray`**: Returns $\lceil x \rceil$ element-wise.
- **`np.trunc(x, /, out=None, ...) -> ndarray`**: Returns truncated integer portion of scalar $x$ towards zero.
- **`np.round(a, decimals=0, out=None) -> ndarray`**: Evenly rounds to the given number of decimals.
- **`np.abs(x, /, out=None, ...) -> ndarray`**: Returns absolute value $|x|$ (alias for `np.absolute`).

---

## 9. Reductions, Searches & Statistics

### `np.all(a, axis=None, out=None, keepdims=<no value>, *, where=<no value>) -> ndarray | bool_`
> Tests whether all array elements along a given axis evaluate to `True`.

### `np.any(a, axis=None, out=None, keepdims=<no value>, *, where=<no value>) -> ndarray | bool_`
> Tests whether any array element along a given axis evaluates to `True`. Used in Pyrite chunk updates to verify if a chunk contains any non-air voxels before constructing a render mesh:
```python
is_chunk_empty = not np.any(voxel_chunk)
```

### `np.sum(a, axis=None, dtype=None, out=None, keepdims=<no value>, initial=<no value>, where=<no value>) -> ndarray | number`
> Sum of array elements over a given axis.

### `np.prod(a, axis=None, dtype=None, out=None, keepdims=<no value>, initial=<no value>, where=<no value>) -> ndarray | number`
> Product of array elements over a given axis.

### `np.min(a, axis=None, out=None, keepdims=<no value>, initial=<no value>, where=<no value>) -> ndarray | number`
> Return the minimum of an array or minimum along an axis.

### `np.max(a, axis=None, out=None, keepdims=<no value>, initial=<no value>, where=<no value>) -> ndarray | number`
> Return the maximum of an array or maximum along an axis.

### `np.argmin(a, axis=None, out=None, *, keepdims=<no value>) -> ndarray | int64`
> Returns the indices of the minimum values along an axis.

### `np.argmax(a, axis=None, out=None, *, keepdims=<no value>) -> ndarray | int64`
> Returns the indices of the maximum values along an axis.

### `np.mean(a, axis=None, dtype=None, out=None, keepdims=<no value>, *, where=<no value>) -> ndarray | float`
> Compute the arithmetic mean along the specified axis. Used in Pyrite engine profiler (`src/core/profiler.py`) to report average frame times.

### `np.percentile(a, q, axis=None, out=None, overwrite_input=False, method='linear', keepdims=False, *, weights=None, interpolation=None) -> ndarray | float`
> Compute the $q$-th percentile of the data along the specified axis. Used in engine frame analysis (e.g. 99th percentile frame times, 1% low FPS).
- **Parameters:**
  - `a` (`array_like`): Input array.
  - `q` (`float | array_like`): Percentile or sequence of percentiles between 0 and 100.
  - `method` (`str`, optional): Estimation method (`'linear'`, `'lower'`, `'higher'`, `'midpoint'`, `'nearest'`). Default `'linear'`.

---

## 10. Linear Algebra & Geometry

### `np.dot(a, b, out=None) -> ndarray`
> Dot product of two arrays.
- If both `a` and `b` are 1D arrays, computes inner vector product $\mathbf{a} \cdot \mathbf{b}$.
- If both `a` and `b` are 2D arrays, computes matrix multiplication.
- **Parameters:**
  - `a`, `b` (`array_like`): Input arrays.
  - `out` (`ndarray`, optional): Output argument.
- **Returns:** `ndarray | scalar`

### `np.cross(a, b, axisa=-1, axisb=-1, axisc=-1, axis=None) -> ndarray`
> Computes the vector cross product $\mathbf{a} \times \mathbf{b}$ in 3D space. Critical for computing face normal vectors from triangle vertex positions.
- **Parameters:**
  - `a`, `b` (`array_like`): Components of vectors.
  - `axisa, axisb, axisc` (`int`, optional): Axes of `a`, `b`, and result defining vectors (default `-1`).
- **Returns:** `ndarray`

### `np.matmul(x1, x2, /, out=None, *, casting='same_kind', order='K', dtype=None, subok=True) -> ndarray`
> Matrix product of two arrays (equivalent to `@` operator). Evaluates stacks of matrices when dimensions exceed 2D.

### `np.matvec(x1, x2, /, out=None, *, casting='same_kind', order='K', dtype=None, subok=True) -> ndarray`
> **New in NumPy 2.2**: Matrix-vector product for stacks of matrices and column vectors.
- **Parameters:**
  - `x1` (`array_like`): Matrix or stack of matrices with shape `(..., M, N)`.
  - `x2` (`array_like`): Vector or stack of vectors with shape `(..., N)`.
- **Returns:** `ndarray` with shape `(..., M)`.

### `np.vecmat(x1, x2, /, out=None, *, casting='same_kind', order='K', dtype=None, subok=True) -> ndarray`
> **New in NumPy 2.2**: Vector-matrix product for stacks of vectors and matrices.
- **Parameters:**
  - `x1` (`array_like`): Vector or stack of vectors with shape `(..., M)`.
  - `x2` (`array_like`): Matrix or stack of matrices with shape `(..., M, N)`.
- **Returns:** `ndarray` with shape `(..., N)`.

### `np.linalg.norm(x, ord=None, axis=None, keepdims=False) -> ndarray | float`
> Matrix or vector norm (Euclidean distance when `ord=None` or `ord=2`). Essential for calculating distance from player to chunk, entity velocities, and frustum bounding sphere distances.
- **Parameters:**
  - `x` (`array_like`): Input array.
  - `ord` (`{None, 1, 2, np.inf, -np.inf}`, optional): Order of the norm. Default Euclidean ($L_2$).
  - `axis` (`int | tuple[int, int]`, optional): Axis along which to compute norm.
  - `keepdims` (`bool`, optional): If `True`, preserved axes have size 1.
- **Returns:** `ndarray | float`

---

## 11. Random Number Generation (`np.random`)

NumPy provides both modern `Generator` (recommended) and legacy APIs for procedural world generation, terrain noise seeds, and particle physics.

### Modern Generator API (`np.random.default_rng`)
```python
rng = np.random.default_rng(seed=1337)
```
- **`rng.integers(low, high=None, size=None, dtype=np.int64, endpoint=False) -> ndarray | int`**:
  Returns random integers from `low` (inclusive) to `high` (exclusive). Set `endpoint=True` for inclusive upper bound.
- **`rng.random(size=None, dtype=np.float64, out=None) -> ndarray | float`**:
  Returns random floating-point numbers in interval `[0.0, 1.0)`.
- **`rng.uniform(low=0.0, high=1.0, size=None) -> ndarray | float`**:
  Returns samples from uniform distribution `[low, high)`.
- **`rng.choice(a, size=None, replace=True, p=None, axis=0, shuffle=True) -> ndarray | Any`**:
  Generates a random sample from a given 1D array.

### Legacy API Functions
Present across existing Pyrite scripts:
- **`np.random.rand(*args) -> ndarray | float`**: Uniform values in `[0, 1)`.
- **`np.random.randn(*args) -> ndarray | float`**: Standard normal distribution ($\mu=0, \sigma=1$).
- **`np.random.randint(low, high=None, size=None, dtype=int) -> ndarray | int`**: Random integers from low to high.
- **`np.random.choice(a, size=None, replace=True, p=None) -> ndarray | Any`**: Random choice from sequence.

---

## 12. High-Performance Voxel Engine Interop (ModernGL & Numba)

### ModernGL Buffer Uploads
To upload mesh vertex attributes to a ModernGL vertex buffer object (`mgl.Buffer`), the NumPy array must be C-contiguous:
```python
# 1. Ensure array is contiguous and matches shader format
clean_vertices = np.ascontiguousarray(vertices, dtype=np.float32)

# 2. Upload directly to ModernGL VBO
vbo = ctx.buffer(clean_vertices.tobytes())
# Or in-place rewrite existing VBO without allocation:
vbo.write(clean_vertices)
```

### Numba JIT Interaction (`@njit(fastmath=True)`)
When passing NumPy arrays to Numba-accelerated functions in Pyrite:
1. **Contiguity Guarantee**: Always pass `arr` where `arr.flags['C_CONTIGUOUS']` is True. Non-contiguous slices (e.g. `arr[::2]`) force Numba to use slow strided iteration.
2. **Explicit Fixed-Width Dtypes**: Always initialize arrays using explicit types:
   ```python
   # Correct
   voxels = np.zeros((16, 256, 16), dtype=np.uint8)
   # Wrong (allocates float64, incompatible with bit shifts)
   voxels = np.zeros((16, 256, 16))
   ```
3. **No Dynamic Shape Allocations in Inner Loops**: Allocate mesh buffers outside hot loops using `np.empty((MAX_VERTICES, ...))` and return vertex counts rather than calling `np.concatenate` or `np.append` inside loops.
4. **Avoiding Python Objects**: Arrays passed to `@njit` must not contain Python objects (`dtype=object`) or non-scalar types. Use structured dtypes or parallel primitive arrays.

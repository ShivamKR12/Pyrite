---
name: pyglm-api
description: API reference for pyglm 2.8.3
---

# PyGLM 2.8.3 API Reference

`pyglm` (OpenGL Mathematics for Python) provides high-performance vector and matrix math adhering to the C++ GLM API specifications.

> **CRITICAL CONVENTIONS**:
> 1. **Angles in Radians**: All trigonometric and rotation functions (`perspective`, `rotate`, `sin`, `cos`, etc.) strictly take angles in **radians**. Use `glm.radians(degrees)` to convert.
> 2. **Constants are Functions**: Mathematical constants in PyGLM are functions, not variables: call `glm.pi()`, `glm.two_pi()`, `glm.half_pi()`, `glm.e()`.
> 3. **Column-Major Memory Layout**: Matrices in PyGLM are column-major. When passing matrices to OpenGL (`glUniformMatrix4fv`), pass `GL_FALSE` for the `transpose` parameter.
> 4. **Buffer Protocol & Pointer**: All PyGLM vectors and matrices implement the Python Buffer Protocol (`memoryview`, `bytes(m)`), have `.to_bytes()`, and provide `glm.value_ptr(x)` for ctypes pointer access.

---

## 1. Vectors (`vec2`, `vec3`, `vec4`)

### Types
- Single precision float (default): `glm.vec2`, `glm.vec3`, `glm.vec4`
- Integer: `glm.ivec2`, `glm.ivec3`, `glm.ivec4` (int32)
- Unsigned integer: `glm.uvec2`, `glm.uvec3`, `glm.uvec4` (uint32)
- Double precision: `glm.dvec2`, `glm.dvec3`, `glm.dvec4` (float64)
- Boolean: `glm.bvec2`, `glm.bvec3`, `glm.bvec4` (bool)

### Constructors

#### `glm.vec2`
```python
glm.vec2()                                 # vec2(0.0, 0.0)
glm.vec2(scalar: float)                    # vec2(s, s)
glm.vec2(x: float, y: float)               # vec2(x, y)
glm.vec2(v: vec2)                          # copy constructor
glm.vec2(iv: ivec2)                        # type conversion
```

#### `glm.vec3`
```python
glm.vec3()                                 # vec3(0.0, 0.0, 0.0)
glm.vec3(scalar: float)                    # vec3(s, s, s)
glm.vec3(x: float, y: float, z: float)     # vec3(x, y, z)
glm.vec3(xy: vec2, z: float)               # composite constructor
glm.vec3(x: float, yz: vec2)               # composite constructor
glm.vec3(v: vec3)                          # copy constructor
```

#### `glm.vec4`
```python
glm.vec4()                                       # vec4(0.0, 0.0, 0.0, 0.0)
glm.vec4(scalar: float)                          # vec4(s, s, s, s)
glm.vec4(x: float, y: float, z: float, w: float) # vec4(x, y, z, w)
glm.vec4(xyz: vec3, w: float)                    # composite constructor
glm.vec4(xy: vec2, z: float, w: float)           # composite constructor
glm.vec4(xy: vec2, zw: vec2)                     # composite constructor
glm.vec4(v: vec4)                                # copy constructor
```

### Component Access & Swizzling
- **Coordinates**: `.x`, `.y`, `.z`, `.w`
- **Colors**: `.r`, `.g`, `.b`, `.a`
- **Texture Coordinates**: `.s`, `.t`, `.p`, `.q`
- **0-based Indexing**: `v[0]`, `v[1]`, `v[2]`, `v[3]`
- **Swizzling**: Returns a new vector or scalar:
  ```python
  v = glm.vec4(1.0, 2.0, 3.0, 4.0)
  v.xy      # glm.vec2(1.0, 2.0)
  v.xyz     # glm.vec3(1.0, 2.0, 3.0)
  v.rgb     # glm.vec3(1.0, 2.0, 3.0)
  v.wzyx    # glm.vec4(4.0, 3.0, 2.0, 1.0)
  ```
- **Swizzle & Index Assignment**:
  ```python
  v[0] = 5.0
  v.xy = glm.vec2(9.0, 8.0)
  ```

### Vector Operators
| Operator | Syntax | Description |
| :--- | :--- | :--- |
| `+` | `v1 + v2`, `v + s` | Component-wise addition |
| `-` | `v1 - v2`, `v - s`, `-v` | Component-wise subtraction / negation |
| `*` | `v1 * v2`, `v * s` | **Component-wise multiplication** (NOT dot product) |
| `/` | `v1 / v2`, `v / s` | Component-wise division |
| `@` | `v1 @ v2` | **Dot product** (`float(glm.dot(v1, v2))`) |
| `==`, `!=` | `v1 == v2` | Value equality |
| `len(v)` | `len(v)` | Component count (2, 3, or 4) |
| `iter(v)` | `for c in v:` | Component iteration |

### Vector Methods
- `v.to_list() -> list[float]`
- `v.to_tuple() -> tuple[float, ...]`
- `v.to_bytes() -> bytes` (Raw IEEE 754 binary bytes: 8 bytes for vec2, 12 for vec3, 16 for vec4)
- `glm.vecN.from_bytes(bytes_data: bytes) -> vecN`

---

## 2. Matrices (`mat4`, `mat3`, `mat2`)

### Types
- `glm.mat4` (alias for `glm.mat4x4`): 4 columns, 4 rows of 32-bit floats
- `glm.mat3` (alias for `glm.mat3x3`): 3 columns, 3 rows of 32-bit floats
- `glm.mat2` (alias for `glm.mat2x2`): 2 columns, 2 rows of 32-bit floats
- `glm.dmat4`: 64-bit double precision 4x4 matrix

### Constructors (`glm.mat4`)
```python
glm.mat4()                     # Identity matrix mat4(1.0)
glm.mat4(1.0)                  # Diagonal matrix with 1.0 on diagonal (Identity)
glm.mat4(s: float)             # Diagonal matrix with s on diagonal
glm.mat4(col0: vec4, col1: vec4, col2: vec4, col3: vec4) # From 4 column vectors
glm.mat4(c0_r0, c0_r1, c0_r2, c0_r3, c1_r0, ...)         # 16 floats (column-major order)
glm.mat4(m3: mat3)             # Embed 3x3 into 4x4 (bottom-right 1.0)
glm.mat4(m: mat4)              # Copy constructor
```

### Indexing & Structure
- **Column-Major**: Indexing a matrix yields its column vectors (`mvec4`):
  ```python
  m = glm.mat4(1.0)
  col0 = m[0]          # mvec4 / vec4 (first column)
  col3 = m[3]          # mvec4 / vec4 (translation column in affine transform)
  elem = m[col][row]   # Float value at column `col`, row `row`
  ```
- **Helper functions**:
  - `glm.column(m: mat4, index: int) -> vec4`
  - `glm.column(m: mat4, index: int, val: vec4) -> mat4`
  - `glm.row(m: mat4, index: int) -> vec4`
  - `glm.row(m: mat4, index: int, val: vec4) -> mat4`

### Matrix Operators
| Operator | Syntax | Description |
| :--- | :--- | :--- |
| `*` or `@` | `m1 * m2` / `m1 @ m2` | **Matrix multiplication** |
| `*` or `@` | `m * v` / `m @ v` | **Transforms column vector** (`vec4` $\rightarrow$ `vec4`) |
| `*` or `@` | `v * m` / `v @ m` | Row vector transformation |
| `+`, `-` | `m1 + m2`, `m1 - m2` | Component-wise addition / subtraction |
| `*`, `/` | `m * s`, `m / s` | Scalar multiplication / division |
| `==`, `!=` | `m1 == m2` | Matrix value equality |

### Matrix Methods
- `m.to_list() -> list[list[float]]`: Nested list of 4 columns, each with 4 floats
- `m.to_tuple() -> tuple[tuple[float, ...], ...]`: Nested tuple of columns
- `m.to_bytes() -> bytes`: Exactly 64 bytes (16 $\times$ 4-byte IEEE 754 floats in column-major order)
- `glm.mat4.from_bytes(data: bytes) -> mat4`
- `m.length() -> int`: Number of columns (4)

---

## 3. Transformation & Projection Functions

### Projection Matrices

#### `glm.perspective`
```python
glm.perspective(fovy: float, aspect: float, near: float, far: float) -> mat4
```
- Builds a right-handed perspective projection matrix for OpenGL [-1, 1] clip depth.
- `fovy`: Vertical field of view in **radians** (e.g. `glm.radians(60.0)`).
- `aspect`: Viewport aspect ratio (`width / height`).
- `near`: Distance to near clipping plane (> 0).
- `far`: Distance to far clipping plane (> near).

#### `glm.perspectiveFov`
```python
glm.perspectiveFov(fov: float, width: float, height: float, near: float, far: float) -> mat4
```
- `fov`: Field of view in **radians**.
- `width`: Viewport width (pixels or units).
- `height`: Viewport height (pixels or units).

#### `glm.ortho`
```python
# 2D Orthographic (zNear = -1.0, zFar = 1.0)
glm.ortho(left: float, right: float, bottom: float, top: float) -> mat4

# 3D Orthographic
glm.ortho(left: float, right: float, bottom: float, top: float, zNear: float, zFar: float) -> mat4
```
- Creates an orthographic projection matrix.

### View Matrices

#### `glm.lookAt`
```python
glm.lookAt(eye: vec3, center: vec3, up: vec3) -> mat4
```
- Builds a standard right-handed look-at view matrix.
- `eye`: Camera position in world space.
- `center`: Point in world space the camera is looking toward.
- `up`: Normalized camera up vector (typically `glm.vec3(0.0, 1.0, 0.0)`).
- Specific handedness variants:
  - `glm.lookAtRH(eye: vec3, center: vec3, up: vec3) -> mat4` (Right-handed, default)
  - `glm.lookAtLH(eye: vec3, center: vec3, up: vec3) -> mat4` (Left-handed)

### Affine Transformations

#### `glm.translate`
```python
# Overload 1: Create pure translation matrix from identity
glm.translate(v: vec3) -> mat4

# Overload 2: Post-multiply matrix m by translation matrix
glm.translate(m: mat4, v: vec3) -> mat4
```
- Note: `glm.translate(m, v)` is mathematically equivalent to `m * glm.translate(v)`.
- 2D variants: `glm.translate(v: vec2) -> mat3`, `glm.translate(m: mat3, v: vec2) -> mat3`.

#### `glm.rotate`
```python
# Overload 1: Create pure rotation matrix from identity
glm.rotate(angle: float, axis: vec3) -> mat4

# Overload 2: Post-multiply matrix m by rotation matrix
glm.rotate(m: mat4, angle: float, axis: vec3) -> mat4

# Overload 3: Rotate a 3D vector around an axis
glm.rotate(v: vec3, angle: float, normal: vec3) -> vec3
```
- `angle`: Rotation angle in **radians** (e.g. `glm.radians(45.0)`).
- `axis`: Axis of rotation, must be normalized (e.g. `glm.vec3(0.0, 1.0, 0.0)`).
- Note: `glm.rotate(m, angle, axis)` is mathematically equivalent to `m * glm.rotate(angle, axis)`.

#### `glm.scale`
```python
# Overload 1: Create pure scaling matrix from identity
glm.scale(v: vec3) -> mat4

# Overload 2: Post-multiply matrix m by scaling matrix
glm.scale(m: mat4, v: vec3) -> mat4
```
- Note: `glm.scale(m, v)` is mathematically equivalent to `m * glm.scale(v)`.

---

## 4. Geometric & Vector Functions

| Function | Signature | Description |
| :--- | :--- | :--- |
| `glm.normalize` | `normalize(x: vecN) -> vecN`<br>`normalize(x: quat) -> quat` | Returns vector with unit length in same direction |
| `glm.cross` | `cross(x: vec3, y: vec3) -> vec3` | Vector cross product (perpendicular vector) |
| `glm.dot` | `dot(x: vecN, y: vecN) -> float`<br>`dot(x: number, y: number) -> float` | Vector dot product |
| `glm.length` | `length(x: vecN) -> float`<br>`length(x: float) -> float` | Euclidean length ($\sqrt{\mathbf{x} \cdot \mathbf{x}}$) |
| `glm.distance` | `distance(p0: vecN, p1: vecN) -> float` | Euclidean distance between two points |
| `glm.distance2` | `distance2(p0: vecN, p1: vecN) -> float` | Squared distance between two points ($|p_0 - p_1|^2$) |
| `glm.reflect` | `reflect(I: vecN, N: vecN) -> vecN` | Reflection direction: $I - 2(N \cdot I)N$ |
| `glm.refract` | `refract(I: vecN, N: vecN, eta: float) -> vecN` | Refraction vector for incident $I$, normal $N$, ratio $eta$ |
| `glm.faceforward`| `faceforward(N: vecN, I: vecN, Nref: vecN) -> vecN` | Orients vector $N$ to point away from surface |

---

## 5. Common Mathematical Functions

### Interpolation & Range Clamping
```python
glm.clamp(x: float|vecN, minVal: float|vecN, maxVal: float|vecN) -> float|vecN
glm.mix(x: float|vecN, y: float|vecN, a: float|vecN) -> float|vecN  # x * (1 - a) + y * a
glm.step(edge: float|vecN, x: float|vecN) -> float|vecN            # 0.0 if x < edge else 1.0
glm.smoothstep(edge0: float|vecN, edge1: float|vecN, x: float|vecN) -> float|vecN
```

### Rounding & Truncation
```python
glm.floor(x: float|vecN) -> float|vecN   # Largest integer <= x
glm.ceil(x: float|vecN) -> float|vecN    # Smallest integer >= x
glm.fract(x: float|vecN) -> float|vecN   # Fractional part: x - floor(x)
glm.mod(a, b) -> Any                     # Modulo equivalent to a % b
glm.abs(x: float|vecN) -> float|vecN     # Absolute value
glm.sign(x: float|vecN) -> float|vecN    # 1.0 (x > 0), 0.0 (x == 0), -1.0 (x < 0)
glm.min(x, y, ...) -> float|vecN         # Minimum value
glm.max(x, y, ...) -> float|vecN         # Maximum value
```

### Trigonometry & Angles
```python
glm.radians(deg: float|vecN) -> float|vecN  # Degrees to radians
glm.degrees(rad: float|vecN) -> float|vecN  # Radians to degrees
glm.sin(x: float|vecN) -> float|vecN
glm.cos(x: float|vecN) -> float|vecN
glm.tan(x: float|vecN) -> float|vecN
glm.asin(x: float|vecN) -> float|vecN
glm.acos(x: float|vecN) -> float|vecN
glm.atan(y: float|vecN, x: float|vecN) -> float|vecN  # 2-argument atan (quadrant aware)
glm.atan(y_over_x: float|vecN) -> float|vecN          # 1-argument atan
```

### Mathematical Constants (Functions)
```python
glm.pi()      # 3.141592653589793
glm.two_pi()  # 6.283185307179586
glm.half_pi() # 1.5707963267948966
glm.e()       # 2.718281828459045
glm.epsilon() # 2.220446049250313e-16
```

---

## 6. Matrix Inversion & Decomposition

```python
glm.inverse(m: mat4) -> mat4           # Matrix inverse
glm.transpose(m: mat4) -> mat4         # Transposed matrix
glm.determinant(m: mat4) -> float      # Matrix determinant
glm.affineInverse(m: mat4) -> mat4     # Fast matrix inverse for affine matrices
```

---

## 7. Screen & Unprojection Utilities

```python
# Project 3D object coordinate to 2D window coordinate
glm.project(obj: vec3, model: mat4, proj: mat4, viewport: vec4) -> vec3

# Map 2D window coordinate back into 3D world/object space
glm.unProject(win: vec3, model: mat4, proj: mat4, viewport: vec4) -> vec3
```
- `viewport`: `vec4(x, y, width, height)`
- `win.z`: Depth buffer coordinate (0.0 to 1.0)

---

## 8. Quaternions (`quat`)

### Constructor & Conversions
```python
glm.quat()                                       # Identity quaternion (w=1, x=0, y=0, z=0)
glm.quat(w: float, x: float, y: float, z: float)
glm.quat(euler_angles_radians: vec3)             # From euler angles (pitch, yaw, roll)
glm.angleAxis(angle: float, axis: vec3) -> quat  # Angle (rad) and normalized axis
glm.mat4_cast(q: quat) -> mat4                   # Convert quaternion to 4x4 matrix
glm.quat_cast(m: mat4) -> quat                   # Convert rotation matrix to quaternion
```

### Operations
```python
glm.slerp(x: quat, y: quat, a: float) -> quat    # Spherical linear interpolation
glm.conjugate(q: quat) -> quat                   # Quaternion conjugate
glm.eulerAngles(q: quat) -> vec3                 # Euler angles in radians: (pitch, yaw, roll)
glm.pitch(q: quat) -> float                      # Pitch angle (radians)
glm.yaw(q: quat) -> float                        # Yaw angle (radians)
glm.roll(q: quat) -> float                       # Roll angle (radians)
```

---

## 9. OpenGL Interop Best Practices in Pyrite

### Uniform Uploads
Pyrite uses `PyOpenGL` alongside `pyglm`. To pass matrices and vectors to shaders:

```python
# Method A: Using value_ptr (direct ctypes pointer)
from OpenGL.GL import glUniformMatrix4fv, glUniform3fv, GL_FALSE

glUniformMatrix4fv(location, 1, GL_FALSE, glm.value_ptr(matrix))
glUniform3fv(location, 1, glm.value_ptr(vector))

# Method B: Using python buffer protocol / bytes
glUniformMatrix4fv(location, 1, GL_FALSE, matrix.to_bytes())
glUniform3fv(location, 1, vector.to_bytes())
```

> **IMPORTANT**:
> - Never set `transpose=GL_TRUE` when using `glm` matrices with standard OpenGL shaders: `glm` matrices are already column-major.
> - `sizeof`: PyGLM provides `glm.sizeof(glm.vec3)` (returns 12), `glm.sizeof(glm.mat4)` (returns 64).

### Typical Camera MVP Calculation
```python
# Projection matrix
proj = glm.perspective(glm.radians(fov), aspect_ratio, near_plane, far_plane)

# View matrix
view = glm.lookAt(cam_pos, cam_pos + cam_front, cam_up)

# Model matrix
model = glm.mat4(1.0)
model = glm.translate(model, world_pos)
model = glm.rotate(model, glm.radians(angle), axis)
model = glm.scale(model, scale_vec)

# Model-View-Projection (MVP)
mvp = proj * view * model
```

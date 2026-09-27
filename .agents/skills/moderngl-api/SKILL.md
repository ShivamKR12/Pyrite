---
name: moderngl-api
description: API reference for moderngl 5.12.0
---

# ModernGL 5.12.0 API Reference

This document provides the exact, verified API specification for **ModernGL 5.12.0** (`moderngl`), focusing on core classes: `Context`, `Buffer`, `VertexArray`, `Program`, `Texture`, and `TextureArray`. All signatures, parameter types, defaults, and return values reflect the tested ModernGL 5.12.0 runtime.

---

## 1. Module-Level Functions

### `moderngl.create_context(require: Optional[int] = 330, standalone: bool = False, share: bool = False, **settings) -> Context`
> Creates and initializes a ModernGL context. If an active OpenGL context already exists (e.g., via Pygame, GLFW, Pyglet, SDL2), it detects and wraps it.
- **Parameters:**
  - `require` (`int`, optional): Minimum required OpenGL version code (e.g. `330` for OpenGL 3.3, `430` for OpenGL 4.3). Default is `330`.
  - `standalone` (`bool`, optional): If `True`, creates a standalone headless context (e.g., using EGL, OSMesa, or headless backend). Default is `False`.
  - `share` (`bool`, optional): Create a shared context with the current active context. Default is `False`.
  - `**settings`: Backend-specific settings passed to the context loader (`glcontext`).
- **Returns:** `Context` - The ModernGL context object.

### `moderngl.create_standalone_context(**kwargs) -> Context`
> Helper shortcut to create a headless/standalone OpenGL context without an existing window.
- **Parameters:**
  - `require` (`int`, optional): Minimum required OpenGL version (default 330).
  - `**kwargs`: Backend options passed to `glcontext`.
- **Returns:** `Context`

### `moderngl.get_context() -> Context`
> Returns the active ModernGL context or the last detected context.
- **Returns:** `Context`

### `moderngl.init_context(loader=None) -> Context`
> Initializes a context using a custom loader function.
- **Parameters:**
  - `loader` (callable, optional): OpenGL loader function `loader(name: str) -> int`.
- **Returns:** `Context`

### `moderngl.detect_format(program: Program, attributes: Sequence[str], mode: str = 'mgl') -> str`
> Inspects the given shader `Program` and auto-detects the buffer format string matching the specified attribute list.
- **Parameters:**
  - `program` (`Program`): The compiled shader program containing attribute definitions.
  - `attributes` (`Sequence[str]`): List or tuple of attribute names as declared in the vertex shader.
  - `mode` (`str`, optional): Format mode syntax (`'mgl'` for ModernGL syntax like `'3f 2f'`).
- **Returns:** `str` - Detected buffer format string.

---

## 2. Class `Context`

The central object responsible for creating and managing all OpenGL resources, pipeline states, and bindings. Instances cannot be created directly via `Context()`; use `moderngl.create_context()`.

### Constants

#### Context Capability Flags
- `Context.NOTHING: int = 0`
- `Context.BLEND: int = 1` - Alpha / color blending (`GL_BLEND`)
- `Context.DEPTH_TEST: int = 2` - Depth buffer testing (`GL_DEPTH_TEST`)
- `Context.CULL_FACE: int = 4` - Face culling (`GL_CULL_FACE`)
- `Context.RASTERIZER_DISCARD: int = 8` - Discard primitives before rasterization (`GL_RASTERIZER_DISCARD`)
- `Context.PROGRAM_POINT_SIZE: int = 16` - Allow vertex shader to set `gl_PointSize` (`GL_PROGRAM_POINT_SIZE`)

#### Primitive Draw Modes
- `Context.POINTS: int = 0x0000`
- `Context.LINES: int = 0x0001`
- `Context.LINE_LOOP: int = 0x0002`
- `Context.LINE_STRIP: int = 0x0003`
- `Context.TRIANGLES: int = 0x0004`
- `Context.TRIANGLE_STRIP: int = 0x0005`
- `Context.TRIANGLE_FAN: int = 0x0006`
- `Context.LINES_ADJACENCY: int = 0x000A`
- `Context.LINE_STRIP_ADJACENCY: int = 0x000B`
- `Context.TRIANGLES_ADJACENCY: int = 0x000C`
- `Context.TRIANGLE_STRIP_ADJACENCY: int = 0x000D`
- `Context.PATCHES: int = 0x000E`

#### Texture Filter Constants
- `Context.NEAREST: int = 0x2600`
- `Context.LINEAR: int = 0x2601`
- `Context.NEAREST_MIPMAP_NEAREST: int = 0x2700`
- `Context.LINEAR_MIPMAP_NEAREST: int = 0x2701`
- `Context.NEAREST_MIPMAP_LINEAR: int = 0x2702`
- `Context.LINEAR_MIPMAP_LINEAR: int = 0x2703`

#### Blend Factors & Equations
- `Context.ZERO: int = 0x0000`
- `Context.ONE: int = 0x0001`
- `Context.SRC_COLOR: int = 0x0300`
- `Context.ONE_MINUS_SRC_COLOR: int = 0x0301`
- `Context.SRC_ALPHA: int = 0x0302`
- `Context.ONE_MINUS_SRC_ALPHA: int = 0x0303`
- `Context.DST_ALPHA: int = 0x0304`
- `Context.ONE_MINUS_DST_ALPHA: int = 0x0305`
- `Context.DST_COLOR: int = 0x0306`
- `Context.ONE_MINUS_DST_COLOR: int = 0x0307`
- `Context.DEFAULT_BLENDING: Tuple[int, int] = (SRC_ALPHA, ONE_MINUS_SRC_ALPHA)`
- `Context.ADDITIVE_BLENDING: Tuple[int, int] = (ONE, ONE)`
- `Context.PREMULTIPLIED_ALPHA: Tuple[int, int] = (SRC_ALPHA, ONE)`
- `Context.FUNC_ADD: int = 0x8006`
- `Context.FUNC_SUBTRACT: int = 0x800A`
- `Context.FUNC_REVERSE_SUBTRACT: int = 0x800B`
- `Context.MIN: int = 0x8007`
- `Context.MAX: int = 0x8008`

#### Provoking Vertex Conventions
- `Context.FIRST_VERTEX_CONVENTION: int = 0x8E4D`
- `Context.LAST_VERTEX_CONVENTION: int = 0x8E4E`

#### Memory Barrier Bits
- `Context.VERTEX_ATTRIB_ARRAY_BARRIER_BIT: int = 0x00000001`
- `Context.ELEMENT_ARRAY_BARRIER_BIT: int = 0x00000002`
- `Context.UNIFORM_BARRIER_BIT: int = 0x00000004`
- `Context.TEXTURE_FETCH_BARRIER_BIT: int = 0x00000008`
- `Context.SHADER_IMAGE_ACCESS_BARRIER_BIT: int = 0x00000020`
- `Context.COMMAND_BARRIER_BIT: int = 0x00000040`
- `Context.PIXEL_BUFFER_BARRIER_BIT: int = 0x00000080`
- `Context.TEXTURE_UPDATE_BARRIER_BIT: int = 0x00000100`
- `Context.BUFFER_UPDATE_BARRIER_BIT: int = 0x00000200`
- `Context.FRAMEBUFFER_BARRIER_BIT: int = 0x00000400`
- `Context.TRANSFORM_FEEDBACK_BARRIER_BIT: int = 0x00000800`
- `Context.ATOMIC_COUNTER_BARRIER_BIT: int = 0x00001000`
- `Context.SHADER_STORAGE_BARRIER_BIT: int = 0x00002000`
- `Context.ALL_BARRIER_BITS: int = 0xFFFFFFFF`

### Properties

- `viewport: Tuple[int, int, int, int]` (get/set): The viewport rectangle `(x, y, width, height)` of the active framebuffer.
- `scissor: Optional[Tuple[int, int, int, int]]` (get/set): Scissor box rectangle `(x, y, width, height)` or `None` to disable scissor testing.
- `screen: Framebuffer` (read-only): Default system framebuffer (FBO 0).
- `fbo: Framebuffer` (read-only): The currently bound framebuffer.
- `line_width: float` (get/set): The line width for line rendering primitives.
- `point_size: float` (get/set): The point size for point rendering primitives.
- `depth_func: str` (write-only): Depth comparison function. Accepted strings: `'<'`, `'<='`, `'=='`, `'!='`, `'>'`, `'>='`, `'never'`, `'always'`.
- `depth_clamp_range: Optional[Tuple[float, float]]` (write-only): Depth clamp near and far ranges `(near, far)`.
- `blend_func: Tuple[int, int] | Tuple[int, int, int, int]` (write-only): Source and destination blend factors `(src, dst)` or `(src_rgb, dst_rgb, src_a, dst_a)`.
- `blend_equation: Tuple[int, ...]` (write-only): Blend mode equation, e.g. `(ctx.FUNC_ADD,)` or `(rgb_equation, alpha_equation)`.
- `multisample: bool` (write-only): Enable or disable multisampling.
- `wireframe: bool` (get/set): Enable or disable wireframe polygon rasterization mode.
- `cull_face: str` (get/set): Face culling mode: `'back'`, `'front'`, or `'front_and_back'`.
- `front_face: str` (get/set): Front-facing polygon orientation: `'ccw'` (counter-clockwise, default) or `'cw'` (clockwise).
- `patch_vertices: int` (get/set): Number of vertices per patch for tessellation shaders.
- `provoking_vertex: int` (write-only): Provoking vertex convention: `ctx.FIRST_VERTEX_CONVENTION` or `ctx.LAST_VERTEX_CONVENTION`.
- `polygon_offset: Tuple[float, float]` (get/set): `(factor, units)` for depth offset calculation.
- `max_samples: int` (read-only): Maximum number of MSAA samples supported.
- `max_integer_samples: int` (read-only): Maximum number of integer samples supported.
- `max_texture_units: int` (read-only): Maximum number of texture image units supported.
- `max_anisotropy: float` (read-only): Maximum texture anisotropy filter level supported.
- `default_texture_unit: int` (get/set): The default active texture unit.
- `supports_labels: bool` (read-only): Whether debug labels (`KHR_debug` or OpenGL 4.3+) are supported.
- `supports_debug_scopes: bool` (read-only): Whether debug scopes are supported.
- `version_code: int` (read-only): OpenGL version code (e.g. `330` for 3.3, `430` for 4.3).
- `error: str` (read-only): The latest OpenGL error string or `'GL_NO_ERROR'`.
- `extensions: Set[str]` (read-only): Set of available OpenGL extensions.
- `info: Dict[str, Any]` (read-only): Dictionary containing OpenGL hardware and driver information.
- `includes: Dict[str, str]` (read-only): Map of `#include` paths for GLSL shaders.
- `gc_mode: Optional[str]` (get/set): Garbage collection mode: `None`, `'auto'`, or `'context_gc'`.
- `objects: collections.deque` (read-only): Queue of deferred objects waiting to be released when `gc_mode='context_gc'`.
- `extra: Any` (get/set): User-defined metadata attachment.

### Methods

#### Resource Creation Methods
- `buffer(data: Optional[Any] = None, reserve: int = 0, dynamic: bool = False) -> Buffer`
  - Creates a GPU memory buffer.
  - `data`: Initial binary content (`bytes`, `bytearray`, `memoryview`, `numpy.ndarray`).
  - `reserve`: Size in bytes (or string shorthand like `'1MB'`) to pre-allocate if `data` is `None`. `data` and `reserve` are mutually exclusive.
  - `dynamic`: Hint indicating frequently updated buffer (`GL_DYNAMIC_DRAW` vs `GL_STATIC_DRAW`).
- `vertex_array(program: Program, content: Sequence[Tuple[Buffer, str, ...]], index_buffer: Optional[Buffer] = None, index_element_size: int = 4, skip_errors: bool = False, mode: Optional[int] = None) -> VertexArray`
  - Creates a Vertex Array Object (VAO).
  - `program`: Shader `Program` containing vertex attributes.
  - `content`: List of tuples specifying buffer layout: `(buffer, format, 'attrib1', 'attrib2', ...)`.
  - `index_buffer`: Optional index/element `Buffer` for indexed rendering.
  - `index_element_size`: Byte size of index elements: `1` (ubyte), `2` (ushort), or `4` (uint, default).
  - `skip_errors`: If `True`, silently ignores missing attributes.
  - `mode`: Default draw mode (e.g. `Context.TRIANGLES`, default).
- `simple_vertex_array(program: Program, buffer: Buffer, *attributes: str, index_buffer: Optional[Buffer] = None, index_element_size: int = 4, mode: Optional[int] = None) -> VertexArray`
  - Shorthand helper for creating a VAO with a single vertex buffer. Format is automatically detected from the program.
- `program(vertex_shader: Optional[str] = None, fragment_shader: Optional[str] = None, geometry_shader: Optional[str] = None, tess_control_shader: Optional[str] = None, tess_evaluation_shader: Optional[str] = None, varyings: Sequence[str] = (), fragment_outputs: Optional[Dict[str, int]] = None, attributes: Optional[Sequence[str]] = None, varyings_capture_mode: str = 'interleaved') -> Program`
  - Compiles and links GLSL shaders into a `Program`.
  - If `fragment_shader` is `None` and `varyings` is provided, creates a transform feedback program.
  - `varyings_capture_mode`: `'interleaved'` (default) or `'separate'`.
  - `fragment_outputs`: Optional dictionary mapping output variable names to explicit framebuffer color attachment locations.
- `texture(size: Tuple[int, int], components: int, data: Optional[Any] = None, samples: int = 0, alignment: int = 1, dtype: str = 'f1', internal_format: Optional[int] = None, renderbuffer: bool = False) -> Texture`
  - Creates a 2D texture.
  - `size`: `(width, height)`.
  - `components`: `1`, `2`, `3`, or `4`.
  - `samples`: MSAA samples (`0` = no multisampling).
  - `alignment`: Byte alignment `1`, `2`, `4`, or `8` (default `1`).
  - `dtype`: Data format string (`'f1'`, `'f2'`, `'f4'`, `'i1'`, `'i2'`, `'i4'`, `'u1'`, `'u2'`, `'u4'`).
  - `internal_format`: Explicit OpenGL internal format override.
  - `renderbuffer`: If `True`, creates a renderbuffer-backed texture.
- `texture_array(size: Tuple[int, int, int], components: int, data: Optional[Any] = None, alignment: int = 1, dtype: str = 'f1') -> TextureArray`
  - Creates a 2D Texture Array (`GL_TEXTURE_2D_ARRAY`).
  - `size`: `(width, height, layers)`.
  - `data`: Raw bytes of stacked layers where total image height is `height * layers`.
  - `components`: `1`, `2`, `3`, or `4`.
  - `alignment`: `1`, `2`, `4`, or `8`.
  - `dtype`: Data format string (default `'f1'`).
- `texture3d(size: Tuple[int, int, int], components: int, data: Optional[Any] = None, alignment: int = 1, dtype: str = 'f1') -> Texture3D`
  - Creates a 3D texture `(width, height, depth)`.
- `texture_cube(size: Tuple[int, int], components: int, data: Optional[Any] = None, alignment: int = 1, dtype: str = 'f1', internal_format: Optional[int] = None) -> TextureCube`
  - Creates a cubemap texture consisting of 6 square faces.
- `depth_texture(size: Tuple[int, int], data: Optional[Any] = None, samples: int = 0, alignment: int = 4, renderbuffer: bool = False) -> Texture`
  - Creates a 2D depth texture (single component, `dtype='f4'`, `depth=True`).
- `depth_texture_cube(size: Tuple[int, int], data: Optional[Any] = None, alignment: int = 4) -> TextureCube`
  - Creates a cubemap depth texture.
- `framebuffer(color_attachments: Sequence[Any] = (), depth_attachment: Optional[Any] = None) -> Framebuffer`
  - Creates a custom Framebuffer Object (FBO).
  - `color_attachments`: Sequence of `Texture` or `Renderbuffer` attachments.
  - `depth_attachment`: Optional `Texture` or `Renderbuffer` depth attachment.
- `simple_framebuffer(size: Tuple[int, int], components: int = 4, samples: int = 0, dtype: str = 'f1') -> Framebuffer`
  - Creates an FBO backed by a color renderbuffer and a depth renderbuffer.
- `empty_framebuffer(size: Tuple[int, int], layers: int = 0, samples: int = 0) -> Framebuffer`
  - Creates an attachmentless framebuffer (OpenGL 4.3+).
- `renderbuffer(size: Tuple[int, int], components: int = 4, samples: int = 0, dtype: str = 'f1') -> Renderbuffer`
  - Creates a color renderbuffer.
- `depth_renderbuffer(size: Tuple[int, int], samples: int = 0) -> Renderbuffer`
  - Creates a depth renderbuffer (`dtype='f4'`).
- `sampler(repeat_x: bool = True, repeat_y: bool = True, repeat_z: bool = True, filter: Optional[Tuple[int, int]] = None, anisotropy: float = 1.0, compare_func: str = '?', border_color: Optional[Tuple[float, float, float, float]] = None, min_lod: float = -1000.0, max_lod: float = 1000.0, texture: Optional[Texture] = None) -> Sampler`
  - Creates an OpenGL Sampler object (`GL_SAMPLER`).
- `scope(framebuffer: Optional[Framebuffer] = None, enable_only: Optional[int] = None, textures: Sequence[Tuple[Texture, int]] = (), uniform_buffers: Sequence[Tuple[Buffer, int]] = (), storage_buffers: Sequence[Tuple[Buffer, int]] = (), samplers: Sequence[Tuple[Sampler, int]] = (), enable: Optional[int] = None) -> Scope`
  - Creates a rendering `Scope` state encapsulating framebuffer, flags, and resource bindings.
- `query(samples: bool = False, any_samples: bool = False, time: bool = False, primitives: bool = False) -> Query`
  - Creates an asynchronous GPU query object for occlusion or timing metrics.
- `compute_shader(source: str) -> ComputeShader`
  - Compiles and links a GLSL compute shader (OpenGL 4.3+).

#### Context State & Execution Methods
- `clear(red: float = 0.0, green: float = 0.0, blue: float = 0.0, alpha: float = 0.0, depth: float = 1.0, viewport: Optional[Tuple[int, int, int, int]] = None, color: Optional[Tuple[float, ...]] = None) -> None`
  - Clears the currently bound framebuffer color and depth buffers.
- `enable(flags: int) -> None`
  - Enables one or more context flags (e.g. `ctx.enable(moderngl.DEPTH_TEST | moderngl.CULL_FACE)`).
- `disable(flags: int) -> None`
  - Disables context flags.
- `enable_only(flags: int) -> None`
  - Sets the exact state flags enabled, disabling all others.
- `enable_direct(enum: int) -> None` / `disable_direct(enum: int) -> None`
  - Direct `glEnable` / `glDisable` by raw OpenGL integer enum.
- `finish() -> None`
  - Blocks until all pending OpenGL commands have fully completed execution (`glFinish`).
- `copy_buffer(dst: Buffer, src: Buffer, size: int = -1, read_offset: int = 0, write_offset: int = 0) -> None`
  - Copies data directly from `src` GPU buffer to `dst` GPU buffer.
- `copy_framebuffer(dst: Framebuffer, src: Framebuffer) -> None`
  - Blits contents from `src` framebuffer to `dst` framebuffer.
- `detect_framebuffer(glo: Optional[int] = None) -> Framebuffer`
  - Wraps an externally created framebuffer object ID.
- `external_buffer(glo: int, size: int) -> Buffer`
  - Wraps an externally allocated OpenGL buffer ID.
- `external_texture(glo: int, size: Tuple[int, int], components: int, samples: int, dtype: str) -> Texture`
  - Wraps an externally allocated OpenGL texture ID.
- `memory_barrier(barriers: int = ALL_BARRIER_BITS, by_region: bool = False) -> None`
  - Enforces GPU memory barrier synchronization (OpenGL 4.2+).
- `clear_samplers(start: int = 0, end: int = -1) -> None`
  - Unbinds samplers in the given slot range.
- `clear_errors() -> None`
  - Clears OpenGL error queue.
- `gc() -> int`
  - Frees unused context-managed objects and returns the count of released objects.
- `release() -> None`
  - Releases the context and all associated OpenGL handles.
- `debug_scope(label: str, group_id: Optional[int] = None, source: str = 'application') -> Generator`
  - Context manager pushing a debug group marker for GPU debuggers (e.g. RenderDoc).

---

## 3. Class `Buffer`

Encapsulates an OpenGL Buffer Object storing unformatted GPU memory (VBOs, IBOs, UBOs, SSBOs).

### Properties

- `size: int` (read-only): Total buffer size in bytes.
- `dynamic: bool` (read-only): Whether the buffer was created with the dynamic allocation hint (`GL_DYNAMIC_DRAW`).
- `glo: int` (read-only): Raw OpenGL buffer name/handle (integer ID).
- `label: Optional[str]` (get/set): Debug label for the buffer.
- `ctx: Context` (read-only): The `Context` to which this buffer belongs.
- `extra: Any` (get/set): User-defined metadata attachment.

### Methods

- `write(data: Any, offset: int = 0) -> None`
  - Writes data into the GPU buffer starting at byte `offset`.
  - `data`: Any object supporting the Python buffer protocol (`bytes`, `bytearray`, `memoryview`, `numpy.ndarray`).
  - `offset`: Byte offset within the GPU buffer.
- `write_chunks(data: Any, start: int, step: int, count: int) -> None`
  - Writes non-contiguous chunks into the buffer.
- `read(size: int = -1, offset: int = 0) -> bytes`
  - Reads data from the GPU buffer into system memory.
  - `size`: Number of bytes to read (`-1` reads all remaining bytes).
  - `offset`: Byte offset to start reading from.
  - Returns `bytes`.
- `read_into(buffer: bytearray, size: int = -1, offset: int = 0, write_offset: int = 0) -> None`
  - Reads bytes from the GPU buffer directly into a pre-allocated writable Python `bytearray` or `memoryview`.
  - `buffer`: Target writable buffer.
  - `size`: Number of bytes to read (`-1` for full remaining buffer).
  - `offset`: Source read offset in GPU buffer.
  - `write_offset`: Destination offset in target buffer.
- `read_chunks(chunk_size: int, start: int, step: int, count: int) -> bytes`
  - Reads multiple evenly-spaced chunks from the buffer into a single concatenated `bytes` object.
- `read_chunks_into(buffer: bytearray, chunk_size: int, start: int, step: int, count: int, write_offset: int = 0) -> None`
  - Reads chunks into an existing writable target buffer.
- `clear(size: int = -1, offset: int = 0, chunk: Optional[bytes] = None) -> None`
  - Clears buffer content with zeros or repeats the specified byte `chunk`.
  - `size`: Number of bytes to clear (`-1` for all).
  - `offset`: Byte start offset.
  - `chunk`: Optional byte pattern to fill.
- `orphan(size: int = -1) -> None`
  - Re-allocates GPU memory storage for the buffer without creating a new object (buffer orphaning). Eliminates GPU sync stalls when overwriting busy buffers.
  - `size`: New size in bytes (`-1` preserves current size).
- `bind_to_uniform_block(binding: int = 0, offset: int = 0, size: int = -1) -> None`
  - Binds the buffer (or a slice) to a uniform buffer binding point (`glBindBufferRange` / `glBindBufferBase`).
  - `binding`: Uniform block binding index.
  - `offset`: Start byte offset (must be aligned to `GL_UNIFORM_BUFFER_OFFSET_ALIGNMENT`).
  - `size`: Size in bytes (`-1` for full buffer).
- `bind_to_storage_buffer(binding: int = 0, offset: int = 0, size: int = -1) -> None`
  - Binds the buffer to a Shader Storage Buffer Object (SSBO) binding point (OpenGL 4.3+).
  - `binding`: Storage buffer binding index.
  - `offset`: Start byte offset (must be aligned to `GL_SHADER_STORAGE_BUFFER_OFFSET_ALIGNMENT`).
  - `size`: Size in bytes (`-1` for full buffer).
- `bind(*attribs: str, layout: Optional[str] = None) -> Tuple[Buffer, Optional[str], str, ...]`
  - Helper returning a tuple designed for `Context.vertex_array()`.
  - Usage: `vbo.bind('in_pos', 'in_norm', layout='3f 3f')`.
- `assign(index: int) -> Tuple[Buffer, int]`
  - Helper returning `(self, index)` for `Context.scope(uniform_buffers=[...])`.
- `release() -> None`
  - Deletes the buffer from GPU memory and invalidates the object.

---

## 4. Class `VertexArray`

Binds vertex attributes from one or more `Buffer` objects to a shader `Program`, along with an optional index buffer and draw mode.

### Properties

- `mode: int` (get/set): The default primitive draw mode (e.g. `Context.TRIANGLES`, `Context.POINTS`).
- `program: Program` (read-only): The shader `Program` associated with this vertex array.
- `index_buffer: Optional[Buffer]` (read-only): The attached index/element buffer, or `None`.
- `index_element_size: int` (read-only): Index element size in bytes (`1`, `2`, or `4`).
- `vertices: int` (get/set): The default vertex count to render.
- `instances: int` (get/set): The default instance count to render.
- `subroutines: Tuple[int, ...]` (get/set): Tuple of subroutine uniform indices.
- `glo: int` (read-only): Raw OpenGL Vertex Array Object (VAO) integer handle.
- `label: Optional[str]` (get/set): Debug label.
- `ctx: Context` (read-only): The `Context` to which this vertex array belongs.
- `scope: Optional[Scope]` (get/set): Scope applied automatically during rendering.
- `extra: Any` (get/set): User metadata.

### Methods

- `render(mode: Optional[int] = None, vertices: int = -1, first: int = 0, instances: int = -1) -> None`
  - Issues a draw call (`glDrawArrays`, `glDrawElements`, `glDrawArraysInstanced`, or `glDrawElementsInstanced`).
  - `mode`: Primitive mode override (`TRIANGLES`, `LINES`, etc.). Default uses `self.mode`.
  - `vertices`: Number of vertices or indices to draw (`-1` uses all available vertices or index count).
  - `first`: Index of the first vertex or element to render.
  - `instances`: Number of instances to render (`-1` uses `self.instances` or 1).
- `render_indirect(buffer: Buffer, mode: Optional[int] = None, count: int = -1, first: int = 0) -> None`
  - Issues an indirect draw call (`glDrawArraysIndirect` or `glDrawElementsIndirect`).
  - `buffer`: `Buffer` containing draw commands (5 integers per command: `count`, `instanceCount`, `firstIndex`, `baseVertex`, `baseInstance`).
  - `mode`: Primitive mode override.
  - `count`: Number of indirect draw commands to execute (`-1` draws all).
  - `first`: Byte or structure offset of the first command.
- `transform(buffer: Union[Buffer, Sequence[Buffer]], mode: Optional[int] = None, vertices: int = -1, first: int = 0, instances: int = -1, buffer_offset: int = 0) -> None`
  - Executes a transform feedback pass, writing output vertices into `buffer` without rasterization.
  - `buffer`: Target output `Buffer` or sequence of `Buffer` objects.
  - `mode`: Transform primitive mode (default `POINTS`).
  - `vertices`: Number of vertices to transform (`-1` for all).
  - `first`: First vertex index.
  - `instances`: Instance count.
  - `buffer_offset`: Byte offset in output buffer.
- `bind(attribute: int, cls: str, buffer: Buffer, fmt: str, offset: int = 0, stride: int = 0, divisor: int = 0, normalize: bool = False) -> None`
  - Low-level binding of an individual vertex attribute location to a buffer.
  - `attribute`: Attribute location integer.
  - `cls`: Attribute type category: `'f'` (float), `'i'` (int), or `'d'` (double).
  - `buffer`: Source `Buffer`.
  - `fmt`: Format string (e.g. `'3f'`).
  - `offset`: Byte offset from buffer start.
  - `stride`: Stride between elements in bytes (0 for tightly packed).
  - `divisor`: Instancing divisor (`0` for per-vertex, `1` for per-instance).
  - `normalize`: Whether fixed-point values should be normalized to `[-1.0, 1.0]` or `[0.0, 1.0]`.
- `release() -> None`
  - Deletes the VAO handle from OpenGL.

---

## 5. Class `Program`

Represents a compiled and linked shader program. Uniforms, uniform blocks, storage blocks, and attributes are accessed via dictionary-like syntax.

### Properties

- `geometry_input: int` (read-only): Geometry shader input primitive type (`POINTS`, `LINES`, `TRIANGLES`, etc.).
- `geometry_output: int` (read-only): Geometry shader output primitive type (`POINTS`, `LINE_STRIP`, `TRIANGLE_STRIP`).
- `geometry_vertices: int` (read-only): Maximum output vertices declared by geometry shader (`layout(max_vertices=N)`).
- `is_transform: bool` (read-only): `True` if this is a transform feedback program (no fragment shader).
- `subroutines: Tuple[str, ...]` (read-only): Names of subroutines declared in the program.
- `glo: int` (read-only): Raw OpenGL program handle.
- `label: Optional[str]` (get/set): Debug label.
- `ctx: Context` (read-only): Parent context.
- `extra: Any` (get/set): User metadata.

### Methods & Operators

- `__getitem__(key: str) -> Union[Uniform, UniformBlock, StorageBlock, Attribute, Subroutine]`
  - Retrieves a named shader resource.
  - Example: `prog['u_view'].write(view_matrix)` or `prog['u_color'].value = (1.0, 0.0, 0.0, 1.0)`.
- `__setitem__(key: str, value: Any) -> None`
  - Shorthand assignment for uniform values.
  - Example: `prog['u_color'] = (1.0, 0.5, 0.2, 1.0)`.
- `__iter__() -> Iterator[str]`
  - Iterates over the names of all introspected members (uniforms, uniform blocks, storage blocks, attributes).
- `get(key: str, default: Any = None) -> Union[Uniform, UniformBlock, StorageBlock, Attribute, Subroutine, Any]`
  - Safe lookup returning `default` if `key` does not exist in the program.
- `release() -> None`
  - Deletes the shader program object from OpenGL.

### Associated Shader Member Types

- **`Uniform`**:
  - `uniform.value`: Get or set uniform value as Python primitive/tuple.
  - `uniform.write(data: Any)`: Write raw byte buffer into uniform (e.g. 4x4 matrix bytes).
  - `uniform.location: int`: OpenGL uniform location.
  - `uniform.dimension: int`: Vector/matrix dimension.
  - `uniform.array_length: int`: Array length (1 if not an array).
- **`UniformBlock`**:
  - `block.binding: int` (get/set): Assigned uniform buffer binding point index.
  - `block.size: int`: Total block size in bytes.
- **`StorageBlock`**:
  - `block.binding: int` (get/set): Assigned shader storage binding point index.
- **`Attribute`**:
  - `attrib.location: int`: Attribute location index.
  - `attrib.array_length: int`: Array length.
  - `attrib.dimension: int`: Vector component count.
  - `attrib.shape: str`: Data type character (`'f'`, `'i'`, `'u'`).

---

## 6. Class `Texture`

Represents a standard 2D OpenGL texture (`GL_TEXTURE_2D` or `GL_TEXTURE_2D_MULTISAMPLE`).

### Properties

- `size: Tuple[int, int]` (read-only): Width and height of the texture `(width, height)`.
- `width: int` (read-only): Width in pixels.
- `height: int` (read-only): Height in pixels.
- `components: int` (read-only): Number of color channels (`1` to `4`).
- `samples: int` (read-only): Number of MSAA samples (0 for non-multisampled).
- `depth: bool` (read-only): `True` if this is a depth texture.
- `dtype: str` (read-only): Data type string (`'f1'`, `'f2'`, `'f4'`, `'u1'`, `'u2'`, `'i4'`, etc.).
- `swizzle: str` (get/set): 4-character swizzle mask string (`'RGBA'`, `'BGRA'`, `'RRR1'`, etc.).
- `repeat_x: bool` (get/set): Wrap mode S (`True` for `GL_REPEAT`, `False` for `GL_CLAMP_TO_EDGE`).
- `repeat_y: bool` (get/set): Wrap mode T (`True` for `GL_REPEAT`, `False` for `GL_CLAMP_TO_EDGE`).
- `filter: Tuple[int, int]` (get/set): Minification and magnification filter tuple `(min_filter, mag_filter)`.
- `compare_func: str` (get/set): Shadow map comparison operator: `'<'`, `'<='`, `'=='`, `'!='`, `'>'`, `'>='`, `'never'`, `'always'`, or `'?'` (disabled).
- `anisotropy: float` (get/set): Anisotropic filtering factor (`1.0` to `ctx.max_anisotropy`).
- `glo: int` (read-only): Raw OpenGL texture integer ID.
- `label: Optional[str]` (get/set): Debug label.
- `ctx: Context` (read-only): Parent context.
- `extra: Any` (get/set): User metadata.

### Methods

- `use(location: int = 0) -> None`
  - Binds texture to the specified texture image unit `location`.
- `write(data: Any, viewport: Optional[Tuple[int, int, int, int]] = None, level: int = 0, alignment: int = 1) -> None`
  - Uploads pixel data to GPU texture memory (`glTexSubImage2D`).
  - `data`: Binary pixels (`bytes`, `bytearray`, `memoryview`, or a `Buffer` object).
  - `viewport`: Sub-rectangle `(x, y, width, height)` to update. `None` updates entire texture.
  - `level`: Mipmap level to write to (default `0`).
  - `alignment`: Byte row alignment (`1`, `2`, `4`, or `8`).
- `read(level: int = 0, alignment: int = 1) -> bytes`
  - Downloads pixel data from the GPU into a new `bytes` object.
  - `level`: Mipmap level to read.
  - `alignment`: Row byte alignment.
  - Returns `bytes`.
- `read_into(buffer: Union[bytearray, Buffer], level: int = 0, alignment: int = 1, write_offset: int = 0) -> None`
  - Reads pixel data directly into an existing `bytearray` or ModernGL `Buffer`.
- `build_mipmaps(base: int = 0, max_level: int = 1000) -> None`
  - Automatically generates mipmaps (`glGenerateMipmap`) and updates texture filter to `(LINEAR_MIPMAP_LINEAR, LINEAR)`.
- `bind_to_image(unit: int, read: bool = True, write: bool = True, level: int = 0, format: int = 0) -> None`
  - Binds texture to an image unit for compute shaders or image load/store (`glBindImageTexture`, OpenGL 4.2+).
- `get_handle(resident: bool = True) -> int`
  - Returns a 64-bit uint handle for ARB/NV bindless textures. Note: once a handle is created, texture parameters become immutable.
- `release() -> None`
  - Deletes the texture from GPU memory.

---

## 7. Class `TextureArray`

Represents an array of 2D images of identical dimensions and format (`GL_TEXTURE_2D_ARRAY`). Frequently used in voxel engines and tile systems to eliminate texture atlas bleeding.

### Properties

- `size: Tuple[int, int, int]` (read-only): `(width, height, layers)`.
- `width: int` (read-only): Width of each layer in pixels.
- `height: int` (read-only): Height of each layer in pixels.
- `layers: int` (read-only): Number of image layers.
- `components: int` (read-only): Channels per pixel (`1` to `4`).
- `dtype: str` (read-only): Data type string (`'f1'`, `'f2'`, `'f4'`, `'u1'`, `'i4'`, etc.).
- `swizzle: str` (get/set): 4-character swizzle mask (e.g. `'RGBA'`).
- `repeat_x: bool` (get/set): S-axis wrap mode (`True` for repeat, `False` for clamp).
- `repeat_y: bool` (get/set): T-axis wrap mode (`True` for repeat, `False` for clamp).
- `filter: Tuple[int, int]` (get/set): Minification and magnification filter `(min_filter, mag_filter)`.
- `anisotropy: float` (get/set): Anisotropic filtering level.
- `glo: int` (read-only): Raw OpenGL texture array handle.
- `label: Optional[str]` (get/set): Debug label.
- `ctx: Context` (read-only): Parent context.
- `extra: Any` (get/set): User metadata.

### Methods

- `use(location: int = 0) -> None`
  - Binds texture array to the specified texture unit `location`.
- `write(data: Any, viewport: Optional[Tuple[int, int, int, int, int, int]] = None, alignment: int = 1) -> None`
  - Uploads pixel data to the texture array.
  - `data`: Binary pixel data (`bytes`, `bytearray`, `memoryview`, or a `Buffer`). If full update, layers must be stacked vertically (i.e. size `(width, height * layers)`).
  - `viewport`: Optional 3D bounding box `(x, y, layer, width, height, num_layers)` to update.
  - `alignment`: Row byte alignment (`1`, `2`, `4`, or `8`).
- `read(alignment: int = 1) -> bytes`
  - Reads the entire texture array contents into system memory as `bytes`.
- `read_into(buffer: Union[bytearray, Buffer], alignment: int = 1, write_offset: int = 0) -> None`
  - Reads the entire texture array directly into a pre-allocated writable Python buffer or ModernGL `Buffer`.
- `build_mipmaps(base: int = 0, max_level: int = 1000) -> None`
  - Generates mipmap chain for all layers in the array.
- `bind_to_image(unit: int, read: bool = True, write: bool = True, level: int = 0, format: int = 0) -> None`
  - Binds the texture array to an image unit for compute/shader load-store.
- `get_handle(resident: bool = True) -> int`
  - Returns a 64-bit uint handle for bindless texture access.
- `release() -> None`
  - Deletes the texture array from GPU memory.

---

## 8. Buffer Formats and Data Types Reference

ModernGL uses concise format syntax for defining vertex buffers, texture dtypes, and uniform layouts.

### Common Type Characters
| Char | Description | ModernGL dtype | Typical Bytes |
| :--- | :--- | :--- | :--- |
| `f`  | 32-bit Float | `'f4'` | 4 |
| `f2` | 16-bit Half-Float | `'f2'` | 2 |
| `f8` | 64-bit Double | `'f8'` | 8 |
| `i`  | 32-bit Signed Int | `'i4'` | 4 |
| `i1` | 8-bit Signed Int | `'i1'` | 1 |
| `i2` | 16-bit Signed Int | `'i2'` | 2 |
| `u`  | 32-bit Unsigned Int | `'u4'` | 4 |
| `u1` | 8-bit Unsigned Int | `'u1'` | 1 |
| `u2` | 16-bit Unsigned Int | `'u2'` | 2 |
| `x`  | Padding / Skip Byte | N/A | 1 |

### Vertex Buffer Layout Syntax
- Format string specifies counts and types separated by spaces:
  - `'3f 2f'`: Vertex has 3 floats (`vec3`), followed by 2 floats (`vec2`). Stride = 20 bytes.
  - `'3f 3f 2f'`: Position (`vec3`), Normal (`vec3`), TexCoord (`vec2`). Stride = 32 bytes.
  - `'1u4 1u4'`: Two 32-bit unsigned integers (packed voxel/lighting data).
  - `'3f 12x 2f'`: 3 floats, skip 12 bytes, 2 floats.
- Instancing modifiers:
  - `/v`: Per-vertex attribute (default).
  - `/i` or `/r`: Per-instance attribute (divisor = 1).
  - Example: `(instance_vbo, '3f /i', 'in_instance_pos')`.

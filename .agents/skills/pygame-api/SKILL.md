---
name: pygame-api
description: API reference for pygame 2.6.1
---

# Pygame 2.6.1 API Reference

This skill document serves as the exact reference manual for the core modules of **Pygame 2.6.1**, focusing specifically on:
- `pygame.display` — Display window, screen modes, surfaces, and OpenGL attributes
- `pygame.event` — Event queue management, posting, filtering, and event types
- `pygame.time` — Frame timing, delays, ticks, and the `Clock` utility
- `pygame.mouse` — Mouse position, button states, relative motion, visibility, and cursors

---

## 1. `pygame.display`

The `pygame.display` module controls the display window and screen. Pygame maintains a single display Surface that can be windowed or fullscreen.

### Functions

#### `pygame.display.init() -> None`
- **Summary**: Initializes the pygame display module.
- **Parameters**: None.
- **Returns**: `None`.
- **Notes**: Usually called automatically by `pygame.init()`. Can be called multiple times safely.

#### `pygame.display.quit() -> None`
- **Summary**: Uninitializes the pygame display module and closes any open display windows.
- **Parameters**: None.
- **Returns**: `None`.
- **Notes**: Automatically called when Python exits. Can be called multiple times safely.

#### `pygame.display.get_init() -> bool`
- **Summary**: Checks whether the display module has been initialized.
- **Parameters**: None.
- **Returns**: `bool` — `True` if initialized, `False` otherwise.

#### `pygame.display.set_mode(size=(0, 0), flags=0, depth=0, display=0, vsync=0) -> Surface`
- **Summary**: Initializes a window or screen for display.
- **Parameters**:
  - `size` (`tuple[int, int]` or `list[int]`): `(width, height)` in pixels. If `(0, 0)` is passed, defaults to the current desktop resolution.
  - `flags` (`int`): Bitwise OR of display flags (e.g. `pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE`).
  - `depth` (`int`): Color depth in bits per pixel. Defaults to `0` (system recommended/native color depth).
  - `display` (`int`): Index of display monitor to use (0 is the primary display).
  - `vsync` (`int`): Request vertical synchronization (`1` to enable, `0` to disable). Supported with `pygame.OPENGL` or `pygame.SCALED`.
- **Returns**: `pygame.Surface` — The display surface.
- **Notes**: Implicitly calls `pygame.display.init()` if not already initialized.

#### `pygame.display.get_surface() -> Surface | None`
- **Summary**: Gets a reference to the currently active display Surface.
- **Parameters**: None.
- **Returns**: `pygame.Surface` if a display mode is set; `None` if no display mode has been set.

#### `pygame.display.flip() -> None`
- **Summary**: Updates the full display Surface to the screen.
- **Parameters**: None.
- **Returns**: `None`.
- **Notes**: When using `pygame.OPENGL` or hardware double-buffering, this performs the buffer swap.

#### `pygame.display.update(rectangle=None) -> None`
#### `pygame.display.update(rectangle_list) -> None`
- **Summary**: Updates portions of the screen for software displays (does not apply to OpenGL displays).
- **Parameters**:
  - `rectangle` (`Rect` or `tuple[int, int, int, int]` or `None`): Single rectangle to update. If `None`, updates the entire screen (like `flip()`).
  - `rectangle_list` (`list[Rect]`): Collection of rectangles to update.
- **Returns**: `None`.

#### `pygame.display.get_driver() -> str`
- **Summary**: Gets the name of the pygame display backend (e.g. `'windows'`, `'x11'`, `'cocoa'`).
- **Parameters**: None.
- **Returns**: `str` — Name of the display driver.

#### `pygame.display.Info() -> VideoInfo`
- **Summary**: Generates a video display information object describing the current display system.
- **Parameters**: None.
- **Returns**: `VideoInfo` object containing display attributes:
  - `hw` (`int`): 1 if hardware acceleration is supported.
  - `wm` (`int`): 1 if window manager is available.
  - `video_mem` (`int`): Kilobytes of display memory (0 if unknown).
  - `bitsize` (`int`): Number of bits per pixel.
  - `bytesize` (`int`): Number of bytes per pixel.
  - `masks` (`tuple[int, int, int, int]`): Bitmasks for RGBA channels.
  - `shifts` (`tuple[int, int, int, int]`): Bit shifts for RGBA channels.
  - `losses` (`tuple[int, int, int, int]`): Loss bits for RGBA channels.
  - `current_w` (`int`): Current display width.
  - `current_h` (`int`): Current display height.
  - `pixel_format` (`str`): Pixel format string (e.g. `'PIXELFORMAT_ARGB8888'`).

#### `pygame.display.get_wm_info() -> dict`
- **Summary**: Gets information about the current windowing system.
- **Parameters**: None.
- **Returns**: `dict` containing system-dependent window handles:
  - Windows: `{'window': HWND, 'hinstance': HINSTANCE}`
  - Linux/X11: `{'display': Display, 'window': Window}`

#### `pygame.display.get_desktop_sizes() -> list[tuple[int, int]]`
- **Summary**: Returns a list of `(width, height)` resolutions for all active desktops/monitors.
- **Parameters**: None.
- **Returns**: `list[tuple[int, int]]`.

#### `pygame.display.list_modes(depth=0, flags=pygame.FULLSCREEN, display=0) -> list[tuple[int, int]] | int`
- **Summary**: Queries the list of available fullscreen resolutions.
- **Parameters**:
  - `depth` (`int`): Color depth in bits.
  - `flags` (`int`): Surface flags (defaults to `pygame.FULLSCREEN`).
  - `display` (`int`): Display monitor index.
- **Returns**: List of `(w, h)` tuples sorted from largest to smallest, or `-1` if any resolution is supported.

#### `pygame.display.mode_ok(size, flags=0, depth=0, display=0) -> int`
- **Summary**: Tests if a requested display mode is supported, and returns the closest color depth.
- **Parameters**:
  - `size` (`tuple[int, int]`): Resolution `(w, h)`.
  - `flags` (`int`): Display flags.
  - `depth` (`int`): Desired bit depth.
  - `display` (`int`): Display index.
- **Returns**: `int` — Best color depth (bits per pixel), or `0` if mode cannot be set.

#### `pygame.display.gl_get_attribute(flag) -> int`
- **Summary**: Gets the value of an OpenGL context attribute for the current display.
- **Parameters**:
  - `flag` (`int`): An OpenGL flag constant (e.g. `pygame.GL_MULTISAMPLESAMPLES`).
- **Returns**: `int` — Attribute value.

#### `pygame.display.gl_set_attribute(flag, value) -> None`
- **Summary**: Requests an OpenGL attribute value to take effect upon the next `pygame.display.set_mode()` call.
- **Parameters**:
  - `flag` (`int`): An OpenGL flag constant (e.g. `pygame.GL_CONTEXT_MAJOR_VERSION`).
  - `value` (`int`): Value to assign.
- **Returns**: `None`.

#### `pygame.display.get_active() -> bool`
- **Summary**: Returns whether the active display surface is visible and not iconified.
- **Parameters**: None.
- **Returns**: `bool` — `True` if visible / active on screen.

#### `pygame.display.iconify() -> bool`
- **Summary**: Minimizes the window into an icon / taskbar.
- **Parameters**: None.
- **Returns**: `bool` — `True` if successful.

#### `pygame.display.toggle_fullscreen() -> int`
- **Summary**: Toggles the display window between fullscreen and windowed modes.
- **Parameters**: None.
- **Returns**: `int` — `1` on success, `0` on failure.

#### `pygame.display.set_gamma(red, green=None, blue=None) -> bool`
- **Summary**: Changes the hardware gamma ramps on the display.
- **Parameters**:
  - `red` (`float`): Gamma factor for red channel (or all channels if green and blue are omitted).
  - `green` (`float | None`): Gamma factor for green channel.
  - `blue` (`float | None`): Gamma factor for blue channel.
- **Returns**: `bool` — `True` on success.

#### `pygame.display.set_gamma_ramp(red, green, blue) -> bool`
- **Summary**: Sets custom hardware lookup gamma ramps.
- **Parameters**:
  - `red`, `green`, `blue`: Sequences of 256 16-bit integers (0 to 65535).
- **Returns**: `bool` — `True` on success.

#### `pygame.display.set_icon(Surface) -> None`
- **Summary**: Sets the system icon for the display window.
- **Parameters**:
  - `Surface` (`pygame.Surface`): Small image (typically 32x32) to use as window icon.
- **Returns**: `None`.

#### `pygame.display.set_caption(title, icontitle=None) -> None`
- **Summary**: Sets the title caption for the display window.
- **Parameters**:
  - `title` (`str`): Window title bar string.
  - `icontitle` (`str | None`): Short title when window is iconified (defaults to `title`).
- **Returns**: `None`.

#### `pygame.display.get_caption() -> tuple[str, str]`
- **Summary**: Gets the current window title and icon title.
- **Parameters**: None.
- **Returns**: `tuple[str, str]` — `(title, icontitle)`.

#### `pygame.display.set_palette(palette=None) -> None`
- **Summary**: Changes the display palette for 8-bit indexed displays.
- **Parameters**:
  - `palette` (`sequence[Color]`): List of RGB colors.
- **Returns**: `None`.

#### `pygame.display.get_num_displays() -> int`
- **Summary**: Returns the count of attached and active monitors/displays.
- **Parameters**: None.
- **Returns**: `int` — Number of displays.

#### `pygame.display.get_window_size() -> tuple[int, int]`
- **Summary**: Returns the current dimensions of the active window or screen.
- **Parameters**: None.
- **Returns**: `tuple[int, int]` — `(width, height)`.

#### `pygame.display.get_allow_screensaver() -> bool`
- **Summary**: Checks whether the operating system screensaver is allowed to run while the game is running.
- **Parameters**: None.
- **Returns**: `bool` (default is `False`).

#### `pygame.display.set_allow_screensaver(bool) -> None`
- **Summary**: Enables or disables the system screensaver while pygame is active.
- **Parameters**:
  - `bool` (`bool`): `True` to allow screensaver, `False` to suppress it.
- **Returns**: `None`.

### Display Constants & Flags

#### Window & Surface Mode Flags
- `pygame.FULLSCREEN`: Creates a fullscreen display.
- `pygame.DOUBLEBUF`: Enables double-buffering (recommended with `OPENGL`).
- `pygame.HWSURFACE`: Obsolete in pygame 2.
- `pygame.OPENGL`: Creates an OpenGL-compatible rendering context.
- `pygame.RESIZABLE`: Allows the window to be resized by the user.
- `pygame.NOFRAME`: Creates a borderless window without title bar or frame.
- `pygame.SCALED`: Automatically scales resolution based on desktop size.
- `pygame.SHOWN`: Opens window in visible mode (default).
- `pygame.HIDDEN`: Opens window in hidden mode.

#### OpenGL Attributes (`gl_set_attribute` / `gl_get_attribute`)
- `pygame.GL_RED_SIZE`: Bit depth of red channel (default: 3).
- `pygame.GL_GREEN_SIZE`: Bit depth of green channel (default: 3).
- `pygame.GL_BLUE_SIZE`: Bit depth of blue channel (default: 2).
- `pygame.GL_ALPHA_SIZE`: Bit depth of alpha channel (default: 0).
- `pygame.GL_BUFFER_SIZE`: Total frame buffer size in bits (default: 0).
- `pygame.GL_DOUBLEBUFFER`: Enable double buffering (0 or 1, default: 1).
- `pygame.GL_DEPTH_SIZE`: Depth buffer (Z-buffer) bit precision (default: 16).
- `pygame.GL_STENCIL_SIZE`: Stencil buffer bit precision (default: 0).
- `pygame.GL_ACCUM_RED_SIZE`, `GL_ACCUM_GREEN_SIZE`, `GL_ACCUM_BLUE_SIZE`, `GL_ACCUM_ALPHA_SIZE`: Accumulation buffer sizes.
- `pygame.GL_STEREO`: Stereo 3D rendering (0 or 1, default: 0).
- `pygame.GL_MULTISAMPLEBUFFERS`: Enable MSAA buffers (0 or 1).
- `pygame.GL_MULTISAMPLESAMPLES`: MSAA sample count (e.g. 2, 4, 8).
- `pygame.GL_ACCELERATED_VISUAL`: Enforce hardware acceleration (1 for hardware, 0 for software).
- `pygame.GL_CONTEXT_MAJOR_VERSION`: OpenGL major version (e.g. 3, 4).
- `pygame.GL_CONTEXT_MINOR_VERSION`: OpenGL minor version (e.g. 3).
- `pygame.GL_CONTEXT_PROFILE_MASK`: Set OpenGL profile:
  - `pygame.GL_CONTEXT_PROFILE_CORE`: Core profile without deprecated APIs.
  - `pygame.GL_CONTEXT_PROFILE_COMPATIBILITY`: Compatibility profile.
  - `pygame.GL_CONTEXT_PROFILE_ES`: Embedded systems profile.
- `pygame.GL_CONTEXT_FLAGS`:
  - `pygame.GL_CONTEXT_DEBUG_FLAG`: Enables GL debug context.
  - `pygame.GL_CONTEXT_FORWARD_COMPATIBLE_FLAG`: Enables forward compatibility.
- `pygame.GL_SHARE_WITH_GLOBAL_CONTEXT`: Share context globally (0 or 1).
- `pygame.GL_FRAMEBUFFER_SRGB_CAPABLE`: Request sRGB-capable default framebuffer (0 or 1).

---

## 2. `pygame.event`

The `pygame.event` module handles the event queue, processing user inputs (mouse, keyboard, controller, touch) and window events.

### Functions

#### `pygame.event.pump() -> None`
- **Summary**: Internally processes and updates the pygame event handlers.
- **Parameters**: None.
- **Returns**: `None`.
- **Notes**: Must be called frequently (usually once per frame, handled automatically by `pygame.event.get()`). If not called, the OS will flag the window as unresponsive ("Not Responding").

#### `pygame.event.get(eventtype=None, pump=True, exclude=None) -> list[Event]`
- **Summary**: Retrieves pending events from the queue and removes them.
- **Parameters**:
  - `eventtype` (`int | sequence[int] | None`): Specific event type(s) to fetch. If `None`, fetches all events.
  - `pump` (`bool`): Whether to call `pygame.event.pump()` before fetching (defaults to `True`).
  - `exclude` (`int | sequence[int] | None`): Specific event type(s) to leave on the queue.
- **Returns**: `list[pygame.event.Event]`.

#### `pygame.event.poll() -> Event`
- **Summary**: Retrieves a single event from the queue and removes it.
- **Parameters**: None.
- **Returns**: `pygame.event.Event` — Next event from queue, or an event with `type == pygame.NOEVENT` if empty.

#### `pygame.event.wait(timeout=0) -> Event`
- **Summary**: Waits for a single event to arrive on the queue.
- **Parameters**:
  - `timeout` (`int`): Maximum milliseconds to wait. `0` means wait indefinitely.
- **Returns**: `pygame.event.Event` — Arrived event, or `pygame.NOEVENT` if timeout expires.

#### `pygame.event.peek(eventtype=None, pump=True) -> bool`
- **Summary**: Tests if specified event types are waiting in the queue without removing them.
- **Parameters**:
  - `eventtype` (`int | sequence[int] | None`): Event type or collection of types to check. If `None`, checks if any event is waiting.
  - `pump` (`bool`): Whether to call `pump()` first (default `True`).
- **Returns**: `bool` — `True` if any matching event is present.

#### `pygame.event.clear(eventtype=None, pump=True) -> None`
- **Summary**: Clears and discards all or specified events from the queue.
- **Parameters**:
  - `eventtype` (`int | sequence[int] | None`): Type(s) to clear. If `None`, clears all events.
  - `pump` (`bool`): Whether to call `pump()` first (default `True`).
- **Returns**: `None`.

#### `pygame.event.event_name(type) -> str`
- **Summary**: Converts a numeric event type ID to its string representation (e.g. `pygame.QUIT` -> `"Quit"`).
- **Parameters**:
  - `type` (`int`): Event type identifier.
- **Returns**: `str` — Name of the event.

#### `pygame.event.set_blocked(type) -> None`
- **Summary**: Prevents specific event types from appearing on the queue. Blocked events are dropped immediately.
- **Parameters**:
  - `type` (`int | sequence[int] | None`): Event type(s) to block. If `None`, all events are blocked.
- **Returns**: `None`.

#### `pygame.event.set_allowed(type) -> None`
- **Summary**: Re-enables event types that were previously blocked.
- **Parameters**:
  - `type` (`int | sequence[int] | None`): Event type(s) to allow. If `None`, all events are allowed.
- **Returns**: `None`.

#### `pygame.event.get_blocked(type) -> bool`
- **Summary**: Tests if a specific event type is currently blocked.
- **Parameters**:
  - `type` (`int`): Event type ID.
- **Returns**: `bool` — `True` if blocked from the queue.

#### `pygame.event.set_grab(bool) -> None`
- **Summary**: Locks all mouse and keyboard input exclusively to the pygame window.
- **Parameters**:
  - `bool` (`bool`): `True` to grab input, `False` to release.
- **Returns**: `None`.

#### `pygame.event.get_grab() -> bool`
- **Summary**: Checks whether input grab is currently active.
- **Parameters**: None.
- **Returns**: `bool` — `True` if input is grabbed.

#### `pygame.event.set_keyboard_grab(bool) -> None`
- **Summary**: Enables capture of system keyboard shortcuts (such as Alt+Tab or Meta/Super key).
- **Parameters**:
  - `bool` (`bool`): `True` to grab keyboard shortcuts.
- **Returns**: `None`.

#### `pygame.event.get_keyboard_grab() -> bool`
- **Summary**: Checks whether system keyboard shortcuts are currently grabbed.
- **Parameters**: None.
- **Returns**: `bool`.

#### `pygame.event.post(Event) -> bool`
- **Summary**: Places a new event object at the end of the event queue.
- **Parameters**:
  - `Event` (`pygame.event.Event`): Event instance to post.
- **Returns**: `bool` — `True` on success, `False` if blocked or queue full.

#### `pygame.event.custom_type() -> int`
- **Summary**: Allocates a unique custom event ID starting above `pygame.USEREVENT`.
- **Parameters**: None.
- **Returns**: `int` — A new unique event type integer.

### Class `pygame.event.Event`

Object representing a discrete user or system event.

#### Constructors
- `pygame.event.Event(type, dict=None, **attributes) -> Event`
- `pygame.event.Event(type, **attributes) -> Event`

#### Attributes
- `event.type` (`int`): Event type constant identifier (e.g. `pygame.KEYDOWN`, `pygame.QUIT`).
- `event.__dict__` (`dict`): Dictionary of event attributes.
- Dynamic attributes can be accessed directly on the event instance (e.g. `event.key`, `event.pos`, `event.button`).

### Standard Event Types and Attributes Table

| Event Constant | Attributes Available | Description |
|---|---|---|
| `pygame.QUIT` | `none` | User clicked close button or requested window exit |
| `pygame.ACTIVEEVENT` | `gain`, `state` | Window focus or iconify state changed |
| `pygame.KEYDOWN` | `key`, `mod`, `unicode`, `scancode`, `window` | Keyboard key pressed down |
| `pygame.KEYUP` | `key`, `mod`, `unicode`, `scancode`, `window` | Keyboard key released |
| `pygame.MOUSEMOTION` | `pos`, `rel`, `buttons`, `touch`, `window` | Mouse moved (`pos=(x, y)`, `rel=(dx, dy)`) |
| `pygame.MOUSEBUTTONDOWN`| `pos`, `button`, `touch`, `window` | Mouse button pressed (`button`: 1=L, 2=M, 3=R) |
| `pygame.MOUSEBUTTONUP` | `pos`, `button`, `touch`, `window` | Mouse button released |
| `pygame.MOUSEWHEEL` | `which`, `flipped`, `x`, `y`, `touch`, `window`, `precise_x`, `precise_y` | Mouse wheel scrolled (`y > 0`: up, `y < 0`: down) |
| `pygame.JOYAXISMOTION` | `joy`, `axis`, `value`, `instance_id` | Joystick axis moved (-1.0 to 1.0) |
| `pygame.JOYBALLMOTION` | `joy`, `ball`, `rel`, `instance_id` | Trackball moved |
| `pygame.JOYHATMOTION` | `joy`, `hat`, `value`, `instance_id` | Joystick D-pad/POV hat moved |
| `pygame.JOYBUTTONDOWN` | `joy`, `button`, `instance_id` | Joystick button pressed |
| `pygame.JOYBUTTONUP` | `joy`, `button`, `instance_id` | Joystick button released |
| `pygame.VIDEORESIZE` | `size`, `w`, `h` | Window resized (`size=(w, h)`) |
| `pygame.VIDEOEXPOSE` | `none` | Window portion uncovered / needs redraw |
| `pygame.USEREVENT` | `code`, ... (custom) | User-defined event base constant |
| `pygame.DROPFILE` | `file`, `window` | File dropped onto window (`file`: path string) |
| `pygame.DROPBEGIN` | `window` | Drag and drop operation started |
| `pygame.DROPCOMPLETE` | `window` | Drag and drop operation completed |
| `pygame.DROPTEXT` | `text`, `window` | Text snippet dropped onto window |
| `pygame.TEXTINPUT` | `text`, `window` | Text input event (IME / Unicode text input) |
| `pygame.TEXTEDITING` | `text`, `start`, `length`, `window` | IME composition string updated |
| `pygame.WINDOWSHOWN` | `window` | Window became visible |
| `pygame.WINDOWHIDDEN` | `window` | Window was hidden |
| `pygame.WINDOWEXPOSED`| `window` | Window exposed |
| `pygame.WINDOWMOVED` | `x`, `y`, `window` | Window moved |
| `pygame.WINDOWRESIZED`| `x`, `y`, `window` | Window resized |
| `pygame.WINDOWSIZECHANGED`| `x`, `y`, `window` | Window size changed internally |
| `pygame.WINDOWMINIMIZED`| `window` | Window minimized |
| `pygame.WINDOWMAXIMIZED`| `window` | Window maximized |
| `pygame.WINDOWRESTORED`| `window` | Window restored from minimized/maximized |
| `pygame.WINDOWENTER` | `window` | Mouse cursor entered window |
| `pygame.WINDOWLEAVE` | `window` | Mouse cursor left window |
| `pygame.WINDOWFOCUSGAINED`| `window` | Window gained keyboard input focus |
| `pygame.WINDOWFOCUSLOST`| `window` | Window lost keyboard input focus |
| `pygame.WINDOWCLOSE` | `window` | Window close requested |

---

## 3. `pygame.time`

The `pygame.time` module manages time, frame rates, delays, and recurring timers.

### Functions

#### `pygame.time.get_ticks() -> int`
- **Summary**: Gets the number of milliseconds elapsed since `pygame.init()` was called.
- **Parameters**: None.
- **Returns**: `int` — Elapsed time in milliseconds.

#### `pygame.time.wait(milliseconds) -> int`
- **Summary**: Pauses the current thread for the specified duration using the OS sleep facility (shares the CPU with other processes).
- **Parameters**:
  - `milliseconds` (`int`): Time to pause in milliseconds.
- **Returns**: `int` — Actual number of milliseconds spent sleeping.

#### `pygame.time.delay(milliseconds) -> int`
- **Summary**: Pauses the current thread using a high-precision busy loop.
- **Parameters**:
  - `milliseconds` (`int`): Time to pause in milliseconds.
- **Returns**: `int` — Actual number of milliseconds spent delaying.
- **Notes**: Uses more processor power than `wait()`, but provides sub-millisecond precision for tight game loops.

#### `pygame.time.set_timer(event, millis, loops=0) -> None`
- **Summary**: Repeatedly posts an event to the pygame event queue at a fixed millisecond interval.
- **Parameters**:
  - `event` (`int | pygame.event.Event`): Event ID or `Event` instance to post.
  - `millis` (`int`): Interval in milliseconds. If set to `0`, stops the active timer.
  - `loops` (`int`): Number of times to fire the timer (pygame >= 2.0.0). `0` (default) means repeat indefinitely.
- **Returns**: `None`.

### Class `pygame.time.Clock`

Controls game loop pacing, frame rate clamping, and delta-time measurement.

#### Constructor
- `pygame.time.Clock() -> Clock`

#### Methods
- `Clock.tick(framerate=0) -> int`
  - Clamps the frame rate so that no more than `framerate` frames occur per second. If `framerate=0`, does not cap the frame rate.
  - Returns the elapsed time in milliseconds since the previous call to `tick()`.
- `Clock.tick_busy_loop(framerate=0) -> int`
  - Same as `tick()`, but uses a busy loop for more accurate delay timing at the expense of higher CPU usage.
  - Returns elapsed milliseconds since previous tick.
- `Clock.get_time() -> int`
  - Returns the duration in milliseconds passed between the last two calls to `tick()`.
- `Clock.get_rawtime() -> int`
  - Returns the time in milliseconds spent during the frame execution itself (excluding any sleep/wait time added by `tick()`).
- `Clock.get_fps() -> float`
  - Computes the running average frame rate over the past ten calls to `tick()`.

---

## 4. `pygame.mouse`

The `pygame.mouse` module provides functions to query the real-time mouse cursor position, button states, visibility, and system cursors.

### Functions

#### `pygame.mouse.get_pressed(num_buttons=3) -> tuple[bool, ...]`
- **Summary**: Queries the current held-down state of mouse buttons.
- **Parameters**:
  - `num_buttons` (`int`): Number of buttons to inspect: `3` (default) or `5`.
- **Returns**:
  - If `num_buttons=3`: `tuple[bool, bool, bool]` representing `(left, middle, right)`.
  - If `num_buttons=5`: `tuple[bool, bool, bool, bool, bool]` representing `(left, middle, right, x1, x2)`.
- **Notes**: Returns real-time state at the moment of call, unlike `pygame.MOUSEBUTTONDOWN` events.

#### `pygame.mouse.get_pos() -> tuple[int, int]`
- **Summary**: Gets the current `(x, y)` coordinates of the mouse cursor relative to the pygame window.
- **Parameters**: None.
- **Returns**: `tuple[int, int]` — `(x, y)` in window pixels.

#### `pygame.mouse.get_rel() -> tuple[int, int]`
- **Summary**: Gets the relative movement `(dx, dy)` of the mouse cursor since the previous call to `get_rel()`.
- **Parameters**: None.
- **Returns**: `tuple[int, int]` — `(dx, dy)` pixel offset.

#### `pygame.mouse.set_pos(pos) -> None`
- **Summary**: Warps the mouse cursor to a specific coordinate within the display window.
- **Parameters**:
  - `pos` (`tuple[int, int]` or `list[int]`): Target `(x, y)` position.
- **Returns**: `None`.
- **Notes**: Generates a `pygame.MOUSEMOTION` event.

#### `pygame.mouse.set_visible(bool) -> bool`
- **Summary**: Hides or displays the mouse cursor on screen.
- **Parameters**:
  - `bool` (`bool`): `True` to show cursor, `False` to hide it.
- **Returns**: `bool` — Previous visibility state of the cursor.

#### `pygame.mouse.get_visible() -> bool`
- **Summary**: Returns whether the mouse cursor is currently visible.
- **Parameters**: None.
- **Returns**: `bool` — `True` if visible, `False` if hidden.

#### `pygame.mouse.get_focused() -> bool`
- **Summary**: Checks whether the pygame display window is currently receiving mouse input (mouse focus).
- **Parameters**: None.
- **Returns**: `bool` — `True` if display has mouse focus.

#### `pygame.mouse.set_cursor(cursor) -> None`
#### `pygame.mouse.set_cursor(size, hotspot, xormasks, andmasks) -> None`
#### `pygame.mouse.set_cursor(hotspot, surface) -> None`
#### `pygame.mouse.set_cursor(constant) -> None`
- **Summary**: Sets the active mouse cursor appearance.
- **Parameters**:
  - `cursor`: A `pygame.cursors.Cursor` instance.
  - Or `size, hotspot, xormasks, andmasks`: Legacy bitmap cursor specification.
  - Or `hotspot, surface`: Color cursor created from a Surface with `hotspot=(x, y)`.
  - Or `constant`: A system cursor constant (e.g. `pygame.SYSTEM_CURSOR_CROSSHAIR`).
- **Returns**: `None`.

#### `pygame.mouse.get_cursor() -> pygame.cursors.Cursor`
- **Summary**: Retrieves the currently active `pygame.cursors.Cursor` object.
- **Parameters**: None.
- **Returns**: `pygame.cursors.Cursor`.

### Mouse & Cursor Constants

#### System Cursor Constants
- `pygame.SYSTEM_CURSOR_ARROW`: Standard arrow cursor.
- `pygame.SYSTEM_CURSOR_IBEAM`: Text insertion bar (I-beam).
- `pygame.SYSTEM_CURSOR_WAIT`: Hourglass or spinning circle wait cursor.
- `pygame.SYSTEM_CURSOR_CROSSHAIR`: Crosshair precision cursor.
- `pygame.SYSTEM_CURSOR_WAITARROW`: Combined arrow and small wait indicator.
- `pygame.SYSTEM_CURSOR_SIZENWSE`: Double-headed diagonal resize cursor (top-left to bottom-right).
- `pygame.SYSTEM_CURSOR_SIZENESW`: Double-headed diagonal resize cursor (top-right to bottom-left).
- `pygame.SYSTEM_CURSOR_SIZEWE`: Double-headed horizontal resize cursor (west to east).
- `pygame.SYSTEM_CURSOR_SIZENS`: Double-headed vertical resize cursor (north to south).
- `pygame.SYSTEM_CURSOR_SIZEALL`: Four-way directional resize/pan cursor.
- `pygame.SYSTEM_CURSOR_NO`: Slashed circle "not allowed" cursor.
- `pygame.SYSTEM_CURSOR_HAND`: Pointing hand link/selection cursor.

#### Mouse Button Numbers (in Event.button)
- `1`: Left mouse button
- `2`: Middle mouse button
- `3`: Right mouse button
- `4`: Mouse wheel scroll up (in legacy SDL1; in SDL2/Pygame 2 use `pygame.MOUSEWHEEL`)
- `5`: Mouse wheel scroll down (in legacy SDL1; in SDL2/Pygame 2 use `pygame.MOUSEWHEEL`)
- `6`: X1 extra mouse thumb button
- `7`: X2 extra mouse thumb button

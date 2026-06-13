.. _main-engine:

================
Core Engine Flow
================

This document describes the runtime flow of the Pyrite engine, focusing on how the application initializes, updates, and renders each frame. It is intended as a system-level guide rather than a line-by-line walkthrough of ``main.py``.

Engine Initialization
---------------------

Pyrite boots by constructing a fullscreen OpenGL context and then initializing all major subsystems. The startup sequence is designed so that the render thread can remain responsive while heavier tasks are deferred or executed in background queues.

* **Multimedia & Context:** Initializes Pygame and configures a hardware-accelerated ModernGL context. It requests a core OpenGL profile with depth testing, face culling, and alpha blending enabled.
* **Configuration Management:** Loads user preferences from a local ``config.json`` file and merges them with defaults. Current configurable values include ``fov``, ``sensitivity``, ``volume``, ``render_distance``, and ``underwater_tint``.
* **Subsystem Instantiation:** Bootstraps all major managers and systems:

  * ``Textures``: Loads and binds image assets to the GPU.
  * ``Player``: Initializes the physics and camera entity.
  * ``Sounds``: Interfaces with the Pygame audio mixer.
  * ``ShaderProgram``: Compiles and manages GLSL shaders.
  * ``UI``: Prepares all interactive menus (Main Menu, Pause, Options).

State Management
----------------

Pyrite operates using a robust finite state machine to delegate logic and rendering. The active state is stored in ``self.game_state`` and seamlessly transitions between the following modes:

* ``MAIN_MENU``: The front-end title screen and world selection interface.
* ``LOADING``: A blocking transition state that flushes the event queue while heavy procedural generation and async database reads occur.
* ``IN_GAME``: The active 3D voxel simulation, handing control over to the ``Scene`` and ``Player`` instances.
* ``INVENTORY``: Pauses player movement and frees the mouse cursor to allow for drag-and-drop item management.
* ``PAUSED``: Suspends background logic and draws a darkened UI overlay, allowing players to adjust settings or exit the session.
* ``OPTIONS``: Renders the configuration sliders, saving changes to disk upon exit.

World Generation and Sessions
-----------------------------

When a player selects a world, ``init_game_session()`` is invoked. This process ensures a clean environment by:

1. **Seeding:** Retrieving an existing seed from the SQLite database or generating a fresh procedural seed.
2. **Instantiating the Scene:** Constructing a new ``Scene`` and ``World`` object.
3. **Pre-loading:** Engaging a blocking loop that forces initial chunks to load, build, and mesh.
4. **Safety Flushing:** Discarding buffered inputs and relative mouse movements to prevent sudden camera snapping when the game begins.

During this phase, a minimal ``render_loading_screen()`` UI overlay is repeatedly drawn to prevent the operating system from flagging the application as unresponsive.

The Main Loop
-------------

The core execution cycle is governed by the ``run()`` method. Until the application halts, it continuously cycles through three primary stages:

1. **Event Polling** (``handle_events``): Intercepts raw OS hardware events (mouse clicks, key presses, window closes). It delegates these events dynamically based on the current ``game_state`` (e.g., passing WASD inputs to the Player in-game, or slider drags to the Options Menu).
2. **Logic Updates** (``update``): Advances internal systems. This increments the ``world_session_time``, processes physics boundaries, and evaluates UI animations. Delta time is strictly capped to prevent extreme physics desynchronization during performance spikes.
3. **Rendering** (``render``): Clears the hardware frame buffer and dispatches draw calls. If in a menu, it disables depth testing to draw 2D quads. If in-game, it directs the ``Scene`` to perform its complex multi-pass rendering pipeline.

Application Control
-------------------

Safely exiting the application is handled by the ``quit_game()`` sequence. It breaks the main execution loop, triggers the world to synchronously serialize all remaining chunks to the SQLite database, and cleanly releases multimedia hardware handles back to the OS.

Detailed Initialization Sequence
---------------------------------

**Step-by-Step Pyrite Startup:**

Pyrite boots by creating a fullscreen OpenGL context, then layering the engine subsystems on top of it. The actual source initializes a fixed fullscreen window using the current desktop resolution, and the configuration file is only used for gameplay options that affect camera, audio, and render streaming.

The key startup stages are:

1. Initialize Pygame and request an OpenGL 3.3 core context.
2. Create a fullscreen window at the current desktop resolution.
3. Create a ModernGL context and enable depth testing, face culling, and blending.
4. Initialize the frame clock and engine timers.
5. Load default configuration values, then override them from ``config.json``.
6. Initialize the texture atlas, shader pipeline, and audio mixer.
7. Instantiate the player, the menu system, and the main game state container.

The configuration keys currently supported are:

- ``fov``: Vertical field of view in degrees.
- ``sensitivity``: Mouse look sensitivity.
- ``volume``: Global sound volume.
- ``render_distance``: Number of chunks loaded around the player.
- ``underwater_tint``: Whether a blue tint is applied underwater.

Detailed State Machine
----------------------

**State Transitions and Logic:**

.. mermaid::

   stateDiagram-v2

      direction LR

      GameOpens --> MAIN_MENU

      MAIN_MENU --> LOADING : Play (world selected)
      MAIN_MENU --> OPTIONS : Settings
      MAIN_MENU --> GameCloses : Quit

      state LOADING {
         [*] --> GenerateChunks
         GenerateChunks --> CompileNumba
         CompileNumba --> Ready
      }

      LOADING --> IN_GAME : Ready

      IN_GAME --> PAUSED : ESC
      IN_GAME --> INVENTORY : E

      INVENTORY --> IN_GAME : E

      PAUSED --> IN_GAME : Resume
      PAUSED --> OPTIONS : Settings
      PAUSED --> MAIN_MENU : Quit to Main Menu

      OPTIONS --> MAIN_MENU : Exit
      OPTIONS --> PAUSED : Exit (from pause)

      GameCloses

      OPTIONS --> PAUSED : Back

**State Handler Implementation:**

.. code-block:: python

    if state == 'MAIN_MENU':
        main_menu.handle_events()
        main_menu.update()

* **State Delegation:** The engine acts as a pure router, dispatching logic and polling events directly to independent GUI instances or 3D scene objects based on the current finite state.

.. code-block:: python

    elif state == 'LOADING':
        while not loading_complete:
            check_loading_progress()

* **Blocking Transitions:** Specific intensive states, like chunk pre-loading, utilize blocking loops to dedicate entire CPU cycles before yielding control.

The Main Game Loop
------------------

**High-Level Loop Structure:**

.. code-block:: python

    delta_time = self.clock.tick(60) / 1000.0
    delta_time = min(delta_time, 0.033)

* **Timing and Clamping:** The core execution loop is strictly regulated. To prevent devastating physics synchronization bugs during lag spikes, delta time is hard-capped to a maximum of 33ms.

.. code-block:: python

    self.handle_events()
    self.update_in_game(delta_time)
    self.render()

* **Synchronous Frame Dispatch:** The render thread guarantees the sequence of user input, logical updates, and visual dispatching across every single pass.

Detailed Event Handling
-----------------------

**Event Loop:**

.. code-block:: python

    for event in pygame.event.get():
        if event.type == pygame.QUIT: return False

* **Polling Inputs:** Every frame, raw hardware events from the operating system are pulled and flushed through the `pygame.event` queue.

.. code-block:: python

    if self.game_state == 'IN_GAME':
        self.player.handle_event(event)

* **Targeted Dispatch:** Keys and mouse inputs are tunneled immediately into the active `game_state`, preventing un-rendered UI elements from consuming inputs.

Detailed Update Step (In-Game)
-------------------------------

**Update Sequence (per frame):**

.. code-block:: python

    self.world.update_loaded_chunks(player_chunk, RENDER_DISTANCE)

* **Chunk Streaming:** The logical step always calculates the player's world position and commands the background pool to load or drop respective memory boundaries.

.. code-block:: python

    self.process_mesh_queue(limit=MAIN_THREAD_MESH_PROCESS_LIMIT_INGAME)

* **Budgeted Queues:** Background workers execute heavily on CPU cores, but VAO/VBO OpenGL initialization is locked strictly to this primary thread and strictly limited per-frame to preserve FPS.

Detailed Render Step
--------------------

**Render Sequence (per frame):**

.. code-block:: python

    self.ctx.clear(0.53, 0.81, 0.92)
    self.ctx.clear_depth(1.0)

* **Buffer Sweeping:** The screen and depth layers are rigorously wiped clean on the graphics card prior to drawing the next visualization.

.. code-block:: python

    self.ctx.disable(moderngl.DEPTH_TEST)
    self.hud.render(self.ctx, self.shader_program)

* **Z-Buffering Control:** By disabling depth evaluations after geometry rendering, the 2D UI elements are mathematically drawn overtop the entire voxel environment without clipping.

Scene Rendering Pipeline
------------------------

**Scene.render() Detail (in-game world rendering):**

.. code-block:: python

    visible_chunks = shader_program.frustum_cull(self.camera, self.world.active_chunks)

* **Vectorized Frustum Culling:** The scene strictly bounds rendering to only what physically fits within the player's 3D cone-of-vision mathematically.

.. code-block:: python

    ctx.enable(moderngl.BLEND)
    chunk.mesh.render_water()

* **Multi-Pass Transparency:** Water and leaves are rendered entirely on an isolated pass with alphablending to prevent Z-fighting.

World Session Initialization (LOADING state)
---------------------------------------------

**init_game_session() Implementation:**

.. code-block:: python

    self.world = World(world_name)
    self.scene = Scene(self.world)

* **System Sub-Allocation:** Core session elements establish a pristine architectural tree.

.. code-block:: python

    pygame.event.clear()
    pygame.mouse.get_rel()

* **Accumulated Safety Flushing:** Discarding lingering hardware events prior to fully bridging ``IN_GAME`` prevents severe camera snapping.

Shutdown and Cleanup
--------------------

**quit_game() Implementation:**

.. code-block:: python

    if self.world:
        self.world.unload_all_chunks()

* **Data Evacuation:** Forcefully drops active terrain sectors straight onto persistent SQLite disk memory prior to closing logic.

.. code-block:: python

    for vbo in self.vbo_pool:
        vbo.release()

* **VRAM Destruction:** Caches pooled inside OpenGL bindings are permanently stripped off the system graphics.

Next Steps
----------

Now that you understand the core engine loop and state machine, proceed to the :doc:`architecture` breakdown to see how Pyrite utilizes multithreading and queue systems under the hood.

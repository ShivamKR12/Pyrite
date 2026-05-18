.. _main-engine:

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

      MAIN_MENU --> WORLD_SELECT : Play
      MAIN_MENU --> OPTIONS : Settings
      MAIN_MENU --> GameCloses : Quit

      WORLD_SELECT --> LOADING : Load/Create World

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

      OPTIONS --> PAUSED : Back

**State Handler Pseudocode:**

.. code-block:: python

    def handle_state(state):
        if state == 'MAIN_MENU':
            main_menu.handle_events()
            main_menu.update()
        elif state == 'LOADING':
            # Blocking loop: load chunks until ready
            while not loading_complete:
                # Generate/fetch chunks
                # Mesh chunks
                # Render loading screen UI
                check_loading_progress()
        elif state == 'IN_GAME':
            player.handle_events()
            world.update()
            scene.update()
        elif state == 'PAUSED':
            pause_menu.handle_events()
            pause_menu.update()
        elif state == 'OPTIONS':
            options_menu.handle_events()
            options_menu.update()

The Main Game Loop (Pseudocode)
-------------------------------

**High-Level Loop Structure:**

.. code-block:: python

    def run(self):
        running = True
        
        while running:
            # 1. FRAME TIMING
            frame_start_time = time.time()
            delta_time = self.clock.tick(60) / 1000.0  # Cap at 60 FPS
            delta_time = min(delta_time, 0.033)  # Clamp to 33ms max to prevent physics explosion
            
            # 2. EVENT HANDLING
            running = self.handle_events()  # Returns False if quit requested
            
            # 3. STATE-SPECIFIC UPDATES
            if self.game_state == 'IN_GAME':
                self.update_in_game(delta_time)
            elif self.game_state == 'PAUSED':
                # No logic updates while paused
                pass
            elif self.game_state == 'LOADING':
                self.update_loading(delta_time)
            
            # 4. RENDER
            self.render()
            
            # 5. DISPLAY
            pygame.display.flip()

Detailed Event Handling
-----------------------

**Event Loop:**

.. code-block:: python

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False  # Exit main loop
            
            # Global events (all states)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                elif event.key == pygame.K_F3:
                    self.show_debug_overlay = not self.show_debug_overlay
            
            # State-specific events
            if self.game_state == 'MAIN_MENU':
                self.main_menu.handle_event(event)
            elif self.game_state == 'IN_GAME':
                self.player.handle_event(event)
                
                # Pause or inventory
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.game_state = 'PAUSED'
                    elif event.key == pygame.K_e:
                        # Toggle inventory (layer on top of IN_GAME)
                        self.show_inventory = not self.show_inventory
                
                # Mining/placing
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # LClick
                        self.start_mining()
                    elif event.button == 3:  # RClick
                        self.place_block()
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        self.stop_mining()
            
            elif self.game_state == 'PAUSED':
                self.pause_menu.handle_event(event)
            
            elif self.game_state == 'OPTIONS':
                self.options_menu.handle_event(event)
        
        return True  # Continue main loop

Detailed Update Step (In-Game)
-------------------------------

**Update Sequence (per frame):**

.. code-block:: python

    def update_in_game(self, delta_time):
        # 1. PLAYER UPDATE
        self.player.update(delta_time)
        
        # 2. WORLD STREAMING
        player_chunk = self.world.get_chunk_containing(self.player.position)
        self.world.update_loaded_chunks(player_chunk, RENDER_DISTANCE)
        
        # 3. QUEUE PROCESSING (budgeted per frame)
        # Pull from load_queue, build_queue, mesh_queue
        self.process_mesh_queue(limit=MAIN_THREAD_MESH_PROCESS_LIMIT_INGAME)
        self.process_chunk_queue(limit=MAIN_THREAD_CHUNK_PROCESS_LIMIT_INGAME)
        
        # 4. VOXEL INTERACTIONS (mining/placing results)
        if self.mining_duration > 0:
            self.mining_duration += delta_time
            if self.mining_duration >= self.current_block_hardness:
                self.voxel_handler.remove_voxel(self.target_block_pos)
                self.mining_duration = 0
        
        # 5. SCENE UPDATE
        self.scene.update(delta_time)
        
        # 6. LIGHTING UPDATES (from block changes)
        # Already queued during voxel_handler calls
        
        # 7. UI ANIMATION
        self.hud.update(delta_time)
        if self.show_inventory:
            self.inventory_ui.update(delta_time)

Detailed Render Step
--------------------

**Render Sequence (per frame):**

.. code-block:: python

    def render(self):
        # 1. CLEAR FRAMEBUFFER
        self.ctx.clear(0.53, 0.81, 0.92)  # Sky blue
        self.ctx.clear_depth(1.0)
        
        # 2. IN-GAME RENDERING (if applicable)
        if self.game_state == 'IN_GAME':
            self.ctx.enable(moderngl.DEPTH_TEST)
            self.scene.render(self.ctx, self.shader_program)
            
            # 3. DISABLE DEPTH FOR UI
            self.ctx.disable(moderngl.DEPTH_TEST)
            
            # 4. RENDER HUD OVERLAY
            self.hud.render(self.ctx, self.shader_program)
            
            # 5. RENDER INVENTORY (if open)
            if self.show_inventory:
                self.inventory_ui.render(self.ctx, self.shader_program)
            
            # 6. RENDER DEBUG OVERLAY
            if self.show_debug_overlay:
                self.debug_overlay.render(self.ctx, self.shader_program)
        
        # 3. MENU RENDERING
        elif self.game_state == 'MAIN_MENU':
            self.ctx.disable(moderngl.DEPTH_TEST)
            self.main_menu.render(self.ctx, self.shader_program)
        
        elif self.game_state == 'PAUSED':
            # Render world darkened in background
            self.ctx.enable(moderngl.DEPTH_TEST)
            self.scene.render(self.ctx, self.shader_program)
            
            # Dim overlay
            self.ctx.disable(moderngl.DEPTH_TEST)
            render_dim_quad((0, 0), (2, 2), (0, 0, 0, 0.5))
            
            # Pause menu on top
            self.pause_menu.render(self.ctx, self.shader_program)
        
        elif self.game_state == 'LOADING':
            self.ctx.disable(moderngl.DEPTH_TEST)
            render_loading_screen(self.loading_progress)

Scene Rendering Pipeline
------------------------

**Scene.render() Detail (in-game world rendering):**

.. code-block:: python

    def render(self, ctx, shader_program):
        # 1. FRUSTUM CULLING
        visible_chunks = shader_program.frustum_cull(
            self.camera,
            self.world.active_chunks
        )
        
        # 2. PREPARE SHADER UNIFORMS
        shader_program.bind_matrices(
            projection=self.camera.projection_matrix,
            view=self.camera.view_matrix,
            model=np.identity(4)
        )
        shader_program.bind_uniforms(
            u_sun_direction=self.world.sun_direction,
            u_time=self.world.session_time,
            u_fog_density=self.config['render_distance'] * 48 * 0.7,
            u_texture_array=self.textures.texture_array,
            u_texture_map=self.textures.texture_map,
            bg_color=(0.53, 0.81, 0.92)  # Sky color
        )
        
        # 3. RENDER OPAQUE CHUNKS (depth write enabled)
        ctx.enable(moderngl.DEPTH_TEST)
        for chunk in visible_chunks:
            if chunk.mesh and not chunk.mesh.is_hidden_by_occlusion_query:
                chunk.mesh.render()  # Render opaque faces
        
        # 4. RENDER WATER (transparency, depth write disabled)
        ctx.enable(moderngl.BLEND)
        for chunk in visible_chunks:
            if chunk.mesh:
                chunk.mesh.render_water()  # Render water faces only
        ctx.disable(moderngl.BLEND)
        
        # 5. RENDER SKY
        self.sky.render(ctx, shader_program)
        
        # 6. RENDER CLOUDS
        self.clouds.render(ctx, shader_program)
        
        # 7. RENDER ITEMS (dropped entities)
        for item in self.world.items:
            item.render(ctx, shader_program)
        
        # 8. RENDER VOXEL MARKER (target block outline)
        if self.voxel_marker.visible:
            self.voxel_marker.render(ctx, shader_program)
        
        # 9. RENDER HELD ITEM (in camera view)
        self.held_item_mesh.render(ctx, shader_program)

World Session Initialization (LOADING state)
---------------------------------------------

**init_game_session() Pseudocode:**

.. code-block:: python

    def init_game_session(self, world_name):
        # 1. CLEAR PREVIOUS WORLD
        if self.world:
            self.world.unload_all_chunks()  # Flush to DB
        
        # 2. LOAD/CREATE WORLD
        self.world = World(world_name)
        self.world.load_metadata()  # Load seed, spawn point
        
        # 3. CREATE SCENE
        self.scene = Scene(self.world)
        
        # 4. LOAD PLAYER
        player_data = self.world.load_player_data()
        self.player = Player(self.world)
        self.player.feet_pos = glm.vec3(player_data['x'], player_data['y'], player_data['z'])
        self.player.inventory = player_data['inventory']
        self.player.health = player_data['health']
        
        # 5. INITIALIZE VOXEL HANDLER
        self.voxel_handler = VoxelHandler(self.world)
        
        # 6. CHUNK PRELOADING (blocking loop)
        self.game_state = 'LOADING'
        initial_chunks_needed = (RENDER_DISTANCE * 2) ** 2
        chunks_loaded = 0
        
        while chunks_loaded < initial_chunks_needed:
            # Request chunk loads
            for chunk_coord in self.world.get_chunks_near_player(self.player, RENDER_DISTANCE):
                if not self.world.chunk_exists(chunk_coord) and not self.world.loading.contains(chunk_coord):
                    self.world.request_chunk_load(chunk_coord)
            
            # Process queue (blocking)
            self.process_mesh_queue(limit=64)  # Load aggressively during init
            self.process_chunk_queue(limit=10)
            
            chunks_loaded = len(self.world.active_chunks)
            loading_percent = int(100 * chunks_loaded / initial_chunks_needed)
            
            # Render loading screen
            self.render_loading_screen(loading_percent)
            pygame.display.flip()
        
        # 7. SAFETY FLUSH (clear buffered inputs)
        pygame.event.clear()
        pygame.mouse.get_rel()  # Consume any accumulated mouse movement
        
        # 8. TRANSITION TO GAMEPLAY
        self.game_state = 'IN_GAME'
        self.player_ready = True

Shutdown and Cleanup
--------------------

**quit_game() Pseudocode:**

.. code-block:: python

    def quit_game(self):
        print("Saving world...")
        
        # 1. SAVE PLAYER STATE
        if self.player:
            player_data = {
                'x': self.player.feet_pos.x,
                'y': self.player.feet_pos.y,
                'z': self.player.feet_pos.z,
                'yaw': self.player.yaw,
                'pitch': self.player.pitch,
                'health': self.player.health,
                'hunger': self.player.hunger,
                'oxygen': self.player.oxygen,
                'inventory': self.player.inventory,
                'inventory_counts': self.player.inventory_counts,
            }
            self.world.save_player_data(player_data)
        
        # 2. UNLOAD ALL CHUNKS (saves to DB)
        if self.world:
            self.world.unload_all_chunks()
        
        # 3. CLOSE DATABASE
        if hasattr(self, 'db'):
            self.db.close()
        
        # 4. RELEASE GPU RESOURCES
        if hasattr(self, 'vbo_pool'):
            for vbo in self.vbo_pool:
                vbo.release()
        
        # 5. CLEANUP AUDIO
        if hasattr(self, 'sounds'):
            pygame.mixer.stop()
        
        # 6. CLOSE PYGAME
        pygame.quit()
        
        print("World saved. Goodbye!")
.. _api:

API Reference
=============

This section provides a structured reference to core Pyrite classes, methods, and constants. Use this for looking up specific functionality.

Core Engine (``main.py``)
-------------------------

**class Pyrite**

Root application class managing game lifecycle, state transitions, and subsystems.

Key Attributes:

- ``game_state``: Current state (``'MAIN_MENU', 'IN_GAME', 'PAUSED', 'OPTIONS', 'LOADING', 'INVENTORY', 'WORLD_SELECT', 'CREATE_WORLD``)
- ``world``: World instance (active when in-game)
- ``player``: Player instance
- ``scene``: Scene manager (rendering)
- ``ctx``: ModernGL context

Key Methods:

- ``__init__()``: Initialize Pygame, OpenGL, load config
- ``init_game_session(save_name, force_seed, game_mode)``: Load/create a world
- ``run()``: Main loop (event → update → render)
- ``handle_events()``: Dispatch OS events
- ``update()``: Tick all systems
- ``render()``: Draw frame
- ``quit_game()``: Shutdown, save world

Player (``player.py``)
----------------------

**class Player(Camera)**

Manages player physics, camera, input, inventory, and survival stats.

Key Attributes:

- ``feet_pos: glm.vec3``: Position at feet (for collisions)
- ``velocity: glm.vec3``: Movement velocity
- ``yaw, pitch: float``: Camera rotation (radians)
- ``on_ground: bool``: Contact with solid block
- ``in_water: bool``: Head submerged
- ``health, hunger, oxygen: float``: Survival stats (0-20)
- ``inventory: List[int]``: 41-slot inventory IDs
- ``inventory_counts: List[int]``: Stack sizes
- ``hotbar_index: int``: Selected hotbar slot (0-8)

Key Methods:

- ``update()``: Physics, movement, animations
- ``handle_event(event)``: Process input
- ``get_aabb()``: Get bounding box
- ``move_and_collide()``: Physics with collision
- ``add_item(voxel_id)``: Pickup item
- ``take_damage(amount)``: Reduce health

World (``world.py``)
---------------------

**class World**

Manages terrain generation, chunk loading/unloading, and persistence.

Key Attributes:

- ``active_chunks: Dict``: Loaded chunks
- ``world_seed: int``: World seed
- ``voxels: np.ndarray``: Massive 1D array of all active world voxels
- ``lightmaps: np.ndarray``: Massive 1D array of all active world light data

Key Methods:

- ``load_chunk(x, y, z)``: Queue a chunk for asynchronous loading/generation
- ``unload_chunk(pos)``: Unload chunk and trigger async DB save
- ``save()``: Synchronous shutdown, flush all to disk

Chunk (``chunk.py``)
----------------------------------

**class Chunk**

Represents a 48x48x48 voxel block.

Key Attributes:

- ``position: (int, int, int)``: Chunk coordinates
- ``voxels: np.ndarray``: (110592,) uint8 voxel IDs
- ``lightmap: np.ndarray``: (110592,) uint8 packed light
- ``mesh: ChunkMesh``: Rendered geometry
- ``is_empty: bool``: True if chunk contains only air
- ``is_visible: bool``: Frustum/Occlusion visibility state

Key Methods:

- ``build_mesh()``: Triggers chunk mesh builder
- ``render()``: Submits VBOs to GPU

Scene (``scene.py``)
--------------------

**class Scene**

Multi-pass rendering orchestrator.

Key Methods:

- ``update()``: Update cameras, animations, chunks
- ``render()``: Render world + UI

VoxelHandler (``voxel_handler.py``)
-----------------------------------

**class VoxelHandler**

Raycast targeting and block manipulation.

Key Methods:

- ``ray_cast()``: Cast ray from camera, return target block
- ``add_voxel()``: Place block
- ``remove_voxel()``: Mine block

Constants (``settings.py``)
---------------------------

Performance Tuning:

- ``MESH_BUILD_LIMIT_INGAME = 4``: Chunks meshed per frame
- ``MAIN_THREAD_MESH_PROCESS_LIMIT_INGAME = 2``: GPU uploads per frame
- ``VBO_POOL_CAP = 150``: Recycled GPU buffers
- ``LIGHTING_QUEUE_SIZE = 200000``: BFS light queue nodes

Physics:

- ``GRAVITY = -0.000025``: Downward acceleration
- ``JUMP_VELOCITY = 0.0095``: Jump boost
- ``PLAYER_SPEED = 0.005``: Movement speed
- ``PLAYER_WIDTH = 0.6``: Collision box width
- ``PLAYER_HEIGHT = 1.8``: Collision box height

Survival:

- ``MAX_HEALTH = 20``: Player dies at 0 health
- ``MAX_HUNGER = 20``: Hunger depletes over time, causes health loss at 0
- ``MAX_OXYGEN = 20``: Breath underwater
- ``BLOCK_HARDNESS``: Dict of block IDs → break time (ms)

Environment:

- ``CHUNK_SIZE = 48``: Voxels per axis
- ``CHUNK_VOL = 110592``: Total voxels per chunk
- ``WATER_LINE = 6``: Sea level
- ``STONE_LVL = 49``: Bedrock layer start
- ``WORLD_W, WORLD_H, WORLD_D``: Max chunk counts

Shader Programs (``shader_program.py``)
---------------------------------------

**Uniform Bindings (All Shaders):**

- ``m_proj: mat4``: Projection matrix
- ``m_view: mat4``: View matrix (camera)
- ``m_model: mat4``: Model matrix
- ``u_sun_direction: vec3``: Sun position (normalized)
- ``u_time: float``: World time (seconds)

**Chunk Shader Uniforms:**

- ``u_texture_array_0: sampler2DArray``: Texture atlas
- ``u_texture_map[256]: int[]``: Voxel ID → texture layer
- ``u_fog_density: float``: Fog start distance
- ``u_underwater_tint: bool``: Apply blue tint
- ``bg_color: vec3``: Background (sky) color

**UI Shader Uniforms:**

- ``u_offset: vec2``: Screen position (NDC)
- ``u_scale: vec2``: Size (NDC)
- ``u_color: vec4``: Color (UI shaders)

Mesh Building (``build_chunk_mesh.py``)
---------------------------------------

**Function:** ``build_chunk_mesh(chunk_voxels, chunk_lightmap, chunk_pos, world_voxels, world_lightmaps, chunk_positions)``

Numba-compiled greedy meshing. Returns vertex data and light data (packed).

**Vertex Packing:**

- Bits 31-26: X coordinate (0-47)
- Bits 25-20: Y coordinate (0-47)
- Bits 19-14: Z coordinate (0-47)
- Bits 13-6: Voxel ID (0-255)
- Bits 5-3: Face ID (0-5)
- Bits 2-1: AO ID (0-3)
- Bit 0: Flip ID (0-1)

**Light Packing:**

- Bits 7-4: Sunlight (0-15)
- Bits 3-0: Blocklight (0-15)

Terrain Generation (``terrain_gen.py``)
---------------------------------------
Handled via Numba JIT functions in ``Chunk.generate_terrain()`` using vectorized 3D simplex noise.

Lighting (``lighting.py``)
--------------------------

Uses BFS lighting propagation logic executed completely through standalone Numba compiled functions such as:

- ``init_chunk_lighting()``
- ``stitch_chunk_lighting()``
- ``update_light_place_block()``
- ``update_light_remove_block()``
- ``place_torch()``

Common Enums and Constants
---------------------------

.. code-block:: python

    # Block IDs
    AIR = 0
    SAND = 1
    GRASS = 2
    DIRT = 3
    STONE = 4
    SNOW = 5
    LEAVES = 6
    WOOD = 7
    GRAVEL = 8
    WOOD_PLANKS = 9
    COBBELSTONE = 10
    WATER = 11
    GLOWSTONE = 12
    GLASS = 13
    CACTUS = 14
    STONE_BRICKS = 15
    # 16-32 are reserved for other blocks, 33+ are items
    STICK = 33
    WOODEN_PICKAXE = 34

    # Game States
    MAIN_MENU
    WORLD_SELECT
    CREATE_WORLD
    LOADING
    IN_GAME
    INVENTORY
    PAUSED
    OPTIONS

    # Transparent Blocks:
    [AIR, WATER, GLASS, LEAVES]

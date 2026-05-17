.. _api:

API Reference
=============

This section provides a structured reference to core Pyrite classes, methods, and constants. Use this for looking up specific functionality.

Core Engine (main.py)
---------------------

**class Pyrite(App)**

Root application class managing game lifecycle, state transitions, and subsystems.

Key Attributes:

- ``game_state``: Current state ('MAIN_MENU', 'IN_GAME', 'PAUSED', 'OPTIONS', 'LOADING')
- ``world``: World instance (active when in-game)
- ``player``: Player instance
- ``scene``: Scene manager (rendering)
- ``ctx``: ModernGL context

Key Methods:

- ``__init__()``: Initialize Pygame, OpenGL, load config
- ``run()``: Main loop (event → update → render)
- ``handle_events()``: Dispatch OS events
- ``update(delta_time)``: Tick all systems
- ``render()``: Draw frame
- ``quit_game()``: Shutdown, save world

Player (player.py)
-------------------

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

- ``update(delta_time)``: Physics, movement, animations
- ``handle_event(event)``: Process input
- ``get_aabb()``: Get bounding box
- ``move_and_collide(delta_time, world)``: Physics with collision
- ``add_item(voxel_id)``: Pickup item
- ``take_damage(amount)``: Reduce health

World (world.py)
-----------------

**class World**

Manages terrain generation, chunk loading/unloading, and persistence.

Key Attributes:

- ``active_chunks: Dict[(x,y,z), Chunk]``: Loaded chunks
- ``seed: int``: World seed
- ``terrain_gen: TerrainGenerator``: Procedural generation
- ``persistence: WorldPersistence``: SQLite I/O

Key Methods:

- ``get_chunk(x, y, z, generate=True)``: Get or generate chunk
- ``get_voxel(x, y, z)``: Get voxel ID at coordinate
- ``set_voxel(x, y, z, id)``: Set voxel, trigger updates
- ``unload_chunk(x, y, z)``: Unload chunk (saves to DB)
- ``unload_all_chunks()``: Shutdown, flush all to disk

Chunk (world_objects/chunk.py)
-------------------------------

**class Chunk**

Represents a 48x48x48 voxel block.

Key Attributes:

- ``position: (int, int, int)``: Chunk coordinates
- ``voxels: np.ndarray``: (110592,) uint8 voxel IDs
- ``lightmap: np.ndarray``: (110592,) uint8 packed light
- ``mesh: ChunkMesh``: Rendered geometry
- ``loaded: bool``: Fully initialized
- ``dirty: bool``: Needs mesh rebuild

Key Methods:

- ``init_lighting()``: BFS light propagation
- ``rebuild_mesh()``: Greedy meshing

Scene (scene.py)
-----------------

**class Scene**

Multi-pass rendering orchestrator.

Key Methods:

- ``update(delta_time)``: Update cameras, animations
- ``render(ctx, program)``: Render world + UI
  - Opaque chunks (depth test)
  - Sky, clouds, items
  - UI overlay (depth disabled)

VoxelHandler (voxel_handler.py)
--------------------------------

**class VoxelHandler**

Raycast targeting and block manipulation.

Key Methods:

- ``raycast(world, max_distance)``: Cast ray from camera, return target block
- ``add_voxel(pos, voxel_id)``: Place block
- ``remove_voxel(pos)``: Mine block

Constants (settings.py)
-----------------------

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

- ``MAX_HEALTH = 20``
- ``MAX_HUNGER = 20``
- ``MAX_OXYGEN = 20``
- ``BLOCK_HARDNESS``: Dict of block IDs → break time (ms)

Environment:

- ``CHUNK_SIZE = 48``: Voxels per axis
- ``CHUNK_VOL = 110592``: Total voxels per chunk
- ``WATER_LVL = 5.6``: Sea level
- ``STONE_LVL = 8``: Bedrock layer start
- ``WORLD_W, WORLD_H, WORLD_D``: Max chunk counts

UI Components (ui/components.py)
---------------------------------

**class UIComponent (Abstract)**

Base class for all UI elements.

Key Methods:

- ``update(delta_time)``
- ``render(ctx, program)``
- ``handle_event(event)``
- ``contains_point(x, y) → bool``

**class Button(UIComponent)**

- ``__init__(pos, size, label, callback)``
- ``on_click()``: Execute callback

**class Slider(UIComponent)**

- ``value: float``: Current value
- ``on_change(callback)``: Called on drag

**class TextInput(UIComponent)**

- ``text: str``: Current input
- ``active: bool``: Focused

Shader Programs
----------------

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

Mesh Building
--------------

**Function: build_chunk_mesh(chunk_voxels, chunk_lightmap, chunk_pos, world_voxels, world_lightmaps, chunk_positions)**

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

Terrain Generation
-------------------

**Function: get_height_at_column(x, z) → float**

FBm noise combining 4 octaves. Returns height 0-256.

**Function: get_biome_at_column(x, z) → str**

Returns one of: 'DESERT', 'SNOW', 'FOREST', 'GRASSLAND', 'PLAINS'

**Function: generate_column(x, z) → List[int]**

Returns voxel IDs from y=0 to y=256 for single column.

Lighting
---------

**Function: propagate_light_queue(queue, world_voxels, world_lightmaps, light_type)**

BFS light spreading. Modifies world_lightmaps in-place.

**Function: stitch_chunk_lighting(chunk, neighbors)**

Synchronize light across chunk boundaries.

Persistence
-----------

**Class: WorldPersistence**

- ``save_chunk_to_db(conn, x, y, z, voxels, lightmap)``
- ``load_chunk_from_db(conn, x, y, z) → (voxels, lightmap)``
- ``save_player_data(conn, player)``
- ``load_player_data(conn) → dict``

Common Enums and Constants
---------------------------

**Block IDs:**

- AIR = 0
- STONE = 1
- DIRT = 2
- GRASS = 3
- SAND = 4
- WATER = 5
- WOOD = 6
- LEAVES = 7
- WOOD_PLANKS = 8
- STICK = 9
- WOODEN_PICKAXE = 10

**Game States:**

- MAIN_MENU
- WORLD_SELECT
- CREATE_WORLD
- LOADING
- IN_GAME
- INVENTORY
- PAUSED
- OPTIONS

**Transparent Blocks:**

[AIR, WATER, GLASS, LEAVES, VINE]


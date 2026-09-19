---
name: pyrite-api
description: >-
  The exact, working code API reference for the Pyrite engine. Contains all classes, methods, and signatures. You MUST read this skill before making any modifications to the codebase to prevent hallucinations.
---

# Pyrite Working API Reference
This document contains the exact, AST-parsed API signatures of the Pyrite project. Always refer to these signatures rather than guessing.

## `src/camera.py`

### Class `Camera`
> Represents a 3D camera in the world.
- `def __init__(self, position: Any, yaw: float, pitch: float) -> None`
- `def update(self) -> None`
- `def update_view_matrix(self) -> None`
- `def update_vectors(self) -> None`
- `def rotate_pitch(self, delta_y: float) -> None`
- `def rotate_yaw(self, delta_x: float) -> None`
- `def move_left(self, velocity: float) -> None`
- `def move_right(self, velocity: float) -> None`
- `def move_up(self, velocity: float) -> None`
- `def move_down(self, velocity: float) -> None`
- `def move_forward(self, velocity: float) -> None`
- `def move_back(self, velocity: float) -> None`

## `src/frustum.py`

### Class `Frustum`
> Calculates the camera's viewing frustum planes and boundaries dynamically
- `def __init__(self, camera: Any) -> None`
- `def update_factors(self, v_fov: float, h_fov: float) -> None`
- `def is_on_frustum(self, chunk: Any) -> bool`
### `def frustum_cull_fast(chunk_centers: Any, out_mask: Any, cam_pos: Any, cam_forward: Any, cam_right: Any, cam_up: Any, tan_y: float, tan_x: float, factor_y: float, factor_x: float) -> Any`
> Numba-optimized vectorized frustum culling.

## `src/lighting.py`

### `def get_voxel_fast(wx: int, wy: int, wz: int, world_voxels: Any, chunk_positions: Any) -> int`
> Numba-optimized helper to quickly retrieve a voxel ID from the global
### `def get_light_fast(wx: int, wy: int, wz: int, world_lightmaps: Any, chunk_positions: Any) -> int`
> Numba-optimized helper to rapidly read the packed light level (Sunlight and Blocklight)
### `def set_light_fast(wx: int, wy: int, wz: int, val: int, world_lightmaps: Any, chunk_positions: Any) -> None`
> Numba-optimized helper to directly write a packed light value into the global
### `def propagate_light_queue(queue: Any, tail: int, is_sun: bool, world_voxels: Any, world_lightmaps: Any, chunk_positions: Any) -> None`
> Numba-optimized Breadth-First Search (BFS) light propagation algorithm.
### `def _init_chunk_lighting(cx: int, cy: int, cz: int, world_voxels: Any, world_lightmaps: Any, chunk_positions: Any, queue_sun: Any, queue_block: Any) -> None`
> Internal Numba implementation for queuing initial light sources within a chunk.
### `def init_chunk_lighting(cx: int, cy: int, cz: int, world_voxels: Any, world_lightmaps: Any, chunk_positions: Any) -> None`
> Scans a newly loaded/generated chunk for sunlight blocks (level 15) and light-emitting
### `def _stitch_chunk_lighting(cx: int, cy: int, cz: int, world_voxels: Any, world_lightmaps: Any, chunk_positions: Any, queue_sun: Any, queue_block: Any) -> None`
> Internal Numba implementation for sampling the borders of adjacent chunks
### `def stitch_chunk_lighting(cx: int, cy: int, cz: int, world_voxels: Any, world_lightmaps: Any, chunk_positions: Any) -> None`
> Cross-chunk boundary light bleeding. Evaluates the outer borders of a given chunk against
### `def remove_light_node(wx: int, wy: int, wz: int, light_level: int, is_sun: bool, world_lightmaps: Any, chunk_positions: Any, refill_queue: Any, tail_refill: int, queue: Any) -> int`
> Strips out lighting dynamically when a light source (or opening) is blocked/destroyed.
### `def _update_light_place_block(wx: int, wy: int, wz: int, world_voxels: Any, world_lightmaps: Any, chunk_positions: Any, refill_queue: Any, removal_queue: Any) -> None`
> Internal Numba implementation for removing light when an opaque block is placed.
### `def update_light_place_block(wx: int, wy: int, wz: int, world_voxels: Any, world_lightmaps: Any, chunk_positions: Any) -> None`
> Executed when a player places a solid block. Strips existing light from the space
### `def _update_light_remove_block(wx: int, wy: int, wz: int, world_voxels: Any, world_lightmaps: Any, chunk_positions: Any, queue_sun: Any, queue_block: Any) -> None`
> Internal Numba implementation for propagating light when a block is removed.
### `def update_light_remove_block(wx: int, wy: int, wz: int, world_voxels: Any, world_lightmaps: Any, chunk_positions: Any) -> None`
> Executed when a player destroys a block. Allows surrounding light to flood into the
### `def _place_torch(wx: int, wy: int, wz: int, world_voxels: Any, world_lightmaps: Any, chunk_positions: Any, queue: Any) -> None`
> Internal Numba implementation for artificially injecting blocklight (level 14)
### `def place_torch(wx: int, wy: int, wz: int, world_voxels: Any, world_lightmaps: Any, chunk_positions: Any) -> None`
> Hardcodes a block light value of 14 into the grid and triggers a blocklight BFS

## `src/main.py`

### Class `Pyrite`
> The core engine application class.
- `def __init__(self) -> None`
- `def load_config(self) -> None`
- `def save_config(self) -> None`
- `def on_init(self) -> None`
- `def init_game_session(self, save_name: str, force_seed: Optional[int], game_mode: Optional[int]) -> None`
- `def render_loading_screen(self, text: str) -> None`
- `def update(self) -> None`
- `def render(self) -> None`
- `def handle_events(self) -> None`
- `def quit_game(self) -> None`
- `def run(self) -> None`

## `src/meshes/base_mesh.py`

### Class `BaseMesh`
> Abstract base class for all OpenGL geometry meshes.
- `def __init__(self) -> None`
- `def get_vertex_data(self) -> Any`
- `def get_vao(self) -> Any`
- `def render(self) -> None`

## `src/meshes/chunk_mesh.py`

### Class `ChunkMesh`
> Manages the OpenGL geometry for a chunk, handling opaque and transparent meshes.
- `def __init__(self, chunk: Any) -> None`
- `def render(self) -> None`
- `def render_water(self) -> None`
- `def get_vao(self) -> Any`
- `def get_vertex_data(self) -> Tuple[Any, int, int]`

## `src/meshes/chunk_mesh_builder.py`

### `def get_ao(local_pos: Tuple[int, int, int], world_pos: Tuple[int, int, int], chunk_voxels: Any, world_voxels: Any, chunk_positions: Any, plane: str) -> Tuple[int, int, int, int]`
> Calculates the ambient occlusion (AO) value for a specific vertex on a block face.
### `def get_vertex_light(local_vertex_pos: Tuple[int, int, int], world_vertex_pos: Tuple[int, int, int], plane: str, face_light: int, chunk_voxels: Any, chunk_lightmap: Any, world_voxels: Any, world_lightmaps: Any, chunk_positions: Any) -> int`
> Computes the smoothed lighting value for a specific vertex by sampling and averaging
### `def pack_data(x: int, y: int, z: int, voxel_id: int, face_id: int, ao_id: int, flip_id: int, light_val: int) -> Tuple[int, int]`
> Packs multiple pieces of vertex data (coordinates, voxel ID, face ID, AO ID, flip ID)
### `def get_chunk_index(world_voxel_pos: Tuple[int, int, int], chunk_positions: Any) -> int`
> Calculates the 1D index of a chunk in the global world arrays based on an absolute
### `def get_neighbor_voxel_id(local_voxel_pos: Tuple[int, int, int], world_voxel_pos: Tuple[int, int, int], chunk_voxels: Any, world_voxels: Any, chunk_positions: Any) -> int`
> Retrieves the voxel ID of a neighboring block given its local and world coordinates.
### `def get_neighbor_light(local_voxel_pos: Tuple[int, int, int], world_voxel_pos: Tuple[int, int, int], chunk_lightmap: Any, world_lightmaps: Any, chunk_positions: Any) -> int`
> Retrieves the packed lighting value (sunlight and blocklight) of a neighboring block
### `def is_transparent(voxel_id: int) -> bool`
> Checks if a given voxel ID corresponds to a transparent block (like air, water, glass, or leaves).
### `def is_void(local_voxel_pos: Tuple[int, int, int], world_voxel_pos: Tuple[int, int, int], chunk_voxels: Any, world_voxels: Any, chunk_positions: Any) -> bool`
> Determines if a block at a given coordinate is empty or transparent, which is used
### `def add_data(vertex_data: Any, index: int) -> int`
> Appends newly packed vertex data and its associated lighting value into the main
### `def build_chunk_mesh(chunk_voxels: Any, chunk_lightmap: Any, format_size: int, chunk_pos: Tuple[int, int, int], world_voxels: Any, world_lightmaps: Any, chunk_positions: Any) -> Tuple[Any, int, int]`
> The core greedy meshing algorithm. It scans through a chunk's voxel data slice by slice

## `src/meshes/cloud_mesh.py`

### Class `CloudMesh`
> Generates the geometry for the procedural 3D cloud layer.
- `def __init__(self, app: Any) -> None`
- `def get_vertex_data(self) -> NDArray[np.uint16]`
- `def gen_clouds(cloud_data: Any, perm_array: Any) -> None`
- `def build_mesh(cloud_data: Any) -> NDArray[np.uint16]`

## `src/meshes/cube_mesh.py`

### Class `CubeMesh`
> Generates the geometry for a standard 3D cube.
- `def __init__(self, app: Any) -> None`
- `def get_data(vertices: List[Any], indices: List[Tuple[int, int, int]]) -> NDArray[np.float16]`
- `def get_vertex_data(self) -> NDArray[np.float16]`

## `src/meshes/item_mesh.py`

### Class `ItemMesh`
> Generates the geometry for dropped 3D items and blocks in the world.
- `def __init__(self, app: Any) -> None`
- `def get_vertex_data(self) -> NDArray[np.float32]`

## `src/meshes/obj_mesh.py`

### Class `ObjMesh`
> Generates rendering geometry by parsing and loading standard 3D Wavefront (.obj) files.
- `def __init__(self, app: Any, obj_path: str, tex_id: Optional[int]) -> None`
- `def render(self) -> None`
- `def parse_mtl(self, mtl_path: str) -> Dict[str, Dict[str, List[float]]]`
- `def get_vertex_data(self) -> NDArray[np.float32]`

## `src/noise.py`

### `def _seed_numba(new_seed: int) -> None`
> Internal helper to seed Numba's random number generator and standard Python random.
### `def set_seed(new_seed: int) -> None`
> Updates the global OpenSimplex permutation arrays with a deterministic seed,
### `def noise2(x: float, y: float, perm_array: Any) -> float`
> Evaluates 2D Simplex Noise using the pre-compiled permutation array.
### `def noise3(x: float, y: float, z: float, perm_array: Any, perm_grad_array: Any) -> float`
> Evaluates 3D Simplex Noise using the pre-compiled permutation arrays.

## `src/player.py`

### Class `Player`
> Represents the player entity in the world.
- `def __init__(self, app: Any, position: Optional[Any], yaw: float, pitch: float) -> None`
- `def find_spawn_position(self) -> Any`
- `def update(self) -> None`
- `def handle_event(self, event: Any) -> None`
- `def mouse_control(self) -> None`
- `def handle_interaction(self) -> None`
- `def keyboard_control(self) -> None`
- `def apply_gravity(self) -> None`
- `def move_and_collide(self) -> None`
- `def resolve_axis(self, axis: str) -> None`
- `def get_aabb(self) -> Tuple[Any, Any]`
- `def aabb_intersect(a_min: Any, a_max: Any, b_min: Any, b_max: Any) -> bool`
- `def add_item(self, voxel_id: int) -> bool`
- `def take_damage(self, amount: int) -> None`
- `def respawn(self) -> None`

## `src/profiler.py`

### Class `ThreadSampleBuffer`
> Isolated, memory-bounded buffer dedicated to a specific thread's metrics.
- `def __init__(self, max_samples: int) -> None`
- `def record(self, category: str, elapsed_time: float) -> None`
### Class `Profiler`
> Production-grade game telemetry system.
- `def __init__(self, max_samples_per_category: int) -> None`
- `def _get_buffer(self) -> ThreadSampleBuffer`
- `def start_frame(self) -> None`
- `def end_frame(self) -> None`
- `def record(self, category: str, elapsed_time: float) -> None`
- `def measure(self, category: str) -> Generator[None, None, None]`
- `def profile_func(self, category: Optional[str]) -> Callable[[Callable[..., Any]], Callable[..., Any]]`
- `def save_report(self, filename: str) -> None`

## `src/scene.py`

### Class `Scene`
> Acts as the primary game session container.
- `def __init__(self, app: Any, save_name: str, seed: int) -> None`
- `def update(self) -> None`
- `def render(self) -> None`

## `src/settings.py`

### `def get_path(relative_path: str) -> str`
> Get absolute path to resource

## `src/shader_program.py`

### Class `ShaderProgram`
> Compiles, links, and manages all GLSL shader programs used by the engine.
- `def __init__(self, app: Any) -> None`
- `def set_uniforms_on_init(self) -> None`
- `def update(self) -> None`
- `def get_program(self, shader_name: str) -> Any`

## `src/sounds.py`

### Class `Sounds`
> Manages all audio assets, sound effects, and background music.
- `def __init__(self, app: Any) -> None`
- `def set_sfx_volume(self, value: float) -> None`
- `def play_walk(self, voxel_id: int) -> None`
- `def play_break(self, voxel_id: int) -> None`
- `def play_place(self, voxel_id: int) -> None`
- `def play_jump(self, voxel_id: int) -> None`
- `def play_breaking(self, voxel_id: int, mining_time: float, mining_duration: float) -> None`
- `def play_place_block(self) -> None`

## `src/terrain_gen.py`

### `def get_biome(x: float, z: float, perm_array: Any) -> Tuple[float, float]`
> Evaluates Simplex noise to determine the overarching temperature and moisture
### `def get_height(x: float, z: float, perm_array: Any) -> int`
> Calculates the absolute maximum surface elevation of the terrain at a specific
### `def get_index(x: int, y: int, z: int) -> int`
> Translates a localized 3D chunk coordinate (x, y, z) into a flattened
### `def set_voxel_column(voxels: Any, x: int, z: int, cx: int, cy: int, cz: int, perm_array: Any, perm_grad_array: Any) -> None`
> Procedurally generates a single vertical column of blocks within a chunk.
### `def place_tree(voxels: Any, x: int, y: int, z: int, voxel_id: int, tree_prob: float) -> None`
> Constructs a localized tree structure (wood trunk and spherical leaf crown)
### `def fill_initial_sunlight(voxels: Any, lightmap: Any, cx: int, cy: int, cz: int, perm_array: Any) -> None`
> Initializes a newly generated chunk's lightmap by simulating direct,

## `src/textures.py`

### Class `Textures`
> Loads, configures, and binds OpenGL textures and texture arrays.
- `def __init__(self, app: Any) -> None`
- `def load(self, file_name: str, is_tex_array: bool, rotation: int, flip_x: bool, flip_y: bool) -> Any`

## `src/ui/components.py`

### `def get_shared_resource(app: Any, res_type: str) -> Any`
> Lazily loads and shares UI meshes, fonts, and textures to prevent VRAM and CPU bloat.
### Class `UINode`
> Base class for all UI elements in the hierarchical layout system.
- `def __init__(self, size: Tuple[float, float]) -> None`
- `def add_child(self, child: 'UINode') -> 'UINode'`
- `def get_global_pos(self) -> Tuple[float, float]`
- `def update_layout(self) -> None`
- `def update(self, mouse_pos: Optional[Tuple[int, int]]) -> None`
- `def handle_event(self, event: Any) -> None`
- `def render(self, offset: Tuple[float, float], alpha: float) -> None`
### Class `VBox`
> Vertical stacking container that automatically arranges its children.
- `def __init__(self, pos: Tuple[float, float], spacing: float) -> None`
- `def update_layout(self) -> None`
### Class `Button`
> Represents a clickable UI button with text, hover effects, and an assigned action.
- `def __init__(self, app: Any, text: str, pos: Tuple[float, float], size: Tuple[float, float], action: Optional[Callable[[], None]], border_radius: int, elevation: int) -> None`
- `def check_hover(self, mouse_pos: Tuple[int, int]) -> bool`
- `def update(self, mouse_pos: Optional[Tuple[int, int]]) -> None`
- `def handle_event(self, event: Any) -> None`
- `def render(self, offset: Tuple[float, float], alpha: float) -> None`
### Class `WorldButton`
> A specialized button used in the World Selection menu to display rich information
- `def __init__(self, app: Any, save_name: str, display_name: str, seed: int, game_mode: int, creation_date: str, last_played: str, pos: Tuple[float, float], size: Tuple[float, float], action: Optional[Callable[[], None]], border_radius: int, elevation: int) -> None`
- `def check_hover(self, mouse_pos: Tuple[int, int]) -> bool`
- `def update(self, mouse_pos: Optional[Tuple[int, int]]) -> None`
- `def handle_event(self, event: Any) -> None`
- `def render(self, offset: Tuple[float, float], alpha: float) -> None`
### Class `TextInput`
> Provides a simple interactive text entry field for the UI.
- `def __init__(self, app: Any, pos: Tuple[float, float], size: Tuple[float, float], label: str) -> None`
- `def handle_event(self, event: Any) -> None`
- `def render(self, offset: Tuple[float, float], alpha: float) -> None`
### Class `Slider`
> An interactive UI slider component used to adjust numerical settings
- `def __init__(self, app: Any, text: str, pos: Tuple[float, float], size: Tuple[float, float], min_val: float, max_val: float, config_key: str, action: Optional[Callable[[Any], None]], is_int: bool) -> None`
- `def update(self, mouse_pos: Optional[Tuple[int, int]]) -> None`
- `def handle_event(self, event: Any) -> None`
- `def render(self, offset: Tuple[float, float], alpha: float) -> None`
### Class `Toggle`
> A binary toggle switch component for the UI (e.g., for On/Off settings).
- `def __init__(self, app: Any, text: str, pos: Tuple[float, float], size: Tuple[float, float], config_key: str, action: Optional[Callable[[bool], None]]) -> None`
- `def update(self, mouse_pos: Optional[Tuple[int, int]]) -> None`
- `def handle_event(self, event: Any) -> None`
- `def render(self, offset: Tuple[float, float], alpha: float) -> None`

## `src/ui/hud.py`

### Class `Crosshair`
> Renders a simple fixed crosshair at the center of the screen.
- `def __init__(self, app: Any) -> None`
- `def render(self) -> None`
### Class `Hotbar`
> Renders the bottom-screen hotbar, including the transparent slot backgrounds,
- `def __init__(self, app: Any) -> None`
- `def render(self) -> None`
### Class `HeldBlock`
> Renders the 3D model of the currently equipped item or block in the player's hand.
- `def __init__(self, app: Any) -> None`
- `def render(self) -> None`
### Class `InventoryUI`
> Manages the full player inventory and crafting grid interface.
- `def __init__(self, app: Any) -> None`
- `def update_crafting(self) -> None`
- `def get_slot_pos(self, i: int) -> Tuple[float, float]`
- `def get_slot_at_mouse(self, mouse_pos: Tuple[int, int]) -> int`
- `def get_closest_valid_slot(self, mouse_pos: Tuple[int, int], drag_id: int, drag_count: int) -> int`
- `def handle_event(self, event: Any) -> None`
- `def close(self) -> None`
- `def render(self) -> None`
### Class `DebugOverlay`
> Displays an on-screen overlay with performance metrics, player coordinates,
- `def __init__(self, app: Any) -> None`
- `def render(self) -> None`

## `src/ui/menus.py`

### Class `MainMenu`
> Manages the Main Menu, World Selection, and World Creation screens.
- `def __init__(self, app: Any) -> None`
- `def trigger_action(self, action: Callable[[], None], anim_dir: int) -> None`
- `def open_options(self) -> None`
- `def toggle_game_mode(self) -> None`
- `def set_state(self, new_state: str) -> None`
- `def load_world_list(self) -> None`
- `def delete_world(self, save_name: str) -> None`
- `def create_world(self) -> None`
- `def update(self) -> None`
- `def handle_event(self, event: Any) -> None`
- `def render_bg(self) -> None`
- `def render(self) -> None`
### Class `PauseMenu`
> Provides the in-game pause screen overlay.
- `def __init__(self, app: Any) -> None`
- `def trigger_action(self, action: Callable[[], None], anim_dir: int) -> None`
- `def open_options(self) -> None`
- `def resume_game(self) -> None`
- `def quit_to_menu(self) -> None`
- `def update(self) -> None`
- `def handle_event(self, event: Any) -> None`
- `def render(self) -> None`
### Class `OptionsMenu`
> Manages the game settings screen.
- `def __init__(self, app: Any) -> None`
- `def trigger_action(self, action: Callable[[], None], anim_dir: int) -> None`
- `def update_fov(self, val: float) -> None`
- `def update_music_volume(self, val: float) -> None`
- `def update_sfx_volume(self, val: float) -> None`
- `def go_back(self) -> None`
- `def update(self) -> None`
- `def handle_event(self, event: Any) -> None`
- `def render(self) -> None`

## `src/ui/meshes.py`

### Class `CrosshairMesh`
> Generates the geometry for the on-screen crosshair.
- `def __init__(self, app: Any) -> None`
- `def get_vertex_data(self) -> NDArray[np.float32]`
### Class `BlockIconMesh`
> Handles the rendering geometry for 2D flat representations of 3D blocks.
- `def __init__(self, app: Any) -> None`
- `def get_vertex_data(self) -> NDArray[np.float32]`
### Class `UIColorMesh`
> Provides the geometry for rendering solid-color geometric elements in the UI.
- `def __init__(self, app: Any) -> None`
- `def get_vertex_data(self) -> NDArray[np.float32]`
### Class `UITextMesh`
> Generates the geometry required to display text strings on the screen.
- `def __init__(self, app: Any) -> None`
- `def get_vertex_data(self) -> NDArray[np.float32]`

## `src/ui/text.py`

### Class `TextRenderer`
> Handles the rendering of text strings into OpenGL textures.
- `def __init__(self, app: Any) -> None`
- `def get_texture(self, text: str) -> Any`
- `def get_dynamic_texture(self, text: str) -> Any`

## `src/voxel_handler.py`

### Class `VoxelHandler`
> Performs raycasting from the player's camera to interact with the voxel world.
- `def __init__(self, world: Any) -> None`
- `def add_voxel(self) -> None`
- `def rebuild_adjacent_chunks(self, world_pos: Any, is_light_update: bool) -> None`
- `def remove_voxel(self) -> None`
- `def set_voxel(self, mode: str) -> None`
- `def update(self) -> None`
- `def ray_cast(self) -> bool`
- `def get_voxel_id(self, voxel_world_pos: Any) -> Tuple[int, int, Any, Any]`

## `src/world.py`

### Class `World`
> Manages the global 3D voxel environment.
- `def __init__(self, app: Any, save_name: str, world_seed: int) -> None`
- `def update(self) -> None`
- `def process_mesh_queue(self) -> None`
- `def process_load_queue(self) -> None`
- `def _fetch_or_generate_voxels(self, x: int, y: int, z: int) -> Tuple[str, float, NDArray[np.uint8], NDArray[np.uint8], bool, bool]`
- `def stream_chunks(self) -> None`
- `def load_chunk(self, x: int, y: int, z: int) -> None`
- `def save_chunk_to_db(self, x: int, y: int, z: int, voxels: NDArray[np.uint8], lightmap: Optional[NDArray[np.uint8]]) -> None`
- `def unload_chunk(self, pos: Tuple[int, int, int]) -> None`
- `def render(self) -> None`
- `def render_water(self) -> None`
- `def save(self) -> None`

## `src/world_objects/chunk.py`

### Class `Chunk`
> Represents a 3D volumetric section of the world (e.g., 48x48x48 blocks).
- `def __init__(self, world: Any, position: Tuple[int, int, int]) -> None`
- `def get_model_matrix(self) -> Any`
- `def set_uniform(self) -> None`
- `def build_mesh(self) -> None`
- `def render(self) -> None`
- `def render_water(self) -> None`
- `def build_voxels(self) -> NDArray[np.uint8]`
- `def generate_terrain(voxels: Any, lightmap: Any, cx: int, cy: int, cz: int, perm_array: Any, perm_grad_array: Any, seed: int) -> None`
- `def fill_initial_sunlight_only(voxels: Any, lightmap: Any, cx: int, cy: int, cz: int, perm_array: Any) -> None`

## `src/world_objects/clouds.py`

### Class `Clouds`
> Manages the procedural 3D cloud layer in the sky.
- `def __init__(self, app: Any) -> None`
- `def update(self) -> None`
- `def render(self) -> None`

## `src/world_objects/item.py`

### Class `Item`
> Represents a physical, dropped 3D item entity in the world.
- `def __init__(self, app: Any, position: Any, voxel_id: Any) -> None`
- `def update(self) -> None`
- `def get_model_matrix(self) -> Any`
### Class `ItemManager`
> Manages all active Item entities in the scene.
- `def __init__(self, app: Any) -> None`
- `def add_item(self, position: Any, voxel_id: int) -> None`
- `def load_item(self, voxel_id: int, px: float, py: float, pz: float, vx: float, vy: float, vz: float) -> None`
- `def update(self) -> None`
- `def render(self) -> None`

## `src/world_objects/sky.py`

### Class `SkyMesh`
> Generates the geometry for the skybox, represented as a full-screen 2D quad.
- `def __init__(self, app: Any) -> None`
- `def get_vertex_data(self) -> NDArray[np.float32]`
### Class `Sky`
> Manages the skybox object, handling the rendering of the atmospheric
- `def __init__(self, app: Any) -> None`
- `def render(self) -> None`

## `src/world_objects/voxel_marker.py`

### Class `VoxelMarker`
> Renders a 3D wireframe highlight around the voxel currently targeted by the player.
- `def __init__(self, voxel_handler: Any) -> None`
- `def update(self) -> None`
- `def set_uniform(self) -> None`
- `def get_model_matrix(self) -> Any`
- `def render(self) -> None`

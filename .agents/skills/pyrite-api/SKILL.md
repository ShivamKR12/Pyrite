---
name: pyrite-api
description: The exact, working code API reference for the Pyrite engine. Contains all classes, methods, and signatures. You MUST read this skill before making any modifications to the codebase to prevent hallucinations.
---

# Pyrite Engine API Reference

## Class: Camera
- `def __init__(self, position, yaw, pitch)`
- `def update(self)`
- `def update_view_matrix(self)`
- `def update_vectors(self)`
- `def rotate_pitch(self, delta_y)`
- `def rotate_yaw(self, delta_x)`
- `def move_left(self, velocity)`
- `def move_right(self, velocity)`
- `def move_up(self, velocity)`
- `def move_down(self, velocity)`
- `def move_forward(self, velocity)`
- `def move_back(self, velocity)`
## Class: Frustum
- `def __init__(self, camera)`
- `def update_factors(self, vertical_fov, horizontal_fov)`
- `def is_on_frustum(self, chunk)`
### `def frustum_cull_fast(chunk_centers, out_mask, camera_position, camera_forward, camera_right, camera_up, tangent_y, tangent_x, factor_y, factor_x)`
### `def get_voxel_fast(world_x, world_y, world_z, world_voxels, chunk_positions)`
### `def get_light_fast(world_x, world_y, world_z, world_lightmaps, chunk_positions)`
### `def set_light_fast(world_x, world_y, world_z, val, world_lightmaps, chunk_positions)`
### `def propagate_light_queue(queue, tail, is_sun, world_voxels, world_lightmaps, chunk_positions)`
### `def _init_chunk_lighting(chunk_x, chunk_y, chunk_z, world_voxels, world_lightmaps, chunk_positions, queue_sun, queue_block)`
### `def init_chunk_lighting(chunk_x, chunk_y, chunk_z, world_voxels, world_lightmaps, chunk_positions)`
### `def _stitch_chunk_lighting(chunk_x, chunk_y, chunk_z, world_voxels, world_lightmaps, chunk_positions, queue_sun, queue_block)`
### `def stitch_chunk_lighting(chunk_x, chunk_y, chunk_z, world_voxels, world_lightmaps, chunk_positions)`
### `def remove_light_node(world_x, world_y, world_z, light_level, is_sun, world_lightmaps, chunk_positions, refill_queue, tail_refill, queue)`
### `def _update_light_place_block(world_x, world_y, world_z, world_voxels, world_lightmaps, chunk_positions, refill_queue, removal_queue)`
### `def update_light_place_block(world_x, world_y, world_z, world_voxels, world_lightmaps, chunk_positions)`
### `def _update_light_remove_block(world_x, world_y, world_z, world_voxels, world_lightmaps, chunk_positions, queue_sun, queue_block)`
### `def update_light_remove_block(world_x, world_y, world_z, world_voxels, world_lightmaps, chunk_positions)`
### `def _place_torch(world_x, world_y, world_z, world_voxels, world_lightmaps, chunk_positions, queue)`
### `def place_torch(world_x, world_y, world_z, world_voxels, world_lightmaps, chunk_positions)`
## Class: Pyrite
- `def __init__(self)`
- `def load_config(self)`
- `def save_config(self)`
- `def on_init(self)`
- `def init_game_session(self, save_name, force_seed, game_mode)`
- `def render_loading_screen(self, text)`
- `def update(self)`
- `def render(self)`
- `def handle_events(self)`
- `def quit_game(self)`
- `def run(self)`
### `def _seed_numba(new_seed)`
### `def set_seed(new_seed)`
### `def noise2(x, y, perm_array)`
### `def noise3(x, y, z, perm_array, perm_grad_array)`
## Class: Player
- `def __init__(self, app, position, yaw, pitch)`
- `def find_spawn_position(self)`
- `def update(self)`
- `def handle_event(self, event)`
- `def mouse_control(self)`
- `def handle_interaction(self)`
- `def keyboard_control(self)`
- `def apply_gravity(self)`
- `def move_and_collide(self)`
- `def resolve_axis(self, axis)`
- `def get_aabb(self)`
- `def aabb_intersect(a_min, a_max, b_min, b_max)`
- `def add_item(self, voxel_id)`
- `def take_damage(self, amount)`
- `def respawn(self)`
## Class: ThreadSampleBuffer
- `def __init__(self, max_samples)`
- `def record(self, category, elapsed_time)`
## Class: Profiler
- `def __init__(self, max_samples_per_category)`
- `def _get_buffer(self)`
- `def start_frame(self)`
- `def end_frame(self)`
- `def record(self, category, elapsed_time)`
- `def measure(self, category)`
- `def profile_func(self, category)`
- `def save_report(self, filename)`
## Class: Scene
- `def __init__(self, app, save_name, seed)`
- `def update(self)`
- `def render(self)`
### `def get_path(relative_path)`
## Class: ShaderProgram
- `def __init__(self, app)`
- `def set_uniforms_on_init(self)`
- `def update(self)`
- `def get_program(self, shader_name)`
## Class: Sounds
- `def __init__(self, app)`
- `def set_sfx_volume(self, value)`
- `def play_walk(self, voxel_id)`
- `def play_break(self, voxel_id)`
- `def play_place(self, voxel_id)`
- `def play_jump(self, voxel_id)`
- `def play_breaking(self, voxel_id, mining_time, mining_duration)`
- `def play_place_block(self)`
### `def get_biome(x, z, perm_array)`
### `def get_height(x, z, perm_array)`
### `def get_index(x, y, z)`
### `def set_voxel_column(voxels, x, z, chunk_x, chunk_y, chunk_z, perm_array, perm_grad_array)`
### `def place_tree(voxels, x, y, z, voxel_id, tree_prob)`
### `def fill_initial_sunlight(voxels, lightmap, chunk_x, chunk_y, chunk_z, perm_array)`
## Class: Textures
- `def __init__(self, app)`
- `def load(self, file_name, is_tex_array, rotation, flip_x, flip_y)`
## Class: VoxelHandler
- `def __init__(self, world)`
- `def add_voxel(self)`
- `def rebuild_adjacent_chunks(self, world_pos, is_light_update)`
- `def remove_voxel(self)`
- `def set_voxel(self, mode)`
- `def update(self)`
- `def ray_cast(self)`
- `def get_voxel_id(self, voxel_world_pos)`
## Class: World
- `def __init__(self, app, save_name, world_seed)`
- `def update(self)`
- `def process_mesh_queue(self)`
- `def process_load_queue(self)`
- `def _fetch_or_generate_voxels(self, x, y, z)`
- `def stream_chunks(self)`
- `def load_chunk(self, x, y, z)`
- `def save_chunk_to_db(self, x, y, z, voxels, lightmap)`
- `def unload_chunk(self, position)`
- `def render(self)`
- `def render_water(self)`
- `def save(self)`
## Class: BaseMesh
- `def __init__(self)`
- `def get_vertex_data(self)`
- `def get_vao(self)`
- `def render(self)`
## Class: ChunkMesh
- `def __init__(self, chunk)`
- `def render(self)`
- `def render_water(self)`
- `def get_vao(self)`
- `def get_vertex_data(self)`
### `def get_ao(local_pos, world_pos, chunk_voxels, world_voxels, chunk_positions, plane)`
### `def get_vertex_light(local_vertex_pos, world_vertex_pos, plane, face_light, chunk_voxels, chunk_lightmap, world_voxels, world_lightmaps, chunk_positions)`
### `def pack_data(x, y, z, voxel_id, face_id, ao_id, flip_id, light_val)`
### `def get_chunk_index(world_voxel_pos, chunk_positions)`
### `def get_neighbor_voxel_id(local_voxel_pos, world_voxel_pos, chunk_voxels, world_voxels, chunk_positions)`
### `def get_neighbor_light(local_voxel_pos, world_voxel_pos, chunk_lightmap, world_lightmaps, chunk_positions)`
### `def is_transparent(voxel_id)`
### `def is_void(local_voxel_pos, world_voxel_pos, chunk_voxels, world_voxels, chunk_positions)`
### `def add_data(vertex_data, index)`
### `def build_chunk_mesh(chunk_voxels, chunk_lightmap, format_size, chunk_pos, world_voxels, world_lightmaps, chunk_positions)`
## Class: CloudMesh
- `def __init__(self, app)`
- `def get_vertex_data(self)`
- `def gen_clouds(cloud_data, perm_array)`
- `def build_mesh(cloud_data)`
## Class: CubeMesh
- `def __init__(self, app)`
- `def get_data(vertices, indices)`
- `def get_vertex_data(self)`
## Class: ItemMesh
- `def __init__(self, app)`
- `def get_vertex_data(self)`
## Class: ObjMesh
- `def __init__(self, app, object_path, texture_id)`
- `def render(self)`
- `def parse_mtl(self, material_path)`
- `def get_vertex_data(self)`
### `def get_shared_resource(app, resource_type)`
## Class: UINode
- `def __init__(self, size)`
- `def add_child(self, child)`
- `def get_global_pos(self)`
- `def update_layout(self)`
- `def update(self, mouse_pos)`
- `def handle_event(self, event)`
- `def render(self, offset, alpha)`
## Class: VBox
- `def __init__(self, position, spacing)`
- `def update_layout(self)`
## Class: Button
- `def __init__(self, app, text, position, size, action, border_radius, elevation)`
- `def check_hover(self, mouse_pos)`
- `def update(self, mouse_pos)`
- `def handle_event(self, event)`
- `def render(self, offset, alpha)`
## Class: WorldButton
- `def __init__(self, app, save_name, display_name, seed, game_mode, creation_date, last_played, position, size, action, border_radius, elevation)`
- `def check_hover(self, mouse_pos)`
- `def update(self, mouse_pos)`
- `def handle_event(self, event)`
- `def render(self, offset, alpha)`
## Class: TextInput
- `def __init__(self, app, position, size, label)`
- `def handle_event(self, event)`
- `def render(self, offset, alpha)`
## Class: Slider
- `def __init__(self, app, text, position, size, min_val, max_val, config_key, action, is_int)`
- `def update(self, mouse_pos)`
- `def handle_event(self, event)`
- `def render(self, offset, alpha)`
## Class: Toggle
- `def __init__(self, app, text, position, size, config_key, action)`
- `def update(self, mouse_pos)`
- `def handle_event(self, event)`
- `def render(self, offset, alpha)`
## Class: Crosshair
- `def __init__(self, app)`
- `def render(self)`
## Class: Hotbar
- `def __init__(self, app)`
- `def render(self)`
## Class: HeldBlock
- `def __init__(self, app)`
- `def render(self)`
## Class: InventoryUI
- `def __init__(self, app)`
- `def update_crafting(self)`
- `def get_slot_pos(self, i)`
- `def get_slot_at_mouse(self, mouse_pos)`
- `def get_closest_valid_slot(self, mouse_pos, drag_id, drag_count)`
- `def handle_event(self, event)`
- `def close(self)`
- `def render(self)`
## Class: DebugOverlay
- `def __init__(self, app)`
- `def render(self)`
## Class: MainMenu
- `def __init__(self, app)`
- `def trigger_action(self, action, animation_direction)`
- `def open_options(self)`
- `def toggle_game_mode(self)`
- `def set_state(self, new_state)`
- `def load_world_list(self)`
- `def delete_world(self, save_name)`
- `def create_world(self)`
- `def update(self)`
- `def handle_event(self, event)`
- `def render_bg(self)`
- `def render(self)`
## Class: PauseMenu
- `def __init__(self, app)`
- `def trigger_action(self, action, animation_direction)`
- `def open_options(self)`
- `def resume_game(self)`
- `def quit_to_menu(self)`
- `def update(self)`
- `def handle_event(self, event)`
- `def render(self)`
## Class: OptionsMenu
- `def __init__(self, app)`
- `def trigger_action(self, action, animation_direction)`
- `def update_fov(self, val)`
- `def update_music_volume(self, val)`
- `def update_sfx_volume(self, val)`
- `def go_back(self)`
- `def update(self)`
- `def handle_event(self, event)`
- `def render(self)`
## Class: CrosshairMesh
- `def __init__(self, app)`
- `def get_vertex_data(self)`
## Class: BlockIconMesh
- `def __init__(self, app)`
- `def get_vertex_data(self)`
## Class: UIColorMesh
- `def __init__(self, app)`
- `def get_vertex_data(self)`
## Class: UITextMesh
- `def __init__(self, app)`
- `def get_vertex_data(self)`
## Class: TextRenderer
- `def __init__(self, app)`
- `def get_texture(self, text)`
- `def get_dynamic_texture(self, text)`
## Class: Chunk
- `def __init__(self, world, position)`
- `def get_model_matrix(self)`
- `def set_uniform(self)`
- `def build_mesh(self)`
- `def render(self)`
- `def render_water(self)`
- `def build_voxels(self)`
- `def generate_terrain(voxels, lightmap, chunk_x, chunk_y, chunk_z, perm_array, perm_grad_array, seed)`
- `def fill_initial_sunlight_only(voxels, lightmap, chunk_x, chunk_y, chunk_z, perm_array)`
## Class: Clouds
- `def __init__(self, app)`
- `def update(self)`
- `def render(self)`
## Class: Item
- `def __init__(self, app, position, voxel_id)`
- `def update(self)`
- `def get_model_matrix(self)`
## Class: ItemManager
- `def __init__(self, app)`
- `def add_item(self, position, voxel_id)`
- `def load_item(self, voxel_id, position_x, position_y, position_z, velocity_x, velocity_y, velocity_z)`
- `def update(self)`
- `def render(self)`
## Class: SkyMesh
- `def __init__(self, app)`
- `def get_vertex_data(self)`
## Class: Sky
- `def __init__(self, app)`
- `def render(self)`
## Class: VoxelMarker
- `def __init__(self, voxel_handler)`
- `def update(self)`
- `def set_uniform(self)`
- `def get_model_matrix(self)`
- `def render(self)`

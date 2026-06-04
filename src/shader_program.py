"""
GLSL Shader program compilation and uniform management.

This module manages the ModernGL shader programs used for rendering the world,
UI, and post-processing effects. It loads vertex and fragment shaders from disk,
compiles them, and provides a central interface for updating dynamic uniforms 
(like camera matrices, fog density, and time of day) every frame.
"""

import numpy as np
from pyglm import glm
from typing import Any
from numpy.typing import NDArray

from settings import (
    BG_COLOR, FOG_DENSITY_BASE, CLOUD_FOG_DENSITY_BASE, DAY_NIGHT_SPEED,
    UNDERWATER_FOG_COLOR, UNDERWATER_FOG_DENSITY, UNDERWATER_FOG_MAX_OPACITY, 
    CLOUD_SCALE, CENTER_XZ, TEXTURE_MAP, get_path
)
from profiler import global_profiler


class ShaderProgram:
    """
    Compiles, links, and manages all GLSL shader programs used by the engine.
    
    Handles sending static and dynamic uniform data (view matrices, lighting, fog) 
    to the GPU to ensure visuals react appropriately to player movement and time.
    
    Args:
        app (Any): The main application context containing the ModernGL instance.
    """
    @global_profiler.profile_func("ShaderProgram_Init")
    def __init__(self, app: Any) -> None:
        """
        Retrieves the GLSL source code for chunks, markers, UI elements, and environments,
        then registers them into ModernGL programs.
        """
        self.app: Any = app
        self.ctx: Any = app.ctx
        self.player: Any = app.player
        
        # -------- shaders -------- #
        self.chunk: Any = self.get_program(shader_name='chunk')
        self.voxel_marker: Any = self.get_program(shader_name='voxel_marker')
        self.clouds: Any = self.get_program('clouds')
        self.sky: Any = self.get_program('sky')
        self.quad: Any = self.get_program('quad')
        self.ui_block: Any = self.get_program('ui_block')
        self.ui_color: Any = self.get_program('ui_color')
        self.ui_text: Any = self.get_program('ui_text')
        self.item: Any = self.get_program('item')
        self.obj: Any = self.get_program('obj')
        
        # ------------------------- #
        self.set_uniforms_on_init()

    @global_profiler.profile_func("ShaderProgram_SetUniformsOnInit")
    def set_uniforms_on_init(self) -> None:
        """
        Initializes static shader uniforms (like texture assignments, texture mapping arrays,
        and basic projection matrices) that only need to be uploaded once.
        """
        # Build the fast lookup array for the shaders
        tex_map: NDArray[np.int32] = np.zeros(256, dtype='int32')
        
        for uid, tex_id in TEXTURE_MAP.items():
            tex_map[uid] = tex_id
        tex_map_bytes: bytes = tex_map.tobytes()

        # chunk
        self.chunk['m_proj'].write(self.player.m_proj)
        self.chunk['m_model'].write(glm.mat4())
        self.chunk['u_texture_array_0'] = 1
        self.chunk['bg_color'].write(BG_COLOR)
        
        if 'u_texture_map' in self.chunk:
            self.chunk['u_texture_map'].write(tex_map_bytes)

        # marker
        self.voxel_marker['m_proj'].write(self.player.m_proj)
        self.voxel_marker['m_model'].write(glm.mat4())
        self.voxel_marker['u_texture_0'] = 0
        self.voxel_marker['u_texture_breaking'] = 3
        self.voxel_marker['mining_progress'] = 0.0
        self.voxel_marker['is_bbox'] = 0

        # clouds
        self.clouds['m_proj'].write(self.player.m_proj)
        self.clouds['center'] = CENTER_XZ
        self.clouds['bg_color'].write(BG_COLOR)
        self.clouds['cloud_scale'] = CLOUD_SCALE
        
        # sky
        self.sky['m_inv_proj'].write(glm.inverse(self.player.m_proj))
        self.sky['m_inv_view'].write(glm.inverse(self.player.m_view))
        self.sky['bg_color'].write(BG_COLOR)
        
        # quad (used for 2D UI)
        self.quad['m_proj'].write(glm.mat4())
        self.quad['m_view'].write(glm.mat4())
        self.quad['m_model'].write(glm.mat4())
        
        # ui block
        self.ui_block['u_texture_array_0'] = 1
        if 'u_texture_map' in self.ui_block:
            self.ui_block['u_texture_map'].write(tex_map_bytes)
        
        # ui text
        self.ui_text['u_texture_0'] = 4
        if 'u_alpha' in self.ui_text:
            self.ui_text['u_alpha'] = 1.0
        if 'u_color' in self.ui_text:
            self.ui_text['u_color'] = (1.0, 1.0, 1.0, 1.0)
        
        if 'u_clip' in self.ui_color:
            self.ui_color['u_clip'] = (-2.0, -2.0, 2.0, 2.0)
        if 'u_clip' in self.ui_text:
            self.ui_text['u_clip'] = (-2.0, -2.0, 2.0, 2.0)
        
        # item
        self.item['m_proj'].write(self.player.m_proj)
        self.item['m_model'].write(glm.mat4())
        self.item['u_texture_array_0'] = 1
        self.item['bg_color'].write(BG_COLOR)
        if 'u_texture_map' in self.item:
            self.item['u_texture_map'].write(tex_map_bytes)
        
        # obj
        self.obj['m_proj'].write(self.player.m_proj)
        self.obj['m_model'].write(glm.mat4())
        self.obj['u_use_texture'] = False
        self.obj['bg_color'].write(BG_COLOR)

    @global_profiler.profile_func("ShaderProgram_Update")
    def update(self) -> None:
        """
        Updates dynamic uniforms every frame. Sends the camera's view matrix, 
        calculates dynamic sun direction/fog density based on the day-night cycle,
        and syncs UI animations (like mining progress).
        """
        self.chunk['m_view'].write(self.player.m_view)
        
        if 'u_time' in self.chunk:
            self.chunk['u_time'] = self.app.world_session_time # Make sure the shader actually has the uniform before writing
        
        self.voxel_marker['m_view'].write(self.player.m_view)
        self.clouds['m_view'].write(self.player.m_view)
        self.clouds['player_pos'].write(self.player.position)
        self.item['m_view'].write(self.player.m_view)
        self.obj['m_view'].write(self.player.m_view)
        
        # Update projection matrix dynamically for FOV zooming
        self.chunk['m_proj'].write(self.player.m_proj)
        self.voxel_marker['m_proj'].write(self.player.m_proj)
        self.clouds['m_proj'].write(self.player.m_proj)
        self.item['m_proj'].write(self.player.m_proj)
        self.obj['m_proj'].write(self.player.m_proj)
        self.sky['m_inv_proj'].write(glm.inverse(self.player.m_proj))
        self.sky['m_inv_view'].write(glm.inverse(self.player.m_view))
        if 'u_time' in self.sky:
            self.sky['u_time'] = self.app.world_session_time

        time_speed: float = DAY_NIGHT_SPEED # Adjust this to make the day longer or shorter based on world_session_time
        sun_y: float = float(glm.cos(self.app.world_session_time * time_speed))

        is_underwater: bool = getattr(self.player, 'head_in_water', False)
        bg_color: Any
        fog_density: float
        cloud_fog_density: float
        fog_max_opacity: float
        
        if is_underwater:
            # Underwater fog!
            bg_color = UNDERWATER_FOG_COLOR
            fog_density = UNDERWATER_FOG_DENSITY
            cloud_fog_density = FOG_DENSITY_BASE / 10.0 # Make clouds just barely visible underwater
            fog_max_opacity = UNDERWATER_FOG_MAX_OPACITY # Cap underwater fog so distant terrain remains visible
        
        else:
            bg_color = BG_COLOR * max(0.05, sun_y + 0.2) # Sky gets dark when sun goes down
            render_dist: float = max(1.0, float(self.app.config.get('render_distance', 6)))
            fog_density = FOG_DENSITY_BASE / (render_dist ** 2)
            cloud_fog_density = CLOUD_FOG_DENSITY_BASE / (render_dist ** 2)
            fog_max_opacity = 1.0  # Fully hide chunk boundaries above water
            
        if 'u_fog_density' in self.chunk:
            self.chunk['u_fog_density'] = fog_density
            
            if 'u_fog_max_opacity' in self.chunk:
                self.chunk['u_fog_max_opacity'] = fog_max_opacity
        
        if 'u_fog_density' in self.item:
            self.item['u_fog_density'] = fog_density
            
            if 'u_fog_max_opacity' in self.item:
                self.item['u_fog_max_opacity'] = fog_max_opacity
        
        if 'u_fog_density' in self.obj:
            self.obj['u_fog_density'] = fog_density
            
            if 'u_fog_max_opacity' in self.obj:
                self.obj['u_fog_max_opacity'] = fog_max_opacity
        
        if 'u_fog_density' in self.clouds:
            self.clouds['u_fog_density'] = cloud_fog_density
            
            if 'u_fog_max_opacity' in self.clouds:
                self.clouds['u_fog_max_opacity'] = fog_max_opacity
        
        if 'u_underwater_tint' in self.chunk:
            self.chunk['u_underwater_tint'] = self.app.config.get('underwater_tint', False)

        mining_progress: float = self.player.mining_time / self.player.mining_duration if self.player.mining_time > 0 else 0.0
        self.voxel_marker['mining_progress'] = mining_progress
        
        # Day / Night Cycle Lighting
        sun_dir: Any = glm.normalize(glm.vec3(0.0, sun_y, glm.sin(self.app.world_session_time * time_speed)))
        
        # Safely write sun direction only if the shader currently supports it
        if 'u_sun_direction' in self.chunk:
            self.chunk['u_sun_direction'].write(sun_dir)
        if 'u_sun_direction' in self.item:
            self.item['u_sun_direction'].write(sun_dir)
        if 'u_sun_direction' in self.obj:
            self.obj['u_sun_direction'].write(sun_dir)
        if 'u_sun_direction' in self.sky:
            self.sky['u_sun_direction'].write(sun_dir)
        if 'u_sun_direction' in self.clouds:
            self.clouds['u_sun_direction'].write(sun_dir)
        
        self.app.bg_color = bg_color
        self.chunk['bg_color'].write(bg_color)
        self.clouds['bg_color'].write(bg_color)
        self.item['bg_color'].write(bg_color)
        self.obj['bg_color'].write(bg_color)
        self.sky['bg_color'].write(bg_color)

    @global_profiler.profile_func("ShaderProgram_GetProgram")
    def get_program(self, shader_name: str) -> Any:
        """
        Helper function to load and compile a matching pair of .vert and .frag shader files from disk.
        """
        with open(get_path(f'src/shaders/{shader_name}.vert'), 'r', encoding='utf-8') as file:
            vertex_shader: str = file.read()
        
        with open(get_path(f'src/shaders/{shader_name}.frag'), 'r', encoding='utf-8') as file:
            fragment_shader: str = file.read()
        
        program: Any = self.ctx.program(vertex_shader=vertex_shader, fragment_shader=fragment_shader)
        
        return program

"""
GLSL Shader program compilation and uniform management.

This module manages the ModernGL shader programs used for rendering the world,
UI, and post-processing effects. It loads vertex and fragment shaders from disk,
compiles them, and provides a central interface for updating dynamic uniforms
(like camera matrices, fog density, and time of day) every frame.
"""

from typing import Any

import numpy as np
from numpy.typing import NDArray
from pyglm import glm

from profiler import global_profiler
from settings import (
    BG_COLOR,
    CENTER_XZ,
    CLOUD_FOG_DENSITY_BASE,
    CLOUD_SCALE,
    DAY_NIGHT_SPEED,
    FOG_DENSITY_BASE,
    TEXTURE_MAP,
    UNDERWATER_FOG_COLOR,
    UNDERWATER_FOG_DENSITY,
    UNDERWATER_FOG_MAX_OPACITY,
    get_path,
)


class ShaderProgram:
    """
    Compiles, links, and manages all GLSL shader programs used by the engine.

    Handles sending static and dynamic uniform data (view matrices, lighting, fog)
    to the GPU to ensure visuals react appropriately to player movement and time.

    Args:
        app (Any): The main application context containing the ModernGL instance.
    """

    @global_profiler.profile_func('ShaderProgram_Init')
    def __init__(self, app: Any) -> None:
        """
        Retrieves the GLSL source code for chunks, markers, UI elements, and environments,
        then registers them into ModernGL programs.
        """
        # Variable assignments
        self.app: Any = app
        self.ctx: Any = app.ctx
        self.player: Any = app.player

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

        # Execute expressions
        self.set_uniforms_on_init()

    @global_profiler.profile_func('ShaderProgram_SetUniformsOnInit')
    def set_uniforms_on_init(self) -> None:
        """
        Initializes static shader uniforms (like texture assignments, texture mapping arrays,
        and basic projection matrices) that only need to be uploaded once.
        """
        # Variable assignments
        tex_map: NDArray[np.int32] = np.zeros(256, dtype='int32')

        # Loop processing
        for uid, tex_id in TEXTURE_MAP.items():
            # Variable assignments
            tex_map[uid] = tex_id
        # Variable assignments
        tex_map_bytes: bytes = tex_map.tobytes()

        # Execute expressions
        self.chunk['m_proj'].write(self.player.m_proj)
        self.chunk['m_model'].write(glm.mat4())
        # Variable assignments
        self.chunk['u_texture_array_0'] = 1
        # Execute expressions
        self.chunk['bg_color'].write(BG_COLOR)

        # Conditional logic
        if 'u_texture_map' in self.chunk:
            # Execute expressions
            self.chunk['u_texture_map'].write(tex_map_bytes)

        # Execute expressions
        self.voxel_marker['m_proj'].write(self.player.m_proj)
        self.voxel_marker['m_model'].write(glm.mat4())
        # Variable assignments
        self.voxel_marker['u_texture_0'] = 0
        self.voxel_marker['u_texture_breaking'] = 3
        self.voxel_marker['mining_progress'] = 0.0
        self.voxel_marker['is_bbox'] = 0

        # Execute expressions
        self.clouds['m_proj'].write(self.player.m_proj)
        # Variable assignments
        self.clouds['center'] = CENTER_XZ
        # Execute expressions
        self.clouds['bg_color'].write(BG_COLOR)
        # Variable assignments
        self.clouds['cloud_scale'] = CLOUD_SCALE

        # Execute expressions
        self.sky['m_inv_proj'].write(glm.inverse(self.player.m_proj))
        self.sky['m_inv_view'].write(glm.inverse(self.player.m_view))
        self.sky['bg_color'].write(BG_COLOR)

        self.quad['m_proj'].write(glm.mat4())
        self.quad['m_view'].write(glm.mat4())
        self.quad['m_model'].write(glm.mat4())

        # Variable assignments
        self.ui_block['u_texture_array_0'] = 1
        # Conditional logic
        if 'u_texture_map' in self.ui_block:
            # Execute expressions
            self.ui_block['u_texture_map'].write(tex_map_bytes)

        # Variable assignments
        self.ui_text['u_texture_0'] = 4
        # Conditional logic
        if 'u_alpha' in self.ui_text:
            # Variable assignments
            self.ui_text['u_alpha'] = 1.0
        if 'u_color' in self.ui_text:
            # Variable assignments
            self.ui_text['u_color'] = (1.0, 1.0, 1.0, 1.0)

        if 'u_clip' in self.ui_color:
            # Variable assignments
            self.ui_color['u_clip'] = (-2.0, -2.0, 2.0, 2.0)
        if 'u_clip' in self.ui_text:
            # Variable assignments
            self.ui_text['u_clip'] = (-2.0, -2.0, 2.0, 2.0)

        # Execute expressions
        self.item['m_proj'].write(self.player.m_proj)
        self.item['m_model'].write(glm.mat4())
        # Variable assignments
        self.item['u_texture_array_0'] = 1
        # Execute expressions
        self.item['bg_color'].write(BG_COLOR)
        # Conditional logic
        if 'u_texture_map' in self.item:
            # Execute expressions
            self.item['u_texture_map'].write(tex_map_bytes)

        # Execute expressions
        self.obj['m_proj'].write(self.player.m_proj)
        self.obj['m_model'].write(glm.mat4())
        # Variable assignments
        self.obj['u_use_texture'] = False
        # Execute expressions
        self.obj['bg_color'].write(BG_COLOR)

    @global_profiler.profile_func('ShaderProgram_Update')
    def update(self) -> None:
        """
        Updates dynamic uniforms every frame. Sends the camera's view matrix,
        calculates dynamic sun direction/fog density based on the day-night cycle,
        and syncs UI animations (like mining progress).
        """
        # Execute expressions
        self.chunk['m_view'].write(self.player.m_view)

        # Conditional logic
        if 'u_time' in self.chunk:
            # Variable assignments
            self.chunk['u_time'] = (
                self.app.world_session_time
            )  # Make sure the shader actually has the uniform before writing

        # Execute expressions
        self.voxel_marker['m_view'].write(self.player.m_view)
        self.clouds['m_view'].write(self.player.m_view)
        self.clouds['player_pos'].write(self.player.position)
        self.item['m_view'].write(self.player.m_view)
        self.obj['m_view'].write(self.player.m_view)

        self.chunk['m_proj'].write(self.player.m_proj)
        self.voxel_marker['m_proj'].write(self.player.m_proj)
        self.clouds['m_proj'].write(self.player.m_proj)
        self.item['m_proj'].write(self.player.m_proj)
        self.obj['m_proj'].write(self.player.m_proj)
        self.sky['m_inv_proj'].write(glm.inverse(self.player.m_proj))
        self.sky['m_inv_view'].write(glm.inverse(self.player.m_view))
        # Conditional logic
        if 'u_time' in self.sky:
            # Variable assignments
            self.sky['u_time'] = self.app.world_session_time

        # Variable assignments
        time_speed: float = DAY_NIGHT_SPEED  # Adjust this to make the day longer or shorter based on world_session_time
        sun_y: float = float(glm.cos(self.app.world_session_time * time_speed))

        is_underwater: bool = getattr(self.player, 'head_in_water', False)
        bg_color: Any
        fog_density: float
        cloud_fog_density: float
        fog_max_opacity: float

        # Conditional logic
        if is_underwater:
            # Variable assignments
            bg_color = UNDERWATER_FOG_COLOR
            fog_density = UNDERWATER_FOG_DENSITY
            cloud_fog_density = FOG_DENSITY_BASE / 10.0  # Make clouds just barely visible underwater
            fog_max_opacity = UNDERWATER_FOG_MAX_OPACITY  # Cap underwater fog so distant terrain remains visible

        else:
            # Variable assignments
            bg_color = BG_COLOR * max(0.05, sun_y + 0.2)  # Sky gets dark when sun goes down
            render_dist: float = max(1.0, float(self.app.config.get('render_distance', 6)))
            fog_density = FOG_DENSITY_BASE / (render_dist**2)
            cloud_fog_density = CLOUD_FOG_DENSITY_BASE / (render_dist**2)
            fog_max_opacity = 1.0  # Fully hide chunk boundaries above water

        if 'u_fog_density' in self.chunk:
            # Variable assignments
            self.chunk['u_fog_density'] = fog_density

            # Conditional logic
            if 'u_fog_max_opacity' in self.chunk:
                # Variable assignments
                self.chunk['u_fog_max_opacity'] = fog_max_opacity

        if 'u_fog_density' in self.item:
            # Variable assignments
            self.item['u_fog_density'] = fog_density

            # Conditional logic
            if 'u_fog_max_opacity' in self.item:
                # Variable assignments
                self.item['u_fog_max_opacity'] = fog_max_opacity

        if 'u_fog_density' in self.obj:
            # Variable assignments
            self.obj['u_fog_density'] = fog_density

            # Conditional logic
            if 'u_fog_max_opacity' in self.obj:
                # Variable assignments
                self.obj['u_fog_max_opacity'] = fog_max_opacity

        if 'u_fog_density' in self.clouds:
            # Variable assignments
            self.clouds['u_fog_density'] = cloud_fog_density

            # Conditional logic
            if 'u_fog_max_opacity' in self.clouds:
                # Variable assignments
                self.clouds['u_fog_max_opacity'] = fog_max_opacity

        if 'u_underwater_tint' in self.chunk:
            # Variable assignments
            self.chunk['u_underwater_tint'] = self.app.config.get('underwater_tint', False)

        # Variable assignments
        mining_progress: float = (
            self.player.mining_time / self.player.mining_duration if self.player.mining_time > 0 else 0.0
        )
        self.voxel_marker['mining_progress'] = mining_progress

        sun_dir: Any = glm.normalize(glm.vec3(0.0, sun_y, glm.sin(self.app.world_session_time * time_speed)))

        # Conditional logic
        if 'u_sun_direction' in self.chunk:
            # Execute expressions
            self.chunk['u_sun_direction'].write(sun_dir)
        if 'u_sun_direction' in self.item:
            # Execute expressions
            self.item['u_sun_direction'].write(sun_dir)
        if 'u_sun_direction' in self.obj:
            # Execute expressions
            self.obj['u_sun_direction'].write(sun_dir)
        if 'u_sun_direction' in self.sky:
            # Execute expressions
            self.sky['u_sun_direction'].write(sun_dir)
        if 'u_sun_direction' in self.clouds:
            # Execute expressions
            self.clouds['u_sun_direction'].write(sun_dir)

        # Variable assignments
        self.app.bg_color = bg_color
        # Execute expressions
        self.chunk['bg_color'].write(bg_color)
        self.clouds['bg_color'].write(bg_color)
        self.item['bg_color'].write(bg_color)
        self.obj['bg_color'].write(bg_color)
        self.sky['bg_color'].write(bg_color)

    @global_profiler.profile_func('ShaderProgram_GetProgram')
    def get_program(self, shader_name: str) -> Any:
        """
        Helper function to load and compile a matching pair of .vert and .frag shader files from disk.
        """
        # Context management
        with open(get_path(f'src/shaders/{shader_name}.vert'), 'r', encoding='utf-8') as file:
            # Variable assignments
            vertex_shader: str = file.read()

        with open(get_path(f'src/shaders/{shader_name}.frag'), 'r', encoding='utf-8') as file:
            # Variable assignments
            fragment_shader: str = file.read()

        # Variable assignments
        program: Any = self.ctx.program(vertex_shader=vertex_shader, fragment_shader=fragment_shader)

        # Return result
        return program

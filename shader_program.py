from settings import *


class ShaderProgram:
    def __init__(self, app):
        self.app = app
        self.ctx = app.ctx
        self.player = app.player
        # -------- shaders -------- #
        self.chunk = self.get_program(shader_name='chunk')
        self.voxel_marker = self.get_program(shader_name='voxel_marker')
        self.water = self.get_program('water')
        self.clouds = self.get_program('clouds')
        self.quad = self.get_program('quad')
        self.ui_block = self.get_program('ui_block')
        # ------------------------- #
        self.set_uniforms_on_init()

    def set_uniforms_on_init(self):
        # chunk
        self.chunk['m_proj'].write(self.player.m_proj)
        self.chunk['m_model'].write(glm.mat4())
        self.chunk['u_texture_array_0'] = 1
        self.chunk['bg_color'].write(BG_COLOR)
        self.chunk['water_line'] = WATER_LINE

        # marker
        self.voxel_marker['m_proj'].write(self.player.m_proj)
        self.voxel_marker['m_model'].write(glm.mat4())
        self.voxel_marker['u_texture_0'] = 0
        self.voxel_marker['u_texture_breaking'] = 3
        self.voxel_marker['mining_progress'] = 0.0

        # water
        self.water['m_proj'].write(self.player.m_proj)
        self.water['u_texture_0'] = 2
        self.water['water_area'] = WATER_AREA
        self.water['water_line'] = WATER_LINE

        # clouds
        self.clouds['m_proj'].write(self.player.m_proj)
        self.clouds['center'] = CENTER_XZ
        self.clouds['bg_color'].write(BG_COLOR)
        self.clouds['cloud_scale'] = CLOUD_SCALE
        
        # quad (used for 2D UI)
        self.quad['m_proj'].write(glm.mat4())
        self.quad['m_view'].write(glm.mat4())
        self.quad['m_model'].write(glm.mat4())
        
        # ui block
        self.ui_block['u_texture_array_0'] = 1

    def update(self):
        self.chunk['m_view'].write(self.player.m_view)
        self.voxel_marker['m_view'].write(self.player.m_view)
        self.water['m_view'].write(self.player.m_view)
        self.water['u_time'] = self.app.time
        self.clouds['m_view'].write(self.player.m_view)
        
        mining_progress = self.player.mining_time / self.player.mining_duration if self.player.mining_time > 0 else 0.0
        self.voxel_marker['mining_progress'] = mining_progress
        
        # Day / Night Cycle Lighting
        time_speed = 1.0 # Adjust this to make the day longer or shorter
        sun_y = glm.cos(self.app.time * time_speed)
        sun_dir = glm.normalize(glm.vec3(0.0, sun_y, glm.sin(self.app.time * time_speed)))
        self.chunk['u_sun_direction'].write(sun_dir)
        
        bg_color = BG_COLOR * max(0.05, sun_y + 0.2) # Sky gets dark when sun goes down
        self.chunk['bg_color'].write(bg_color)
        self.clouds['bg_color'].write(bg_color)

    def get_program(self, shader_name):
        with open(f'shaders/{shader_name}.vert') as file:
            vertex_shader = file.read()

        with open(f'shaders/{shader_name}.frag') as file:
            fragment_shader = file.read()

        program = self.ctx.program(vertex_shader=vertex_shader, fragment_shader=fragment_shader)
        return program

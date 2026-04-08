from settings import *
from meshes.base_mesh import BaseMesh
import numpy as np
import glm

class CrosshairMesh(BaseMesh):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.ctx = self.app.ctx
        self.program = self.app.shader_program.quad
        self.vbo_format = '3f 3f'
        self.attrs = ('in_position', 'in_color')
        self.vao = self.get_vao()

    def get_vertex_data(self):
        w = 0.015
        h = w * ASPECT_RATIO
        # Creates a perfect '+' sign in the center of the screen
        vertices = [
            # Horizontal line
            (-w, -0.002 * ASPECT_RATIO, 0.0), (w, -0.002 * ASPECT_RATIO, 0.0), (w, 0.002 * ASPECT_RATIO, 0.0),
            (-w, -0.002 * ASPECT_RATIO, 0.0), (w, 0.002 * ASPECT_RATIO, 0.0), (-w, 0.002 * ASPECT_RATIO, 0.0),
            # Vertical line
            (-0.002, -h, 0.0), (0.002, -h, 0.0), (0.002, h, 0.0),
            (-0.002, -h, 0.0), (0.002, h, 0.0), (-0.002, h, 0.0)
        ]
        colors = [(0.9, 0.9, 0.9) for _ in vertices]
        return np.hstack([vertices, colors]).astype('float32')

class BlockIconMesh(BaseMesh):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.ctx = self.app.ctx
        self.program = self.app.shader_program.ui_block
        self.vbo_format = '2f 2f'
        self.attrs = ('in_position', 'in_tex_coord')
        self.vao = self.get_vao()

    def get_vertex_data(self):
        # Standard normalized quad [-1, 1]
        vertices = [
            (-1.0, -1.0), ( 1.0, -1.0), ( 1.0,  1.0),
            (-1.0, -1.0), ( 1.0,  1.0), (-1.0,  1.0)
        ]
        tex_coords = [(0, 0), (1, 0), (1, 1), (0, 0), (1, 1), (0, 1)]
        return np.hstack([vertices, tex_coords]).astype('float32')

class UIColorMesh(BaseMesh):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.ctx = self.app.ctx
        self.program = self.app.shader_program.ui_color
        self.vbo_format = '2f'
        self.attrs = ('in_position',)
        self.vao = self.get_vao()

    def get_vertex_data(self):
        vertices = [
            (-1.0, -1.0), ( 1.0, -1.0), ( 1.0,  1.0),
            (-1.0, -1.0), ( 1.0,  1.0), (-1.0,  1.0)
        ]
        return np.array(vertices, dtype='float32')

class Crosshair:
    def __init__(self, app):
        self.app = app
        self.mesh = CrosshairMesh(app)

    def render(self):
        self.mesh.render()

class Hotbar:
    def __init__(self, app):
        self.app = app
        self.block_mesh = BlockIconMesh(app)
        self.color_mesh = UIColorMesh(app)
        
    def render(self):
        player = self.app.player
        s = 0.045  # Base scale for blocks
        slot_s = 0.06 # Scale of slot background
        spacing = 0.13
        start_x = -4 * spacing
        y = -0.85
        
        # 1. Draw the transparent slot backgrounds and selection frame
        for i in range(9):
            x = start_x + i * spacing
            is_selected = (i == player.hotbar_index)
            
            if is_selected:
                # Draw white outline frame
                sel_s = slot_s + 0.006
                self.color_mesh.program['u_scale'] = (sel_s / ASPECT_RATIO, sel_s)
                self.color_mesh.program['u_offset'] = (x, y)
                self.color_mesh.program['u_color'] = (0.9, 0.9, 0.9, 0.9)
                self.color_mesh.render()
                
                # Draw slightly lighter inner background
                self.color_mesh.program['u_scale'] = (slot_s / ASPECT_RATIO, slot_s)
                self.color_mesh.program['u_color'] = (0.5, 0.5, 0.5, 0.7)
                self.color_mesh.render()
            else:
                # Draw standard dark background
                self.color_mesh.program['u_scale'] = (slot_s / ASPECT_RATIO, slot_s)
                self.color_mesh.program['u_offset'] = (x, y)
                self.color_mesh.program['u_color'] = (0.2, 0.2, 0.2, 0.6)
                self.color_mesh.render()

        # 2. Draw the 3D block icons inside the slots
        for i in range(9):
            voxel_id = player.hotbar[i]
            if voxel_id != 0:
                self.block_mesh.program['u_scale'] = (s / ASPECT_RATIO, s)
                self.block_mesh.program['u_offset'] = (start_x + i * spacing, y)
                self.block_mesh.program['voxel_id'] = voxel_id
                self.block_mesh.render()
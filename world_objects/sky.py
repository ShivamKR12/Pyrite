import numpy as np
import moderngl as mgl
from meshes.base_mesh import BaseMesh

class SkyMesh(BaseMesh):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.ctx = app.ctx
        self.program = app.shader_program.sky
        self.vbo_format = '2f'
        self.attrs = ('in_position',)
        self.vao = self.get_vao()

    def get_vertex_data(self):
        # Full screen quad spanning normalized device coordinates [-1, 1]
        return np.array([
            (-1.0, -1.0), ( 1.0, -1.0), ( 1.0,  1.0),
            (-1.0, -1.0), ( 1.0,  1.0), (-1.0,  1.0)
        ], dtype='float32')

class Sky:
    def __init__(self, app):
        self.app = app
        self.mesh = SkyMesh(app)

    def render(self):
        self.app.ctx.disable(mgl.DEPTH_TEST)
        self.mesh.render()
        self.app.ctx.enable(mgl.DEPTH_TEST)
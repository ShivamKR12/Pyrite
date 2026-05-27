import numpy as np
import moderngl as mgl
from meshes.base_mesh import BaseMesh
from profiler import global_profiler


class SkyMesh(BaseMesh):
    """
    Generates the geometry for the skybox, represented as a full-screen 2D quad.
    """
    @global_profiler.profile_func("SkyMesh_Init")
    def __init__(self, app):
        """
        Initializes the sky mesh, binding it to the shader program responsible 
        for rendering the atmosphere, sun, moon, and stars.
        """
        super().__init__()
        self.app = app
        self.ctx = app.ctx
        self.program = app.shader_program.sky
        self.vbo_format = '2f'
        self.attrs = ('in_position',)
        self.vao = self.get_vao()

    @global_profiler.profile_func("SkyMesh_GetVertexData")
    def get_vertex_data(self):
        """
        Returns the vertex coordinates for a full-screen quad spanning 
        normalized device coordinates.
        """
        # Full screen quad spanning normalized device coordinates [-1, 1]
        return np.array([
            (-1.0, -1.0), ( 1.0, -1.0), ( 1.0,  1.0),
            (-1.0, -1.0), ( 1.0,  1.0), (-1.0,  1.0)
        ], dtype='float32')


class Sky:
    """
    Manages the skybox object, handling the rendering of the atmospheric 
    background and celestial bodies.
    """
    @global_profiler.profile_func("Sky_Init")
    def __init__(self, app):
        """
        Initializes the sky object and creates its associated full-screen quad mesh.
        """
        self.app = app
        self.mesh = SkyMesh(app)

    @global_profiler.profile_func("Sky_Render")
    def render(self):
        """
        Issues the draw call for the skybox. Temporarily disables depth testing 
        to ensure the sky is drawn strictly behind all other 3D geometry.
        """
        self.app.ctx.disable(mgl.DEPTH_TEST)
        self.mesh.render()
        self.app.ctx.enable(mgl.DEPTH_TEST)

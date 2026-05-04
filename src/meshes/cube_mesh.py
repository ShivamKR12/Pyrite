from settings import *
from meshes.base_mesh import BaseMesh


class CubeMesh(BaseMesh):
    """
    Generates the geometry for a standard 3D cube.
    Used primarily for the wireframe voxel marker that highlights targeted blocks.
    """
    def __init__(self, app):
        """
        Initializes the cube mesh, binding it to the voxel marker shader program.
        """
        super().__init__()
        self.app = app
        self.ctx = self.app.ctx
        self.program = self.app.shader_program.voxel_marker

        self.vbo_format = '2f2 3f2'
        self.attrs = ('in_tex_coord_0', 'in_position',)
        self.vao = self.get_vao()

    @staticmethod
    def get_data(vertices, indices):
        """
        Flattens the structured lists of vertices and indices into a contiguous 
        1D Numpy array required by OpenGL.
        """
        data = [vertices[ind] for triangle in indices for ind in triangle]
        return np.array(data, dtype='float16')

    def get_vertex_data(self):
        """
        Defines the local 3D coordinates and 2D texture UVs for all six faces 
        of the cube, and assembles them into the final vertex buffer payload.
        """
        vertices = [
            (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1),
            (0, 1, 0), (0, 0, 0), (1, 0, 0), (1, 1, 0)
        ]
        indices = [
            (0, 2, 3), (0, 1, 2),
            (1, 7, 2), (1, 6, 7),
            (6, 5, 4), (4, 7, 6),
            (3, 4, 5), (3, 5, 0),
            (3, 7, 4), (3, 2, 7),
            (0, 6, 1), (0, 5, 6)
        ]
        vertex_data = self.get_data(vertices, indices)

        tex_coord_vertices = [(0, 0), (1, 0), (1, 1), (0, 1)]
        tex_coord_indices = [
            (0, 2, 3), (0, 1, 2),
            (0, 2, 3), (0, 1, 2),
            (0, 1, 2), (2, 3, 0),
            (2, 3, 0), (2, 0, 1),
            (0, 2, 3), (0, 1, 2),
            (3, 1, 2), (3, 0, 1),
        ]
        tex_coord_data = self.get_data(tex_coord_vertices, tex_coord_indices)
        vertex_data = np.hstack([tex_coord_data, vertex_data])
        return vertex_data

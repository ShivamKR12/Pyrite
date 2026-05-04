import numpy as np
from meshes.base_mesh import BaseMesh


class ItemMesh(BaseMesh):
    """
    Generates the geometry for dropped 3D items and blocks in the world.
    Builds a standard cube mesh formatted to support the global block texture atlas.
    """
    def __init__(self, app):
        """
        Initializes the item mesh, binding it to the specialized item shader program
        which handles dynamic lighting and texture mapping for dropped entities.
        """
        super().__init__()
        self.app = app
        self.ctx = self.app.ctx
        self.program = self.app.shader_program.item
        self.vbo_format = '3f 2f 1f'
        self.attrs = ('in_position', 'in_tex_coord', 'in_face_id')
        self.vao = self.get_vao()

    def get_vertex_data(self):
        """
        Calculates and returns the complete set of vertices, texture coordinates, 
        and face IDs required to construct a 3D block representation.
        """
        # format: pos(3), uv(2), face_id(1)
        # face_ids: 0: top, 1: bottom, 2: right, 3: left, 4: back, 5: front
        vertices = [
            # Top
            0,1,1, 0,1, 0,  1,1,1, 1,1, 0,  1,1,0, 1,0, 0,
            0,1,1, 0,1, 0,  1,1,0, 1,0, 0,  0,1,0, 0,0, 0,
            # Bottom
            0,0,0, 0,0, 1,  1,0,0, 1,0, 1,  1,0,1, 1,1, 1,
            0,0,0, 0,0, 1,  1,0,1, 1,1, 1,  0,0,1, 0,1, 1,
            # Right
            1,0,1, 0,1, 2,  1,0,0, 1,1, 2,  1,1,0, 1,0, 2,
            1,0,1, 0,1, 2,  1,1,0, 1,0, 2,  1,1,1, 0,0, 2,
            # Left
            0,0,0, 0,1, 3,  0,0,1, 1,1, 3,  0,1,1, 1,0, 3,
            0,0,0, 0,1, 3,  0,1,1, 1,0, 3,  0,1,0, 0,0, 3,
            # Back
            1,0,0, 0,1, 4,  0,0,0, 1,1, 4,  0,1,0, 1,0, 4,
            1,0,0, 0,1, 4,  0,1,0, 1,0, 4,  1,1,0, 0,0, 4,
            # Front
            0,0,1, 0,1, 5,  1,0,1, 1,1, 5,  1,1,1, 1,0, 5,
            0,0,1, 0,1, 5,  1,1,1, 1,0, 5,  0,1,1, 0,0, 5,
        ]
        return np.array(vertices, dtype='float32')
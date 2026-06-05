"""
Standard 3D cube mesh generator.

This module constructs the geometry for a basic 1x1x1 cube. It is primarily
utilized for rendering the wireframe voxel marker that highlights targeted
blocks in the world, ensuring the player knows exactly where they are aiming.
"""

import numpy as np
from typing import Any, List, Tuple
from numpy.typing import NDArray

from meshes.base_mesh import BaseMesh
from profiler import global_profiler


class CubeMesh(BaseMesh):
    """
    Generates the geometry for a standard 3D cube.

    Used primarily for the wireframe voxel marker that highlights targeted blocks.
    Constructs the vertices and UVs needed to map a simple texture over a unit cube.

    Args:
        app (Any): The main application context providing the shaders.
    """

    @global_profiler.profile_func('CubeMesh_Init')
    def __init__(self, app: Any) -> None:
        """
        Initializes the cube mesh, binding it to the voxel marker shader program.
        """
        super().__init__()
        self.app: Any = app
        self.ctx: Any = self.app.ctx
        self.program: Any = self.app.shader_program.voxel_marker

        self.vbo_format: str = '2f2 3f2'
        self.attrs: Tuple[str, ...] = (
            'in_tex_coord_0',
            'in_position',
        )
        self.vao: Any = self.get_vao()

    @staticmethod
    def get_data(vertices: List[Any], indices: List[Tuple[int, int, int]]) -> NDArray[np.float16]:
        """
        Flattens the structured lists of vertices and indices into a contiguous
        1D Numpy array required by OpenGL.
        """
        data: List[float] = [vertices[ind] for triangle in indices for ind in triangle]

        return np.array(data, dtype='float16')

    @global_profiler.profile_func('CubeMesh_GetVertexData')
    def get_vertex_data(self) -> NDArray[np.float16]:
        """
        Defines the local 3D coordinates and 2D texture UVs for all six faces
        of the cube, and assembles them into the final vertex buffer payload.
        """
        vertices: List[Tuple[int, int, int]] = [
            (0, 0, 1),
            (1, 0, 1),
            (1, 1, 1),
            (0, 1, 1),
            (0, 1, 0),
            (0, 0, 0),
            (1, 0, 0),
            (1, 1, 0),
        ]

        indices: List[Tuple[int, int, int]] = [
            (0, 2, 3),
            (0, 1, 2),
            (1, 7, 2),
            (1, 6, 7),
            (6, 5, 4),
            (4, 7, 6),
            (3, 4, 5),
            (3, 5, 0),
            (3, 7, 4),
            (3, 2, 7),
            (0, 6, 1),
            (0, 5, 6),
        ]

        vertex_data: NDArray[np.float16] = self.get_data(vertices, indices)

        tex_coord_vertices: List[Tuple[int, int]] = [(0, 0), (1, 0), (1, 1), (0, 1)]

        tex_coord_indices: List[Tuple[int, int, int]] = [
            (0, 2, 3),
            (0, 1, 2),
            (0, 2, 3),
            (0, 1, 2),
            (0, 1, 2),
            (2, 3, 0),
            (2, 3, 0),
            (2, 0, 1),
            (0, 2, 3),
            (0, 1, 2),
            (3, 1, 2),
            (3, 0, 1),
        ]

        tex_coord_data: NDArray[np.float16] = self.get_data(tex_coord_vertices, tex_coord_indices)

        combined_data: NDArray[np.float16] = np.hstack([tex_coord_data, vertex_data])

        return combined_data

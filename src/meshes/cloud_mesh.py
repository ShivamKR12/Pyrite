"""
Procedural cloud mesh generation and greedy meshing.

This module manages the volumetric cloud layer by generating 2D noise-based
density maps and using a specialized 2D greedy meshing algorithm to compile
optimized, low-polygon chunks of clouds that scroll across the sky.
"""

from typing import Any, Tuple

import numpy as np
from numba import njit, prange
from numpy.typing import NDArray

import noise
from meshes.base_mesh import BaseMesh
from noise import noise2
from profiler import global_profiler
from settings import CHUNK_AREA, CHUNK_SIZE, CLOUD_HEIGHT, WORLD_AREA, WORLD_D, WORLD_W


class CloudMesh(BaseMesh):
    """
    Generates the geometry for the procedural 3D cloud layer.

    Utilizes simplex noise to map cloud density and a 2D greedy meshing algorithm
    to create an optimized, low-polygon mesh of cloud blocks.

    Args:
        app (Any): The main application instance providing the ModernGL context.
    """

    @global_profiler.profile_func('CloudMesh_Init')
    def __init__(self, app: Any) -> None:
        """
        Initializes the cloud mesh, setting up the shader program and vertex buffer
        configuration required to render the volumetric clouds.
        """
        super().__init__()
        self.app: Any = app
        self.ctx: Any = self.app.ctx
        self.program: Any = self.app.shader_program.clouds
        self.vbo_format: str = '3u2'
        self.attrs: Tuple[str, ...] = ('in_position',)
        self.vao: Any = self.get_vao()

    @global_profiler.profile_func('CloudMesh_GetVertexData')
    def get_vertex_data(self) -> NDArray[np.uint16]:
        """
        Coordinates the generation of the raw cloud density data and subsequently
        constructs the optimized 3D mesh vertex data required for rendering.
        """
        cloud_data: Any = np.zeros(WORLD_AREA * CHUNK_SIZE**2, dtype='uint8')
        self.gen_clouds(cloud_data, noise.perm)

        return self.build_mesh(cloud_data)  # type: ignore[no-any-return]

    @staticmethod
    @njit(cache=True, fastmath=True, parallel=True, nogil=True)
    def gen_clouds(cloud_data: Any, perm_array: Any) -> None:
        """
        Populates a 2D density grid using multi-octave simplex noise to procedurally
        determine the exact locations where clouds should form in the sky.
        """
        for x in prange(WORLD_W * CHUNK_SIZE):
            for z in range(WORLD_D * CHUNK_SIZE):
                if noise2(0.13 * x, 0.13 * z, perm_array) < 0.2:
                    continue

                cloud_data[x + WORLD_W * CHUNK_SIZE * z] = 1

    @staticmethod
    @njit(cache=True, fastmath=True, nogil=True)
    def build_mesh(cloud_data: Any) -> NDArray[np.uint16]:
        """
        A specialized 2D greedy meshing algorithm that scans the generated cloud density grid.
        It mathematically combines adjacent, identical cloud blocks into massive single
        polygonal faces, drastically reducing the total number of vertices sent to the GPU.
        """
        mesh = np.empty(WORLD_AREA * CHUNK_AREA * 6 * 3, dtype='uint16')
        index = 0
        width = WORLD_W * CHUNK_SIZE
        depth = WORLD_D * CHUNK_SIZE

        y = CLOUD_HEIGHT
        visited = set()

        for z in range(depth):
            for x in range(width):
                idx = x + width * z
                if not cloud_data[idx] or idx in visited:
                    continue

                # find number of continuous quads along x
                x_count = 1
                idx = (x + x_count) + width * z

                while x + x_count < width and cloud_data[idx] and idx not in visited:
                    x_count += 1
                    idx = (x + x_count) + width * z

                # find the number of continuous quads along z for each x
                z_count_list = []

                for ix in range(x_count):
                    z_count = 1
                    idx = (x + ix) + width * (z + z_count)

                    while (z + z_count) < depth and cloud_data[idx] and idx not in visited:
                        z_count += 1
                        idx = (x + ix) + width * (z + z_count)

                    z_count_list.append(z_count)

                # find min count z to form a large quad
                z_count = min(z_count_list) if z_count_list else 1

                # mark all unit quads of the large quad as visited
                for ix in range(x_count):
                    for iz in range(z_count):
                        visited.add((x + ix) + width * (z + iz))

                v0 = x, y, z
                v1 = x + x_count, y, z + z_count
                v2 = x + x_count, y, z
                v3 = x, y, z + z_count

                for vertex in (v0, v1, v2, v0, v3, v1):
                    for attr in vertex:
                        mesh[index] = attr
                        index += 1

        mesh = mesh[: index + 1]

        return mesh

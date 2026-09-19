"""
Chunk data structures, voxel management, and rendering logic.

This module defines the `Chunk` class, which serves as a volumetric container
for a specific 3D region of the world. It manages the chunk's Numpy arrays
(voxels and lightmaps), hardware occlusion queries, and acts as the bridge
between the Numba terrain generation and the OpenGL mesh builders.
"""

import random
from typing import Any, Optional, Tuple

import numpy as np
from numba import njit
from numpy.typing import NDArray
from pyglm import glm

from meshes.chunk_mesh import ChunkMesh
from profiler import global_profiler
from settings import CHUNK_SIZE, CHUNK_VOLUME
from terrain_gen import fill_initial_sunlight, set_voxel_column


class Chunk:
    """
    Represents a 3D volumetric section of the world (e.g., 48x48x48 blocks).

    Stores the voxel array, lightmap, and coordinates, and handles issuing draw calls
    for its corresponding ChunkMesh.

    Args:
        world (Any): The parent `World` instance this chunk belongs to.
        position (Tuple[int, int, int]): The spatial chunk coordinate (e.g., (0, 0, 0)).
    """

    @global_profiler.profile_func('Chunk_Init')
    def __init__(self, world: Any, position: Tuple[int, int, int]) -> None:
        """
        Initializes a chunk, preparing its occlusion queries and position boundaries.
        """
        self.app: Any = world.app
        self.world: Any = world
        self.position: Tuple[int, int, int] = position
        self.m_model: Any = self.get_model_matrix()
        self.voxels: Optional[NDArray[np.uint8]] = None
        self.lightmap: Optional[NDArray[np.uint8]] = None
        self.mesh: Optional[ChunkMesh] = None
        self.is_empty: bool = True

        # We generate an OpenGL asynchronous occlusion query object.
        # This hardware query counts the number of fragments (pixels) that pass the depth test.
        # If the result is 0, the chunk is entirely obscured by other geometry and can be skipped in future frames.
        self.query: Any = self.app.ctx.query(samples=True)

        # We start by assuming the chunk is visible until proven otherwise by the query.
        self.is_visible: bool = True

        # Tracks whether an occlusion query is currently in flight on the GPU to prevent redundant queries.
        self.query_submitted: bool = False

        self.center: Any = (glm.vec3(self.position) + 0.5) * CHUNK_SIZE
        self.is_on_frustum: Any = self.app.player.frustum.is_on_frustum

        self.pending_lighting: bool = False

    @global_profiler.profile_func('Chunk_GetModelMatrix')
    def get_model_matrix(self) -> Any:
        """
        Calculates the transformation matrix required to position this chunk
        correctly within the global 3D world space.
        """
        m_model: Any = glm.translate(glm.mat4(), glm.vec3(self.position) * CHUNK_SIZE)
        return m_model

    @global_profiler.profile_func('Chunk_SetUniform')
    def set_uniform(self) -> None:
        """
        Writes this chunk's model matrix to the active shader.
        """
        if self.mesh:
            self.mesh.program['m_model'].write(self.m_model)

    @global_profiler.profile_func('Chunk_BuildMesh')
    def build_mesh(self) -> None:
        """
        Instantiates a ChunkMesh object to begin the greedy meshing process.
        """
        self.mesh = ChunkMesh(self)

    @global_profiler.profile_func('Chunk_Render')
    def render(self) -> None:
        """
        Issues the draw call for the opaque geometry (stone, dirt, grass) of this chunk.
        """
        if not self.is_empty and self.mesh and self.mesh.vao:
            self.set_uniform()
            self.mesh.render()

    @global_profiler.profile_func('Chunk_RenderWater')
    def render_water(self) -> None:
        """
        Issues the draw call for the transparent geometry (water) of this chunk.
        """
        if not self.is_empty and self.mesh and self.mesh.vao:
            self.set_uniform()
            self.mesh.render_water()

    @global_profiler.profile_func('Chunk_BuildVoxels')
    def build_voxels(self) -> NDArray[np.uint8]:
        """
        Helper function to allocate an empty array and immediately invoke the terrain generator.
        """
        # Allocate a continuous block of 1D memory representing the 3D volume.
        # Using uint8 minimizes memory overhead, as voxel IDs range from 0 to 255.
        voxels: NDArray[np.uint8] = np.zeros(CHUNK_VOLUME, dtype='uint8')

        # Convert the chunk's grid position into absolute world block coordinates.
        # cx, cy, cz represent the exact minimum bounds (bottom-left-back corner) of the chunk.
        cx, cy, cz = map(int, glm.ivec3(self.position) * CHUNK_SIZE)

        self.generate_terrain(voxels, cx, cy, cz)

        if np.any(voxels):
            self.is_empty = False

        return voxels

    @staticmethod
    @njit(cache=True, fastmath=True, nogil=True)
    def generate_terrain(
        voxels: Any, lightmap: Any, cx: int, cy: int, cz: int, perm_array: Any, perm_grad_array: Any, seed: int
    ) -> None:
        """
        A highly parallelized Numba wrapper that populates a chunk's voxel and lighting arrays
        deterministically based on the world seed.
        """
        # We compute a unique hash for this specific chunk by bitwise XORing the world seed
        # with the chunk's absolute spatial coordinates (cx, cy, cz).
        # This guarantees that the local RNG state is identically initialized every time this
        # exact chunk is generated, preventing structural seams between adjacent chunks.
        np.random.seed(seed ^ cx ^ cy ^ cz)
        random.seed(seed ^ cx ^ cy ^ cz)

        # We iterate over the 2D local plane (x, z) of the chunk.
        # For each vertical column, we evaluate the 2D and 3D noise functions.
        for x in range(CHUNK_SIZE):
            for z in range(CHUNK_SIZE):
                # set_voxel_column computes the heightmap, applies biome rules, and fills
                # the 1D voxels array from the bottom (cy) to the computed surface height.
                set_voxel_column(voxels, x, z, cx, cy, cz, perm_array, perm_grad_array)

        # After the physical blocks are placed, we run a top-down raycasting pass.
        # This traces from the sky downwards, marking blocks with sunlight (level 15)
        # until an opaque block is hit, populating the parallel lightmap array.
        fill_initial_sunlight(voxels, lightmap, cx, cy, cz, perm_array)

    @staticmethod
    @njit(cache=True, fastmath=True, nogil=True)
    def fill_initial_sunlight_only(voxels: Any, lightmap: Any, cx: int, cy: int, cz: int, perm_array: Any) -> None:
        """
        A Numba-optimized function to fill sunlight in a chunk's lightmap without modifying the voxel data.
        Used during world loading to quickly restore lighting without regenerating terrain.
        """
        fill_initial_sunlight(voxels, lightmap, cx, cy, cz, perm_array)

"""
Chunk data structures, voxel management, and rendering logic.

This module defines the `Chunk` class, which serves as a volumetric container 
for a specific 3D region of the world. It manages the chunk's Numpy arrays 
(voxels and lightmaps), hardware occlusion queries, and acts as the bridge 
between the Numba terrain generation and the OpenGL mesh builders.
"""

import numpy as np
import random
from pyglm import glm
from numba import njit
from typing import Any, Optional, Tuple
from numpy.typing import NDArray

from meshes.chunk_mesh import ChunkMesh
from terrain_gen import set_voxel_column, fill_initial_sunlight
from profiler import global_profiler
from settings import CHUNK_SIZE, CHUNK_VOL


class Chunk:
    """
    Represents a 3D volumetric section of the world (e.g., 48x48x48 blocks).
    
    Stores the voxel array, lightmap, and coordinates, and handles issuing draw calls 
    for its corresponding ChunkMesh.
    
    Args:
        world (Any): The parent `World` instance this chunk belongs to.
        position (Tuple[int, int, int]): The spatial chunk coordinate (e.g., (0, 0, 0)).
    """
    @global_profiler.profile_func("Chunk_Init")
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

        self.query: Any = self.app.ctx.query(samples=True)
        self.is_visible: bool = True
        self.query_submitted: bool = False

        self.center: Any = (glm.vec3(self.position) + 0.5) * CHUNK_SIZE
        self.is_on_frustum: Any = self.app.player.frustum.is_on_frustum

    @global_profiler.profile_func("Chunk_GetModelMatrix")
    def get_model_matrix(self) -> Any:
        """
        Calculates the transformation matrix required to position this chunk 
        correctly within the global 3D world space.
        """
        m_model: Any = glm.translate(glm.mat4(), glm.vec3(self.position) * CHUNK_SIZE)
        return m_model

    @global_profiler.profile_func("Chunk_SetUniform")
    def set_uniform(self) -> None:
        """
        Writes this chunk's model matrix to the active shader.
        """
        if self.mesh:
            self.mesh.program['m_model'].write(self.m_model)

    @global_profiler.profile_func("Chunk_BuildMesh")
    def build_mesh(self) -> None:
        """
        Instantiates a ChunkMesh object to begin the greedy meshing process.
        """
        self.mesh = ChunkMesh(self)

    @global_profiler.profile_func("Chunk_Render")
    def render(self) -> None:
        """
        Issues the draw call for the opaque geometry (stone, dirt, grass) of this chunk.
        """
        if not self.is_empty and self.mesh and self.mesh.vao:
            self.set_uniform()
            self.mesh.render()

    @global_profiler.profile_func("Chunk_RenderWater")
    def render_water(self) -> None:
        """
        Issues the draw call for the transparent geometry (water) of this chunk.
        """
        if not self.is_empty and self.mesh and self.mesh.vao:
            self.set_uniform()
            self.mesh.render_water()

    @global_profiler.profile_func("Chunk_BuildVoxels")
    def build_voxels(self) -> NDArray[np.uint8]:
        """
        Helper function to allocate an empty array and immediately invoke the terrain generator.
        """
        voxels: NDArray[np.uint8] = np.zeros(CHUNK_VOL, dtype='uint8')

        cx, cy, cz = map(int, glm.ivec3(self.position) * CHUNK_SIZE)
        self.generate_terrain(voxels, cx, cy, cz)

        if np.any(voxels):
            self.is_empty = False
        
        return voxels

    @staticmethod
    @njit(cache=True, fastmath=True, nogil=True)
    def generate_terrain(voxels: Any, lightmap: Any, cx: int, cy: int, cz: int, perm_array: Any, perm_grad_array: Any, seed: int) -> None:
        """
        A highly parallelized Numba wrapper that populates a chunk's voxel and lighting arrays 
        deterministically based on the world seed.
        """
        np.random.seed(seed ^ cx ^ cy ^ cz)
        random.seed(seed ^ cx ^ cy ^ cz)
        
        for x in range(CHUNK_SIZE):
            for z in range(CHUNK_SIZE):
                set_voxel_column(voxels, x, z, cx, cy, cz, perm_array, perm_grad_array)
        
        fill_initial_sunlight(voxels, lightmap, cx, cy, cz, perm_array)

    @staticmethod
    @njit(cache=True, fastmath=True, nogil=True)
    def fill_initial_sunlight_only(voxels: Any, lightmap: Any, cx: int, cy: int, cz: int, perm_array: Any) -> None:
        """
        A Numba-optimized function to fill sunlight in a chunk's lightmap without modifying the voxel data.
        Used during world loading to quickly restore lighting without regenerating terrain.
        """
        fill_initial_sunlight(voxels, lightmap, cx, cy, cz, perm_array)

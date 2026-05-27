from settings import *
from meshes.chunk_mesh import ChunkMesh
from terrain_gen import *
import numpy as np
import random
from profiler import global_profiler


class Chunk:
    """
    Represents a 3D volumetric section of the world (e.g., 48x48x48 blocks).
    Stores the voxel array, lightmap, and coordinates, and handles issuing draw calls 
    for its corresponding ChunkMesh.
    """
    @global_profiler.profile_func("Chunk_Init")
    def __init__(self, world, position):
        """
        Initializes a chunk, preparing its occlusion queries and position boundaries.
        """
        self.app = world.app
        self.world = world
        self.position = position
        self.m_model = self.get_model_matrix()
        self.voxels: np.array = None
        self.lightmap: np.array = None
        self.mesh: ChunkMesh = None
        self.is_empty = True

        self.query = self.app.ctx.query(samples=True)
        self.is_visible = True
        self.query_submitted = False

        self.center = (glm.vec3(self.position) + 0.5) * CHUNK_SIZE
        self.is_on_frustum = self.app.player.frustum.is_on_frustum

    @global_profiler.profile_func("Chunk_GetModelMatrix")
    def get_model_matrix(self):
        """
        Calculates the transformation matrix required to position this chunk 
        correctly within the global 3D world space.
        """
        m_model = glm.translate(glm.mat4(), glm.vec3(self.position) * CHUNK_SIZE)
        return m_model

    @global_profiler.profile_func("Chunk_SetUniform")
    def set_uniform(self):
        """
        Writes this chunk's model matrix to the active shader.
        """
        self.mesh.program['m_model'].write(self.m_model)

    @global_profiler.profile_func("Chunk_BuildMesh")
    def build_mesh(self):
        """
        Instantiates a ChunkMesh object to begin the greedy meshing process.
        """
        self.mesh = ChunkMesh(self)

    @global_profiler.profile_func("Chunk_Render")
    def render(self):
        """
        Issues the draw call for the opaque geometry (stone, dirt, grass) of this chunk.
        """
        if not self.is_empty and self.mesh and self.mesh.vao:
            self.set_uniform()
            self.mesh.render()

    @global_profiler.profile_func("Chunk_RenderWater")
    def render_water(self):
        """
        Issues the draw call for the transparent geometry (water) of this chunk.
        """
        if not self.is_empty and self.mesh and self.mesh.vao:
            self.set_uniform()
            self.mesh.render_water()

    @global_profiler.profile_func("Chunk_BuildVoxels")
    def build_voxels(self):
        """
        Helper function to allocate an empty array and immediately invoke the terrain generator.
        """
        voxels = np.zeros(CHUNK_VOL, dtype='uint8')

        cx, cy, cz = glm.ivec3(self.position) * CHUNK_SIZE
        self.generate_terrain(voxels, cx, cy, cz)

        if np.any(voxels):
            self.is_empty = False
        
        return voxels

    @staticmethod
    @njit(cache=True)
    def generate_terrain(voxels, lightmap, cx, cy, cz, perm_array, perm_grad_array, seed):
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
    @njit(cache=True)
    def fill_initial_sunlight_only(voxels, lightmap, cx, cy, cz, perm_array):
        """
        A Numba-optimized function to fill sunlight in a chunk's lightmap without modifying the voxel data.
        Used during world loading to quickly restore lighting without regenerating terrain.
        """
        fill_initial_sunlight(voxels, lightmap, cx, cy, cz, perm_array)

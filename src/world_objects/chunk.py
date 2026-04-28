from settings import *
from meshes.chunk_mesh import ChunkMesh
from terrain_gen import *
import numpy as np
import random


class Chunk:
    def __init__(self, world, position):
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

    def get_model_matrix(self):
        m_model = glm.translate(glm.mat4(), glm.vec3(self.position) * CHUNK_SIZE)
        return m_model

    def set_uniform(self):
        self.mesh.program['m_model'].write(self.m_model)

    def build_mesh(self):
        self.mesh = ChunkMesh(self)

    def render(self):
        if not self.is_empty and self.mesh and self.mesh.vao:
            self.set_uniform()
            self.mesh.render()

    def render_water(self):
        if not self.is_empty and self.mesh and self.mesh.vao:
            self.set_uniform()
            self.mesh.render_water()

    def build_voxels(self):
        voxels = np.zeros(CHUNK_VOL, dtype='uint8')

        cx, cy, cz = glm.ivec3(self.position) * CHUNK_SIZE
        self.generate_terrain(voxels, cx, cy, cz)

        if np.any(voxels):
            self.is_empty = False
        return voxels

    @staticmethod
    @njit(cache=True)
    def generate_terrain(voxels, lightmap, cx, cy, cz, perm_array, perm_grad_array, seed):
        np.random.seed(seed ^ cx ^ cy ^ cz)
        random.seed(seed ^ cx ^ cy ^ cz)
        for x in range(CHUNK_SIZE):
            for z in range(CHUNK_SIZE):
                set_voxel_column(voxels, x, z, cx, cy, cz, perm_array, perm_grad_array)
        fill_initial_sunlight(voxels, lightmap, cx, cy, cz, perm_array)

    @staticmethod
    @njit(cache=True)
    def fill_initial_sunlight_only(voxels, lightmap, cx, cy, cz, perm_array):
        fill_initial_sunlight(voxels, lightmap, cx, cy, cz, perm_array)

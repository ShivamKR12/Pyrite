from meshes.base_mesh import BaseMesh
from meshes.chunk_mesh_builder import build_chunk_mesh


class ChunkMesh(BaseMesh):
    def __init__(self, chunk):
        super().__init__()
        self.app = chunk.app
        self.chunk = chunk
        self.ctx = self.app.ctx
        self.program = self.app.shader_program.chunk

        self.vbo_format = '1u4'
        self.format_size = sum(int(fmt[:1]) for fmt in self.vbo_format.split())
        self.attrs = ('packed_data',)
        self.vao = None
        self.vbo = None
        self.vertex_data = None

    def render(self):
        if self.vao:
            super().render()

    def rebuild(self):
        if self.vao:
            self.vao.release()
        if self.vbo:
            self.vbo.release()
        self.vertex_data = None
        self.vao = self.get_vao()

    def get_vao(self):
        if self.vertex_data is None:
            self.vertex_data = self.get_vertex_data()

        if self.vertex_data.size == 0:
            return None

        self.vbo = self.ctx.buffer(self.vertex_data)
        vao = self.ctx.vertex_array(
            self.program, [(self.vbo, self.vbo_format, *self.attrs)], skip_errors=True
        )
        return vao

    def get_vertex_data(self):
        mesh = build_chunk_mesh(
            chunk_voxels=self.chunk.voxels,
            format_size=self.format_size,
            chunk_pos=self.chunk.position,
            world_voxels=self.chunk.world.voxels,
            chunk_positions=self.chunk.world.chunk_positions
        )
        return mesh

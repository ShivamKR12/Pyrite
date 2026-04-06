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
        self.vertex_data = None

    def render(self):
        if self.vao:
            super().render()

    def rebuild(self):
        self.vertex_data = self.get_vertex_data()
        self.vao = self.get_vao()

    def get_vao(self):
        vertex_data = self.get_vertex_data() if self.vertex_data is None else self.vertex_data
        vbo = self.ctx.buffer(vertex_data)
        vao = self.ctx.vertex_array(
            self.program, [(vbo, self.vbo_format, *self.attrs)], skip_errors=True
        )
        return vao

    def get_vertex_data(self):
        mesh = build_chunk_mesh(
            chunk_voxels=self.chunk.voxels,
            format_size=self.format_size,
            chunk_pos=self.chunk.position,
            world_voxels=self.chunk.world.voxels
        )
        return mesh

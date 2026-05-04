from meshes.base_mesh import BaseMesh
from meshes.chunk_mesh_builder import build_chunk_mesh
import math


class ChunkMesh(BaseMesh):
    """
    Manages the OpenGL geometry for a chunk, handling both opaque and transparent (water) meshes. 
    It interfaces with the greedy meshing builder to generate vertex data and utilizes 
    a VBO pool to manage GPU memory efficiently.
    """
    def __init__(self, chunk):
        """
        Initializes the chunk mesh, linking it to its parent chunk and the appropriate shader program. 
        Sets up the vertex buffer format and prepares attributes for rendering.
        """
        super().__init__()
        self.app = chunk.app
        self.chunk = chunk
        self.ctx = self.app.ctx
        self.program = self.app.shader_program.chunk

        self.vbo_format = '1u4 1u4'
        self.format_size = 2
        self.attrs = ('packed_data', 'light_data')
        self.vao = None
        self.vbo = None
        self.vertex_data = None
        self.opaque_count = 0
        self.water_count = 0

    def render(self):
        """
        Issues the draw call for the opaque portion of the chunk's mesh, 
        provided it has valid geometry to render.
        """
        if self.vao and self.opaque_count > 0:
            self.vao.render(vertices=self.opaque_count)

    def render_water(self):
        """
        Issues the draw call for the transparent water portion of the chunk's mesh, 
        starting from the end of the opaque vertex data.
        """
        if self.vao and self.water_count > 0:
            self.vao.render(vertices=self.water_count, first=self.opaque_count)

    def get_vao(self):
        """
        Retrieves or builds the Vertex Array Object (VAO) for the chunk. It first generates 
        the raw vertex data, then attempts to recycle an appropriately sized VBO from 
        the global pool to prevent memory leaks, allocating a new one if necessary.
        """
        if self.vertex_data is None:
            result = self.get_vertex_data()
            self.vertex_data = result[0]
            self.opaque_count = result[1]
            self.water_count = result[2]

        if self.vertex_data.size == 0:
            return None

        byte_size = self.vertex_data.nbytes
        pool = self.chunk.world.vbo_pool

        # Find the smallest VBO in the pool that can safely fit our new mesh data
        best_i = -1
        best_size = float('inf')
        for i, (p_vbo, p_vao) in enumerate(pool):
            if p_vbo.size >= byte_size and p_vbo.size < best_size:
                best_i = i
                best_size = p_vbo.size

        if best_i != -1:
            self.vbo, self.vao = pool.pop(best_i)
            self.vbo.write(self.vertex_data)
            self.vertex_data = None
            return self.vao

        # Allocate a new VBO, but round the size up to the nearest power of 2
        # This ensures the VBOs are generic sizes (e.g. 128KB, 256KB) and highly reusable!
        reserve_size = 2 ** math.ceil(math.log2(byte_size)) if byte_size > 0 else 0
        self.vbo = self.ctx.buffer(reserve=reserve_size)
        self.vbo.write(self.vertex_data)
        
        vao = self.ctx.vertex_array(
            self.program, [(self.vbo, self.vbo_format, *self.attrs)], skip_errors=True
        )
        self.vertex_data = None
        return vao

    def get_vertex_data(self):
        """
        Triggers the greedy meshing algorithm to construct the optimized vertex payload 
        (including ambient occlusion and lighting) from the chunk's 3D voxel array.
        """
        mesh = build_chunk_mesh(
            chunk_voxels=self.chunk.voxels,
            chunk_lightmap=self.chunk.lightmap,
            format_size=self.format_size,
            chunk_pos=self.chunk.position,
            world_voxels=self.chunk.world.voxels,
            world_lightmaps=self.chunk.world.lightmaps,
            chunk_positions=self.chunk.world.chunk_positions
        )
        return mesh

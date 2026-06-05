"""
OpenGL geometry wrapper and VRAM manager for active world chunks.

This module links the generated Numba geometry data directly to the ModernGL VAO/VBO contexts.
Crucially, it handles the dynamic VBO object pooling architecture, safely tracking and recycling
massive GPU memory buffers on the fly to prevent strict VRAM memory leaking during chunk streaming.
"""

import math
from typing import Any, Tuple

from meshes.base_mesh import BaseMesh
from meshes.chunk_mesh_builder import build_chunk_mesh
from profiler import global_profiler


class ChunkMesh(BaseMesh):
    """
    Manages the OpenGL geometry for a chunk, handling opaque and transparent meshes.

    It interfaces with the greedy meshing builder to generate vertex data and utilizes
    a VBO pool to manage GPU memory efficiently. Ensures chunks can be seamlessly
    uploaded and released from VRAM during rapid world streaming.

    Args:
        chunk (Any): The parent chunk instance this mesh is visually representing.
    """

    @global_profiler.profile_func('ChunkMesh_Init')
    def __init__(self, chunk: Any) -> None:
        """
        Initializes the chunk mesh, linking it to its parent chunk and the appropriate shader program.
        Sets up the vertex buffer format and prepares attributes for rendering.
        """
        super().__init__()
        self.app: Any = chunk.app
        self.chunk: Any = chunk

        self.ctx: Any = self.app.ctx
        self.program: Any = self.app.shader_program.chunk

        self.vbo_format: str = '1u4 1u4'
        self.format_size: int = 2
        self.attrs: Tuple[str, ...] = ('packed_data', 'light_data')

        self.vao: Any = None
        self.vbo: Any = None
        self.vertex_data: Any = None
        self.opaque_count: int = 0
        self.water_count: int = 0

    @global_profiler.profile_func('ChunkMesh_Render')
    def render(self) -> None:
        """
        Issues the draw call for the opaque portion of the chunk's mesh,
        provided it has valid geometry to render.
        """
        if self.vao and self.opaque_count > 0:
            self.vao.render(vertices=self.opaque_count)

    @global_profiler.profile_func('ChunkMesh_RenderWater')
    def render_water(self) -> None:
        """
        Issues the draw call for the transparent water portion of the chunk's mesh,
        starting from the end of the opaque vertex data.
        """
        if self.vao and self.water_count > 0:
            self.vao.render(vertices=self.water_count, first=self.opaque_count)

    @global_profiler.profile_func('ChunkMesh_GetVAO')
    def get_vao(self) -> Any:
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

        byte_size: int = self.vertex_data.nbytes
        pool: Any = self.chunk.world.vbo_pool

        # Find the smallest VBO in the pool that can safely fit our new mesh data
        best_i: int = -1
        best_size: float = float('inf')

        for i, (p_vbo, p_vao) in enumerate(pool):
            if p_vbo.size >= byte_size and p_vbo.size < best_size:
                best_i = i
                best_size = p_vbo.size

        if best_i != -1:
            pool.rotate(-best_i)
            self.vbo, self.vao = pool.popleft()
            self.vbo.write(self.vertex_data)
            self.vertex_data = None

            return self.vao

        # Allocate a new VBO, but round the size up to the nearest power of 2
        # This ensures the VBOs are generic sizes (e.g. 128KB, 256KB) and highly reusable!
        reserve_size: int = 2 ** math.ceil(math.log2(byte_size)) if byte_size > 0 else 0
        self.vbo = self.ctx.buffer(reserve=reserve_size)
        self.vbo.write(self.vertex_data)

        vao: Any = self.ctx.vertex_array(self.program, [(self.vbo, self.vbo_format, *self.attrs)], skip_errors=True)

        self.vertex_data = None

        return vao

    @global_profiler.profile_func('ChunkMesh_GetVertexData')
    def get_vertex_data(self) -> Tuple[Any, int, int]:
        """
        Triggers the greedy meshing algorithm to construct the optimized vertex payload
        (including ambient occlusion and lighting) from the chunk's 3D voxel array.
        """
        mesh: Tuple[Any, int, int] = build_chunk_mesh(
            chunk_voxels=self.chunk.voxels,
            chunk_lightmap=self.chunk.lightmap,
            format_size=self.format_size,
            chunk_pos=self.chunk.position,
            world_voxels=self.chunk.world.voxels,
            world_lightmaps=self.chunk.world.lightmaps,
            chunk_positions=self.chunk.world.chunk_positions,
        )

        return mesh

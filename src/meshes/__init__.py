"""
Meshes package: greedy meshing, mesh builders and helpers.

This package implements the chunk mesh pipeline (greedy meshing, vertex
packing, AO, and VBO upload helpers). Submodules expose `BaseMesh`,
`ChunkMesh`, and specialized meshes used by the renderer.

Providing a clear package docstring helps Sphinx autodoc and autosummary
generate a better overview page for the `meshes` package.
"""

__all__ = [
    'base_mesh',
    'chunk_mesh',
    'chunk_mesh_builder',
    'cloud_mesh',
    'cube_mesh',
    'item_mesh',
    'obj_mesh',
]

from settings import AIR, WATER, GLASS, LEAVES, STONE, GRASS
from meshes.chunk_mesh_builder import is_transparent


def test_transparent_blocks():
    """Ensure the meshing engine correctly identifies transparent blocks for face culling."""
    assert is_transparent(AIR) == True
    assert is_transparent(WATER) == True
    assert is_transparent(GLASS) == True
    assert is_transparent(LEAVES) == True
    assert is_transparent(STONE) == False
    assert is_transparent(GRASS) == False

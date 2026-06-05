"""Tests for the meshing engine, specifically the face culling logic
that determines which block faces to render based on transparency."""

from meshes.chunk_mesh_builder import is_transparent
from settings import AIR, GLASS, GRASS, LEAVES, STONE, WATER


def test_transparent_blocks():
    """Ensure the meshing engine correctly identifies transparent blocks for face culling."""
    assert is_transparent(AIR) is True
    assert is_transparent(WATER) is True
    assert is_transparent(GLASS) is True
    assert is_transparent(LEAVES) is True
    assert is_transparent(STONE) is False
    assert is_transparent(GRASS) is False

"""
Unit tests for the procedural terrain generation logic.

This test suite validates the complex deterministic math driving the engine's
terrain, such as 3D coordinate flattening (get_index), boundary enforcement,
Simplex noise outputs for biome determination, and the structural integrity
of Numba-compiled tree placements within chunk boundaries.
"""

from typing import Any

import numpy as np
import pytest

from settings import CHUNK_AREA, CHUNK_SIZE, DIRT, OAK_LOG, WORLD_HEIGHT
from terrain_gen import get_biome, get_index, get_terrain_params, place_tree


@pytest.fixture
def mock_perm_array() -> Any:
    """Provides a deterministic random noise permutation array for Simplex testing."""
    np.random.seed(42)
    return np.random.randint(0, 256, size=512, dtype=np.uint8)


def test_get_index_boundaries() -> None:
    """Verifies that 3D chunk coordinates flatten correctly into a 1D array index."""
    # Check absolute origin
    assert get_index(0, 0, 0) == 0

    # Check maximum possible coordinate boundaries inside a single chunk
    x, y, z = CHUNK_SIZE - 1, CHUNK_SIZE - 1, CHUNK_SIZE - 1
    expected_index = x + CHUNK_SIZE * z + CHUNK_AREA * y
    assert get_index(x, y, z) == expected_index


def test_get_terrain_params_safety_limits(mock_perm_array: Any) -> None:
    """Verifies that height generation respects exact boundaries (Boundary Value Analysis)."""
    height_offset, squashing_factor, biome_id = get_terrain_params(500.0, 500.0, mock_perm_array)

    assert isinstance(height_offset, float)
    assert isinstance(squashing_factor, float)
    assert isinstance(biome_id, int)

    # Check if the base height offset is within a reasonable range
    assert 0 <= height_offset <= WORLD_HEIGHT * CHUNK_SIZE


def test_place_tree_structure() -> None:
    """Tests the structural placement of tree wood and leaf voxels in the 1D array."""
    voxels = np.zeros(CHUNK_SIZE * CHUNK_AREA, dtype=np.uint8)

    # Place tree directly in the center of an empty chunk and force 100% probability
    place_tree(voxels, x=8, y=5, z=8, voxel_id=DIRT, tree_prob=1.0)

    assert voxels[get_index(8, 5, 8)] == DIRT, 'Tree did not place dirt at its base.'
    assert voxels[get_index(8, 6, 8)] == OAK_LOG, 'Tree trunk was not placed directly above the dirt.'


def test_place_tree_out_of_bounds() -> None:
    """Applies Boundary Value Analysis to ensure trees aren't placed outside chunk memory."""
    voxels = np.zeros(CHUNK_SIZE * CHUNK_AREA, dtype=np.uint8)

    # Attempt to place a tree directly on the X=0 chunk border
    place_tree(voxels, x=0, y=5, z=8, voxel_id=DIRT, tree_prob=1.0)

    assert np.all(voxels == 0), 'Tree bypassed boundaries and attempted to write outside chunk.'

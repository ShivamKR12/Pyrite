"""
Unit tests for the procedural terrain generation logic.

This test suite validates the complex deterministic math driving the engine's 
terrain, such as 3D coordinate flattening (get_index), boundary enforcement, 
Simplex noise outputs for biome determination, and the structural integrity 
of Numba-compiled tree placements within chunk boundaries.
"""

import pytest
import numpy as np
from typing import Any

from terrain_gen import get_biome, get_height, get_index, place_tree
from settings import CHUNK_SIZE, CHUNK_AREA, WOOD, DIRT, WORLD_H


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


def test_get_biome_output(mock_perm_array: Any) -> None:
    """Ensures the biome generator returns a valid Temperature and Moisture tuple."""
    temp, moist = get_biome(100.5, 200.5, mock_perm_array)
    
    assert isinstance(temp, float)
    assert isinstance(moist, float)
    assert -2.0 <= temp <= 2.0, "Temperature out of expected Simplex noise range."
    assert -2.0 <= moist <= 2.0, "Moisture out of expected Simplex noise range."


def test_get_height_safety_limits(mock_perm_array: Any) -> None:
    """Verifies that height generation respects exact boundaries (Boundary Value Analysis)."""
    height = get_height(500.0, 500.0, mock_perm_array)
    
    assert isinstance(height, int)
    assert height >= 2, "Terrain generated below the absolute minimum boundary."
    assert height <= WORLD_H * CHUNK_SIZE - 2, "Terrain exceeded the maximum world height boundary."


def test_place_tree_structure() -> None:
    """Tests the structural placement of tree wood and leaf voxels in the 1D array."""
    voxels = np.zeros(CHUNK_SIZE * CHUNK_AREA, dtype=np.uint8)
    
    # Place tree directly in the center of an empty chunk and force 100% probability
    place_tree(voxels, x=8, y=5, z=8, voxel_id=DIRT, tree_prob=1.0)
    
    assert voxels[get_index(8, 5, 8)] == DIRT, "Tree did not place dirt at its base."
    assert voxels[get_index(8, 6, 8)] == WOOD, "Tree trunk was not placed directly above the dirt."


def test_place_tree_out_of_bounds() -> None:
    """Applies Boundary Value Analysis to ensure trees aren't placed outside chunk memory."""
    voxels = np.zeros(CHUNK_SIZE * CHUNK_AREA, dtype=np.uint8)
    
    # Attempt to place a tree directly on the X=0 chunk border
    place_tree(voxels, x=0, y=5, z=8, voxel_id=DIRT, tree_prob=1.0)
    
    assert np.all(voxels == 0), "Tree bypassed boundaries and attempted to write outside chunk."
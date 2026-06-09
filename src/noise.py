"""
Procedural noise generation and deterministic seeding.

This module provides Numba-optimized wrappers around OpenSimplex noise functions.
It manages the global permutation arrays and ensures that both standard Python
random and Numba's internal RNG are perfectly synchronized to the world seed
for 100% deterministic terrain generation.
"""

import random
from typing import Any

import numpy as np
from numba import njit
from opensimplex.internals import _init, _noise2, _noise3

# Pre-allocate the arrays with a default seed. Numba will hardcode the memory pointers to these arrays.
perm: Any
perm_grad_index3: Any
perm, perm_grad_index3 = _init(seed=0)


@njit(cache=True, nogil=True)
def _seed_numba(new_seed: int) -> None:
    """
    Internal helper to seed Numba's random number generator and standard Python random.
    """
    np.random.seed(new_seed)
    random.seed(new_seed)


def set_seed(new_seed: int) -> None:
    """
    Updates the global OpenSimplex permutation arrays with a deterministic seed,
    ensuring identical noise generation for a given world seed.
    """
    global perm, perm_grad_index3
    perm, perm_grad_index3 = _init(seed=new_seed)
    _seed_numba(new_seed)
    np.random.seed(new_seed)
    random.seed(new_seed)


@njit(cache=True, fastmath=True, nogil=True)
def noise2(x: float, y: float, perm_array: Any) -> float:
    """
    Evaluates 2D Simplex Noise using the pre-compiled permutation array.
    """
    return float(_noise2(x, y, perm_array))


@njit(cache=True, fastmath=True, nogil=True)
def noise3(x: float, y: float, z: float, perm_array: Any, perm_grad_array: Any) -> float:
    """
    Evaluates 3D Simplex Noise using the pre-compiled permutation arrays.
    """
    return float(_noise3(x, y, z, perm_array, perm_grad_array))

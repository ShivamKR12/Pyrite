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
    # Numba maintains its own internal PRNG state independent of Python's `random` or NumPy's global state.
    # By calling np.random.seed inside a JIT-compiled function, we explicitly overwrite Numba's internal
    # state with the deterministic seed, ensuring that any random operations inside @njit blocks are reproducible.
    np.random.seed(new_seed)

    # Similarly, we seed Python's standard `random` module for any non-NumPy randomization.
    random.seed(new_seed)


def set_seed(new_seed: int) -> None:
    """
    Updates the global OpenSimplex permutation arrays with a deterministic seed,
    ensuring identical noise generation for a given world seed.
    """
    global perm, perm_grad_index3

    # _init generates the canonical 256-element permutation table used in Simplex noise,
    # extended to 512 elements to avoid modulo wrap-around during index lookups.
    # It also generates the gradient index array for 3D noise vectors.
    perm, perm_grad_index3 = _init(seed=new_seed)

    # We must synchronize Numba's isolated RNG state with the newly provided world seed.
    _seed_numba(new_seed)

    # We also synchronize the global NumPy RNG state which is accessible from standard Python execution.
    np.random.seed(new_seed)

    # Finally, we synchronize the standard Python random module's state.
    random.seed(new_seed)


@njit(cache=True, fastmath=True, nogil=True)
def noise2(x: float, y: float, perm_array: Any) -> float:
    """
    Evaluates 2D Simplex Noise using the pre-compiled permutation array.
    """
    # _noise2 computes the 2D simplex noise by determining the skewed simplex grid cell containing (x, y).
    # It calculates the contribution from the 3 vertices of the simplex (a triangle in 2D) using a
    # distance-based attenuation function. The perm_array hashes the vertex coordinates to select
    # pseudo-random gradient vectors, which are then dot-producted with the distance vectors.
    return float(_noise2(x, y, perm_array))


@njit(cache=True, fastmath=True, nogil=True)
def noise3(x: float, y: float, z: float, perm_array: Any, perm_grad_array: Any) -> float:
    """
    Evaluates 3D Simplex Noise using the pre-compiled permutation arrays.
    """
    # _noise3 projects the 3D coordinate (x, y, z) into the 3D simplex grid (a tetrahedron).
    # It identifies the 4 vertices of the enclosing simplex and computes their gradient contributions.
    # perm_array provides the hashed lookup indices, while perm_grad_array maps those indices
    # directly to one of the 12 edges of a cube (or midpoints), acting as the gradient vectors.
    # The final noise value is the sum of these 4 attenuated dot products.
    return float(_noise3(x, y, z, perm_array, perm_grad_array))

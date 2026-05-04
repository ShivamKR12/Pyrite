from numba import njit
from opensimplex.internals import _noise2, _noise3, _init
import numpy as np
import random


# Pre-allocate the arrays with a default seed. Numba will hardcode the memory pointers to these arrays.
perm, perm_grad_index3 = _init(seed=0)


@njit
def _seed_numba(new_seed):
    """
    Internal helper to seed Numba's random number generator and standard Python random.
    """
    np.random.seed(new_seed)
    random.seed(new_seed)


def set_seed(new_seed):
    """
    Updates the global OpenSimplex permutation arrays with a deterministic seed,
    ensuring identical noise generation for a given world seed.
    """
    global perm, perm_grad_index3
    perm, perm_grad_index3 = _init(seed=new_seed)
    _seed_numba(new_seed)


@njit(cache=True, fastmath=True, nogil=True)
def noise2(x, y, perm_array):
    """
    Evaluates 2D Simplex Noise using the pre-compiled permutation array.
    """
    return _noise2(x, y, perm_array)


@njit(cache=True, fastmath=True, nogil=True)
def noise3(x, y, z, perm_array, perm_grad_array):
    """
    Evaluates 3D Simplex Noise using the pre-compiled permutation arrays.
    """
    return _noise3(x, y, z, perm_array, perm_grad_array)

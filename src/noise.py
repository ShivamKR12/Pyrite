from numba import njit
from opensimplex.internals import _noise2, _noise3, _init
import numpy as np
import random


# Pre-allocate the arrays with a default seed. Numba will hardcode the memory pointers to these arrays.
perm, perm_grad_index3 = _init(seed=0)


@njit
def _seed_numba(new_seed):
    np.random.seed(new_seed)
    random.seed(new_seed)


def set_seed(new_seed):
    global perm, perm_grad_index3
    perm, perm_grad_index3 = _init(seed=new_seed)
    _seed_numba(new_seed)


@njit(cache=True, fastmath=True, nogil=True)
def noise2(x, y, perm_array):
    return _noise2(x, y, perm_array)


@njit(cache=True, fastmath=True, nogil=True)
def noise3(x, y, z, perm_array, perm_grad_array):
    return _noise3(x, y, z, perm_array, perm_grad_array)

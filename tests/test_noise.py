"""
Unit tests for the deterministic noise and procedural seeding systems.
"""

import random

import numpy as np

import noise


def test_set_seed() -> None:
    """
    Validates that setting a seed changes the OpenSimplex permutation arrays
    and strictly syncs Numba and Python random number generators.
    """
    noise.set_seed(42)
    val1 = noise.noise2(0.5, 0.5, noise.perm)
    np_val1 = np.random.rand()
    rnd_val1 = random.random()

    noise.set_seed(43)
    val2 = noise.noise2(0.5, 0.5, noise.perm)
    assert val1 != val2, 'Noise output should change with a different seed.'

    noise.set_seed(42)
    val3 = noise.noise2(0.5, 0.5, noise.perm)
    np_val2 = np.random.rand()
    rnd_val2 = random.random()

    assert val1 == val3, 'Noise output should be exactly identical for the same seed.'
    assert np_val1 == np_val2, 'Numpy random states must be fully deterministic.'
    assert rnd_val1 == rnd_val2, 'Python random states must be fully deterministic.'

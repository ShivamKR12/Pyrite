"""
Unit tests to enforce Numba JIT compilation constraints.

This ensures that contributors do not accidentally introduce parallel=True
or prange into modules that are not mathematically proven to be thread-safe,
preventing catastrophic race conditions and memory corruption.
"""

import os

import pytest

# Only these specific modules are "Embarrassingly Parallel" and mathematically safe.
ALLOWED_PARALLEL_MODULES = ['frustum.py', 'cloud_mesh.py']


def test_numba_parallel_constraints() -> None:
    """
    Scans all source files to ensure `parallel=True` and `prange` are only
    used in the explicitly allowed modules.
    """
    src_dir = 'src'
    if not os.path.exists(src_dir):
        pytest.skip('Source directory not found. Skipping constraint tests.')

    for root, _, files in os.walk(src_dir):
        for file in files:
            if not file.endswith('.py'):
                continue

            if file not in ALLOWED_PARALLEL_MODULES:
                with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                    content = f.read()
                    assert 'parallel=True' not in content, (
                        f"Numba Constraint Violation: '{file}' uses 'parallel=True'. This is not allowed!"
                    )
                    assert 'prange' not in content, (
                        f"Numba Constraint Violation: '{file}' imports or uses 'prange'. This is not allowed!"
                    )

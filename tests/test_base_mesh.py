"""
Unit tests for verifying the foundational OpenGL BaseMesh components.
"""

from typing import Any
from unittest.mock import MagicMock

import numpy as np

from meshes.base_mesh import BaseMesh


class DummyMesh(BaseMesh):
    """A mock implementation of BaseMesh to test rendering hooks."""

    def get_vertex_data(self) -> Any:
        return np.array([1, 2, 3], dtype='float32')


def test_base_mesh_init() -> None:
    """Ensures empty default configurations are generated for safety."""
    bm = BaseMesh()
    assert bm.ctx is None
    assert bm.program is None
    assert bm.vbo_format == ''
    assert not bm.attrs
    assert bm.vao is None


def test_base_mesh_get_vao() -> None:
    """Rigorously checks how the context buffers vertex layouts."""
    mesh = DummyMesh()
    mesh.ctx = MagicMock()
    mesh.program = MagicMock()
    mesh.vbo_format = '3f'
    mesh.attrs = ('in_position',)

    vao = mesh.get_vao()

    assert mesh.ctx.buffer.call_count == 1
    call_args = mesh.ctx.buffer.call_args[0][0]
    np.testing.assert_array_equal(call_args, mesh.get_vertex_data())

    mesh.ctx.vertex_array.assert_called_once_with(
        mesh.program, [(mesh.ctx.buffer.return_value, '3f', 'in_position')], skip_errors=True
    )
    assert vao == mesh.ctx.vertex_array.return_value


def test_base_mesh_render() -> None:
    """Asserts GPU draw calls are passed through securely."""
    bm = BaseMesh()
    bm.vao = MagicMock()
    bm.render()
    bm.vao.render.assert_called_once()

"""
Unit tests for validating 2D User Interface mesh generation.

This test module mocks the main ModernGL context to safely execute UI mesh
constructors without needing a window. It rigorously checks the exact shape,
data types, and dimensions of the resulting vertex, UV, and color Numpy arrays
dispatched to the GPU for rendering.
"""

import pytest
import numpy as np
from unittest.mock import MagicMock
from typing import Any

from ui.meshes import CrosshairMesh, BlockIconMesh, UIColorMesh, UITextMesh


@pytest.fixture
def mock_app() -> Any:
    """Mocks the main application context to bypass OpenGL context creation."""
    app = MagicMock()
    app.ctx = MagicMock()
    app.shader_program = MagicMock()
    return app


def test_crosshair_mesh_vertex_data(mock_app: Any) -> None:
    """Tests the complex crosshair geometry (12 vertices with position + color data)."""
    mesh = CrosshairMesh(mock_app)

    # Assert that the BaseMesh actually created the OpenGL buffers via the context
    mock_app.ctx.buffer.assert_called()
    mock_app.ctx.vertex_array.assert_called()

    data = mesh.get_vertex_data()

    assert isinstance(data, np.ndarray), 'Crosshair data must be a numpy array.'
    assert data.dtype == np.float32, 'Crosshair data must be float32 for ModernGL.'
    # 12 vertices x 6 attributes (3 pos + 3 color)
    assert data.shape == (12, 6), f'Expected shape (12, 6), got {data.shape}'


def test_block_icon_mesh_vertex_data(mock_app: Any) -> None:
    """Tests the block icon UI mesh (6 vertices with position + UV data)."""
    mesh = BlockIconMesh(mock_app)
    mock_app.ctx.buffer.assert_called()
    mock_app.ctx.vertex_array.assert_called()

    data = mesh.get_vertex_data()

    # 6 vertices x 4 attributes (2 pos + 2 uv)
    assert data.shape == (6, 4), f'Expected shape (6, 4), got {data.shape}'


def test_ui_color_mesh_vertex_data(mock_app: Any) -> None:
    """Tests the simple solid color UI mesh (6 vertices with position only)."""
    mesh = UIColorMesh(mock_app)
    mock_app.ctx.buffer.assert_called()
    mock_app.ctx.vertex_array.assert_called()

    data = mesh.get_vertex_data()

    # 6 vertices x 2 attributes (2 pos)
    assert data.shape == (6, 2), f'Expected shape (6, 2), got {data.shape}'


def test_ui_text_mesh_vertex_data(mock_app: Any) -> None:
    """Tests the text quad generator for font rendering."""
    mesh = UITextMesh(mock_app)
    mock_app.ctx.buffer.assert_called()
    mock_app.ctx.vertex_array.assert_called()

    data = mesh.get_vertex_data()

    assert data.shape == (6, 4), f'Expected shape (6, 4), got {data.shape}'

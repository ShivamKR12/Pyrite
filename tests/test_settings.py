"""
Unit tests for the settings module.
"""

import os
import sys
from unittest.mock import patch

import settings


def test_get_path_development() -> None:
    """Test path resolution in a standard Python development environment."""
    expected_base = os.path.abspath(os.path.join(os.path.dirname(settings.__file__), '..'))
    assert settings.get_path('assets') == os.path.join(expected_base, 'assets')


def test_get_path_pyinstaller() -> None:
    """Test path resolution when the game is bundled into an executable via PyInstaller."""
    with patch.object(sys, '_MEIPASS', '/fake/pyinstaller/path', create=True):
        assert settings.get_path('assets') == os.path.join('/fake/pyinstaller/path', 'assets')

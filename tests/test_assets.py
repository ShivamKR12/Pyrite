"""
Unit tests for validating external engine assets.

These tests enforce the strict asset formatting rules outlined in the project's 
contribution guidelines, such as ensuring texture atlases perfectly conform to 
16-bit retro scaling (multiples of 16px) and validating the geometry of `.obj` model files.
"""

import os
import pytest
import pygame as pg


def test_texture_atlas_dimensions() -> None:
    """
    Ensures the texture atlas dimensions are exact multiples of 16.
    This matches the 16-bit retro aesthetic mentioned in CONTRIBUTING.md.
    """
    atlas_path = os.path.join('assets', 'texture_atlas.png')
    
    # We only run the assertion if the file actually exists locally
    if os.path.exists(atlas_path):
        img = pg.image.load(atlas_path)
        w, h = img.get_size()
        
        assert w % 16 == 0, f"Texture atlas width ({w}) is not a multiple of 16!"
        assert h % 16 == 0, f"Texture atlas height ({h}) is not a multiple of 16!"


def test_obj_models_format() -> None:
    """
    Iterates through the assets/models directory to verify that all .obj files 
    contain at least one vertex ('v ') and one face ('f ') declaration.
    """
    models_dir = os.path.join('assets', 'models')
    
    if not os.path.exists(models_dir):
        pytest.skip("Models directory not found. Skipping OBJ tests.")
        
    for filename in os.listdir(models_dir):
        if filename.endswith('.obj'):
            with open(os.path.join(models_dir, filename), 'r') as f:
                content = f.read()
                
                assert 'v ' in content, f"OBJ model '{filename}' contains no vertex data."
                assert 'f ' in content, f"OBJ model '{filename}' contains no face geometry."

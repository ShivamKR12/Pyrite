"""
Texture loading and OpenGL binding management.

This module is responsible for loading 2D image assets via Pygame, applying transforms, 
and safely mapping them into ModernGL `Texture` and `TextureArray` objects. 
It enforces strict mipmap generation and anisotropic filtering to guarantee crisp 
pixel art visuals across all rendering distances.
"""

import pygame as pg
import moderngl as mgl
from typing import Any

from settings import get_path
from profiler import global_profiler


class Textures:
    """
    Loads, configures, and binds OpenGL textures and texture arrays.
    
    Handles mipmapping, anisotropic filtering, and texture units for crisp rendering.
    It pre-loads all essential visual assets during initialization and assigns them
    to specific texture binding locations for the GLSL shaders to sample from.
    
    Args:
        app (Any): The main application instance containing the Pygame and ModernGL contexts.
    """
    @global_profiler.profile_func("Textures_Init")
    def __init__(self, app: Any) -> None:
        """
        Instantiates and assigns the various textures to their respective OpenGL 
        texture locations so shaders can access them simultaneously.
        """
        self.app: Any = app
        self.ctx: Any = app.ctx

        # load textures
        self.texture_0: Any = self.load('textures/uis/frame.png')
        self.texture_array_0: Any = self.load('textures/arrays/texture-array-2.png', is_tex_array=True)
        self.texture_breaking: Any = self.load('textures/effects/block-breaking.png')
        self.texture_stick: Any = self.load('models/items/stick/stick.png')
        self.texture_pickaxe: Any = self.load('models/items/wooden-pickaxe/wooden_pickaxe.png', rotation=-90)

        # assign texture unit
        self.texture_0.use(location=0)
        self.texture_array_0.use(location=1)
        self.texture_breaking.use(location=3)
        self.texture_stick.use(location=5)
        self.texture_pickaxe.use(location=6)

    @global_profiler.profile_func("Textures_Load")
    def load(self, file_name: str, is_tex_array: bool = False, rotation: int = 0, flip_x: bool = True, flip_y: bool = False) -> Any:
        """
        Reads an image file and converts it into an OpenGL Texture or TextureArray.
        Applies requested rotations/flips and automatically calculates 3D texture array 
        dimensions if the image contains vertical strips.
        """
        texture: Any = pg.image.load(get_path(f'assets/{file_name}'))
        
        if rotation != 0:
            texture = pg.transform.rotate(texture, rotation)
        
        texture = pg.transform.flip(texture, flip_x=flip_x, flip_y=flip_y)

        if is_tex_array:
            num_layers = 3 * texture.get_height() // texture.get_width()  # 3 textures per layer
            texture = self.app.ctx.texture_array(
                size=(texture.get_width(), texture.get_height() // num_layers, num_layers),
                components=4,
                data=pg.image.tobytes(texture, 'RGBA', False)
            )
        
        else:
            texture = self.ctx.texture(
                size=texture.get_size(),
                components=4,
                data=pg.image.tobytes(texture, 'RGBA', False)
            )
        
        texture.anisotropy = 32.0
        texture.build_mipmaps()
        texture.filter = (mgl.NEAREST, mgl.NEAREST)
        
        return texture

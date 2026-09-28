"""
Text rendering and caching for OpenGL textures.

This module provides the TextRenderer class, which converts strings into
Pygame surfaces with drop shadows, and then uploads them to the GPU as
ModernGL textures. It supports both caching for static text and immediate
generation for dynamic, single-frame text.
"""

from typing import Any, Dict

import moderngl as mgl
import pygame as pg

from profiler import global_profiler
from settings import FONT_SIZE_STATS, UI_SHADOW_COLOR, UI_TEXT_COLOR


class TextRenderer:
    """
    Handles the rendering of text strings into OpenGL textures.

    Provides methods for caching static text and generating single-frame dynamic text.

    Args:
        app (Any): The main application context.
    """

    @global_profiler.profile_func('TextRenderer_Init')
    def __init__(self, app: Any) -> None:
        """
        Initializes the text renderer, setting up the default font and preparing
        the texture cache.
        """

        # Process logic block
        self.app: Any = app
        self.ctx: Any = app.ctx

        # Execute expression statement
        pg.font.init()

        # Process logic block
        self.font: pg.font.Font = pg.font.SysFont('arial', FONT_SIZE_STATS, bold=True)
        self.textures: Dict[str, Any] = {}

    @global_profiler.profile_func('TextRenderer_GetTexture')
    def get_texture(self, text: str) -> Any:
        """
        Generates and returns an OpenGL texture for the specified text string.
        Caches the generated texture so subsequent requests for the same text
        are returned instantly without re-rendering.
        """

        # Handle conditional branching
        if text in self.textures:
            return self.textures[text]

        # Process logic block
        surface: pg.Surface = self.font.render(text, True, UI_TEXT_COLOR)
        shadow_offset: int = max(2, self.font.get_height() // 15)
        background_surface: pg.Surface = pg.Surface(
            (surface.get_width() + shadow_offset, surface.get_height() + shadow_offset), pg.SRCALPHA
        )
        shadow: pg.Surface = self.font.render(text, True, UI_SHADOW_COLOR)

        # Execute expression statement
        background_surface.blit(shadow, (shadow_offset, shadow_offset))
        background_surface.blit(surface, (0, 0))

        # Process logic block
        texture: Any = self.ctx.texture(
            background_surface.get_size(), 4, pg.image.tobytes(background_surface, 'RGBA', True)
        )

        # Execute expression statement
        texture.build_mipmaps()

        # Initialize and update variables
        texture.filter = (mgl.LINEAR_MIPMAP_LINEAR, mgl.LINEAR)
        self.textures[text] = texture

        # Return computed result
        return texture

    @global_profiler.profile_func('TextRenderer_GetDynamicTexture')
    def get_dynamic_texture(self, text: str) -> Any:
        """
        Generates and returns an OpenGL texture for text that changes frequently.
        Does not cache the texture or build mipmaps, saving memory and processing
        time for single-frame usage.
        """

        # Process logic block
        surface: pg.Surface = self.font.render(text, True, UI_TEXT_COLOR)
        shadow_offset: int = max(2, self.font.get_height() // 15)
        background_surface: pg.Surface = pg.Surface(
            (surface.get_width() + shadow_offset, surface.get_height() + shadow_offset), pg.SRCALPHA
        )
        shadow: pg.Surface = self.font.render(text, True, UI_SHADOW_COLOR)

        # Execute expression statement
        background_surface.blit(shadow, (shadow_offset, shadow_offset))
        background_surface.blit(surface, (0, 0))

        # Process logic block
        texture: Any = self.ctx.texture(
            background_surface.get_size(), 4, pg.image.tobytes(background_surface, 'RGBA', True)
        )

        # Initialize and update variables
        texture.filter = (mgl.LINEAR, mgl.LINEAR)

        # Return computed result
        return texture

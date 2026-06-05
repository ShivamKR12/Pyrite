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
        self.app: Any = app
        self.ctx: Any = app.ctx
        pg.font.init()
        self.font: pg.font.Font = pg.font.SysFont('arial', FONT_SIZE_STATS, bold=True)
        self.textures: Dict[str, Any] = {}

    @global_profiler.profile_func('TextRenderer_GetTexture')
    def get_texture(self, text: str) -> Any:
        """
        Generates and returns an OpenGL texture for the specified text string.
        Caches the generated texture so subsequent requests for the same text
        are returned instantly without re-rendering.
        """
        if text in self.textures:
            return self.textures[text]

        surf: pg.Surface = self.font.render(text, True, UI_TEXT_COLOR)
        shadow_offset: int = max(2, self.font.get_height() // 15)

        bg_surf: pg.Surface = pg.Surface(
            (surf.get_width() + shadow_offset, surf.get_height() + shadow_offset), pg.SRCALPHA
        )

        shadow: pg.Surface = self.font.render(text, True, UI_SHADOW_COLOR)

        bg_surf.blit(shadow, (shadow_offset, shadow_offset))
        bg_surf.blit(surf, (0, 0))

        texture: Any = self.ctx.texture(bg_surf.get_size(), 4, pg.image.tobytes(bg_surf, 'RGBA', True))
        texture.build_mipmaps()
        texture.filter = (mgl.LINEAR_MIPMAP_LINEAR, mgl.LINEAR)
        self.textures[text] = texture

        return texture

    @global_profiler.profile_func('TextRenderer_GetDynamicTexture')
    def get_dynamic_texture(self, text: str) -> Any:
        """
        Generates and returns an OpenGL texture for text that changes frequently.
        Does not cache the texture or build mipmaps, saving memory and processing
        time for single-frame usage.
        """
        surf: pg.Surface = self.font.render(text, True, UI_TEXT_COLOR)

        shadow_offset: int = max(2, self.font.get_height() // 15)

        bg_surf: pg.Surface = pg.Surface(
            (surf.get_width() + shadow_offset, surf.get_height() + shadow_offset), pg.SRCALPHA
        )

        shadow: pg.Surface = self.font.render(text, True, UI_SHADOW_COLOR)

        bg_surf.blit(shadow, (shadow_offset, shadow_offset))
        bg_surf.blit(surf, (0, 0))

        texture: Any = self.ctx.texture(bg_surf.get_size(), 4, pg.image.tobytes(bg_surf, 'RGBA', True))
        # Dynamic textures don't need mipmaps since they are only used for one frame
        texture.filter = (mgl.LINEAR, mgl.LINEAR)

        return texture

from settings import *
import moderngl as mgl
import pygame as pg
from profiler import global_profiler


class TextRenderer:
    """
    Handles the rendering of text strings into OpenGL textures.
    Provides methods for caching static text and generating single-frame dynamic text.
    """
    @global_profiler.profile_func("TextRenderer_Init")
    def __init__(self, app):
        """
        Initializes the text renderer, setting up the default font and preparing
        the texture cache.
        """
        self.app = app
        self.ctx = app.ctx
        pg.font.init()
        self.font = pg.font.SysFont('arial', FONT_SIZE_STATS, bold=True)
        self.textures = {}

    @global_profiler.profile_func("TextRenderer_GetTexture")
    def get_texture(self, text):
        """
        Generates and returns an OpenGL texture for the specified text string.
        Caches the generated texture so subsequent requests for the same text
        are returned instantly without re-rendering.
        """
        if text in self.textures:
            return self.textures[text]
        
        surf = self.font.render(text, True, UI_TEXT_COLOR)
        shadow_offset = max(2, self.font.get_height() // 15)
        
        bg_surf = pg.Surface((surf.get_width() + shadow_offset, surf.get_height() + shadow_offset), pg.SRCALPHA)
        
        shadow = self.font.render(text, True, UI_SHADOW_COLOR)
        
        bg_surf.blit(shadow, (shadow_offset, shadow_offset))
        bg_surf.blit(surf, (0, 0))
        
        texture = self.ctx.texture(bg_surf.get_size(), 4, pg.image.tobytes(bg_surf, 'RGBA', True))
        texture.build_mipmaps()
        texture.filter = (mgl.LINEAR_MIPMAP_LINEAR, mgl.LINEAR)
        self.textures[text] = texture
        
        return texture

    @global_profiler.profile_func("TextRenderer_GetDynamicTexture")
    def get_dynamic_texture(self, text):
        """
        Generates and returns an OpenGL texture for text that changes frequently.
        Does not cache the texture or build mipmaps, saving memory and processing
        time for single-frame usage.
        """
        surf = self.font.render(text, True, UI_TEXT_COLOR)
        
        shadow_offset = max(2, self.font.get_height() // 15)
        
        bg_surf = pg.Surface((surf.get_width() + shadow_offset, surf.get_height() + shadow_offset), pg.SRCALPHA)
        
        shadow = self.font.render(text, True, UI_SHADOW_COLOR)
        
        bg_surf.blit(shadow, (shadow_offset, shadow_offset))
        bg_surf.blit(surf, (0, 0))
        
        texture = self.ctx.texture(bg_surf.get_size(), 4, pg.image.tobytes(bg_surf, 'RGBA', True))
        # Dynamic textures don't need mipmaps since they are only used for one frame
        texture.filter = (mgl.LINEAR, mgl.LINEAR)
        
        return texture

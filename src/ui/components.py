from settings import *
import moderngl as mgl
import pygame as pg
from .meshes import UIColorMesh, UITextMesh
from .text import TextRenderer


class Button:
    def __init__(self, app, text, pos, size, action):
        self.app = app
        self.text = text
        self.pos = pos
        self.size = size
        self.action = action

        self.color_mesh = UIColorMesh(app)
        self.text_renderer = TextRenderer(app)
        self.text_renderer.font = pg.font.SysFont('arial', FONT_SIZE_BUTTONS, bold=True)
        self.text_mesh = UITextMesh(app)

        self.is_hovered = False
        self.base_color = UI_BUTTON_COLOR
        self.hover_color = UI_HOVER_COLOR

    def check_hover(self, mouse_pos):
        x, y = self.pos
        w, h = self.size
        
        # Convert normalized screen coords to pixel coords
        mouse_x, mouse_y = mouse_pos
        win_w, win_h = WIN_RES
        
        # Convert button normalized pos/size to pixel coords
        btn_x = (x + 1) * 0.5 * win_w
        btn_y = (-y + 1) * 0.5 * win_h
        btn_w = w * 0.5 * win_w
        btn_h = h * 0.5 * win_h
        
        self.is_hovered = btn_x - btn_w < mouse_x < btn_x + btn_w and \
                          btn_y - btn_h < mouse_y < btn_y + btn_h
        return self.is_hovered

    def render(self):
        # 1. Render background
        color = self.hover_color if self.is_hovered else self.base_color
        self.color_mesh.program['u_scale'] = (self.size[0], self.size[1])
        self.color_mesh.program['u_offset'] = self.pos
        self.color_mesh.program['u_color'] = color
        self.color_mesh.render()

        # 2. Render text
        tex = self.text_renderer.get_texture(self.text)
        tex.use(location=4)
        tex_w, tex_h = tex.size
        scale_y = self.size[1] * 0.5
        scale_x = scale_y * (tex_w / tex_h) / ASPECT_RATIO
        self.text_mesh.program['u_scale'] = (scale_x, scale_y)
        self.text_mesh.program['u_offset'] = self.pos
        self.text_mesh.render()


class WorldButton:
    def __init__(self, app, save_name, display_name, seed, game_mode, creation_date, last_played, pos, size, action):
        self.app = app
        self.save_name = save_name
        self.display_name = display_name
        self.seed = seed
        self.game_mode = "Survival" if game_mode == 1 else "Creative"
        self.creation_date = creation_date
        self.last_played = last_played
        self.pos = pos
        self.size = size
        self.action = action

        self.color_mesh = UIColorMesh(app)
        self.text_renderer = TextRenderer(app)
        self.text_renderer.font = pg.font.SysFont('arial', FONT_SIZE_BUTTONS, bold=True)
        self.text_mesh = UITextMesh(app)

        self.is_hovered = False
        self.base_color = UI_BUTTON_COLOR
        self.hover_color = UI_HOVER_COLOR
        
        import os
        thumb_path = f'saves/{save_name}_thumb.png'
        if os.path.exists(thumb_path):
            img = pg.image.load(thumb_path).convert_alpha()
        else:
            img = pg.Surface((320, 180), pg.SRCALPHA)
            img.fill((80, 80, 80, 255))
        
        self.thumb_tex = self.app.ctx.texture(img.get_size(), 4, pg.image.tobytes(img, 'RGBA', True))
        self.thumb_tex.filter = (mgl.LINEAR, mgl.LINEAR)

    def check_hover(self, mouse_pos):
        x, y = self.pos
        w, h = self.size
        win_w, win_h = WIN_RES
        btn_x = (x + 1) * 0.5 * win_w
        btn_y = (-y + 1) * 0.5 * win_h
        btn_w = w * 0.5 * win_w
        btn_h = h * 0.5 * win_h
        
        self.is_hovered = btn_x - btn_w < mouse_pos[0] < btn_x + btn_w and \
                          btn_y - btn_h < mouse_pos[1] < btn_y + btn_h
        return self.is_hovered

    def render(self):
        color = self.hover_color if self.is_hovered else self.base_color
        self.color_mesh.program['u_scale'] = (self.size[0], self.size[1])
        self.color_mesh.program['u_offset'] = self.pos
        self.color_mesh.program['u_color'] = color
        self.color_mesh.render()

        self.thumb_tex.use(location=4)
        thumb_h = self.size[1] * 0.8
        thumb_w = thumb_h * (self.thumb_tex.width / self.thumb_tex.height) / ASPECT_RATIO
        thumb_x = self.pos[0] - self.size[0] + 0.02 + thumb_w
        self.text_mesh.program['u_scale'] = (thumb_w, thumb_h)
        self.text_mesh.program['u_offset'] = (thumb_x, self.pos[1])
        self.text_mesh.render()
        
        text_x = thumb_x + thumb_w + 0.02
        
        def render_text(text, offset_y, scale_h):
            tex = self.text_renderer.get_dynamic_texture(text)
            tex.use(location=4)
            scale_y = self.size[1] * scale_h
            scale_x = scale_y * (tex.width / tex.height) / ASPECT_RATIO
            self.text_mesh.program['u_scale'] = (scale_x, scale_y)
            self.text_mesh.program['u_offset'] = (text_x + scale_x, self.pos[1] + self.size[1] * offset_y)
            self.text_mesh.render()
            tex.release()

        render_text(self.display_name, 0.4, 0.25)
        render_text(f"{self.game_mode} Mode  |  Seed: {self.seed}", -0.05, 0.15)
        render_text(f"Created: {self.creation_date}  |  Last Played: {self.last_played}", -0.4, 0.12)


class TextInput:
    def __init__(self, app, pos, size, label=""):
        self.app = app
        self.pos = pos
        self.size = size
        self.label = label
        self.text = ""
        self.is_active = False

        self.color_mesh = UIColorMesh(app)
        self.text_renderer = TextRenderer(app)
        self.text_renderer.font = pg.font.SysFont('arial', FONT_SIZE_BUTTONS, bold=False)
        self.text_mesh = UITextMesh(app)

    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pg.mouse.get_pos()
            x, y = self.pos
            w, h = self.size
            win_w, win_h = WIN_RES
            btn_x = (x + 1) * 0.5 * win_w
            btn_y = (-y + 1) * 0.5 * win_h
            btn_w = w * 0.5 * win_w
            btn_h = h * 0.5 * win_h
            self.is_active = btn_x - btn_w < mouse_pos[0] < btn_x + btn_w and \
                             btn_y - btn_h < mouse_pos[1] < btn_y + btn_h

        if self.is_active and event.type == pg.KEYDOWN:
            if event.key == pg.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pg.K_RETURN or event.key == pg.K_ESCAPE:
                self.is_active = False
            else:
                if len(self.text) < 20 and event.unicode.isprintable():
                    self.text += event.unicode

    def render(self):
        color = (0.2, 0.2, 0.2, 0.9) if self.is_active else (0.1, 0.1, 0.1, 0.7)
        self.color_mesh.program['u_scale'] = (self.size[0], self.size[1])
        self.color_mesh.program['u_offset'] = self.pos
        self.color_mesh.program['u_color'] = color
        self.color_mesh.render()

        display_text = self.text + ("_" if self.is_active and (pg.time.get_ticks() // 500) % 2 == 0 else "")
        if not display_text and not self.is_active:
            display_text = self.label
            
        tex = self.text_renderer.get_dynamic_texture(display_text)
        tex.use(location=4)
        tex_w, tex_h = tex.size
        scale_y = self.size[1] * 0.6
        scale_x = scale_y * (tex_w / tex_h) / ASPECT_RATIO
        
        self.text_mesh.program['u_scale'] = (scale_x, scale_y)
        self.text_mesh.program['u_offset'] = self.pos
        self.text_mesh.render()
        tex.release() # Release dynamic memory instantly to prevent VRAM leaking


class Slider:
    def __init__(self, app, text, pos, size, min_val, max_val, config_key, action=None, is_int=False):
        self.app = app
        self.text = text
        self.pos = pos
        self.size = size
        self.min_val = min_val
        self.max_val = max_val
        self.config_key = config_key
        self.action = action
        self.is_int = is_int

        self.color_mesh = UIColorMesh(app)
        self.text_renderer = TextRenderer(app)
        self.text_renderer.font = pg.font.SysFont('arial', FONT_SIZE_SLIDERS, bold=True)
        self.text_mesh = UITextMesh(app)

        self.is_hovered = False
        self.is_dragging = False

    def update(self):
        mouse_pos = pg.mouse.get_pos()
        x, y = self.pos
        w, h = self.size
        win_w, win_h = WIN_RES
        
        btn_x = (x + 1) * 0.5 * win_w
        btn_y = (-y + 1) * 0.5 * win_h
        btn_w = w * 0.5 * win_w
        btn_h = h * 0.5 * win_h
        
        self.is_hovered = btn_x - btn_w < mouse_pos[0] < btn_x + btn_w and \
                          btn_y - btn_h < mouse_pos[1] < btn_y + btn_h

        if self.is_dragging:
            if not pg.mouse.get_pressed()[0]:
                self.is_dragging = False
                self.app.save_config()
            else:
                progress = (mouse_pos[0] - (btn_x - btn_w)) / (btn_w * 2)
                progress = max(0.0, min(1.0, progress))
                val = self.min_val + progress * (self.max_val - self.min_val)
                
                if self.is_int:
                    val = int(round(val))
                elif self.config_key == 'sensitivity':
                    val = round(val, 4)
                    
                self.app.config[self.config_key] = val
                if self.action:
                    self.action(val)

    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                self.is_dragging = True

    def render(self):
        self.color_mesh.program['u_scale'] = (self.size[0], self.size[1])
        self.color_mesh.program['u_offset'] = self.pos
        self.color_mesh.program['u_color'] = (0.1, 0.1, 0.1, 0.8)
        self.color_mesh.render()
        
        val = self.app.config[self.config_key]
        progress = (val - self.min_val) / (self.max_val - self.min_val)
        
        fill_w = self.size[0] * progress
        fill_x = self.pos[0] - self.size[0] + fill_w
        
        self.color_mesh.program['u_scale'] = (fill_w, self.size[1])
        self.color_mesh.program['u_offset'] = (fill_x, self.pos[1])
        self.color_mesh.program['u_color'] = (0.2, 0.6, 0.3, 0.8)
        self.color_mesh.render()

        if self.is_int or self.config_key == 'fov':
            display_val = int(val)
        else:
            display_val = f"{val:.4f}"
            
        tex = self.text_renderer.get_dynamic_texture(f"{self.text}: {display_val}")
        tex.use(location=4)
        tex_w, tex_h = tex.size
        scale_y = self.size[1] * 0.6
        scale_x = scale_y * (tex_w / tex_h) / ASPECT_RATIO
        
        self.text_mesh.program['u_scale'] = (scale_x, scale_y)
        self.text_mesh.program['u_offset'] = self.pos
        self.text_mesh.render()
        tex.release()

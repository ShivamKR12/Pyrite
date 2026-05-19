from settings import *
import moderngl as mgl
import pygame as pg
from .meshes import UIColorMesh, UITextMesh
from .text import TextRenderer
import os


_shared_ui_resources = {}

def get_shared_resource(app, res_type, **kwargs):
    """Lazily loads and shares UI meshes and fonts to prevent VRAM and CPU bloat."""
    if res_type == 'color_mesh':
        if 'color_mesh' not in _shared_ui_resources:
            _shared_ui_resources['color_mesh'] = UIColorMesh(app)
        return _shared_ui_resources['color_mesh']
    elif res_type == 'text_mesh':
        if 'text_mesh' not in _shared_ui_resources:
            _shared_ui_resources['text_mesh'] = UITextMesh(app)
        return _shared_ui_resources['text_mesh']
    elif res_type == 'text_renderer':
        font_size, bold = kwargs.get('size', 24), kwargs.get('bold', True)
        key = f'text_renderer_{font_size}_{bold}'
        if key not in _shared_ui_resources:
            tr = TextRenderer(app)
            tr.font = pg.font.SysFont('arial', font_size, bold=bold)
            _shared_ui_resources[key] = tr
        return _shared_ui_resources[key]
    elif res_type == 'button_mask':
        radius = kwargs.get('radius', 12)
        w, h = kwargs.get('size', (0.2, 0.05))
        key = f"mask_{w}_{h}_{radius}"
        if key not in _shared_ui_resources:
            px_w = max(1, int(w * WIN_RES.x))
            px_h = max(1, int(h * WIN_RES.y))
            surf = pg.Surface((px_w, px_h), pg.SRCALPHA)
            pg.draw.rect(surf, (255, 255, 255, 255), surf.get_rect(), border_radius=radius)
            tex = app.ctx.texture(surf.get_size(), 4, pg.image.tobytes(surf, 'RGBA', True))
            tex.filter = (mgl.LINEAR, mgl.LINEAR)
            _shared_ui_resources[key] = tex
        return _shared_ui_resources[key]


class Button:
    """
    Represents a clickable UI button with text, hover effects, and an assigned action.
    """
    def __init__(self, app, text, pos, size, action, border_radius=12, elevation=5):
        """
        Initializes the button with its text, position, size, and the callback function
        to execute when clicked. Prepares necessary text and color meshes.
        """
        self.app = app
        self.text = text
        self.pos = pos
        self.size = size
        self.action = action
        self.border_radius = border_radius
        self.elevation = elevation
        self.dynamic_elevation = elevation

        self.color_mesh = get_shared_resource(app, 'color_mesh')
        self.text_mesh = get_shared_resource(app, 'text_mesh')
        self.text_renderer = get_shared_resource(app, 'text_renderer', size=FONT_SIZE_BUTTONS, bold=True)

        self.is_hovered = False
        self.is_pressed = False
        self.base_color = UI_BUTTON_COLOR
        self.hover_color = UI_HOVER_COLOR

    def check_hover(self, mouse_pos):
        """
        Checks if the given mouse position falls within the button's screen boundaries
        and updates its hover state accordingly.
        """
        x, y = self.pos
        y_dynamic = y + (self.dynamic_elevation / WIN_RES.y)
        w, h = self.size
        
        # Convert normalized screen coords to pixel coords
        mouse_x, mouse_y = mouse_pos
        win_w, win_h = WIN_RES
        
        # Convert button normalized pos/size to pixel coords
        btn_x = (x + 1) * 0.5 * win_w
        btn_y = (-y_dynamic + 1) * 0.5 * win_h
        btn_w = w * 0.5 * win_w
        btn_h = h * 0.5 * win_h
        
        self.is_hovered = btn_x - btn_w < mouse_x < btn_x + btn_w and \
                          btn_y - btn_h < mouse_y < btn_y + btn_h
                          
        if not self.is_hovered and self.is_pressed:
            self.is_pressed = False
            self.dynamic_elevation = self.elevation
            
        return self.is_hovered

    def handle_event(self, event):
        """
        Tracks mouse clicks to animate the button and trigger its assigned action
        only when the mouse is released while still hovering over it.
        """
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                self.is_pressed = True
                self.dynamic_elevation = 0
        elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
            if self.is_pressed:
                self.is_pressed = False
                self.dynamic_elevation = self.elevation
                if self.is_hovered and self.action:
                    self.action()

    def render(self, offset=(0, 0), alpha=1.0):
        """
        Renders the button with a 3D elevation effect and state-dependent colors.
        """
        px, py = self.pos
        w, h = self.size
        
        # Render Bottom (Elevation) Quad
        mask = get_shared_resource(self.app, 'button_mask', radius=self.border_radius, size=(w, h))
        mask.use(location=4)
        
        b_c = self.base_color
        self.text_mesh.program['u_scale'] = (w, h)
        self.text_mesh.program['u_offset'] = (px + offset[0], py + offset[1])
        if 'u_color' in self.text_mesh.program: self.text_mesh.program['u_color'] = (b_c[0] * 0.5, b_c[1] * 0.5, b_c[2] * 0.5, b_c[3])
        if 'u_alpha' in self.text_mesh.program: self.text_mesh.program['u_alpha'] = alpha
        self.text_mesh.render()

        # Render Top (Main) Quad
        py_dynamic = py + (self.dynamic_elevation / WIN_RES.y)
        c = self.hover_color if self.is_hovered else self.base_color
        self.text_mesh.program['u_scale'] = (w, h)
        self.text_mesh.program['u_offset'] = (px + offset[0], py_dynamic + offset[1])
        if 'u_color' in self.text_mesh.program: self.text_mesh.program['u_color'] = c
        self.text_mesh.render()

        # Render Text
        tex = self.text_renderer.get_texture(self.text)
        tex.use(location=4)
        tex_w, tex_h = tex.size
        scale_y = h * 0.5
        scale_x = scale_y * (tex_w / tex_h) / ASPECT_RATIO
        self.text_mesh.program['u_scale'] = (scale_x, scale_y)
        self.text_mesh.program['u_offset'] = (px + offset[0], py_dynamic + offset[1])
        if 'u_color' in self.text_mesh.program: self.text_mesh.program['u_color'] = (1.0, 1.0, 1.0, 1.0)
        self.text_mesh.render()
        if 'u_alpha' in self.text_mesh.program: self.text_mesh.program['u_alpha'] = 1.0


class WorldButton:
    """
    A specialized button used in the World Selection menu to display rich information 
    about a saved game world, including its thumbnail, seed, and playtime data.
    """
    def __init__(self, app, save_name, display_name, seed, game_mode, creation_date, last_played, pos, size, action, border_radius=12, elevation=5):
        """
        Initializes the world button with detailed metadata and loads its corresponding
        saved thumbnail image from the disk.
        """
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
        self.border_radius = border_radius
        self.elevation = elevation
        self.dynamic_elevation = elevation

        self.color_mesh = get_shared_resource(app, 'color_mesh')
        self.text_mesh = get_shared_resource(app, 'text_mesh')
        self.text_renderer = get_shared_resource(app, 'text_renderer', size=FONT_SIZE_BUTTONS, bold=True)

        self.is_hovered = False
        self.is_pressed = False
        self.base_color = UI_BUTTON_COLOR
        self.hover_color = UI_HOVER_COLOR
        
        thumb_path = f'saves/{save_name}_thumb.png'
        if os.path.exists(thumb_path):
            img = pg.image.load(thumb_path).convert_alpha()
        else:
            img = pg.Surface((320, 180), pg.SRCALPHA)
            img.fill((80, 80, 80, 255))
        
        self.thumb_tex = self.app.ctx.texture(img.get_size(), 4, pg.image.tobytes(img, 'RGBA', True))
        self.thumb_tex.filter = (mgl.LINEAR, mgl.LINEAR)

    def check_hover(self, mouse_pos):
        """
        Calculates if the mouse cursor is currently over the button's bounding box
        to trigger visual hover states.
        """
        x, y = self.pos
        y_dynamic = y + (self.dynamic_elevation / WIN_RES.y)
        w, h = self.size
        win_w, win_h = WIN_RES
        btn_x = (x + 1) * 0.5 * win_w
        btn_y = (-y_dynamic + 1) * 0.5 * win_h
        btn_w = w * 0.5 * win_w
        btn_h = h * 0.5 * win_h
        
        self.is_hovered = btn_x - btn_w < mouse_pos[0] < btn_x + btn_w and \
                          btn_y - btn_h < mouse_pos[1] < btn_y + btn_h
                          
        if not self.is_hovered and self.is_pressed:
            self.is_pressed = False
            self.dynamic_elevation = self.elevation
            
        return self.is_hovered

    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                self.is_pressed = True
                self.dynamic_elevation = 0
        
        elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
            if self.is_pressed:
                self.is_pressed = False
                self.dynamic_elevation = self.elevation
                if self.is_hovered and self.action:
                    self.action()

    def render(self, offset=(0, 0), alpha=1.0):
        """
        Draws the interactive button background, the world thumbnail image, and dynamically
        generates the text layout for the world's metadata.
        """
        px, py = self.pos
        w, h = self.size

        mask = get_shared_resource(self.app, 'button_mask', radius=self.border_radius, size=(w, h))
        mask.use(location=4)
        
        b_c = self.base_color
        render_pos_bottom = (px + offset[0], py + offset[1])
        self.text_mesh.program['u_scale'] = (w, h)
        self.text_mesh.program['u_offset'] = render_pos_bottom
        if 'u_color' in self.text_mesh.program: self.text_mesh.program['u_color'] = (b_c[0] * 0.5, b_c[1] * 0.5, b_c[2] * 0.5, b_c[3])
        if 'u_alpha' in self.text_mesh.program: self.text_mesh.program['u_alpha'] = alpha
        self.text_mesh.render()

        py_dynamic = py + (self.dynamic_elevation / WIN_RES.y)
        render_pos_top = (px + offset[0], py_dynamic + offset[1])
        c = self.hover_color if self.is_hovered else self.base_color
        self.text_mesh.program['u_scale'] = (w, h)
        self.text_mesh.program['u_offset'] = render_pos_top
        if 'u_color' in self.text_mesh.program: self.text_mesh.program['u_color'] = c
        self.text_mesh.render()

        if 'u_color' in self.text_mesh.program: self.text_mesh.program['u_color'] = (1.0, 1.0, 1.0, 1.0)

        self.thumb_tex.use(location=4)
        thumb_h = h * 0.8
        thumb_w = thumb_h * (self.thumb_tex.width / self.thumb_tex.height) / ASPECT_RATIO
        thumb_x = render_pos_top[0] - w + 0.02 + thumb_w
        self.text_mesh.program['u_scale'] = (thumb_w, thumb_h)
        self.text_mesh.program['u_offset'] = (thumb_x, render_pos_top[1])
        self.text_mesh.render()
        
        text_x = thumb_x + thumb_w + 0.02
        
        def render_text(text, offset_y, scale_h):
            tex = self.text_renderer.get_dynamic_texture(text)
            tex.use(location=4)
            scale_y = h * scale_h
            scale_x = scale_y * (tex.width / tex.height) / ASPECT_RATIO
            self.text_mesh.program['u_scale'] = (scale_x, scale_y)
            self.text_mesh.program['u_offset'] = (text_x + scale_x, render_pos_top[1] + h * offset_y)
            self.text_mesh.render()
            tex.release()

        render_text(self.display_name, 0.4, 0.25)
        render_text(f"{self.game_mode} Mode  |  Seed: {self.seed}", -0.05, 0.15)
        render_text(f"Created: {self.creation_date}  |  Last Played: {self.last_played}", -0.4, 0.12)
        if 'u_alpha' in self.text_mesh.program: self.text_mesh.program['u_alpha'] = 1.0


class TextInput:
    """
    Provides a simple interactive text entry field for the UI.
    Captures keyboard input and visually indicates when it is active.
    """
    def __init__(self, app, pos, size, label=""):
        """
        Initializes the text input field with a placeholder label, screen position,
        and sets up the required text rendering meshes.
        """
        self.app = app
        self.pos = pos
        self.size = size
        self.label = label
        self.text = ""
        self.is_active = False

        self.color_mesh = get_shared_resource(app, 'color_mesh')
        self.text_mesh = get_shared_resource(app, 'text_mesh')
        self.text_renderer = get_shared_resource(app, 'text_renderer', size=FONT_SIZE_BUTTONS, bold=False)

    def handle_event(self, event):
        """
        Processes mouse clicks to activate/deactivate the input field and captures
        keyboard keystrokes to append or delete characters from the text string.
        """
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

    def render(self, offset=(0, 0), alpha=1.0):
        """
        Draws the input field's background and current text. Renders a blinking 
        underscore cursor if the field is currently active.
        """
        w, h = self.size
        c = (0.2, 0.25, 0.3, 0.9) if self.is_active else (0.1, 0.12, 0.15, 0.7)
        color = (c[0], c[1], c[2], c[3] * alpha)
        render_pos = (self.pos[0] + offset[0], self.pos[1] + offset[1])
        
        mask = get_shared_resource(self.app, 'button_mask', radius=8, size=(w, h))
        mask.use(location=4)
        self.text_mesh.program['u_scale'] = (w, h)
        self.text_mesh.program['u_offset'] = render_pos
        if 'u_color' in self.text_mesh.program: self.text_mesh.program['u_color'] = color
        if 'u_alpha' in self.text_mesh.program: self.text_mesh.program['u_alpha'] = 1.0
        self.text_mesh.render()

        display_text = self.text + ("_" if self.is_active and (pg.time.get_ticks() // 500) % 2 == 0 else "")
        if not display_text and not self.is_active:
            display_text = self.label
            
        if 'u_color' in self.text_mesh.program: self.text_mesh.program['u_color'] = (1.0, 1.0, 1.0, 1.0)
        if 'u_alpha' in self.text_mesh.program: self.text_mesh.program['u_alpha'] = alpha
        
        # The rest of your text rendering logic remains the same
        tex = self.text_renderer.get_dynamic_texture(display_text)
        tex.use(location=4)
        tex_w, tex_h = tex.size
        scale_y = h * 0.6
        scale_x = scale_y * (tex_w / tex_h) / ASPECT_RATIO
        
        self.text_mesh.program['u_scale'] = (scale_x, scale_y)
        self.text_mesh.program['u_offset'] = render_pos
        self.text_mesh.render()
        tex.release()


class Slider:
    """
    An interactive UI slider component used to adjust numerical settings 
    between a predefined minimum and maximum value.
    """
    def __init__(self, app, text, pos, size, min_val, max_val, config_key, action=None, is_int=False):
        """
        Initializes the slider, binding it to a specific configuration key, setting 
        its value range, and preparing its visual meshes.
        """
        self.app = app
        self.text = text
        self.pos = pos
        self.size = size
        self.min_val = min_val
        self.max_val = max_val
        self.config_key = config_key
        self.action = action
        self.is_int = is_int

        self.color_mesh = get_shared_resource(app, 'color_mesh')
        self.text_mesh = get_shared_resource(app, 'text_mesh')
        self.text_renderer = get_shared_resource(app, 'text_renderer', size=FONT_SIZE_SLIDERS, bold=True)

        self.is_hovered = False
        self.is_dragging = False

    def update(self, mouse_pos=None):
        """
        Updates the slider's hover state and dragging interaction. Modifies the 
        associated configuration value based on the mouse's horizontal position 
        along the slider track.
        """
        if mouse_pos is None:
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
        """
        Detects mouse down events to initiate the dragging state if the cursor 
        is hovering over the slider.
        """
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                self.is_dragging = True

    def render(self, offset=(0, 0), alpha=1.0):
        """
        Renders the dark background track, the highlighted fill bar representing 
        the current progress, and the dynamic text showing the exact numerical value.
        """
        w, h = self.size
        render_pos = (self.pos[0] + offset[0], self.pos[1] + offset[1])

        mask = get_shared_resource(self.app, 'button_mask', radius=8, size=(w, h))
        mask.use(location=4)
        self.text_mesh.program['u_scale'] = (w, h)
        self.text_mesh.program['u_offset'] = render_pos
        if 'u_color' in self.text_mesh.program: self.text_mesh.program['u_color'] = (0.1, 0.1, 0.1, 0.8 * alpha)
        if 'u_alpha' in self.text_mesh.program: self.text_mesh.program['u_alpha'] = 1.0
        self.text_mesh.render()
        
        val = self.app.config[self.config_key]
        progress = (val - self.min_val) / (self.max_val - self.min_val)
        
        if progress > 0:
            # Clip the fill bar to the correct progress width
            clip_x_max = render_pos[0] - w + (w * 2 * progress)
            if 'u_clip' in self.app.shader_program.ui_text: self.app.shader_program.ui_text['u_clip'] = (-2.0, -2.0, clip_x_max, 2.0)

            fill_color = (UI_HOVER_COLOR[0], UI_HOVER_COLOR[1], UI_HOVER_COLOR[2], UI_HOVER_COLOR[3] * alpha)
            if 'u_color' in self.text_mesh.program: self.text_mesh.program['u_color'] = fill_color
            self.text_mesh.render()

            # Reset clipping area
            if 'u_clip' in self.app.shader_program.ui_text: self.app.shader_program.ui_text['u_clip'] = (-2.0, -2.0, 2.0, 2.0)

        if self.is_int or self.config_key == 'fov':
            display_val = int(val)
        else:
            display_val = f"{val:.4f}"
            
        tex = self.text_renderer.get_dynamic_texture(f"{self.text}: {display_val}")
        tex.use(location=4)
        tex_w, tex_h = tex.size
        scale_y = h * 0.6
        scale_x = scale_y * (tex_w / tex_h) / ASPECT_RATIO
        
        self.text_mesh.program['u_scale'] = (scale_x, scale_y)
        self.text_mesh.program['u_offset'] = render_pos
        if 'u_color' in self.text_mesh.program: self.text_mesh.program['u_color'] = (1.0, 1.0, 1.0, 1.0)
        if 'u_alpha' in self.text_mesh.program: self.text_mesh.program['u_alpha'] = alpha
        self.text_mesh.render()
        if 'u_alpha' in self.text_mesh.program: self.text_mesh.program['u_alpha'] = 1.0
        tex.release()


class Toggle:
    """
    A binary toggle switch component for the UI (e.g. On/Off settings).
    """
    def __init__(self, app, text, pos, size, config_key, action=None):
        self.app = app
        self.text = text
        self.pos = pos
        self.size = size
        self.config_key = config_key
        self.action = action

        self.color_mesh = get_shared_resource(app, 'color_mesh')
        self.text_mesh = get_shared_resource(app, 'text_mesh')
        self.text_renderer = get_shared_resource(app, 'text_renderer', size=FONT_SIZE_SLIDERS, bold=True)

        self.is_hovered = False

    def update(self, mouse_pos=None):
        if mouse_pos is None:
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

    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                val = self.app.config.get(self.config_key, False)
                self.app.config[self.config_key] = not val
                self.app.save_config()
                if self.action:
                    self.action(not val)

    def render(self, offset=(0, 0), alpha=1.0):
        w, h = self.size
        render_pos = (self.pos[0] + offset[0], self.pos[1] + offset[1])

        val = self.app.config.get(self.config_key, False)

        # Render text aligned to the left of the toggle switch
        display_val = 'ON' if val else 'OFF'
        tex = self.text_renderer.get_dynamic_texture(f"{self.text}: {display_val}")
        tex.use(location=4)
        tex_w, tex_h = tex.size
        scale_y = h * 0.8
        scale_x = scale_y * (tex_w / tex_h) / ASPECT_RATIO
        
        text_x = render_pos[0] - w - scale_x - 0.02
        
        self.text_mesh.program['u_scale'] = (scale_x, scale_y)
        self.text_mesh.program['u_offset'] = (text_x, render_pos[1])
        if 'u_color' in self.text_mesh.program: self.text_mesh.program['u_color'] = (1.0, 1.0, 1.0, 1.0)
        if 'u_alpha' in self.text_mesh.program: self.text_mesh.program['u_alpha'] = alpha
        self.text_mesh.render()
        tex.release()

        # Render track (pill shape)
        track_mask = get_shared_resource(self.app, 'button_mask', radius=int(h * WIN_RES.y), size=(w, h))
        track_mask.use(location=4)
        self.text_mesh.program['u_scale'] = (w, h)
        self.text_mesh.program['u_offset'] = render_pos
        if 'u_color' in self.text_mesh.program: self.text_mesh.program['u_color'] = (0.1, 0.1, 0.1, 0.8 * alpha)
        if 'u_alpha' in self.text_mesh.program: self.text_mesh.program['u_alpha'] = 1.0
        self.text_mesh.render()
        
        thumb_w, thumb_h = h / ASPECT_RATIO, h
        travel_dist = w - thumb_w
        thumb_x = render_pos[0] + travel_dist if val else render_pos[0] - travel_dist

        thumb_mask = get_shared_resource(self.app, 'button_mask', radius=int(h * WIN_RES.y), size=(thumb_w, thumb_h))
        thumb_mask.use(location=4)
        self.text_mesh.program['u_scale'] = (thumb_w, thumb_h)
        self.text_mesh.program['u_offset'] = (thumb_x, render_pos[1])
        
        base_c = (0.2, 0.7, 0.3, alpha) if val else (0.7, 0.2, 0.2, alpha)
        if self.is_hovered:
            base_c = (base_c[0]+0.1, base_c[1]+0.1, base_c[2]+0.1, alpha)
        if 'u_color' in self.text_mesh.program: self.text_mesh.program['u_color'] = base_c
        self.text_mesh.render()
        if 'u_alpha' in self.text_mesh.program: self.text_mesh.program['u_alpha'] = 1.0

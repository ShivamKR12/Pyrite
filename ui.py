from settings import *
from meshes.base_mesh import BaseMesh
import numpy as np
import moderngl as mgl
import pygame as pg
import glm
from meshes.item_mesh import ItemMesh

class CrosshairMesh(BaseMesh):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.ctx = self.app.ctx
        self.program = self.app.shader_program.quad
        self.vbo_format = '3f 3f'
        self.attrs = ('in_position', 'in_color')
        self.vao = self.get_vao()

    def get_vertex_data(self):
        w = 0.015
        h = w * ASPECT_RATIO
        # Creates a perfect '+' sign in the center of the screen
        vertices = [
            # Horizontal line
            (-w, -0.002 * ASPECT_RATIO, 0.0), (w, -0.002 * ASPECT_RATIO, 0.0), (w, 0.002 * ASPECT_RATIO, 0.0),
            (-w, -0.002 * ASPECT_RATIO, 0.0), (w, 0.002 * ASPECT_RATIO, 0.0), (-w, 0.002 * ASPECT_RATIO, 0.0),
            # Vertical line
            (-0.002, -h, 0.0), (0.002, -h, 0.0), (0.002, h, 0.0),
            (-0.002, -h, 0.0), (0.002, h, 0.0), (-0.002, h, 0.0)
        ]
        colors = [(0.9, 0.9, 0.9) for _ in vertices]
        return np.hstack([vertices, colors]).astype('float32')

class BlockIconMesh(BaseMesh):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.ctx = self.app.ctx
        self.program = self.app.shader_program.ui_block
        self.vbo_format = '2f 2f'
        self.attrs = ('in_position', 'in_tex_coord')
        self.vao = self.get_vao()

    def get_vertex_data(self):
        # Standard normalized quad [-1, 1]
        vertices = [
            (-1.0, -1.0), ( 1.0, -1.0), ( 1.0,  1.0),
            (-1.0, -1.0), ( 1.0,  1.0), (-1.0,  1.0)
        ]
        tex_coords = [(0, 0), (1, 0), (1, 1), (0, 0), (1, 1), (0, 1)]
        return np.hstack([vertices, tex_coords]).astype('float32')

class UIColorMesh(BaseMesh):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.ctx = self.app.ctx
        self.program = self.app.shader_program.ui_color
        self.vbo_format = '2f'
        self.attrs = ('in_position',)
        self.vao = self.get_vao()

    def get_vertex_data(self):
        vertices = [
            (-1.0, -1.0), ( 1.0, -1.0), ( 1.0,  1.0),
            (-1.0, -1.0), ( 1.0,  1.0), (-1.0,  1.0)
        ]
        return np.array(vertices, dtype='float32')

class UITextMesh(BaseMesh):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.ctx = self.app.ctx
        self.program = self.app.shader_program.ui_text
        self.vbo_format = '2f 2f'
        self.attrs = ('in_position', 'in_tex_coord')
        self.vao = self.get_vao()

    def get_vertex_data(self):
        vertices = [
            (-1.0, -1.0), ( 1.0, -1.0), ( 1.0,  1.0),
            (-1.0, -1.0), ( 1.0,  1.0), (-1.0,  1.0)
        ]
        tex_coords = [(0, 0), (1, 0), (1, 1), (0, 0), (1, 1), (0, 1)]
        return np.hstack([vertices, tex_coords]).astype('float32')

class TextRenderer:
    def __init__(self, app):
        self.app = app
        self.ctx = app.ctx
        pg.font.init()
        self.font = pg.font.SysFont('arial', 20, bold=True)
        self.textures = {}

    def get_texture(self, text):
        if text in self.textures:
            return self.textures[text]
        surf = self.font.render(text, True, (255, 255, 255))
        bg_surf = pg.Surface((surf.get_width() + 2, surf.get_height() + 2), pg.SRCALPHA)
        shadow = self.font.render(text, True, (40, 40, 40))
        bg_surf.blit(shadow, (2, 2))
        bg_surf.blit(surf, (0, 0))
        texture = self.ctx.texture(bg_surf.get_size(), 4, pg.image.tostring(bg_surf, 'RGBA', True))
        texture.filter = (mgl.LINEAR, mgl.LINEAR)
        self.textures[text] = texture
        return texture

class Crosshair:
    def __init__(self, app):
        self.app = app
        self.mesh = CrosshairMesh(app)

    def render(self):
        self.mesh.render()

class Hotbar:
    def __init__(self, app):
        self.app = app
        self.block_mesh = BlockIconMesh(app)
        self.color_mesh = UIColorMesh(app)
        self.text_mesh = UITextMesh(app)
        self.text_renderer = TextRenderer(app)
        
    def render(self):
        player = self.app.player
        s = 0.045  # Base scale for blocks
        slot_s = 0.06 # Scale of slot background
        spacing = 0.13
        start_x = -4 * spacing
        y = -0.85
        
        # 1. Draw the transparent slot backgrounds and selection frame
        for i in range(9):
            x = start_x + i * spacing
            is_selected = (i == player.hotbar_index)
            
            if is_selected:
                # Draw white outline frame
                sel_s = slot_s + 0.006
                self.color_mesh.program['u_scale'] = (sel_s / ASPECT_RATIO, sel_s)
                self.color_mesh.program['u_offset'] = (x, y)
                self.color_mesh.program['u_color'] = (0.9, 0.9, 0.9, 0.9)
                self.color_mesh.render()
                
                # Draw slightly lighter inner background
                self.color_mesh.program['u_scale'] = (slot_s / ASPECT_RATIO, slot_s)
                self.color_mesh.program['u_color'] = (0.5, 0.5, 0.5, 0.7)
                self.color_mesh.render()
            else:
                # Draw standard dark background
                self.color_mesh.program['u_scale'] = (slot_s / ASPECT_RATIO, slot_s)
                self.color_mesh.program['u_offset'] = (x, y)
                self.color_mesh.program['u_color'] = (0.2, 0.2, 0.2, 0.6)
                self.color_mesh.render()

        # 2. Draw the 3D block icons inside the slots
        for i in range(9):
            voxel_id = player.hotbar[i]
            if voxel_id != 0:
                self.block_mesh.program['u_scale'] = (s / ASPECT_RATIO, s)
                self.block_mesh.program['u_offset'] = (start_x + i * spacing, y)
                self.block_mesh.program['voxel_id'] = voxel_id
                self.block_mesh.render()

        # 3. Draw the stack counts
        for i in range(9):
            count = player.hotbar_counts[i]
            if count > 0:
                tex = self.text_renderer.get_texture(str(count))
                tex.use(location=4)
                
                tex_w, tex_h = tex.size
                scale_y = 0.015
                scale_x = scale_y * (tex_w / tex_h) / ASPECT_RATIO
                
                offset_x = start_x + i * spacing + 0.015
                offset_y = y - 0.025
                
                self.text_mesh.program['u_scale'] = (scale_x, scale_y)
                self.text_mesh.program['u_offset'] = (offset_x, offset_y)
                self.text_mesh.render()

class HeldBlock:
    def __init__(self, app):
        self.app = app
        self.mesh = ItemMesh(app)

    def render(self):
        player = self.app.player
        voxel_id = player.hotbar[player.hotbar_index]
        if voxel_id == 0:
            return

        # 1. View bobbing
        bob_offset_y = glm.sin(player.step_counter) * 0.03
        bob_offset_x = glm.cos(player.step_counter * 0.5) * 0.02

        # 2. Swinging animation
        swing_offset_y = 0.0
        swing_offset_z = 0.0
        swing_rot_x = 0.0
        
        if player.mining_time > 0.0:
            swing_val = max(0, glm.sin(player.mining_time * 0.03))
            swing_offset_y = swing_val * 0.15
            swing_offset_z = -swing_val * 0.1
            swing_rot_x = swing_val * 0.4
        else:
            time_since_place = pg.time.get_ticks() - player.interaction_timer
            if time_since_place < player.interaction_delay:
                progress = time_since_place / player.interaction_delay
                swing_val = glm.sin(progress * glm.pi())
                swing_offset_y = swing_val * 0.2
                swing_rot_x = swing_val * 0.3

        # 3. Position the block in the bottom right (in local camera space)
        pos = glm.vec3(0.5 + bob_offset_x, -0.4 + bob_offset_y - swing_offset_y, -1.0 + swing_offset_z)
        
        # Compute Model Matrix in World Space for perfectly accurate lighting
        m_model = glm.inverse(player.m_view)
        m_model = glm.translate(m_model, pos)
        m_model = glm.rotate(m_model, glm.radians(-15.0) - swing_rot_x, glm.vec3(1, 0, 0)) # Tilt slightly down
        m_model = glm.rotate(m_model, glm.radians(45.0), glm.vec3(0, 1, 0))                # Rotate to show faces
        m_model = glm.scale(m_model, glm.vec3(0.35))

        self.mesh.program['m_proj'].write(player.m_proj)
        self.mesh.program['m_view'].write(player.m_view) 
        self.mesh.program['m_model'].write(m_model)
        self.mesh.program['voxel_id'] = voxel_id

        self.app.ctx.disable(mgl.DEPTH_TEST) # Draw on top of the world without depth clearing
        self.mesh.render()
        self.app.ctx.enable(mgl.DEPTH_TEST)

class Button:
    def __init__(self, app, text, pos, size, action):
        self.app = app
        self.text = text
        self.pos = pos
        self.size = size
        self.action = action

        self.color_mesh = UIColorMesh(app)
        self.text_renderer = TextRenderer(app)
        self.text_renderer.font = pg.font.SysFont('arial', 40, bold=True)
        self.text_mesh = UITextMesh(app)

        self.is_hovered = False
        self.base_color = (0.2, 0.2, 0.2, 0.7)
        self.hover_color = (0.3, 0.3, 0.3, 0.8)

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

class Menu:
    def __init__(self, app):
        self.app = app
        self.title_renderer = TextRenderer(app)
        self.title_renderer.font = pg.font.SysFont('arial', 100, bold=True)
        self.title_mesh = UITextMesh(app)

        self.buttons = [
            Button(app, 'Start Game', (0, 0.15), (0.2, 0.07), self.app.init_game_session),
            Button(app, 'Options', (0, 0.0), (0.2, 0.07), self.open_options),
            Button(app, 'Quit', (0, -0.15), (0.2, 0.07), self.app.quit_game)
        ]

    def open_options(self):
        self.app.options_menu.previous_state = 'MAIN_MENU'
        self.app.game_state = 'OPTIONS'

    def update(self):
        mouse_pos = pg.mouse.get_pos()
        for button in self.buttons:
            button.check_hover(mouse_pos)

    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            for button in self.buttons:
                if button.is_hovered:
                    button.action()
                    break

    def render(self):
        # Render title
        tex = self.title_renderer.get_texture("Voxel Engine")
        tex.use(location=4)
        
        tex_w, tex_h = tex.size
        scale_y = 0.1
        scale_x = scale_y * (tex_w / tex_h) / ASPECT_RATIO
        
        self.title_mesh.program['u_scale'] = (scale_x, scale_y)
        self.title_mesh.program['u_offset'] = (0.0, 0.5)
        self.title_mesh.render()

        # Render buttons
        for button in self.buttons:
            button.render()

class PauseMenu:
    def __init__(self, app):
        self.app = app
        self.title_renderer = TextRenderer(app)
        self.title_renderer.font = pg.font.SysFont('arial', 80, bold=True)
        self.title_mesh = UITextMesh(app)
        self.bg_mesh = UIColorMesh(app)

        self.buttons = [
            Button(app, 'Resume', (0, 0.15), (0.3, 0.07), self.resume_game),
            Button(app, 'Options', (0, 0.0), (0.3, 0.07), self.open_options),
            Button(app, 'Quit to Menu', (0, -0.15), (0.3, 0.07), self.quit_to_menu)
        ]

    def open_options(self):
        self.app.options_menu.previous_state = 'PAUSED'
        self.app.game_state = 'OPTIONS'

    def resume_game(self):
        self.app.game_state = 'IN_GAME'
        pg.event.set_grab(True)
        pg.mouse.set_visible(False)

    def quit_to_menu(self):
        self.app.game_state = 'MAIN_MENU'
        if self.app.scene:
            self.app.scene.world.save()
            self.app.scene = None # Unload the world to free memory

    def update(self):
        mouse_pos = pg.mouse.get_pos()
        for button in self.buttons:
            button.check_hover(mouse_pos)

    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            for button in self.buttons:
                if button.is_hovered:
                    button.action()
                    break

    def render(self):
        self.bg_mesh.program['u_scale'] = (1.0, 1.0)
        self.bg_mesh.program['u_offset'] = (0.0, 0.0)
        self.bg_mesh.program['u_color'] = (0.0, 0.0, 0.0, 0.6)
        self.bg_mesh.render()

        tex = self.title_renderer.get_texture("Game Paused")
        tex.use(location=4)
        tex_w, tex_h = tex.size
        scale_y = 0.08
        scale_x = scale_y * (tex_w / tex_h) / ASPECT_RATIO
        self.title_mesh.program['u_scale'] = (scale_x, scale_y)
        self.title_mesh.program['u_offset'] = (0.0, 0.4)
        self.title_mesh.render()

        for button in self.buttons:
            button.render()

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
        self.text_renderer.font = pg.font.SysFont('arial', 30, bold=True)
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
            
        tex = self.text_renderer.get_texture(f"{self.text}: {display_val}")
        tex.use(location=4)
        tex_w, tex_h = tex.size
        scale_y = self.size[1] * 0.6
        scale_x = scale_y * (tex_w / tex_h) / ASPECT_RATIO
        
        self.text_mesh.program['u_scale'] = (scale_x, scale_y)
        self.text_mesh.program['u_offset'] = self.pos
        self.text_mesh.render()

class OptionsMenu:
    def __init__(self, app):
        self.app = app
        self.title_renderer = TextRenderer(app)
        self.title_renderer.font = pg.font.SysFont('arial', 80, bold=True)
        self.title_mesh = UITextMesh(app)
        self.bg_mesh = UIColorMesh(app)

        self.sliders = [
            Slider(app, 'FOV', (0, 0.2), (0.3, 0.05), 30, 110, 'fov', self.update_fov, is_int=True),
            Slider(app, 'Sensitivity', (0, 0.0), (0.3, 0.05), 0.0005, 0.005, 'sensitivity'),
            Slider(app, 'Volume', (0, -0.2), (0.3, 0.05), 0, 100, 'volume', self.update_volume, is_int=True),
            Slider(app, 'Render Distance', (0, -0.4), (0.3, 0.05), 2, 14, 'render_distance', is_int=True)
        ]
        self.back_button = Button(app, 'Back', (0, -0.6), (0.2, 0.07), self.go_back)
        self.previous_state = 'MAIN_MENU'

    def update_fov(self, val):
        if self.app.scene:
            self.app.player.fov = glm.radians(val)

    def update_volume(self, val):
        pg.mixer.music.set_volume(val / 100.0)

    def go_back(self):
        self.app.game_state = self.previous_state

    def update(self):
        for slider in self.sliders:
            slider.update()
        self.back_button.check_hover(pg.mouse.get_pos())

    def handle_event(self, event):
        for slider in self.sliders:
            slider.handle_event(event)
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.back_button.is_hovered:
                self.back_button.action()

    def render(self):
        if self.previous_state == 'PAUSED':
            self.bg_mesh.program['u_scale'] = (1.0, 1.0)
            self.bg_mesh.program['u_offset'] = (0.0, 0.0)
            self.bg_mesh.program['u_color'] = (0.0, 0.0, 0.0, 0.8)
            self.bg_mesh.render()

        tex = self.title_renderer.get_texture("Options")
        tex.use(location=4)
        tex_w, tex_h = tex.size
        scale_y = 0.08
        scale_x = scale_y * (tex_w / tex_h) / ASPECT_RATIO
        self.title_mesh.program['u_scale'] = (scale_x, scale_y)
        self.title_mesh.program['u_offset'] = (0.0, 0.45)
        self.title_mesh.render()

        for slider in self.sliders:
            slider.render()
        self.back_button.render()
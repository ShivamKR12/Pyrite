from settings import *
import pygame as pg
import moderngl as mgl
from pyglm import glm
from .components import Button, WorldButton, TextInput, Slider
from .meshes import UIColorMesh, UITextMesh
from .text import TextRenderer


class Menu:
    def __init__(self, app):
        self.app = app
        self.title_renderer = TextRenderer(app)
        self.title_renderer.font = pg.font.SysFont('arial', FONT_SIZE_TITLE, bold=True)
        self.title_mesh = UITextMesh(app)

        try:
            img = pg.image.load(get_path('assets/pyrite.png')).convert_alpha()
            self.title_tex = self.app.ctx.texture(img.get_size(), 4, pg.image.tobytes(img, 'RGBA', True))
            self.title_tex.build_mipmaps()
            self.title_tex.filter = (mgl.LINEAR_MIPMAP_LINEAR, mgl.LINEAR)
        except Exception:
            self.title_tex = self.title_renderer.get_texture("Pyrite")

        self.state = 'MAIN'
        self.world_buttons = []
        self.delete_buttons = []
        self.scroll_offset = 0.0

        # Main Menu
        self.btn_play = Button(app, 'Play', (0, 0.15), (0.2, 0.07), lambda: self.set_state('SELECT_WORLD'))
        self.btn_options = Button(app, 'Options', (0, 0.0), (0.2, 0.07), self.open_options)
        self.btn_quit = Button(app, 'Quit', (0, -0.15), (0.2, 0.07), self.app.quit_game)

        # Create World
        self.input_name = TextInput(app, (0, 0.15), (0.3, 0.05), "World Name")
        self.input_seed = TextInput(app, (0, 0.0), (0.3, 0.05), "Seed (Leave blank for random)")
        self.create_game_mode = 1 # 1 is SURVIVAL
        self.btn_game_mode = Button(app, 'Game Mode: Survival', (0, -0.15), (0.3, 0.05), self.toggle_game_mode)
        self.btn_create = Button(app, 'Create New World', (0, -0.3), (0.3, 0.07), self.create_world)
        self.btn_back_create = Button(app, 'Back', (0, -0.5), (0.2, 0.07), lambda: self.set_state('SELECT_WORLD'))
        
        # Select World (will be populated dynamically)
        self.btn_new_world = Button(app, 'Create New World', (0, 0.32), (0.3, 0.07), lambda: self.set_state('CREATE_WORLD'))
        self.btn_back_select = Button(app, 'Back', (0, -0.65), (0.2, 0.07), lambda: self.set_state('MAIN'))

    def open_options(self):
        self.app.options_menu.previous_state = 'MAIN_MENU'
        self.app.game_state = 'OPTIONS'

    def toggle_game_mode(self):
        self.create_game_mode = 0 if self.create_game_mode == 1 else 1
        mode_text = "Survival" if self.create_game_mode == 1 else "Creative"
        self.btn_game_mode.text = f"Game Mode: {mode_text}"

    def set_state(self, new_state):
        self.state = new_state
        if new_state == 'SELECT_WORLD':
            self.load_world_list()
        elif new_state == 'CREATE_WORLD':
            self.input_name.text = ""
            self.input_seed.text = ""
            self.input_name.is_active = True
            self.create_game_mode = 1
            self.btn_game_mode.text = 'Game Mode: Survival'

    def load_world_list(self):
        import os
        import sqlite3
        for btn in self.world_buttons:
            if hasattr(btn, 'thumb_tex'):
                btn.thumb_tex.release() # Safely release old image memory
        self.world_buttons = []
        self.delete_buttons = []
        self.scroll_offset = 0.0
        os.makedirs('saves', exist_ok=True)
        # Sort by modification time (most recent first)
        saves = sorted([f for f in os.listdir('saves') if f.endswith('.db')], 
                       key=lambda x: os.path.getmtime(os.path.join('saves', x)), 
                       reverse=True)
        
        y_offset = 0.05
        for save_file in saves: # Load all worlds dynamically
            save_name = save_file[:-3]
            display_name, seed, game_mode, creation_date, last_played = save_name, 0, 1, "Unknown", "Unknown"
            try:
                conn = sqlite3.connect(f'saves/{save_file}')
                cursor = conn.cursor()
                cursor.execute('SELECT world_name, seed, game_mode, creation_date, last_played FROM world_meta WHERE id=1')
                row = cursor.fetchone()
                if row:
                    display_name = row[0]
                    seed = row[1]
                    game_mode = row[2]
                    creation_date = row[3][:16].replace('T', ' ') if row[3] else "Unknown"
                    last_played = row[4][:16].replace('T', ' ') if row[4] else "Unknown"
                conn.close()
            except:
                pass
            
            btn = WorldButton(self.app, save_name, display_name, seed, game_mode, creation_date, last_played, 
                              (0, y_offset), (0.65, 0.12), lambda sn=save_name: self.app.init_game_session(sn))
            self.world_buttons.append(btn)
            
            # Create a small red 'X' button positioned right next to the WorldButton
            del_btn = Button(self.app, 'X', (0.55, y_offset), (0.05, 0.08), lambda sn=save_name: self.delete_world(sn))
            del_btn.base_color = (0.4, 0.1, 0.1, 0.7)
            del_btn.hover_color = (0.8, 0.1, 0.1, 0.9)
            self.delete_buttons.append(del_btn)
            
            y_offset -= 0.26

    def delete_world(self, save_name):
        import os
        try:
            if os.path.exists(f'saves/{save_name}.db'):
                os.remove(f'saves/{save_name}.db')
            if os.path.exists(f'saves/{save_name}_thumb.png'):
                os.remove(f'saves/{save_name}_thumb.png')
        except Exception as e:
            print(f"[SYSTEM] Failed to delete world: {e}")
        self.load_world_list() # Refresh the UI list instantly!

    def create_world(self):
        name = self.input_name.text.strip()
        if not name:
            name = "New_World"
            
        base_save_name = name.replace(" ", "_")
        save_name = base_save_name
        
        import os
        counter = 1
        while os.path.exists(f'saves/{save_name}.db'):
            save_name = f"{base_save_name}_{counter}"
            counter += 1

        seed_str = self.input_seed.text.strip()
        if not seed_str:
            import random
            seed = random.randint(100000, 999999999)
        else:
            try:
                seed = int(seed_str)
            except ValueError:
                # Convert letters into an exact numerical seed!
                import hashlib
                seed = int(hashlib.md5(seed_str.encode()).hexdigest(), 16) % (10**9)
                
        self.app.init_game_session(save_name, seed, self.create_game_mode)

    def update(self):
        mouse_pos = pg.mouse.get_pos()
        if self.state == 'MAIN':
            for btn in [self.btn_play, self.btn_options, self.btn_quit]:
                btn.check_hover(mouse_pos)
        elif self.state == 'SELECT_WORLD':
            self.btn_new_world.check_hover(mouse_pos)
            self.btn_back_select.check_hover(mouse_pos)
            
            # Apply the scroll offset and disable hover interactions if the button goes out of bounds
            base_y = 0.05
            for i, (btn, del_btn) in enumerate(zip(self.world_buttons, self.delete_buttons)):
                new_y = base_y - i * 0.26 + self.scroll_offset
                btn.pos = (0, new_y)
                del_btn.pos = (0.55, new_y)
                if -0.45 < new_y < 0.12:
                    btn.check_hover(mouse_pos)
                    del_btn.check_hover(mouse_pos)
                else:
                    btn.is_hovered = False
                    del_btn.is_hovered = False
        elif self.state == 'CREATE_WORLD':
            self.btn_game_mode.check_hover(mouse_pos)
            self.btn_create.check_hover(mouse_pos)
            self.btn_back_create.check_hover(mouse_pos)

    def handle_event(self, event):
        if self.state == 'CREATE_WORLD':
            self.input_name.handle_event(event)
            self.input_seed.handle_event(event)
            
        if event.type == pg.MOUSEBUTTONDOWN:
            if event.button == 1:
                if self.state == 'MAIN':
                    for btn in [self.btn_play, self.btn_options, self.btn_quit]:
                        if btn.is_hovered:
                            btn.action()
                            break
                elif self.state == 'SELECT_WORLD':
                    if self.btn_new_world.is_hovered:
                        self.btn_new_world.action()
                    elif self.btn_back_select.is_hovered:
                        self.btn_back_select.action()
                    else:
                        for btn, del_btn in zip(self.world_buttons, self.delete_buttons):
                            if -0.45 < btn.pos[1] < 0.12:
                                if del_btn.is_hovered:
                                    del_btn.action()
                                    break
                                elif btn.is_hovered:
                                    btn.action()
                                    break
                elif self.state == 'CREATE_WORLD':
                    if self.btn_game_mode.is_hovered:
                        self.btn_game_mode.action()
                    elif self.btn_create.is_hovered:
                        self.btn_create.action()
                    elif self.btn_back_create.is_hovered:
                        self.btn_back_create.action()
            elif self.state == 'SELECT_WORLD':
                if event.button == 4: # Mouse Wheel Scroll Up
                    self.scroll_offset = max(0.0, self.scroll_offset - 0.26)
                elif event.button == 5: # Mouse Wheel Scroll Down
                    max_scroll = max(0.0, (len(self.world_buttons) - 2) * 0.26)
                    self.scroll_offset = min(max_scroll, self.scroll_offset + 0.26)

    def render(self):
        # Render title
        self.title_tex.use(location=4)
        
        tex_w, tex_h = self.title_tex.size
        scale_y = 0.15
        scale_x = scale_y * (tex_w / tex_h) / ASPECT_RATIO
        
        self.title_mesh.program['u_scale'] = (scale_x, scale_y)
        self.title_mesh.program['u_offset'] = (0.0, 0.5)
        self.title_mesh.render()

        if self.state == 'MAIN':
            for btn in [self.btn_play, self.btn_options, self.btn_quit]:
                btn.render()
        elif self.state == 'SELECT_WORLD':
            self.btn_new_world.render()
            for btn, del_btn in zip(self.world_buttons, self.delete_buttons):
                if -0.45 < btn.pos[1] < 0.12:
                    btn.render()
                    del_btn.render()
            self.btn_back_select.render()
        elif self.state == 'CREATE_WORLD':
            self.input_name.render()
            self.input_seed.render()
            self.btn_game_mode.render()
            self.btn_create.render()
            self.btn_back_create.render()


class PauseMenu:
    def __init__(self, app):
        self.app = app
        self.title_renderer = TextRenderer(app)
        self.title_renderer.font = pg.font.SysFont('arial', FONT_SIZE_PAUSED, bold=True)
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


class OptionsMenu:
    def __init__(self, app):
        self.app = app
        self.title_renderer = TextRenderer(app)
        self.title_renderer.font = pg.font.SysFont('arial', FONT_SIZE_PAUSED, bold=True)
        self.title_mesh = UITextMesh(app)
        self.bg_mesh = UIColorMesh(app)

        self.sliders = [
            Slider(app, 'FOV', (0, 0.2), (0.3, 0.05), 30, 110, 'fov', self.update_fov, is_int=True),
            Slider(app, 'Sensitivity', (0, 0.0), (0.3, 0.05), 0.0005, 0.005, 'sensitivity'),
            Slider(app, 'Volume', (0, -0.2), (0.3, 0.05), 0, 100, 'volume', self.update_volume, is_int=True),
            Slider(app, 'Render Distance', (0, -0.4), (0.3, 0.05), 2, 14, 'render_distance', is_int=True)
        ]
        self.buttons = [
            Button(app, '', (0, -0.6), (0.3, 0.05), self.toggle_tint),
            Button(app, 'Back', (0, -0.8), (0.2, 0.07), self.go_back)
        ]
        self.previous_state = 'MAIN_MENU'

    def update_fov(self, val):
        if self.app.scene:
            self.app.player.fov = glm.radians(val)

    def update_volume(self, val):
        pg.mixer.music.set_volume(val / 100.0)

    def toggle_tint(self):
        current_val = self.app.config.get('underwater_tint', False)
        self.app.config['underwater_tint'] = not current_val
        self.app.save_config()

    def go_back(self):
        self.app.save_config()
        self.app.game_state = self.previous_state

    def update(self):
        for slider in self.sliders:
            slider.update()

        tint_on = self.app.config.get('underwater_tint', False)
        self.buttons[0].text = f"Underwater Tint: {'On' if tint_on else 'Off'}"

        mouse_pos = pg.mouse.get_pos()
        for button in self.buttons:
            button.check_hover(mouse_pos)

    def handle_event(self, event):
        for slider in self.sliders:
            slider.handle_event(event)
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            for button in self.buttons:
                if button.is_hovered:
                    button.action()
                    break

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
        for button in self.buttons:
            button.render()

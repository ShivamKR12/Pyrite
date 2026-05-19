from settings import *
import pygame as pg
import moderngl as mgl
from pyglm import glm
from .components import Button, WorldButton, TextInput, Slider
from .meshes import UIColorMesh, UITextMesh
from .text import TextRenderer


class Menu:
    """
    Manages the Main Menu, World Selection, and World Creation screens.
    Handles smooth state transitions, dynamic world list loading from the 
    SQLite saves directory, and interaction events.
    """
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

        try:
            bg_img = pg.image.load(get_path('assets/background.jpg')).convert_alpha()
            self.bg_tex = self.app.ctx.texture(bg_img.get_size(), 4, pg.image.tobytes(bg_img, 'RGBA', True))
            self.bg_tex.filter = (mgl.LINEAR, mgl.LINEAR)
            self.bg_tex_mesh = UITextMesh(app)
        except Exception as e:
            print(f"Failed to load background: {e}")
            self.bg_tex = None

        self.state = 'MAIN'
        self.transition_state = 'IN' # 'IN', 'OUT', 'IDLE'
        self.transition_progress = 0.0
        self.pending_action = None
        self.anim_dir = 1
        self.world_buttons = []
        self.delete_buttons = []
        self.scroll_offset = 0.0

        # Main Menu
        self.btn_play = Button(app, 'Play', (0, 0.15), (0.2, 0.07), lambda: self.trigger_action(lambda: self.set_state('SELECT_WORLD'), -1))
        self.btn_options = Button(app, 'Options', (0, 0.0), (0.2, 0.07), lambda: self.trigger_action(self.open_options, 1))
        self.btn_quit = Button(app, 'Quit', (0, -0.15), (0.2, 0.07), lambda: self.trigger_action(self.app.quit_game, 1))

        # Create World
        self.input_name = TextInput(app, (0, 0.15), (0.3, 0.05), "World Name")
        self.input_seed = TextInput(app, (0, 0.0), (0.3, 0.05), "Seed (Leave blank for random)")
        self.create_game_mode = 1 # 1 is SURVIVAL
        self.btn_game_mode = Button(app, 'Game Mode: Survival', (0, -0.15), (0.3, 0.05), self.toggle_game_mode)
        self.btn_create = Button(app, 'Create New World', (0, -0.3), (0.3, 0.07), lambda: self.trigger_action(self.create_world, 1))
        self.btn_back_create = Button(app, 'Back', (0, -0.5), (0.2, 0.07), lambda: self.trigger_action(lambda: self.set_state('SELECT_WORLD'), 1))
        
        # Select World (will be populated dynamically)
        self.btn_new_world = Button(app, 'Create New World', (0, 0.22), (0.3, 0.07), lambda: self.trigger_action(lambda: self.set_state('CREATE_WORLD'), -1))
        self.btn_back_select = Button(app, 'Back', (0, -0.65), (0.2, 0.07), lambda: self.trigger_action(lambda: self.set_state('MAIN'), 1))

    def trigger_action(self, action, anim_dir=1):
        if self.transition_state in ('IDLE', 'IN'):
            self.pending_action = action
            self.transition_state = 'OUT'
            self.transition_progress = 0.0
            self.anim_dir = anim_dir

    def open_options(self):
        self.app.options_menu.previous_state = 'MAIN_MENU'
        self.app.game_state = 'OPTIONS'
        self.app.options_menu.transition_state = 'IN'
        self.app.options_menu.transition_progress = 0.0

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
        self.transition_state = 'IN'
        self.transition_progress = 0.0

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
        
        y_offset = -0.05
        for save_file in saves: # Load all worlds dynamically
            save_name = save_file[:-3]
            display_name, seed, game_mode, creation_date, last_played = save_name, 0, 1, "Unknown", "Unknown"
            try:
                connection = sqlite3.connect(f'saves/{save_file}')
                cursor = connection.cursor()
                cursor.execute('SELECT world_name, seed, game_mode, creation_date, last_played FROM world_meta WHERE id=1')
                row = cursor.fetchone()
                if row:
                    display_name = row[0]
                    seed = row[1]
                    game_mode = row[2]
                    creation_date = row[3][:16].replace('T', ' ') if row[3] else "Unknown"
                    last_played = row[4][:16].replace('T', ' ') if row[4] else "Unknown"
                connection.close()
            except:
                pass
            
            def load_and_reset(sn=save_name):
                self.app.init_game_session(sn)
                self.set_state('MAIN')
            
            btn = WorldButton(self.app, save_name, display_name, seed, game_mode, creation_date, last_played, 
                              (0, y_offset), (0.65, 0.12), lambda sn=save_name: self.trigger_action(lambda: load_and_reset(sn), -1))
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
        self.set_state('MAIN')

    def update(self):
        if self.transition_state != 'IDLE':
            self.transition_progress += self.app.delta_time * 0.005 # ~200ms transitions
            if self.transition_progress >= 1.0:
                self.transition_progress = 1.0
                if self.transition_state == 'OUT':
                    if self.pending_action:
                        action = self.pending_action
                        self.pending_action = None
                        action()
                    else:
                        self.transition_state = 'IDLE'
                elif self.transition_state == 'IN':
                    self.transition_state = 'IDLE'

        if self.transition_state != 'IDLE':
            mouse_pos = (-999, -999) # Lock interactions during animations
        else:
            mouse_pos = pg.mouse.get_pos()
            
        if self.state == 'MAIN':
            for btn in [self.btn_play, self.btn_options, self.btn_quit]:
                btn.check_hover(mouse_pos)
        elif self.state == 'SELECT_WORLD':
            self.btn_new_world.check_hover(mouse_pos)
            self.btn_back_select.check_hover(mouse_pos)
            
            # Apply the scroll offset and disable hover interactions if the button goes out of bounds
            base_y = -0.05
            for i, (btn, del_btn) in enumerate(zip(self.world_buttons, self.delete_buttons)):
                new_y = base_y - i * 0.26 + self.scroll_offset
                btn.pos = (0, new_y)
                del_btn.pos = (0.55, new_y)
                if -0.45 < new_y < 0.02:
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
        if self.transition_state != 'IDLE': return # Ignore inputs during transitions

        if self.state == 'CREATE_WORLD':
            self.input_name.handle_event(event)
            self.input_seed.handle_event(event)
            self.btn_game_mode.handle_event(event)
            self.btn_create.handle_event(event)
            self.btn_back_create.handle_event(event)

        elif self.state == 'MAIN':
            for btn in [self.btn_play, self.btn_options, self.btn_quit]:
                btn.handle_event(event)
    
        elif self.state == 'SELECT_WORLD':
            self.btn_new_world.handle_event(event)
            self.btn_back_select.handle_event(event)

            for btn, del_btn in zip(self.world_buttons, self.delete_buttons):
                if -0.45 < btn.pos[1] < 0.02:
                    btn.handle_event(event)
                    del_btn.handle_event(event)

            if event.type == pg.MOUSEBUTTONDOWN:
                if event.button == 4: # Mouse Wheel Scroll Up
                    self.scroll_offset = max(0.0, self.scroll_offset - 0.26)

                elif event.button == 5: # Mouse Wheel Scroll Down
                    max_scroll = max(0.0, (len(self.world_buttons) - 2) * 0.26)
                    self.scroll_offset = min(max_scroll, self.scroll_offset + 0.26)        

    def render_bg(self):
        if hasattr(self, 'bg_tex') and self.bg_tex:
            self.bg_tex.use(location=4)
            img_aspect = self.bg_tex.width / self.bg_tex.height
            if img_aspect > ASPECT_RATIO:
                scale_x, scale_y = img_aspect / ASPECT_RATIO, 1.0
            else:
                scale_x, scale_y = 1.0, ASPECT_RATIO / img_aspect
            self.bg_tex_mesh.program['u_scale'] = (scale_x, scale_y)
            self.bg_tex_mesh.program['u_offset'] = (0.0, 0.0)
            if 'u_alpha' in self.bg_tex_mesh.program: self.bg_tex_mesh.program['u_alpha'] = 1.0
            self.bg_tex_mesh.render()

    def render(self):
        t = self.transition_progress
        ease = 1.0 - (1.0 - t) ** 3
        offset_y = 0.0
        alpha = 1.0
        
        if self.transition_state == 'IN':
            offset_y = (1.0 - ease) * -0.5 * self.anim_dir
            alpha = ease
        elif self.transition_state == 'OUT':
            offset_y = ease * 0.5 * self.anim_dir
            alpha = 1.0 - ease
            
        offset = (0.0, offset_y)
        
        self.render_bg()

        # Render title
        self.title_tex.use(location=4)
        
        tex_w, tex_h = self.title_tex.size
        scale_y = 0.15
        scale_x = scale_y * (tex_w / tex_h) / ASPECT_RATIO
        
        self.title_mesh.program['u_scale'] = (scale_x, scale_y)
        self.title_mesh.program['u_offset'] = (0.0, 0.5 + offset_y * 0.5) # Parallax!
        if 'u_alpha' in self.title_mesh.program: self.title_mesh.program['u_alpha'] = alpha
        self.title_mesh.render()
        if 'u_alpha' in self.title_mesh.program: self.title_mesh.program['u_alpha'] = 1.0

        if self.state == 'MAIN':
            for btn in [self.btn_play, self.btn_options, self.btn_quit]:
                btn.render(offset, alpha)
        elif self.state == 'SELECT_WORLD':
            self.btn_new_world.render(offset, alpha)
            for btn, del_btn in zip(self.world_buttons, self.delete_buttons):
                if -0.45 < btn.pos[1] < 0.02:
                    btn.render(offset, alpha)
                    del_btn.render(offset, alpha)
            self.btn_back_select.render(offset, alpha)
        elif self.state == 'CREATE_WORLD':
            self.input_name.render(offset, alpha)
            self.input_seed.render(offset, alpha)
            self.btn_game_mode.render(offset, alpha)
            self.btn_create.render(offset, alpha)
            self.btn_back_create.render(offset, alpha)


class PauseMenu:
    """
    Provides the in-game pause screen overlay.
    Allows the player to resume the game, open options, or quit back to the Main Menu.
    """
    def __init__(self, app):
        self.app = app
        self.title_renderer = TextRenderer(app)
        self.title_renderer.font = pg.font.SysFont('arial', FONT_SIZE_PAUSED, bold=True)
        self.title_mesh = UITextMesh(app)
        self.bg_mesh = UIColorMesh(app)

        self.transition_state = 'IN'
        self.transition_progress = 0.0
        self.pending_action = None
        self.anim_dir = 1

        self.buttons = [
            Button(app, 'Resume', (0, 0.15), (0.3, 0.07), lambda: self.trigger_action(self.resume_game, -1)),
            Button(app, 'Options', (0, 0.0), (0.3, 0.07), lambda: self.trigger_action(self.open_options, 1)),
            Button(app, 'Quit to Menu', (0, -0.15), (0.3, 0.07), lambda: self.trigger_action(self.quit_to_menu, 1))
        ]

    def trigger_action(self, action, anim_dir=1):
        if self.transition_state in ('IDLE', 'IN'):
            self.pending_action = action
            self.transition_state = 'OUT'
            self.transition_progress = 0.0
            self.anim_dir = anim_dir

    def open_options(self):
        self.app.options_menu.previous_state = 'PAUSED'
        self.app.game_state = 'OPTIONS'
        self.app.options_menu.transition_state = 'IN'
        self.app.options_menu.transition_progress = 0.0

    def resume_game(self):
        self.app.game_state = 'IN_GAME'
        pg.event.set_grab(True)
        pg.mouse.set_visible(False)

    def quit_to_menu(self):
        self.app.game_state = 'MAIN_MENU'
        self.app.menu.state = 'MAIN'
        if self.app.scene:
            self.app.scene.world.save()
            self.app.scene = None # Unload the world to free memory

    def update(self):
        if self.transition_state != 'IDLE':
            self.transition_progress += self.app.delta_time * 0.005
            if self.transition_progress >= 1.0:
                self.transition_progress = 1.0
                if self.transition_state == 'OUT':
                    if self.pending_action:
                        action = self.pending_action
                        self.pending_action = None
                        action()
                    else:
                        self.transition_state = 'IDLE'
                elif self.transition_state == 'IN':
                    self.transition_state = 'IDLE'
                    
        if self.transition_state != 'IDLE':
            mouse_pos = (-999, -999)
        else:
            mouse_pos = pg.mouse.get_pos()
            
        for button in self.buttons:
            button.check_hover(mouse_pos)

    def handle_event(self, event):
        if self.transition_state != 'IDLE': return
        for button in self.buttons:
            button.handle_event(event)

    def render(self):
        t = self.transition_progress
        ease = 1.0 - (1.0 - t) ** 3
        offset_y = 0.0
        alpha = 1.0
        
        if self.transition_state == 'IN':
            offset_y = (1.0 - ease) * -0.5 * self.anim_dir
            alpha = ease
        elif self.transition_state == 'OUT':
            offset_y = ease * 0.5 * self.anim_dir
            alpha = 1.0 - ease
            
        offset = (0.0, offset_y)
        bg_alpha = alpha if self.transition_state != 'IDLE' else 1.0
        
        self.bg_mesh.program['u_scale'] = (1.0, 1.0)
        self.bg_mesh.program['u_offset'] = (0.0, 0.0)
        self.bg_mesh.program['u_color'] = (0.0, 0.0, 0.0, 0.6 * bg_alpha)
        self.bg_mesh.render()

        tex = self.title_renderer.get_texture("Game Paused")
        tex.use(location=4)
        tex_w, tex_h = tex.size
        scale_y = 0.08
        scale_x = scale_y * (tex_w / tex_h) / ASPECT_RATIO
        self.title_mesh.program['u_scale'] = (scale_x, scale_y)
        self.title_mesh.program['u_offset'] = (0.0, 0.4 + offset_y * 0.5)
        if 'u_alpha' in self.title_mesh.program: self.title_mesh.program['u_alpha'] = alpha
        self.title_mesh.render()
        if 'u_alpha' in self.title_mesh.program: self.title_mesh.program['u_alpha'] = 1.0

        for button in self.buttons:
            button.render(offset, alpha)


class OptionsMenu:
    """
    Manages the game settings screen.
    Provides sliders and toggles for FOV, Mouse Sensitivity, Volume, Render Distance, 
    and Visual Tints. Handles serializing these settings to config.json.
    """
    def __init__(self, app):
        self.app = app
        self.title_renderer = TextRenderer(app)
        self.title_renderer.font = pg.font.SysFont('arial', FONT_SIZE_PAUSED, bold=True)
        self.title_mesh = UITextMesh(app)
        self.bg_mesh = UIColorMesh(app)

        self.transition_state = 'IN'
        self.transition_progress = 0.0
        self.pending_action = None
        self.anim_dir = 1

        self.sliders = [
            Slider(app, 'FOV', (0, 0.3), (0.3, 0.05), 30, 110, 'fov', self.update_fov, is_int=True),
            Slider(app, 'Sensitivity', (0, 0.1), (0.3, 0.05), 0.0005, 0.005, 'sensitivity'),
            Slider(app, 'Volume', (0, -0.1), (0.3, 0.05), 0, 100, 'volume', self.update_volume, is_int=True),
            Slider(app, 'Render Distance', (0, -0.3), (0.3, 0.05), 2, 14, 'render_distance', is_int=True)
        ]
        self.buttons = [
            Button(app, '', (0, -0.5), (0.3, 0.05), self.toggle_tint),
            Button(app, 'Back', (0, -0.7), (0.2, 0.07), lambda: self.trigger_action(self.go_back, 1))
        ]
        self.previous_state = 'MAIN_MENU'

    def trigger_action(self, action, anim_dir=1):
        if self.transition_state in ('IDLE', 'IN'):
            self.pending_action = action
            self.transition_state = 'OUT'
            self.transition_progress = 0.0
            self.anim_dir = anim_dir

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
        if self.previous_state == 'MAIN_MENU':
            self.app.menu.transition_state = 'IN'
            self.app.menu.transition_progress = 0.0
        elif self.previous_state == 'PAUSED':
            self.app.pause_menu.transition_state = 'IN'
            self.app.pause_menu.transition_progress = 0.0

    def update(self):
        if self.transition_state != 'IDLE':
            self.transition_progress += self.app.delta_time * 0.005
            if self.transition_progress >= 1.0:
                self.transition_progress = 1.0
                if self.transition_state == 'OUT':
                    if self.pending_action:
                        action = self.pending_action
                        self.pending_action = None
                        action()
                    else:
                        self.transition_state = 'IDLE'
                elif self.transition_state == 'IN':
                    self.transition_state = 'IDLE'
                    
        if self.transition_state != 'IDLE':
            mouse_pos = (-999, -999)
        else:
            mouse_pos = pg.mouse.get_pos()
            
        for slider in self.sliders:
            slider.update(mouse_pos)

        tint_on = self.app.config.get('underwater_tint', False)
        self.buttons[0].text = f"Underwater Tint: {'On' if tint_on else 'Off'}"

        for button in self.buttons:
            button.check_hover(mouse_pos)

    def handle_event(self, event):
        if self.transition_state != 'IDLE': return
        for slider in self.sliders:
            slider.handle_event(event)
        for button in self.buttons:
            button.handle_event(event)

    def render(self):
        t = self.transition_progress
        ease = 1.0 - (1.0 - t) ** 3
        offset_y = 0.0
        alpha = 1.0
        
        if self.transition_state == 'IN':
            offset_y = (1.0 - ease) * -0.5 * self.anim_dir
            alpha = ease
        elif self.transition_state == 'OUT':
            offset_y = ease * 0.5 * self.anim_dir
            alpha = 1.0 - ease
            
        offset = (0.0, offset_y)
        bg_alpha = alpha if self.transition_state != 'IDLE' else 1.0
        
        if self.previous_state == 'PAUSED':
            self.bg_mesh.program['u_scale'] = (1.0, 1.0)
            self.bg_mesh.program['u_offset'] = (0.0, 0.0)
            self.bg_mesh.program['u_color'] = (0.0, 0.0, 0.0, 0.8 * bg_alpha)
            self.bg_mesh.render()

        tex = self.title_renderer.get_texture("Options")
        tex.use(location=4)
        tex_w, tex_h = tex.size
        scale_y = 0.08
        scale_x = scale_y * (tex_w / tex_h) / ASPECT_RATIO
        self.title_mesh.program['u_scale'] = (scale_x, scale_y)
        self.title_mesh.program['u_offset'] = (0.0, 0.55 + offset_y * 0.5)
        if 'u_alpha' in self.title_mesh.program: self.title_mesh.program['u_alpha'] = alpha
        self.title_mesh.render()
        if 'u_alpha' in self.title_mesh.program: self.title_mesh.program['u_alpha'] = 1.0

        for slider in self.sliders:
            slider.render(offset, alpha)
        for button in self.buttons:
            button.render(offset, alpha)

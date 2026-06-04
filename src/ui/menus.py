"""
UI Menu systems: Main Menu, Pause Menu, and Options Menu.

This module manages the interactive overlays and state machines for the 
game's user interfaces. It handles dynamic world saving/loading screens, 
configuration binding for settings, and smooth animated transitions between states.
"""

import pygame as pg
import moderngl as mgl
from pyglm import glm
import sqlite3
import random
import hashlib
import os
from typing import Any, Callable, List, Optional, Tuple

from .components import Button, WorldButton, TextInput, Slider, Toggle, VBox, UINode
from .meshes import UIColorMesh, UITextMesh
from .text import TextRenderer
from profiler import global_profiler
from settings import ASPECT_RATIO, FONT_SIZE_TITLE, FONT_SIZE_PAUSED, get_path


class MainMenu:
    """
    Manages the Main Menu, World Selection, and World Creation screens.
    
    Handles smooth state transitions, dynamic world list loading from the 
    SQLite saves directory, and interaction events.
    
    Args:
        app (Any): The main application context.
    """
    @global_profiler.profile_func("MainMenu_Init")
    def __init__(self, app: Any) -> None:
        self.app: Any = app
        self.title_renderer: Any = TextRenderer(app)
        self.title_renderer.font = pg.font.SysFont('arial', FONT_SIZE_TITLE, bold=True)
        self.title_mesh: Any = UITextMesh(app)

        try:
            img: pg.Surface = pg.image.load(get_path('assets/textures/uis/pyrite-logo.png')).convert_alpha()
            self.title_tex: Any = self.app.ctx.texture(img.get_size(), 4, pg.image.tobytes(img, 'RGBA', True))
            self.title_tex.build_mipmaps()
            self.title_tex.filter = (mgl.LINEAR_MIPMAP_LINEAR, mgl.LINEAR)
        except Exception:
            self.title_tex = self.title_renderer.get_texture("Pyrite")

        try:
            bg_img: pg.Surface = pg.image.load(get_path('assets/textures/uis/background.jpg')).convert_alpha()
            self.bg_tex: Any = self.app.ctx.texture(bg_img.get_size(), 4, pg.image.tobytes(bg_img, 'RGBA', True))
            self.bg_tex.filter = (mgl.LINEAR, mgl.LINEAR)
            self.bg_tex_mesh: Any = UITextMesh(app)
        except Exception as e:
            print(f"Failed to load background: {e}")
            self.bg_tex = None

        self.state: str = 'MAIN'
        self.transition_state: str = 'IN' # 'IN', 'OUT', 'IDLE'
        self.transition_progress: float = 0.0
        self.pending_action: Optional[Callable[[], None]] = None
        self.anim_dir: int = 1
        self.world_buttons: List[Any] = []
        self.delete_buttons: List[Any] = []
        self.scroll_offset: float = 0.0
        self.target_scroll_offset: float = 0.0

        # Main Menu
        self.layout_main: Any = VBox(pos=(0, 0.15), spacing=0.1)
        self.layout_main.add_child(Button(app, 'Play', (0, 0), (0.2, 0.07), lambda: self.trigger_action(lambda: self.set_state('SELECT_WORLD'), -1)))
        self.layout_main.add_child(Button(app, 'Options', (0, 0), (0.2, 0.07), lambda: self.trigger_action(self.open_options, 1)))
        self.layout_main.add_child(Button(app, 'Quit', (0, 0), (0.2, 0.07), lambda: self.trigger_action(self.app.quit_game, 1)))
        self.layout_main.update_layout()

        # Create World
        self.create_game_mode: int = 1 # 1 is SURVIVAL
        self.layout_create: Any = VBox(pos=(0, 0.25), spacing=0.2) # Master container gap
        
        config_group: Any = self.layout_create.add_child(VBox(spacing=0.1)) # Tight grouping for inputs!
        self.input_name: Any = config_group.add_child(TextInput(app, (0, 0), (0.3, 0.05), "World Name"))
        self.input_seed: Any = config_group.add_child(TextInput(app, (0, 0), (0.3, 0.05), "Seed (Leave blank for random)"))
        self.btn_game_mode: Any = config_group.add_child(Button(app, 'Game Mode: Survival', (0, 0), (0.3, 0.05), self.toggle_game_mode))
        
        action_group: Any = self.layout_create.add_child(VBox(spacing=0.1)) # Normal spacing for buttons
        self.btn_create: Any = action_group.add_child(Button(app, 'Create New World', (0, 0), (0.3, 0.07), lambda: self.trigger_action(self.create_world, 1)))
        self.btn_back_create: Any = action_group.add_child(Button(app, 'Back', (0, 0), (0.2, 0.07), lambda: self.trigger_action(lambda: self.set_state('SELECT_WORLD'), 1)))
        self.layout_create.update_layout()
        
        # Select World (will be populated dynamically)
        self.btn_new_world: Any = Button(app, 'Create New World', (0, 0.22), (0.3, 0.07), lambda: self.trigger_action(lambda: self.set_state('CREATE_WORLD'), -1))
        self.btn_back_select: Any = Button(app, 'Back', (0, -0.65), (0.2, 0.07), lambda: self.trigger_action(lambda: self.set_state('MAIN'), 1))

    @global_profiler.profile_func("MainMenu_TriggerAction")
    def trigger_action(self, action: Callable[[], None], anim_dir: int = 1) -> None:
        """Initiates a smooth animation transition before executing a state-change callback."""
        if self.transition_state in ('IDLE', 'IN'):
            self.pending_action = action
            self.transition_state = 'OUT'
            self.transition_progress = 0.0
            self.anim_dir = anim_dir

    @global_profiler.profile_func("MainMenu_OpenOptions")
    def open_options(self) -> None:
        """Transitions to the Options Menu overlay."""
        self.app.options_menu.previous_state = 'MAIN_MENU'
        self.app.game_state = 'OPTIONS'
        self.app.options_menu.transition_state = 'IN'
        self.app.options_menu.transition_progress = 0.0

    @global_profiler.profile_func("MainMenu_ToggleGameMode")
    def toggle_game_mode(self) -> None:
        """Toggles the selected creation game mode (Survival/Creative)."""
        self.create_game_mode = 0 if self.create_game_mode == 1 else 1
        mode_text: str = "Survival" if self.create_game_mode == 1 else "Creative"
        self.btn_game_mode.text = f"Game Mode: {mode_text}"
        self.btn_game_mode.text_tex = self.btn_game_mode.text_renderer.get_texture(self.btn_game_mode.text)

    @global_profiler.profile_func("MainMenu_SetState")
    def set_state(self, new_state: str) -> None:
        """Switches the active Main Menu context and resets dynamic UI elements."""
        self.state = new_state
        
        if new_state == 'SELECT_WORLD':
            self.load_world_list()
        
        elif new_state == 'CREATE_WORLD':
            self.input_name.text = ""
            self.input_seed.text = ""
            self.input_name.is_active = True
            self.create_game_mode = 1
            self.btn_game_mode.text = 'Game Mode: Survival'
            self.btn_game_mode.text_tex = self.btn_game_mode.text_renderer.get_texture(self.btn_game_mode.text)
        
        self.transition_state = 'IN'
        self.transition_progress = 0.0

    @global_profiler.profile_func("MainMenu_LoadWorldList")
    def load_world_list(self) -> None:
        """Queries the local `saves` directory and generates buttons for all existing databases."""
        for btn in self.world_buttons:
            if hasattr(btn, 'thumb_tex'):
                btn.thumb_tex.release()
                btn.tex_title.release()
                btn.tex_details.release()
                btn.tex_dates.release()
        
        self.world_buttons = []
        self.delete_buttons = []
        self.scroll_offset = 0.0
        self.target_scroll_offset = 0.0
        
        os.makedirs('saves', exist_ok=True)
        # Sort by modification time (most recent first)
        saves: List[str] = sorted([f for f in os.listdir('saves') if f.endswith('.db')], 
                                  key=lambda x: os.path.getmtime(os.path.join('saves', x)), 
                                  reverse=True)
        
        y_offset: float = -0.05
        for save_file in saves: # Load all worlds dynamically
            save_name: str = save_file[:-3]
            display_name: str = save_name
            seed: int = 0
            game_mode: int = 1
            creation_date: str = "Unknown"
            last_played: str = "Unknown"
            
            try:
                connection: sqlite3.Connection = sqlite3.connect(f'saves/{save_file}')
                cursor: sqlite3.Cursor = connection.cursor()
                cursor.execute('SELECT world_name, seed, game_mode, creation_date, last_played FROM world_meta WHERE id=1')
                row: Any = cursor.fetchone()
                
                if row:
                    display_name = row[0]
                    seed = row[1]
                    game_mode = row[2]
                    creation_date = row[3][:16].replace('T', ' ') if row[3] else "Unknown"
                    last_played = row[4][:16].replace('T', ' ') if row[4] else "Unknown"
                
                connection.close()
            
            except:
                pass
            
            def load_and_reset(sn: str = save_name) -> None:
                self.app.init_game_session(sn)
                self.set_state('MAIN')
            
            btn: Any = WorldButton(self.app, save_name, display_name, seed, game_mode, creation_date, last_played, 
                              (0, y_offset), (0.65, 0.12), lambda sn=save_name: self.trigger_action(lambda: load_and_reset(sn), -1))
            self.world_buttons.append(btn)
            
            # Create a small red 'X' button positioned right next to the WorldButton
            del_btn: Any = Button(self.app, 'X', (0.55, y_offset), (0.05, 0.08), lambda sn=save_name: self.delete_world(sn))
            del_btn.base_color = (0.4, 0.1, 0.1, 0.7)
            del_btn.hover_color = (0.8, 0.1, 0.1, 0.9)
            self.delete_buttons.append(del_btn)
            
            y_offset -= 0.26

    @global_profiler.profile_func("MainMenu_DeleteWorld")
    def delete_world(self, save_name: str) -> None:
        """Deletes a saved world database and its thumbnail from the disk."""
        try:
            if os.path.exists(f'saves/{save_name}.db'):
                os.remove(f'saves/{save_name}.db')
            
            if os.path.exists(f'saves/{save_name}_thumb.png'):
                os.remove(f'saves/{save_name}_thumb.png')
        
        except Exception as e:
            print(f"[SYSTEM] Failed to delete world: {e}")
        
        self.load_world_list() # Refresh the UI list instantly!

    @global_profiler.profile_func("MainMenu_CreateWorld")
    def create_world(self) -> None:
        """Creates a new world database using the parameters from the input fields."""
        name: str = self.input_name.text.strip()
        
        if not name:
            name = "New_World"
            
        base_save_name: str = name.replace(" ", "_")
        save_name: str = base_save_name
        
        counter: int = 1
        while os.path.exists(f'saves/{save_name}.db'):
            save_name = f"{base_save_name}_{counter}"
            counter += 1

        seed_str: str = self.input_seed.text.strip()
        seed: int
        if not seed_str:
            seed = random.randint(100000, 999999999)
        
        else:
            try:
                seed = int(seed_str)
            
            except ValueError:
                # Convert letters into an exact numerical seed!
                seed = int(hashlib.md5(seed_str.encode()).hexdigest(), 16) % (10**9)
                
        self.app.init_game_session(save_name, seed, self.create_game_mode)
        self.set_state('MAIN')

    @global_profiler.profile_func("MainMenu_Update")
    def update(self) -> None:
        """Updates animations, scrolling, and distributes events to active UI components."""
        if self.transition_state != 'IDLE':
            self.transition_progress += self.app.delta_time * 0.005 # ~200ms transitions
            
            if self.transition_progress >= 1.0:
                self.transition_progress = 1.0
                
                if self.transition_state == 'OUT':
                    if self.pending_action:
                        action: Callable[[], None] = self.pending_action
                        self.pending_action = None
                        action()
                    
                    else:
                        self.transition_state = 'IDLE'
                
                elif self.transition_state == 'IN':
                    self.transition_state = 'IDLE'

        if self.transition_state != 'IDLE':
            mouse_pos: Tuple[int, int] = (-999, -999) # Lock interactions during animations
        
        else:
            mouse_pos = pg.mouse.get_pos()
            
        if self.state == 'MAIN':
            self.layout_main.update(mouse_pos)
        
        elif self.state == 'SELECT_WORLD':
            # Smooth scroll interpolation
            if abs(self.target_scroll_offset - self.scroll_offset) > 0.001:
                self.scroll_offset += (self.target_scroll_offset - self.scroll_offset) * min(1.0, 15.0 * self.app.delta_time * 0.001)
            
            else:
                self.scroll_offset = self.target_scroll_offset

            self.btn_new_world.check_hover(mouse_pos)
            self.btn_back_select.check_hover(mouse_pos)
            
            # Apply the scroll offset and disable hover interactions if the button goes out of bounds
            base_y: float = -0.05
            for i, (btn, del_btn) in enumerate(zip(self.world_buttons, self.delete_buttons)):
                new_y: float = base_y - i * 0.26 + self.scroll_offset
                btn.local_pos = [0, new_y]
                del_btn.local_pos = [0.55, new_y]
                
                if -0.45 < new_y < 0.02:
                    btn.check_hover(mouse_pos)
                    del_btn.check_hover(mouse_pos)
                    
                    # Prevent hitbox overlap: If hovering the delete button, ignore the world button underneath!
                    if del_btn.is_hovered:
                        btn.is_hovered = False
                        btn.is_pressed = False
                
                else:
                    btn.is_hovered = False
                    del_btn.is_hovered = False
        
        elif self.state == 'CREATE_WORLD':
            self.layout_create.update(mouse_pos)

    @global_profiler.profile_func("MainMenu_HandleEvent")
    def handle_event(self, event: Any) -> None:
        if self.transition_state != 'IDLE':
            return # Ignore inputs during transitions

        if self.state == 'CREATE_WORLD':
            self.layout_create.handle_event(event)
        
        elif self.state == 'MAIN':
            self.layout_main.handle_event(event)
        
        elif self.state == 'SELECT_WORLD':
            self.btn_new_world.handle_event(event)
            self.btn_back_select.handle_event(event)

            for btn, del_btn in zip(self.world_buttons, self.delete_buttons):
                if -0.45 < btn.local_pos[1] < 0.02:
                    btn.handle_event(event)
                    del_btn.handle_event(event)

            if event.type == pg.MOUSEBUTTONDOWN:
                if event.button == 4: # Mouse Wheel Scroll Up
                    self.target_scroll_offset = max(0.0, self.target_scroll_offset - 0.26)

                elif event.button == 5: # Mouse Wheel Scroll Down
                    max_scroll: float = max(0.0, (len(self.world_buttons) - 2) * 0.26)
                    self.target_scroll_offset = min(max_scroll, self.target_scroll_offset + 0.26)        

    @global_profiler.profile_func("MainMenu_RenderBg")
    def render_bg(self) -> None:
        """Renders the fullscreen background image dynamically scaled to the window aspect ratio."""
        if hasattr(self, 'bg_tex') and self.bg_tex:
            self.bg_tex.use(location=4)
            img_aspect: float = self.bg_tex.width / self.bg_tex.height
            
            if img_aspect > ASPECT_RATIO:
                scale_x, scale_y = img_aspect / ASPECT_RATIO, 1.0
            else:
                scale_x, scale_y = 1.0, ASPECT_RATIO / img_aspect
            
            self.bg_tex_mesh.program['u_scale'] = (scale_x, scale_y)
            self.bg_tex_mesh.program['u_offset'] = (0.0, 0.0)
            
            if 'u_alpha' in self.bg_tex_mesh.program:
                self.bg_tex_mesh.program['u_alpha'] = 1.0
            
            self.bg_tex_mesh.render()

    @global_profiler.profile_func("MainMenu_Render")
    def render(self) -> None:
        """Issues draw calls for the title, current layout, and applies animated transition offsets."""
        t: float = self.transition_progress
        ease: float = 1.0 - (1.0 - t) ** 3
        offset_y: float = 0.0
        alpha: float = 1.0
        
        if self.transition_state == 'IN':
            offset_y = (1.0 - ease) * -0.5 * self.anim_dir
            alpha = ease
        
        elif self.transition_state == 'OUT':
            offset_y = ease * 0.5 * self.anim_dir
            alpha = 1.0 - ease
            
        offset: Tuple[float, float] = (0.0, offset_y)
        
        self.render_bg()

        # Render title
        self.title_tex.use(location=4)
        
        tex_w: int = self.title_tex.size[0]
        tex_h: int = self.title_tex.size[1]
        scale_y: float = 0.15
        scale_x: float = scale_y * (tex_w / tex_h) / ASPECT_RATIO
        
        self.title_mesh.program['u_scale'] = (scale_x, scale_y)
        self.title_mesh.program['u_offset'] = (0.0, 0.5 + offset_y * 0.5) # Parallax!
        
        if 'u_alpha' in self.title_mesh.program:
            self.title_mesh.program['u_alpha'] = alpha
        self.title_mesh.render()
        
        if 'u_alpha' in self.title_mesh.program:
            self.title_mesh.program['u_alpha'] = 1.0

        if self.state == 'MAIN':
            self.layout_main.render(offset, alpha)
        
        elif self.state == 'SELECT_WORLD':
            self.btn_new_world.render(offset, alpha)
            
            # Enable shader clipping area (x_min, y_min, x_max, y_max)
            if 'u_clip' in self.app.shader_program.ui_color:
                self.app.shader_program.ui_color['u_clip'] = (-2.0, -0.55, 2.0, 0.1)
            
            if 'u_clip' in self.app.shader_program.ui_text:
                self.app.shader_program.ui_text['u_clip'] = (-2.0, -0.55, 2.0, 0.1)

            for btn, del_btn in zip(self.world_buttons, self.delete_buttons):
                btn.render(offset, alpha)
                del_btn.render(offset, alpha)
                
            # Reset clipping area
            if 'u_clip' in self.app.shader_program.ui_color:
                self.app.shader_program.ui_color['u_clip'] = (-2.0, -2.0, 2.0, 2.0)
            
            if 'u_clip' in self.app.shader_program.ui_text:
                self.app.shader_program.ui_text['u_clip'] = (-2.0, -2.0, 2.0, 2.0)

            self.btn_back_select.render(offset, alpha)
        
        elif self.state == 'CREATE_WORLD':
            self.layout_create.render(offset, alpha)


class PauseMenu:
    """
    Provides the in-game pause screen overlay.
    
    Allows the player to resume the game, open options, or quit back to the Main Menu.
    
    Args:
        app (Any): The main application context.
    """
    @global_profiler.profile_func("PauseMenu_Init")
    def __init__(self, app: Any) -> None:
        self.app: Any = app
        self.title_renderer: Any = TextRenderer(app)
        self.title_renderer.font = pg.font.SysFont('arial', FONT_SIZE_PAUSED, bold=True)
        self.title_mesh: Any = UITextMesh(app)
        self.title_tex: Any = self.title_renderer.get_texture("Game Paused")
        self.bg_mesh: Any = UIColorMesh(app)

        self.transition_state: str = 'IN'
        self.transition_progress: float = 0.0
        self.pending_action: Optional[Callable[[], None]] = None
        self.anim_dir: int = 1

        self.layout: Any = VBox(pos=(0, 0.15), spacing=0.1)
        self.layout.add_child(Button(app, 'Resume', (0, 0), (0.3, 0.07), lambda: self.trigger_action(self.resume_game, -1)))
        self.layout.add_child(Button(app, 'Options', (0, 0), (0.3, 0.07), lambda: self.trigger_action(self.open_options, 1)))
        self.layout.add_child(Button(app, 'Quit to Menu', (0, 0), (0.3, 0.07), lambda: self.trigger_action(self.quit_to_menu, 1)))
        
        self.layout.update_layout()

    @global_profiler.profile_func("PauseMenu_TriggerAction")
    def trigger_action(self, action: Callable[[], None], anim_dir: int = 1) -> None:
        """Triggers an out-transition before calling the specified action."""
        if self.transition_state in ('IDLE', 'IN'):
            self.pending_action = action
            self.transition_state = 'OUT'
            self.transition_progress = 0.0
            self.anim_dir = anim_dir

    @global_profiler.profile_func("PauseMenu_OpenOptions")
    def open_options(self) -> None:
        """Transitions to the Options Menu."""
        self.app.options_menu.previous_state = 'PAUSED'
        self.app.game_state = 'OPTIONS'
        self.app.options_menu.transition_state = 'IN'
        self.app.options_menu.transition_progress = 0.0

    @global_profiler.profile_func("PauseMenu_ResumeGame")
    def resume_game(self) -> None:
        """Hides the pause menu and re-captures the mouse for gameplay."""
        self.app.game_state = 'IN_GAME'
        pg.event.set_grab(True)
        pg.mouse.set_visible(False)

    @global_profiler.profile_func("PauseMenu_QuitToMenu")
    def quit_to_menu(self) -> None:
        """Unloads the game world and returns to the Main Menu."""
        self.app.game_state = 'MAIN_MENU'
        self.app.menu.state = 'MAIN'
        
        if self.app.scene:
            self.app.scene.world.save()
            self.app.scene = None # Unload the world to free memory

    @global_profiler.profile_func("PauseMenu_Update")
    def update(self) -> None:
        """Processes animations and propagates update events to children."""
        if self.transition_state != 'IDLE':
            self.transition_progress += self.app.delta_time * 0.005
            
            if self.transition_progress >= 1.0:
                self.transition_progress = 1.0
                
                if self.transition_state == 'OUT':
                    if self.pending_action:
                        action: Callable[[], None] = self.pending_action
                        self.pending_action = None
                        action()
                    
                    else:
                        self.transition_state = 'IDLE'
                
                elif self.transition_state == 'IN':
                    self.transition_state = 'IDLE'
                    
        if self.transition_state != 'IDLE':
            mouse_pos: Tuple[int, int] = (-999, -999)
        
        else:
            mouse_pos = pg.mouse.get_pos()
            
        self.layout.update(mouse_pos)

    @global_profiler.profile_func("PauseMenu_HandleEvent")
    def handle_event(self, event: Any) -> None:
        if self.transition_state != 'IDLE':
            return
        
        self.layout.handle_event(event)

    @global_profiler.profile_func("PauseMenu_Render")
    def render(self) -> None:
        """Renders the dimming background and the menu elements with animation easing."""
        t: float = self.transition_progress
        ease: float = 1.0 - (1.0 - t) ** 3
        offset_y: float = 0.0
        alpha: float = 1.0
        
        if self.transition_state == 'IN':
            offset_y = (1.0 - ease) * -0.5 * self.anim_dir
            alpha = ease
        
        elif self.transition_state == 'OUT':
            offset_y = ease * 0.5 * self.anim_dir
            alpha = 1.0 - ease
            
        offset: Tuple[float, float] = (0.0, offset_y)
        bg_alpha: float = alpha if self.transition_state != 'IDLE' else 1.0
        
        self.bg_mesh.program['u_scale'] = (1.0, 1.0)
        self.bg_mesh.program['u_offset'] = (0.0, 0.0)
        self.bg_mesh.program['u_color'] = (0.0, 0.0, 0.0, 0.6 * bg_alpha)
        self.bg_mesh.render()

        tex: Any = self.title_tex
        tex.use(location=4)
        tex_w: int = tex.size[0]
        tex_h: int = tex.size[1]
        scale_y: float = 0.08
        scale_x: float = scale_y * (tex_w / tex_h) / ASPECT_RATIO
        self.title_mesh.program['u_scale'] = (scale_x, scale_y)
        self.title_mesh.program['u_offset'] = (0.0, 0.4 + offset_y * 0.5)
        
        if 'u_alpha' in self.title_mesh.program:
            self.title_mesh.program['u_alpha'] = alpha
        
        self.title_mesh.render()
        
        if 'u_alpha' in self.title_mesh.program:
            self.title_mesh.program['u_alpha'] = 1.0

        self.layout.render(offset, alpha)


class OptionsMenu:
    """
    Manages the game settings screen.
    
    Provides sliders and toggles for FOV, Mouse Sensitivity, Volume, Render Distance, 
    and Visual Tints. Handles serializing these settings to config.json.
    
    Args:
        app (Any): The main application context.
    """
    @global_profiler.profile_func("OptionsMenu_Init")
    def __init__(self, app: Any) -> None:
        self.app: Any = app
        self.title_renderer: Any = TextRenderer(app)
        self.title_renderer.font = pg.font.SysFont('arial', FONT_SIZE_PAUSED, bold=True)
        self.title_mesh: Any = UITextMesh(app)
        self.title_tex: Any = self.title_renderer.get_texture("Options")
        self.bg_mesh: Any = UIColorMesh(app)

        self.transition_state: str = 'IN'
        self.transition_progress: float = 0.0
        self.pending_action: Optional[Callable[[], None]] = None
        self.anim_dir: int = 1

        # Ensure config keys exist to prevent KeyError on old config.json files
        if 'music_volume' not in app.config:
            app.config['music_volume'] = app.config.get('volume', 50)
        
        if 'sfx_volume' not in app.config:
            app.config['sfx_volume'] = 20

        self.layout: Any = VBox(pos=(0, 0.3), spacing=0.09)
        self.layout.add_child(Slider(app, 'FOV', (0, 0), (0.3, 0.05), 30, 110, 'fov', self.update_fov, is_int=True))
        self.layout.add_child(Slider(app, 'Sensitivity', (0, 0), (0.3, 0.05), 0.0005, 0.005, 'sensitivity'))
        self.layout.add_child(Slider(app, 'Music Volume', (0, 0), (0.3, 0.05), 0, 100, 'music_volume', self.update_music_volume, is_int=True))
        self.layout.add_child(Slider(app, 'SFX Volume', (0, 0), (0.3, 0.05), 0, 100, 'sfx_volume', self.update_sfx_volume, is_int=True))
        self.layout.add_child(Slider(app, 'Render Distance', (0, 0), (0.3, 0.05), 2, 14, 'render_distance', is_int=True))
        self.layout.add_child(Toggle(app, 'Underwater Tint', (0.12, 0), (0.04, 0.035), 'underwater_tint'))
        self.layout.add_child(UINode(size=(0, 0.05))) # Positive Spacer to add space
        self.layout.add_child(Button(app, 'Back', (0, 0), (0.2, 0.06), lambda: self.trigger_action(self.go_back, 1)))
        
        self.layout.update_layout()
        
        self.previous_state: str = 'MAIN_MENU'

    @global_profiler.profile_func("OptionsMenu_TriggerAction")
    def trigger_action(self, action: Callable[[], None], anim_dir: int = 1) -> None:
        """Initiates an animated transition out before running the requested action."""
        if self.transition_state in ('IDLE', 'IN'):
            self.pending_action = action
            self.transition_state = 'OUT'
            self.transition_progress = 0.0
            self.anim_dir = anim_dir

    @global_profiler.profile_func("OptionsMenu_UpdateFov")
    def update_fov(self, val: float) -> None:
        """Applies the field-of-view setting instantly to the active player."""
        if self.app.scene:
            self.app.player.fov = glm.radians(val)

    @global_profiler.profile_func("OptionsMenu_UpdateMusicVolume")
    def update_music_volume(self, val: float) -> None:
        """Adjusts the global Pygame mixer music volume."""
        pg.mixer.music.set_volume(val / 100.0)

    @global_profiler.profile_func("OptionsMenu_UpdateSfxVolume")
    def update_sfx_volume(self, val: float) -> None:
        """Delegates sound effect volume changes to the central Sounds manager."""
        self.app.sounds.set_sfx_volume(val)

    @global_profiler.profile_func("OptionsMenu_GoBack")
    def go_back(self) -> None:
        """Returns to the menu that originally opened this options screen."""
        self.app.save_config()
        self.app.game_state = self.previous_state
        
        if self.previous_state == 'MAIN_MENU':
            self.app.menu.transition_state = 'IN'
            self.app.menu.transition_progress = 0.0
        
        elif self.previous_state == 'PAUSED':
            self.app.pause_menu.transition_state = 'IN'
            self.app.pause_menu.transition_progress = 0.0

    @global_profiler.profile_func("OptionsMenu_Update")
    def update(self) -> None:
        """Updates animations and cascades logic down to layout components."""
        if self.transition_state != 'IDLE':
            self.transition_progress += self.app.delta_time * 0.005
            
            if self.transition_progress >= 1.0:
                self.transition_progress = 1.0
                
                if self.transition_state == 'OUT':
                    if self.pending_action:
                        action: Callable[[], None] = self.pending_action
                        self.pending_action = None
                        action()
                    
                    else:
                        self.transition_state = 'IDLE'
                
                elif self.transition_state == 'IN':
                    self.transition_state = 'IDLE'
                    
        if self.transition_state != 'IDLE':
            mouse_pos: Tuple[int, int] = (-999, -999)
        
        else:
            mouse_pos = pg.mouse.get_pos()
            
        self.layout.update(mouse_pos)

    @global_profiler.profile_func("OptionsMenu_HandleEvent")
    def handle_event(self, event: Any) -> None:
        if self.transition_state != 'IDLE':
            return
        
        self.layout.handle_event(event)

    @global_profiler.profile_func("OptionsMenu_Render")
    def render(self) -> None:
        """Draws the options layout UI nodes alongside their animated transitions."""
        t: float = self.transition_progress
        ease: float = 1.0 - (1.0 - t) ** 3
        offset_y: float = 0.0
        alpha: float = 1.0
        
        if self.transition_state == 'IN':
            offset_y = (1.0 - ease) * -0.5 * self.anim_dir
            alpha = ease
        
        elif self.transition_state == 'OUT':
            offset_y = ease * 0.5 * self.anim_dir
            alpha = 1.0 - ease
            
        offset: Tuple[float, float] = (0.0, offset_y)
        bg_alpha: float = alpha if self.transition_state != 'IDLE' else 1.0
        
        if self.previous_state == 'PAUSED':
            self.bg_mesh.program['u_scale'] = (1.0, 1.0)
            self.bg_mesh.program['u_offset'] = (0.0, 0.0)
            self.bg_mesh.program['u_color'] = (0.0, 0.0, 0.0, 0.8 * bg_alpha)
            self.bg_mesh.render()

        tex: Any = self.title_tex
        tex.use(location=4)
        tex_w: int = tex.size[0]
        tex_h: int = tex.size[1]
        scale_y: float = 0.08
        scale_x: float = scale_y * (tex_w / tex_h) / ASPECT_RATIO
        self.title_mesh.program['u_scale'] = (scale_x, scale_y)
        self.title_mesh.program['u_offset'] = (0.0, 0.55 + offset_y * 0.5)
        
        if 'u_alpha' in self.title_mesh.program:
            self.title_mesh.program['u_alpha'] = alpha
        self.title_mesh.render()
        
        if 'u_alpha' in self.title_mesh.program:
            self.title_mesh.program['u_alpha'] = 1.0

        self.layout.render(offset, alpha)

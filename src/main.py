"""Main application module for the Pyrite graphics engine."""

from settings import *
import moderngl as mgl
import pygame as pg
import json
import random
import sqlite3
from noise import set_seed
import os
import sys
from shader_program import ShaderProgram
from scene import Scene
from player import Player
from sounds import Sounds
from textures import Textures
from ui import TextRenderer, UITextMesh, MainMenu, PauseMenu, OptionsMenu
from profiler import global_profiler


class Pyrite:
    """
    The core engine application class. 
    Manages the Pygame window, ModernGL context, main game loop, and dispatches 
    rendering and logic to the active game state (e.g., Menus vs In-Game).
    """
    @global_profiler.profile_func("Pyrite_Init")
    def __init__(self):
        """
        Initializes Pygame, the OpenGL context, window settings, and prepares 
        global game state variables and configurations.
        """
        pg.init()
        
        try:
            icon_img = pg.image.load(get_path('assets/icon-nobg.png'))
            pg.display.set_icon(icon_img)
        except pg.error:
            pass
        
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MAJOR_VERSION, MAJOR_VER)
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MINOR_VERSION, MINOR_VER)
        pg.display.gl_set_attribute(pg.GL_CONTEXT_PROFILE_MASK, pg.GL_CONTEXT_PROFILE_CORE)
        pg.display.gl_set_attribute(pg.GL_DEPTH_SIZE, DEPTH_SIZE)
        pg.display.gl_set_attribute(pg.GL_MULTISAMPLESAMPLES, NUM_SAMPLES)

        pg.display.set_mode(WIN_RES, flags=pg.OPENGL | pg.DOUBLEBUF | pg.FULLSCREEN)
        self.ctx = mgl.create_context()

        self.ctx.enable(flags=mgl.DEPTH_TEST | mgl.CULL_FACE | mgl.BLEND)
        self.ctx.gc_mode = 'auto'

        self.clock = pg.time.Clock()
        self.delta_time = 0
        self.time = 0
        self.world_session_time = 0.0 # New variable for in-game time
        self.bg_color = BG_COLOR

        self.is_running = True
        self.game_state = 'MAIN_MENU'
        
        self.config = {
            'fov': FOV_DEG,
            'sensitivity': MOUSE_SENSITIVITY,
            'volume': 10,
            'render_distance': 4,
            'underwater_tint': False
        }
        self.load_config()
        
        # Placeholders for game session objects
        self.scene = None
        self.menu = None
        self.wireframe = False
        self.freeze_culling = False
        self.show_debug = False

        self.on_init()

    @global_profiler.profile_func("Load_Config")
    def load_config(self):
        """
        Reads and applies engine settings from a local JSON configuration file.
        """
        if os.path.exists('config.json'):
            with open('config.json', 'r', encoding='utf-8') as f:
                try:
                    self.config.update(json.load(f))
                except json.JSONDecodeError:
                    pass

    @global_profiler.profile_func("Save_Config")
    def save_config(self):
        """
        Serializes and saves the active engine configuration to disk.
        """
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(self.config, f)

    @global_profiler.profile_func("On_Init")
    def on_init(self):
        """
        Instantiates critical subsystems including UI menus, Shader programs, 
        Sound mixers, Textures, and the Player entity.
        """
        self.textures = Textures(self)
        self.player = Player(self)
        self.sounds = Sounds(self)
        self.shader_program = ShaderProgram(self)
        self.menu = MainMenu(self)
        self.pause_menu = PauseMenu(self)
        self.options_menu = OptionsMenu(self)

    @global_profiler.profile_func("Init_Game_Session")
    def init_game_session(self, save_name="Default_World", force_seed=None, game_mode=None):
        """
        Initializes a designated world session, seeding the procedural generator
        and executing a blocking load loop until the initial area is fully generated 
        and prepared for rendering.
        """
        self.game_state = 'LOADING'
        
        if game_mode is not None:
            self.player.game_mode = game_mode

        # Determine the seed BEFORE any world objects are created to prevent premature Numba compilation.
        save_path = f'saves/{save_name}.db'
        seed = 0
        
        if os.path.exists(save_path):
            try:
                connection = sqlite3.connect(save_path)
                cursor = connection.cursor()
                cursor.execute('SELECT seed FROM world_meta WHERE id=1')
                row = cursor.fetchone()
                if row:
                    seed = row[0]
                connection.close()
            
            except sqlite3.Error as e:
                print(f"[SYSTEM] Could not read seed from existing save file: {e}")
                seed = random.randint(100000, 999999999)
        
        else:
            seed = force_seed if force_seed is not None else random.randint(100000, 999999999)
            
        set_seed(seed)
        
        self.world_session_time = 0.0 # Reset world session time for the new world
        self.scene = Scene(self, save_name, seed) # Pass seed to scene/world
        
        self.render_loading_screen("STARTING GAME...")
        
        # Pre-load initial chunks
        self.scene.world.update()
        
        loading_progress = 0
        
        # Wait for all initial chunks to generate and mesh
        while self.scene.world.load_queue or self.scene.world.build_queue or self.scene.world.mesh_queue:
            self.scene.world.update()
            
            active = len(self.scene.world.active_chunks)
            queues = len(self.scene.world.load_queue) + len(self.scene.world.build_queue) + len(self.scene.world.mesh_queue)
            ready = active - queues
            progress = max(0, min(100, int((ready / active) * 100) if active > 0 else 0))
            loading_progress = max(loading_progress, progress)
            
            self.render_loading_screen(f"GENERATING TERRAIN... {loading_progress}%")
        
        # Clear the event queue one last time to prevent buffered inputs
        pg.event.clear()
        pg.mouse.get_rel() # Reset relative mouse movement to prevent sudden camera spinning
        pg.event.set_grab(True)
        pg.mouse.set_visible(False)
        
        self.game_state = 'IN_GAME'

    @global_profiler.profile_func("Render_Loading_Screen")
    def render_loading_screen(self, text="INITIALIZING..."):
        """
        Renders a minimal UI overlay during heavily blocking load operations, 
        ensuring Pygame's event queue is flushed so the operating system doesn't 
        flag the application as "Not Responding".
        """
        # Discard pending events to prevent OS freezing and buffered inputs
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.quit_game()
                sys.exit()

        self.ctx.clear(color=(0.1, 0.1, 0.1))
        
        text_renderer = TextRenderer(self)
        text_mesh = UITextMesh(self)
        
        # 1. Main Title
        text_renderer.font = pg.font.SysFont('arial', FONT_SIZE_LOADING, bold=True)
        tex = text_renderer.get_texture("LOADING WORLD...")
        tex.use(location=4)
        
        tex_w, tex_h = tex.size
        scale_y = 0.1
        scale_x = scale_y * (tex_w / tex_h) / ASPECT_RATIO
        
        text_mesh.program['u_scale'] = (scale_x, scale_y)
        text_mesh.program['u_offset'] = (0.0, 0.1)
        
        self.ctx.disable(mgl.DEPTH_TEST)
        text_mesh.render()
        
        # 2. Sub-status text
        text_renderer.font = pg.font.SysFont('arial', FONT_SIZE_SUBTITLE, bold=False)
        tex_sub = text_renderer.get_texture(text)
        tex_sub.use(location=4)
        
        tex_w, tex_h = tex_sub.size
        scale_y = 0.04
        scale_x = scale_y * (tex_w / tex_h) / ASPECT_RATIO
        
        text_mesh.program['u_scale'] = (scale_x, scale_y)
        text_mesh.program['u_offset'] = (0.0, -0.15)
        text_mesh.render()
        
        pg.display.flip()

    @global_profiler.profile_func("Pyrite_Update")
    def update(self):
        """
        Advances the central engine logic. Delegates to the active game state 
        (e.g., ticking the world simulation, evaluating UI animations).
        """
        if self.game_state == 'MAIN_MENU':
            self.menu.update()
        
        elif self.game_state in ('IN_GAME', 'INVENTORY'):
            self.player.update()
            self.shader_program.update()
            self.world_session_time += self.delta_time * 0.001
            self.scene.update()
        
        elif self.game_state == 'PAUSED':
            self.pause_menu.update()
        
        elif self.game_state == 'OPTIONS':
            self.options_menu.update()

        self.delta_time = min(self.clock.tick(), 50) # Cap delta time to avoid physics lag spikes
        self.time = pg.time.get_ticks() * 0.001
        
        if self.game_state == 'IN_GAME':
            pg.display.set_caption(f'{self.clock.get_fps() :.0f}')
        
        elif self.game_state == 'PAUSED':
            pg.display.set_caption('Game Paused')
        
        else:
            pg.display.set_caption('Pyrite')

    @global_profiler.profile_func("Pyrite_Render")
    def render(self):
        """
        Clears the OpenGL framebuffer and issues draw instructions corresponding 
        to the active state, layering menus over 3D scenes when appropriate.
        """
        self.ctx.clear(color=self.bg_color)
        
        if self.game_state == 'MAIN_MENU':
            self.ctx.disable(mgl.DEPTH_TEST)
            self.menu.render()
            self.ctx.enable(mgl.DEPTH_TEST)
        
        elif self.game_state in ('IN_GAME', 'INVENTORY'):
            self.scene.render()
        
        elif self.game_state == 'PAUSED':
            if self.scene:
                self.scene.render()
            
            self.ctx.disable(mgl.DEPTH_TEST)
            self.pause_menu.render()
            self.ctx.enable(mgl.DEPTH_TEST)
        
        elif self.game_state == 'OPTIONS':
            if self.options_menu.previous_state == 'PAUSED' and self.scene:
                self.scene.render()
            
            elif self.options_menu.previous_state == 'MAIN_MENU':
                self.ctx.disable(mgl.DEPTH_TEST)
                self.menu.render_bg()
            
            self.ctx.disable(mgl.DEPTH_TEST)
            self.options_menu.render()
            self.ctx.enable(mgl.DEPTH_TEST)
            
        pg.display.flip()

    @global_profiler.profile_func("Handle_Events")
    def handle_events(self):
        """
        Polls raw input events from the operating system and routes them 
        to the respective handlers (e.g., player movement, UI button clicks, 
        or screen toggles).
        """
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.quit_game()
            
            elif event.type == pg.KEYDOWN and event.key == pg.K_p:
                self.wireframe = not self.wireframe
            
            elif event.type == pg.KEYDOWN and event.key == pg.K_o:
                self.freeze_culling = not self.freeze_culling
            
            elif event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                if self.game_state == 'IN_GAME':
                    
                    # Capture screen for thumbnail before UI draws over it!
                    try:
                        data = self.ctx.screen.read(components=3)
                        img = pg.image.frombuffer(data, (int(WIN_RES.x), int(WIN_RES.y)), 'RGB')
                        img = pg.transform.flip(img, False, True) # OpenGL renders bottom-up
                        thumb_w, thumb_h = 320, int(320 / ASPECT_RATIO)
                        img = pg.transform.smoothscale(img, (thumb_w, thumb_h))
                        pg.image.save(img, f"saves/{self.scene.world.save_name}_thumb.png")
                    
                    except Exception as e:
                        print(f"Failed to save thumbnail: {e}")
                    
                    self.game_state = 'PAUSED'
                    self.pause_menu.transition_state = 'IN'
                    self.pause_menu.transition_progress = 0.0
                    pg.event.set_grab(False)
                    pg.mouse.set_visible(True)
                
                elif self.game_state == 'INVENTORY':
                    self.scene.inventory_ui.close()
                    self.game_state = 'IN_GAME'
                    pg.event.set_grab(True)
                    pg.mouse.set_visible(False)
                
                elif self.game_state == 'PAUSED':
                    self.pause_menu.trigger_action(self.pause_menu.resume_game, 1)
                
                elif self.game_state == 'OPTIONS':
                    self.options_menu.trigger_action(self.options_menu.go_back, 1)
                
                else: # Esc inside Main Menu quits the game
                    self.menu.trigger_action(self.quit_game, 1)
            
            elif event.type == pg.KEYDOWN and event.key == pg.K_F3:
                self.show_debug = not self.show_debug
            
            elif event.type == pg.KEYDOWN and event.key == pg.K_e:
                if self.game_state == 'IN_GAME':
                    self.game_state = 'INVENTORY'
                    pg.event.set_grab(False)
                    pg.mouse.set_visible(True)
                
                elif self.game_state == 'INVENTORY':
                    self.scene.inventory_ui.close()
                    self.game_state = 'IN_GAME'
                    pg.event.set_grab(True)
                    pg.mouse.set_visible(False)
            
            if self.game_state == 'MAIN_MENU':
                self.menu.handle_event(event)
            
            elif self.game_state == 'IN_GAME':
                self.player.handle_event(event=event)
            
            elif self.game_state == 'INVENTORY':
                self.scene.inventory_ui.handle_event(event)
            
            elif self.game_state == 'PAUSED':
                self.pause_menu.handle_event(event)
            
            elif self.game_state == 'OPTIONS':
                self.options_menu.handle_event(event)

    @global_profiler.profile_func("Quit_Game")
    def quit_game(self):
        """
        Interrupts the primary application execution loop to safely shut down.
        """
        self.is_running = False

    @global_profiler.profile_func("Pyrite_Run")
    def run(self):
        """
        The primary execution loop tracking logic updates, event polling, 
        and frame rendering until the application halts.
        """
        while self.is_running:
            global_profiler.start_frame()
            self.handle_events()
            self.update()
            self.render()
            global_profiler.end_frame()
            
        if self.scene:
            self.scene.world.save()
        
        pg.quit()
        global_profiler.save_report("profiling_results.json")
        sys.exit()


if __name__ == '__main__':
    app = Pyrite()
    app.run()

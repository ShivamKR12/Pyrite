from settings import *
import moderngl as mgl
import pygame as pg
import json
import os
import sys
from shader_program import ShaderProgram
from scene import Scene
from player import Player
from sounds import Sounds
from textures import Textures
from ui import TextRenderer, UITextMesh, Menu, PauseMenu, OptionsMenu


class VoxelEngine:
    def __init__(self):
        pg.init()
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MAJOR_VERSION, MAJOR_VER)
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MINOR_VERSION, MINOR_VER)
        pg.display.gl_set_attribute(pg.GL_CONTEXT_PROFILE_MASK, pg.GL_CONTEXT_PROFILE_CORE)
        pg.display.gl_set_attribute(pg.GL_DEPTH_SIZE, DEPTH_SIZE)
        pg.display.gl_set_attribute(pg.GL_MULTISAMPLESAMPLES, NUM_SAMPLES)

        pg.display.set_mode(WIN_RES, flags=pg.OPENGL | pg.DOUBLEBUF)
        self.ctx = mgl.create_context()

        self.ctx.enable(flags=mgl.DEPTH_TEST | mgl.CULL_FACE | mgl.BLEND)
        self.ctx.gc_mode = 'auto'

        self.clock = pg.time.Clock()
        self.delta_time = 0
        self.time = 0
        self.bg_color = BG_COLOR

        self.is_running = True
        self.game_state = 'MAIN_MENU'
        
        self.config = {
            'fov': FOV_DEG,
            'sensitivity': MOUSE_SENSITIVITY,
            'volume': 0.1,
            'render_distance': 4
        }
        self.load_config()
        
        # Placeholders for game session objects
        self.scene = None
        self.menu = None
        self.wireframe = False
        self.freeze_culling = False

        self.on_init()

    def load_config(self):
        if os.path.exists('config.json'):
            with open('config.json', 'r') as f:
                try:
                    self.config.update(json.load(f))
                except json.JSONDecodeError:
                    pass

    def save_config(self):
        with open('config.json', 'w') as f:
            json.dump(self.config, f)

    def on_init(self):
        self.textures = Textures(self)
        self.player = Player(self)
        self.sounds = Sounds(self)
        self.shader_program = ShaderProgram(self)
        self.menu = Menu(self)
        self.pause_menu = PauseMenu(self)
        self.options_menu = OptionsMenu(self)

    def init_game_session(self):
        self.game_state = 'LOADING'
        self.render_loading_screen()
        
        self.scene = Scene(self)
        
        pg.event.set_grab(True)
        pg.mouse.set_visible(False)
        self.game_state = 'IN_GAME'

    def render_loading_screen(self):
        self.ctx.clear(color=(0.1, 0.1, 0.1))
        
        text_renderer = TextRenderer(self)
        text_renderer.font = pg.font.SysFont('arial', 48, bold=True)
        tex = text_renderer.get_texture("LOADING WORLD...")
        tex.use(location=4)
        
        text_mesh = UITextMesh(self)
        
        tex_w, tex_h = tex.size
        scale_y = 0.1
        scale_x = scale_y * (tex_w / tex_h) / ASPECT_RATIO
        
        text_mesh.program['u_scale'] = (scale_x, scale_y)
        text_mesh.program['u_offset'] = (0.0, 0.0)
        
        self.ctx.disable(mgl.DEPTH_TEST)
        text_mesh.render()
        
        pg.display.flip()

    def update(self):
        if self.game_state == 'MAIN_MENU':
            self.menu.update()
        elif self.game_state == 'IN_GAME':
            self.player.update()
            self.shader_program.update()
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
            pg.display.set_caption('Voxel Engine')

    def render(self):
        self.ctx.clear(color=self.bg_color)
        if self.game_state == 'MAIN_MENU':
            self.ctx.disable(mgl.DEPTH_TEST)
            self.menu.render()
            self.ctx.enable(mgl.DEPTH_TEST)
        elif self.game_state == 'IN_GAME':
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
            self.ctx.disable(mgl.DEPTH_TEST)
            self.options_menu.render()
            self.ctx.enable(mgl.DEPTH_TEST)
            
        pg.display.flip()

    def handle_events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.quit_game()
            elif event.type == pg.KEYDOWN and event.key == pg.K_p:
                self.wireframe = not self.wireframe
            elif event.type == pg.KEYDOWN and event.key == pg.K_o:
                self.freeze_culling = not self.freeze_culling
            elif event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                if self.game_state == 'IN_GAME':
                    self.game_state = 'PAUSED'
                    pg.event.set_grab(False)
                    pg.mouse.set_visible(True)
                elif self.game_state == 'PAUSED':
                    self.pause_menu.resume_game()
                elif self.game_state == 'OPTIONS':
                    self.options_menu.go_back()
                else: # Esc inside Main Menu quits the game
                    self.quit_game()
            
            if self.game_state == 'MAIN_MENU':
                self.menu.handle_event(event)
            elif self.game_state == 'IN_GAME':
                self.player.handle_event(event=event)
            elif self.game_state == 'PAUSED':
                self.pause_menu.handle_event(event)
            elif self.game_state == 'OPTIONS':
                self.options_menu.handle_event(event)

    def quit_game(self):
        self.is_running = False

    def run(self):
        while self.is_running:
            self.handle_events()
            self.update()
            self.render()
            
        if self.scene:
            self.scene.world.save()
        pg.quit()
        sys.exit()


if __name__ == '__main__':
    app = VoxelEngine()
    app.run()

from settings import *
import moderngl as mgl
import pygame as pg
import sys
from shader_program import ShaderProgram
from scene import Scene
from player import Player
from sounds import Sounds
from textures import Textures
from ui import TextRenderer, UITextMesh, Menu, PauseMenu


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
        
        # Placeholders for game session objects
        self.scene = None
        self.menu = None

        self.on_init()

    def on_init(self):
        self.textures = Textures(self)
        self.player = Player(self)
        self.sounds = Sounds(self)
        self.shader_program = ShaderProgram(self)
        self.menu = Menu(self)
        self.pause_menu = PauseMenu(self)

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
        pg.display.flip()

    def handle_events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.quit_game()
            elif event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                if self.game_state == 'IN_GAME':
                    self.game_state = 'PAUSED'
                    pg.event.set_grab(False)
                    pg.mouse.set_visible(True)
                elif self.game_state == 'PAUSED':
                    self.pause_menu.resume_game()
                else: # Esc inside Main Menu quits the game
                    self.quit_game()
            
            if self.game_state == 'MAIN_MENU':
                self.menu.handle_event(event)
            elif self.game_state == 'IN_GAME':
                self.player.handle_event(event=event)
            elif self.game_state == 'PAUSED':
                self.pause_menu.handle_event(event)

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

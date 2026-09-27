"""
Main application module and entry point for the Pyrite graphics engine.

This module contains the core `Pyrite` class which orchestrates the entire application.
It manages the OS-level Pygame window, establishes the ModernGL hardware context,
controls the primary execution loop, and routes inputs to the active game state.
"""

import json
import os
import random
import sqlite3
import sys
from typing import Any, Dict, Optional

import moderngl as mgl
import pygame as pg

from noise import set_seed
from player import Player
from profiler import global_profiler
from scene import Scene
from settings import (
    ASPECT_RATIO,
    BG_COLOR,
    DEPTH_SIZE,
    FONT_SIZE_LOADING,
    FONT_SIZE_SUBTITLE,
    FOV_DEGREE,
    MAJOR_VERSION,
    MINOR_VERSION,
    MOUSE_SENSITIVITY,
    NUM_SAMPLES,
    WINDOW_RESOLUTION,
    get_path,
)
from shader_program import ShaderProgram
from sounds import Sounds
from textures import Textures
from ui.components import TextRenderer, UITextMesh
from ui.menus import MainMenu, OptionsMenu, PauseMenu


class Pyrite:
    """
    The core engine application class.
    Manages the Pygame window, ModernGL context, main game loop, and dispatches
    rendering and logic to the active game state (e.g., Menus vs In-Game).
    """

    @global_profiler.profile_func('Pyrite_Init')
    def __init__(self) -> None:
        """
        Initializes Pygame, the OpenGL context, window settings, and prepares
        global game state variables and configurations.
        """
        # Execute expressions
        pg.init()

        # Error handling
        try:
            # Variable assignments
            icon_img: pg.Surface = pg.image.load(get_path('assets/icons/icon-nobg.png'))
            # Execute expressions
            pg.display.set_icon(icon_img)
        except pg.error:
            # No operation
            pass

        # Execute expressions
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MAJOR_VERSION, MAJOR_VERSION)
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MINOR_VERSION, MINOR_VERSION)
        pg.display.gl_set_attribute(pg.GL_CONTEXT_PROFILE_MASK, pg.GL_CONTEXT_PROFILE_CORE)
        pg.display.gl_set_attribute(pg.GL_DEPTH_SIZE, DEPTH_SIZE)
        pg.display.gl_set_attribute(pg.GL_MULTISAMPLESAMPLES, NUM_SAMPLES)

        pg.display.set_mode(WINDOW_RESOLUTION, flags=pg.OPENGL | pg.DOUBLEBUF | pg.FULLSCREEN)
        # Variable assignments
        self.ctx: Any = mgl.create_context()

        # Execute expressions
        self.ctx.enable(flags=mgl.DEPTH_TEST | mgl.CULL_FACE | mgl.BLEND)
        # Variable assignments
        self.ctx.gc_mode = 'auto'

        self.clock: pg.time.Clock = pg.time.Clock()
        self.delta_time: int = 0
        self.time: float = 0.0
        self.world_session_time: float = 0.0  # New variable for in-game time
        self.bg_color: Any = BG_COLOR

        self.is_running: bool = True
        self.game_state: str = 'MAIN_MENU'

        self.config: Dict[str, Any] = {
            'fov': FOV_DEGREE,
            'sensitivity': MOUSE_SENSITIVITY,
            'volume': 10,
            'render_distance': 4,
            'underwater_tint': False,
        }
        # Execute expressions
        self.load_config()

        # Variable assignments
        self.scene: Any = None
        self.menu: Any = None
        self.wireframe: bool = False
        self.freeze_culling: bool = False
        self.show_debug: bool = False

        self.textures: Any = None
        self.player: Any = None
        self.sounds: Any = None
        self.shader_program: Any = None
        self.pause_menu: Any = None
        self.options_menu: Any = None

        # Execute expressions
        self.on_init()

    @global_profiler.profile_func('Load_Config')
    def load_config(self) -> None:
        """
        Reads and applies engine settings from a local JSON configuration file.
        """
        # Conditional logic
        if os.path.exists('config.json'):
            # Context management
            with open('config.json', 'r', encoding='utf-8') as f:
                # Error handling
                try:
                    # Execute expressions
                    self.config.update(json.load(f))
                except json.JSONDecodeError:
                    # No operation
                    pass

    @global_profiler.profile_func('Save_Config')
    def save_config(self) -> None:
        """
        Serializes and saves the active engine configuration to disk.
        """
        # Context management
        with open('config.json', 'w', encoding='utf-8') as f:
            # Execute expressions
            json.dump(self.config, f)

    @global_profiler.profile_func('On_Init')
    def on_init(self) -> None:
        """
        Instantiates critical subsystems including UI menus, Shader programs,
        Sound mixers, Textures, and the Player entity.
        """
        # Variable assignments
        self.textures = Textures(self)
        self.player = Player(self)
        self.sounds = Sounds(self)
        self.shader_program = ShaderProgram(self)
        self.menu = MainMenu(self)
        self.pause_menu = PauseMenu(self)
        self.options_menu = OptionsMenu(self)

    @global_profiler.profile_func('Init_Game_Session')
    def init_game_session(
        self, save_name: str = 'Default_World', force_seed: Optional[int] = None, game_mode: Optional[int] = None
    ) -> None:
        """
        Initializes a designated world session, seeding the procedural generator
        and executing a blocking load loop until the initial area is fully generated
        and prepared for rendering.
        """
        # Variable assignments
        self.game_state = 'LOADING'

        # Conditional logic
        if game_mode is not None:
            # Variable assignments
            self.player.game_mode = game_mode

        # Variable assignments
        save_path: str = f'saves/{save_name}.db'
        seed: int = 0

        # Conditional logic
        if os.path.exists(save_path):
            # Variable assignments
            connection: Optional[sqlite3.Connection] = None
            cursor: Optional[sqlite3.Cursor] = None
            # Error handling
            try:
                # Variable assignments
                connection = sqlite3.connect(save_path)
                cursor = connection.cursor()
                # Execute expressions
                cursor.execute('SELECT seed FROM world_meta WHERE id=1')
                # Variable assignments
                row: Any = cursor.fetchone()
                # Conditional logic
                if row:
                    # Variable assignments
                    seed = row[0]

            except sqlite3.Error as e:
                # Execute expressions
                print(f'[SYSTEM] Could not read seed from existing save file: {e}')
                # Variable assignments
                seed = random.randint(100000, 999999999)
            finally:
                # Conditional logic
                if cursor:
                    # Error handling
                    try:
                        # Execute expressions
                        cursor.close()
                    except Exception as e:
                        # Execute expressions
                        print(f'[SYSTEM] Error closing cursor: {e}')
                if connection:
                    # Error handling
                    try:
                        # Execute expressions
                        connection.close()
                    except Exception as e:
                        # Execute expressions
                        print(f'[SYSTEM] Error closing connection: {e}')

        else:
            # Variable assignments
            seed = force_seed if force_seed is not None else random.randint(100000, 999999999)

        # Execute expressions
        set_seed(seed)

        # Variable assignments
        self.world_session_time = 0.0  # Reset world session time for the new world
        self.scene = Scene(self, save_name, seed)  # Pass seed to scene/world

        # Execute expressions
        self.render_loading_screen('STARTING GAME...')

        self.scene.world.update()

        # Variable assignments
        loading_progress: int = 0

        # Loop processing
        while self.scene.world.load_queue or self.scene.world.build_queue or self.scene.world.mesh_queue:
            # Execute expressions
            self.scene.world.update()

            # Variable assignments
            active: int = len(self.scene.world.active_chunks)
            queues: int = (
                len(self.scene.world.load_queue) + len(self.scene.world.build_queue) + len(self.scene.world.mesh_queue)
            )
            ready: int = active - queues
            progress: int = max(0, min(100, int((ready / active) * 100) if active > 0 else 0))
            loading_progress = max(loading_progress, progress)

            # Execute expressions
            self.render_loading_screen(f'GENERATING TERRAIN... {loading_progress}%')

        # Execute expressions
        pg.event.clear()
        pg.mouse.get_rel()  # Reset relative mouse movement to prevent sudden camera spinning
        pg.event.set_grab(True)
        pg.mouse.set_visible(False)

        # Variable assignments
        self.game_state = 'IN_GAME'

    @global_profiler.profile_func('Render_Loading_Screen')
    def render_loading_screen(self, text: str = 'INITIALIZING...') -> None:
        """
        Renders a minimal UI overlay during heavily blocking load operations,
        ensuring Pygame's event queue is flushed so the operating system doesn't
        flag the application as "Not Responding".
        """
        # Loop processing
        for event in pg.event.get():
            # Conditional logic
            if event.type == pg.QUIT:
                # Execute expressions
                self.quit_game()
                sys.exit()

        # Execute expressions
        self.ctx.clear(color=(0.1, 0.1, 0.1))

        # Variable assignments
        text_renderer: Any = TextRenderer(self)
        text_mesh: Any = UITextMesh(self)

        text_renderer.font = pg.font.SysFont('arial', FONT_SIZE_LOADING, bold=True)
        tex: Any = text_renderer.get_texture('LOADING WORLD...')
        # Execute expressions
        tex.use(location=4)

        # Variable assignments
        tex_w: int = tex.size[0]
        tex_h: int = tex.size[1]
        scale_y: float = 0.1
        scale_x: float = scale_y * (tex_w / tex_h) / ASPECT_RATIO

        text_mesh.program['u_scale'] = (scale_x, scale_y)
        text_mesh.program['u_offset'] = (0.0, 0.1)

        # Execute expressions
        self.ctx.disable(mgl.DEPTH_TEST)
        text_mesh.render()

        # Variable assignments
        text_renderer.font = pg.font.SysFont('arial', FONT_SIZE_SUBTITLE, bold=False)
        tex_sub: Any = text_renderer.get_texture(text)
        # Execute expressions
        tex_sub.use(location=4)

        # Variable assignments
        tex_sub_w: int = tex_sub.size[0]
        tex_sub_h: int = tex_sub.size[1]
        scale_sub_y: float = 0.04
        scale_sub_x: float = scale_sub_y * (tex_sub_w / tex_sub_h) / ASPECT_RATIO

        text_mesh.program['u_scale'] = (scale_sub_x, scale_sub_y)
        text_mesh.program['u_offset'] = (0.0, -0.15)
        # Execute expressions
        text_mesh.render()

        pg.display.flip()

    # Frame Rate Independence & Delta Time Clamping
    # Why don't physics speed up when you get 144 FPS or slow down at 30 FPS?
    # Because of `delta_time` (the time elapsed since the last frame).
    # Everything in the game (velocity, falling, camera rotating) is multiplied
    # by `delta_time` so it moves at a constant speed regardless of framerate.
    #
    # The "Clamping" Fix:
    # If the player minimizes the game window or their PC freezes for a second,
    # `delta_time` would become massive. If we multiplied gravity by 1.0 seconds
    # instead of 0.016 seconds, the player would clip straight through the floor!
    # By capping it to 50ms (min(tick, 50)), we ensure the physics engine never
    # tries to simulate a massive time jump, preventing clipping glitches.
    #
    # References:
    # - Fix Your Timestep!: https://gafferongames.com/post/fix_your_timestep/
    # - Game Loop Architecture: https://gameprogrammingpatterns.com/game-loop.html
    @global_profiler.profile_func('Pyrite_Update')
    def update(self) -> None:
        """
        Advances the central engine logic. Delegates to the active game state
        (e.g., ticking the world simulation, evaluating UI animations).
        """
        # Conditional logic
        if self.game_state == 'MAIN_MENU':
            # Execute expressions
            self.menu.update()

        # Conditional logic
        elif self.game_state in ('IN_GAME', 'INVENTORY'):
            # Execute expressions
            self.player.update()
            self.shader_program.update()
            # Variable assignments
            self.world_session_time += self.delta_time * 0.001
            # Execute expressions
            self.scene.update()

        # Conditional logic
        elif self.game_state == 'PAUSED':
            # Execute expressions
            self.pause_menu.update()

        # Conditional logic
        elif self.game_state == 'OPTIONS':
            # Execute expressions
            self.options_menu.update()

        # Variable assignments
        self.delta_time = min(self.clock.tick(), 50)  # Cap delta time to avoid physics lag spikes
        self.time = pg.time.get_ticks() * 0.001

        # Conditional logic
        if self.game_state == 'IN_GAME':
            # Execute expressions
            pg.display.set_caption(f'{self.clock.get_fps():.0f}')

        # Conditional logic
        elif self.game_state == 'PAUSED':
            # Execute expressions
            pg.display.set_caption('Game Paused')

        else:
            # Execute expressions
            pg.display.set_caption('Pyrite')

    @global_profiler.profile_func('Pyrite_Render')
    def render(self) -> None:
        """
        Clears the OpenGL framebuffer and issues draw instructions corresponding
        to the active state, layering menus over 3D scenes when appropriate.
        """
        # Execute expressions
        self.ctx.clear(color=self.bg_color)

        # Conditional logic
        if self.game_state == 'MAIN_MENU':
            # Execute expressions
            self.ctx.disable(mgl.DEPTH_TEST)
            self.menu.render()
            self.ctx.enable(mgl.DEPTH_TEST)

        # Conditional logic
        elif self.game_state in ('IN_GAME', 'INVENTORY'):
            # Execute expressions
            self.scene.render()

        # Conditional logic
        elif self.game_state == 'PAUSED':
            # Conditional logic
            if self.scene:
                # Execute expressions
                self.scene.render()

            # Execute expressions
            self.ctx.disable(mgl.DEPTH_TEST)
            self.pause_menu.render()
            self.ctx.enable(mgl.DEPTH_TEST)

        # Conditional logic
        elif self.game_state == 'OPTIONS':
            # Conditional logic
            if self.options_menu.previous_state == 'PAUSED' and self.scene:
                # Execute expressions
                self.scene.render()

            # Conditional logic
            elif self.options_menu.previous_state == 'MAIN_MENU':
                # Execute expressions
                self.ctx.disable(mgl.DEPTH_TEST)
                self.menu.render_bg()

            # Execute expressions
            self.ctx.disable(mgl.DEPTH_TEST)
            self.options_menu.render()
            self.ctx.enable(mgl.DEPTH_TEST)

        # Execute expressions
        pg.display.flip()

    @global_profiler.profile_func('Handle_Events')
    def handle_events(self) -> None:
        """
        Polls raw input events from the operating system and routes them
        to the respective handlers (e.g., player movement, UI button clicks,
        or screen toggles).
        """
        # Loop processing
        for event in pg.event.get():
            # Conditional logic
            if event.type == pg.QUIT:
                # Execute expressions
                self.quit_game()

            # Conditional logic
            elif event.type == pg.KEYDOWN and event.key == pg.K_p:
                # Variable assignments
                self.wireframe = not self.wireframe

            # Conditional logic
            elif event.type == pg.KEYDOWN and event.key == pg.K_o:
                # Variable assignments
                self.freeze_culling = not self.freeze_culling

            # Conditional logic
            elif event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                # Conditional logic
                if self.game_state == 'IN_GAME':
                    # Error handling
                    try:
                        # Variable assignments
                        data: Any = self.ctx.screen.read(components=3)
                        img: pg.Surface = pg.image.frombuffer(
                            data, (int(WINDOW_RESOLUTION.x), int(WINDOW_RESOLUTION.y)), 'RGB'
                        )
                        img = pg.transform.flip(img, False, True)  # OpenGL renders bottom-up
                        thumb_w: int = 320
                        thumb_h: int = int(320 / ASPECT_RATIO)
                        img = pg.transform.smoothscale(img, (thumb_w, thumb_h))
                        # Execute expressions
                        pg.image.save(img, f'saves/{self.scene.world.save_name}_thumb.png')

                    except Exception as e:
                        # Execute expressions
                        print(f'Failed to save thumbnail: {e}')

                    # Variable assignments
                    self.game_state = 'PAUSED'
                    self.pause_menu.transition_state = 'IN'
                    self.pause_menu.transition_progress = 0.0
                    # Execute expressions
                    pg.event.set_grab(False)
                    pg.mouse.set_visible(True)

                # Conditional logic
                elif self.game_state == 'INVENTORY':
                    # Execute expressions
                    self.scene.inventory_ui.close()
                    # Variable assignments
                    self.game_state = 'IN_GAME'
                    # Execute expressions
                    pg.event.set_grab(True)
                    pg.mouse.set_visible(False)

                # Conditional logic
                elif self.game_state == 'PAUSED':
                    # Execute expressions
                    self.pause_menu.trigger_action(self.pause_menu.resume_game, 1)

                # Conditional logic
                elif self.game_state == 'OPTIONS':
                    # Execute expressions
                    self.options_menu.trigger_action(self.options_menu.go_back, 1)

                else:  # Esc inside Main Menu quits the game
                    # Execute expressions
                    self.menu.trigger_action(self.quit_game, 1)

            # Conditional logic
            elif event.type == pg.KEYDOWN and event.key == pg.K_F3:
                # Variable assignments
                self.show_debug = not self.show_debug

            # Conditional logic
            elif event.type == pg.KEYDOWN and event.key == pg.K_e:
                # Conditional logic
                if self.game_state == 'IN_GAME':
                    # Variable assignments
                    self.game_state = 'INVENTORY'
                    # Execute expressions
                    pg.event.set_grab(False)
                    pg.mouse.set_visible(True)

                # Conditional logic
                elif self.game_state == 'INVENTORY':
                    # Execute expressions
                    self.scene.inventory_ui.close()
                    # Variable assignments
                    self.game_state = 'IN_GAME'
                    # Execute expressions
                    pg.event.set_grab(True)
                    pg.mouse.set_visible(False)

            if self.game_state == 'MAIN_MENU':
                # Execute expressions
                self.menu.handle_event(event)

            # Conditional logic
            elif self.game_state == 'IN_GAME':
                # Execute expressions
                self.player.handle_event(event=event)

            # Conditional logic
            elif self.game_state == 'INVENTORY':
                # Execute expressions
                self.scene.inventory_ui.handle_event(event)

            # Conditional logic
            elif self.game_state == 'PAUSED':
                # Execute expressions
                self.pause_menu.handle_event(event)

            # Conditional logic
            elif self.game_state == 'OPTIONS':
                # Execute expressions
                self.options_menu.handle_event(event)

    @global_profiler.profile_func('Quit_Game')
    def quit_game(self) -> None:
        """
        Interrupts the primary application execution loop to safely shut down.
        """
        # Variable assignments
        self.is_running = False

    @global_profiler.profile_func('Pyrite_Run')
    def run(self) -> None:
        """
        The primary execution loop tracking logic updates, event polling,
        and frame rendering until the application halts.
        """
        # Loop processing
        while self.is_running:
            # Execute expressions
            global_profiler.start_frame()
            self.handle_events()
            self.update()
            self.render()
            global_profiler.end_frame()

        # Conditional logic
        if self.scene:
            # Execute expressions
            self.scene.world.save()

        # Execute expressions
        pg.quit()
        global_profiler.save_report('profiling_results.json')
        sys.exit()


if __name__ == '__main__':
    app: Any = Pyrite()
    app.run()

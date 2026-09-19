"""
Main scene graph and render pipeline coordinator.

This module defines the `Scene` class which acts as the primary game session container.
It instantiates and manages the world environment, 3D items, UI components,
and handles the overarching rendering pipeline for the in-game state.
"""

from typing import Any

import moderngl as mgl

from profiler import global_profiler
from ui.hud import Crosshair, DebugOverlay, HeldBlock, Hotbar, InventoryUI
from world import World
from world_objects.clouds import Clouds
from world_objects.item import ItemManager
from world_objects.sky import Sky
from world_objects.voxel_marker import VoxelMarker


class Scene:
    """
    Acts as the primary game session container.

    Instantiates and manages the world environment, 3D items, UI components,
    and handles the overarching rendering pipeline for the in-game state.

    Args:
        app (Any): The main application context.
        save_name (str): The filename/identifier for the world SQLite database.
        seed (int): The deterministic seed for world generation.
    """

    @global_profiler.profile_func('Scene_Init')
    def __init__(self, app: Any, save_name: str, seed: int) -> None:
        """
        Initializes the scene components, including the terrain world,
        environment decorations (clouds/sky), 3D item entities, and HUD interfaces.
        """
        self.app: Any = app
        self.world: Any = World(self.app, save_name, seed)
        self.app.render_loading_screen('INITIALIZING MARKERS...')
        self.voxel_marker: Any = VoxelMarker(self.world.voxel_handler)
        self.app.render_loading_screen('INITIALIZING ENVIRONMENT...')
        self.clouds: Any = Clouds(app)
        self.sky: Any = Sky(app)
        self.app.render_loading_screen('INITIALIZING UI...')
        self.crosshair: Any = Crosshair(app)
        self.hotbar: Any = Hotbar(app)
        self.inventory_ui: Any = InventoryUI(app)
        self.held_block: Any = HeldBlock(app)
        self.item_manager: Any = ItemManager(app)
        self.debug_overlay: Any = DebugOverlay(app)

        # Restore saved dropped items from the database
        for item_data in self.world.saved_dropped_items:
            self.item_manager.load_item(*item_data)

    @global_profiler.profile_func('Scene_Update')
    def update(self) -> None:
        """
        Ticks the overarching logic of the scene, progressing the world state,
        updating environmental visuals, and tracking physics for active items.
        """
        self.world.update()
        self.voxel_marker.update()
        self.clouds.update()
        self.item_manager.update()

    @global_profiler.profile_func('Scene_Render')
    def render(self) -> None:
        """
        Executes the multi-pass rendering pipeline.
        Draws the skybox, opaque chunks, entities, transparent layers (water/clouds), and UI.
        """
        if self.app.wireframe:
            self.app.ctx.wireframe = True

        # Skybox pass
        # The skybox is drawn first without any depth testing constraints.
        # It sits firmly in the background at the maximum depth of 1.0.
        self.sky.render()

        # Opaque Solid Pass
        # We explicitly ENABLE face culling (CULL_FACE).
        # This tells OpenGL to throw away any triangles facing away from the camera.
        # If we are looking at the outside of a cube, the 3 back faces are instantly culled
        # mathematically before rasterization, saving 50% of our fragment shader cost!
        self.app.ctx.enable(mgl.CULL_FACE)

        # Draw all opaque chunks and entities. These will write to the depth buffer.
        self.world.render()
        self.item_manager.render()

        # Transparent Cloud Pass
        # We explicitly DISABLE face culling here.
        # Clouds are mathematically 2D planes hovering in the sky. If we culled back-faces, 
        # the clouds would suddenly turn completely invisible if we flew above them and looked down!
        self.app.ctx.disable(mgl.CULL_FACE)
        self.clouds.render()

        # Transparent Water Pass
        # We RE-ENABLE face culling for water. 
        # Water blocks are full 3D cubes. If we didn't cull back-faces, the semi-transparent 
        # blending equation would draw the bottom of the water block *through* the top surface, 
        # making it look like a weird double-layered box instead of a solid volume of liquid.
        self.app.ctx.enable(mgl.CULL_FACE)
        self.world.render_water()

        if self.app.wireframe:
            self.app.ctx.wireframe = False

        # Voxel Selection Marker (Draws over everything else)
        self.voxel_marker.render()

        # View Model (Held Block)
        self.held_block.render()

        # UI rendering (disable depth testing so it draws over everything)
        self.app.ctx.disable(mgl.DEPTH_TEST)

        if self.app.game_state == 'IN_GAME':
            self.crosshair.render()
            self.hotbar.render()

        elif self.app.game_state == 'INVENTORY':
            self.inventory_ui.render()

        if getattr(self.app, 'show_debug', False):
            self.debug_overlay.render()

        self.app.ctx.enable(mgl.DEPTH_TEST)

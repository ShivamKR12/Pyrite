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
        # Variable assignments
        self.app: Any = app
        self.world: Any = World(self.app, save_name, seed)
        # Execute expressions
        self.app.render_loading_screen('INITIALIZING MARKERS...')
        # Variable assignments
        self.voxel_marker: Any = VoxelMarker(self.world.voxel_handler)
        # Execute expressions
        self.app.render_loading_screen('INITIALIZING ENVIRONMENT...')
        # Variable assignments
        self.clouds: Any = Clouds(app)
        self.sky: Any = Sky(app)
        # Execute expressions
        self.app.render_loading_screen('INITIALIZING UI...')
        # Variable assignments
        self.crosshair: Any = Crosshair(app)
        self.hotbar: Any = Hotbar(app)
        self.inventory_ui: Any = InventoryUI(app)
        self.held_block: Any = HeldBlock(app)
        self.item_manager: Any = ItemManager(app)
        self.debug_overlay: Any = DebugOverlay(app)

        # Loop processing
        for item_data in self.world.saved_dropped_items:
            # Execute expressions
            self.item_manager.load_item(*item_data)

    @global_profiler.profile_func('Scene_Update')
    def update(self) -> None:
        """
        Ticks the overarching logic of the scene, progressing the world state,
        updating environmental visuals, and tracking physics for active items.
        """
        # Execute expressions
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
        # Conditional logic
        if self.app.wireframe:
            # Variable assignments
            self.app.ctx.wireframe = True

        # Execute expressions
        self.sky.render()

        self.app.ctx.enable(mgl.CULL_FACE)

        self.world.render()
        self.item_manager.render()

        self.app.ctx.disable(mgl.CULL_FACE)
        self.clouds.render()

        self.app.ctx.enable(mgl.CULL_FACE)
        self.world.render_water()

        # Conditional logic
        if self.app.wireframe:
            # Variable assignments
            self.app.ctx.wireframe = False

        # Execute expressions
        self.voxel_marker.render()

        self.held_block.render()

        self.app.ctx.disable(mgl.DEPTH_TEST)

        # Conditional logic
        if self.app.game_state == 'IN_GAME':
            # Execute expressions
            self.crosshair.render()
            self.hotbar.render()

        # Conditional logic
        elif self.app.game_state == 'INVENTORY':
            # Execute expressions
            self.inventory_ui.render()

        if getattr(self.app, 'show_debug', False):
            # Execute expressions
            self.debug_overlay.render()

        # Execute expressions
        self.app.ctx.enable(mgl.DEPTH_TEST)

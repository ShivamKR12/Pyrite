"""
Main scene graph and render pipeline coordinator.

This module defines the `Scene` class which acts as the primary game session container.
It instantiates and manages the world environment, 3D items, UI components,
and handles the overarching rendering pipeline for the in-game state.
"""

import moderngl as mgl
from typing import Any

from world import World
from world_objects.voxel_marker import VoxelMarker
from world_objects.clouds import Clouds
from world_objects.sky import Sky
from ui import Crosshair
from ui import Hotbar
from ui import HeldBlock
from ui import InventoryUI
from ui import DebugOverlay
from world_objects.item import ItemManager
from profiler import global_profiler


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
    @global_profiler.profile_func("Scene_Init")
    def __init__(self, app: Any, save_name: str, seed: int) -> None:
        """
        Initializes the scene components, including the terrain world,
        environment decorations (clouds/sky), 3D item entities, and HUD interfaces.
        """
        self.app: Any = app
        self.world: Any = World(self.app, save_name, seed)
        self.app.render_loading_screen("INITIALIZING MARKERS...")
        self.voxel_marker: Any = VoxelMarker(self.world.voxel_handler)
        self.app.render_loading_screen("INITIALIZING ENVIRONMENT...")
        self.clouds: Any = Clouds(app)
        self.sky: Any = Sky(app)
        self.app.render_loading_screen("INITIALIZING UI...")
        self.crosshair: Any = Crosshair(app)
        self.hotbar: Any = Hotbar(app)
        self.inventory_ui: Any = InventoryUI(app)
        self.held_block: Any = HeldBlock(app)
        self.item_manager: Any = ItemManager(app)
        self.debug_overlay: Any = DebugOverlay(app)
        
        # Restore saved dropped items from the database
        for item_data in self.world.saved_dropped_items:
            self.item_manager.load_item(*item_data)

    @global_profiler.profile_func("Scene_Update")
    def update(self) -> None:
        """
        Ticks the overarching logic of the scene, progressing the world state,
        updating environmental visuals, and tracking physics for active items.
        """
        self.world.update()
        self.voxel_marker.update()
        self.clouds.update()
        self.item_manager.update()

    @global_profiler.profile_func("Scene_Render")
    def render(self) -> None:
        """
        Executes the multi-pass rendering pipeline.
        Draws the skybox, opaque chunks, entities, transparent layers (water/clouds), and UI.
        """
        if self.app.wireframe:
            self.app.ctx.wireframe = True
        
        # skybox rendering FIRST, entirely in the background
        self.sky.render()

        # Disable face culling so we can see the inside of glass and leaves!
        self.app.ctx.enable(mgl.CULL_FACE)

        # chunks rendering
        self.world.render()
        self.item_manager.render()

        # rendering without cull face
        self.app.ctx.disable(mgl.CULL_FACE)
        self.clouds.render()
        
        # Enable face-culling and blend mode to draw semi-transparent water chunks cleanly!
        self.app.ctx.enable(mgl.CULL_FACE)
        self.world.render_water()
        
        if self.app.wireframe:
            self.app.ctx.wireframe = False

        # voxel selection
        self.voxel_marker.render()
        
        # view model (held block)
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

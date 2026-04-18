from settings import *
import moderngl as mgl
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
from meshes.cube_mesh import CubeMesh


class Scene:
    def __init__(self, app, save_name):
        self.app = app
        self.world = World(self.app, save_name)
        self.app.render_loading_screen("INITIALIZING MARKERS...")
        self.voxel_marker = VoxelMarker(self.world.voxel_handler)
        self.app.render_loading_screen("INITIALIZING ENVIRONMENT...")
        self.clouds = Clouds(app)
        self.sky = Sky(app)
        self.app.render_loading_screen("INITIALIZING UI...")
        self.crosshair = Crosshair(app)
        self.hotbar = Hotbar(app)
        self.inventory_ui = InventoryUI(app)
        self.held_block = HeldBlock(app)
        self.item_manager = ItemManager(app)
        self.debug_overlay = DebugOverlay(app)

    def update(self):
        self.world.update()
        self.voxel_marker.update()
        self.clouds.update()
        self.item_manager.update()

    def render(self):
        if self.app.wireframe:
            self.app.ctx.wireframe = True
        
        # skybox rendering FIRST, entirely in the background
        self.sky.render()

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

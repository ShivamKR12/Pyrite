from settings import *
import moderngl as mgl
from world import World
from world_objects.voxel_marker import VoxelMarker
from world_objects.water import Water
from world_objects.clouds import Clouds
from ui import Crosshair
from ui import Hotbar
from world_objects.item import ItemManager


class Scene:
    def __init__(self, app):
        self.app = app
        self.world = World(self.app)
        self.voxel_marker = VoxelMarker(self.world.voxel_handler)
        self.water = Water(app)
        self.clouds = Clouds(app)
        self.crosshair = Crosshair(app)
        self.hotbar = Hotbar(app)
        self.item_manager = ItemManager(app)

    def update(self):
        self.world.update()
        self.voxel_marker.update()
        self.clouds.update()
        self.item_manager.update()

    def render(self):
        # chunks rendering
        self.world.render()
        self.item_manager.render()

        # rendering without cull face
        self.app.ctx.disable(mgl.CULL_FACE)
        self.clouds.render()
        self.water.render()
        self.app.ctx.enable(mgl.CULL_FACE)

        # voxel selection
        self.voxel_marker.render()
        
        # UI rendering (disable depth testing so it draws over everything)
        self.app.ctx.disable(mgl.DEPTH_TEST)
        self.crosshair.render()
        self.hotbar.render()
        self.app.ctx.enable(mgl.DEPTH_TEST)

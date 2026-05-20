import random
import pygame as pg
from settings import *
from pyglm import glm
from meshes.item_mesh import ItemMesh
from meshes.obj_mesh import ObjMesh


class Item:
    """
    Represents a physical, dropped 3D item entity in the world.
    Handles gravity, sliding friction, bouncing, and player pickup detection.
    """
    def __init__(self, app, position, voxel_id):
        """
        Spawns an item bursting out of the specified position with a randomized velocity,
        and applies a short pickup delay to prevent instant re-collection.
        """
        self.app = app
        self.position = glm.vec3(position) + 0.5 # Burst from the center of the block
        self.velocity = glm.vec3((random.random() - 0.5) * ITEM_SPAWN_VELOCITY_MULTIPLIER, 0.005, (random.random() - 0.5) * ITEM_SPAWN_VELOCITY_MULTIPLIER)
        self.voxel_id = voxel_id
        self.rotation = 0.0
        self.scale = ITEM_SCALE
        self.is_dead = False
        self.pickup_delay = pg.time.get_ticks() + ITEM_PICKUP_DELAY

    def update(self):
        """
        Applies continuous gravity and velocity updates, handles simple ground collisions,
        and destroys the item if it falls into the void or is collected by the player.
        """
        self.velocity.y += GRAVITY * self.app.delta_time
        self.position += self.velocity * self.app.delta_time
        
        world = self.app.scene.world
        check_pos = glm.ivec3(self.position.x, self.position.y - self.scale / 2, self.position.z)
        
        if world.voxel_handler.get_voxel_id(check_pos)[0]:
            self.position.y = check_pos.y + 1.0 + self.scale / 2
            self.velocity.x *= 0.8 # Friction
            self.velocity.z *= 0.8 
            self.velocity.y = 0
        
        elif self.position.y < -10:
            self.is_dead = True
            
        self.rotation += 0.003 * self.app.delta_time
        
        if pg.time.get_ticks() > self.pickup_delay:
            if glm.distance(self.position, self.app.player.position) < ITEM_PICKUP_RADIUS:
               
                if self.app.player.add_item(self.voxel_id):
                    self.is_dead = True
                    self.app.sounds.play_place_block() # Pop sound!

    def get_model_matrix(self):
        """
        Returns the transformation matrix required to position, rotate, and scale 
        the 3D item for rendering.
        """
        m_model = glm.translate(glm.mat4(), self.position)
        m_model = glm.rotate(m_model, self.rotation, glm.vec3(0, 1, 0))
        
        return glm.scale(m_model, glm.vec3(self.scale))


class ItemManager:
    """
    Manages all active Item entities in the scene.
    Handles updating physics, rendering, and enforcing an entity cap to prevent lag.
    """
    def __init__(self, app):
        """
        Initializes the item list and pre-loads the meshes required to render 
        blocks and 3D models like pickaxes or sticks.
        """
        self.app = app
        self.items = []
        self.mesh = ItemMesh(app)
        self.stick_mesh = ObjMesh(app, get_path('assets/stick/stick.obj'))
        self.pickaxe_mesh = ObjMesh(app, get_path('assets/wooden_pickaxe/wooden_pickaxe.obj'))

    def add_item(self, position, voxel_id):
        """
        Spawns a new item entity into the world. Enforces a First-In-First-Out (FIFO) 
        limit to automatically despawn old items if too many are active at once.
        """
        # Prevent entity overflow crashes if too many blocks break at once
        if len(self.items) > ITEM_ENTITY_CAP:
            self.items.pop(0) # Automatically despawn the oldest item
        
        self.items.append(Item(self.app, position, voxel_id))

    def load_item(self, voxel_id, px, py, pz, vx, vy, vz):
        """
        Restores a previously saved item entity into the world with its exact 
        former position and velocity to bypass the random spawn burst.
        """
        if len(self.items) > ITEM_ENTITY_CAP:
            self.items.pop(0)
        
        item = Item(self.app, (0, 0, 0), voxel_id)
        item.position = glm.vec3(px, py, pz)
        item.velocity = glm.vec3(vx, vy, vz)
        self.items.append(item)

    def update(self):
        """
        Updates physics for all active items and removes ones marked as dead.
        """
        for item in self.items:
            item.update()
        
        self.items = [item for item in self.items if not item.is_dead]

    def render(self):
        """
        Renders all items that fall within the specific item render distance.
        """
        self.app.ctx.disable(self.app.ctx.CULL_FACE) # Don't cull rotating cubes
        
        player_pos = self.app.player.position
        for item in self.items:
            # Simple distance culling (don't render items further than 32 blocks away)
            if glm.distance2(item.position, player_pos) > ITEM_RENDER_DISTANCE_SQUARED:
                continue
             
            if item.voxel_id == STICK:
                mesh = self.stick_mesh
            
            elif item.voxel_id == WOODEN_PICKAXE:
                mesh = self.pickaxe_mesh
            
            else:
                mesh = self.mesh
             
            mesh.program['m_model'].write(item.get_model_matrix())
            
            if 'voxel_id' in mesh.program:
                mesh.program['voxel_id'] = item.voxel_id
            
            mesh.render()

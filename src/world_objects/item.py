"""
Physical dropped item entity management.

This module manages the instantiation, 3D physics, collision handling, and rendering of
items that pop out of broken blocks. The `ItemManager` utilizes a strict First-In-First-Out
(FIFO) cap to forcefully limit active entities, guaranteeing smooth framerates regardless of
how many blocks are exploded concurrently.
"""

import random
from typing import Any, List

import pygame as pg
from pyglm import glm

from meshes.item_mesh import ItemMesh
from meshes.obj_mesh import ObjMesh
from profiler import global_profiler
from settings import (
    GRAVITY,
    ITEM_ENTITY_CAP,
    ITEM_PICKUP_DELAY,
    ITEM_PICKUP_RADIUS,
    ITEM_RENDER_DISTANCE_SQUARED,
    ITEM_SCALE,
    ITEM_SPAWN_VELOCITY_MULTIPLIER,
    STICK,
    WOODEN_PICKAXE,
    get_path,
)


class Item:
    """
    Represents a physical, dropped 3D item entity in the world.

    Handles gravity, sliding friction, bouncing, and player pickup detection.
    Items are spawned when blocks are broken or when dropped from the inventory.

    Args:
        app (Any): The main application instance.
        position (Any): A PyGLM vec3 or tuple representing the initial world spawn coordinates.
        voxel_id (int): The block or item UID that dictates its visual mesh and inventory value.
    """

    @global_profiler.profile_func('Item_Init')
    def __init__(self, app: Any, position: Any, voxel_id: int) -> None:
        """
        Spawns an item bursting out of the specified position with a randomized velocity,
        and applies a short pickup delay to prevent instant re-collection.
        """
        self.app: Any = app
        self.position: Any = glm.vec3(position) + 0.5  # Burst from the center of the block
        self.velocity: Any = glm.vec3(
            (random.random() - 0.5) * ITEM_SPAWN_VELOCITY_MULTIPLIER,
            0.005,
            (random.random() - 0.5) * ITEM_SPAWN_VELOCITY_MULTIPLIER,
        )
        self.voxel_id: int = voxel_id
        self.rotation: float = 0.0
        self.scale: float = ITEM_SCALE
        self.is_dead: bool = False
        self.pickup_delay: int = pg.time.get_ticks() + ITEM_PICKUP_DELAY

    @global_profiler.profile_func('Item_Update')
    def update(self) -> None:
        """
        Applies continuous gravity and velocity updates, handles simple ground collisions,
        and destroys the item if it falls into the void or is collected by the player.
        """
        self.velocity.y += GRAVITY * self.app.delta_time
        self.position += self.velocity * self.app.delta_time

        world: Any = self.app.scene.world
        check_pos: Any = glm.ivec3(self.position.x, self.position.y - self.scale / 2, self.position.z)

        if world.voxel_handler.get_voxel_id(check_pos)[0]:
            self.position.y = check_pos.y + 1.0 + self.scale / 2
            self.velocity.x *= 0.8  # Friction
            self.velocity.z *= 0.8
            self.velocity.y = 0

        elif self.position.y < -10:
            self.is_dead = True

        self.rotation += 0.003 * self.app.delta_time

        if pg.time.get_ticks() > self.pickup_delay:
            if glm.distance(self.position, self.app.player.position) < ITEM_PICKUP_RADIUS:
                if self.app.player.add_item(self.voxel_id):
                    self.is_dead = True
                    self.app.sounds.play_place_block()  # Pop sound!

    @global_profiler.profile_func('Item_GetModelMatrix')
    def get_model_matrix(self) -> Any:
        """
        Returns the transformation matrix required to position, rotate, and scale
        the 3D item for rendering.
        """
        m_model: Any = glm.translate(glm.mat4(), self.position)
        m_model = glm.rotate(m_model, self.rotation, glm.vec3(0, 1, 0))

        return glm.scale(m_model, glm.vec3(self.scale))


class ItemManager:
    """
    Manages all active Item entities in the scene.

    Handles updating physics, batched rendering, and enforcing an entity cap
    to prevent performance degradation from extreme item quantities.

    Args:
        app (Any): The main application instance.
    """

    @global_profiler.profile_func('ItemManager_Init')
    def __init__(self, app: Any) -> None:
        """
        Initializes the item list and pre-loads the meshes required to render
        blocks and 3D models like pickaxes or sticks.
        """
        self.app: Any = app
        self.items: List[Item] = []
        self.mesh: Any = ItemMesh(app)
        self.stick_mesh: Any = ObjMesh(app, get_path('assets/models/items/stick/stick.obj'))
        self.pickaxe_mesh: Any = ObjMesh(app, get_path('assets/models/items/wooden-pickaxe/wooden_pickaxe.obj'))

    @global_profiler.profile_func('ItemManager_AddItem')
    def add_item(self, position: Any, voxel_id: int) -> None:
        """
        Spawns a new item entity into the world. Enforces a First-In-First-Out (FIFO)
        limit to automatically despawn old items if too many are active at once.
        """
        # Prevent entity overflow crashes if too many blocks break at once
        if len(self.items) > ITEM_ENTITY_CAP:
            self.items.pop(0)  # Automatically despawn the oldest item

        self.items.append(Item(self.app, position, voxel_id))

    @global_profiler.profile_func('ItemManager_LoadItem')
    def load_item(self, voxel_id: int, px: float, py: float, pz: float, vx: float, vy: float, vz: float) -> None:
        """
        Restores a previously saved item entity into the world with its exact
        former position and velocity to bypass the random spawn burst.
        """
        if len(self.items) > ITEM_ENTITY_CAP:
            self.items.pop(0)

        item: Item = Item(self.app, (0, 0, 0), voxel_id)
        item.position = glm.vec3(px, py, pz)
        item.velocity = glm.vec3(vx, vy, vz)
        self.items.append(item)

    @global_profiler.profile_func('ItemManager_Update')
    def update(self) -> None:
        """
        Updates physics for all active items and removes ones marked as dead.
        """
        for item in self.items:
            item.update()

        self.items = [item for item in self.items if not item.is_dead]

    @global_profiler.profile_func('ItemManager_Render')
    def render(self) -> None:
        """
        Renders all items that fall within the specific item render distance.
        """
        self.app.ctx.disable(self.app.ctx.CULL_FACE)  # Don't cull rotating cubes

        player_pos: Any = self.app.player.position
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

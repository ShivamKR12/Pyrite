"""
Physical dropped item entity management.

This module manages the instantiation, 3D physics, collision handling, and rendering of
items that pop out of broken blocks. The `ItemManager` utilizes a strict First-In-First-Out
(FIFO) cap to forcefully limit active entities, guaranteeing smooth framerates regardless of
how many blocks are exploded concurrently.
"""

import math
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
    def __init__(self, app: Any, position: Any, voxel_id: Any) -> None:
        """
        Spawns an item bursting out of the specified position with a randomized velocity,
        and applies a short pickup delay to prevent instant re-collection.
        """
        # Store a reference to the main application instance to access global state
        self.app: Any = app

        # Offset the initial spawn position by 0.5 on all axes to center it within the broken block's coordinate space
        self.position: Any = glm.vec3(position) + 0.5

        # Generate a randomized ejection velocity to make the item burst outwards
        # X and Z axes get a random spread, while Y gets a slight upward bump
        self.velocity: Any = glm.vec3(
            (random.random() - 0.5) * ITEM_SPAWN_VELOCITY_MULTIPLIER,
            0.005,
            (random.random() - 0.5) * ITEM_SPAWN_VELOCITY_MULTIPLIER,
        )

        # Handle type conversion for voxel_id, which may come in as raw bytes from the SQLite database
        self.voxel_id: int = int.from_bytes(voxel_id, 'little') if isinstance(voxel_id, bytes) else int(voxel_id)

        # Initialize the baseline Y-axis rotation (yaw) for the item's spinning animation
        self.rotation: float = 0.0

        # Set the global scaling factor for how large dropped items appear in the world
        self.scale: float = ITEM_SCALE

        # Flag to track whether this item should be garbage collected (e.g., if picked up or fallen into the void)
        self.is_dead: bool = False

        # Calculate the absolute timestamp (in milliseconds) when this item becomes eligible for pickup
        self.pickup_delay: int = pg.time.get_ticks() + ITEM_PICKUP_DELAY

    @global_profiler.profile_func('Item_Update')
    def update(self) -> None:
        """
        Applies continuous gravity and velocity updates, handles simple ground collisions,
        and destroys the item if it falls into the void or is collected by the player.
        """
        # Apply gravitational acceleration downwards, scaled by the time since the last frame
        self.velocity.y += GRAVITY * self.app.delta_time

        # Integrate the velocity vector into the current position to move the item through space
        self.position += self.velocity * self.app.delta_time

        # Retrieve a reference to the world state to check for block collisions
        world: Any = self.app.scene.world

        # Calculate the integer coordinate directly below the item to check if it has hit the floor
        check_pos: Any = glm.ivec3(self.position.x, self.position.y - self.scale / 2, self.position.z)

        # Query the voxel handler to see if the block at check_pos is solid (non-zero ID)
        if world.voxel_handler.get_voxel_id(check_pos)[0]:
            # If a collision is detected, snap the item's Y position to rest precisely on top of the block surface
            self.position.y = check_pos.y + 1.0 + self.scale / 2

            # Apply a harsh dampening factor (friction) to the X and Z velocities so the item stops sliding
            self.velocity.x *= 0.8
            self.velocity.z *= 0.8

            # Nullify the vertical velocity completely since it is now resting on the ground
            self.velocity.y = 0

        # Check if the item has fallen below the world boundary (-10 Y) and mark it for deletion
        elif self.position.y < -10:
            self.is_dead = True

        # Increment the item's yaw rotation continuously based on elapsed time to create a spinning effect
        self.rotation += 0.003 * self.app.delta_time

        # Ensure the mandatory pickup cooldown period has elapsed before checking for player collision
        if pg.time.get_ticks() > self.pickup_delay:
            # Calculate the Euclidean distance between the item's center and the player's center
            if glm.distance(self.position, self.app.player.position) < ITEM_PICKUP_RADIUS:
                # Attempt to add the item's voxel ID to the player's inventory
                if self.app.player.add_item(self.voxel_id):
                    # If the inventory accepted the item, mark this entity for destruction
                    self.is_dead = True
                    # Trigger the auditory feedback for a successful item pickup
                    self.app.sounds.play_place_block()

    @global_profiler.profile_func('Item_GetModelMatrix')
    def get_model_matrix(self) -> Any:
        """
        Returns the transformation matrix required to position, rotate, and scale
        the 3D item for rendering.
        """
        # Calculate a time-based bobbing offset using a continuous sine wave based on the system clock
        # This provides the classic 3D hovering/floating effect for dropped items
        bobbing_offset = math.sin(pg.time.get_ticks() * 0.003) * 0.1

        # Apply the computed bobbing offset to the item's absolute Y position
        bob_pos = glm.vec3(self.position.x, self.position.y + bobbing_offset, self.position.z)

        # Initialize a 4x4 identity matrix and apply a translation transformation to move the model to its world coordinates
        m_model: Any = glm.translate(glm.mat4(), bob_pos)

        # Apply a rotational transformation around the global Y-axis (up vector) using the accumulated rotation angle
        m_model = glm.rotate(m_model, self.rotation, glm.vec3(0, 1, 0))

        # Finally, apply a uniform scaling transformation to shrink the model to the defined ITEM_SCALE size
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
        # Retain the application context
        self.app: Any = app

        # Initialize an empty list that will act as the live entity pool for all dropped items
        self.items: List[Item] = []

        # Instantiate the generic cubic mesh used for standard voxel block drops
        self.mesh: Any = ItemMesh(app)

        # Load the custom 3D Wavefront (.obj) model specifically for the stick item
        self.stick_mesh: Any = ObjMesh(app, get_path('assets/models/items/stick/stick.obj'))

        # Load the custom 3D Wavefront (.obj) model specifically for the wooden pickaxe item
        self.pickaxe_mesh: Any = ObjMesh(app, get_path('assets/models/items/wooden-pickaxe/wooden_pickaxe.obj'))

    @global_profiler.profile_func('ItemManager_AddItem')
    def add_item(self, position: Any, voxel_id: int) -> None:
        """
        Spawns a new item entity into the world. Enforces a First-In-First-Out (FIFO)
        limit to automatically despawn old items if too many are active at once.
        """
        # Check if adding a new item would exceed the hardcoded global entity cap
        if len(self.items) > ITEM_ENTITY_CAP:
            # Forcefully remove the oldest item in the list (index 0) to maintain strict memory and CPU bounds
            self.items.pop(0)

        # Instantiate a new Item object at the designated coordinates and append it to the active pool
        self.items.append(Item(self.app, position, voxel_id))

    @global_profiler.profile_func('ItemManager_LoadItem')
    def load_item(self, voxel_id: int, px: float, py: float, pz: float, vx: float, vy: float, vz: float) -> None:
        """
        Restores a previously saved item entity into the world with its exact
        former position and velocity to bypass the random spawn burst.
        """
        # Enforce the exact same entity cap logic as add_item to prevent save-scumming overload
        if len(self.items) > ITEM_ENTITY_CAP:
            self.items.pop(0)

        # Instantiate a shell Item object at the origin
        item: Item = Item(self.app, (0, 0, 0), voxel_id)

        # Overwrite the random initial position with the exact coordinates loaded from the database
        item.position = glm.vec3(px, py, pz)

        # Overwrite the random burst velocity with the preserved momentum vector
        item.velocity = glm.vec3(vx, vy, vz)

        # Append the restored item to the active pool
        self.items.append(item)

    @global_profiler.profile_func('ItemManager_Update')
    def update(self) -> None:
        """
        Updates physics for all active items and removes ones marked as dead.
        """
        # Iterate through every active item entity and invoke its internal physics/logic update step
        for item in self.items:
            item.update()

        # Rebuild the active items list, filtering out any entities that have flagged themselves as dead
        self.items = [item for item in self.items if not item.is_dead]

    @global_profiler.profile_func('ItemManager_Render')
    def render(self) -> None:
        """
        Renders all items that fall within the specific item render distance.
        """
        # Temporarily disable OpenGL backface culling because the items spin, exposing all geometric faces
        self.app.ctx.disable(self.app.ctx.CULL_FACE)

        # Cache the player's current world position to calculate render distances efficiently
        player_pos: Any = self.app.player.position

        # Iterate through the entire active item pool for the render pass
        for item in self.items:
            # Perform a fast squared-distance check to cull items that are too far away to be visible
            if glm.distance2(item.position, player_pos) > ITEM_RENDER_DISTANCE_SQUARED:
                continue

            # Route the item to its appropriate 3D mesh based on its unique voxel ID
            if item.voxel_id == STICK:
                mesh = self.stick_mesh
            elif item.voxel_id == WOODEN_PICKAXE:
                mesh = self.pickaxe_mesh
            else:
                # Default to the generic cubic block mesh
                mesh = self.mesh

            # Calculate the final Model matrix containing all position, rotation, and scaling data
            # and write it directly into the shader's 'm_model' uniform
            mesh.program['m_model'].write(item.get_model_matrix())

            # If the shader requires texture indexing (for blocks), pass the voxel ID uniform
            if 'voxel_id' in mesh.program:
                mesh.program['voxel_id'] = int(item.voxel_id)

            # Issue the final OpenGL draw call for this specific item mesh
            mesh.render()

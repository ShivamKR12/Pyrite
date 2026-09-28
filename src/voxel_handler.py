"""
Block interaction handler for raycasting, placing, and breaking voxels.

This module implements the mathematical DDA (Digital Differential Analyzer)
raycasting algorithm to cleanly trace the player's line of sight through
the 3D chunk grid. It triggers multithreaded lighting and meshing updates
whenever the player adds or destroys blocks in the world.
"""

from typing import Any, Tuple

from pyglm import glm

from lighting import place_torch, update_light_place_block, update_light_remove_block
from profiler import global_profiler
from settings import (
    CHUNK_AREA,
    CHUNK_SIZE,
    GLOWSTONE,
    MAX_RAY_DISTANCE,
    NON_PLACEABLE,
    STONE,
    SURVIVAL,
    WATER,
    WOODEN_PICKAXE,
)


class VoxelHandler:
    """
    Performs raycasting from the player's camera to interact with the voxel world.
    Handles calculating the targeted block, removing blocks (mining), and adding
    blocks (placing), while triggering necessary lighting and meshing updates.

    Args:
        world (Any): The main world context containing the chunk array.
    """

    @global_profiler.profile_func('VoxelHandler_Init')
    def __init__(self, world: Any) -> None:
        """
        Initialize the `VoxelHandler` for a world instance.

        Args:
            world: The world object that owns this handler (provides app, chunks, etc.).
        """
        # World references
        self.app: Any = world.app
        self.chunks: Any = world.chunks

        # Ray casting result state
        self.chunk: Any = None
        self.voxel_id: int = 0
        self.voxel_index: int = 0
        self.voxel_local_pos: Any = None
        self.voxel_world_pos: Any = None
        self.voxel_normal: Any = None

        # Interaction settings
        self.interaction_mode: int = 0

    @global_profiler.profile_func('VoxelHandler_AddVoxel')
    def add_voxel(self) -> None:
        """
        Attempts to place the currently held block into the world at the targeted face.
        Checks for player collision, updates lighting (e.g. for Glowstone),
        and queues adjacent chunks for remeshing.
        """
        if self.voxel_id:
            # Check selected item
            current_id: int = self.app.player.inventory[self.app.player.hotbar_index]
            if current_id == 0 or current_id in NON_PLACEABLE:
                return

            # Check placement target validity
            new_voxel_pos: Any = self.voxel_world_pos + self.voxel_normal
            result: Tuple[int, int, Any, Any] = self.get_voxel_id(new_voxel_pos)

            if not result[0]:
                # Verify player intersection bounds
                player_min, player_max = self.app.player.get_aabb()
                voxel_min: Any = glm.vec3(new_voxel_pos)
                voxel_max: Any = voxel_min + 1.0
                if self.app.player.aabb_intersect(player_min, player_max, voxel_min, voxel_max):
                    return

                # Apply block to chunk
                voxel_index: int = result[1]
                chunk: Any = result[3]
                chunk.voxels[voxel_index] = current_id
                world_x: float = float(new_voxel_pos.x)
                world_y: float = float(new_voxel_pos.y)
                world_z: float = float(new_voxel_pos.z)

                # Dispatch async lighting and mesh updates
                def async_add_voxel(
                    world_x: float = world_x,
                    world_y: float = world_y,
                    world_z: float = world_z,
                    cid: int = current_id,
                    ch: Any = chunk,
                ) -> None:
                    update_light_place_block(
                        int(world_x),
                        int(world_y),
                        int(world_z),
                        self.app.scene.world.voxels,
                        self.app.scene.world.lightmaps,
                        self.app.scene.world.chunk_positions,
                    )
                    if cid == GLOWSTONE:
                        place_torch(
                            int(world_x),
                            int(world_y),
                            int(world_z),
                            self.app.scene.world.voxels,
                            self.app.scene.world.lightmaps,
                            self.app.scene.world.chunk_positions,
                        )
                    if ch not in self.app.scene.world.build_queue:
                        self.app.scene.world.build_queue.append(ch)
                    self.rebuild_adjacent_chunks(glm.vec3(world_x, world_y, world_z), is_light_update=True)

                self.app.scene.world.executor.submit(async_add_voxel)

                # Process interaction effects
                self.app.sounds.play_place(current_id)
                if self.app.player.game_mode == SURVIVAL:
                    self.app.player.inventory_counts[self.app.player.hotbar_index] -= 1
                    if self.app.player.inventory_counts[self.app.player.hotbar_index] <= 0:
                        self.app.player.inventory[self.app.player.hotbar_index] = 0
                if chunk.is_empty:
                    chunk.is_empty = False

    @global_profiler.profile_func('VoxelHandler_RebuildAdjacentChunks')
    def rebuild_adjacent_chunks(self, world_pos: Any, is_light_update: bool = True) -> None:
        """
        Automatically queues neighboring chunks for mesh regeneration if a block
        modification occurs near a chunk border, or if it creates a large lighting
        update requiring neighbors to recalculate their block/sunlight visuals.
        """
        # Calculate update radii and bounds
        world_x: int = int(world_pos.x)
        world_y: int = int(world_pos.y)
        world_z: int = int(world_pos.z)
        chunk_x: int = world_x // CHUNK_SIZE
        chunk_y: int = world_y // CHUNK_SIZE
        chunk_z: int = world_z // CHUNK_SIZE
        radius: int = 15 if is_light_update else 1
        min_cx: int = (world_x - radius) // CHUNK_SIZE
        max_cx: int = (world_x + radius) // CHUNK_SIZE
        min_cz: int = (world_z - radius) // CHUNK_SIZE
        max_cz: int = (world_z + radius) // CHUNK_SIZE
        min_cy: int = 0 if is_light_update else (world_y - radius) // CHUNK_SIZE
        max_cy: int = (world_y + radius) // CHUNK_SIZE

        # Queue chunks in range
        for x in range(min_cx, max_cx + 1):
            for y in range(min_cy, max_cy + 1):
                for z in range(min_cz, max_cz + 1):
                    if x == chunk_x and y == chunk_y and z == chunk_z:
                        continue
                    chunk_pos: Tuple[int, int, int] = (x, y, z)
                    if chunk_pos in self.app.scene.world.active_chunks:
                        chunk: Any = self.app.scene.world.active_chunks[chunk_pos]
                        if chunk not in self.app.scene.world.build_queue:
                            self.app.scene.world.build_queue.append(chunk)

    @global_profiler.profile_func('VoxelHandler_RemoveVoxel')
    def remove_voxel(self) -> None:
        """
        Breaks the targeted voxel, updates local block lighting (stripping or
        letting sunlight in), spawns a dropped item entity in Survival mode,
        and queues chunks for remeshing.
        """
        if self.voxel_id:
            # Clear targeted block
            world_x: float = float(self.voxel_world_pos.x)
            world_y: float = float(self.voxel_world_pos.y)
            world_z: float = float(self.voxel_world_pos.z)
            self.chunk.voxels[self.voxel_index] = 0

            # Dispatch async lighting and mesh updates
            def async_remove_voxel(
                world_x: float = world_x,
                world_y: float = world_y,
                world_z: float = world_z,
                vid: int = self.voxel_id,
                ch: Any = self.chunk,
            ) -> None:
                if vid == GLOWSTONE:
                    update_light_place_block(
                        int(world_x),
                        int(world_y),
                        int(world_z),
                        self.app.scene.world.voxels,
                        self.app.scene.world.lightmaps,
                        self.app.scene.world.chunk_positions,
                    )
                update_light_remove_block(
                    int(world_x),
                    int(world_y),
                    int(world_z),
                    self.app.scene.world.voxels,
                    self.app.scene.world.lightmaps,
                    self.app.scene.world.chunk_positions,
                )
                if ch not in self.app.scene.world.build_queue:
                    self.app.scene.world.build_queue.append(ch)
                self.rebuild_adjacent_chunks(glm.vec3(world_x, world_y, world_z), is_light_update=True)

            self.app.scene.world.executor.submit(async_remove_voxel)

            # Process interaction effects
            self.app.sounds.play_break(self.voxel_id)
            if self.app.player.game_mode == SURVIVAL:
                held_id: int = self.app.player.inventory[self.app.player.hotbar_index]
                if self.voxel_id == STONE and held_id != WOODEN_PICKAXE:
                    pass
                else:
                    self.app.scene.item_manager.add_item(self.voxel_world_pos, self.voxel_id)

    @global_profiler.profile_func('VoxelHandler_SetVoxel')
    def set_voxel(self, mode: str = 'remove') -> None:
        """
        Wrapper to call either add_voxel or remove_voxel based on the mode.
        """
        # Execute voxel action
        if mode == 'add':
            self.add_voxel()
        elif mode == 'remove':
            self.remove_voxel()

    @global_profiler.profile_func('VoxelHandler_Update')
    def update(self) -> None:
        """
        Update per-frame voxel interaction state (casts the interaction ray).

        This should be called from the main update loop to refresh the
        targeted voxel based on the player's view.
        """
        # Execute frame interaction
        self.ray_cast()

    # Fast Voxel Traversal Algorithm (3D DDA)
    # How does the game know exactly which block you are looking at?
    # It uses a technique called 3D Digital Differential Analyzer (DDA), specifically
    # the "Amanatides & Woo" algorithm for fast voxel traversal.
    #
    # How it works:
    # Instead of "stepping" forward by tiny amounts and checking if we hit a block
    # (which is slow and can "skip" through thin corners), this algorithm calculates
    # exactly how far the ray must travel to hit the next X, Y, or Z grid boundary
    # (`max_x`, `max_y`, `max_z`).
    #
    # We step into the grid along whichever axis is closest, update the boundary
    # distance (`delta_x`, `delta_y`, `delta_z`), and repeat until we hit a solid
    # block. It guarantees we never miss a block and runs incredibly fast since
    # it only evaluates grid intersections!
    #
    # References:
    # - 3D DDA Visualized: https://www.youtube.com/watch?v=NbSee-cg7Ig
    # - Original Amanatides & Woo Paper: http://www.cse.yorku.ca/~amana/research/grid.pdf
    # - LodeV's Raycasting Tutorial: https://lodev.org/cgtutor/raycasting.html
    @global_profiler.profile_func('VoxelHandler_RayCast')
    def ray_cast(self) -> bool:
        """
        Casts a ray forward from the camera's position through the voxel grid using
        a fast voxel traversal algorithm. Determines the exact targeted voxel and
        its normal face.
        """
        # Define ray boundaries
        x1, y1, z1 = self.app.player.position
        x2, y2, z2 = self.app.player.position + self.app.player.forward * MAX_RAY_DISTANCE
        current_voxel_pos: Any = glm.ivec3(x1, y1, z1)
        self.voxel_id = 0
        self.voxel_normal = glm.ivec3(0)
        step_dir: int = -1

        # Initialize DDA variables
        dx: float = float(glm.sign(x2 - x1))
        delta_x: float = min(dx / (x2 - x1), 10000000.0) if dx != 0 else 10000000.0
        max_x: float = delta_x * (1.0 - glm.fract(x1)) if dx > 0 else delta_x * glm.fract(x1)
        dy: float = float(glm.sign(y2 - y1))
        delta_y: float = min(dy / (y2 - y1), 10000000.0) if dy != 0 else 10000000.0
        max_y: float = delta_y * (1.0 - glm.fract(y1)) if dy > 0 else delta_y * glm.fract(y1)
        dz: float = float(glm.sign(z2 - z1))
        delta_z: float = min(dz / (z2 - z1), 10000000.0) if dz != 0 else 10000000.0
        max_z: float = delta_z * (1.0 - glm.fract(z1)) if dz > 0 else delta_z * glm.fract(z1)

        # Traverse grid
        while not (max_x > 1.0 and max_y > 1.0 and max_z > 1.0):
            result: Tuple[int, int, Any, Any] = self.get_voxel_id(voxel_world_pos=current_voxel_pos)

            # Check for solid block intersection
            if result[0] and result[0] != WATER:
                self.voxel_id = result[0]
                self.voxel_index = result[1]
                self.voxel_local_pos = result[2]
                self.chunk = result[3]
                self.voxel_world_pos = current_voxel_pos
                if step_dir == 0:
                    self.voxel_normal.x = -dx
                elif step_dir == 1:
                    self.voxel_normal.y = -dy
                else:
                    self.voxel_normal.z = -dz
                return True

            # Step along shortest distance
            if max_x < max_y:
                if max_x < max_z:
                    current_voxel_pos.x += int(dx)
                    max_x += delta_x
                    step_dir = 0
                else:
                    current_voxel_pos.z += int(dz)
                    max_z += delta_z
                    step_dir = 2
            else:
                if max_y < max_z:
                    current_voxel_pos.y += int(dy)
                    max_y += delta_y
                    step_dir = 1
                else:
                    current_voxel_pos.z += int(dz)
                    max_z += delta_z
                    step_dir = 2

        return False

    @global_profiler.profile_func('VoxelHandler_GetVoxelId')
    def get_voxel_id(self, voxel_world_pos: Any) -> Tuple[int, int, Any, Any]:
        """
        Resolve a world-space voxel position to its chunk-local index and id.

        Args:
            voxel_world_pos: 3D position (vec-like) in world coordinates.

        Returns:
            A tuple of (voxel_id, voxel_index, voxel_local_pos, chunk) where
            `voxel_id` is 0 for empty space, `voxel_index` is the linear index
            inside the chunk voxel array, `voxel_local_pos` is the local 3D
            integer coordinate within the chunk, and `chunk` is the chunk object
            containing the voxel (or None if out of loaded range).
        """
        # Determine target chunk
        chunk_x: int = int(glm.floor(voxel_world_pos.x / CHUNK_SIZE))
        chunk_y: int = int(glm.floor(voxel_world_pos.y / CHUNK_SIZE))
        chunk_z: int = int(glm.floor(voxel_world_pos.z / CHUNK_SIZE))
        chunk_pos: Tuple[int, int, int] = (chunk_x, chunk_y, chunk_z)

        # Fetch local voxel data
        if chunk_pos in self.app.scene.world.active_chunks:
            chunk: Any = self.app.scene.world.active_chunks[chunk_pos]
            if chunk.voxels is None:
                return 0, 0, None, None
            lx, ly, lz = voxel_local_pos = (
                glm.ivec3(voxel_world_pos) - glm.ivec3(chunk_x, chunk_y, chunk_z) * CHUNK_SIZE
            )
            voxel_index: int = lx + CHUNK_SIZE * lz + CHUNK_AREA * ly
            voxel_id: int = chunk.voxels[voxel_index]
            return voxel_id, voxel_index, voxel_local_pos, chunk

        return 0, 0, None, None

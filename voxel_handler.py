from settings import *
from meshes.chunk_mesh_builder import get_chunk_index


class VoxelHandler:
    def __init__(self, world):
        self.app = world.app
        self.chunks = world.chunks

        # ray casting result
        self.chunk = None
        self.voxel_id = None
        self.voxel_index = None
        self.voxel_local_pos = None
        self.voxel_world_pos = None
        self.voxel_normal = None

        # Keep for voxel_marker compatibility, permanently set to 0 for standard Minecraft highlighting
        self.interaction_mode = 0  

    def add_voxel(self):
        if self.voxel_id:
            current_id = self.app.player.inventory[self.app.player.hotbar_index]
            if current_id == 0 or current_id in NON_PLACEABLE:
                return # Can't place empty air

            # check voxel id along normal
            new_voxel_pos = self.voxel_world_pos + self.voxel_normal
            result = self.get_voxel_id(new_voxel_pos)

            # is the new place empty?
            if not result[0]:
                # prevent placing blocks inside the player
                player_min, player_max = self.app.player.get_aabb()
                voxel_min = glm.vec3(new_voxel_pos)
                voxel_max = voxel_min + 1.0
                if self.app.player.aabb_intersect(player_min, player_max, voxel_min, voxel_max):
                    return

                _, voxel_index, _, chunk = result
                chunk.voxels[voxel_index] = current_id
                if chunk not in self.app.scene.world.build_queue:
                    self.app.scene.world.build_queue.append(chunk)
                self.app.sounds.play_dig(current_id)

                # Consume item from hotbar if in Survival mode
                if self.app.player.game_mode == SURVIVAL:
                    self.app.player.inventory_counts[self.app.player.hotbar_index] -= 1
                    if self.app.player.inventory_counts[self.app.player.hotbar_index] <= 0:
                        self.app.player.inventory[self.app.player.hotbar_index] = 0

                # was it an empty chunk
                if chunk.is_empty:
                    chunk.is_empty = False

    def rebuild_adj_chunk(self, adj_voxel_pos):
        cx, cy, cz = int(adj_voxel_pos[0] // CHUNK_SIZE), int(adj_voxel_pos[1] // CHUNK_SIZE), int(adj_voxel_pos[2] // CHUNK_SIZE)
        chunk_pos = (cx, cy, cz)
        if chunk_pos in self.app.scene.world.active_chunks:
            chunk = self.app.scene.world.active_chunks[chunk_pos]
            if chunk not in self.app.scene.world.build_queue:
                self.app.scene.world.build_queue.append(chunk)

    def rebuild_adjacent_chunks(self):
        lx, ly, lz = self.voxel_local_pos
        wx, wy, wz = self.voxel_world_pos

        if lx == 0:
            self.rebuild_adj_chunk((wx - 1, wy, wz))
        elif lx == CHUNK_SIZE - 1:
            self.rebuild_adj_chunk((wx + 1, wy, wz))

        if ly == 0:
            self.rebuild_adj_chunk((wx, wy - 1, wz))
        elif ly == CHUNK_SIZE - 1:
            self.rebuild_adj_chunk((wx, wy + 1, wz))

        if lz == 0:
            self.rebuild_adj_chunk((wx, wy, wz - 1))
        elif lz == CHUNK_SIZE - 1:
            self.rebuild_adj_chunk((wx, wy, wz + 1))

    def remove_voxel(self):
        if self.voxel_id:
            self.chunk.voxels[self.voxel_index] = 0

            if self.chunk not in self.app.scene.world.build_queue:
                self.app.scene.world.build_queue.append(self.chunk)
            self.rebuild_adjacent_chunks()
            self.app.sounds.play_dig(self.voxel_id)
            
            # Spawn dropped item only in Survival mode
            if self.app.player.game_mode == SURVIVAL:
                held_id = self.app.player.inventory[self.app.player.hotbar_index]
                if self.voxel_id == STONE and held_id != WOODEN_PICKAXE:
                    pass # Break but drop nothing!
                else:
                    self.app.scene.item_manager.add_item(self.voxel_world_pos, self.voxel_id)

    def set_voxel(self, mode='remove'):
        if mode == 'add':
            self.add_voxel()
        elif mode == 'remove':
            self.remove_voxel()

    def update(self):
        self.ray_cast()

    def ray_cast(self):
        # start point
        x1, y1, z1 = self.app.player.position
        # end point
        x2, y2, z2 = self.app.player.position + self.app.player.forward * MAX_RAY_DIST

        current_voxel_pos = glm.ivec3(x1, y1, z1)
        self.voxel_id = 0
        self.voxel_normal = glm.ivec3(0)
        step_dir = -1

        dx = glm.sign(x2 - x1)
        delta_x = min(dx / (x2 - x1), 10000000.0) if dx != 0 else 10000000.0
        max_x = delta_x * (1.0 - glm.fract(x1)) if dx > 0 else delta_x * glm.fract(x1)

        dy = glm.sign(y2 - y1)
        delta_y = min(dy / (y2 - y1), 10000000.0) if dy != 0 else 10000000.0
        max_y = delta_y * (1.0 - glm.fract(y1)) if dy > 0 else delta_y * glm.fract(y1)

        dz = glm.sign(z2 - z1)
        delta_z = min(dz / (z2 - z1), 10000000.0) if dz != 0 else 10000000.0
        max_z = delta_z * (1.0 - glm.fract(z1)) if dz > 0 else delta_z * glm.fract(z1)

        while not (max_x > 1.0 and max_y > 1.0 and max_z > 1.0):

            result = self.get_voxel_id(voxel_world_pos=current_voxel_pos)
            # Ignore water blocks for raycasting so the player can break blocks underwater!
            if result[0] and result[0] != WATER:
                self.voxel_id, self.voxel_index, self.voxel_local_pos, self.chunk = result
                self.voxel_world_pos = current_voxel_pos

                if step_dir == 0:
                    self.voxel_normal.x = -dx
                elif step_dir == 1:
                    self.voxel_normal.y = -dy
                else:
                    self.voxel_normal.z = -dz
                return True

            if max_x < max_y:
                if max_x < max_z:
                    current_voxel_pos.x += dx
                    max_x += delta_x
                    step_dir = 0
                else:
                    current_voxel_pos.z += dz
                    max_z += delta_z
                    step_dir = 2
            else:
                if max_y < max_z:
                    current_voxel_pos.y += dy
                    max_y += delta_y
                    step_dir = 1
                else:
                    current_voxel_pos.z += dz
                    max_z += delta_z
                    step_dir = 2
        return False

    def get_voxel_id(self, voxel_world_pos):
        cx = int(glm.floor(voxel_world_pos.x / CHUNK_SIZE))
        cy = int(glm.floor(voxel_world_pos.y / CHUNK_SIZE))
        cz = int(glm.floor(voxel_world_pos.z / CHUNK_SIZE))
        chunk_pos = (cx, cy, cz)

        if chunk_pos in self.app.scene.world.active_chunks:
            chunk = self.app.scene.world.active_chunks[chunk_pos]
            # Prevent errors if interacting with a chunk that is still loading asynchronously
            if chunk.voxels is None:
                return 0, 0, 0, 0
                
            lx, ly, lz = voxel_local_pos = glm.ivec3(voxel_world_pos) - glm.ivec3(cx, cy, cz) * CHUNK_SIZE

            voxel_index = lx + CHUNK_SIZE * lz + CHUNK_AREA * ly
            voxel_id = chunk.voxels[voxel_index]

            return voxel_id, voxel_index, voxel_local_pos, chunk
        return 0, 0, 0, 0

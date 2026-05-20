from settings import *
from lighting import update_light_place_block, place_torch, update_light_remove_block


class VoxelHandler:
    """
    Performs raycasting from the player's camera to interact with the voxel world.
    Handles calculating the targeted block, removing blocks (mining), and adding 
    blocks (placing), while triggering necessary lighting and meshing updates.
    """
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
        """
        Attempts to place the currently held block into the world at the targeted face.
        Checks for player collision, updates lighting (e.g. for Glowstone), 
        and queues adjacent chunks for remeshing.
        """
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

                wx, wy, wz = new_voxel_pos
                update_light_place_block(int(wx), int(wy), int(wz), self.app.scene.world.voxels, self.app.scene.world.lightmaps, self.app.scene.world.chunk_positions)
                
                if current_id == GLOWSTONE:
                    place_torch(int(wx), int(wy), int(wz), self.app.scene.world.voxels, self.app.scene.world.lightmaps, self.app.scene.world.chunk_positions)
                
                if chunk not in self.app.scene.world.build_queue:
                    self.app.scene.world.build_queue.append(chunk)
                
                self.rebuild_adjacent_chunks(new_voxel_pos, is_light_update=True)
                self.app.sounds.play_place(current_id)

                # Consume item from hotbar if in Survival mode
                if self.app.player.game_mode == SURVIVAL:
                    self.app.player.inventory_counts[self.app.player.hotbar_index] -= 1
                    
                    if self.app.player.inventory_counts[self.app.player.hotbar_index] <= 0:
                        self.app.player.inventory[self.app.player.hotbar_index] = 0

                # was it an empty chunk
                if chunk.is_empty:
                    chunk.is_empty = False

    def rebuild_adjacent_chunks(self, world_pos, is_light_update=True):
        """
        Automatically queues neighboring chunks for mesh regeneration if a block 
        modification occurs near a chunk border, or if it creates a large lighting 
        update requiring neighbors to recalculate their block/sunlight visuals.
        """
        wx, wy, wz = int(world_pos.x), int(world_pos.y), int(world_pos.z)
        cx, cy, cz = wx // CHUNK_SIZE, wy // CHUNK_SIZE, wz // CHUNK_SIZE

        # Light updates (breaking a block, placing a light source) can travel up to 15 blocks
        radius = 15 if is_light_update else 1

        min_cx = (wx - radius) // CHUNK_SIZE
        max_cx = (wx + radius) // CHUNK_SIZE
        min_cz = (wz - radius) // CHUNK_SIZE
        max_cz = (wz + radius) // CHUNK_SIZE
        
        # Sunlight casts shadows all the way down, so update everything below!
        min_cy = 0 if is_light_update else (wy - radius) // CHUNK_SIZE
        max_cy = (wy + radius) // CHUNK_SIZE

        for x in range(min_cx, max_cx + 1):
            for y in range(min_cy, max_cy + 1):
                for z in range(min_cz, max_cz + 1):
                    
                    if x == cx and y == cy and z == cz:
                        continue # Main chunk is already in the build queue
                    
                    chunk_pos = (x, y, z)
                    if chunk_pos in self.app.scene.world.active_chunks:
                        chunk = self.app.scene.world.active_chunks[chunk_pos]
                        
                        if chunk not in self.app.scene.world.build_queue:
                            self.app.scene.world.build_queue.append(chunk)

    def remove_voxel(self):
        """
        Breaks the targeted voxel, updates local block lighting (stripping or 
        letting sunlight in), spawns a dropped item entity in Survival mode, 
        and queues chunks for remeshing.
        """
        if self.voxel_id:
            wx, wy, wz = self.voxel_world_pos
            
            if self.voxel_id == GLOWSTONE:
                # Strips torch block light from the area first!
                update_light_place_block(int(wx), int(wy), int(wz), self.app.scene.world.voxels, self.app.scene.world.lightmaps, self.app.scene.world.chunk_positions)
                
            self.chunk.voxels[self.voxel_index] = 0
            
            # Allows sunlight/blocklight from neighbors back into the new hole!
            update_light_remove_block(int(wx), int(wy), int(wz), self.app.scene.world.voxels, self.app.scene.world.lightmaps, self.app.scene.world.chunk_positions)

            if self.chunk not in self.app.scene.world.build_queue:
                self.app.scene.world.build_queue.append(self.chunk)
            
            self.rebuild_adjacent_chunks(self.voxel_world_pos, is_light_update=True)
            self.app.sounds.play_break(self.voxel_id)
            
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
        """
        Casts a ray forward from the camera's position through the voxel grid using 
        a fast voxel traversal algorithm. Determines the exact targeted voxel and 
        its normal face.
        """
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

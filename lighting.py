from numba import njit
import numpy as np
from settings import *
from meshes.chunk_mesh_builder import get_chunk_index


DIRS = np.array([
    [0, 1, 0], [0, -1, 0], [1, 0, 0], [-1, 0, 0], [0, 0, -1], [0, 0, 1]
], dtype=np.int32)


@njit(cache=True, nogil=True)
def get_voxel_fast(wx, wy, wz, world_voxels, chunk_positions):
    idx = get_chunk_index((wx, wy, wz), chunk_positions)
    if idx == -1: return 1
    lx, ly, lz = wx % CHUNK_SIZE, wy % CHUNK_SIZE, wz % CHUNK_SIZE
    return world_voxels[idx][lx + lz * CHUNK_SIZE + ly * CHUNK_AREA]


@njit(cache=True, nogil=True)
def get_light_fast(wx, wy, wz, world_lightmaps, chunk_positions):
    idx = get_chunk_index((wx, wy, wz), chunk_positions)
    if idx == -1: return 0
    lx, ly, lz = wx % CHUNK_SIZE, wy % CHUNK_SIZE, wz % CHUNK_SIZE
    return world_lightmaps[idx][lx + lz * CHUNK_SIZE + ly * CHUNK_AREA]


@njit(cache=True, nogil=True)
def set_light_fast(wx, wy, wz, val, world_lightmaps, chunk_positions):
    idx = get_chunk_index((wx, wy, wz), chunk_positions)
    if idx != -1:
        lx, ly, lz = wx % CHUNK_SIZE, wy % CHUNK_SIZE, wz % CHUNK_SIZE
        world_lightmaps[idx][lx + lz * CHUNK_SIZE + ly * CHUNK_AREA] = val


@njit(cache=True, nogil=True)
def propagate_light_queue(queue, tail, is_sun, world_voxels, world_lightmaps, chunk_positions):
    # Initialize with dummy arrays to satisfy Numba's strict type inference
    local_voxels = world_voxels[0] 
    local_lightmaps = world_lightmaps[0]
    cx_base, cy_base, cz_base = -1, -1, -1

    head = 0
    while head < tail and tail < 199990:
        packed = queue[head]
        head += 1
        x = int((packed >> 32) & 0xFFFF)
        y = int((packed >> 16) & 0xFFFF)
        z = int(packed & 0xFFFF)

        val = get_light_fast(x, y, z, world_lightmaps, chunk_positions)
        L = (val >> 4) if is_sun else (val & 15)

        chunk_idx = get_chunk_index((x, y, z), chunk_positions)
        has_fast_path = chunk_idx != -1
        
        if has_fast_path:
            local_voxels = world_voxels[chunk_idx]
            local_lightmaps = world_lightmaps[chunk_idx]
            cx_base = x // CHUNK_SIZE
            cy_base = y // CHUNK_SIZE
            cz_base = z // CHUNK_SIZE

        for i in range(6):
            nx, ny, nz = x + DIRS[i][0], y + DIRS[i][1], z + DIRS[i][2]
            if ny < 0 or ny >= WORLD_H * CHUNK_SIZE: continue

            # AAA Optimization: In-Chunk Fast Path (Bypasses slow Modulo & Array Lookups!)
            is_local = has_fast_path and (nx // CHUNK_SIZE) == cx_base and (ny // CHUNK_SIZE) == cy_base and (nz // CHUNK_SIZE) == cz_base
            idx = 0
            if is_local:
                lx, ly, lz = nx % CHUNK_SIZE, ny % CHUNK_SIZE, nz % CHUNK_SIZE
                idx = lx + lz * CHUNK_SIZE + ly * CHUNK_AREA
                voxel_id = local_voxels[idx]
                n_val = local_lightmaps[idx]
            else:
                voxel_id = get_voxel_fast(nx, ny, nz, world_voxels, chunk_positions)
                n_val = get_light_fast(nx, ny, nz, world_lightmaps, chunk_positions)

            if voxel_id != AIR and voxel_id != WATER and voxel_id != GLASS and voxel_id != LEAVES: continue

            n_L = (n_val >> 4) if is_sun else (n_val & 15)

            if voxel_id == WATER or voxel_id == LEAVES:
                diminish = 2
            else:
                diminish = 1
            new_L = L - diminish
            # Sunlight drops vertically through air without losing power!
            if is_sun and DIRS[i][1] == -1 and L == 15 and voxel_id == 0:
                new_L = 15

            if n_L < new_L:
                if is_sun:
                    new_val = (new_L << 4) | (n_val & 15)
                else:
                    new_val = ((n_val >> 4) << 4) | new_L
                    
                if is_local:
                    local_lightmaps[idx] = new_val
                else:
                    set_light_fast(nx, ny, nz, new_val, world_lightmaps, chunk_positions)
                
                queue[tail] = (np.uint64(nx) << 32) | (np.uint64(ny) << 16) | np.uint64(nz)
                tail += 1


@njit(cache=True, nogil=True)
def init_chunk_lighting(cx, cy, cz, world_voxels, world_lightmaps, chunk_positions):
    queue_sun = np.empty(200000, dtype=np.uint64)
    tail_sun = 0
    queue_block = np.empty(200000, dtype=np.uint64)
    tail_block = 0

    chunk_idx = get_chunk_index((cx, cy, cz), chunk_positions)
    if chunk_idx != -1:
        local_lightmap = world_lightmaps[chunk_idx]
        local_voxels = world_voxels[chunk_idx]
        
        for y in range(CHUNK_SIZE):
            for z in range(CHUNK_SIZE):
                for x in range(CHUNK_SIZE):
                    # Calculate the raw 1D array index instantly
                    idx = x + z * CHUNK_SIZE + y * CHUNK_AREA
                    val = local_lightmap[idx]
                    voxel_id = local_voxels[idx]
                    
                    # Fallback for old save files: Ignite un-cached Glowstone blocks!
                    if voxel_id == GLOWSTONE:
                        val = (val & 240) | 14 # Preserve sunlight (240), set block light to 14
                        local_lightmap[idx] = val
                    
                    sun = val >> 4
                    if sun > 0:
                        if x == 0 or x == CHUNK_SIZE - 1 or y == 0 or y == CHUNK_SIZE - 1 or z == 0 or z == CHUNK_SIZE - 1:
                            queue_sun[tail_sun] = (np.uint64(x + cx) << 32) | (np.uint64(y + cy) << 16) | np.uint64(z + cz)
                            tail_sun += 1
                        else:
                            if (local_lightmap[(x-1) + z*CHUNK_SIZE + y*CHUNK_AREA] >> 4) < sun or \
                               (local_lightmap[(x+1) + z*CHUNK_SIZE + y*CHUNK_AREA] >> 4) < sun or \
                               (local_lightmap[x + (z-1)*CHUNK_SIZE + y*CHUNK_AREA] >> 4) < sun or \
                               (local_lightmap[x + (z+1)*CHUNK_SIZE + y*CHUNK_AREA] >> 4) < sun or \
                               (local_lightmap[x + z*CHUNK_SIZE + (y-1)*CHUNK_AREA] >> 4) < sun or \
                               (local_lightmap[x + z*CHUNK_SIZE + (y+1)*CHUNK_AREA] >> 4) < sun:
                                queue_sun[tail_sun] = (np.uint64(x + cx) << 32) | (np.uint64(y + cy) << 16) | np.uint64(z + cz)
                                tail_sun += 1
                                
                    block = val & 15
                    if block > 0:
                        if x == 0 or x == CHUNK_SIZE - 1 or y == 0 or y == CHUNK_SIZE - 1 or z == 0 or z == CHUNK_SIZE - 1:
                            queue_block[tail_block] = (np.uint64(x + cx) << 32) | (np.uint64(y + cy) << 16) | np.uint64(z + cz)
                            tail_block += 1
                        else:
                            if (local_lightmap[(x-1) + z*CHUNK_SIZE + y*CHUNK_AREA] & 15) < block or \
                               (local_lightmap[(x+1) + z*CHUNK_SIZE + y*CHUNK_AREA] & 15) < block or \
                               (local_lightmap[x + (z-1)*CHUNK_SIZE + y*CHUNK_AREA] & 15) < block or \
                               (local_lightmap[x + (z+1)*CHUNK_SIZE + y*CHUNK_AREA] & 15) < block or \
                               (local_lightmap[x + z*CHUNK_SIZE + (y-1)*CHUNK_AREA] & 15) < block or \
                               (local_lightmap[x + z*CHUNK_SIZE + (y+1)*CHUNK_AREA] & 15) < block:
                                queue_block[tail_block] = (np.uint64(x + cx) << 32) | (np.uint64(y + cy) << 16) | np.uint64(z + cz)
                                tail_block += 1
                    
    propagate_light_queue(queue_sun, tail_sun, True, world_voxels, world_lightmaps, chunk_positions)
    propagate_light_queue(queue_block, tail_block, False, world_voxels, world_lightmaps, chunk_positions)


@njit(cache=True, nogil=True)
def remove_light_node(wx, wy, wz, light_level, is_sun, world_lightmaps, chunk_positions, refill_queue, tail_refill):
    queue = np.empty(200000, dtype=np.uint64)
    head = 0
    tail = 0
    queue[tail] = (np.uint64(wx) << 40) | (np.uint64(wy) << 24) | (np.uint64(wz) << 8) | np.uint64(light_level)
    tail += 1

    while head < tail and tail < 199990:
        packed = queue[head]
        head += 1
        x = int((packed >> 40) & 0xFFFF)
        y = int((packed >> 24) & 0xFFFF)
        z = int((packed >> 8) & 0xFFFF)
        L = int(packed & 0xFF)

        for i in range(6):
            nx, ny, nz = x + DIRS[i][0], y + DIRS[i][1], z + DIRS[i][2]
            if ny < 0 or ny >= WORLD_H * CHUNK_SIZE: continue

            n_val = get_light_fast(nx, ny, nz, world_lightmaps, chunk_positions)
            n_L = (n_val >> 4) if is_sun else (n_val & 15)

            if n_L != 0 and n_L < L:
                if is_sun:
                    set_light_fast(nx, ny, nz, (0 << 4) | (n_val & 15), world_lightmaps, chunk_positions)
                else:
                    set_light_fast(nx, ny, nz, ((n_val >> 4) << 4) | 0, world_lightmaps, chunk_positions)
                
                queue[tail] = (np.uint64(nx) << 40) | (np.uint64(ny) << 24) | (np.uint64(nz) << 8) | np.uint64(n_L)
                tail += 1
            elif n_L >= L:
                refill_queue[tail_refill] = (np.uint64(nx) << 32) | (np.uint64(ny) << 16) | np.uint64(nz)
                tail_refill += 1
                
    return tail_refill


@njit(cache=True, nogil=True)
def update_light_place_block(wx, wy, wz, world_voxels, world_lightmaps, chunk_positions):
    curr_val = get_light_fast(wx, wy, wz, world_lightmaps, chunk_positions)
    sun, block = curr_val >> 4, curr_val & 15
    set_light_fast(wx, wy, wz, 0, world_lightmaps, chunk_positions)
    
    refill_queue = np.empty(200000, dtype=np.uint64)
    if sun > 0:
        tail_refill = remove_light_node(wx, wy, wz, sun, True, world_lightmaps, chunk_positions, refill_queue, 0)
        propagate_light_queue(refill_queue, tail_refill, True, world_voxels, world_lightmaps, chunk_positions)
    if block > 0:
        tail_refill = remove_light_node(wx, wy, wz, block, False, world_lightmaps, chunk_positions, refill_queue, 0)
        propagate_light_queue(refill_queue, tail_refill, False, world_voxels, world_lightmaps, chunk_positions)


@njit(cache=True, nogil=True)
def update_light_remove_block(wx, wy, wz, world_voxels, world_lightmaps, chunk_positions):
    queue_sun = np.empty(200000, dtype=np.uint64)
    tail_sun = 0
    queue_block = np.empty(200000, dtype=np.uint64)
    tail_block = 0
    
    up_val = get_light_fast(wx, wy + 1, wz, world_lightmaps, chunk_positions)
    if (up_val >> 4) == 15:
        # AAA Optimization: Vertical Raycast! (Turns O(N^3) expansion into O(1) linear line!)
        curr_y = wy
        while curr_y >= 0:
            voxel_id = get_voxel_fast(wx, curr_y, wz, world_voxels, chunk_positions)
            if voxel_id != AIR and voxel_id != WATER and voxel_id != GLASS and voxel_id != LEAVES:
                break
            
            curr_val = get_light_fast(wx, curr_y, wz, world_lightmaps, chunk_positions)
            set_light_fast(wx, curr_y, wz, (15 << 4) | (curr_val & 15), world_lightmaps, chunk_positions)
            queue_sun[tail_sun] = (np.uint64(wx) << 32) | (np.uint64(curr_y) << 16) | np.uint64(wz)
            tail_sun += 1
            
            if voxel_id == WATER or voxel_id == LEAVES:
                break
            curr_y -= 1
        
    for i in range(6):
        nx, ny, nz = wx + DIRS[i][0], wy + DIRS[i][1], wz + DIRS[i][2]
        if ny < 0 or ny >= WORLD_H * CHUNK_SIZE: continue
        
        n_val = get_light_fast(nx, ny, nz, world_lightmaps, chunk_positions)
        if (n_val >> 4) > 0:
            queue_sun[tail_sun] = (np.uint64(nx) << 32) | (np.uint64(ny) << 16) | np.uint64(nz)
            tail_sun += 1
        if (n_val & 15) > 0:
            queue_block[tail_block] = (np.uint64(nx) << 32) | (np.uint64(ny) << 16) | np.uint64(nz)
            tail_block += 1
            
    propagate_light_queue(queue_sun, tail_sun, True, world_voxels, world_lightmaps, chunk_positions)
    propagate_light_queue(queue_block, tail_block, False, world_voxels, world_lightmaps, chunk_positions)


@njit(cache=True, nogil=True)
def place_torch(wx, wy, wz, world_voxels, world_lightmaps, chunk_positions):
    curr_val = get_light_fast(wx, wy, wz, world_lightmaps, chunk_positions)
    set_light_fast(wx, wy, wz, ((curr_val >> 4) << 4) | 14, world_lightmaps, chunk_positions)
    
    queue = np.empty(200000, dtype=np.uint64)
    queue[0] = (np.uint64(wx) << 32) | (np.uint64(wy) << 16) | np.uint64(wz)
    propagate_light_queue(queue, 1, False, world_voxels, world_lightmaps, chunk_positions)

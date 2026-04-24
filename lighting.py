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
    head = 0
    while head < tail and tail < 199990:
        x, y, z = queue[head]
        head += 1
        val = get_light_fast(x, y, z, world_lightmaps, chunk_positions)
        L = (val >> 4) if is_sun else (val & 15)

        for i in range(6):
            nx, ny, nz = x + DIRS[i][0], y + DIRS[i][1], z + DIRS[i][2]
            if ny < 0 or ny >= WORLD_H * CHUNK_SIZE: continue

            voxel_id = get_voxel_fast(nx, ny, nz, world_voxels, chunk_positions)
            if voxel_id != AIR and voxel_id != WATER and voxel_id != GLASS and voxel_id != LEAVES: continue

            n_val = get_light_fast(nx, ny, nz, world_lightmaps, chunk_positions)
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
                    set_light_fast(nx, ny, nz, (new_L << 4) | (n_val & 15), world_lightmaps, chunk_positions)
                else:
                    set_light_fast(nx, ny, nz, ((n_val >> 4) << 4) | new_L, world_lightmaps, chunk_positions)
                
                queue[tail] = (nx, ny, nz)
                tail += 1


@njit(cache=True, nogil=True)
def init_chunk_lighting(cx, cy, cz, world_voxels, world_lightmaps, chunk_positions):
    queue_sun = np.empty((200000, 3), dtype=np.int32)
    tail_sun = 0
    queue_block = np.empty((200000, 3), dtype=np.int32)
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
                            queue_sun[tail_sun] = (x + cx, y + cy, z + cz)
                            tail_sun += 1
                        else:
                            if (local_lightmap[(x-1) + z*CHUNK_SIZE + y*CHUNK_AREA] >> 4) < sun or \
                               (local_lightmap[(x+1) + z*CHUNK_SIZE + y*CHUNK_AREA] >> 4) < sun or \
                               (local_lightmap[x + (z-1)*CHUNK_SIZE + y*CHUNK_AREA] >> 4) < sun or \
                               (local_lightmap[x + (z+1)*CHUNK_SIZE + y*CHUNK_AREA] >> 4) < sun or \
                               (local_lightmap[x + z*CHUNK_SIZE + (y-1)*CHUNK_AREA] >> 4) < sun or \
                               (local_lightmap[x + z*CHUNK_SIZE + (y+1)*CHUNK_AREA] >> 4) < sun:
                                queue_sun[tail_sun] = (x + cx, y + cy, z + cz)
                                tail_sun += 1
                                
                    block = val & 15
                    if block > 0:
                        if x == 0 or x == CHUNK_SIZE - 1 or y == 0 or y == CHUNK_SIZE - 1 or z == 0 or z == CHUNK_SIZE - 1:
                            queue_block[tail_block] = (x + cx, y + cy, z + cz)
                            tail_block += 1
                        else:
                            if (local_lightmap[(x-1) + z*CHUNK_SIZE + y*CHUNK_AREA] & 15) < block or \
                               (local_lightmap[(x+1) + z*CHUNK_SIZE + y*CHUNK_AREA] & 15) < block or \
                               (local_lightmap[x + (z-1)*CHUNK_SIZE + y*CHUNK_AREA] & 15) < block or \
                               (local_lightmap[x + (z+1)*CHUNK_SIZE + y*CHUNK_AREA] & 15) < block or \
                               (local_lightmap[x + z*CHUNK_SIZE + (y-1)*CHUNK_AREA] & 15) < block or \
                               (local_lightmap[x + z*CHUNK_SIZE + (y+1)*CHUNK_AREA] & 15) < block:
                                queue_block[tail_block] = (x + cx, y + cy, z + cz)
                                tail_block += 1
                    
    propagate_light_queue(queue_sun, tail_sun, True, world_voxels, world_lightmaps, chunk_positions)
    propagate_light_queue(queue_block, tail_block, False, world_voxels, world_lightmaps, chunk_positions)


@njit(cache=True, nogil=True)
def remove_light_node(wx, wy, wz, light_level, is_sun, world_lightmaps, chunk_positions, refill_queue, tail_refill):
    queue = np.empty((200000, 4), dtype=np.int32)
    head = 0
    tail = 0
    queue[tail] = (wx, wy, wz, light_level)
    tail += 1

    while head < tail and tail < 199990:
        x, y, z, L = queue[head]
        head += 1

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
                
                queue[tail] = (nx, ny, nz, n_L)
                tail += 1
            elif n_L >= L:
                refill_queue[tail_refill] = (nx, ny, nz)
                tail_refill += 1
                
    return tail_refill


@njit(cache=True, nogil=True)
def update_light_place_block(wx, wy, wz, world_voxels, world_lightmaps, chunk_positions):
    curr_val = get_light_fast(wx, wy, wz, world_lightmaps, chunk_positions)
    sun, block = curr_val >> 4, curr_val & 15
    set_light_fast(wx, wy, wz, 0, world_lightmaps, chunk_positions)
    
    refill_queue = np.empty((200000, 3), dtype=np.int32)
    if sun > 0:
        tail_refill = remove_light_node(wx, wy, wz, sun, True, world_lightmaps, chunk_positions, refill_queue, 0)
        propagate_light_queue(refill_queue, tail_refill, True, world_voxels, world_lightmaps, chunk_positions)
    if block > 0:
        tail_refill = remove_light_node(wx, wy, wz, block, False, world_lightmaps, chunk_positions, refill_queue, 0)
        propagate_light_queue(refill_queue, tail_refill, False, world_voxels, world_lightmaps, chunk_positions)


@njit(cache=True, nogil=True)
def update_light_remove_block(wx, wy, wz, world_voxels, world_lightmaps, chunk_positions):
    queue_sun = np.empty((6, 3), dtype=np.int32)
    tail_sun = 0
    queue_block = np.empty((6, 3), dtype=np.int32)
    tail_block = 0
    
    up_val = get_light_fast(wx, wy + 1, wz, world_lightmaps, chunk_positions)
    if (up_val >> 4) == 15:
        set_light_fast(wx, wy, wz, (15 << 4) | 0, world_lightmaps, chunk_positions)
        queue_sun[tail_sun] = (wx, wy, wz)
        tail_sun += 1
        
    for i in range(6):
        nx, ny, nz = wx + DIRS[i][0], wy + DIRS[i][1], wz + DIRS[i][2]
        if ny < 0 or ny >= WORLD_H * CHUNK_SIZE: continue
        
        n_val = get_light_fast(nx, ny, nz, world_lightmaps, chunk_positions)
        if (n_val >> 4) > 0:
            queue_sun[tail_sun] = (nx, ny, nz)
            tail_sun += 1
        if (n_val & 15) > 0:
            queue_block[tail_block] = (nx, ny, nz)
            tail_block += 1
            
    propagate_light_queue(queue_sun, tail_sun, True, world_voxels, world_lightmaps, chunk_positions)
    propagate_light_queue(queue_block, tail_block, False, world_voxels, world_lightmaps, chunk_positions)


@njit(cache=True, nogil=True)
def place_torch(wx, wy, wz, world_voxels, world_lightmaps, chunk_positions):
    curr_val = get_light_fast(wx, wy, wz, world_lightmaps, chunk_positions)
    set_light_fast(wx, wy, wz, ((curr_val >> 4) << 4) | 14, world_lightmaps, chunk_positions)
    
    queue = np.empty((200000, 3), dtype=np.int32)
    queue[0] = (wx, wy, wz)
    propagate_light_queue(queue, 1, False, world_voxels, world_lightmaps, chunk_positions)

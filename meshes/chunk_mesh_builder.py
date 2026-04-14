from settings import *
from numba import uint8


@njit(cache=True)
def get_ao(local_pos, world_pos, world_voxels, chunk_positions, plane):
    x, y, z = local_pos
    wx, wy, wz = world_pos

    if plane == 'Y':
        a = is_void((x    , y, z - 1), (wx    , wy, wz - 1), world_voxels, chunk_positions)
        b = is_void((x - 1, y, z - 1), (wx - 1, wy, wz - 1), world_voxels, chunk_positions)
        c = is_void((x - 1, y, z    ), (wx - 1, wy, wz    ), world_voxels, chunk_positions)
        d = is_void((x - 1, y, z + 1), (wx - 1, wy, wz + 1), world_voxels, chunk_positions)
        e = is_void((x    , y, z + 1), (wx    , wy, wz + 1), world_voxels, chunk_positions)
        f = is_void((x + 1, y, z + 1), (wx + 1, wy, wz + 1), world_voxels, chunk_positions)
        g = is_void((x + 1, y, z    ), (wx + 1, wy, wz    ), world_voxels, chunk_positions)
        h = is_void((x + 1, y, z - 1), (wx + 1, wy, wz - 1), world_voxels, chunk_positions)

    elif plane == 'X':
        a = is_void((x, y    , z - 1), (wx, wy    , wz - 1), world_voxels, chunk_positions)
        b = is_void((x, y - 1, z - 1), (wx, wy - 1, wz - 1), world_voxels, chunk_positions)
        c = is_void((x, y - 1, z    ), (wx, wy - 1, wz    ), world_voxels, chunk_positions)
        d = is_void((x, y - 1, z + 1), (wx, wy - 1, wz + 1), world_voxels, chunk_positions)
        e = is_void((x, y    , z + 1), (wx, wy    , wz + 1), world_voxels, chunk_positions)
        f = is_void((x, y + 1, z + 1), (wx, wy + 1, wz + 1), world_voxels, chunk_positions)
        g = is_void((x, y + 1, z    ), (wx, wy + 1, wz    ), world_voxels, chunk_positions)
        h = is_void((x, y + 1, z - 1), (wx, wy + 1, wz - 1), world_voxels, chunk_positions)

    else:  # Z plane
        a = is_void((x - 1, y    , z), (wx - 1, wy    , wz), world_voxels, chunk_positions)
        b = is_void((x - 1, y - 1, z), (wx - 1, wy - 1, wz), world_voxels, chunk_positions)
        c = is_void((x    , y - 1, z), (wx    , wy - 1, wz), world_voxels, chunk_positions)
        d = is_void((x + 1, y - 1, z), (wx + 1, wy - 1, wz), world_voxels, chunk_positions)
        e = is_void((x + 1, y    , z), (wx + 1, wy    , wz), world_voxels, chunk_positions)
        f = is_void((x + 1, y + 1, z), (wx + 1, wy + 1, wz), world_voxels, chunk_positions)
        g = is_void((x    , y + 1, z), (wx    , wy + 1, wz), world_voxels, chunk_positions)
        h = is_void((x - 1, y + 1, z), (wx - 1, wy + 1, wz), world_voxels, chunk_positions)

    ao = (a + b + c), (g + h + a), (e + f + g), (c + d + e)
    return ao


@njit(cache=True)
def pack_data(x, y, z, voxel_id, face_id, ao_id, flip_id):
    # x: 6bit  y: 6bit  z: 6bit  voxel_id: 8bit  face_id: 3bit  ao_id: 2bit  flip_id: 1bit
    a, b, c, d, e, f, g = x, y, z, voxel_id, face_id, ao_id, flip_id

    b_bit, c_bit, d_bit, e_bit, f_bit, g_bit = 6, 6, 8, 3, 2, 1
    fg_bit = f_bit + g_bit
    efg_bit = e_bit + fg_bit
    defg_bit = d_bit + efg_bit
    cdefg_bit = c_bit + defg_bit
    bcdefg_bit = b_bit + cdefg_bit

    packed_data = (
        a << bcdefg_bit |
        b << cdefg_bit |
        c << defg_bit |
        d << efg_bit |
        e << fg_bit |
        f << g_bit | g
    )
    return packed_data


@njit(cache=True)
def get_chunk_index(world_voxel_pos, chunk_positions):
    wx, wy, wz = world_voxel_pos
    cx = wx // CHUNK_SIZE
    cy = wy // CHUNK_SIZE
    cz = wz // CHUNK_SIZE
    if not (0 <= cy < WORLD_H):
        return -1

    index = (cx % WORLD_W) + WORLD_W * (cz % WORLD_D) + WORLD_AREA * (cy % WORLD_H)
    if chunk_positions[index][0] == cx and chunk_positions[index][1] == cy and chunk_positions[index][2] == cz:
        return index
    return -1


@njit(cache=True)
def get_neighbor_voxel_id(local_voxel_pos, world_voxel_pos, world_voxels, chunk_positions):
    chunk_index = get_chunk_index(world_voxel_pos, chunk_positions)
    if chunk_index == -1:
        return 0
    chunk_voxels = world_voxels[chunk_index]

    x, y, z = local_voxel_pos
    voxel_index = x % CHUNK_SIZE + z % CHUNK_SIZE * CHUNK_SIZE + y % CHUNK_SIZE * CHUNK_AREA

    return chunk_voxels[voxel_index]


@njit(cache=True)
def is_void(local_voxel_pos, world_voxel_pos, world_voxels, chunk_positions):
    val = get_neighbor_voxel_id(local_voxel_pos, world_voxel_pos, world_voxels, chunk_positions)
    # 9 is WATER. Water does not cast AO shadows!
    return val == 0 or val == WATER


@njit(cache=True)
def add_data(vertex_data, index, *vertices):
    for vertex in vertices:
        vertex_data[index] = vertex
        index += 1
    return index


@njit(cache=True)
def build_chunk_mesh(chunk_voxels, format_size, chunk_pos, world_voxels, chunk_positions):
    vertex_data = np.empty(CHUNK_VOL * 18 * format_size, dtype='uint32')
    water_data = np.empty(CHUNK_VOL * 18 * format_size, dtype='uint32')
    index = 0
    water_index = 0

    cx, cy, cz = chunk_pos
    mask0 = np.empty((CHUNK_SIZE, CHUNK_SIZE), dtype='uint32')
    mask1 = np.empty((CHUNK_SIZE, CHUNK_SIZE), dtype='uint32')

    # ================== Y PLANES (Top/Bottom) ==================
    for y in range(CHUNK_SIZE):
        mask0.fill(0)
        mask1.fill(0)
        wy = y + cy * CHUNK_SIZE
        for x in range(CHUNK_SIZE):
            wx = x + cx * CHUNK_SIZE
            for z in range(CHUNK_SIZE):
                wz = z + cz * CHUNK_SIZE
                voxel_id = chunk_voxels[x + CHUNK_SIZE * z + CHUNK_AREA * y]
                if not voxel_id: continue

                # top face
                neighbor_id = get_neighbor_voxel_id((x, y + 1, z), (wx, wy + 1, wz), world_voxels, chunk_positions)
                if (voxel_id == WATER and neighbor_id == 0) or (voxel_id != WATER and (neighbor_id == 0 or neighbor_id == WATER)):
                    ao = get_ao((x, y + 1, z), (wx, wy + 1, wz), world_voxels, chunk_positions, plane='Y')
                    flip_id = ao[1] + ao[3] > ao[0] + ao[2]
                    v_id = (voxel_id | 128) if neighbor_id == WATER else voxel_id
                    mask0[x, z] = (v_id << 10) | (ao[0] << 8) | (ao[1] << 6) | (ao[2] << 4) | (ao[3] << 2) | flip_id

                # bottom face
                neighbor_id = get_neighbor_voxel_id((x, y - 1, z), (wx, wy - 1, wz), world_voxels, chunk_positions)
                if (voxel_id == WATER and neighbor_id == 0) or (voxel_id != WATER and (neighbor_id == 0 or neighbor_id == WATER)):
                    ao = get_ao((x, y - 1, z), (wx, wy - 1, wz), world_voxels, chunk_positions, plane='Y')
                    flip_id = ao[1] + ao[3] > ao[0] + ao[2]
                    v_id = (voxel_id | 128) if neighbor_id == WATER else voxel_id
                    mask1[x, z] = (v_id << 10) | (ao[0] << 8) | (ao[1] << 6) | (ao[2] << 4) | (ao[3] << 2) | flip_id

        for x in range(CHUNK_SIZE):
            for z in range(CHUNK_SIZE):
                val = mask0[x, z]
                if val:
                    w, h = 1, 1
                    while x + w < CHUNK_SIZE and mask0[x + w, z] == val: w += 1
                    done = False
                    while z + h < CHUNK_SIZE:
                        for ix in range(w):
                            if mask0[x + ix, z + h] != val: done = True; break
                        if done: break
                        h += 1
                    
                    v_id = (val >> 10) & 0xFF
                    ao0, ao1, ao2, ao3 = (val >> 8) & 3, (val >> 6) & 3, (val >> 4) & 3, (val >> 2) & 3
                    flip_id = val & 1

                    v0 = pack_data(x    , y + 1, z    , v_id, 0, ao0, flip_id)
                    v1 = pack_data(x + w, y + 1, z    , v_id, 0, ao1, flip_id)
                    v2 = pack_data(x + w, y + 1, z + h, v_id, 0, ao2, flip_id)
                    v3 = pack_data(x    , y + 1, z + h, v_id, 0, ao3, flip_id)

                    if v_id == WATER:
                        if flip_id: water_index = add_data(water_data, water_index, v1, v0, v3, v1, v3, v2)
                        else:       water_index = add_data(water_data, water_index, v0, v3, v2, v0, v2, v1)
                    else:
                        if flip_id: index = add_data(vertex_data, index, v1, v0, v3, v1, v3, v2)
                        else:       index = add_data(vertex_data, index, v0, v3, v2, v0, v2, v1)

                    for ix in range(w):
                        for iz in range(h): mask0[x + ix, z + iz] = 0

        for x in range(CHUNK_SIZE):
            for z in range(CHUNK_SIZE):
                val = mask1[x, z]
                if val:
                    w, h = 1, 1
                    while x + w < CHUNK_SIZE and mask1[x + w, z] == val: w += 1
                    done = False
                    while z + h < CHUNK_SIZE:
                        for ix in range(w):
                            if mask1[x + ix, z + h] != val: done = True; break
                        if done: break
                        h += 1
                    
                    v_id = (val >> 10) & 0xFF
                    ao0, ao1, ao2, ao3 = (val >> 8) & 3, (val >> 6) & 3, (val >> 4) & 3, (val >> 2) & 3
                    flip_id = val & 1

                    v0 = pack_data(x    , y, z    , v_id, 1, ao0, flip_id)
                    v1 = pack_data(x + w, y, z    , v_id, 1, ao1, flip_id)
                    v2 = pack_data(x + w, y, z + h, v_id, 1, ao2, flip_id)
                    v3 = pack_data(x    , y, z + h, v_id, 1, ao3, flip_id)

                    if v_id == WATER:
                        if flip_id: water_index = add_data(water_data, water_index, v1, v3, v0, v1, v2, v3)
                        else:       water_index = add_data(water_data, water_index, v0, v2, v3, v0, v1, v2)
                    else:
                        if flip_id: index = add_data(vertex_data, index, v1, v3, v0, v1, v2, v3)
                        else:       index = add_data(vertex_data, index, v0, v2, v3, v0, v1, v2)

                    for ix in range(w):
                        for iz in range(h): mask1[x + ix, z + iz] = 0

    # ================== X PLANES (Right/Left) ==================
    for x in range(CHUNK_SIZE):
        mask0.fill(0)
        mask1.fill(0)
        wx = x + cx * CHUNK_SIZE
        for y in range(CHUNK_SIZE):
            wy = y + cy * CHUNK_SIZE
            for z in range(CHUNK_SIZE):
                wz = z + cz * CHUNK_SIZE
                voxel_id = chunk_voxels[x + CHUNK_SIZE * z + CHUNK_AREA * y]
                if not voxel_id: continue

                neighbor_id = get_neighbor_voxel_id((x + 1, y, z), (wx + 1, wy, wz), world_voxels, chunk_positions)
                if (voxel_id == WATER and neighbor_id == 0) or (voxel_id != WATER and (neighbor_id == 0 or neighbor_id == WATER)):
                    ao = get_ao((x + 1, y, z), (wx + 1, wy, wz), world_voxels, chunk_positions, plane='X')
                    flip_id = ao[1] + ao[3] > ao[0] + ao[2]
                    v_id = (voxel_id | 128) if neighbor_id == WATER else voxel_id
                    mask0[y, z] = (v_id << 10) | (ao[0] << 8) | (ao[1] << 6) | (ao[2] << 4) | (ao[3] << 2) | flip_id

                neighbor_id = get_neighbor_voxel_id((x - 1, y, z), (wx - 1, wy, wz), world_voxels, chunk_positions)
                if (voxel_id == WATER and neighbor_id == 0) or (voxel_id != WATER and (neighbor_id == 0 or neighbor_id == WATER)):
                    ao = get_ao((x - 1, y, z), (wx - 1, wy, wz), world_voxels, chunk_positions, plane='X')
                    flip_id = ao[1] + ao[3] > ao[0] + ao[2]
                    v_id = (voxel_id | 128) if neighbor_id == WATER else voxel_id
                    mask1[y, z] = (v_id << 10) | (ao[0] << 8) | (ao[1] << 6) | (ao[2] << 4) | (ao[3] << 2) | flip_id

        for y in range(CHUNK_SIZE):
            for z in range(CHUNK_SIZE):
                val = mask0[y, z]
                if val:
                    w, h = 1, 1
                    while y + w < CHUNK_SIZE and mask0[y + w, z] == val: w += 1
                    done = False
                    while z + h < CHUNK_SIZE:
                        for iy in range(w):
                            if mask0[y + iy, z + h] != val: done = True; break
                        if done: break
                        h += 1
                    
                    v_id = (val >> 10) & 0xFF
                    ao0, ao1, ao2, ao3 = (val >> 8) & 3, (val >> 6) & 3, (val >> 4) & 3, (val >> 2) & 3
                    flip_id = val & 1

                    v0 = pack_data(x + 1, y    , z    , v_id, 2, ao0, flip_id)
                    v1 = pack_data(x + 1, y + w, z    , v_id, 2, ao1, flip_id)
                    v2 = pack_data(x + 1, y + w, z + h, v_id, 2, ao2, flip_id)
                    v3 = pack_data(x + 1, y    , z + h, v_id, 2, ao3, flip_id)

                    if v_id == WATER:
                        if flip_id: water_index = add_data(water_data, water_index, v3, v0, v1, v3, v1, v2)
                        else:       water_index = add_data(water_data, water_index, v0, v1, v2, v0, v2, v3)
                    else:
                        if flip_id: index = add_data(vertex_data, index, v3, v0, v1, v3, v1, v2)
                        else:       index = add_data(vertex_data, index, v0, v1, v2, v0, v2, v3)

                    for iy in range(w):
                        for iz in range(h): mask0[y + iy, z + iz] = 0

        for y in range(CHUNK_SIZE):
            for z in range(CHUNK_SIZE):
                val = mask1[y, z]
                if val:
                    w, h = 1, 1
                    while y + w < CHUNK_SIZE and mask1[y + w, z] == val: w += 1
                    done = False
                    while z + h < CHUNK_SIZE:
                        for iy in range(w):
                            if mask1[y + iy, z + h] != val: done = True; break
                        if done: break
                        h += 1
                    
                    v_id = (val >> 10) & 0xFF
                    ao0, ao1, ao2, ao3 = (val >> 8) & 3, (val >> 6) & 3, (val >> 4) & 3, (val >> 2) & 3
                    flip_id = val & 1

                    v0 = pack_data(x, y    , z    , v_id, 3, ao0, flip_id)
                    v1 = pack_data(x, y + w, z    , v_id, 3, ao1, flip_id)
                    v2 = pack_data(x, y + w, z + h, v_id, 3, ao2, flip_id)
                    v3 = pack_data(x, y    , z + h, v_id, 3, ao3, flip_id)

                    if v_id == WATER:
                        if flip_id: water_index = add_data(water_data, water_index, v3, v1, v0, v3, v2, v1)
                        else:       water_index = add_data(water_data, water_index, v0, v2, v1, v0, v3, v2)
                    else:
                        if flip_id: index = add_data(vertex_data, index, v3, v1, v0, v3, v2, v1)
                        else:       index = add_data(vertex_data, index, v0, v2, v1, v0, v3, v2)

                    for iy in range(w):
                        for iz in range(h): mask1[y + iy, z + iz] = 0

    # ================== Z PLANES (Back/Front) ==================
    for z in range(CHUNK_SIZE):
        mask0.fill(0)
        mask1.fill(0)
        wz = z + cz * CHUNK_SIZE
        for x in range(CHUNK_SIZE):
            wx = x + cx * CHUNK_SIZE
            for y in range(CHUNK_SIZE):
                wy = y + cy * CHUNK_SIZE
                voxel_id = chunk_voxels[x + CHUNK_SIZE * z + CHUNK_AREA * y]
                if not voxel_id: continue

                neighbor_id = get_neighbor_voxel_id((x, y, z - 1), (wx, wy, wz - 1), world_voxels, chunk_positions)
                if (voxel_id == WATER and neighbor_id == 0) or (voxel_id != WATER and (neighbor_id == 0 or neighbor_id == WATER)):
                    ao = get_ao((x, y, z - 1), (wx, wy, wz - 1), world_voxels, chunk_positions, plane='Z')
                    flip_id = ao[1] + ao[3] > ao[0] + ao[2]
                    v_id = (voxel_id | 128) if neighbor_id == WATER else voxel_id
                    mask0[x, y] = (v_id << 10) | (ao[0] << 8) | (ao[1] << 6) | (ao[2] << 4) | (ao[3] << 2) | flip_id

                neighbor_id = get_neighbor_voxel_id((x, y, z + 1), (wx, wy, wz + 1), world_voxels, chunk_positions)
                if (voxel_id == WATER and neighbor_id == 0) or (voxel_id != WATER and (neighbor_id == 0 or neighbor_id == WATER)):
                    ao = get_ao((x, y, z + 1), (wx, wy, wz + 1), world_voxels, chunk_positions, plane='Z')
                    flip_id = ao[1] + ao[3] > ao[0] + ao[2]
                    v_id = (voxel_id | 128) if neighbor_id == WATER else voxel_id
                    mask1[x, y] = (v_id << 10) | (ao[0] << 8) | (ao[1] << 6) | (ao[2] << 4) | (ao[3] << 2) | flip_id

        for x in range(CHUNK_SIZE):
            for y in range(CHUNK_SIZE):
                val = mask0[x, y]
                if val:
                    w, h = 1, 1
                    while x + w < CHUNK_SIZE and mask0[x + w, y] == val: w += 1
                    done = False
                    while y + h < CHUNK_SIZE:
                        for ix in range(w):
                            if mask0[x + ix, y + h] != val: done = True; break
                        if done: break
                        h += 1
                    
                    v_id = (val >> 10) & 0xFF
                    ao0, ao1, ao2, ao3 = (val >> 8) & 3, (val >> 6) & 3, (val >> 4) & 3, (val >> 2) & 3
                    flip_id = val & 1

                    v0 = pack_data(x    , y    , z, v_id, 4, ao0, flip_id)
                    v1 = pack_data(x    , y + h, z, v_id, 4, ao1, flip_id)
                    v2 = pack_data(x + w, y + h, z, v_id, 4, ao2, flip_id)
                    v3 = pack_data(x + w, y    , z, v_id, 4, ao3, flip_id)

                    if v_id == WATER:
                        if flip_id: water_index = add_data(water_data, water_index, v3, v0, v1, v3, v1, v2)
                        else:       water_index = add_data(water_data, water_index, v0, v1, v2, v0, v2, v3)
                    else:
                        if flip_id: index = add_data(vertex_data, index, v3, v0, v1, v3, v1, v2)
                        else:       index = add_data(vertex_data, index, v0, v1, v2, v0, v2, v3)

                    for ix in range(w):
                        for iy in range(h): mask0[x + ix, y + iy] = 0

        for x in range(CHUNK_SIZE):
            for y in range(CHUNK_SIZE):
                val = mask1[x, y]
                if val:
                    w, h = 1, 1
                    while x + w < CHUNK_SIZE and mask1[x + w, y] == val: w += 1
                    done = False
                    while y + h < CHUNK_SIZE:
                        for ix in range(w):
                            if mask1[x + ix, y + h] != val: done = True; break
                        if done: break
                        h += 1
                    
                    v_id = (val >> 10) & 0xFF
                    ao0, ao1, ao2, ao3 = (val >> 8) & 3, (val >> 6) & 3, (val >> 4) & 3, (val >> 2) & 3
                    flip_id = val & 1

                    v0 = pack_data(x    , y    , z + 1, v_id, 5, ao0, flip_id)
                    v1 = pack_data(x    , y + h, z + 1, v_id, 5, ao1, flip_id)
                    v2 = pack_data(x + w, y + h, z + 1, v_id, 5, ao2, flip_id)
                    v3 = pack_data(x + w, y    , z + 1, v_id, 5, ao3, flip_id)

                    if v_id == WATER:
                        if flip_id: water_index = add_data(water_data, water_index, v3, v1, v0, v3, v2, v1)
                        else:       water_index = add_data(water_data, water_index, v0, v2, v1, v0, v3, v2)
                    else:
                        if flip_id: index = add_data(vertex_data, index, v3, v1, v0, v3, v2, v1)
                        else:       index = add_data(vertex_data, index, v0, v2, v1, v0, v3, v2)

                    for ix in range(w):
                        for iy in range(h): mask1[x + ix, y + iy] = 0

    opaque_mesh = vertex_data[:index]
    water_mesh = water_data[:water_index]
    combined_mesh = np.hstack((opaque_mesh, water_mesh))
    return combined_mesh, index // format_size, water_index // format_size

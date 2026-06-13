"""
Numba-optimized Greedy Meshing algorithm and lighting evaluation.

This module scans 3D voxel arrays and mathematically combines adjacent, coplanar
block faces into massive single polygons to drastically reduce GPU draw calls.
It evaluates Ambient Occlusion (AO) and volumetric Breadth-First Search (BFS)
lighting at every vertex lock-free across multiple CPU threads.
"""

from typing import Any, Tuple

import numpy as np
from numba import njit

from settings import (
    AIR,
    CHUNK_AREA,
    CHUNK_SIZE,
    CHUNK_VOLUME,
    GLASS,
    LEAVES,
    WATER,
    WORLD_AREA,
    WORLD_DEPTH,
    WORLD_HEIGHT,
    WORLD_WIDTH,
)


@njit(cache=True, nogil=True)
def get_ao(
    local_pos: Tuple[int, int, int],
    world_pos: Tuple[int, int, int],
    chunk_voxels: Any,
    world_voxels: Any,
    chunk_positions: Any,
    plane: str,
) -> Tuple[int, int, int, int]:
    """
    Calculates the ambient occlusion (AO) value for a specific vertex on a block face.
    It checks the surrounding blocks in the specified plane to determine how occluded
    the corner is, returning a tuple of AO values for the four vertices of the face.
    """
    x, y, z = local_pos
    wx, wy, wz = world_pos

    if plane == 'Y':
        a = is_void((x, y, z - 1), (wx, wy, wz - 1), chunk_voxels, world_voxels, chunk_positions)
        b = is_void((x - 1, y, z - 1), (wx - 1, wy, wz - 1), chunk_voxels, world_voxels, chunk_positions)
        c = is_void((x - 1, y, z), (wx - 1, wy, wz), chunk_voxels, world_voxels, chunk_positions)
        d = is_void((x - 1, y, z + 1), (wx - 1, wy, wz + 1), chunk_voxels, world_voxels, chunk_positions)
        e = is_void((x, y, z + 1), (wx, wy, wz + 1), chunk_voxels, world_voxels, chunk_positions)
        f = is_void((x + 1, y, z + 1), (wx + 1, wy, wz + 1), chunk_voxels, world_voxels, chunk_positions)
        g = is_void((x + 1, y, z), (wx + 1, wy, wz), chunk_voxels, world_voxels, chunk_positions)
        h = is_void((x + 1, y, z - 1), (wx + 1, wy, wz - 1), chunk_voxels, world_voxels, chunk_positions)

    elif plane == 'X':
        a = is_void((x, y, z - 1), (wx, wy, wz - 1), chunk_voxels, world_voxels, chunk_positions)
        b = is_void((x, y - 1, z - 1), (wx, wy - 1, wz - 1), chunk_voxels, world_voxels, chunk_positions)
        c = is_void((x, y - 1, z), (wx, wy - 1, wz), chunk_voxels, world_voxels, chunk_positions)
        d = is_void((x, y - 1, z + 1), (wx, wy - 1, wz + 1), chunk_voxels, world_voxels, chunk_positions)
        e = is_void((x, y, z + 1), (wx, wy, wz + 1), chunk_voxels, world_voxels, chunk_positions)
        f = is_void((x, y + 1, z + 1), (wx, wy + 1, wz + 1), chunk_voxels, world_voxels, chunk_positions)
        g = is_void((x, y + 1, z), (wx, wy + 1, wz), chunk_voxels, world_voxels, chunk_positions)
        h = is_void((x, y + 1, z - 1), (wx, wy + 1, wz - 1), chunk_voxels, world_voxels, chunk_positions)

    else:  # Z plane
        a = is_void((x - 1, y, z), (wx - 1, wy, wz), chunk_voxels, world_voxels, chunk_positions)
        b = is_void((x - 1, y - 1, z), (wx - 1, wy - 1, wz), chunk_voxels, world_voxels, chunk_positions)
        c = is_void((x, y - 1, z), (wx, wy - 1, wz), chunk_voxels, world_voxels, chunk_positions)
        d = is_void((x + 1, y - 1, z), (wx + 1, wy - 1, wz), chunk_voxels, world_voxels, chunk_positions)
        e = is_void((x + 1, y, z), (wx + 1, wy, wz), chunk_voxels, world_voxels, chunk_positions)
        f = is_void((x + 1, y + 1, z), (wx + 1, wy + 1, wz), chunk_voxels, world_voxels, chunk_positions)
        g = is_void((x, y + 1, z), (wx, wy + 1, wz), chunk_voxels, world_voxels, chunk_positions)
        h = is_void((x - 1, y + 1, z), (wx - 1, wy + 1, wz), chunk_voxels, world_voxels, chunk_positions)

    ao = (a + b + c), (g + h + a), (e + f + g), (c + d + e)
    return ao


@njit(cache=True, nogil=True)
def get_vertex_light(
    local_vertex_pos: Tuple[int, int, int],
    world_vertex_pos: Tuple[int, int, int],
    plane: str,
    face_light: int,
    chunk_voxels: Any,
    chunk_lightmap: Any,
    world_voxels: Any,
    world_lightmaps: Any,
    chunk_positions: Any,
) -> int:
    """
    Computes the smoothed lighting value for a specific vertex by sampling and averaging
    the sunlight and blocklight from the four surrounding blocks that share the vertex
    in the given plane.
    """
    lx, ly, lz = local_vertex_pos
    vx, vy, vz = world_vertex_pos

    if plane == 'Y':
        # Vertex is on an XZ plane, so we sample the 4 adjacent blocks in that plane.
        b0 = get_neighbor_voxel_id((lx, ly, lz), (vx, vy, vz), chunk_voxels, world_voxels, chunk_positions)
        b1 = get_neighbor_voxel_id((lx - 1, ly, lz), (vx - 1, vy, vz), chunk_voxels, world_voxels, chunk_positions)
        b2 = get_neighbor_voxel_id((lx, ly, lz - 1), (vx, vy, vz - 1), chunk_voxels, world_voxels, chunk_positions)
        b3 = get_neighbor_voxel_id(
            (lx - 1, ly, lz - 1), (vx - 1, vy, vz - 1), chunk_voxels, world_voxels, chunk_positions
        )

        l0 = (
            face_light
            if not is_transparent(b0)
            else get_neighbor_light((lx, ly, lz), (vx, vy, vz), chunk_lightmap, world_lightmaps, chunk_positions)
        )
        l1 = (
            face_light
            if not is_transparent(b1)
            else get_neighbor_light(
                (lx - 1, ly, lz), (vx - 1, vy, vz), chunk_lightmap, world_lightmaps, chunk_positions
            )
        )
        l2 = (
            face_light
            if not is_transparent(b2)
            else get_neighbor_light(
                (lx, ly, lz - 1), (vx, vy, vz - 1), chunk_lightmap, world_lightmaps, chunk_positions
            )
        )
        l3 = (
            face_light
            if not is_transparent(b3)
            else get_neighbor_light(
                (lx - 1, ly, lz - 1), (vx - 1, vy, vz - 1), chunk_lightmap, world_lightmaps, chunk_positions
            )
        )

    elif plane == 'X':
        # Vertex is on a YZ plane
        b0 = get_neighbor_voxel_id((lx, ly, lz), (vx, vy, vz), chunk_voxels, world_voxels, chunk_positions)
        b1 = get_neighbor_voxel_id((lx, ly - 1, lz), (vx, vy - 1, vz), chunk_voxels, world_voxels, chunk_positions)
        b2 = get_neighbor_voxel_id((lx, ly, lz - 1), (vx, vy, vz - 1), chunk_voxels, world_voxels, chunk_positions)
        b3 = get_neighbor_voxel_id(
            (lx, ly - 1, lz - 1), (vx, vy - 1, vz - 1), chunk_voxels, world_voxels, chunk_positions
        )

        l0 = (
            face_light
            if not is_transparent(b0)
            else get_neighbor_light((lx, ly, lz), (vx, vy, vz), chunk_lightmap, world_lightmaps, chunk_positions)
        )
        l1 = (
            face_light
            if not is_transparent(b1)
            else get_neighbor_light(
                (lx, ly - 1, lz), (vx, vy - 1, vz), chunk_lightmap, world_lightmaps, chunk_positions
            )
        )
        l2 = (
            face_light
            if not is_transparent(b2)
            else get_neighbor_light(
                (lx, ly, lz - 1), (vx, vy, vz - 1), chunk_lightmap, world_lightmaps, chunk_positions
            )
        )
        l3 = (
            face_light
            if not is_transparent(b3)
            else get_neighbor_light(
                (lx, ly - 1, lz - 1), (vx, vy - 1, vz - 1), chunk_lightmap, world_lightmaps, chunk_positions
            )
        )

    else:  # Z plane
        # Vertex is on an XY plane
        b0 = get_neighbor_voxel_id((lx, ly, lz), (vx, vy, vz), chunk_voxels, world_voxels, chunk_positions)
        b1 = get_neighbor_voxel_id((lx - 1, ly, lz), (vx - 1, vy, vz), chunk_voxels, world_voxels, chunk_positions)
        b2 = get_neighbor_voxel_id((lx, ly - 1, lz), (vx, vy - 1, vz), chunk_voxels, world_voxels, chunk_positions)
        b3 = get_neighbor_voxel_id(
            (lx - 1, ly - 1, lz), (vx - 1, vy - 1, vz), chunk_voxels, world_voxels, chunk_positions
        )

        l0 = (
            face_light
            if not is_transparent(b0)
            else get_neighbor_light((lx, ly, lz), (vx, vy, vz), chunk_lightmap, world_lightmaps, chunk_positions)
        )
        l1 = (
            face_light
            if not is_transparent(b1)
            else get_neighbor_light(
                (lx - 1, ly, lz), (vx - 1, vy, vz), chunk_lightmap, world_lightmaps, chunk_positions
            )
        )
        l2 = (
            face_light
            if not is_transparent(b2)
            else get_neighbor_light(
                (lx, ly - 1, lz), (vx, vy - 1, vz), chunk_lightmap, world_lightmaps, chunk_positions
            )
        )
        l3 = (
            face_light
            if not is_transparent(b3)
            else get_neighbor_light(
                (lx - 1, ly - 1, lz), (vx - 1, vy - 1, vz), chunk_lightmap, world_lightmaps, chunk_positions
            )
        )

    # Average the Sun and Block light separately to prevent overflow and incorrect mixing.
    sun = ((l0 >> 4) + (l1 >> 4) + (l2 >> 4) + (l3 >> 4)) >> 2
    block = ((l0 & 15) + (l1 & 15) + (l2 & 15) + (l3 & 15)) >> 2

    return int((sun << 4) | block)


@njit(cache=True, nogil=True)
def pack_data(
    x: int, y: int, z: int, voxel_id: int, face_id: int, ao_id: int, flip_id: int, light_val: int
) -> Tuple[int, int]:
    """
    Packs multiple pieces of vertex data (coordinates, voxel ID, face ID, AO ID, flip ID)
    into a single 32-bit unsigned integer to minimize memory usage and GPU bandwidth.
    """
    # x: 6bit  y: 6bit  z: 6bit  voxel_id: 8bit  face_id: 3bit  ao_id: 2bit  flip_id: 1bit
    a, b, c, d, e, f, g = x, y, z, voxel_id, face_id, ao_id, flip_id

    b_bit, c_bit, d_bit, e_bit, f_bit, g_bit = 6, 6, 8, 3, 2, 1
    fg_bit = f_bit + g_bit
    efg_bit = e_bit + fg_bit
    defg_bit = d_bit + efg_bit
    cdefg_bit = c_bit + defg_bit
    bcdefg_bit = b_bit + cdefg_bit

    packed_data = a << bcdefg_bit | b << cdefg_bit | c << defg_bit | d << efg_bit | e << fg_bit | f << g_bit | g

    return packed_data, light_val


@njit(cache=True, nogil=True)
def get_chunk_index(world_voxel_pos: Tuple[int, int, int], chunk_positions: Any) -> int:
    """
    Calculates the 1D index of a chunk in the global world arrays based on an absolute
    world voxel coordinate. Returns -1 if the chunk is not currently loaded or out of bounds.
    """
    wx, wy, wz = world_voxel_pos
    cx = wx // CHUNK_SIZE
    cy = wy // CHUNK_SIZE
    cz = wz // CHUNK_SIZE

    if not (0 <= cy < WORLD_HEIGHT):
        return -1

    index = (cx % WORLD_WIDTH) + WORLD_WIDTH * (cz % WORLD_DEPTH) + WORLD_AREA * (cy % WORLD_HEIGHT)

    if chunk_positions[index][0] == cx and chunk_positions[index][1] == cy and chunk_positions[index][2] == cz:
        return index

    return -1


@njit(cache=True, nogil=True)
def get_neighbor_voxel_id(
    local_voxel_pos: Tuple[int, int, int],
    world_voxel_pos: Tuple[int, int, int],
    chunk_voxels: Any,
    world_voxels: Any,
    chunk_positions: Any,
) -> int:
    """
    Retrieves the voxel ID of a neighboring block given its local and world coordinates.
    Safely handles cross-chunk boundaries by looking up the appropriate chunk in the world arrays.
    """
    x, y, z = local_voxel_pos
    if 0 <= x < CHUNK_SIZE and 0 <= y < CHUNK_SIZE and 0 <= z < CHUNK_SIZE:
        return int(chunk_voxels[x + z * CHUNK_SIZE + y * CHUNK_AREA])

    chunk_index = get_chunk_index(world_voxel_pos, chunk_positions)

    if chunk_index == -1:
        return 0

    chunk_voxels_global = world_voxels[chunk_index]

    lx = world_voxel_pos[0] % CHUNK_SIZE
    ly = world_voxel_pos[1] % CHUNK_SIZE
    lz = world_voxel_pos[2] % CHUNK_SIZE
    voxel_index = lx + lz * CHUNK_SIZE + ly * CHUNK_AREA

    return int(chunk_voxels_global[voxel_index])


@njit(cache=True, nogil=True)
def get_neighbor_light(
    local_voxel_pos: Tuple[int, int, int],
    world_voxel_pos: Tuple[int, int, int],
    chunk_lightmap: Any,
    world_lightmaps: Any,
    chunk_positions: Any,
) -> int:
    """
    Retrieves the packed lighting value (sunlight and blocklight) of a neighboring block
    given its local and world coordinates, safely crossing chunk boundaries if needed.
    """
    x, y, z = local_voxel_pos
    if 0 <= x < CHUNK_SIZE and 0 <= y < CHUNK_SIZE and 0 <= z < CHUNK_SIZE:
        return int(chunk_lightmap[x + z * CHUNK_SIZE + y * CHUNK_AREA])

    chunk_index = get_chunk_index(world_voxel_pos, chunk_positions)

    if chunk_index == -1:
        return 255

    chunk_lights_global = world_lightmaps[chunk_index]

    lx = world_voxel_pos[0] % CHUNK_SIZE
    ly = world_voxel_pos[1] % CHUNK_SIZE
    lz = world_voxel_pos[2] % CHUNK_SIZE
    voxel_index = lx + lz * CHUNK_SIZE + ly * CHUNK_AREA

    return int(chunk_lights_global[voxel_index])


@njit(cache=True, nogil=True)
def is_transparent(voxel_id: int) -> bool:
    """
    Checks if a given voxel ID corresponds to a transparent block (like air, water, glass, or leaves).
    Transparent blocks do not cull adjacent faces and do not cast hard ambient occlusion shadows.
    """
    return voxel_id == AIR or voxel_id == WATER or voxel_id == GLASS or voxel_id == LEAVES


@njit(cache=True, nogil=True)
def is_void(
    local_voxel_pos: Tuple[int, int, int],
    world_voxel_pos: Tuple[int, int, int],
    chunk_voxels: Any,
    world_voxels: Any,
    chunk_positions: Any,
) -> bool:
    """
    Determines if a block at a given coordinate is empty or transparent, which is used
    specifically during the ambient occlusion calculation to see if a corner is occluded.
    """
    val = get_neighbor_voxel_id(local_voxel_pos, world_voxel_pos, chunk_voxels, world_voxels, chunk_positions)

    # Transparent blocks do not cast AO shadows!
    return bool(is_transparent(val))


@njit(cache=True, nogil=True)
def add_data(vertex_data: Any, index: int, *vertices: Tuple[int, int]) -> int:
    """
    Appends newly packed vertex data and its associated lighting value into the main
    mesh arrays, advancing the current index counter.
    """
    for vertex in vertices:
        vertex_data[index] = vertex[0]
        vertex_data[index + 1] = vertex[1]
        index += 2

    return index


@njit(cache=True, nogil=True)
def build_chunk_mesh(
    chunk_voxels: Any,
    chunk_lightmap: Any,
    format_size: int,
    chunk_pos: Tuple[int, int, int],
    world_voxels: Any,
    world_lightmaps: Any,
    chunk_positions: Any,
) -> Tuple[Any, int, int]:
    """
    The core greedy meshing algorithm. It scans through a chunk's voxel data slice by slice
    along the X, Y, and Z planes. It groups adjacent, identical, and coplanar block faces
    into massive single polygons, calculating ambient occlusion and smoothed lighting
    along the way. Returns the combined vertex data for both opaque and water meshes.
    """
    vertex_data = np.empty(CHUNK_VOLUME * 18 * format_size, dtype='uint32')
    water_data = np.empty(CHUNK_VOLUME * 18 * format_size, dtype='uint32')
    index = 0
    water_index = 0

    cx, cy, cz = chunk_pos
    mask0 = np.zeros((CHUNK_SIZE, CHUNK_SIZE), dtype=np.uint64)
    mask1 = np.zeros((CHUNK_SIZE, CHUNK_SIZE), dtype=np.uint64)

    # ================== Y PLANES (Top/Bottom) ==================
    for y in range(CHUNK_SIZE):
        wy = y + cy * CHUNK_SIZE

        for x in range(CHUNK_SIZE):
            wx = x + cx * CHUNK_SIZE

            for z in range(CHUNK_SIZE):
                wz = z + cz * CHUNK_SIZE

                voxel_id = chunk_voxels[x + CHUNK_SIZE * z + CHUNK_AREA * y]

                if not voxel_id:
                    continue

                # top face
                neighbor_id = get_neighbor_voxel_id(
                    (x, y + 1, z), (wx, wy + 1, wz), chunk_voxels, world_voxels, chunk_positions
                )

                if is_transparent(neighbor_id) and voxel_id != neighbor_id:
                    ao = get_ao((x, y + 1, z), (wx, wy + 1, wz), chunk_voxels, world_voxels, chunk_positions, plane='Y')

                    # flip_id = ao[1] + ao[3] > ao[0] + ao[2]
                    v_id = (voxel_id | 128) if neighbor_id == WATER else voxel_id

                    face_light = get_neighbor_light(
                        (x, y + 1, z), (wx, wy + 1, wz), chunk_lightmap, world_lightmaps, chunk_positions
                    )
                    l0 = get_vertex_light(
                        (x, y + 1, z),
                        (wx, wy + 1, wz),
                        'Y',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    l1 = get_vertex_light(
                        (x + 1, y + 1, z),
                        (wx + 1, wy + 1, wz),
                        'Y',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    l2 = get_vertex_light(
                        (x + 1, y + 1, z + 1),
                        (wx + 1, wy + 1, wz + 1),
                        'Y',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    l3 = get_vertex_light(
                        (x, y + 1, z + 1),
                        (wx, wy + 1, wz + 1),
                        'Y',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )

                    flip_id = ((l1 >> 4) + (l1 & 15) + ao[1]) + ((l3 >> 4) + (l3 & 15) + ao[3]) > (
                        (l0 >> 4) + (l0 & 15) + ao[0]
                    ) + ((l2 >> 4) + (l2 & 15) + ao[2])
                    mask0[x, z] = (
                        (np.uint64(v_id) << 41)
                        | (np.uint64(l0) << 33)
                        | (np.uint64(l1) << 25)
                        | (np.uint64(l2) << 17)
                        | (np.uint64(l3) << 9)
                        | (np.uint64(ao[0]) << 7)
                        | (np.uint64(ao[1]) << 5)
                        | (np.uint64(ao[2]) << 3)
                        | (np.uint64(ao[3]) << 1)
                        | np.uint64(flip_id)
                    )

                # bottom face
                neighbor_id = get_neighbor_voxel_id(
                    (x, y - 1, z), (wx, wy - 1, wz), chunk_voxels, world_voxels, chunk_positions
                )

                if is_transparent(neighbor_id) and voxel_id != neighbor_id:
                    ao = get_ao((x, y - 1, z), (wx, wy - 1, wz), chunk_voxels, world_voxels, chunk_positions, plane='Y')

                    # flip_id = ao[1] + ao[3] > ao[0] + ao[2]
                    v_id = (voxel_id | 128) if neighbor_id == WATER else voxel_id

                    face_light = get_neighbor_light(
                        (x, y - 1, z), (wx, wy - 1, wz), chunk_lightmap, world_lightmaps, chunk_positions
                    )
                    l0 = get_vertex_light(
                        (x, y, z),
                        (wx, wy, wz),
                        'Y',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    l1 = get_vertex_light(
                        (x + 1, y, z),
                        (wx + 1, wy, wz),
                        'Y',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    l2 = get_vertex_light(
                        (x + 1, y, z + 1),
                        (wx + 1, wy, wz + 1),
                        'Y',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    l3 = get_vertex_light(
                        (x, y, z + 1),
                        (wx, wy, wz + 1),
                        'Y',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )

                    flip_id = ((l1 >> 4) + (l1 & 15) + ao[1]) + ((l3 >> 4) + (l3 & 15) + ao[3]) > (
                        (l0 >> 4) + (l0 & 15) + ao[0]
                    ) + ((l2 >> 4) + (l2 & 15) + ao[2])
                    mask1[x, z] = (
                        (np.uint64(v_id) << 41)
                        | (np.uint64(l0) << 33)
                        | (np.uint64(l1) << 25)
                        | (np.uint64(l2) << 17)
                        | (np.uint64(l3) << 9)
                        | (np.uint64(ao[0]) << 7)
                        | (np.uint64(ao[1]) << 5)
                        | (np.uint64(ao[2]) << 3)
                        | (np.uint64(ao[3]) << 1)
                        | np.uint64(flip_id)
                    )

        for x in range(CHUNK_SIZE):
            for z in range(CHUNK_SIZE):
                val = mask0[x, z]

                if val:
                    w, h = 1, 1

                    while x + w < CHUNK_SIZE and mask0[x + w, z] == val:
                        w += 1

                    done = False

                    while z + h < CHUNK_SIZE:
                        for ix in range(w):
                            if mask0[x + ix, z + h] != val:
                                done = True
                                break

                        if done:
                            break
                        h += 1

                    v_id = int((val >> 41) & 0xFF)
                    l0 = int((val >> 33) & 0xFF)
                    l1 = int((val >> 25) & 0xFF)
                    l2 = int((val >> 17) & 0xFF)
                    l3 = int((val >> 9) & 0xFF)

                    ao0 = int((val >> 7) & 3)
                    ao1 = int((val >> 5) & 3)
                    ao2 = int((val >> 3) & 3)
                    ao3 = int((val >> 1) & 3)
                    flip_id = int(val & 1)

                    v0 = pack_data(x, y + 1, z, v_id, 0, ao0, flip_id, l0)
                    v1 = pack_data(x + w, y + 1, z, v_id, 0, ao1, flip_id, l1)
                    v2 = pack_data(x + w, y + 1, z + h, v_id, 0, ao2, flip_id, l2)
                    v3 = pack_data(x, y + 1, z + h, v_id, 0, ao3, flip_id, l3)

                    if v_id == WATER:
                        if flip_id:
                            water_index = add_data(water_data, water_index, v1, v0, v3, v1, v3, v2)
                        else:
                            water_index = add_data(water_data, water_index, v0, v3, v2, v0, v2, v1)

                    else:
                        if flip_id:
                            index = add_data(vertex_data, index, v1, v0, v3, v1, v3, v2)
                        else:
                            index = add_data(vertex_data, index, v0, v3, v2, v0, v2, v1)

                    for ix in range(w):
                        for iz in range(h):
                            mask0[x + ix, z + iz] = 0

        for x in range(CHUNK_SIZE):
            for z in range(CHUNK_SIZE):
                val = mask1[x, z]

                if val:
                    w, h = 1, 1

                    while x + w < CHUNK_SIZE and mask1[x + w, z] == val:
                        w += 1

                    done = False

                    while z + h < CHUNK_SIZE:
                        for ix in range(w):
                            if mask1[x + ix, z + h] != val:
                                done = True
                                break

                        if done:
                            break

                        h += 1

                    v_id = int((val >> 41) & 0xFF)
                    l0 = int((val >> 33) & 0xFF)
                    l1 = int((val >> 25) & 0xFF)
                    l2 = int((val >> 17) & 0xFF)
                    l3 = int((val >> 9) & 0xFF)

                    ao0 = int((val >> 7) & 3)
                    ao1 = int((val >> 5) & 3)
                    ao2 = int((val >> 3) & 3)
                    ao3 = int((val >> 1) & 3)
                    flip_id = int(val & 1)

                    v0 = pack_data(x, y, z, v_id, 1, ao0, flip_id, l0)
                    v1 = pack_data(x + w, y, z, v_id, 1, ao1, flip_id, l1)
                    v2 = pack_data(x + w, y, z + h, v_id, 1, ao2, flip_id, l2)
                    v3 = pack_data(x, y, z + h, v_id, 1, ao3, flip_id, l3)

                    if v_id == WATER:
                        if flip_id:
                            water_index = add_data(water_data, water_index, v1, v3, v0, v1, v2, v3)
                        else:
                            water_index = add_data(water_data, water_index, v0, v2, v3, v0, v1, v2)

                    else:
                        if flip_id:
                            index = add_data(vertex_data, index, v1, v3, v0, v1, v2, v3)
                        else:
                            index = add_data(vertex_data, index, v0, v2, v3, v0, v1, v2)

                    for ix in range(w):
                        for iz in range(h):
                            mask1[x + ix, z + iz] = 0

    # ================== X PLANES (Right/Left) ==================
    for x in range(CHUNK_SIZE):
        wx = x + cx * CHUNK_SIZE

        for y in range(CHUNK_SIZE):
            wy = y + cy * CHUNK_SIZE

            for z in range(CHUNK_SIZE):
                wz = z + cz * CHUNK_SIZE

                voxel_id = chunk_voxels[x + CHUNK_SIZE * z + CHUNK_AREA * y]

                if not voxel_id:
                    continue

                neighbor_id = get_neighbor_voxel_id(
                    (x + 1, y, z), (wx + 1, wy, wz), chunk_voxels, world_voxels, chunk_positions
                )

                if is_transparent(neighbor_id) and voxel_id != neighbor_id:
                    ao = get_ao((x + 1, y, z), (wx + 1, wy, wz), chunk_voxels, world_voxels, chunk_positions, plane='X')

                    # flip_id = ao[1] + ao[3] > ao[0] + ao[2]
                    v_id = (voxel_id | 128) if neighbor_id == WATER else voxel_id

                    face_light = get_neighbor_light(
                        (x + 1, y, z), (wx + 1, wy, wz), chunk_lightmap, world_lightmaps, chunk_positions
                    )
                    l0 = get_vertex_light(
                        (x + 1, y, z),
                        (wx + 1, wy, wz),
                        'X',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    l1 = get_vertex_light(
                        (x + 1, y + 1, z),
                        (wx + 1, wy + 1, wz),
                        'X',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    l2 = get_vertex_light(
                        (x + 1, y + 1, z + 1),
                        (wx + 1, wy + 1, wz + 1),
                        'X',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    l3 = get_vertex_light(
                        (x + 1, y, z + 1),
                        (wx + 1, wy, wz + 1),
                        'X',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )

                    flip_id = ((l1 >> 4) + (l1 & 15) + ao[1]) + ((l3 >> 4) + (l3 & 15) + ao[3]) > (
                        (l0 >> 4) + (l0 & 15) + ao[0]
                    ) + ((l2 >> 4) + (l2 & 15) + ao[2])
                    mask0[y, z] = (
                        (np.uint64(v_id) << 41)
                        | (np.uint64(l0) << 33)
                        | (np.uint64(l1) << 25)
                        | (np.uint64(l2) << 17)
                        | (np.uint64(l3) << 9)
                        | (np.uint64(ao[0]) << 7)
                        | (np.uint64(ao[1]) << 5)
                        | (np.uint64(ao[2]) << 3)
                        | (np.uint64(ao[3]) << 1)
                        | np.uint64(flip_id)
                    )

                neighbor_id = get_neighbor_voxel_id(
                    (x - 1, y, z), (wx - 1, wy, wz), chunk_voxels, world_voxels, chunk_positions
                )

                if is_transparent(neighbor_id) and voxel_id != neighbor_id:
                    ao = get_ao((x - 1, y, z), (wx - 1, wy, wz), chunk_voxels, world_voxels, chunk_positions, plane='X')

                    # flip_id = ao[1] + ao[3] > ao[0] + ao[2]
                    v_id = (voxel_id | 128) if neighbor_id == WATER else voxel_id

                    face_light = get_neighbor_light(
                        (x - 1, y, z), (wx - 1, wy, wz), chunk_lightmap, world_lightmaps, chunk_positions
                    )
                    l0 = get_vertex_light(
                        (x, y, z),
                        (wx, wy, wz),
                        'X',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    l1 = get_vertex_light(
                        (x, y + 1, z),
                        (wx, wy + 1, wz),
                        'X',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    l2 = get_vertex_light(
                        (x, y + 1, z + 1),
                        (wx, wy + 1, wz + 1),
                        'X',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    l3 = get_vertex_light(
                        (x, y, z + 1),
                        (wx, wy, wz + 1),
                        'X',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )

                    flip_id = ((l1 >> 4) + (l1 & 15) + ao[1]) + ((l3 >> 4) + (l3 & 15) + ao[3]) > (
                        (l0 >> 4) + (l0 & 15) + ao[0]
                    ) + ((l2 >> 4) + (l2 & 15) + ao[2])
                    mask1[y, z] = (
                        (np.uint64(v_id) << 41)
                        | (np.uint64(l0) << 33)
                        | (np.uint64(l1) << 25)
                        | (np.uint64(l2) << 17)
                        | (np.uint64(l3) << 9)
                        | (np.uint64(ao[0]) << 7)
                        | (np.uint64(ao[1]) << 5)
                        | (np.uint64(ao[2]) << 3)
                        | (np.uint64(ao[3]) << 1)
                        | np.uint64(flip_id)
                    )

        for y in range(CHUNK_SIZE):
            for z in range(CHUNK_SIZE):
                val = mask0[y, z]

                if val:
                    w, h = 1, 1

                    while y + w < CHUNK_SIZE and mask0[y + w, z] == val:
                        w += 1

                    done = False

                    while z + h < CHUNK_SIZE:
                        for iy in range(w):
                            if mask0[y + iy, z + h] != val:
                                done = True
                                break

                        if done:
                            break

                        h += 1

                    v_id = int((val >> 41) & 0xFF)
                    l0 = int((val >> 33) & 0xFF)
                    l1 = int((val >> 25) & 0xFF)
                    l2 = int((val >> 17) & 0xFF)
                    l3 = int((val >> 9) & 0xFF)

                    ao0 = int((val >> 7) & 3)
                    ao1 = int((val >> 5) & 3)
                    ao2 = int((val >> 3) & 3)
                    ao3 = int((val >> 1) & 3)
                    flip_id = int(val & 1)

                    v0 = pack_data(x + 1, y, z, v_id, 2, ao0, flip_id, l0)
                    v1 = pack_data(x + 1, y + w, z, v_id, 2, ao1, flip_id, l1)
                    v2 = pack_data(x + 1, y + w, z + h, v_id, 2, ao2, flip_id, l2)
                    v3 = pack_data(x + 1, y, z + h, v_id, 2, ao3, flip_id, l3)

                    if v_id == WATER:
                        if flip_id:
                            water_index = add_data(water_data, water_index, v3, v0, v1, v3, v1, v2)
                        else:
                            water_index = add_data(water_data, water_index, v0, v1, v2, v0, v2, v3)

                    else:
                        if flip_id:
                            index = add_data(vertex_data, index, v3, v0, v1, v3, v1, v2)
                        else:
                            index = add_data(vertex_data, index, v0, v1, v2, v0, v2, v3)

                    for iy in range(w):
                        for iz in range(h):
                            mask0[y + iy, z + iz] = 0

        for y in range(CHUNK_SIZE):
            for z in range(CHUNK_SIZE):
                val = mask1[y, z]

                if val:
                    w, h = 1, 1

                    while y + w < CHUNK_SIZE and mask1[y + w, z] == val:
                        w += 1

                    done = False

                    while z + h < CHUNK_SIZE:
                        for iy in range(w):
                            if mask1[y + iy, z + h] != val:
                                done = True
                                break

                        if done:
                            break

                        h += 1

                    v_id = int((val >> 41) & 0xFF)
                    l0 = int((val >> 33) & 0xFF)
                    l1 = int((val >> 25) & 0xFF)
                    l2 = int((val >> 17) & 0xFF)
                    l3 = int((val >> 9) & 0xFF)

                    ao0 = int((val >> 7) & 3)
                    ao1 = int((val >> 5) & 3)
                    ao2 = int((val >> 3) & 3)
                    ao3 = int((val >> 1) & 3)
                    flip_id = int(val & 1)

                    v0 = pack_data(x, y, z, v_id, 3, ao0, flip_id, l0)
                    v1 = pack_data(x, y + w, z, v_id, 3, ao1, flip_id, l1)
                    v2 = pack_data(x, y + w, z + h, v_id, 3, ao2, flip_id, l2)
                    v3 = pack_data(x, y, z + h, v_id, 3, ao3, flip_id, l3)

                    if v_id == WATER:
                        if flip_id:
                            water_index = add_data(water_data, water_index, v3, v1, v0, v3, v2, v1)
                        else:
                            water_index = add_data(water_data, water_index, v0, v2, v1, v0, v3, v2)

                    else:
                        if flip_id:
                            index = add_data(vertex_data, index, v3, v1, v0, v3, v2, v1)
                        else:
                            index = add_data(vertex_data, index, v0, v2, v1, v0, v3, v2)

                    for iy in range(w):
                        for iz in range(h):
                            mask1[y + iy, z + iz] = 0

    # ================== Z PLANES (Back/Front) ==================
    for z in range(CHUNK_SIZE):
        wz = z + cz * CHUNK_SIZE

        for x in range(CHUNK_SIZE):
            wx = x + cx * CHUNK_SIZE

            for y in range(CHUNK_SIZE):
                wy = y + cy * CHUNK_SIZE

                voxel_id = chunk_voxels[x + CHUNK_SIZE * z + CHUNK_AREA * y]

                if not voxel_id:
                    continue

                neighbor_id = get_neighbor_voxel_id(
                    (x, y, z - 1), (wx, wy, wz - 1), chunk_voxels, world_voxels, chunk_positions
                )

                if is_transparent(neighbor_id) and voxel_id != neighbor_id:
                    ao = get_ao((x, y, z - 1), (wx, wy, wz - 1), chunk_voxels, world_voxels, chunk_positions, plane='Z')

                    # flip_id = ao[1] + ao[3] > ao[0] + ao[2]
                    v_id = (voxel_id | 128) if neighbor_id == WATER else voxel_id

                    face_light = get_neighbor_light(
                        (x, y, z - 1), (wx, wy, wz - 1), chunk_lightmap, world_lightmaps, chunk_positions
                    )
                    l0 = get_vertex_light(
                        (x, y, z),
                        (wx, wy, wz),
                        'Z',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    l1 = get_vertex_light(
                        (x, y + 1, z),
                        (wx, wy + 1, wz),
                        'Z',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    l2 = get_vertex_light(
                        (x + 1, y + 1, z),
                        (wx + 1, wy + 1, wz),
                        'Z',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    l3 = get_vertex_light(
                        (x + 1, y, z),
                        (wx + 1, wy, wz),
                        'Z',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )

                    flip_id = ((l1 >> 4) + (l1 & 15) + ao[1]) + ((l3 >> 4) + (l3 & 15) + ao[3]) > (
                        (l0 >> 4) + (l0 & 15) + ao[0]
                    ) + ((l2 >> 4) + (l2 & 15) + ao[2])
                    mask0[x, y] = (
                        (np.uint64(v_id) << 41)
                        | (np.uint64(l0) << 33)
                        | (np.uint64(l1) << 25)
                        | (np.uint64(l2) << 17)
                        | (np.uint64(l3) << 9)
                        | (np.uint64(ao[0]) << 7)
                        | (np.uint64(ao[1]) << 5)
                        | (np.uint64(ao[2]) << 3)
                        | (np.uint64(ao[3]) << 1)
                        | np.uint64(flip_id)
                    )

                neighbor_id = get_neighbor_voxel_id(
                    (x, y, z + 1), (wx, wy, wz + 1), chunk_voxels, world_voxels, chunk_positions
                )

                if is_transparent(neighbor_id) and voxel_id != neighbor_id:
                    ao = get_ao((x, y, z + 1), (wx, wy, wz + 1), chunk_voxels, world_voxels, chunk_positions, plane='Z')

                    # flip_id = ao[1] + ao[3] > ao[0] + ao[2]
                    v_id = (voxel_id | 128) if neighbor_id == WATER else voxel_id

                    face_light = get_neighbor_light(
                        (x, y, z + 1), (wx, wy, wz + 1), chunk_lightmap, world_lightmaps, chunk_positions
                    )
                    l0 = get_vertex_light(
                        (x, y, z + 1),
                        (wx, wy, wz + 1),
                        'Z',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    l1 = get_vertex_light(
                        (x, y + 1, z + 1),
                        (wx, wy + 1, wz + 1),
                        'Z',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    l2 = get_vertex_light(
                        (x + 1, y + 1, z + 1),
                        (wx + 1, wy + 1, wz + 1),
                        'Z',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    l3 = get_vertex_light(
                        (x + 1, y, z + 1),
                        (wx + 1, wy, wz + 1),
                        'Z',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )

                    flip_id = ((l1 >> 4) + (l1 & 15) + ao[1]) + ((l3 >> 4) + (l3 & 15) + ao[3]) > (
                        (l0 >> 4) + (l0 & 15) + ao[0]
                    ) + ((l2 >> 4) + (l2 & 15) + ao[2])
                    mask1[x, y] = (
                        (np.uint64(v_id) << 41)
                        | (np.uint64(l0) << 33)
                        | (np.uint64(l1) << 25)
                        | (np.uint64(l2) << 17)
                        | (np.uint64(l3) << 9)
                        | (np.uint64(ao[0]) << 7)
                        | (np.uint64(ao[1]) << 5)
                        | (np.uint64(ao[2]) << 3)
                        | (np.uint64(ao[3]) << 1)
                        | np.uint64(flip_id)
                    )

        for x in range(CHUNK_SIZE):
            for y in range(CHUNK_SIZE):
                val = mask0[x, y]

                if val:
                    w, h = 1, 1

                    while x + w < CHUNK_SIZE and mask0[x + w, y] == val:
                        w += 1

                    done = False

                    while y + h < CHUNK_SIZE:
                        for ix in range(w):
                            if mask0[x + ix, y + h] != val:
                                done = True
                                break

                        if done:
                            break

                        h += 1

                    v_id = int((val >> 41) & 0xFF)
                    l0 = int((val >> 33) & 0xFF)
                    l1 = int((val >> 25) & 0xFF)
                    l2 = int((val >> 17) & 0xFF)
                    l3 = int((val >> 9) & 0xFF)

                    ao0 = int((val >> 7) & 3)
                    ao1 = int((val >> 5) & 3)
                    ao2 = int((val >> 3) & 3)
                    ao3 = int((val >> 1) & 3)
                    flip_id = int(val & 1)

                    v0 = pack_data(x, y, z, v_id, 4, ao0, flip_id, l0)
                    v1 = pack_data(x, y + h, z, v_id, 4, ao1, flip_id, l1)
                    v2 = pack_data(x + w, y + h, z, v_id, 4, ao2, flip_id, l2)
                    v3 = pack_data(x + w, y, z, v_id, 4, ao3, flip_id, l3)

                    if v_id == WATER:
                        if flip_id:
                            water_index = add_data(water_data, water_index, v3, v0, v1, v3, v1, v2)
                        else:
                            water_index = add_data(water_data, water_index, v0, v1, v2, v0, v2, v3)

                    else:
                        if flip_id:
                            index = add_data(vertex_data, index, v3, v0, v1, v3, v1, v2)
                        else:
                            index = add_data(vertex_data, index, v0, v1, v2, v0, v2, v3)

                    for ix in range(w):
                        for iy in range(h):
                            mask0[x + ix, y + iy] = 0

        for x in range(CHUNK_SIZE):
            for y in range(CHUNK_SIZE):
                val = mask1[x, y]

                if val:
                    w, h = 1, 1

                    while x + w < CHUNK_SIZE and mask1[x + w, y] == val:
                        w += 1

                    done = False

                    while y + h < CHUNK_SIZE:
                        for ix in range(w):
                            if mask1[x + ix, y + h] != val:
                                done = True
                                break

                        if done:
                            break

                        h += 1

                    v_id = int((val >> 41) & 0xFF)
                    l0 = int((val >> 33) & 0xFF)
                    l1 = int((val >> 25) & 0xFF)
                    l2 = int((val >> 17) & 0xFF)
                    l3 = int((val >> 9) & 0xFF)

                    ao0 = int((val >> 7) & 3)
                    ao1 = int((val >> 5) & 3)
                    ao2 = int((val >> 3) & 3)
                    ao3 = int((val >> 1) & 3)
                    flip_id = int(val & 1)

                    v0 = pack_data(x, y, z + 1, v_id, 5, ao0, flip_id, l0)
                    v1 = pack_data(x, y + h, z + 1, v_id, 5, ao1, flip_id, l1)
                    v2 = pack_data(x + w, y + h, z + 1, v_id, 5, ao2, flip_id, l2)
                    v3 = pack_data(x + w, y, z + 1, v_id, 5, ao3, flip_id, l3)

                    if v_id == WATER:
                        if flip_id:
                            water_index = add_data(water_data, water_index, v3, v1, v0, v3, v2, v1)
                        else:
                            water_index = add_data(water_data, water_index, v0, v2, v1, v0, v3, v2)

                    else:
                        if flip_id:
                            index = add_data(vertex_data, index, v3, v1, v0, v3, v2, v1)
                        else:
                            index = add_data(vertex_data, index, v0, v2, v1, v0, v3, v2)

                    for ix in range(w):
                        for iy in range(h):
                            mask1[x + ix, y + iy] = 0

    opaque_mesh = vertex_data[:index]
    water_mesh = water_data[:water_index]
    combined_mesh = np.hstack((opaque_mesh, water_mesh))

    return combined_mesh, index // format_size, water_index // format_size

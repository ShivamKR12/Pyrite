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

# ============================================================================
# REAL-WORLD CONTEXT: Voxel Ambient Occlusion (AO)
# ============================================================================
# This function calculates "Ambient Occlusion" for a specific face of a voxel.
# AO is a shading technique used to simulate how light gets trapped in corners
# and crevices, giving depth to the geometry.
#
# How it works in a Voxel Engine:
# Since Voxels are on a strict grid, we don't need expensive ray-tracing or SSAO.
# Instead, we do "Per-Vertex AO". For a given block face (e.g., the Top face 'Y'),
# we check the 8 neighboring blocks surrounding that face. If a neighbor is solid,
# it casts a small "shadow" on the corresponding corner/vertex.
#
# The result is passed to the chunk shader, which darkens the corners of blocks
# that are touching other blocks, creating the iconic "soft shadows" seen in
# Minecraft-like games.
#
# References:
# - Ambient Occlusion: https://en.wikipedia.org/wiki/Ambient_occlusion
# - Voxel Meshing & Shading concepts: https://www.reddit.com/r/VoxelGameDev/
# ============================================================================


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
    world_x, world_y, world_z = world_pos

    if plane == 'Y':
        a = is_void((x, y, z - 1), (world_x, world_y, world_z - 1), chunk_voxels, world_voxels, chunk_positions)
        b = is_void((x - 1, y, z - 1), (world_x - 1, world_y, world_z - 1), chunk_voxels, world_voxels, chunk_positions)
        c = is_void((x - 1, y, z), (world_x - 1, world_y, world_z), chunk_voxels, world_voxels, chunk_positions)
        d = is_void((x - 1, y, z + 1), (world_x - 1, world_y, world_z + 1), chunk_voxels, world_voxels, chunk_positions)
        e = is_void((x, y, z + 1), (world_x, world_y, world_z + 1), chunk_voxels, world_voxels, chunk_positions)
        f = is_void((x + 1, y, z + 1), (world_x + 1, world_y, world_z + 1), chunk_voxels, world_voxels, chunk_positions)
        g = is_void((x + 1, y, z), (world_x + 1, world_y, world_z), chunk_voxels, world_voxels, chunk_positions)
        h = is_void((x + 1, y, z - 1), (world_x + 1, world_y, world_z - 1), chunk_voxels, world_voxels, chunk_positions)

    elif plane == 'X':
        a = is_void((x, y, z - 1), (world_x, world_y, world_z - 1), chunk_voxels, world_voxels, chunk_positions)
        b = is_void((x, y - 1, z - 1), (world_x, world_y - 1, world_z - 1), chunk_voxels, world_voxels, chunk_positions)
        c = is_void((x, y - 1, z), (world_x, world_y - 1, world_z), chunk_voxels, world_voxels, chunk_positions)
        d = is_void((x, y - 1, z + 1), (world_x, world_y - 1, world_z + 1), chunk_voxels, world_voxels, chunk_positions)
        e = is_void((x, y, z + 1), (world_x, world_y, world_z + 1), chunk_voxels, world_voxels, chunk_positions)
        f = is_void((x, y + 1, z + 1), (world_x, world_y + 1, world_z + 1), chunk_voxels, world_voxels, chunk_positions)
        g = is_void((x, y + 1, z), (world_x, world_y + 1, world_z), chunk_voxels, world_voxels, chunk_positions)
        h = is_void((x, y + 1, z - 1), (world_x, world_y + 1, world_z - 1), chunk_voxels, world_voxels, chunk_positions)

    else:  # Z plane
        a = is_void((x - 1, y, z), (world_x - 1, world_y, world_z), chunk_voxels, world_voxels, chunk_positions)
        b = is_void((x - 1, y - 1, z), (world_x - 1, world_y - 1, world_z), chunk_voxels, world_voxels, chunk_positions)
        c = is_void((x, y - 1, z), (world_x, world_y - 1, world_z), chunk_voxels, world_voxels, chunk_positions)
        d = is_void((x + 1, y - 1, z), (world_x + 1, world_y - 1, world_z), chunk_voxels, world_voxels, chunk_positions)
        e = is_void((x + 1, y, z), (world_x + 1, world_y, world_z), chunk_voxels, world_voxels, chunk_positions)
        f = is_void((x + 1, y + 1, z), (world_x + 1, world_y + 1, world_z), chunk_voxels, world_voxels, chunk_positions)
        g = is_void((x, y + 1, z), (world_x, world_y + 1, world_z), chunk_voxels, world_voxels, chunk_positions)
        h = is_void((x - 1, y + 1, z), (world_x - 1, world_y + 1, world_z), chunk_voxels, world_voxels, chunk_positions)

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
    local_x, local_y, local_z = local_vertex_pos
    velocity_x, velocity_y, velocity_z = world_vertex_pos

    if plane == 'Y':
        # Vertex is on an XZ plane, so we sample the 4 adjacent blocks in that plane.
        block_0 = get_neighbor_voxel_id(
            (local_x, local_y, local_z),
            (velocity_x, velocity_y, velocity_z),
            chunk_voxels,
            world_voxels,
            chunk_positions,
        )
        block_1 = get_neighbor_voxel_id(
            (local_x - 1, local_y, local_z),
            (velocity_x - 1, velocity_y, velocity_z),
            chunk_voxels,
            world_voxels,
            chunk_positions,
        )
        block_2 = get_neighbor_voxel_id(
            (local_x, local_y, local_z - 1),
            (velocity_x, velocity_y, velocity_z - 1),
            chunk_voxels,
            world_voxels,
            chunk_positions,
        )
        block_3 = get_neighbor_voxel_id(
            (local_x - 1, local_y, local_z - 1),
            (velocity_x - 1, velocity_y, velocity_z - 1),
            chunk_voxels,
            world_voxels,
            chunk_positions,
        )

        light_0 = (
            face_light
            if not is_transparent(block_0)
            else get_neighbor_light(
                (local_x, local_y, local_z),
                (velocity_x, velocity_y, velocity_z),
                chunk_lightmap,
                world_lightmaps,
                chunk_positions,
            )
        )
        light_1 = (
            face_light
            if not is_transparent(block_1)
            else get_neighbor_light(
                (local_x - 1, local_y, local_z),
                (velocity_x - 1, velocity_y, velocity_z),
                chunk_lightmap,
                world_lightmaps,
                chunk_positions,
            )
        )
        light_2 = (
            face_light
            if not is_transparent(block_2)
            else get_neighbor_light(
                (local_x, local_y, local_z - 1),
                (velocity_x, velocity_y, velocity_z - 1),
                chunk_lightmap,
                world_lightmaps,
                chunk_positions,
            )
        )
        light_3 = (
            face_light
            if not is_transparent(block_3)
            else get_neighbor_light(
                (local_x - 1, local_y, local_z - 1),
                (velocity_x - 1, velocity_y, velocity_z - 1),
                chunk_lightmap,
                world_lightmaps,
                chunk_positions,
            )
        )

    elif plane == 'X':
        # Vertex is on a YZ plane
        block_0 = get_neighbor_voxel_id(
            (local_x, local_y, local_z),
            (velocity_x, velocity_y, velocity_z),
            chunk_voxels,
            world_voxels,
            chunk_positions,
        )
        block_1 = get_neighbor_voxel_id(
            (local_x, local_y - 1, local_z),
            (velocity_x, velocity_y - 1, velocity_z),
            chunk_voxels,
            world_voxels,
            chunk_positions,
        )
        block_2 = get_neighbor_voxel_id(
            (local_x, local_y, local_z - 1),
            (velocity_x, velocity_y, velocity_z - 1),
            chunk_voxels,
            world_voxels,
            chunk_positions,
        )
        block_3 = get_neighbor_voxel_id(
            (local_x, local_y - 1, local_z - 1),
            (velocity_x, velocity_y - 1, velocity_z - 1),
            chunk_voxels,
            world_voxels,
            chunk_positions,
        )

        light_0 = (
            face_light
            if not is_transparent(block_0)
            else get_neighbor_light(
                (local_x, local_y, local_z),
                (velocity_x, velocity_y, velocity_z),
                chunk_lightmap,
                world_lightmaps,
                chunk_positions,
            )
        )
        light_1 = (
            face_light
            if not is_transparent(block_1)
            else get_neighbor_light(
                (local_x, local_y - 1, local_z),
                (velocity_x, velocity_y - 1, velocity_z),
                chunk_lightmap,
                world_lightmaps,
                chunk_positions,
            )
        )
        light_2 = (
            face_light
            if not is_transparent(block_2)
            else get_neighbor_light(
                (local_x, local_y, local_z - 1),
                (velocity_x, velocity_y, velocity_z - 1),
                chunk_lightmap,
                world_lightmaps,
                chunk_positions,
            )
        )
        light_3 = (
            face_light
            if not is_transparent(block_3)
            else get_neighbor_light(
                (local_x, local_y - 1, local_z - 1),
                (velocity_x, velocity_y - 1, velocity_z - 1),
                chunk_lightmap,
                world_lightmaps,
                chunk_positions,
            )
        )

    else:  # Z plane
        # Vertex is on an XY plane
        block_0 = get_neighbor_voxel_id(
            (local_x, local_y, local_z),
            (velocity_x, velocity_y, velocity_z),
            chunk_voxels,
            world_voxels,
            chunk_positions,
        )
        block_1 = get_neighbor_voxel_id(
            (local_x - 1, local_y, local_z),
            (velocity_x - 1, velocity_y, velocity_z),
            chunk_voxels,
            world_voxels,
            chunk_positions,
        )
        block_2 = get_neighbor_voxel_id(
            (local_x, local_y - 1, local_z),
            (velocity_x, velocity_y - 1, velocity_z),
            chunk_voxels,
            world_voxels,
            chunk_positions,
        )
        block_3 = get_neighbor_voxel_id(
            (local_x - 1, local_y - 1, local_z),
            (velocity_x - 1, velocity_y - 1, velocity_z),
            chunk_voxels,
            world_voxels,
            chunk_positions,
        )

        light_0 = (
            face_light
            if not is_transparent(block_0)
            else get_neighbor_light(
                (local_x, local_y, local_z),
                (velocity_x, velocity_y, velocity_z),
                chunk_lightmap,
                world_lightmaps,
                chunk_positions,
            )
        )
        light_1 = (
            face_light
            if not is_transparent(block_1)
            else get_neighbor_light(
                (local_x - 1, local_y, local_z),
                (velocity_x - 1, velocity_y, velocity_z),
                chunk_lightmap,
                world_lightmaps,
                chunk_positions,
            )
        )
        light_2 = (
            face_light
            if not is_transparent(block_2)
            else get_neighbor_light(
                (local_x, local_y - 1, local_z),
                (velocity_x, velocity_y - 1, velocity_z),
                chunk_lightmap,
                world_lightmaps,
                chunk_positions,
            )
        )
        light_3 = (
            face_light
            if not is_transparent(block_3)
            else get_neighbor_light(
                (local_x - 1, local_y - 1, local_z),
                (velocity_x - 1, velocity_y - 1, velocity_z),
                chunk_lightmap,
                world_lightmaps,
                chunk_positions,
            )
        )

    # Average the Sun and Block light separately to prevent overflow and incorrect mixing.
    sun = ((light_0 >> 4) + (light_1 >> 4) + (light_2 >> 4) + (light_3 >> 4)) >> 2
    block = ((light_0 & 15) + (light_1 & 15) + (light_2 & 15) + (light_3 & 15)) >> 2

    return int((sun << 4) | block)


@njit(cache=True, nogil=True)
def pack_data(
    x: int, y: int, z: int, voxel_id: int, face_id: int, ao_id: int, flip_id: int, light_val: int
) -> Tuple[int, int]:
    """
    Packs multiple pieces of vertex data (coordinates, voxel ID, face ID, AO ID, flip ID)
    into a single 32-bit unsigned integer to minimize memory usage and GPU bandwidth.
    """
    # Map input attributes to variables
    # x: 6bit  y: 6bit  z: 6bit  voxel_id: 8bit  face_id: 3bit  ao_id: 2bit  flip_id: 1bit
    a, b, c, d, e, f, g = x, y, z, voxel_id, face_id, ao_id, flip_id

    # Compute bit offsets for packing
    b_bit, c_bit, d_bit, e_bit, f_bit, g_bit = 6, 6, 8, 3, 2, 1
    fg_bit = f_bit + g_bit
    efg_bit = e_bit + fg_bit
    defg_bit = d_bit + efg_bit
    cdefg_bit = c_bit + defg_bit
    bcdefg_bit = b_bit + cdefg_bit

    # Pack attributes into a single integer
    packed_data = a << bcdefg_bit | b << cdefg_bit | c << defg_bit | d << efg_bit | e << fg_bit | f << g_bit | g

    return packed_data, light_val


@njit(cache=True, nogil=True)
def get_chunk_index(world_voxel_pos: Tuple[int, int, int], chunk_positions: Any) -> int:
    """
    Calculates the 1D index of a chunk in the global world arrays based on an absolute
    world voxel coordinate. Returns -1 if the chunk is not currently loaded or out of bounds.
    """
    # Calculate chunk coordinates from global voxel position
    world_x, world_y, world_z = world_voxel_pos
    chunk_x = world_x // CHUNK_SIZE
    chunk_y = world_y // CHUNK_SIZE
    chunk_z = world_z // CHUNK_SIZE

    # Validate Y axis bounds
    if not (0 <= chunk_y < WORLD_HEIGHT):
        return -1

    # Calculate 1D chunk index and verify chunk existence
    index = (chunk_x % WORLD_WIDTH) + WORLD_WIDTH * (chunk_z % WORLD_DEPTH) + WORLD_AREA * (chunk_y % WORLD_HEIGHT)

    if (
        chunk_positions[index][0] == chunk_x
        and chunk_positions[index][1] == chunk_y
        and chunk_positions[index][2] == chunk_z
    ):
        return index

    # Return -1 if chunk is out of bounds or unloaded
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
    # Check if voxel is within the current chunk boundaries
    x, y, z = local_voxel_pos
    if 0 <= x < CHUNK_SIZE and 0 <= y < CHUNK_SIZE and 0 <= z < CHUNK_SIZE:
        return int(chunk_voxels[x + z * CHUNK_SIZE + y * CHUNK_AREA])

    # Attempt to retrieve voxel from neighboring chunk
    chunk_index = get_chunk_index(world_voxel_pos, chunk_positions)

    if chunk_index == -1:
        return 0

    chunk_voxels_global = world_voxels[chunk_index]

    local_x = world_voxel_pos[0] % CHUNK_SIZE
    local_y = world_voxel_pos[1] % CHUNK_SIZE
    local_z = world_voxel_pos[2] % CHUNK_SIZE
    voxel_index = local_x + local_z * CHUNK_SIZE + local_y * CHUNK_AREA

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
    # Check if voxel is within the current chunk boundaries
    x, y, z = local_voxel_pos
    if 0 <= x < CHUNK_SIZE and 0 <= y < CHUNK_SIZE and 0 <= z < CHUNK_SIZE:
        return int(chunk_lightmap[x + z * CHUNK_SIZE + y * CHUNK_AREA])

    # Attempt to retrieve light value from neighboring chunk
    chunk_index = get_chunk_index(world_voxel_pos, chunk_positions)

    if chunk_index == -1:
        return 255

    chunk_lights_global = world_lightmaps[chunk_index]

    local_x = world_voxel_pos[0] % CHUNK_SIZE
    local_y = world_voxel_pos[1] % CHUNK_SIZE
    local_z = world_voxel_pos[2] % CHUNK_SIZE
    voxel_index = local_x + local_z * CHUNK_SIZE + local_y * CHUNK_AREA

    return int(chunk_lights_global[voxel_index])


@njit(cache=True, nogil=True)
def is_transparent(voxel_id: int) -> bool:
    """
    Checks if a given voxel ID corresponds to a transparent block (like air, water, glass, or leaves).
    Transparent blocks do not cull adjacent faces and do not cast hard ambient occlusion shadows.
    """
    # Check if voxel ID is a transparent block
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
    # Get neighbor voxel ID
    value = get_neighbor_voxel_id(local_voxel_pos, world_voxel_pos, chunk_voxels, world_voxels, chunk_positions)

    # Transparent blocks do not cast AO shadows!
    return bool(is_transparent(value))


@njit(cache=True, nogil=True)
def add_data(vertex_data: Any, index: int, *vertices: Tuple[int, int]) -> int:
    """
    Appends newly packed vertex data and its associated lighting value into the main
    mesh arrays, advancing the current index counter.
    """
    # Append newly packed vertex data to mesh array
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
    # Initialize vertex buffers and indices
    vertex_data = np.empty(CHUNK_VOLUME * 18 * format_size, dtype='uint32')
    water_data = np.empty(CHUNK_VOLUME * 18 * format_size, dtype='uint32')
    index = 0
    water_index = 0

    # Extract chunk coordinates and initialize face masks
    chunk_x, chunk_y, chunk_z = chunk_pos
    mask0 = np.zeros((CHUNK_SIZE, CHUNK_SIZE), dtype=np.uint64)
    mask1 = np.zeros((CHUNK_SIZE, CHUNK_SIZE), dtype=np.uint64)

    # Y PLANES (Top/Bottom)
    for y in range(CHUNK_SIZE):
        world_y = y + chunk_y * CHUNK_SIZE

        for x in range(CHUNK_SIZE):
            world_x = x + chunk_x * CHUNK_SIZE

            for z in range(CHUNK_SIZE):
                world_z = z + chunk_z * CHUNK_SIZE

                voxel_id = chunk_voxels[x + CHUNK_SIZE * z + CHUNK_AREA * y]

                if not voxel_id:
                    continue

                # top face
                neighbor_id = get_neighbor_voxel_id(
                    (x, y + 1, z), (world_x, world_y + 1, world_z), chunk_voxels, world_voxels, chunk_positions
                )

                if is_transparent(neighbor_id) and voxel_id != neighbor_id:
                    ao = get_ao(
                        (x, y + 1, z),
                        (world_x, world_y + 1, world_z),
                        chunk_voxels,
                        world_voxels,
                        chunk_positions,
                        plane='Y',
                    )

                    # flip_id = ao[1] + ao[3] > ao[0] + ao[2]
                    voxel_id = (voxel_id | 128) if neighbor_id == WATER else voxel_id

                    face_light = get_neighbor_light(
                        (x, y + 1, z), (world_x, world_y + 1, world_z), chunk_lightmap, world_lightmaps, chunk_positions
                    )
                    light_0 = get_vertex_light(
                        (x, y + 1, z),
                        (world_x, world_y + 1, world_z),
                        'Y',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    light_1 = get_vertex_light(
                        (x + 1, y + 1, z),
                        (world_x + 1, world_y + 1, world_z),
                        'Y',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    light_2 = get_vertex_light(
                        (x + 1, y + 1, z + 1),
                        (world_x + 1, world_y + 1, world_z + 1),
                        'Y',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    light_3 = get_vertex_light(
                        (x, y + 1, z + 1),
                        (world_x, world_y + 1, world_z + 1),
                        'Y',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )

                    # Determine if the quad should be flipped to prevent anisotropic lighting artifacts.
                    # We compare the total lighting (sun + block + ao) of the two diagonals.
                    # The diagonal with the higher total light is split to create smoother gradients.
                    flip_id = ((light_1 >> 4) + (light_1 & 15) + ao[1]) + ((light_3 >> 4) + (light_3 & 15) + ao[3]) > (
                        (light_0 >> 4) + (light_0 & 15) + ao[0]
                    ) + ((light_2 >> 4) + (light_2 & 15) + ao[2])
                    # Pack all vertex attributes (voxel ID, 4 light values, 4 AO values, and flip ID)
                    # into a single 64-bit integer mask for efficient greedy meshing later.
                    # 41: voxel_id, 33: light_0, 25: light_1, 17: light_2, 9: light_3, 7: ambient_occlusion_0, 5: ambient_occlusion_1, 3: ambient_occlusion_2, 1: ambient_occlusion_3, 0: flip_id
                    mask0[x, z] = (
                        (np.uint64(voxel_id) << 41)
                        | (np.uint64(light_0) << 33)
                        | (np.uint64(light_1) << 25)
                        | (np.uint64(light_2) << 17)
                        | (np.uint64(light_3) << 9)
                        | (np.uint64(ao[0]) << 7)
                        | (np.uint64(ao[1]) << 5)
                        | (np.uint64(ao[2]) << 3)
                        | (np.uint64(ao[3]) << 1)
                        | np.uint64(flip_id)
                    )

                # bottom face
                neighbor_id = get_neighbor_voxel_id(
                    (x, y - 1, z), (world_x, world_y - 1, world_z), chunk_voxels, world_voxels, chunk_positions
                )

                if is_transparent(neighbor_id) and voxel_id != neighbor_id:
                    ao = get_ao(
                        (x, y - 1, z),
                        (world_x, world_y - 1, world_z),
                        chunk_voxels,
                        world_voxels,
                        chunk_positions,
                        plane='Y',
                    )

                    # flip_id = ao[1] + ao[3] > ao[0] + ao[2]
                    voxel_id = (voxel_id | 128) if neighbor_id == WATER else voxel_id

                    face_light = get_neighbor_light(
                        (x, y - 1, z), (world_x, world_y - 1, world_z), chunk_lightmap, world_lightmaps, chunk_positions
                    )
                    light_0 = get_vertex_light(
                        (x, y, z),
                        (world_x, world_y, world_z),
                        'Y',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    light_1 = get_vertex_light(
                        (x + 1, y, z),
                        (world_x + 1, world_y, world_z),
                        'Y',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    light_2 = get_vertex_light(
                        (x + 1, y, z + 1),
                        (world_x + 1, world_y, world_z + 1),
                        'Y',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    light_3 = get_vertex_light(
                        (x, y, z + 1),
                        (world_x, world_y, world_z + 1),
                        'Y',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )

                    # Determine if the quad should be flipped to prevent anisotropic lighting artifacts.
                    # We compare the total lighting (sun + block + ao) of the two diagonals.
                    # The diagonal with the higher total light is split to create smoother gradients.
                    flip_id = ((light_1 >> 4) + (light_1 & 15) + ao[1]) + ((light_3 >> 4) + (light_3 & 15) + ao[3]) > (
                        (light_0 >> 4) + (light_0 & 15) + ao[0]
                    ) + ((light_2 >> 4) + (light_2 & 15) + ao[2])
                    # Pack all vertex attributes (voxel ID, 4 light values, 4 AO values, and flip ID)
                    # into a single 64-bit integer mask for efficient greedy meshing later.
                    # 41: voxel_id, 33: light_0, 25: light_1, 17: light_2, 9: light_3, 7: ambient_occlusion_0, 5: ambient_occlusion_1, 3: ambient_occlusion_2, 1: ambient_occlusion_3, 0: flip_id
                    mask1[x, z] = (
                        (np.uint64(voxel_id) << 41)
                        | (np.uint64(light_0) << 33)
                        | (np.uint64(light_1) << 25)
                        | (np.uint64(light_2) << 17)
                        | (np.uint64(light_3) << 9)
                        | (np.uint64(ao[0]) << 7)
                        | (np.uint64(ao[1]) << 5)
                        | (np.uint64(ao[2]) << 3)
                        | (np.uint64(ao[3]) << 1)
                        | np.uint64(flip_id)
                    )

        for x in range(CHUNK_SIZE):
            for z in range(CHUNK_SIZE):
                value = mask0[x, z]

                if value:
                    w, h = 1, 1

                    # Greedy meshing: Find the maximum width (w) this face can extend along the first axis
                    # where all faces share the exact same attributes (voxel ID, lighting, AO, etc).
                    while x + w < CHUNK_SIZE and mask0[x + w, z] == value:
                        w += 1

                    done = False

                    while z + h < CHUNK_SIZE:
                        for index_x in range(w):
                            if mask0[x + index_x, z + h] != value:
                                done = True
                                break

                        if done:
                            break
                        h += 1

                    # Unpack the chunked face attributes from the 64-bit mask value
                    voxel_id = int((value >> 41) & 0xFF)
                    light_0 = int((value >> 33) & 0xFF)
                    light_1 = int((value >> 25) & 0xFF)
                    light_2 = int((value >> 17) & 0xFF)
                    light_3 = int((value >> 9) & 0xFF)

                    ambient_occlusion_0 = int((value >> 7) & 3)
                    ambient_occlusion_1 = int((value >> 5) & 3)
                    ambient_occlusion_2 = int((value >> 3) & 3)
                    ambient_occlusion_3 = int((value >> 1) & 3)
                    flip_id = int(value & 1)

                    # Pack the final geometric vertex data (position, voxel_id, face_id, etc) into a 32-bit int.
                    v0 = pack_data(x, y + 1, z, voxel_id, 0, ambient_occlusion_0, flip_id, light_0)
                    v1 = pack_data(x + w, y + 1, z, voxel_id, 0, ambient_occlusion_1, flip_id, light_1)
                    v2 = pack_data(x + w, y + 1, z + h, voxel_id, 0, ambient_occlusion_2, flip_id, light_2)
                    v3 = pack_data(x, y + 1, z + h, voxel_id, 0, ambient_occlusion_3, flip_id, light_3)

                    if voxel_id == WATER:
                        if flip_id:
                            water_index = add_data(water_data, water_index, v1, v0, v3, v1, v3, v2)
                        else:
                            water_index = add_data(water_data, water_index, v0, v3, v2, v0, v2, v1)

                    else:
                        if flip_id:
                            index = add_data(vertex_data, index, v1, v0, v3, v1, v3, v2)
                        else:
                            index = add_data(vertex_data, index, v0, v3, v2, v0, v2, v1)

                    for index_x in range(w):
                        for index_z in range(h):
                            mask0[x + index_x, z + index_z] = 0

        for x in range(CHUNK_SIZE):
            for z in range(CHUNK_SIZE):
                value = mask1[x, z]

                if value:
                    w, h = 1, 1

                    while x + w < CHUNK_SIZE and mask1[x + w, z] == value:
                        w += 1

                    done = False

                    while z + h < CHUNK_SIZE:
                        for index_x in range(w):
                            if mask1[x + index_x, z + h] != value:
                                done = True
                                break

                        if done:
                            break

                        h += 1

                    # Unpack the chunked face attributes from the 64-bit mask value
                    voxel_id = int((value >> 41) & 0xFF)
                    light_0 = int((value >> 33) & 0xFF)
                    light_1 = int((value >> 25) & 0xFF)
                    light_2 = int((value >> 17) & 0xFF)
                    light_3 = int((value >> 9) & 0xFF)

                    ambient_occlusion_0 = int((value >> 7) & 3)
                    ambient_occlusion_1 = int((value >> 5) & 3)
                    ambient_occlusion_2 = int((value >> 3) & 3)
                    ambient_occlusion_3 = int((value >> 1) & 3)
                    flip_id = int(value & 1)

                    # Pack the final geometric vertex data (position, voxel_id, face_id, etc) into a 32-bit int.
                    v0 = pack_data(x, y, z, voxel_id, 1, ambient_occlusion_0, flip_id, light_0)
                    v1 = pack_data(x + w, y, z, voxel_id, 1, ambient_occlusion_1, flip_id, light_1)
                    v2 = pack_data(x + w, y, z + h, voxel_id, 1, ambient_occlusion_2, flip_id, light_2)
                    v3 = pack_data(x, y, z + h, voxel_id, 1, ambient_occlusion_3, flip_id, light_3)

                    if voxel_id == WATER:
                        if flip_id:
                            water_index = add_data(water_data, water_index, v1, v3, v0, v1, v2, v3)
                        else:
                            water_index = add_data(water_data, water_index, v0, v2, v3, v0, v1, v2)

                    else:
                        if flip_id:
                            index = add_data(vertex_data, index, v1, v3, v0, v1, v2, v3)
                        else:
                            index = add_data(vertex_data, index, v0, v2, v3, v0, v1, v2)

                    for index_x in range(w):
                        for index_z in range(h):
                            mask1[x + index_x, z + index_z] = 0

    # X PLANES (Right/Left)
    for x in range(CHUNK_SIZE):
        world_x = x + chunk_x * CHUNK_SIZE

        for y in range(CHUNK_SIZE):
            world_y = y + chunk_y * CHUNK_SIZE

            for z in range(CHUNK_SIZE):
                world_z = z + chunk_z * CHUNK_SIZE

                voxel_id = chunk_voxels[x + CHUNK_SIZE * z + CHUNK_AREA * y]

                if not voxel_id:
                    continue

                neighbor_id = get_neighbor_voxel_id(
                    (x + 1, y, z), (world_x + 1, world_y, world_z), chunk_voxels, world_voxels, chunk_positions
                )

                if is_transparent(neighbor_id) and voxel_id != neighbor_id:
                    ao = get_ao(
                        (x + 1, y, z),
                        (world_x + 1, world_y, world_z),
                        chunk_voxels,
                        world_voxels,
                        chunk_positions,
                        plane='X',
                    )

                    # flip_id = ao[1] + ao[3] > ao[0] + ao[2]
                    voxel_id = (voxel_id | 128) if neighbor_id == WATER else voxel_id

                    face_light = get_neighbor_light(
                        (x + 1, y, z), (world_x + 1, world_y, world_z), chunk_lightmap, world_lightmaps, chunk_positions
                    )
                    light_0 = get_vertex_light(
                        (x + 1, y, z),
                        (world_x + 1, world_y, world_z),
                        'X',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    light_1 = get_vertex_light(
                        (x + 1, y + 1, z),
                        (world_x + 1, world_y + 1, world_z),
                        'X',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    light_2 = get_vertex_light(
                        (x + 1, y + 1, z + 1),
                        (world_x + 1, world_y + 1, world_z + 1),
                        'X',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    light_3 = get_vertex_light(
                        (x + 1, y, z + 1),
                        (world_x + 1, world_y, world_z + 1),
                        'X',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )

                    # Determine if the quad should be flipped to prevent anisotropic lighting artifacts.
                    # We compare the total lighting (sun + block + ao) of the two diagonals.
                    # The diagonal with the higher total light is split to create smoother gradients.
                    flip_id = ((light_1 >> 4) + (light_1 & 15) + ao[1]) + ((light_3 >> 4) + (light_3 & 15) + ao[3]) > (
                        (light_0 >> 4) + (light_0 & 15) + ao[0]
                    ) + ((light_2 >> 4) + (light_2 & 15) + ao[2])
                    # Pack all vertex attributes (voxel ID, 4 light values, 4 AO values, and flip ID)
                    # into a single 64-bit integer mask for efficient greedy meshing later.
                    # 41: voxel_id, 33: light_0, 25: light_1, 17: light_2, 9: light_3, 7: ambient_occlusion_0, 5: ambient_occlusion_1, 3: ambient_occlusion_2, 1: ambient_occlusion_3, 0: flip_id
                    mask0[y, z] = (
                        (np.uint64(voxel_id) << 41)
                        | (np.uint64(light_0) << 33)
                        | (np.uint64(light_1) << 25)
                        | (np.uint64(light_2) << 17)
                        | (np.uint64(light_3) << 9)
                        | (np.uint64(ao[0]) << 7)
                        | (np.uint64(ao[1]) << 5)
                        | (np.uint64(ao[2]) << 3)
                        | (np.uint64(ao[3]) << 1)
                        | np.uint64(flip_id)
                    )

                neighbor_id = get_neighbor_voxel_id(
                    (x - 1, y, z), (world_x - 1, world_y, world_z), chunk_voxels, world_voxels, chunk_positions
                )

                if is_transparent(neighbor_id) and voxel_id != neighbor_id:
                    ao = get_ao(
                        (x - 1, y, z),
                        (world_x - 1, world_y, world_z),
                        chunk_voxels,
                        world_voxels,
                        chunk_positions,
                        plane='X',
                    )

                    # flip_id = ao[1] + ao[3] > ao[0] + ao[2]
                    voxel_id = (voxel_id | 128) if neighbor_id == WATER else voxel_id

                    face_light = get_neighbor_light(
                        (x - 1, y, z), (world_x - 1, world_y, world_z), chunk_lightmap, world_lightmaps, chunk_positions
                    )
                    light_0 = get_vertex_light(
                        (x, y, z),
                        (world_x, world_y, world_z),
                        'X',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    light_1 = get_vertex_light(
                        (x, y + 1, z),
                        (world_x, world_y + 1, world_z),
                        'X',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    light_2 = get_vertex_light(
                        (x, y + 1, z + 1),
                        (world_x, world_y + 1, world_z + 1),
                        'X',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    light_3 = get_vertex_light(
                        (x, y, z + 1),
                        (world_x, world_y, world_z + 1),
                        'X',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )

                    # Determine if the quad should be flipped to prevent anisotropic lighting artifacts.
                    # We compare the total lighting (sun + block + ao) of the two diagonals.
                    # The diagonal with the higher total light is split to create smoother gradients.
                    flip_id = ((light_1 >> 4) + (light_1 & 15) + ao[1]) + ((light_3 >> 4) + (light_3 & 15) + ao[3]) > (
                        (light_0 >> 4) + (light_0 & 15) + ao[0]
                    ) + ((light_2 >> 4) + (light_2 & 15) + ao[2])
                    # Pack all vertex attributes (voxel ID, 4 light values, 4 AO values, and flip ID)
                    # into a single 64-bit integer mask for efficient greedy meshing later.
                    # 41: voxel_id, 33: light_0, 25: light_1, 17: light_2, 9: light_3, 7: ambient_occlusion_0, 5: ambient_occlusion_1, 3: ambient_occlusion_2, 1: ambient_occlusion_3, 0: flip_id
                    mask1[y, z] = (
                        (np.uint64(voxel_id) << 41)
                        | (np.uint64(light_0) << 33)
                        | (np.uint64(light_1) << 25)
                        | (np.uint64(light_2) << 17)
                        | (np.uint64(light_3) << 9)
                        | (np.uint64(ao[0]) << 7)
                        | (np.uint64(ao[1]) << 5)
                        | (np.uint64(ao[2]) << 3)
                        | (np.uint64(ao[3]) << 1)
                        | np.uint64(flip_id)
                    )

        for y in range(CHUNK_SIZE):
            for z in range(CHUNK_SIZE):
                value = mask0[y, z]

                if value:
                    w, h = 1, 1

                    while y + w < CHUNK_SIZE and mask0[y + w, z] == value:
                        w += 1

                    done = False

                    while z + h < CHUNK_SIZE:
                        for index_y in range(w):
                            if mask0[y + index_y, z + h] != value:
                                done = True
                                break

                        if done:
                            break

                        h += 1

                    # Unpack the chunked face attributes from the 64-bit mask value
                    voxel_id = int((value >> 41) & 0xFF)
                    light_0 = int((value >> 33) & 0xFF)
                    light_1 = int((value >> 25) & 0xFF)
                    light_2 = int((value >> 17) & 0xFF)
                    light_3 = int((value >> 9) & 0xFF)

                    ambient_occlusion_0 = int((value >> 7) & 3)
                    ambient_occlusion_1 = int((value >> 5) & 3)
                    ambient_occlusion_2 = int((value >> 3) & 3)
                    ambient_occlusion_3 = int((value >> 1) & 3)
                    flip_id = int(value & 1)

                    # Pack the final geometric vertex data (position, voxel_id, face_id, etc) into a 32-bit int.
                    v0 = pack_data(x + 1, y, z, voxel_id, 2, ambient_occlusion_0, flip_id, light_0)
                    v1 = pack_data(x + 1, y + w, z, voxel_id, 2, ambient_occlusion_1, flip_id, light_1)
                    v2 = pack_data(x + 1, y + w, z + h, voxel_id, 2, ambient_occlusion_2, flip_id, light_2)
                    v3 = pack_data(x + 1, y, z + h, voxel_id, 2, ambient_occlusion_3, flip_id, light_3)

                    if voxel_id == WATER:
                        if flip_id:
                            water_index = add_data(water_data, water_index, v3, v0, v1, v3, v1, v2)
                        else:
                            water_index = add_data(water_data, water_index, v0, v1, v2, v0, v2, v3)

                    else:
                        if flip_id:
                            index = add_data(vertex_data, index, v3, v0, v1, v3, v1, v2)
                        else:
                            index = add_data(vertex_data, index, v0, v1, v2, v0, v2, v3)

                    for index_y in range(w):
                        for index_z in range(h):
                            mask0[y + index_y, z + index_z] = 0

        for y in range(CHUNK_SIZE):
            for z in range(CHUNK_SIZE):
                value = mask1[y, z]

                if value:
                    w, h = 1, 1

                    while y + w < CHUNK_SIZE and mask1[y + w, z] == value:
                        w += 1

                    done = False

                    while z + h < CHUNK_SIZE:
                        for index_y in range(w):
                            if mask1[y + index_y, z + h] != value:
                                done = True
                                break

                        if done:
                            break

                        h += 1

                    # Unpack the chunked face attributes from the 64-bit mask value
                    voxel_id = int((value >> 41) & 0xFF)
                    light_0 = int((value >> 33) & 0xFF)
                    light_1 = int((value >> 25) & 0xFF)
                    light_2 = int((value >> 17) & 0xFF)
                    light_3 = int((value >> 9) & 0xFF)

                    ambient_occlusion_0 = int((value >> 7) & 3)
                    ambient_occlusion_1 = int((value >> 5) & 3)
                    ambient_occlusion_2 = int((value >> 3) & 3)
                    ambient_occlusion_3 = int((value >> 1) & 3)
                    flip_id = int(value & 1)

                    # Pack the final geometric vertex data (position, voxel_id, face_id, etc) into a 32-bit int.
                    v0 = pack_data(x, y, z, voxel_id, 3, ambient_occlusion_0, flip_id, light_0)
                    v1 = pack_data(x, y + w, z, voxel_id, 3, ambient_occlusion_1, flip_id, light_1)
                    v2 = pack_data(x, y + w, z + h, voxel_id, 3, ambient_occlusion_2, flip_id, light_2)
                    v3 = pack_data(x, y, z + h, voxel_id, 3, ambient_occlusion_3, flip_id, light_3)

                    if voxel_id == WATER:
                        if flip_id:
                            water_index = add_data(water_data, water_index, v3, v1, v0, v3, v2, v1)
                        else:
                            water_index = add_data(water_data, water_index, v0, v2, v1, v0, v3, v2)

                    else:
                        if flip_id:
                            index = add_data(vertex_data, index, v3, v1, v0, v3, v2, v1)
                        else:
                            index = add_data(vertex_data, index, v0, v2, v1, v0, v3, v2)

                    for index_y in range(w):
                        for index_z in range(h):
                            mask1[y + index_y, z + index_z] = 0

    # Z PLANES (Back/Front)
    for z in range(CHUNK_SIZE):
        world_z = z + chunk_z * CHUNK_SIZE

        for x in range(CHUNK_SIZE):
            world_x = x + chunk_x * CHUNK_SIZE

            for y in range(CHUNK_SIZE):
                world_y = y + chunk_y * CHUNK_SIZE

                voxel_id = chunk_voxels[x + CHUNK_SIZE * z + CHUNK_AREA * y]

                if not voxel_id:
                    continue

                neighbor_id = get_neighbor_voxel_id(
                    (x, y, z - 1), (world_x, world_y, world_z - 1), chunk_voxels, world_voxels, chunk_positions
                )

                if is_transparent(neighbor_id) and voxel_id != neighbor_id:
                    ao = get_ao(
                        (x, y, z - 1),
                        (world_x, world_y, world_z - 1),
                        chunk_voxels,
                        world_voxels,
                        chunk_positions,
                        plane='Z',
                    )

                    # flip_id = ao[1] + ao[3] > ao[0] + ao[2]
                    voxel_id = (voxel_id | 128) if neighbor_id == WATER else voxel_id

                    face_light = get_neighbor_light(
                        (x, y, z - 1), (world_x, world_y, world_z - 1), chunk_lightmap, world_lightmaps, chunk_positions
                    )
                    light_0 = get_vertex_light(
                        (x, y, z),
                        (world_x, world_y, world_z),
                        'Z',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    light_1 = get_vertex_light(
                        (x, y + 1, z),
                        (world_x, world_y + 1, world_z),
                        'Z',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    light_2 = get_vertex_light(
                        (x + 1, y + 1, z),
                        (world_x + 1, world_y + 1, world_z),
                        'Z',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    light_3 = get_vertex_light(
                        (x + 1, y, z),
                        (world_x + 1, world_y, world_z),
                        'Z',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )

                    # Determine if the quad should be flipped to prevent anisotropic lighting artifacts.
                    # We compare the total lighting (sun + block + ao) of the two diagonals.
                    # The diagonal with the higher total light is split to create smoother gradients.
                    flip_id = ((light_1 >> 4) + (light_1 & 15) + ao[1]) + ((light_3 >> 4) + (light_3 & 15) + ao[3]) > (
                        (light_0 >> 4) + (light_0 & 15) + ao[0]
                    ) + ((light_2 >> 4) + (light_2 & 15) + ao[2])
                    # Pack all vertex attributes (voxel ID, 4 light values, 4 AO values, and flip ID)
                    # into a single 64-bit integer mask for efficient greedy meshing later.
                    # 41: voxel_id, 33: light_0, 25: light_1, 17: light_2, 9: light_3, 7: ambient_occlusion_0, 5: ambient_occlusion_1, 3: ambient_occlusion_2, 1: ambient_occlusion_3, 0: flip_id
                    mask0[x, y] = (
                        (np.uint64(voxel_id) << 41)
                        | (np.uint64(light_0) << 33)
                        | (np.uint64(light_1) << 25)
                        | (np.uint64(light_2) << 17)
                        | (np.uint64(light_3) << 9)
                        | (np.uint64(ao[0]) << 7)
                        | (np.uint64(ao[1]) << 5)
                        | (np.uint64(ao[2]) << 3)
                        | (np.uint64(ao[3]) << 1)
                        | np.uint64(flip_id)
                    )

                neighbor_id = get_neighbor_voxel_id(
                    (x, y, z + 1), (world_x, world_y, world_z + 1), chunk_voxels, world_voxels, chunk_positions
                )

                if is_transparent(neighbor_id) and voxel_id != neighbor_id:
                    ao = get_ao(
                        (x, y, z + 1),
                        (world_x, world_y, world_z + 1),
                        chunk_voxels,
                        world_voxels,
                        chunk_positions,
                        plane='Z',
                    )

                    # flip_id = ao[1] + ao[3] > ao[0] + ao[2]
                    voxel_id = (voxel_id | 128) if neighbor_id == WATER else voxel_id

                    face_light = get_neighbor_light(
                        (x, y, z + 1), (world_x, world_y, world_z + 1), chunk_lightmap, world_lightmaps, chunk_positions
                    )
                    light_0 = get_vertex_light(
                        (x, y, z + 1),
                        (world_x, world_y, world_z + 1),
                        'Z',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    light_1 = get_vertex_light(
                        (x, y + 1, z + 1),
                        (world_x, world_y + 1, world_z + 1),
                        'Z',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    light_2 = get_vertex_light(
                        (x + 1, y + 1, z + 1),
                        (world_x + 1, world_y + 1, world_z + 1),
                        'Z',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )
                    light_3 = get_vertex_light(
                        (x + 1, y, z + 1),
                        (world_x + 1, world_y, world_z + 1),
                        'Z',
                        face_light,
                        chunk_voxels,
                        chunk_lightmap,
                        world_voxels,
                        world_lightmaps,
                        chunk_positions,
                    )

                    # Determine if the quad should be flipped to prevent anisotropic lighting artifacts.
                    # We compare the total lighting (sun + block + ao) of the two diagonals.
                    # The diagonal with the higher total light is split to create smoother gradients.
                    flip_id = ((light_1 >> 4) + (light_1 & 15) + ao[1]) + ((light_3 >> 4) + (light_3 & 15) + ao[3]) > (
                        (light_0 >> 4) + (light_0 & 15) + ao[0]
                    ) + ((light_2 >> 4) + (light_2 & 15) + ao[2])
                    # Pack all vertex attributes (voxel ID, 4 light values, 4 AO values, and flip ID)
                    # into a single 64-bit integer mask for efficient greedy meshing later.
                    # 41: voxel_id, 33: light_0, 25: light_1, 17: light_2, 9: light_3, 7: ambient_occlusion_0, 5: ambient_occlusion_1, 3: ambient_occlusion_2, 1: ambient_occlusion_3, 0: flip_id
                    mask1[x, y] = (
                        (np.uint64(voxel_id) << 41)
                        | (np.uint64(light_0) << 33)
                        | (np.uint64(light_1) << 25)
                        | (np.uint64(light_2) << 17)
                        | (np.uint64(light_3) << 9)
                        | (np.uint64(ao[0]) << 7)
                        | (np.uint64(ao[1]) << 5)
                        | (np.uint64(ao[2]) << 3)
                        | (np.uint64(ao[3]) << 1)
                        | np.uint64(flip_id)
                    )

        for x in range(CHUNK_SIZE):
            for y in range(CHUNK_SIZE):
                value = mask0[x, y]

                if value:
                    w, h = 1, 1

                    while x + w < CHUNK_SIZE and mask0[x + w, y] == value:
                        w += 1

                    done = False

                    while y + h < CHUNK_SIZE:
                        for index_x in range(w):
                            if mask0[x + index_x, y + h] != value:
                                done = True
                                break

                        if done:
                            break

                        h += 1

                    # Unpack the chunked face attributes from the 64-bit mask value
                    voxel_id = int((value >> 41) & 0xFF)
                    light_0 = int((value >> 33) & 0xFF)
                    light_1 = int((value >> 25) & 0xFF)
                    light_2 = int((value >> 17) & 0xFF)
                    light_3 = int((value >> 9) & 0xFF)

                    ambient_occlusion_0 = int((value >> 7) & 3)
                    ambient_occlusion_1 = int((value >> 5) & 3)
                    ambient_occlusion_2 = int((value >> 3) & 3)
                    ambient_occlusion_3 = int((value >> 1) & 3)
                    flip_id = int(value & 1)

                    # Pack the final geometric vertex data (position, voxel_id, face_id, etc) into a 32-bit int.
                    v0 = pack_data(x, y, z, voxel_id, 4, ambient_occlusion_0, flip_id, light_0)
                    v1 = pack_data(x, y + h, z, voxel_id, 4, ambient_occlusion_1, flip_id, light_1)
                    v2 = pack_data(x + w, y + h, z, voxel_id, 4, ambient_occlusion_2, flip_id, light_2)
                    v3 = pack_data(x + w, y, z, voxel_id, 4, ambient_occlusion_3, flip_id, light_3)

                    if voxel_id == WATER:
                        if flip_id:
                            water_index = add_data(water_data, water_index, v3, v0, v1, v3, v1, v2)
                        else:
                            water_index = add_data(water_data, water_index, v0, v1, v2, v0, v2, v3)

                    else:
                        if flip_id:
                            index = add_data(vertex_data, index, v3, v0, v1, v3, v1, v2)
                        else:
                            index = add_data(vertex_data, index, v0, v1, v2, v0, v2, v3)

                    for index_x in range(w):
                        for index_y in range(h):
                            mask0[x + index_x, y + index_y] = 0

        for x in range(CHUNK_SIZE):
            for y in range(CHUNK_SIZE):
                value = mask1[x, y]

                if value:
                    w, h = 1, 1

                    while x + w < CHUNK_SIZE and mask1[x + w, y] == value:
                        w += 1

                    done = False

                    while y + h < CHUNK_SIZE:
                        for index_x in range(w):
                            if mask1[x + index_x, y + h] != value:
                                done = True
                                break

                        if done:
                            break

                        h += 1

                    # Unpack the chunked face attributes from the 64-bit mask value
                    voxel_id = int((value >> 41) & 0xFF)
                    light_0 = int((value >> 33) & 0xFF)
                    light_1 = int((value >> 25) & 0xFF)
                    light_2 = int((value >> 17) & 0xFF)
                    light_3 = int((value >> 9) & 0xFF)

                    ambient_occlusion_0 = int((value >> 7) & 3)
                    ambient_occlusion_1 = int((value >> 5) & 3)
                    ambient_occlusion_2 = int((value >> 3) & 3)
                    ambient_occlusion_3 = int((value >> 1) & 3)
                    flip_id = int(value & 1)

                    # Pack the final geometric vertex data (position, voxel_id, face_id, etc) into a 32-bit int.
                    v0 = pack_data(x, y, z + 1, voxel_id, 5, ambient_occlusion_0, flip_id, light_0)
                    v1 = pack_data(x, y + h, z + 1, voxel_id, 5, ambient_occlusion_1, flip_id, light_1)
                    v2 = pack_data(x + w, y + h, z + 1, voxel_id, 5, ambient_occlusion_2, flip_id, light_2)
                    v3 = pack_data(x + w, y, z + 1, voxel_id, 5, ambient_occlusion_3, flip_id, light_3)

                    if voxel_id == WATER:
                        if flip_id:
                            water_index = add_data(water_data, water_index, v3, v1, v0, v3, v2, v1)
                        else:
                            water_index = add_data(water_data, water_index, v0, v2, v1, v0, v3, v2)

                    else:
                        if flip_id:
                            index = add_data(vertex_data, index, v3, v1, v0, v3, v2, v1)
                        else:
                            index = add_data(vertex_data, index, v0, v2, v1, v0, v3, v2)

                    for index_x in range(w):
                        for index_y in range(h):
                            mask1[x + index_x, y + index_y] = 0

    # Slice and combine opaque and transparent meshes
    opaque_mesh = vertex_data[:index]
    water_mesh = water_data[:water_index]
    combined_mesh = np.hstack((opaque_mesh, water_mesh))

    return combined_mesh, index // format_size, water_index // format_size

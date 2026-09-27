"""
Core procedural terrain and biome generation mechanics.

This module utilizes high-performance `@njit` (Numba) compilation to execute
complex 3D Simplex noise and fractional Brownian motion calculations across the CPU.
It dictates the shaping of landmasses, continentalness modifiers, biome distributions
(sand, snow, grass), cave carving logic, and structural tree generation entirely
lock-free to prevent main-thread latency.
"""

# """
from random import random
from typing import Any, Tuple

from numba import njit

from noise import noise2, noise3
from settings import (
    AIR,
    CENTER_Y,
    CHUNK_AREA,
    CHUNK_SIZE,
    DIRT,
    GLASS,
    GRASS,
    LEAVES,
    SAND,
    SNOW,
    STONE,
    STONE_LVL,
    TREE_H_HEIGHT,
    TREE_H_WIDTH,
    TREE_HEIGHT,
    WATER,
    WATER_LINE,
    WOOD,
    WORLD_HEIGHT,
)


# Terrain generator with temperature, moisture, and continentalness to create distinct biomes and landforms.
# Has Biome Dithering to create more natural transitions and less blocky borders.
@njit(cache=True, fastmath=True, nogil=True)
def get_biome(x: float, z: float, perm_array: Any) -> Tuple[float, float]:
    """
    Evaluates Simplex noise to determine the overarching temperature and moisture
    levels of a specific vertical column, shaping its respective biome.
    """
    # Calculate temperature
    temp = noise2(x * 0.002, z * 0.002, perm_array)

    # Calculate moisture with spatial offset
    moist = noise2(x * 0.002 + 100.0, z * 0.002 + 100.0, perm_array)

    return temp, moist


# Procedural Terrain Generation using Noise
# This function calculates the Y-height of the terrain for any given (X, Z) coordinate.
#
# How it works:
# 1. It uses Fractional Brownian Motion (fBm) by layering multiple "octaves" of
#    Simplex noise. Each subsequent octave has double the frequency (f2, f4, f8)
#    and half the amplitude (a2, a4, a8).
# 2. Summing these layers creates natural-looking fractal terrain, where the first
#    layer defines the massive mountains/valleys, and the last layer defines small bumps.
# 3. We then use a "Continentalness" noise map to warp the final height. If the
#    continentalness is low, we forcefully squash the height map to create flat
#    oceans. If it's high, we amplify the amplitude to create towering peaks.
#
# References:
# - Making Maps with Noise (Amazing visual guide): https://www.redblobgames.com/maps/terrain-from-noise/
# - Fractional Brownian Motion: https://en.wikipedia.org/wiki/Fractional_Brownian_motion
# - Simplex Noise overview: https://en.wikipedia.org/wiki/Simplex_noise


@njit(cache=True, fastmath=True, nogil=True)
def get_height(x: float, z: float, perm_array: Any) -> int:
    """
    Calculates the absolute maximum surface elevation of the terrain at a specific
    X,Z coordinate using fractional Brownian motion and continentalness modifiers.
    """
    # Calculate continentalness
    cont = noise2(x * 0.003 + 100.0, z * 0.003 + 100.0, perm_array)

    # Setup noise octaves
    a1 = CENTER_Y
    a2, a4, a8 = a1 * 0.5, a1 * 0.25, a1 * 0.125
    f1 = 0.005
    f2, f4, f8 = f1 * 2, f1 * 4, f1 * 8

    # Evaluate base height and details
    base_h = noise2(x * f1, z * f1, perm_array) * a1 + a1
    detail_1 = noise2(x * f2, z * f2, perm_array) * a2 - a2
    detail_2 = noise2(x * f4, z * f4, perm_array) * a4 + a4
    detail_3 = noise2(x * f8, z * f8, perm_array) * a8 - a8
    height = base_h + detail_1 + detail_2 + detail_3

    # Shape terrain by continentalness
    if cont < -0.2:
        w = min((-0.2 - cont) * 5.0, 1.0)
        target_h = WATER_LINE - 2 + detail_2 * 0.3 + detail_3 * 0.3
        height = height * (1.0 - w) + target_h * w
    elif cont > 0.4:
        w = min((cont - 0.4) * 5.0, 1.0)
        target_h = base_h * 1.5 + detail_1 * 2.0 + detail_2 + detail_3 + 30
        height = height * (1.0 - w) + target_h * w
    elif 0.1 < cont <= 0.3:
        w = min((cont - 0.1) * 10.0, 1.0) * min((0.3 - cont) * 10.0, 1.0)
        plat_h = CENTER_Y + 12
        if height > plat_h:
            flattened = plat_h + (height - plat_h) * 0.1
            height = height * (1.0 - w) + flattened * w

    # Apply limits and micro-noise
    height = max(height, noise2(x * f8, z * f8, perm_array) + 2)
    height = min(height, WORLD_HEIGHT * CHUNK_SIZE - 2)
    height = max(height, 2.0)

    return int(height)


@njit(cache=True, fastmath=True, nogil=True)
def get_index(x: int, y: int, z: int) -> int:
    """
    Translates a localized 3D chunk coordinate (x, y, z) into a flattened
    1D array index for highly optimized, contiguous memory access.
    """
    return x + CHUNK_SIZE * z + CHUNK_AREA * y


@njit(cache=True, fastmath=True, nogil=True)
def set_voxel_column(
    voxels: Any, x: int, z: int, cx: int, cy: int, cz: int, perm_array: Any, perm_grad_array: Any
) -> None:
    """
    Procedurally generates a single vertical column of blocks within a chunk.
    Applies complex biome mapping, depth stratification, and 3D cave carving logic.
    """
    # Calculate global coordinates and height
    wx = x + cx
    wz = z + cz
    world_height = get_height(wx, wz, perm_array)
    max_h = max(world_height, int(WATER_LINE) + 1)
    local_height = min(max_h - cy, CHUNK_SIZE)
    if local_height <= 0:
        return

    # Determine biome properties
    temp, moist = get_biome(wx, wz, perm_array)
    dither = noise2(wx * 0.2, wz * 0.2, perm_array) * 0.05 + noise2(wx * 0.8, wz * 0.8, perm_array) * 0.03
    temp += dither
    moist += dither
    is_desert = temp > 0.3 and moist < -0.2
    is_snow = temp < -0.2

    # Identify terrain features
    is_underwater = world_height <= WATER_LINE
    is_beach = world_height <= WATER_LINE + 2 and not is_underwater

    # Assign surface blocks based on biome
    if is_underwater or is_beach or is_desert:
        surface_id = SAND
        subsurface_id = SAND
    elif is_snow:
        surface_id = SNOW
        subsurface_id = DIRT
    else:
        surface_id = GRASS
        subsurface_id = DIRT

    # Evaluate depth and noise masks
    dirt_depth = int((noise2(wx * 0.1, wz * 0.1, perm_array) * 0.5 + 0.5) * 5) + 3
    entrance_mask = noise2(wx * 0.02 + 200.0, wz * 0.02 + 200.0, perm_array)
    crust = noise2(wx * 0.1, wz * 0.1, perm_array) * 3 + 3

    # Generate vertical column blocks
    for y in range(local_height):
        wy = y + cy
        voxel_id = 0

        if wy > world_height - 1:
            if wy <= WATER_LINE:
                voxel_id = WATER
        else:
            if wy == world_height - 1:
                voxel_id = surface_id
            elif wy >= world_height - dirt_depth:
                voxel_id = subsurface_id
            else:
                voxel_id = STONE

            if wy > crust:
                surface_dist = world_height - wy
                if not ((is_underwater or is_beach) and surface_dist <= dirt_depth):
                    cave_noise = noise3(wx * 0.09, wy * 0.09, wz * 0.09, perm_array, perm_grad_array)
                    cave_threshold = 0.0
                    if surface_dist < 14:
                        taper_factor = (14 - surface_dist) / 14.0
                        target_threshold = 0.3 + max(0.0, 0.5 - entrance_mask) * 4.0
                        cave_threshold = target_threshold * taper_factor

                    if cave_noise > cave_threshold:
                        voxel_id = 0

        # Set block ID
        if voxel_id:
            voxels[get_index(x, y, z)] = voxel_id

        # Place vegetation
        if wy == world_height - 1 and voxel_id == surface_id and not is_underwater and not is_beach and wy < STONE_LVL:
            tree_prob = 0.0
            if surface_id == GRASS:
                if moist > 0.4:
                    tree_prob = 0.04
                elif moist > 0.0:
                    tree_prob = 0.005
                else:
                    tree_prob = 0.0001
            if tree_prob > 0:
                place_tree(voxels, x, y, z, surface_id, tree_prob)


@njit(cache=True, fastmath=True, nogil=True)
def place_tree(voxels: Any, x: int, y: int, z: int, voxel_id: int, tree_prob: float) -> None:
    """
    Constructs a localized tree structure (wood trunk and spherical leaf crown)
    within the chunk volume if probability and physical boundaries allow for it.
    """
    # Evaluate probability and bounds
    rnd = random()
    if rnd > tree_prob:
        return None
    if y + TREE_HEIGHT >= CHUNK_SIZE:
        return None
    if x - TREE_H_WIDTH < 0 or x + TREE_H_WIDTH >= CHUNK_SIZE:
        return None
    if z - TREE_H_WIDTH < 0 or z + TREE_H_WIDTH >= CHUNK_SIZE:
        return None

    # Place dirt foundation
    voxels[get_index(x, y, z)] = DIRT

    # Generate leaf crown
    m = 0
    for n, iy in enumerate(range(TREE_H_HEIGHT, TREE_HEIGHT - 1)):
        k = iy % 2
        rng = int(random() * 2)
        for ix in range(-TREE_H_WIDTH + m, TREE_H_WIDTH - m * rng):
            for iz in range(-TREE_H_WIDTH + m * rng, TREE_H_WIDTH - m):
                if (ix + iz) % 4:
                    voxels[get_index(x + ix + k, y + iy, z + iz + k)] = LEAVES
        m += 1 if n > 0 else 3 if n > 1 else 0

    # Generate wood trunk
    for iy in range(1, TREE_HEIGHT - 2):
        voxels[get_index(x, y + iy, z)] = WOOD

    # Place top leaf
    voxels[get_index(x, y + TREE_HEIGHT - 2, z)] = LEAVES


@njit(cache=True, fastmath=True, nogil=True)
def fill_initial_sunlight(voxels: Any, lightmap: Any, cx: int, cy: int, cz: int, perm_array: Any) -> None:
    """
    Initializes a newly generated chunk's lightmap by simulating direct,
    overhead sunlight falling vertically onto the procedural terrain layout.
    """
    # Evaluate sunlight per column
    for x in range(CHUNK_SIZE):
        for z in range(CHUNK_SIZE):
            wx = x + cx
            wz = z + cz
            world_height = get_height(wx, wz, perm_array)

            # Assign sunlight based on block depth
            for y in range(CHUNK_SIZE):
                wy = y + cy
                index = get_index(x, y, z)

                if wy >= world_height:
                    voxel_id = voxels[index]
                    if voxel_id == AIR or voxel_id == GLASS:
                        lightmap[index] = (15 << 4) | 0
                    elif voxel_id == WATER:
                        depth = world_height - wy
                        sun = max(0, 15 + depth * 2)
                        lightmap[index] = (sun << 4) | 0
                    elif voxel_id == LEAVES:
                        lightmap[index] = (14 << 4) | 0
                    else:
                        lightmap[index] = 0
                else:
                    lightmap[index] = 0

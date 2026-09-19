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
    # Calculate temperature by evaluating 2D Simplex noise at the given (x, z) coordinates.
    # The coordinate scaling factor of 0.002 represents the frequency of the noise.
    # A smaller frequency stretches the noise out, resulting in massive, sprawling biomes
    # rather than rapidly alternating hot/cold patches. The noise output inherently ranges
    # from approximately -1.0 to 1.0.
    temp = noise2(x * 0.002, z * 0.002, perm_array)

    # Calculate moisture using the same 2D Simplex noise function and frequency scaling (0.002).
    # We add a fixed offset of 100.0 to both the x and z coordinates before evaluation.
    # This acts as a spatial translation, sampling the noise field from a distant region.
    # Since Simplex noise is deterministic but pseudorandom, this effectively generates a
    # completely independent, uncorrelated moisture map using the same permutation array,
    # ensuring temperature and moisture don't mirror each other.
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
    # Calculate continentalness using 2D Simplex noise, acting as an overarching
    # macro-scale terrain modifier. The frequency 0.003 dictates very broad geographical
    # features (continents and oceans). We apply a spatial offset of +100.0 to x and z
    # to decouple this noise map from the temperature/moisture maps, preventing correlation.
    cont = noise2(x * 0.003 + 100.0, z * 0.003 + 100.0, perm_array)

    # Base properties for the first octave (the fundamental shape of the terrain).
    # a1 represents the amplitude (maximum vertical displacement) of the primary base terrain.
    a1 = CENTER_Y

    # Calculate the amplitudes for the subsequent octaves (detail layers).
    # In standard fractional Brownian motion (fBm), amplitude halves with each octave
    # (persistence = 0.5), meaning finer details have progressively less vertical impact.
    a2, a4, a8 = a1 * 0.5, a1 * 0.25, a1 * 0.125

    # f1 represents the frequency (horizontal stretching) of the primary base terrain.
    f1 = 0.005

    # Calculate the frequencies for the subsequent octaves.
    # In standard fBm, frequency doubles with each octave (lacunarity = 2.0),
    # meaning each new layer adds smaller, more tightly packed details.
    f2, f4, f8 = f1 * 2, f1 * 4, f1 * 8

    # Evaluate the first octave (base height). We multiply the noise output [-1, 1]
    # by amplitude a1 to scale it to [-a1, a1]. We then add a1 to shift the range to [0, 2*a1],
    # ensuring the base terrain sits entirely above y=0, centered around a1.
    base_h = noise2(x * f1, z * f1, perm_array) * a1 + a1

    # Evaluate the second octave (first detail pass). Multiplied by its smaller amplitude a2
    # for a range of [-a2, a2]. We subtract a2 to shift the range downwards to [-2*a2, 0].
    # This creates a bias towards carving out valleys and lowering peaks relative to the base height.
    detail_1 = noise2(x * f2, z * f2, perm_array) * a2 - a2

    # Evaluate the third octave. Multiplied by a4, yielding [-a4, a4]. Adding a4 shifts
    # the range upwards to [0, 2*a4], adding small bumps and localized ridges.
    detail_2 = noise2(x * f4, z * f4, perm_array) * a4 + a4

    # Evaluate the fourth octave. Multiplied by a8, yielding [-a8, a8]. Subtracting a8 shifts
    # the range downwards to [-2*a8, 0], etching fine erosion patterns and micro-valleys.
    detail_3 = noise2(x * f8, z * f8, perm_array) * a8 - a8

    # Superimpose all the fractional Brownian motion octaves together. This linear combination
    # fuses the massive base structure with the progressively finer surface details.
    height = base_h + detail_1 + detail_2 + detail_3

    # Terrain Shaping based on Continentalness
    if cont < -0.2:
        # Deep Plains & Oceans (Flatter and lower)
        # Calculate a blending weight 'w'. We measure how deep the continentalness goes below -0.2.
        # Multiplying by 5.0 scales this penetration such that cont values from -0.2 to -0.4
        # map to weights from 0.0 to 1.0. The min() clamps the maximum weight at 1.0.
        w = min((-0.2 - cont) * 5.0, 1.0)

        # Define the target height for oceans/plains. We start near the WATER_LINE,
        # and only include the smallest detail octaves (scaled down by 0.3) to keep the seabed flat.
        target_h = WATER_LINE - 2 + detail_2 * 0.3 + detail_3 * 0.3

        # Linearly interpolate (lerp) between the original highly-varied height and the flattened
        # target_h, using the blend weight w. As continentalness decreases, the terrain flattens out.
        height = height * (1.0 - w) + target_h * w

    elif cont > 0.4:
        # Extreme Mountains
        # Calculate blending weight 'w' measuring how far continentalness exceeds 0.4.
        # Scaled by 5.0, cont values from 0.4 to 0.6 map to weights from 0.0 to 1.0. Clamped to 1.0.
        w = min((cont - 0.4) * 5.0, 1.0)

        # Define the target mountain height. We heavily exaggerate the base height (x1.5)
        # and the largest detail layer (x2.0), while keeping smaller details normal.
        # A static +30 offset ensures these peaks definitively tower over everything else.
        target_h = base_h * 1.5 + detail_1 * 2.0 + detail_2 + detail_3 + 30

        # Linearly interpolate between the standard terrain height and the exaggerated
        # mountain height using weight w, causing terrain to soar smoothly upwards.
        height = height * (1.0 - w) + target_h * w

    elif 0.1 < cont <= 0.3:
        # Plateaus (steep cliffs, flat tops)
        # Calculate a dual-sided weight using a bell-curve-like mapping.
        # (cont - 0.1) * 10.0 goes from 0 to 1 as cont goes 0.1 -> 0.2.
        # (0.3 - cont) * 10.0 goes from 0 to 1 as cont goes 0.3 -> 0.2.
        # Multiplying these clamps shapes a peak weight of ~1.0 at cont=0.2, fading to 0 at the edges.
        w = min((cont - 0.1) * 10.0, 1.0) * min((0.3 - cont) * 10.0, 1.0)

        # Define the fixed plateau altitude, hovering just above the world center.
        plat_h = CENTER_Y + 12

        # If the underlying raw terrain attempts to poke above the plateau altitude,
        # we forcefully squash it down.
        if height > plat_h:
            # Compress any height exceeding plat_h to only 10% of its original overage,
            # effectively shearing the tops off mountains to create flat plateau surfaces.
            flattened = plat_h + (height - plat_h) * 0.1

            # Interpolate between the raw towering height and the sheared plateau surface
            # using our localized plateau weight w.
            height = height * (1.0 - w) + flattened * w

    # A final micro-noise perturbation at the highest frequency (f8) is evaluated and added to 2.
    # The terrain height is then clamped via max() to never drop below this noisy floor.
    # This prevents the absolute lowest bedrock layers from being perfectly flat.
    height = max(height, noise2(x * f8, z * f8, perm_array) + 2)

    # Absolute safety nets: prevent terrain from ever exceeding the chunk limits
    # Cap the maximum height slightly below the total world chunk volume limit to avoid Out-Of-Bounds errors.
    height = min(height, WORLD_HEIGHT * CHUNK_SIZE - 2)

    # Cap the absolute minimum height to 2.0 to ensure a solid, unbreakable bedrock floor always exists.
    height = max(height, 2.0)

    # Cast the floating-point height evaluation into an integer index to align with the voxel grid.
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
    wx = x + cx
    wz = z + cz
    world_height = get_height(wx, wz, perm_array)

    max_h = max(world_height, int(WATER_LINE) + 1)
    local_height = min(max_h - cy, CHUNK_SIZE)

    if local_height <= 0:
        return

    # Determine biome and surface blocks ONCE per column (Huge Optimization)
    temp, moist = get_biome(wx, wz, perm_array)

    # Add natural dithering to the biome borders so blocks mix organically
    dither = noise2(wx * 0.2, wz * 0.2, perm_array) * 0.05 + noise2(wx * 0.8, wz * 0.8, perm_array) * 0.03
    temp += dither
    moist += dither

    is_desert = temp > 0.3 and moist < -0.2
    is_snow = temp < -0.2

    # Define Water bodies and Beaches based on height!
    # Any terrain dipping below WATER_LINE naturally acts as a lake/ocean.
    is_underwater = world_height <= WATER_LINE
    is_beach = world_height <= WATER_LINE + 2 and not is_underwater

    # Exactly as requested: Sand ONLY in deserts, lakes, oceans, and beaches!
    if is_underwater or is_beach or is_desert:
        surface_id = SAND
        subsurface_id = SAND

    elif is_snow:
        surface_id = SNOW
        subsurface_id = DIRT

    else:
        surface_id = GRASS
        subsurface_id = DIRT

    # Depth logic
    # Deterministic noise for dirt depth mapping from 3 to 8 blocks deep
    dirt_depth = int((noise2(wx * 0.1, wz * 0.1, perm_array) * 0.5 + 0.5) * 5) + 3

    # Pre-calculate 2D masks once per column instead of every Y block
    entrance_mask = noise2(wx * 0.02 + 200.0, wz * 0.02 + 200.0, perm_array)
    crust = noise2(wx * 0.1, wz * 0.1, perm_array) * 3 + 3

    for y in range(local_height):
        wy = y + cy
        voxel_id = 0

        if wy > world_height - 1:
            if wy <= WATER_LINE:
                voxel_id = WATER

        else:
            # Determine default solid block type
            if wy == world_height - 1:
                voxel_id = surface_id

            elif wy >= world_height - dirt_depth:
                voxel_id = subsurface_id

            else:
                voxel_id = STONE

            if wy > crust:
                surface_dist = world_height - wy

                # Keep water/beaches intact by blocking cave generation entirely in the top sand/dirt layers
                if not ((is_underwater or is_beach) and surface_dist <= dirt_depth):
                    # Cave Carving using 3D noise
                    cave_noise = noise3(wx * 0.09, wy * 0.09, wz * 0.09, perm_array, perm_grad_array)
                    cave_threshold = 0.0

                    # Taper the cave noise threshold near the surface to create natural, narrow cave mouths
                    if surface_dist < 14:
                        # Smoothly increase the threshold as we get closer to the surface
                        taper_factor = (14 - surface_dist) / 14.0
                        target_threshold = 0.3 + max(0.0, 0.5 - entrance_mask) * 4.0
                        cave_threshold = target_threshold * taper_factor

                    if cave_noise > cave_threshold:
                        voxel_id = 0

        # setting ID
        if voxel_id:
            voxels[get_index(x, y, z)] = voxel_id

        # Place Tree: No trees underwater, no trees on high mountains, no trees on snow, no floating trees!
        if wy == world_height - 1 and voxel_id == surface_id and not is_underwater and not is_beach and wy < STONE_LVL:
            tree_prob = 0.0

            if surface_id == GRASS:
                if moist > 0.4:
                    tree_prob = 0.04  # Dense forest

                elif moist > 0.0:
                    tree_prob = 0.005  # Sparse woods

                else:
                    tree_prob = 0.0001  # Extreme plains (~1 tree every 5 chunks)

            if tree_prob > 0:
                place_tree(voxels, x, y, z, surface_id, tree_prob)


@njit(cache=True, fastmath=True, nogil=True)
def place_tree(voxels: Any, x: int, y: int, z: int, voxel_id: int, tree_prob: float) -> None:
    """
    Constructs a localized tree structure (wood trunk and spherical leaf crown)
    within the chunk volume if probability and physical boundaries allow for it.
    """
    rnd = random()
    if rnd > tree_prob:
        return None

    if y + TREE_HEIGHT >= CHUNK_SIZE:
        return None

    if x - TREE_H_WIDTH < 0 or x + TREE_H_WIDTH >= CHUNK_SIZE:
        return None

    if z - TREE_H_WIDTH < 0 or z + TREE_H_WIDTH >= CHUNK_SIZE:
        return None

    # dirt under the tree
    voxels[get_index(x, y, z)] = DIRT

    # leaves
    m = 0
    for n, iy in enumerate(range(TREE_H_HEIGHT, TREE_HEIGHT - 1)):
        k = iy % 2
        rng = int(random() * 2)

        for ix in range(-TREE_H_WIDTH + m, TREE_H_WIDTH - m * rng):
            for iz in range(-TREE_H_WIDTH + m * rng, TREE_H_WIDTH - m):
                if (ix + iz) % 4:
                    voxels[get_index(x + ix + k, y + iy, z + iz + k)] = LEAVES

        m += 1 if n > 0 else 3 if n > 1 else 0

    # tree trunk
    for iy in range(1, TREE_HEIGHT - 2):
        voxels[get_index(x, y + iy, z)] = WOOD

    # top
    voxels[get_index(x, y + TREE_HEIGHT - 2, z)] = LEAVES


@njit(cache=True, fastmath=True, nogil=True)
def fill_initial_sunlight(voxels: Any, lightmap: Any, cx: int, cy: int, cz: int, perm_array: Any) -> None:
    """
    Initializes a newly generated chunk's lightmap by simulating direct,
    overhead sunlight falling vertically onto the procedural terrain layout.
    """
    for x in range(CHUNK_SIZE):
        for z in range(CHUNK_SIZE):
            wx = x + cx
            wz = z + cz
            world_height = get_height(wx, wz, perm_array)

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

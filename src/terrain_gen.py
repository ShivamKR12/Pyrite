"""
Core procedural terrain and biome generation mechanics.

This module utilizes high-performance `@njit` (Numba) compilation to execute
complex 3D Simplex noise and fractional Brownian motion calculations across the CPU.
It dictates the shaping of landmasses, continentalness modifiers, biome distributions
(sand, snow, grass), cave carving logic, and structural tree generation entirely
lock-free to prevent main-thread latency.
"""

# """
import random
from typing import Any, Tuple

from numba import njit

from noise import noise2, noise3
from settings import (
    ACACIA_LOG,
    AIR,
    BIRCH_LOG,
    CENTER_XZ,
    CENTER_Y,
    CHUNK_AREA,
    CHUNK_SIZE,
    DARK_OAK_LOG,
    DIRT,
    GLASS,
    GRASS,
    JUNGLE_LOG,
    OAK_LEAVES,
    OAK_LOG,
    SAND,
    SNOW,
    SPRUCE_LOG,
    STONE,
    STONE_LVL,
    TREE_H_HEIGHT,
    TREE_H_WIDTH,
    TREE_HEIGHT,
    WATER,
    WATER_LINE,
    WORLD_HEIGHT,
)
from terrain_data import (
    BEACH,
    BIOME_TABLE,
    BIRCH_FOREST,
    CONTINENTALNESS_RANGES,
    CONTINENTALNESS_SPLINE,
    DESERT,
    EROSION_RANGES,
    FOREST,
    HUMIDITY_RANGES,
    JAGGED_PEAKS,
    JUNGLE,
    OCEAN,
    PV_RANGES,
    SAVANNA,
    SNOWY_BEACH,
    SNOWY_PLAINS,
    SNOWY_TAIGA,
    STONY_PEAKS,
    STONY_SHORE,
    SWAMP,
    TAIGA,
    TEMPERATURE_RANGES,
)

# Terrain generator with temperature, moisture, and continentalness to create distinct biomes and landforms.
# Has Biome Dithering to create more natural transitions and less blocky borders.


@njit(cache=True, fastmath=True, nogil=True)
def get_terrain_factors(x: float, z: float, perm_array: Any) -> Tuple[float, float, float, float, float]:
    """
    Calculates the five abstract 2D noise fields that drive terrain and biome generation.

    Returns:
        A tuple containing (continentalness, erosion, pv, temperature, humidity).
    """
    # 1. Continentalness: Low-frequency noise for large landmasses vs. oceans.
    cont = noise2(x * 0.0032, z * 0.0032, perm_array)  # 4x frequency for smaller continents

    # 2. Erosion: Medium-frequency noise for jagged vs. smooth terrain.
    erosion = noise2(x * 0.002, z * 0.002, perm_array)

    # 3. Peaks & Valleys (PV): Higher-frequency noise for local hills and ridges.
    pv_base = noise2(x * 0.005, z * 0.005, perm_array)  # Keep this for terrain detail
    pv_detail = noise2(x * 0.02, z * 0.02, perm_array) * 0.25
    pv = pv_base + pv_detail

    # 4. Temperature: Very low-frequency noise for broad climate zones.
    temp = noise2(x * 0.002, z * 0.002, perm_array)  # 4x frequency for smaller climate zones

    # 5. Humidity: Low-frequency noise for moisture levels (deserts vs. swamps).
    humidity = noise2(x * 0.004, z * 0.004, perm_array)  # 4x frequency for smaller humidity zones

    return cont, erosion, pv, temp, humidity


@njit(cache=True, fastmath=True, nogil=True)
def interpolate_spline(value: float, spline: Any) -> Tuple[float, float]:
    """
    Performs linear interpolation on a 2D spline data structure.

    Finds the two points in the spline that bracket the input value and
    interpolates the two corresponding output values.

    Args:
        value (float): The input noise value to interpolate.
        spline (Any): A Numba-compatible 2D NumPy array representing the spline.

    Returns:
        A tuple containing the two interpolated output values.
    """
    # Find the segment of the spline that the value falls into
    for i in range(len(spline) - 1):
        x1, y1_out1, y1_out2 = spline[i]
        x2, y2_out1, y2_out2 = spline[i + 1]

        if x1 <= value <= x2:
            # Linear interpolation factor
            t = (value - x1) / (x2 - x1)

            # Interpolate both output values
            out1 = y1_out1 + t * (y2_out1 - y1_out1)
            out2 = y1_out2 + t * (y2_out2 - y1_out2)
            return out1, out2

    # If value is outside the spline's range, clamp to the nearest end
    if value < spline[0][0]:
        return spline[0][1], spline[0][2]
    return spline[-1][1], spline[-1][2]


@njit(cache=True, fastmath=True, nogil=True)
def get_slice_index(value: float, ranges: Any) -> int:
    """
    Converts a continuous noise value (-1.0 to 1.0) into a discrete index
    by finding where it falls within the provided slicing ranges.
    """
    for i in range(len(ranges)):
        if value <= ranges[i]:
            return i
    return len(ranges)  # Return the last slice index if value is greater than all ranges


@njit(cache=True, fastmath=True, nogil=True)
def get_biome(cont: float, erosion: float, pv: float, temp: float, humidity: float) -> int:
    """
    Determines the biome for a location using the 5D Biome Matrix.

    Takes the five continuous noise values, converts them to discrete indices,
    and performs a lookup in the BIOME_TABLE to get the final biome ID.

    Returns:
        The integer ID of the determined biome.
    """
    temp_idx = get_slice_index(temp, TEMPERATURE_RANGES)
    hum_idx = get_slice_index(humidity, HUMIDITY_RANGES)
    cont_idx = get_slice_index(cont, CONTINENTALNESS_RANGES)
    ero_idx = get_slice_index(erosion, EROSION_RANGES)
    pv_idx = get_slice_index(pv, PV_RANGES)

    # Perform the 5D lookup
    biome_id = BIOME_TABLE[temp_idx, hum_idx, cont_idx, ero_idx, pv_idx]
    return biome_id


@njit(cache=True, fastmath=True, nogil=True)
def get_terrain_params(x: float, z: float, perm_array: Any) -> Tuple[float, float, int]:
    """
    Calculates the final terrain parameters by blending noise fields through splines.

    Args:
        x (float): World-space X coordinate.
        z (float): World-space Z coordinate.
        perm_array (Any): The Numba-compatible noise permutation array.

    Returns:
        A tuple containing (height_offset, squashing_factor, biome_id).
    """
    cont, erosion, pv, temp, humidity = get_terrain_factors(x, z, perm_array)

    # Use the new spline system to determine height and squashing
    height_offset, squashing_factor = interpolate_spline(cont, CONTINENTALNESS_SPLINE)

    # Add peaks and valleys for detail
    height_offset += pv * 10

    biome_id = get_biome(cont, erosion, pv, temp, humidity)

    return height_offset, squashing_factor, biome_id


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

    height_offset, squashing_factor, biome_id = get_terrain_params(wx, wz, perm_array)

    # Determine surface blocks based on biome ID
    surface_id = GRASS
    tree_type = OAK_LOG

    if biome_id in (OCEAN, BEACH):
        surface_id = SAND
    elif biome_id in (DESERT, SAVANNA):
        surface_id = SAND
        tree_type = ACACIA_LOG
    elif biome_id in (SNOWY_PLAINS, SNOWY_TAIGA, SNOWY_BEACH):
        surface_id = SNOW
        tree_type = SPRUCE_LOG
    elif biome_id in (JAGGED_PEAKS, STONY_PEAKS, STONY_SHORE):
        surface_id = STONE
    elif biome_id == TAIGA:
        tree_type = SPRUCE_LOG
    elif biome_id == BIRCH_FOREST:
        tree_type = BIRCH_LOG
    elif biome_id == JUNGLE:
        tree_type = JUNGLE_LOG

    # Determine subsurface block
    subsurface_id = DIRT
    if biome_id in (DESERT, SAVANNA, BEACH):
        subsurface_id = SAND

    dirt_depth = int((noise2(wx * 0.1, wz * 0.1, perm_array) * 0.5 + 0.5) * 5) + 3

    placed_tree = False
    for y in range(CHUNK_SIZE):
        wy = y + cy

        # 1. Calculate 3D density noise
        density = noise3(wx * 0.01, wy * 0.01, wz * 0.01, perm_array, perm_grad_array)

        # 2. Apply height bias (squashing)
        density -= (wy - height_offset) * squashing_factor

        # 3. Determine if the block is solid or air based on density
        if density > 0:
            # Find the surface to apply grass/dirt
            density_above = noise3(wx * 0.01, (wy + 1) * 0.01, wz * 0.01, perm_array, perm_grad_array)
            density_above -= ((wy + 1) - height_offset) * squashing_factor

            # Place Tree: No trees underwater, no trees on high mountains, no trees on snow, no floating trees!
            if not placed_tree and density_above <= 0 and wy > WATER_LINE and wy < STONE_LVL and surface_id == GRASS:
                if random.random() < 0.005:
                    place_tree_at(voxels, x, y, z, tree_type)
                    placed_tree = True
            # Determine block type based on depth from the surface
            if density_above <= 0:
                voxels[get_index(x, y, z)] = surface_id
            else:
                # Check density a few blocks down to determine if it's subsurface or deep stone
                density_below = noise3(wx * 0.01, (wy - dirt_depth) * 0.01, wz * 0.01, perm_array, perm_grad_array)
                density_below -= ((wy - dirt_depth) - height_offset) * squashing_factor
                if density_below > 0:
                    voxels[get_index(x, y, z)] = STONE
                else:
                    voxels[get_index(x, y, z)] = subsurface_id

        else:
            # It's air, but check if it should be water
            if wy <= WATER_LINE:
                voxels[get_index(x, y, z)] = WATER
            else:
                voxels[get_index(x, y, z)] = AIR


@njit(cache=True, fastmath=True, nogil=True)
def place_oak_tree(voxels: Any, x: int, y: int, z: int, trunk_id: int) -> None:
    """
    Constructs a standard oak-like tree with a spherical leaf crown.
    """
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
        rng = int(random.random() * 2)

        for ix in range(-TREE_H_WIDTH + m, TREE_H_WIDTH - m * rng):
            for iz in range(-TREE_H_WIDTH + m * rng, TREE_H_WIDTH - m):
                if (ix + iz) % 4:
                    voxels[get_index(x + ix + k, y + iy, z + iz + k)] = OAK_LEAVES

        m += 1 if n > 0 else 3 if n > 1 else 0

    # tree trunk
    for iy in range(1, TREE_HEIGHT - 2):
        voxels[get_index(x, y + iy, z)] = trunk_id

    # top
    voxels[get_index(x, y + TREE_HEIGHT - 2, z)] = OAK_LEAVES


@njit(cache=True, fastmath=True, nogil=True)
def place_spruce_tree(voxels: Any, x: int, y: int, z: int, trunk_id: int) -> None:
    """
    Constructs a conical spruce/pine tree.
    """
    height = TREE_HEIGHT + 2
    if y + height >= CHUNK_SIZE:
        return None

    voxels[get_index(x, y, z)] = DIRT

    # Conical leaves
    radius = 0
    for iy in range(height, 2, -1):
        if iy % 2 == 0:
            radius += 1
        for ix in range(-radius, radius + 1):
            for iz in range(-radius, radius + 1):
                if ix * ix + iz * iz <= radius * radius:
                    if 0 <= x + ix < CHUNK_SIZE and 0 <= z + iz < CHUNK_SIZE:
                        voxels[get_index(x + ix, y + iy, z + iz)] = OAK_LEAVES

    # Trunk
    for iy in range(1, height):
        voxels[get_index(x, y + iy, z)] = trunk_id


@njit(cache=True, fastmath=True, nogil=True)
def place_acacia_tree(voxels: Any, x: int, y: int, z: int, trunk_id: int) -> None:
    """
    Constructs an acacia-style tree with a forked trunk and a flat top.
    """
    height = TREE_HEIGHT - 1
    if y + height + 2 >= CHUNK_SIZE:
        return

    voxels[get_index(x, y, z)] = DIRT

    # Forked trunk
    for i in range(height // 2):
        voxels[get_index(x, y + 1 + i, z)] = trunk_id

    voxels[get_index(x + 1, y + 1 + height // 2, z + 1)] = trunk_id
    voxels[get_index(x + 1, y + 2 + height // 2, z + 2)] = trunk_id
    voxels[get_index(x, y + 3 + height // 2, z + 2)] = trunk_id

    # Flat canopy
    canopy_y = y + height
    for ix in range(-2, 3):
        for iz in range(-3, 3):
            if 0 <= x + ix < CHUNK_SIZE and 0 <= z + iz < CHUNK_SIZE:
                voxels[get_index(x + ix, canopy_y, z + iz)] = OAK_LEAVES
                if random.random() < 0.5:
                    voxels[get_index(x + ix, canopy_y + 1, z + iz)] = OAK_LEAVES


@njit(cache=True, fastmath=True, nogil=True)
def place_jungle_tree(voxels: Any, x: int, y: int, z: int, trunk_id: int) -> None:
    """
    Constructs a tall jungle tree.
    """
    height = TREE_HEIGHT + 6
    if y + height >= CHUNK_SIZE:
        return

    voxels[get_index(x, y, z)] = DIRT

    # Trunk
    for iy in range(1, height):
        voxels[get_index(x, y + iy, z)] = trunk_id

    # Canopy
    for iy in range(height - 3, height + 1):
        radius = 2 if iy < height else 1
        for ix in range(-radius, radius + 1):
            for iz in range(-radius, radius + 1):
                if ix != 0 or iz != 0:  # Leave center hollow for trunk
                    if 0 <= x + ix < CHUNK_SIZE and 0 <= z + iz < CHUNK_SIZE:
                        voxels[get_index(x + ix, iy + y, z + iz)] = OAK_LEAVES


@njit(cache=True, fastmath=True, nogil=True)
def place_tree_at(voxels: Any, x: int, y: int, z: int, tree_type: int) -> None:
    """
    Dispatcher function that calls the correct tree generation logic based on the tree type ID.
    """
    if tree_type == SPRUCE_LOG:
        place_spruce_tree(voxels, x, y, z, tree_type)
    elif tree_type == ACACIA_LOG:
        place_acacia_tree(voxels, x, y, z, tree_type)
    elif tree_type == JUNGLE_LOG:
        place_jungle_tree(voxels, x, y, z, tree_type)
    else:  # Default to Oak/Birch style
        place_oak_tree(voxels, x, y, z, tree_type)


@njit(cache=True, fastmath=True, nogil=True)
def fill_initial_sunlight(voxels: Any, lightmap: Any, cx: int, cy: int, cz: int, perm_array: Any, seed: int) -> None:
    """
    Initializes a newly generated chunk's lightmap by simulating direct,
    overhead sunlight falling vertically onto the procedural terrain layout.
    """
    # Seed the random generator for deterministic tree placement
    # Numba requires this to be done inside the JIT-compiled function
    random.seed(seed ^ cx ^ cy ^ cz)

    for x in range(CHUNK_SIZE):
        for z in range(CHUNK_SIZE):
            sun_level = 15
            for y in range(CHUNK_SIZE - 1, -1, -1):
                index = get_index(x, y, z)
                voxel_id = voxels[index]

                if sun_level > 0:
                    lightmap[index] = (sun_level << 4) | (lightmap[index] & 0x0F)

                if voxel_id == WATER or voxel_id == OAK_LEAVES:
                    sun_level = max(0, sun_level - 2)
                elif voxel_id == AIR or voxel_id == GLASS:
                    sun_level = 15  # Sunlight passes through air/glass without losing strength
                else:
                    sun_level = 0  # Opaque block, stop all light

# """
from noise import noise2, noise3
from random import random
from settings import *


# Terrain generator with temperature, moisture, and continentalness to create distinct biomes and landforms.
# Has Biome Dithering to create more natural transitions and less blocky borders.
@njit(cache=True)
def get_biome(x, z):
    # Temperature and Moisture noise to determine biome type (returns approx -1.0 to 1.0)
    # Scaled down frequencies by 10x to create massive, sprawling biomes
    temp = noise2(x * 0.002, z * 0.002)
    moist = noise2(x * 0.002 + 100.0, z * 0.002 + 100.0)
    return temp, moist

@njit(cache=True)
def get_height(x, z):
    temp, moist = get_biome(x, z)

    # Continentalness: Controls overall elevation independently from climate
    # This creates distinct Plains, Hills, Plateaus, and Mountains!
    cont = noise2(x * 0.003 + 100.0, z * 0.003 + 100.0)

    # Base properties
    a1 = CENTER_Y
    a2, a4, a8 = a1 * 0.5, a1 * 0.25, a1 * 0.125
    f1 = 0.005
    f2, f4, f8 = f1 * 2, f1 * 4, f1 * 8

    base_h = noise2(x * f1, z * f1) * a1 + a1
    detail_1 = noise2(x * f2, z * f2) * a2 - a2
    detail_2 = noise2(x * f4, z * f4) * a4 + a4
    detail_3 = noise2(x * f8, z * f8) * a8 - a8

    height = base_h + detail_1 + detail_2 + detail_3

    # Terrain Shaping based on Continentalness
    if cont < -0.2:
        # Deep Plains & Oceans (Flatter and lower)
        w = min((-0.2 - cont) * 5.0, 1.0)
        target_h = WATER_LINE - 2 + detail_2 * 0.3 + detail_3 * 0.3
        height = height * (1.0 - w) + target_h * w
    elif cont > 0.4:
        # Extreme Mountains
        w = min((cont - 0.4) * 5.0, 1.0)
        target_h = base_h * 1.5 + detail_1 * 2.0 + detail_2 + detail_3 + 30
        height = height * (1.0 - w) + target_h * w
    elif cont > 0.1 and cont <= 0.3:
        # Plateaus (steep cliffs, flat tops)
        w = min((cont - 0.1) * 10.0, 1.0) * min((0.3 - cont) * 10.0, 1.0)
        plat_h = CENTER_Y + 12
        if height > plat_h:
            flattened = plat_h + (height - plat_h) * 0.1
            height = height * (1.0 - w) + flattened * w

    height = max(height,  noise2(x * f8, z * f8) + 2)
    
    # Absolute safety net: prevent terrain from ever exceeding the top chunk's limit
    height = min(height, WORLD_H * CHUNK_SIZE - 2)

    return int(height)


@njit(cache=True)
def get_index(x, y, z):
    return x + CHUNK_SIZE * z + CHUNK_AREA * y


@njit(cache=True)
def set_voxel_id(voxels, x, y, z, wx, wy, wz, world_height):
    voxel_id = 0

    # Determine biome and surface blocks
    temp, moist = get_biome(wx, wz)
    
    # Add natural dithering to the biome borders so blocks mix organically
    dither = noise2(wx * 0.2, wz * 0.2) * 0.05 + noise2(wx * 0.8, wz * 0.8) * 0.03
    temp += dither
    moist += dither
    
    is_desert = temp > 0.3 and moist < -0.2
    is_snow = temp < -0.2

    # Define Water bodies and Beaches based on height!
    # Any terrain dipping below WATER_LINE naturally acts as a lake/ocean.
    is_underwater = world_height <= WATER_LINE
    is_beach = world_height <= WATER_LINE + 2 and not is_underwater

    # Exactly as requested: Sand ONLY in deserts, lakes, oceans, and beaches!
    if is_underwater or is_beach:
        surface_id = SAND
        subsurface_id = SAND
    elif is_desert:
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
    dirt_depth = int((noise2(wx * 0.1, wz * 0.1) * 0.5 + 0.5) * 5) + 3

    if wy > world_height - 1:
        if wy <= WATER_LINE:
            voxel_id = WATER
        else:
            pass # Air
    else:
        # Determine default solid block type
        if wy == world_height - 1:
            voxel_id = surface_id
        elif wy >= world_height - dirt_depth:
            voxel_id = subsurface_id
        else:
            voxel_id = STONE

        # Cave Carving using 3D noise
        cave_noise = noise3(wx * 0.09, wy * 0.09, wz * 0.09)
        
        # Taper the cave noise threshold near the surface to create natural, narrow cave mouths
        surface_dist = world_height - wy
        cave_threshold = 0.0
        if surface_dist < 14:
            # 2D mask to restrict cave entrances to rare, specific locations (~1 per few chunks)
            entrance_mask = noise2(wx * 0.02 + 200.0, wz * 0.02 + 200.0)
            
            # Smoothly increase the threshold as we get closer to the surface
            taper_factor = (14 - surface_dist) / 14.0
            
            # If entrance_mask is low, the target threshold is high (closing the cave dome)
            # If entrance_mask is high (>0.5), it stays low (0.3), carving a small hole to the surface!
            target_threshold = 0.3 + max(0.0, 0.5 - entrance_mask) * 4.0
            
            cave_threshold = target_threshold * taper_factor

        # Check if the block falls within the cave noise and is above the bottom crust
        if cave_noise > cave_threshold and wy > noise2(wx * 0.1, wz * 0.1) * 3 + 3:
            # Keep water/beaches intact by blocking cave generation in the top sand/dirt layers
            if not ((is_underwater or is_beach) and surface_dist <= dirt_depth):
                if wy <= WATER_LINE:
                    voxel_id = WATER
                else:
                    voxel_id = 0

    # setting ID
    if voxel_id:
        voxels[get_index(x, y, z)] = voxel_id

    # Place Tree: No trees underwater, no trees on high mountains, no trees on snow, no floating trees!
    if wy == world_height - 1 and voxel_id == surface_id and not is_underwater and not is_beach and wy < STONE_LVL:
        tree_prob = 0.0
        if surface_id == GRASS:
            if moist > 0.4: 
                tree_prob = 0.04   # Dense forest
            elif moist > 0.0: 
                tree_prob = 0.005  # Sparse woods
            else: 
                tree_prob = 0.0001 # Extreme plains (~1 tree every 5 chunks)
            
        if tree_prob > 0:
            place_tree(voxels, x, y, z, surface_id, tree_prob)


@njit(cache=True)
def place_tree(voxels, x, y, z, voxel_id, tree_prob):
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
# """



# Simple Terrain generator, using heights to determine block types, 
# mimicing a simple biome system based on height (snow at high altitudes, 
# sand near water, grass/dirt in between). No biome dithering, no continentalness, 
# no temperature/moisture. Just pure noise-based terrain with caves and trees.
"""
from noise import noise2, noise3
from random import random
from settings import *


@njit(cache=True)
def get_height(x, z):
    # amplitude
    a1 = CENTER_Y
    a2, a4, a8 = a1 * 0.5, a1 * 0.25, a1 * 0.125

    # frequency
    f1 = 0.005
    f2, f4, f8 = f1 * 2, f1 * 4, f1 * 8

    if noise2(0.1 * x, 0.1 * z) < 0:
        a1 /= 1.07

    height = 0
    height += noise2(x * f1, z * f1) * a1 + a1
    height += noise2(x * f2, z * f2) * a2 - a2
    height += noise2(x * f4, z * f4) * a4 + a4
    height += noise2(x * f8, z * f8) * a8 - a8

    height = max(height,  noise2(x * f8, z * f8) + 2)

    return int(height)


@njit(cache=True)
def get_index(x, y, z):
    return x + CHUNK_SIZE * z + CHUNK_AREA * y


@njit(cache=True)
def set_voxel_id(voxels, x, y, z, wx, wy, wz, world_height):
    voxel_id = 0

    if wy < world_height - 1:
        # create caves
        if (noise3(wx * 0.09, wy * 0.09, wz * 0.09) > 0 and
                noise2(wx * 0.1, wz * 0.1) * 3 + 3 < wy < world_height - 10):
            voxel_id = 0

        else:
            voxel_id = STONE
    else:
        rng = int(7 * random())
        ry = wy - rng
        if SNOW_LVL <= ry < world_height:
            voxel_id = SNOW

        elif STONE_LVL <= ry < SNOW_LVL:
            voxel_id = STONE

        elif DIRT_LVL <= ry < STONE_LVL:
            voxel_id = DIRT

        elif GRASS_LVL <= ry < DIRT_LVL:
            voxel_id = GRASS

        else:
            voxel_id = SAND

    # setting ID
    voxels[get_index(x, y, z)] = voxel_id

    # place tree
    if wy < DIRT_LVL:
        place_tree(voxels, x, y, z, voxel_id)


@njit(cache=True)
def place_tree(voxels, x, y, z, voxel_id):
    rnd = random()
    if voxel_id != GRASS or rnd > TREE_PROBABILITY:
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

"""



# A basic terrain generator that creates height-based biomes (snow at high altitudes, sand near water, grass/dirt in between).
# Uses a island mask to create a central landmass surrounded by water, 
"""
from noise import noise2, noise3
from random import random
from settings import *


@njit(cache=True)
def get_height(x, z):
    # island mask
    island = 1 / (pow(0.0025 * math.hypot(x - CENTER_XZ, z - CENTER_XZ), 20) + 0.0001)
    island = min(island, 1)

    # amplitude
    a1 = CENTER_Y
    a2, a4, a8 = a1 * 0.5, a1 * 0.25, a1 * 0.125

    # frequency
    f1 = 0.005
    f2, f4, f8 = f1 * 2, f1 * 4, f1 * 8

    if noise2(0.1 * x, 0.1 * z) < 0:
        a1 /= 1.07

    height = 0
    height += noise2(x * f1, z * f1) * a1 + a1
    height += noise2(x * f2, z * f2) * a2 - a2
    height += noise2(x * f4, z * f4) * a4 + a4
    height += noise2(x * f8, z * f8) * a8 - a8

    height = max(height,  noise2(x * f8, z * f8) + 2)
    height *= island

    return int(height)


@njit(cache=True)
def get_index(x, y, z):
    return x + CHUNK_SIZE * z + CHUNK_AREA * y


@njit(cache=True)
def set_voxel_id(voxels, x, y, z, wx, wy, wz, world_height):
    voxel_id = 0

    if wy < world_height - 1:
        # create caves
        if (noise3(wx * 0.09, wy * 0.09, wz * 0.09) > 0 and
                noise2(wx * 0.1, wz * 0.1) * 3 + 3 < wy < world_height - 10):
            voxel_id = 0

        else:
            voxel_id = STONE
    else:
        rng = int(7 * random())
        ry = wy - rng
        if SNOW_LVL <= ry < world_height:
            voxel_id = SNOW

        elif STONE_LVL <= ry < SNOW_LVL:
            voxel_id = STONE

        elif DIRT_LVL <= ry < STONE_LVL:
            voxel_id = DIRT

        elif GRASS_LVL <= ry < DIRT_LVL:
            voxel_id = GRASS

        else:
            voxel_id = SAND

    # setting ID
    voxels[get_index(x, y, z)] = voxel_id

    # place tree
    if wy < DIRT_LVL:
        place_tree(voxels, x, y, z, voxel_id)


@njit(cache=True)
def place_tree(voxels, x, y, z, voxel_id):
    rnd = random()
    if voxel_id != GRASS or rnd > TREE_PROBABILITY:
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

"""
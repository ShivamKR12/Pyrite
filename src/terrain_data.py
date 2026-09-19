"""
Data-driven terrain shaping and biome placement configuration.

This module contains the static data structures (splines and biome tables)
that define the procedural generation rules for the entire world. By modifying
these values, the shape and distribution of terrain and biomes can be radically
altered without changing the core generation code.
"""

from typing import Any

import numpy as np

# ============================================================================
# Terrain Shaping Splines
# ============================================================================
# Splines are used to map a continuous noise value (like continentalness) to
# one or more output values (like terrain height and 3D noise squashing).
#
# Each spline is a NumPy array of points, where each point is:
#   [input_noise_value, (output_value_1, output_value_2, ...)]
#
# The terrain generator will linearly interpolate between these points.
#
# For terrain shaping, the output values are:
#   - height_offset: The base vertical position of the terrain.
#   - squashing_factor: Controls how much the 3D density noise is flattened.
#     High values create flat terrain (plains), low values create jagged,
#     chaotic terrain (mountains, floating islands).

# ----------------------------------------------------------------------------
# Continentalness Spline
# ----------------------------------------------------------------------------
# Maps large-scale continental noise to the primary landforms.
CONTINENTALNESS_SPLINE: Any = np.array(
    [
        # Noise, (Height, Squashing)
        [-1.0, 20.0, 0.8],  # Deep Oceans: Low height, very flat
        [-0.4, 50.0, 0.6],  # Shallow Oceans / Coastlines
        [-0.3, 70.0, 0.5],  # Plains: Average height, flat
        [0.1, 80.0, 0.2],  # Highlands: Taller, more varied
        [0.5, 150.0, 0.05],  # Mountains: High elevation, very low squashing (jagged)
        [1.0, 180.0, 0.01],  # Extreme Mountain Peaks
    ],
    dtype=np.float32,
)

# ----------------------------------------------------------------------------
# Erosion Spline
# ----------------------------------------------------------------------------
# Maps erosion noise to create smoother or more rugged areas.
EROSION_SPLINE: Any = np.array(
    [
        # Noise, (Height_Multiplier, Squashing_Factor)
        [-1.0, 1.2, 0.1],  # Low Erosion: Jagged, slightly higher peaks
        [0.0, 1.0, 0.4],  # Medium Erosion: Normal terrain
        [1.0, 0.8, 0.9],  # High Erosion: Smoothed out, flatter hills
    ],
    dtype=np.float32,
)

# ============================================================================
# 5D Biome Placement Matrix
# ============================================================================
# Biomes are determined by a point's location within a 5D data space.
# The continuous noise values (-1.0 to 1.0) for each of the five abstract
# fields are "sliced" into discrete integer indices using the range arrays below.
# These indices are then used to perform a direct lookup into the 5D BIOME_TABLE.

# ----------------------------------------------------------------------------
# Biome ID Constants
# ----------------------------------------------------------------------------
# These are abstract IDs. The terrain generator will map them to surface blocks.

# Generic
OCEAN = 0
PLAINS = 1
RIVER = 2

# Mountain Biomes
MEADOW = 10
GROVE = 11
SNOWY_SLOPES = 12
JAGGED_PEAKS = 13
FROZEN_PEAKS = 14
STONY_PEAKS = 15

# Highland Biomes
WINDSWEPT_HILLS = 20
WINDSWEPT_GRAVELLY_HILLS = 21
WINDSWEPT_FOREST = 22

# Woodland Biomes
FOREST = 30
FLOWER_FOREST = 31
DARK_FOREST = 32
BIRCH_FOREST = 33
OLD_GROWTH_BIRCH_FOREST = 34
TAIGA = 35
OLD_GROWTH_PINE_TAIGA = 36
OLD_GROWTH_SPRUCE_TAIGA = 37
SNOWY_TAIGA = 38
JUNGLE = 39
SPARSE_JUNGLE = 40
BAMBOO_JUNGLE = 41

# Flatland Biomes
SUNFLOWER_PLAINS = 50
SNOWY_PLAINS = 51
ICE_SPIKES = 52

# Arid Land Biomes
DESERT = 60
SAVANNA = 61
SAVANNA_PLATEAU = 62
WINDSWEPT_SAVANNA = 63
BADLANDS = 64
ERODED_BADLANDS = 65
WOODED_BADLANDS = 66

# Wetland & Coastal Biomes
SWAMP = 70
FROZEN_RIVER = 71
BEACH = 72
SNOWY_BEACH = 73
STONY_SHORE = 74

# Ocean & Island Biomes
DEEP_OCEAN = 80
WARM_OCEAN = 81
LUKEWARM_OCEAN = 82
DEEP_LUKEWARM_OCEAN = 83
COLD_OCEAN = 84
DEEP_COLD_OCEAN = 85
FROZEN_OCEAN = 86
DEEP_FROZEN_OCEAN = 87
MUSHROOM_FIELDS = 88

# Cave Biomes (Note: Not fully implemented with a 'depth' dimension yet)
LUSH_CAVES = 90
DRIPSTONE_CAVES = 91
DEEP_DARK = 92

# ----------------------------------------------------------------------------
# Noise Slicing Ranges
# ----------------------------------------------------------------------------
# Each array defines the upper bound for a slice. For example, for temperature,
# any value <= -0.5 is index 0, > -0.5 and <= 0.0 is index 1, etc.

# Temperature: 5 bands from Hyper-Cold to Hot
TEMPERATURE_RANGES = np.array([-0.45, -0.15, 0.2, 0.55], dtype=np.float32)
# Temp Indices: 0: Hyper-Cold, 1: Cold, 2: Neutral, 3: Warm, 4: Hot

# Humidity: 5 bands from Arid to Lush
HUMIDITY_RANGES = np.array([-0.45, -0.15, 0.2, 0.55], dtype=np.float32)
# Humid Indices: 0: Arid, 1: Dry, 2: Normal, 3: Moist, 4: Lush

# Continentalness: 7 bands from Deep Ocean to Inland Peaks
CONTINENTALNESS_RANGES = np.array([-0.45, -0.15, -0.05, 0.05, 0.3, 0.6], dtype=np.float32)
# Cont Indices: 0: Deep Ocean, 1: Ocean, 2: Coast, 3: Near Inland, 4: Mid Inland, 5: Far Inland, 6: Mountain

# Erosion: 4 bands from Low to Extreme
EROSION_RANGES = np.array([-0.4, 0.2, 0.7], dtype=np.float32)
# Erosion Indices: 0: Low (Peaks), 1: Moderate (Plateaus), 2: High (Plains), 3: Extreme (Valleys)

# Peaks & Valleys: 4 bands from Valley to Peak
PV_RANGES = np.array([-0.5, 0.0, 0.5], dtype=np.float32)
# PV Indices: 0: Valley, 1: Low Slice, 2: Mid Slice, 3: Peak

# ----------------------------------------------------------------------------
# The 5D Biome Table
# ----------------------------------------------------------------------------
# Dimensions: [Temperature, Humidity, Continentalness, Erosion, Peaks & Valleys]
# The values are the Biome IDs defined above.

BIOME_TABLE_SHAPE = (
    len(TEMPERATURE_RANGES) + 1,
    len(HUMIDITY_RANGES) + 1,
    len(CONTINENTALNESS_RANGES) + 1,
    len(EROSION_RANGES) + 1,
    len(PV_RANGES) + 1,
)

# Initialize with PLAINS as the default biome for all combinations.
BIOME_TABLE: Any = np.full(BIOME_TABLE_SHAPE, PLAINS, dtype=np.uint8)

# --- Define Biome Placement Rules (based on Minecraft 1.18 multi-noise) ---

# Oceans (Low Continentalness)
BIOME_TABLE[4, :, 0, :, :] = DEEP_FROZEN_OCEAN  # Hot Temp, Deep Ocean -> Frozen (Anomaly)
BIOME_TABLE[3, :, 0, :, :] = DEEP_LUKEWARM_OCEAN  # Warm Temp, Deep Ocean
BIOME_TABLE[2, :, 0, :, :] = DEEP_COLD_OCEAN  # Neutral Temp, Deep Ocean
BIOME_TABLE[1, :, 0, :, :] = DEEP_COLD_OCEAN  # Cold Temp, Deep Ocean
BIOME_TABLE[0, :, 0, :, :] = DEEP_FROZEN_OCEAN  # Hyper-Cold Temp, Deep Ocean

BIOME_TABLE[4, :, 1, :, :] = WARM_OCEAN  # Hot Temp, Ocean
BIOME_TABLE[3, :, 1, :, :] = LUKEWARM_OCEAN  # Warm Temp, Ocean
BIOME_TABLE[2, :, 1, :, :] = COLD_OCEAN  # Neutral Temp, Ocean
BIOME_TABLE[1, :, 1, :, :] = COLD_OCEAN  # Cold Temp, Ocean
BIOME_TABLE[0, :, 1, :, :] = FROZEN_OCEAN  # Hyper-Cold Temp, Ocean

# Coasts (Transition Continentalness)
BIOME_TABLE[0, :, 2, :, :] = SNOWY_BEACH  # Hyper-Cold Coast
BIOME_TABLE[1:, :, 2, 0:2, :] = STONY_SHORE  # Non-Cold Coast, Low/Mid Erosion
BIOME_TABLE[1:, :, 2, 2:, :] = BEACH  # Non-Cold Coast, High/Extreme Erosion

# Rivers (Extreme Erosion)
BIOME_TABLE[0:2, :, 3:, 3, :] = FROZEN_RIVER  # Cold/Hyper-Cold, Extreme Erosion
BIOME_TABLE[2:, :, 3:, 3, :] = RIVER  # Neutral/Warm/Hot, Extreme Erosion

# Swamps (Warm, Moist, High Erosion)
BIOME_TABLE[3, 3, 3:, 2, :] = SWAMP

# Mountains (Far Inland, Low Erosion)
BIOME_TABLE[0, :, 6, 0, :] = FROZEN_PEAKS  # Hyper-Cold
BIOME_TABLE[1, :, 6, 0, :] = JAGGED_PEAKS  # Cold
BIOME_TABLE[2:, 0:3, 6, 0, :] = STONY_PEAKS  # Neutral/Warm/Hot, Not Moist/Lush
BIOME_TABLE[2:, 3:, 6, 0, :] = JAGGED_PEAKS  # Neutral/Warm/Hot, Moist/Lush

# Plateaus & Slopes (Far Inland, Moderate Erosion)
BIOME_TABLE[0, :, 6, 1, :] = SNOWY_SLOPES  # Hyper-Cold
BIOME_TABLE[1, :, 6, 1, :] = GROVE  # Cold
BIOME_TABLE[2, :, 6, 1, :] = MEADOW  # Neutral
BIOME_TABLE[3:, 0, 6, 1, :] = SAVANNA_PLATEAU  # Warm/Hot, Arid

# Standard Land (Inland, High Erosion)
BIOME_TABLE[0, :, 3:, 2, :] = SNOWY_PLAINS  # Hyper-Cold
BIOME_TABLE[1, :, 3:, 2, :] = SNOWY_TAIGA  # Cold
BIOME_TABLE[2, 2, 3:, 2, :] = FOREST  # Neutral, Normal Humidity
BIOME_TABLE[2, 3, 3:, 2, :] = DARK_FOREST  # Neutral, Moist Humidity
BIOME_TABLE[3, 0, 3:, 2, :] = SAVANNA  # Warm, Arid
BIOME_TABLE[4, 0, 3:, 2, :] = DESERT  # Hot, Arid
BIOME_TABLE[4, 3:, 3:, 2, :] = JUNGLE  # Hot, Moist/Lush

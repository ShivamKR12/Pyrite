.. _terrain:

Terrain Systems and Procedural Generation Breakdown
===================================================

This document provides detailed explanations of Pyrite's procedural terrain generation, including deterministic seeding, biome selection, height mapping (FBm), cave carving, and structural tree placement. All core terrain logic is located in ``src/terrain_gen.py`` and ``src/noise.py``.

Architecture Overview
---------------------

Pyrite utilizes a heavily parallelized, lock-free approach to generate infinite terrain:

.. code-block:: text

    1. Noise Foundation    → Deterministic OpenSimplex noise and Numba JIT.
    2. Biome Selection     → 2D Temperature and Moisture evaluation.
    3. Height Generation   → Fractional Brownian Motion (FBm) + Continentalness.
    4. Cave Carving        → 3D Volumetric noise with entrance tapering.
    5. Tree Placement      → Probabilistic structural generation.

Noise Foundation (Deterministic Generation)
-------------------------------------------

``src/noise.py`` - Noise & Seeding Engine

Purpose: Manage global permutation arrays, synchronize RNG, and ensure 100% deterministic world generation.

.. code-block:: python

    def set_seed(new_seed: int) -> None:

* **Seed Conversion:** This function initializes the deterministic sequence. The engine hashes string inputs (like "PyriteIsCool") into a 32-bit integer seed to feed into this function.

.. code-block:: python

    perm, perm_grad_index3 = _init(seed=new_seed)

* **OpenSimplex Initialization:** We generate the fundamental noise permutation arrays. Numba will hardcode pointers to these specific arrays in memory to bypass Python object overhead.

.. code-block:: python

    _seed_numba(new_seed)
    np.random.seed(new_seed)
    random.seed(new_seed)

* **RNG Synchronization:** Because performance-critical loops are compiled with Numba, we must explicitly seed Numba's internal RNG (``_seed_numba``) as well as standard Python random modules. This ensures functions like random chance for tree placement are identical on every launch.

``src/terrain_gen.py`` - Numba JIT Compilation

Purpose: Execute complex noise math at near-C++ speeds using LLVM.

.. code-block:: python

    @njit(cache=True, fastmath=True, nogil=True)

* **Numba JIT Compilation:** Functions decorated with ``@njit`` bypass the Python Global Interpreter Lock (``nogil=True``) allowing true multithreading, use relaxed floating-point math (``fastmath=True``) for speed, and cache the compiled LLVM binary (``cache=True``) to speed up subsequent engine launches.

Biome Selection Algorithm
-------------------------

``src/terrain_gen.py`` - Biome Evaluation

Purpose: Determine temperature and moisture to map out expansive biomes like deserts, snow, and forests.

.. code-block:: python

    temp = noise2(x * 0.002, z * 0.002, perm_array)

* **Temperature Calculation:** Temperature is evaluated using 2D Simplex noise. The ``0.002`` scale is extremely low, ensuring biomes are massive and sprawling across thousands of blocks.

.. code-block:: python

    moist = noise2(x * 0.002 + 100.0, z * 0.002 + 100.0, perm_array)

* **Moisture Calculation:** Moisture is evaluated using the exact same massive scale but is offset by ``100.0``. This ensures its noise map doesn't identically overlap with the temperature map, creating diverse intersections (hot/dry, hot/wet, cold/dry, etc.).

.. code-block:: python

    dither = noise2(wx * 0.2, wz * 0.2, perm_array) * 0.05 + noise2(wx * 0.8, wz * 0.8, perm_array) * 0.03
    temp += dither
    moist += dither

* **Biome Dithering:** To make biome transitions organic rather than perfectly straight, mathematical lines, we sample two much higher frequencies (``0.2`` and ``0.8``). By scaling them down and adding them to the base temp/moist, we subtly scramble the exact borders, causing blocks from adjacent biomes to mix naturally.

.. code-block:: python

    is_desert = temp > 0.3 and moist < -0.2
    is_snow = temp < -0.2

* **Biome Palettes:** Using the dithered values, we define strict cutoff thresholds for deserts (hot and dry) and snow (cold). If neither matches, the terrain defaults to standard grass/dirt.

Height Generation Algorithm
---------------------------

``src/terrain_gen.py`` - Height Evaluation

Purpose: Utilize Fractional Brownian Motion (FBm) combined with continental modifiers to sculpt oceans, plains, and mountains.

.. code-block:: python

    cont = noise2(x * 0.003 + 100.0, z * 0.003 + 100.0, perm_array)

* **Continentalness:** We sample a slow-changing base map (offset to prevent overlap with biome noise) that defines the overarching landmass type independently of the climate.

.. code-block:: python

    base_h = noise2(x * f1, z * f1, perm_array) * a1 + a1

* **FBm Base Octave:** The base octave uses a very low frequency (``f1 = 0.005``) and high amplitude (``a1 = CENTER_Y``) to create sweeping, gentle hills and valleys.

.. code-block:: python

    detail_1 = noise2(x * f2, z * f2, perm_array) * a2 - a2
    detail_2 = noise2(x * f4, z * f4, perm_array) * a4 + a4
    detail_3 = noise2(x * f8, z * f8, perm_array) * a8 - a8
    height = base_h + detail_1 + detail_2 + detail_3

* **FBm Detail Octaves:** Each subsequent octave doubles the frequency (``f2, f4, f8``) and halves the amplitude (``a2, a4, a8``). Summing these together creates increasingly fine, localized bumps across the terrain.

.. code-block:: python

    if cont < -0.2:
    w = min((-0.2 - cont) * 5.0, 1.0)
    target_h = WATER_LINE - 2 + detail_2 * 0.3 + detail_3 * 0.3
    height = height * (1.0 - w) + target_h * w

* **Terrain Shaping:** If continentalness is very low, we treat it as Deep Plains or Oceans. We calculate an interpolation weight ``w`` and heavily flatten the ``target_h`` just below the water line, linearly interpolating the raw FBm height towards it.

Cave Carving Algorithm (3D)
---------------------------

``src/terrain_gen.py`` - Volumetric Cave Carving

Purpose: Hollow out complex underground cave systems using 3D noise while preventing unnatural surface craters.

.. code-block:: python

    cave_noise = noise3(wx * 0.09, wy * 0.09, wz * 0.09, perm_array, perm_grad_array)

* **Volumetric Carving:** For every solid block beneath the crust, we evaluate 3D Simplex noise using the exact ``wx, wy, wz`` world coordinates.

.. code-block:: python

    entrance_mask = noise2(wx * 0.02 + 200.0, wz * 0.02 + 200.0, perm_array)

* **Entrance Mask:** Before looping through the Y-axis, we calculate a 2D map once per column to determine how "open" or "closed" the surface should be, preventing all caves from breaching the top.

.. code-block:: python

    if surface_dist < 14:
    taper_factor = (14 - surface_dist) / 14.0
    target_threshold = 0.3 + max(0.0, 0.5 - entrance_mask) * 4.0

* **Dynamic Tapering:** If we are within 14 blocks of the surface crust, the tapering mechanism kicks in. We calculate a linear factor that shifts the ``target_threshold`` higher, making it harder for noise to exceed it.

.. code-block:: python

    cave_threshold = target_threshold * taper_factor
    if cave_noise > cave_threshold:
        voxel_id = 0

* **Block Removal:** We scale the threshold shift by the taper factor. The closer you get to the grass, the harder it becomes for a cave to break through. If the noise still beats the modified threshold, the block is forced to ``0`` (AIR).

Tree Placement and Structure
-----------------------------

``src/terrain_gen.py`` - Flora Generation

Purpose: Probabilistically spawn and construct multi-block tree structures within chunk memory bounds.

.. code-block:: python

    if wy == world_height - 1 and voxel_id == surface_id and not is_underwater and not is_beach and wy < STONE_LVL:

* **Spawning Constraints:** Trees are strictly constrained. They can only spawn on the absolute top surface block, cannot spawn in water or on beaches, and cannot spawn high up in the mountains (above ``STONE_LVL``).

.. code-block:: python

    if surface_id == GRASS:
        if moist > 0.4:
            tree_prob = 0.04
        elif moist > 0.0:
            tree_prob = 0.005

* **Moisture-based Density:** Tree density is tied directly to the biome's moisture rating. Dense forests have a 4% spawn rate per column, while sparse woods drop to 0.5%.

.. code-block:: python

    rnd = random()
    if rnd > tree_prob:
        return None

* **Probabilistic Check:** The Numba-compiled ``random()`` uses our globally synchronized deterministic seed to decide if this specific column gets a tree.

.. code-block:: python

    if x - TREE_H_WIDTH < 0 or x + TREE_H_WIDTH >= CHUNK_SIZE:
        return None

* **Chunk Boundary Safety:** To prevent the engine from crashing by writing outside of the 1D chunk array, we strictly verify that the tree's leafy crown will not bleed over the X or Z chunk borders.

.. code-block:: python

    voxels[get_index(x, y, z)] = DIRT
    for iy in range(1, TREE_HEIGHT - 2):
        voxels[get_index(x, y + iy, z)] = WOOD

* **Structural Building:** The block directly under the trunk is forced to be dirt. The trunk is grown straight up using the fast 1D array coordinate flattener ``get_index``.

.. code-block:: python

    if (ix + iz) % 4:
        voxels[get_index(x + ix + k, y + iy, z + iz + k)] = LEAVES

* **Sparse Leaf Crown:** The spherical crown is generated layer by layer. We utilize modulo math (``% 4``) to skip specific leaf blocks, creating a sparse, organic checkerboard pattern that allows ambient light to pass through.

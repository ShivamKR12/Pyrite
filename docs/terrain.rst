Procedural Terrain Generation
=============================

Pyrite generates infinite, deterministic worlds using highly parallelized OpenSimplex noise. By utilizing MD5 string-hashing, custom string seeds (e.g., "PyriteIsCool") are converted into numerical integer seeds. The Numba compiler locks this seed via `numpy.random.seed()`, ensuring the exact same terrain topology is generated every time.

Biome & Topography System
-------------------------
The terrain generation heavily relies on independent, overlapping noise frequencies:

* **Continentalness:** Dictates the physical landform (evaluated across 4 layered octaves: `f1, f2, f4, f8`). Very low values carve deep oceans, mid values create sweeping plains, and high values linearly interpolate the terrain upward into extreme mountains or plateaus.
* **Temperature & Moisture:** Evaluated via separate 2D noise maps to dictate the biome's block palette (e.g., Snow vs. Desert Sand vs. Grass).

**Biome Dithering:**
To prevent unnatural, blocky straight lines at biome borders, a subtle, high-frequency noise "dithering" offset is mathematically added to the temperature and moisture values. This creates a natural scatter effect, allowing blocks from adjacent biomes to organically mix at the edges.

Cave Carving
------------
Underground systems are carved dynamically using volumetric 3D noise (`noise3`). 

First, the engine determines a deterministic `crust` thickness. Below this safe top layer, 3D noise is evaluated for every single block coordinate. If the 3D noise exceeds a specific density threshold, the block is overridden and forced to become `AIR`.

**Natural Entrances:**
To create natural cave entrances rather than massive sinkholes, the cave threshold is dynamically tapered near the surface using a 2D `entrance_mask` noise map. This forces the 3D carving logic to narrow out and tighten before breaking through the grass layer.

Tree & Flora Generation
-----------------------
Trees are placed procedurally during column generation based on the target Biome's moisture rating. 
* High moisture yields a `4%` probability per column (Dense Forests).
* Low moisture yields a `0.01%` probability (Sparse Plains).

The tree structure is pre-defined using local relative coordinates. The engine enforces several environment constraints before spawning a tree:

1. Trees cannot spawn underwater.
2. Trees cannot spawn on Snow or Sand.
3. Trees cannot spawn at extreme mountain altitudes (`wy > STONE_LVL`).
4. A tree's bounding box cannot exceed the chunk's boundaries (preventing neighbor-chunk bleeding crashes).

Noise Foundation (Deterministic Generation)
--------------------------------------------

**Seed Conversion:**

**Seed Conversion (Reference Implementation):**

.. code-block:: python

    # Note: Actual seed handling in engine uses set_seed() from src/noise.py
    # This is a reference implementation showing the concept:
    import hashlib
    
    def string_to_seed(seed_string):
        # Convert string seed to integer
        hash_obj = hashlib.md5(seed_string.encode())
        seed_int = int(hash_obj.hexdigest(), 16) % (2**31)
        return seed_int
    
    # Example:
    seed = string_to_seed("PyriteIsCool")  # Result: deterministic 32-bit integer

**OpenSimplex 2D Noise (Biomes):**


**OpenSimplex 2D Noise (Biomes - Pseudo-code):**

.. note:: Actual function is ``get_biome(x, z, perm_array)`` in ``src/terrain_gen.py``

.. code-block:: python

    # Reference implementation of biome noise calculation
    from opensimplex import OpenSimplex
    
    def get_biome_noise_ref(x, z, scale=0.05):
        # Initialize noise generator with seed (actual code: perm_array lookup)
        noise_gen = OpenSimplex(seed)
        
        # Evaluate noise at point (returns temperature/moisture blend)
        value = noise_gen.noise2(x * scale, z * scale)  # Returns -1.0 to 1.0
        return value

**OpenSimplex 3D Noise (Caves - Pseudo-code):**

.. note:: Actual cave generation is embedded in ``Chunk.generate_terrain()`` in ``src/world_objects/chunk.py``

.. code-block:: python

    # Reference implementation of cave carving noise (actual: inlined in chunk generation)
    def get_cave_noise_ref(x, y, z, scale=0.09):
        noise_gen = OpenSimplex(seed)
        value = noise_gen.noise3(x * scale, y * scale, z * scale)
        return value  # Returns -1.0 to 1.0; carve if > cave_threshold

Height Generation Algorithm
---------------------------

**Multi-Octave Frequency Blending (FBm - Fractional Brownian Motion):**

Height at column (x, z) is calculated by summing noise at multiple frequencies. Each octave has half the amplitude and double the frequency of the previous.

.. code-block:: python

.. note:: Actual function: ``get_height(x, z, perm_array)`` in ``src/terrain_gen.py``

.. code-block:: python

    # Terrain height generation at a column (x, z in world coordinates)
    def get_height(x, z, perm_array):
        # Column generation (for all 48 Y values)
        
        # Step 1: Evaluate continentalness (overall landform)
        continentalness = 0
        amplitude = 1.0
        frequency = 0.005  # Scale for first octave
        
        for octave in [1, 2, 4, 8]:  # 4 octaves
            freq = frequency * octave
            noise_value = opensimplex_noise(x * freq, z * freq)
            continentalness += noise_value * amplitude
            amplitude *= 0.5  # Halve amplitude each octave
        
        # Normalize continentalness to -1.0 to 1.0
        continentalness = clamp(continentalness / 1.875, -1.0, 1.0)  # 1.875 = sum of amplitudes
        
        # Step 2: Evaluate jaggedness (mountain sharpness)
        jaggedness = opensimplex_noise(x * 0.04, z * 0.04)  # Higher frequency
        
        # Step 3: Determine base height from continentalness
        if continentalness < -0.2:
            # Deep ocean
            base_height = 5.6 + continentalness * 3  # Range: ~2 to 5.6 blocks
        elif -0.2 <= continentalness <= 0.1:
            # Beaches, plains
            base_height = 5.6 + continentalness * 8  # Range: 5.6 to ~6 blocks (mostly flat)
        elif 0.1 < continentalness <= 0.3:
            # Plateaus
            base_height = 6.0 + continentalness * 30  # Range: 6 to ~15 blocks, cliffier
            jaggedness *= 2  # Emphasize jaggedness on plateaus
        else:
            # Mountains
            base_height = 15.0 + continentalness * 50  # Range: 15 to 35+ blocks
            jaggedness *= 3  # Very jagged
        
        # Apply jaggedness
        height = base_height + jaggedness * 4
        
        # Clamp to world bounds (0 to 256)
        height = clamp(height, 0, 256)
        
        return int(height)

**Height Constants:**

.. code-block:: python

    STONE_LVL = 8          # Below this Y, all blocks are stone (bedrock layer)
    WATER_LVL = 5.6        # Sea level
    SNOW_LVL = 25          # Above this, snow biomes appear
    GRASS_LVL = 15         # Below this, grass; above, snow/rock

Biome Selection Algorithm
-------------------------

**Two-Stage Process:**

1. Evaluate temperature and moisture maps (independent 2D noise)
2. Use lookup table or conditions to select block palette

.. code-block:: python

.. note:: Actual function: ``get_biome(x, z, perm_array)`` in ``src/terrain_gen.py``

.. code-block:: python

    # Determine biome type based on temperature and moisture at column
    def get_biome(x, z, perm_array):
        # Sample temperature and moisture
        temperature = opensimplex_noise(x * 0.01, z * 0.01)  # -1.0 to 1.0
        moisture = opensimplex_noise(x * 0.015, z * 0.015)
        
        # Apply dithering (high-frequency noise for variety)
        dither = opensimplex_noise(x * 0.1, z * 0.1) * 0.05  # ±0.05 offset
        temperature += dither
        moisture += dither
        
        # Biome lookup table
        if temperature > 0.3 and moisture < -0.2:
            return 'DESERT'
        elif temperature < -0.2:
            return 'SNOW'
        elif moisture > 0.2:
            return 'FOREST'
        elif moisture < -0.1:
            return 'PLAINS'
        else:
            return 'GRASSLAND'

**Biome Block Palettes:**

.. code-block:: text

    DESERT:
        Surface:    SAND
        Under:      SAND (3 blocks)
        Base:       STONE
    
    SNOW:
        Surface:    SNOW
        Under:      DIRT (2 blocks)
        Base:       STONE
    
    FOREST/GRASSLAND:
        Surface:    GRASS
        Under:      DIRT (2-4 blocks)
        Base:       STONE

Cave Carving Algorithm (3D)
---------------------------

**Volumetric Carving:**

.. code-block:: python

    def generate_and_carve_chunk(chunk_voxels, chunk_x, chunk_y, chunk_z):
        # First, generate terrain normally (above stone level)
        
        # Then, carve caves below a certain Y threshold
        CAVE_THRESHOLD = 40  # Only cave below this
        CAVE_SPAWN_Y = 15
        
        for local_x in range(48):
            for local_y in range(48):
                for local_z in range(48):
                    world_x = chunk_x * 48 + local_x
                    world_y = chunk_y * 48 + local_y
                    world_z = chunk_z * 48 + local_z
                    
                    # Only carve solidblocks below threshold
                    if world_y < CAVE_SPAWN_Y or world_y > CAVE_THRESHOLD:
                        continue
                    
                    # Skip air/water
                    voxel_id = chunk_voxels[local_x + local_z * 48 + local_y * 48**2]
                    if is_transparent(voxel_id):
                        continue
                    
                    # Evaluate 3D cave noise
                    cave_noise = opensimplex_noise_3d(world_x * 0.09, world_y * 0.09, world_z * 0.09)
                    
                    # Apply entrance tapering (near surface, make caves narrower)
                    surface_distance = world_y - CAVE_SPAWN_Y
                    taper_factor = 1.0 - (surface_distance / 14.0) ** 2  # Tapers over 14 blocks
                    
                    entrance_mask = opensimplex_noise(world_x * 0.02, world_z * 0.02)
                    cave_threshold = 0.3 + taper_factor * 0.2
                    
                    # Carve if noise exceeds threshold
                    if cave_noise > cave_threshold and entrance_mask < 0.5:
                        chunk_voxels[...] = AIR  # Carve out voxel

Tree Placement and Structure
-----------------------------

**Probabilistic Placement:**

.. code-block:: python

    def try_place_tree_in_column(x, z, biome, height):
        # Determine tree probability from biome
        if biome == 'FOREST':
            tree_probability = 0.04  # 4% per column
        elif biome == 'GRASSLAND':
            tree_probability = 0.005  # 0.5% per column
        elif biome == 'PLAINS':
            tree_probability = 0.0001  # 0.01% per column
        else:
            return None  # No trees in desert/snow
        
        # Seeded random check
        rng_value = pseudo_random(x, z, seed)  # 0.0 to 1.0
        
        if rng_value > tree_probability:
            return None  # Don't place tree
        
        # Check placement constraints
        
        # 1. Not underwater
        if height < WATER_LVL:
            return None
        
        # 2. Not on sand or snow
        if biome in ['DESERT', 'SNOW']:
            return None
        
        # 3. Not at extreme altitudes
        if height > SNOW_LVL:
            return None
        
        # 4. Bounding box doesn't exceed chunk
        tree_height = 8
        tree_crown_radius = 4
        
        local_x = x % 48
        local_z = z % 48
        
        if local_x - tree_crown_radius < 0 or local_x + tree_crown_radius >= 48:
            return None
        if local_z - tree_crown_radius < 0 or local_z + tree_crown_radius >= 48:
            return None
        
        # All checks pass - place tree
        return place_tree_structure(x, height, z)

**Tree Structure (Predefined):**

.. code-block:: python

    def place_tree_structure(x, base_y, z):
        # Tree structure (relative coordinates from base)
        trunk_height = 8
        crown_start_y = 5
        
        # Trunk (straight column of wood)
        for dy in range(trunk_height):
            world_x, world_y, world_z = x, base_y + dy, z
            set_voxel(world_x, world_y, world_z, WOOD)
        
        # Crown (spherical leaves)
        crown_y = base_y + crown_start_y
        crown_radius = 4
        
        for dx in range(-crown_radius, crown_radius + 1):
            for dy in range(-crown_radius, crown_radius + 1):
                for dz in range(-crown_radius, crown_radius + 1):
                    distance = sqrt(dx**2 + dy**2 + dz**2)
                    if distance <= crown_radius:
                        # Checker pattern (sparse leaves for light penetration)
                        if (abs(dx) + abs(dz)) % 4 != 0:
                            world_x = x + dx
                            world_y = crown_y + dy
                            world_z = z + dz
                            set_voxel(world_x, world_y, world_z, LEAVES)

Ore Generation
--------------

Pyrite does not currently implement dedicated ore spawning. Terrain generation focuses on biome placement, caves, trees, and surface details rather than mineral deposits.

Column Generation Sequence
--------------------------

**Per-Column Processing (called for each X,Z coordinate):**

.. code-block:: python

    def generate_column(x, z, perm_array):
        height = get_height(x, z, perm_array)
        biome = get_biome(x, z, perm_array)
        
        column_voxels = []  # 0 to 256 (Y=0 is bedrock)
        
        # 1. Fill with stone below height
        for y in range(STONE_LVL, int(height)):
            if y <= STONE_LVL + 1:
                column_voxels.append(BEDROCK)
            else:
                column_voxels.append(STONE)
        
        # 2. Add surface layer
        surface = get_biome_surface_block(biome, int(height))
        if int(height) < 256:
            column_voxels[int(height)] = surface
        
        # 3. Add dirt layer (2-4 blocks)
        dirt_depth = 3
        for i in range(dirt_depth):
            if int(height) - i - 1 >= STONE_LVL:
                column_voxels[int(height) - i - 1] = DIRT
        
        # 4. Fill above height with air (or water if below sea level)
        for y in range(int(height) + 1, 256):
            if y < WATER_LVL:
                column_voxels.append(WATER)
            else:
                column_voxels.append(AIR)
        
        # 5. Return for insertion into chunk
        return column_voxels

Replication Checklist
---------------------

To reimplement terrain generation:

1. ✓ Seed conversion (string → int via MD5 or similar)
2. ✓ OpenSimplex initialization with deterministic seed
3. ✓ Multi-octave FBm height calculation
4. ✓ Biome lookup (temperature + moisture → palette)
5. ✓ 3D cave carving with entrance tapering
6. ✓ 2D tree placement with probabilistic seeding
7. ✓ Tree structure generation (trunk + crown)
8. ✓ Column generation in correct order
9. ✓ Integration with chunk meshing pipeline


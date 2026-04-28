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

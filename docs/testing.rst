.. _testing:

Testing and Profiling
=====================

This chapter covers unit testing, integration testing, and performance profiling strategies for Pyrite.

Testing Framework Setup
-----------------------

Pyrite uses **pytest** for automated testing. Install with::

    pip install pytest pytest-cov pytest-xdist

Create a test file structure in ``tests/`` directory::

    tests/
        test_engine.py
        test_terrain.py
        test_physicsv
        test_mesh.py
        test_lighting.py

Run tests with::

    pytest tests/ -v                    # Verbose output
    pytest tests/ -v --cov=src          # With coverage report
    pytest tests/ -v -n 4               # Parallel (4 workers)

Core Terrain Tests
-------------------

**Test: Terrain Generation Determinism**

Verify that same seed produces identical terrain::

    def test_terrain_determinism():
        """Same seed should produce same terrain"""
        seed = 42
        
        # Generate column at (100, 100) twice
        gen1 = TerrainGenerator(seed)
        col1 = [gen1.get_height_at_column(100, 100) for _ in range(1)]
        
        gen2 = TerrainGenerator(seed)
        col2 = [gen2.get_height_at_column(100, 100) for _ in range(1)]
        
        assert col1 == col2, "Same seed should produce identical terrain"

**Test: Biome Distribution**

Check that biomes are reasonably distributed::

    def test_biome_distribution():
        """Verify biome sampling covers all types"""
        gen = TerrainGenerator(12345)
        biomes = set()
        
        for x in range(0, 500, 50):
            for z in range(0, 500, 50):
                biome = gen.get_biome_at_column(x, z)
                biomes.add(biome)
        
        expected_biomes = {'DESERT', 'SNOW', 'FOREST', 'GRASSLAND', 'PLAINS'}
        assert biomes == expected_biomes, f"Expected {expected_biomes}, got {biomes}"

**Test: Height Range Validation**

Ensure heights stay within valid bounds::

    def test_height_bounds():
        """All heights should be 0-256"""
        gen = TerrainGenerator(999)
        
        for x in range(0, 1000, 100):
            for z in range(0, 1000, 100):
                height = gen.get_height_at_column(x, z)
                assert 0 <= height <= 256, f"Height {height} out of bounds"

Mesh Generation Tests
---------------------

**Test: Greedy Meshing Output**

Verify mesh generation produces valid vertex data::

    def test_greedy_mesh_output():
        """Greedy mesher should produce valid quads"""
        from src.meshes.chunk_mesh_builder import build_chunk_mesh
        
        # Create simple test chunk: 48x48x48 stone
        voxels = np.ones(48*48*48, dtype=np.uint8) * 1  # Stone
        lightmap = np.ones(48*48*48, dtype=np.uint8) * 0xFF  # Max light
        
        # Build mesh
        vertices, lights = build_chunk_mesh(
            voxels, lightmap, (0, 0, 0),
            {}, {}
        )
        
        assert vertices is not None, "Mesh build failed"
        assert len(vertices) % 4 == 0, "Vertices not multiple of 4 (quads)"
        assert len(lights) == len(vertices) // 4, "Light count mismatch"

**Test: AO Calculation**

Verify ambient occlusion darkening::

    def test_ao_calculation():
        """AO should darken exposed corners"""
        # Create 1x1x1 cube surrounded by stone
        voxels = np.zeros(48*48*48, dtype=np.uint8)
        voxels[(24)*48*48 + (24)*48 + (24)] = 1  # Center stone block
        
        # Fill surrounding
        for x in range(23, 26):
            for y in range(23, 26):
                for z in range(23, 26):
                    if (x, y, z) != (24, 24, 24):
                        voxels[y*48*48 + z*48 + x] = 1
        
        lightmap = np.full(48*48*48, 0xFF, dtype=np.uint8)
        
        vertices, lights = build_chunk_mesh(
            voxels, lightmap, (0, 0, 0), {}, {}
        )
        
        # Center cube should have AO applied
        assert len(vertices) > 0, "No vertices generated"

Collision Detection Tests
--------------------------

**Test: AABB Intersection**

Verify collision box detection::

    def test_aabb_intersection():
        """AABB should detect overlaps correctly"""
        box1 = (0.0, 0.0, 0.0, 0.6, 1.8, 0.6)  # Player at origin
        box2 = (0.5, 0.5, 0.5, 1.5, 1.5, 1.5)    # Overlapping cube
        
        assert boxes_intersect(box1, box2), "Should detect overlap"
        
        box3 = (2.0, 2.0, 2.0, 3.0, 3.0, 3.0)    # Separate cube
        assert not boxes_intersect(box1, box3), "Should not detect non-overlap"

**Test: Axis-Separated Resolution**

Check collision response::

    def test_collision_resolution():
        """Player should slide along walls"""
        from src.player import Player
        
        player = Player()
        player.feet_pos = glm.vec3(1.0, 0.0, 1.0)
        player.velocity = glm.vec3(2.0, 0.0, 0.0)  # Moving right
        
        # Build mock world with wall at x=2
        world = MockWorld()
        world.add_solid_voxel(2, 0, 1)
        
        # Move and collide
        player.move_and_collide(0.016, world)
        
        # Should collide with wall, stop before it
        assert player.feet_pos.x < 1.7, "Should collide with wall"
        assert abs(player.feet_pos.z - 1.0) < 0.01, "Should maintain Z position"

Lighting Tests
--------------

**Test: BFS Light Propagation**

Verify light spreads correctly::

    def test_light_propagation():
        """Light should decrease with distance"""
        from src.lighting import LightQueue, propagate_light_queue
        
        # Create chunk with torch at center
        lightmap = np.zeros(48*48*48, dtype=np.uint8)
        center = (24, 24, 24)
        lightmap[center[1]*48*48 + center[2]*48 + center[0]] = 0xEE  # Level 14 blocklight
        
        # Propagate
        queue = LightQueue()
        queue.enqueue(center[0], center[1], center[2], 14)
        
        # (Requires access to world voxel data)
        # propagate_light_queue(queue, world_voxels, lightmap)
        
        # Verify distance-1 neighbors are level 13
        neighbors = [
            (25, 24, 24), (23, 24, 24),
            (24, 25, 24), (24, 23, 24),
            (24, 24, 25), (24, 24, 23)
        ]
        for nx, ny, nz in neighbors:
            light = lightmap[ny*48*48 + nz*48 + nx]
            block_light = light & 0x0F
            assert block_light == 13, f"Neighbor light should be 13, got {block_light}"

Inventory Tests
---------------

**Test: Item Stacking**

Verify inventory stacking logic::

    def test_inventory_stacking():
        """Identical items should stack to 64"""
        inv = Inventory()
        
        # Add 30 dirt
        inv.add_item(2, 30)
        assert inv.get_item_count(2) == 30
        
        # Add 40 more dirt
        inv.add_item(2, 40)
        assert inv.get_item_count(2) == 64, "Should cap at max stack"

**Test: Crafting Recipe**

Verify crafting produces correct output::

    def test_crafting_recipe():
        """Wood should craft into 4 planks"""
        inv = Inventory()
        
        # Add wood
        inv.add_item(5, 1)  # Wood block
        
        # Craft
        result = inv.craft_wood_to_planks()
        
        assert result == True, "Craft should succeed"
        assert inv.get_item_count(5) == 0, "Wood should be consumed"
        assert inv.get_item_count(8) == 4, "Should produce 4 planks"

Performance Profiling
---------------------

**CPU Profiling with cProfile**

Identify bottlenecks in mesh building::

    import cProfile
    import pstats
    
    def profile_mesh_building():
        profiler = cProfile.Profile()
        profiler.enable()
        
        # Run 10 mesh builds
        for i in range(10):
            chunk = Chunk(0, 0, 0)
            chunk.rebuild_mesh()
        
        profiler.disable()
        stats = pstats.Stats(profiler)
        stats.sort_stats('cumulative')
        stats.print_stats(20)  # Top 20 functions

Expected Output::

    ncalls  tottime  cumtime  filename:lineno(function)
        10    0.005   0.124   chunk_mesh_builder.py:15(build_chunk_mesh)
        10    0.050   0.090   chunk_mesh_builder.py:45(greedy_meshing_pass)
        10    0.020   0.040   chunk_mesh_builder.py:122(calculate_ao)

**GPU Memory Profiling**

Monitor texture/VBO usage (GPU)::

    def check_gpu_memory():
        """Print GPU memory stats"""
        ctx = moderngl.create_standalone_context()
        
        # Get GPU capabilities
        print(f"Max 2D texture size: {ctx.max_texture_size}")
        print(f"Max 3D texture size: {ctx.max_3d_texture_size}")
        
        # Monitor during runtime
        def log_vbo_pool_stats(pool):
            allocated = len(pool.allocated)
            available = len(pool.available)
            print(f"VBO Pool: {allocated} allocated, {available} available")

**Terrain Generation Profiling**

Benchmark terrain generation speed::

    def benchmark_terrain():
        """Measure chunk generation speed"""
        import timeit
        
        gen = TerrainGenerator(42)
        
        def generate_chunk():
            voxels = np.zeros(48*48*48, dtype=np.uint8)
            for cx in range(48):
                for cz in range(48):
                    col = gen.generate_column(cx, cz)
                    for cy in range(48):
                        voxels[cy*48*48 + cz*48 + cx] = col[cy]
        
        time_taken = timeit.timeit(generate_chunk, number=100)
        print(f"100 chunks: {time_taken:.2f}s ({time_taken/100*1000:.1f}ms per chunk)")

Expected: ~2-5ms per chunk on modern CPU with Numba JIT.

**Lighting Propagation Profiling**

Measure BFS light update speed::

    def benchmark_lighting():
        """Measure light propagation"""
        config = LightingConfig(queue_size=200000)
        queue = LightQueue(config)
        
        # Simulate adding 1000 voxels to propagate
        for i in range(1000):
            queue.enqueue(i % 48, i // 48, 0, 14)
        
        start = time.time()
        propagate_light_queue(queue, world_voxels, world_lightmaps)
        elapsed = time.time() - start
        
        print(f"Light propagation: {elapsed*1000:.1f}ms for 1000 nodes")

Expected: <50ms for typical chunk update (with Numba JIT).

Continuous Integration
----------------------

**GitHub Actions Workflow Example**

Create ``.github/workflows/test.yml``::

    name: Tests
    
    on: [push, pull_request]
    
    jobs:
      test:
        runs-on: ubuntu-latest
        strategy:
          matrix:
            python-version: ['3.9', '3.10', '3.11']
        
        steps:
        - uses: actions/checkout@v3
        - name: Set up Python
          uses: actions/setup-python@v4
          with:
            python-version: ${{ matrix.python-version }}
        
        - name: Install dependencies
          run: |
            python -m pip install -r requirements-dev.txt
        
        - name: Run tests
          run: |
            pytest tests/ -v --cov=src --cov-report=xml
        
        - name: Upload coverage
          uses: codecov/codecov-action@v3

Test Coverage Goals
-------------------

- **Core terrain generation**: >90% (highest priority)
- **Mesh building**: >85% (complex algorithm)
- **Physics/collision**: >80% (safety-critical)
- **Lighting**: >75% (complex BFS)
- **UI/Inventory**: >60% (lower priority)

Replication Checklist
---------------------

✓ Set up pytest with coverage
✓ Create test files for terrain, mesh, physics, lighting
✓ Run >10 test cases (determinism, bounds, algorithms)
✓ Profile hotspots (mesh building, terrain gen, lighting)
✓ Set up GitHub Actions CI/CD
✓ Achieve >80% code coverage for critical systems
✓ Document test-passing baseline performance

See :ref:`deployment` for integration with build pipeline.

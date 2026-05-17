.. _tutorials:

Implementation Tutorials and Replication Guides
================================================

This section provides step-by-step guides to replicate core Pyrite systems from scratch. Each tutorial assumes knowledge of the relevant documentation section and focuses on practical implementation.

Tutorial 1: Build a Terrain Generation System
----------------------------------------------

**Objective:** Implement a procedural terrain generator using OpenSimplex noise that produces biome-based, deterministic worlds.

**Time:** 2 hours | **Difficulty:** Medium

**Prerequisites:**
- Understand OpenSimplex noise (read terrain.rst)
- Familiarity with NumPy (for array operations)
- Python 3.9+

**Step 1: Set Up Noise Generator**

.. code-block:: python

    import hashlib
    from opensimplex import OpenSimplex
    import numpy as np
    
    class TerrainGenerator:
        def __init__(self, seed_string):
            # Convert string seed to integer
            hash_obj = hashlib.md5(seed_string.encode())
            self.seed = int(hash_obj.hexdigest(), 16) % (2**31 - 1)
            
            # Initialize noise generator
            self.noise_gen = OpenSimplex(self.seed)
            
            # Constants
            self.CHUNK_SIZE = 48
            self.STONE_LVL = 8
            self.WATER_LVL = 5.6
        
        def noise_2d(self, x, z, scale):
            """Sample 2D OpenSimplex noise"""
            return self.noise_gen.noise2(x * scale, z * scale)
        
        def noise_3d(self, x, y, z, scale):
            """Sample 3D OpenSimplex noise"""
            return self.noise_gen.noise3(x * scale, y * scale, z * scale)

**Step 2: Implement Height Generation (FBm)**

.. code-block:: python

    def get_height_at_column(self, world_x, world_z):
        """Calculate terrain height using fractional Brownian motion"""
        continentalness = 0
        amplitude = 1.0
        frequency = 0.005
        max_amplitude = 0  # For normalization
        
        # 4 octaves of noise
        for octave in [1, 2, 4, 8]:
            freq = frequency * octave
            noise = self.noise_2d(world_x, world_z, freq)
            continentalness += noise * amplitude
            max_amplitude += amplitude
            amplitude *= 0.5
        
        # Normalize
        continentalness /= max_amplitude
        continentalness = np.clip(continentalness, -1.0, 1.0)
        
        # Compute height based on continentalness
        if continentalness < -0.2:
            height = 5.6 + continentalness * 3
        elif continentalness <= 0.1:
            height = 5.6 + continentalness * 8
        elif continentalness <= 0.3:
            height = 6.0 + continentalness * 30
        else:
            height = 15.0 + continentalness * 50
        
        # Add jaggedness
        jaggedness = self.noise_2d(world_x, world_z, 0.04)
        height += jaggedness * 4
        
        return np.clip(height, 0, 256)

**Step 3: Implement Biome Selection**

.. code-block:: python

    BLOCK_IDS = {'GRASS': 1, 'DIRT': 2, 'STONE': 3, 'SAND': 4, 'SNOW': 5, 'WATER': 6}
    
    def get_biome_at_column(self, world_x, world_z):
        """Determine biome from temperature and moisture"""
        temperature = self.noise_2d(world_x, world_z, 0.01)
        moisture = self.noise_2d(world_x, world_z, 0.015)
        
        # Dithering for natural transitions
        dither = self.noise_2d(world_x, world_z, 0.1) * 0.05
        temperature += dither
        moisture += dither
        
        if temperature > 0.3 and moisture < -0.2:
            return 'DESERT'
        elif temperature < -0.2:
            return 'SNOW'
        elif moisture > 0.2:
            return 'FOREST'
        else:
            return 'GRASSLAND'

**Step 4: Generate Chunk Voxels**

.. code-block:: python

    def generate_chunk(self, chunk_x, chunk_y, chunk_z):
        """Generate all voxels for a chunk"""
        chunk_voxels = np.zeros((self.CHUNK_SIZE ** 3,), dtype=np.uint8)
        
        for local_x in range(self.CHUNK_SIZE):
            for local_z in range(self.CHUNK_SIZE):
                world_x = chunk_x * self.CHUNK_SIZE + local_x
                world_z = chunk_z * self.CHUNK_SIZE + local_z
                
                # Get column data
                height = self.get_height_at_column(world_x, world_z)
                biome = self.get_biome_at_column(world_x, world_z)
                
                # Fill column
                for local_y in range(self.CHUNK_SIZE):
                    world_y = chunk_y * self.CHUNK_SIZE + local_y
                    voxel_index = local_x + local_z * self.CHUNK_SIZE + local_y * self.CHUNK_SIZE ** 2
                    
                    if world_y < self.STONE_LVL:
                        chunk_voxels[voxel_index] = BLOCK_IDS['STONE']
                    elif world_y < height:
                        if world_y <= height - 3:
                            chunk_voxels[voxel_index] = BLOCK_IDS['STONE']
                        elif world_y <= height - 1:
                            chunk_voxels[voxel_index] = BLOCK_IDS['DIRT']
                        else:
                            # Surface block
                            if biome == 'DESERT':
                                chunk_voxels[voxel_index] = BLOCK_IDS['SAND']
                            elif biome == 'SNOW':
                                chunk_voxels[voxel_index] = BLOCK_IDS['SNOW']
                            else:
                                chunk_voxels[voxel_index] = BLOCK_IDS['GRASS']
                    elif world_y < self.WATER_LVL:
                        chunk_voxels[voxel_index] = BLOCK_IDS['WATER']
                    else:
                        chunk_voxels[voxel_index] = 0  # AIR
        
        return chunk_voxels

**Verification:**
- Generate a test chunk at (0, 0, 0) and (1, 0, 1)
- Verify same seed produces identical chunks
- Visualize height map (different seeds = different patterns)

Tutorial 2: Implement Greedy Meshing
-------------------------------------

**Objective:** Build a greedy meshing algorithm to reduce polygon count by 90%+.

**Time:** 3 hours | **Difficulty:** Hard

**Prerequisites:**
- Understand bit-packing (read meshes.rst)
- Comfortable with 3D array indexing
- Numba JIT knowledge (optional but helpful)

**Step 1: Check Transparency**

.. code-block:: python

    TRANSPARENT_BLOCKS = {0, 6, 7, 8, 9}  # AIR, WATER, GLASS, LEAVES, VINE
    
    def is_transparent(voxel_id):
        return voxel_id in TRANSPARENT_BLOCKS
    
    def is_solid(voxel_id):
        return not is_transparent(voxel_id)

**Step 2: Implement AO Calculation**

.. code-block:: python

    def get_ao(chunk_voxels, local_y, local_z):
        """Calculate ambient occlusion for a corner"""
        # Check 2x2 block neighbors
        corners = [
            (local_y - 1, local_z - 1),
            (local_y,     local_z - 1),
            (local_y - 1, local_z),
            (local_y,     local_z),
        ]
        
        ao_count = 0
        for y, z in corners:
            if 0 <= y < 48 and 0 <= z < 48:
                voxel_id = chunk_voxels[y, z]  # Simplified index
                if not is_transparent(voxel_id):
                    ao_count += 1
        
        return min(ao_count, 3)  # Clamp to 0-3

**Step 3: Build Greedy Quads**

.. code-block:: python

    def build_greedy_quad(chunk_voxels, plane='Y'):
        """Extract greedy quads from a plane (simplified for XY plane)"""
        vertices = []
        
        # Build 2D mask
        mask = np.zeros((48, 48), dtype=bool)
        for y in range(48):
            for z in range(48):
                voxel_id = chunk_voxels[y, z]
                if is_solid(voxel_id):
                    mask[y, z] = True
        
        processed = set()
        
        for y in range(48):
            for z in range(48):
                if (y, z) in processed or not mask[y, z]:
                    continue
                
                # Find greedy width (extend along Z)
                width = 1
                while z + width < 48 and mask[y, z + width]:
                    width += 1
                
                # Find greedy height (extend along Y)
                height = 1
                valid = True
                while y + height < 48 and valid:
                    for z_check in range(z, z + width):
                        if not mask[y + height, z_check]:
                            valid = False
                            break
                    if valid:
                        height += 1
                    else:
                        break
                
                # Mark as processed
                for dy in range(height):
                    for dz in range(width):
                        processed.add((y + dy, z + dz))
                        mask[y + dy, z + dz] = False
                
                # Add quad vertices
                # (simplified: just record quad dimensions)
                vertices.append({
                    'y': y, 'z': z,
                    'width': width, 'height': height
                })
        
        return vertices

**Verification:**
- Mesh a simple grid of cubes
- Count triangles (should be ~2/3 of naive implementation)
- Visual check: uniform color cubes should render as expected

Tutorial 3: Implement AABB Collision Detection
-----------------------------------------------

**Objective:** Build player-terrain collision detection with axis-separated movement.

**Time:** 2 hours | **Difficulty:** Medium

**Prerequisites:**
- Basic 3D math (vectors, AABBs)
- Understand axis-separated movement (read player.rst)

**Step 1: Define AABB**

.. code-block:: python

    import glm
    
    class AABB:
        def __init__(self, min_pos, max_pos):
            self.min = min_pos  # glm.vec3
            self.max = max_pos  # glm.vec3
        
        def intersects(self, other):
            """Check intersection with another AABB"""
            return (self.min.x < other.max.x and self.max.x > other.min.x and
                    self.min.y < other.max.y and self.max.y > other.min.y and
                    self.min.z < other.max.z and self.max.z > other.min.z)
        
        def get_voxel_aabbs(self, world):
            """Get all solid voxel AABBs within and around this AABB"""
            min_x, min_y, min_z = floor(self.min.x), floor(self.min.y), floor(self.min.z)
            max_x, max_y, max_z = ceil(self.max.x), ceil(self.max.y), ceil(self.max.z)
            
            voxel_boxes = []
            for vx in range(int(min_x), int(max_x) + 1):
                for vy in range(int(min_y), int(max_y) + 1):
                    for vz in range(int(min_z), int(max_z) + 1):
                        voxel_id = world.get_voxel(vx, vy, vz)
                        if not is_transparent(voxel_id):
                            voxel_aabb = AABB(
                                glm.vec3(vx, vy, vz),
                                glm.vec3(vx + 1, vy + 1, vz + 1)
                            )
                            voxel_boxes.append(voxel_aabb)
            
            return voxel_boxes

**Step 2: Resolve Collisions Per-Axis**

.. code-block:: python

    def resolve_axis(axis, player_pos, player_aabb, velocity, world):
        """Resolve collision for single axis"""
        # Compute new position
        old_pos = player_pos.copy()
        player_pos[axis] += velocity[axis]
        
        # Get new AABB
        new_aabb = AABB(
            player_pos - player_half_extents,
            player_pos + player_half_extents
        )
        
        # Check collisions
        voxel_boxes = new_aabb.get_voxel_aabbs(world)
        
        for voxel_box in voxel_boxes:
            if new_aabb.intersects(voxel_box):
                # Collision detected: snap to voxel boundary
                if velocity[axis] > 0:  # Moving positive
                    player_pos[axis] = voxel_box.min[axis] - player_half_extents[axis]
                else:  # Moving negative
                    player_pos[axis] = voxel_box.max[axis] + player_half_extents[axis]
                
                # Handle ground detection (for Y-axis)
                if axis == 1 and velocity[axis] < 0:  # Landing downward
                    on_ground = True
                
                velocity[axis] = 0
                break
        
        return player_pos, velocity

**Step 3: Integrate into Player Update**

.. code-block:: python

    def move_and_collide(player, delta_time, world):
        """Apply velocity to player with collision"""
        velocity = player.velocity.copy()
        
        # Apply gravity
        velocity.y += GRAVITY * delta_time
        
        # Resolve per-axis
        for axis in [0, 1, 2]:  # X, Y, Z
            player.feet_pos, velocity = resolve_axis(
                axis, player.feet_pos, player.get_aabb(), velocity, world
            )
        
        player.velocity = velocity
        player.position = player.feet_pos + glm.vec3(0, PLAYER_EYE_HEIGHT, 0)

**Verification:**
- Place player in mid-air above ground
- Verify gravity pulls down and stops at ground
- Walk into walls (should stop, not clip through)
- Jump and fall (should stick to ground when landing)

Tutorial 4: Implement Inventory and Crafting
---------------------------------------------

**Objective:** Build a 41-slot inventory with drag-drop UI and crafting recipes.

**Time:** 1.5 hours | **Difficulty:** Easy

**Prerequisites:**
- UI components (read ui.rst)
- Basic event handling

**Step 1: Inventory Data Structure**

.. code-block:: python

    NUM_SLOTS = 41
    HOTBAR_SIZE = 9
    MAX_STACK = 64
    
    class Inventory:
        def __init__(self):
            self.slots = [0] * NUM_SLOTS  # 0 = empty, 1-255 = voxel ID
            self.counts = [0] * NUM_SLOTS  # Stack size
            self.selected_slot = 0  # Hotbar index
        
        def add_item(self, voxel_id):
            """Add item to inventory, stack if possible"""
            # Try existing stacks
            for i in range(NUM_SLOTS):
                if self.slots[i] == voxel_id and self.counts[i] < MAX_STACK:
                    self.counts[i] += 1
                    return True
            
            # Add to empty slot
            for i in range(NUM_SLOTS):
                if self.slots[i] == 0:
                    self.slots[i] = voxel_id
                    self.counts[i] = 1
                    return True
            
            return False  # Inventory full
        
        def remove_item(self, slot_index, count=1):
            """Remove items from slot"""
            if self.counts[slot_index] >= count:
                self.counts[slot_index] -= count
                if self.counts[slot_index] == 0:
                    self.slots[slot_index] = 0
                return True
            return False

**Step 2: Crafting Recipes**

.. code-block:: python

    RECIPES = {
        # (slot36, slot37, slot38, slot39) → (output_id, count)
        (WOOD, 0, 0, 0): (WOOD_PLANK, 4),
        (WOOD_PLANK, WOOD_PLANK, STICK, 0): (WOODEN_PICKAXE, 1),
        # ... more recipes
    }
    
    def update_crafting(inventory):
        """Check crafting grid and update output"""
        inputs = (
            inventory.slots[36],
            inventory.slots[37],
            inventory.slots[38],
            inventory.slots[39],
        )
        
        if inputs in RECIPES:
            output_id, count = RECIPES[inputs]
            inventory.slots[40] = output_id
            inventory.counts[40] = count
        else:
            inventory.slots[40] = 0
            inventory.counts[40] = 0

**Step 3: Drag-Drop UI Logic**

.. code-block:: python

    class InventoryUI:
        def __init__(self, inventory):
            self.inventory = inventory
            self.dragging_from = None
            self.dragging_item_id = 0
            self.dragging_count = 0
        
        def on_click(self, slot_index, button):
            if button == 1:  # LClick
                if self.dragging_from is None:
                    # Start drag
                    self.dragging_from = slot_index
                    self.dragging_item_id = self.inventory.slots[slot_index]
                    self.dragging_count = self.inventory.counts[slot_index]
                else:
                    # Drop on target
                    self.swap_or_merge(slot_index)
                    self.dragging_from = None
            
            elif button == 3:  # RClick
                # Split stack
                if self.inventory.counts[slot_index] > 1:
                    half = self.inventory.counts[slot_index] // 2
                    self.inventory.counts[slot_index] -= half
                    # Create shadow item...
        
        def swap_or_merge(self, target_slot):
            """Merge dragged items into target slot"""
            drag_slot = self.dragging_from
            
            if self.inventory.slots[target_slot] == self.inventory.slots[drag_slot]:
                # Same item: merge
                space = MAX_STACK - self.inventory.counts[target_slot]
                transfer = min(space, self.inventory.counts[drag_slot])
                
                self.inventory.counts[target_slot] += transfer
                self.inventory.counts[drag_slot] -= transfer
                
                if self.inventory.counts[drag_slot] == 0:
                    self.inventory.slots[drag_slot] = 0
            else:
                # Different items: swap
                self.inventory.slots[drag_slot], self.inventory.slots[target_slot] = (
                    self.inventory.slots[target_slot], self.inventory.slots[drag_slot]
                )
                self.inventory.counts[drag_slot], self.inventory.counts[target_slot] = (
                    self.inventory.counts[target_slot], self.inventory.counts[drag_slot]
                )

**Verification:**
- Add items to inventory
- Verify stacking works
- Drag items around, test merge/swap
- Check crafting recipe updates output slot


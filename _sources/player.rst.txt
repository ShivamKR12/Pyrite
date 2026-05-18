.. _player:

Player Systems
==============

This document details player control schemes, AABB collision detection, physics simulations, and survival mechanics (health, hunger, oxygen).

Player Class Hierarchy
----------------------

**Player (inherits from Camera)**

The player object manages:

- Position, velocity, view direction
- Physics (gravity, jump, collisions)
- Input handling (keyboard, mouse)
- Survival stats (health, hunger, oxygen)
- Inventory and held item

Architecture:

.. code-block:: text

    class Player(Camera):
        __init__(self, world, start_pos=(0, 50, 0)):
            # Inherited from Camera
            self.position: glm.vec3                    # Camera position (eye)
            self.yaw, self.pitch: float                # Rotation angles (radians)
            
            # Physics state
            self.feet_pos: glm.vec3                    # Position at feet (for collisions)
            self.velocity: glm.vec3                    # Movement velocity
            self.on_ground: bool                       # Contact with solid block
            self.in_water: bool                        # Submerged
            self.head_in_water: bool                   # Head above surface
            
            # Survival stats
            self.health: float                         # 0-20
            self.hunger: float                         # 0-20
            self.oxygen: float                         # 0-20
            self.highest_y: float                       # For fall damage calculation
            
            # Inventory
            self.inventory: List[int]                  # 41 slots, voxel IDs
            self.inventory_counts: List[int]           # Stack sizes (1-64)
            self.hotbar_index: int                     # Selected slot (0-8)
            
            # Mode
            self.game_mode: str                        # 'SURVIVAL' or 'CREATIVE'
            
            # Animation
            self.step_counter: float                   # For view bobbing, footsteps
            self.held_item_swing: float                # 0-1, for swing animation
            
            # Input state
            self.keys_pressed: dict                    # Keys currently held

Coordinate System
-----------------

**Feet Position vs. Eye Position**

- **feet_pos:** Base of player bounding box (Y=0 of AABB)
- **position (inherited):** Eye level = feet_pos.y + EYE_HEIGHT

.. code-block:: python

    PLAYER_WIDTH = 0.6         # XZ diameter
    PLAYER_HEIGHT = 1.8        # Total height
    PLAYER_HALF_W = 0.3        # Half-width for AABB
    PLAYER_EYE_HEIGHT = 1.6    # Distance from feet to eyes
    
    # Calculate AABB
    def get_aabb():
        half_w = PLAYER_HALF_W
        return (
            feet_pos.x - half_w, feet_pos.y,     feet_pos.z - half_w,  # Min
            feet_pos.x + half_w, feet_pos.y + PLAYER_HEIGHT, feet_pos.z + half_w  # Max
        )

Controls and Input Handling
----------------------------

**Keyboard Input (per update, based on held keys)**

+----------+-------------------+---------------------+
| Key      | Survival Mode     | Creative Mode       |
+==========+===================+=====================+
| W        | Move forward      | Move forward        |
+----------+-------------------+---------------------+
| A        | Move left         | Move left           |
+----------+-------------------+---------------------+
| S        | Move backward     | Move backward       |
+----------+-------------------+---------------------+
| D        | Move right        | Move right          |
+----------+-------------------+---------------------+
| Space    | Jump (if grounded)| Move up (fly)       |
+----------+-------------------+---------------------+
| LShift   | Toggle sprint     | Move down (fly)     |
+----------+-------------------+---------------------+
| Mouse    | Look around       | Look around         |
+----------+-------------------+---------------------+
| LClick   | Mine block        | Destroy block       |
+----------+-------------------+---------------------+
| RClick   | Place block       | Place block (fill)  |
+----------+-------------------+---------------------+
| E        | Toggle inventory  | Toggle inventory    |
+----------+-------------------+---------------------+
| Scroll   | Select hotbar     | Select hotbar       |
+----------+-------------------+---------------------+
| 1-9      | Select hotbar     | Select hotbar       |
+----------+-------------------+---------------------+

**Movement Calculation (Survival Mode)**

.. code-block:: python

    def update_movement(delta_time):
        # Compute move direction (camera-relative)
        direction = glm.vec3(0)
        
        if keys['W']: direction += get_forward_vector()
        if keys['S']: direction -= get_forward_vector()
        if keys['A']: direction -= get_right_vector()
        if keys['D']: direction += get_right_vector()
        
        # Sprint multiplier
        if keys['LShift'] and on_ground:
            sprint_mult = PLAYER_SPRINT_MULTIPLIER  # 1.5
            is_sprinting = True
        else:
            sprint_mult = 1.0
            is_sprinting = False
        
        # Apply movement speed
        if len(direction) > 0:
            direction = normalize(direction)
            velocity.x += direction.x * PLAYER_SPEED * sprint_mult * delta_time
            velocity.z += direction.z * PLAYER_SPEED * sprint_mult * delta_time
            
            # View bobbing (sine wave based on distance traveled)
            step_counter += length(glm.vec2(velocity.x, velocity.z)) * delta_time
        
        # Jump (only on ground)
        if keys['Space'] and on_ground:
            velocity.y = JUMP_VELOCITY
            on_ground = False
        
        # Creative fly mode
        if game_mode == 'CREATIVE':
            if keys['Space']:
                velocity.y = PLAYER_SPEED * 5  # Upward
            if keys['LShift']:
                velocity.y = -PLAYER_SPEED * 5  # Downward

**Mouse Input (Camera Control)**

.. code-block:: python

    def handle_mouse_motion(rel_x, rel_y, sensitivity):
        # rel_x, rel_y from pygame.mouse.get_rel()
        
        # Yaw (left-right, X-axis rotation)
        self.yaw -= rel_x * sensitivity
        
        # Pitch (up-down, Y-axis rotation)
        self.pitch -= rel_y * sensitivity
        
        # Clamp pitch to ±90 degrees to prevent over-rotation
        self.pitch = glm.clamp(self.pitch, -glm.pi() / 2, glm.pi() / 2)
        
        # Update camera view matrix accordingly

Physics: Gravity and Velocity
-----------------------------

Applied each update:

.. code-block:: python

    def apply_gravity(delta_time):
        if not on_ground:
            # Fall acceleration
            velocity.y += GRAVITY * delta_time  # GRAVITY = -0.000025
        
        if in_water:
            # Water buoyancy (reduced gravity)
            velocity.y += GRAVITY * PLAYER_UNDERWATER_GRAVITY_MULTIPLIER * delta_time
            # Also apply drag to vertical movement
            velocity.y *= (1.0 - PLAYER_VERTICAL_WATER_DRAG)
        
        # Terminal velocity (optional clamping to prevent extreme speeds)
        velocity.y = max(velocity.y, -0.1)

**Movement and Collision Resolution:**

Movement is axis-separated to enable smooth wall-sliding:

.. code-block:: python

    def move_and_collide(delta_time):
        # Apply velocity to get new position candidates
        new_pos = feet_pos + velocity * delta_time
        
        # Resolve collisions per-axis
        resolve_axis('X', feet_pos, new_pos)
        resolve_axis('Y', feet_pos, new_pos)
        resolve_axis('Z', feet_pos, new_pos)
        
        # Update final position
        feet_pos = new_pos
        position = feet_pos + glm.vec3(0, PLAYER_EYE_HEIGHT, 0)

AABB Collision Detection
------------------------

**Axis-Aligned Bounding Box (AABB)**

.. code-block:: python

    def resolve_axis(axis, current_pos, new_pos):
        # Get AABB after movement
        aabb_min, aabb_max = get_aabb_at(new_pos)
        
        # Scan all voxels within and around AABB
        for vx in range(floor(aabb_min.x), ceil(aabb_max.x)):
            for vy in range(floor(aabb_min.y), ceil(aabb_max.y)):
                for vz in range(floor(aabb_min.z), ceil(aabb_max.z)):
                    voxel_id = world.get_voxel(vx, vy, vz)
                    
                    # Skip transparent voxels (water allows movement)
                    if is_transparent(voxel_id):
                        continue
                    
                    # Check AABB intersection
                    voxel_box = (vx, vy, vz, vx+1, vy+1, vz+1)
                    
                    if aabb_intersect(aabb_min, aabb_max, voxel_box):
                        # Collision: snap position to voxel boundary
                        if axis == 'X':
                            if velocity.x > 0:  # Moving +X
                                new_pos.x = voxel_box[0] - (aabb_max.x - current_pos.x)
                            else:  # Moving -X
                                new_pos.x = voxel_box[3] + (current_pos.x - aabb_min.x)
                            velocity.x = 0
                        
                        elif axis == 'Y':
                            if velocity.y > 0:  # Moving +Y
                                new_pos.y = voxel_box[1] - (aabb_max.y - current_pos.y)
                            else:  # Moving -Y
                                new_pos.y = voxel_box[4] + (current_pos.y - aabb_min.y)
                                on_ground = True
                            velocity.y = 0
                        
                        elif axis == 'Z':
                            if velocity.z > 0:  # Moving +Z
                                new_pos.z = voxel_box[2] - (aabb_max.z - current_pos.z)
                            else:  # Moving -Z
                                new_pos.z = voxel_box[5] + (current_pos.z - aabb_min.z)
                            velocity.z = 0

**AABB Intersection Test:**

.. code-block:: python

    def aabb_intersect(aabb1_min, aabb1_max, aabb2_min, aabb2_max):
        # No separation on any axis = collision
        return (aabb1_min.x < aabb2_max.x and aabb1_max.x > aabb2_min.x and
                aabb1_min.y < aabb2_max.y and aabb1_max.y > aabb2_min.y and
                aabb1_min.z < aabb2_max.z and aabb1_max.z > aabb2_min.z)

Water Physics
-------------

When in water:

.. code-block:: python

    def update_in_water():
        # Check if feet_pos in water voxel
        voxel = world.get_voxel(int(feet_pos.x), int(feet_pos.y), int(feet_pos.z))
        
        if voxel == WATER:
            in_water = True
            
            # Check if head in water (for oxygen drain)
            head_voxel = world.get_voxel(int(position.x), int(position.y), int(position.z))
            head_in_water = (head_voxel == WATER)
            
            # Horizontal drag
            velocity.x *= PLAYER_WATER_DRAG_MULTIPLIER  # 0.5
            velocity.z *= PLAYER_WATER_DRAG_MULTIPLIER
            
            # Vertical drag
            velocity.y *= (1.0 - PLAYER_VERTICAL_WATER_DRAG)  # Additional damping
        else:
            in_water = False
            head_in_water = False

**Dolphin Leap (jump near surface):**

.. code-block:: python

    def try_jump_in_water():
        if in_water and keys['Space']:
            # Check if near surface (head not in water)
            if not head_in_water:
                # Apply upward boost
                velocity.y = JUMP_VELOCITY * PLAYER_DOLPHIN_LEAP_MULTIPLIER  # 1.05x
            else:
                # Normal swimming upward
                velocity.y = PLAYER_SPEED * 3

Survival Stats Management
-------------------------

**Health** (0-20)

- Damaged by: Fall > 3 blocks, void (Y < -64), drowning, contact with hazards
- Healed by: Food (not implemented in basic version)
- Death: respawn at spawn point

.. code-block:: python

    def apply_fall_damage(delta_time):
        if not on_ground:
            highest_y = max(highest_y, feet_pos.y)
        
        if on_ground and feet_pos.y < highest_y - 3.0:
            # Fall distance > 3 blocks
            fall_distance = highest_y - feet_pos.y
            damage = int(fall_distance - 3.0)
            take_damage(damage)
            highest_y = feet_pos.y

**Hunger** (0-20)

- Drains when sprinting or traveling
- Restored by consuming food

.. code-block:: python

    HUNGER_DRAIN_SPRINT = 0.002       # per millisecond
    HUNGER_DRAIN_WALK = 0.0005
    
    def update_hunger(delta_time):
        if is_sprinting:
            hunger -= HUNGER_DRAIN_SPRINT * delta_time
        elif is_moving:
            hunger -= HUNGER_DRAIN_WALK * delta_time
        
        hunger = clamp(hunger, 0, MAX_HUNGER)

**Oxygen** (0-20)

- Depletes when head in water
- Regenerates when above water surface

.. code-block:: python

    OXYGEN_LOSE_TIMER = 1000    # ms, depletes 1 oxygen per second
    OXYGEN_GAIN_TIMER = 200     # ms, regenerates 1 oxygen per 200ms
    
    def update_oxygen(delta_time):
        if head_in_water:
            oxygen_drain_time += delta_time
            if oxygen_drain_time >= OXYGEN_LOSE_TIMER:
                oxygen -= 1
                oxygen_drain_time = 0
        else:
            oxygen_refill_time += delta_time
            if oxygen_refill_time >= OXYGEN_GAIN_TIMER:
                oxygen += 1
                oxygen_refill_time = 0
        
        oxygen = clamp(oxygen, 0, MAX_OXYGEN)
        
        # Drowned at 0 oxygen
        if oxygen == 0:
            take_damage(1)  # 1 damage per frame

**Void Damage** (Y < -64)

.. code-block:: python

    VOID_DEATH_Y = -64
    VOID_DAMAGE = 1
    VOID_DAMAGE_INTERVAL = 500  # ms
    
    def apply_void_damage(delta_time):
        if feet_pos.y < VOID_DEATH_Y:
            void_damage_time += delta_time
            if void_damage_time >= VOID_DAMAGE_INTERVAL:
                take_damage(VOID_DAMAGE)
                void_damage_time = 0

Inventory Management
--------------------

**Structure:**

.. code-block:: python

    inventory = [0] * 41  # 41 slots, 0 = empty, 1-255 = voxel ID
    inventory_counts = [0] * 41  # Stack sizes (1-64)
    
    # Slots breakdown:
    # 0-8:   Hotbar
    # 9-35:  Main storage (27 slots)
    # 36-39: Crafting 2x2 grid
    # 40:    Crafting output

**Add Item (pickup or craft):**

.. code-block:: python

    def add_item(voxel_id):
        # Try to stack on existing
        for slot in range(41):
            if inventory[slot] == voxel_id and inventory_counts[slot] < 64:
                space = 64 - inventory_counts[slot]
                inventory_counts[slot] += 1
                return
        
        # Add to empty slot (hotbar first)
        for slot in range(41):
            if inventory[slot] == 0:
                inventory[slot] = voxel_id
                inventory_counts[slot] = 1
                return

**Get Held Item:**

.. code-block:: python

    def get_held_item():
        return inventory[hotbar_index], inventory_counts[hotbar_index]

Mining and Placing
------------------

**Mining (LClick):**

1. Raycast from player camera to find target block
2. Calculate break time based on block hardness and held tool
3. If held long enough, remove block and drop item

.. code-block:: python

    BLOCK_HARDNESS = {
        STONE: 1500,        # ms to break
        WOOD: 1000,
        DIRT: 500,
        GRASS: 300,
        ...
    }
    
    TOOL_MULTIPLIER = {
        BARE_HAND: 1.0,
        WOODEN_PICKAXE: 0.2,   # 5x faster than bare hand
        STONE_PICKAXE: 0.1,
        ...
    }
    
    def mine_block(target_block_id):
        hardness = BLOCK_HARDNESS.get(target_block_id, 1000)
        held_item = get_held_item()
        multiplier = TOOL_MULTIPLIER.get(held_item, 1.0)
        
        break_time = hardness * multiplier  # ms
        
        # Player holds LClick; after break_time, remove block
        if held_click_duration >= break_time:
            world.remove_voxel(target_pos)
            # Drop item if not in creative mode or not holding wrong tool
            if game_mode == 'SURVIVAL':
                drop_item(target_block_id)

**Placing (RClick):**

1. Raycast to find target face
2. Place block on adjacent empty voxel
3. Consume from inventory

.. code-block:: python

    def place_block():
        target_face_normal = raycast_result.normal
        target_pos = raycast_result.pos
        
        # Compute placement position (adjacent to target)
        place_pos = target_pos + target_face_normal
        
        # Check empty and no player collision
        if not world.is_solid(place_pos) and not aabb_intersect_voxel(place_pos):
            voxel_id = get_held_item()
            world.place_voxel(place_pos, voxel_id)
            
            if game_mode == 'SURVIVAL':
                consume_inventory(hotbar_index, 1)

View Bobbing and Hand Animation
-------------------------------

**View Bobbing (Camera offset):**

.. code-block:: python

    def update_view_bobbing():
        # Sine wave based on step_counter
        bob_y = math.sin(step_counter * BOB_FREQ) * BOB_AMPLITUDE
        
        # Vertical head offset
        position.y += bob_y

**Held Item Swing (for visual feedback):**

.. code-block:: python

    def update_held_item_animation():
        if held_item_swing > 0:
            # Decrease swing over time
            held_item_swing -= delta_time / SWING_DURATION  # e.g., 0.2 seconds
            held_item_swing = max(held_item_swing, 0)
        
        # During swing, rotate/bob held item in camera space
        swing_rotation = held_item_swing * 45  # degrees
        swing_bob = sin(held_item_swing * PI) * 0.1

Dynamic FOV During Sprint
--------------------------

.. code-block:: python

    def update_fov():
        target_fov = BASE_FOV  # e.g., 70 degrees
        
        if is_sprinting:
            target_fov = BASE_FOV + 10  # Expand FOV while running
        
        # Smooth lerp
        current_fov = lerp(current_fov, target_fov, 0.1 * delta_time)

Integration with Game Loop
----------------------------

.. code-block:: python

    def player_update(delta_time):
        update_movement(delta_time)
        handle_mouse_motion()
        apply_gravity(delta_time)
        move_and_collide(delta_time)
        update_in_water()
        update_oxygen(delta_time)
        update_hunger(delta_time)
        apply_fall_damage(delta_time)
        apply_void_damage(delta_time)
        update_held_item_animation()
        update_view_bobbing()


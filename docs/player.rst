.. _player:

==============
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

    self.feet_pos: glm.vec3
    self.velocity: glm.vec3

* **Physics State:** The player relies on a separate `feet_pos` for accurate AABB collision detection, while `velocity` governs movement directions independently of the camera's true position.

.. code-block:: text

    self.health: float
    self.hunger: float
    self.oxygen: float

* **Survival Metrics:** Tracking variables process independent decrement logics per-update for standard mechanics.

Coordinate System
-----------------

**Feet Position vs. Eye Position**

- **feet_pos:** Base of player bounding box (Y=0 of AABB)
- **position (inherited):** Eye level = feet_pos.y + EYE_HEIGHT

.. code-block:: python

    def get_aabb():
        return (feet_pos.x - half_w, feet_pos.y, feet_pos.z - half_w,  # Min
                feet_pos.x + half_w, feet_pos.y + PLAYER_HEIGHT, feet_pos.z + half_w)  # Max

* **AABB Computation:** The bounding geometry wraps identically relative strictly around the bottom-point geometry calculation.

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

    if keys['W']: direction += get_forward_vector()
    if keys['S']: direction -= get_forward_vector()

* **Directional Vectors:** Key matrices immediately transpose specific geometric coordinates normalized onto the velocity stack.

.. code-block:: python

    if keys['Space'] and on_ground:
        velocity.y = JUMP_VELOCITY

* **Velocity Stacking:** Vertical impulses manipulate specifically isolated single-axis floating calculations to resolve jumping.

**Mouse Input (Camera Control)**

.. code-block:: python

    self.yaw -= rel_x * sensitivity
    self.pitch -= rel_y * sensitivity
    self.pitch = glm.clamp(self.pitch, -glm.pi() / 2, glm.pi() / 2)

* **Mouse Polling:** Relative hardware motion continuously calculates yaw bounds alongside hard-clamped pitch maximums.

Physics: Gravity and Velocity
-----------------------------

Applied each update:

.. code-block:: python

    if not on_ground:
        velocity.y += GRAVITY * delta_time

* **Falling Physics:** Downward velocity accrues natively minus specific localized modifiers if swimming.

**Movement and Collision Resolution:**

Movement is axis-separated to enable smooth wall-sliding:

.. code-block:: python

    resolve_axis('X', feet_pos, new_pos)
    resolve_axis('Y', feet_pos, new_pos)
    resolve_axis('Z', feet_pos, new_pos)

* **Axis Separation:** To permit fluid surface sliding instead of sharp halts, boundaries check independently per explicit dimension vector.

AABB Collision Detection
------------------------

**Axis-Aligned Bounding Box (AABB)**

.. code-block:: python

    if aabb_intersect(aabb_min, aabb_max, voxel_box):
        new_pos.y = voxel_box[1] - (aabb_max.y - current_pos.y)

* **Collision Resolution:** Geometric bounds explicitly calculate distance snapping exactly flush to intersection thresholds seamlessly.

**AABB Intersection Test:**

.. code-block:: python

    return (aabb1_min.x < aabb2_max.x and aabb1_max.x > aabb2_min.x and
            aabb1_min.y < aabb2_max.y and aabb1_max.y > aabb2_min.y and
            aabb1_min.z < aabb2_max.z and aabb1_max.z > aabb2_min.z)

* **Volume Intersection:** Bounding box verifications check all parallel overlapping instances definitively.

Water Physics
-------------

When in water:

.. code-block:: python

    velocity.x *= PLAYER_WATER_DRAG_MULTIPLIER
    velocity.y *= (1.0 - PLAYER_VERTICAL_WATER_DRAG)

* **Liquid Dampening:** Severe scalar decrements forcefully apply across movement bounds strictly inside liquid domains.

**Dolphin Leap (jump near surface):**

.. code-block:: python

    if not head_in_water:
        velocity.y = JUMP_VELOCITY * PLAYER_DOLPHIN_LEAP_MULTIPLIER

* **Surface Leaping:** Distinct thresholds evaluate if oxygen metrics align safely prior to launching elevated velocity spikes natively.

Survival Stats Management
-------------------------

**Health** (0-20)

- Damaged by: Fall > 3 blocks, void (Y < -64), drowning, contact with hazards
- Healed by: Food (not implemented in basic version)
- Death: respawn at spawn point

.. code-block:: python

    fall_distance = highest_y - feet_pos.y
    damage = int(fall_distance - 3.0)

* **Height Injury:** Substantial block thresholds directly convert raw velocity differentials into discrete damage indices seamlessly.

**Hunger** (0-20)

- Drains when sprinting or traveling
- Restored by consuming food

.. code-block:: python

    hunger -= HUNGER_DRAIN_SPRINT * delta_time
    hunger -= HUNGER_DRAIN_WALK * delta_time

* **Endurance Depletion:** Specific sub-values continually detach natively mapped multipliers across elapsed time intervals precisely.

**Oxygen** (0-20)

- Depletes when head in water
- Regenerates when above water surface

.. code-block:: python

    if oxygen_drain_time >= OXYGEN_LOSE_TIMER:
        oxygen -= 1

* **Breath Decrements:** Time loops repeatedly fire structural logic limits checking head positioning securely above physics grids dynamically.

**Void Damage** (Y < -64)

.. code-block:: python

    if feet_pos.y < VOID_DEATH_Y:
        take_damage(VOID_DAMAGE)

* **Abyss Processing:** Infinite downward limits automatically strike static variables halting map leaks successfully.

Inventory Management
--------------------

**Structure:**

.. code-block:: python

    inventory = [0] * 41
    inventory_counts = [0] * 41

* **Allocation Geometry:** Fundamental grid arrays separate specifically localized components intuitively spanning up to 41 distinct fields effortlessly.

**Add Item (pickup or craft):**

.. code-block:: python

    if inventory[slot] == voxel_id and inventory_counts[slot] < 64:
        inventory_counts[slot] += 1

* **Stack Increment:** Incoming item instances cleanly augment parallel matching vectors up to specified bounds safely via loop detection logic reliably.

**Get Held Item:**

.. code-block:: python

    return inventory[hotbar_index], inventory_counts[hotbar_index]

* **Held Element:** Easy index matching retrieves mapped pointers quickly globally precisely.

Mining and Placing
------------------

**Mining (LClick):**

1. Raycast from player camera to find target block
2. Calculate break time based on block hardness and held tool
3. If held long enough, remove block and drop item

.. code-block:: python

    break_time = hardness * multiplier
    if held_click_duration >= break_time: world.remove_voxel(target_pos)

* **Hardness Modifiers:** Tool matrices dramatically reduce required click thresholds dynamically processing interaction ray calculations simultaneously universally accurately.

**Placing (RClick):**

1. Raycast to find target face
2. Place block on adjacent empty voxel
3. Consume from inventory

.. code-block:: python

    if not world.is_solid(place_pos) and not aabb_intersect_voxel(place_pos):
        world.place_voxel(place_pos, voxel_id)

* **Void Bounds:** Face computations place items exclusively when checking empty volume availability actively safely maintaining grid consistency robustly effortlessly.

View Bobbing and Hand Animation
-------------------------------

**View Bobbing (Camera offset):**

.. code-block:: python

    bob_y = math.sin(step_counter * BOB_FREQ) * BOB_AMPLITUDE
    position.y += bob_y

* **Visual Pacing:** Harmonic sine logic strictly couples offset manipulation dynamically toward pure distance evaluations smoothly realistically continuously.

**Held Item Swing (for visual feedback):**

.. code-block:: python

    swing_rotation = held_item_swing * 45
    swing_bob = sin(held_item_swing * PI) * 0.1

* **Swing Metrics:** Action interpolations cleanly render independent UI item arrays naturally completely synchronously via normalized duration thresholds purely.

Dynamic FOV During Sprint
--------------------------

.. code-block:: python

    if is_sprinting: target_fov = BASE_FOV + 10
    current_fov = lerp(current_fov, target_fov, 0.1 * delta_time)

* **Perspective Expansion:** Linear interpolation visually manipulates lens sizing rapidly during advanced velocity scenarios effectively smoothly securely.

Integration with Game Loop
----------------------------

.. code-block:: python

    apply_gravity(delta_time)
    move_and_collide(delta_time)

* **Delegation Pass:** Singular unified core looping handles continuous physical physics state adjustments transparently uniformly.

Next Steps
----------

Now that player movement and block interactions are covered, explore the :doc:`survival` mechanics to see how health, inventory, and item physics complete the gameplay loop.

import pygame as pg
from pyglm import glm
import math
from camera import Camera
from settings import *
from terrain_gen import get_height
import noise


class Player(Camera):
    def __init__(self, app, position=None, yaw=-90, pitch=0):
        self.app = app
        if position is None:
            position = self.find_spawn_position()
        super().__init__(position, yaw, pitch)
        # physics state
        self.velocity = glm.vec3(0)
        self.on_ground = False
        self.in_water = False
        self.feet_pos = glm.vec3(position)
        self.game_mode = SURVIVAL
        self.step_counter = 0
        self.interaction_timer = 0
        self.interaction_delay = INTERACTION_DELAY
        self.last_step_time = 0
        
        self.target_voxel_pos = None
        self.mining_time = 0.0
        self.mining_duration = 0.0 # updated dynamically
        
        self.inventory = [0] * INVENTORY_SIZE # 0 means empty slot
        self.inventory_counts = [0] * INVENTORY_SIZE
        self.hotbar_index = 0
        
        self.fov = glm.radians(self.app.config['fov'])
        self.is_sprinting = False

        # --- Survival Stats ---
        self.max_health = MAX_HEALTH
        self.health = self.max_health
        self.max_hunger = MAX_HUNGER
        self.hunger = self.max_hunger
        self.max_oxygen = MAX_OXYGEN
        self.oxygen = self.max_oxygen
        
        self.highest_y = position.y
        self.oxygen_timer = 0
        self.last_damage_time = 0
        self.spawn_immunity = True

    def find_spawn_position(self):        
        center_x = int(CENTER_XZ)
        center_z = int(CENTER_XZ)
        
        # Expanding grid search for the closest solid block
        for radius in range(0, SPAWN_SEARCH_RADIUS):
            for dx in range(-radius, radius + 1):
                for dz in range(-radius, radius + 1):
                    # Check only the perimeter of the current radius to expand outward layer by layer
                    if abs(dx) == radius or abs(dz) == radius: 
                        x = center_x + dx
                        z = center_z + dz
                        y = get_height(x, z, noise.perm)
                        
                        # Ensure the player doesn't spawn underwater
                        if y > WATER_LINE:
                            return glm.vec3(x + 0.5, y, z + 0.5)
                            
        return glm.vec3(PLAYER_POS)

    def update(self):
        if self.app.game_state == 'IN_GAME':
            self.mouse_control()
            
        if self.game_mode == CREATIVE:
            # free camera mode — NO PHYSICS
            if self.app.game_state == 'IN_GAME':
                self.keyboard_control()
            else:
                self.velocity = glm.vec3(0)
                
            # Check if player HEAD is in water so the blue fog shader updates properly in creative mode!
            head_pos = glm.ivec3(glm.floor(self.position.x), glm.floor(self.position.y), glm.floor(self.position.z))
            voxel_head, *_ = self.app.scene.world.voxel_handler.get_voxel_id(head_pos)
            self.head_in_water = (voxel_head == WATER)
        else:
            # player mode — physics + collisions
            was_on_ground = self.on_ground
            if self.app.game_state == 'IN_GAME':
                self.keyboard_control()
            else:
                self.velocity.x = self.velocity.z = 0.0
                self.is_sprinting = False
            self.apply_gravity()
            self.on_ground = False
            
            prev_feet_pos = glm.vec3(self.feet_pos)
            self.move_and_collide()
            
            # Get block under player
            block_under_pos = glm.ivec3(glm.floor(self.feet_pos.x), glm.floor(self.feet_pos.y - 0.05), glm.floor(self.feet_pos.z))
            voxel_under, *_ = self.app.scene.world.voxel_handler.get_voxel_id(block_under_pos)
            if not voxel_under: 
                voxel_under = GRASS

            # Check if player body is in water
            body_pos = glm.ivec3(glm.floor(self.position.x), glm.floor(self.position.y - PLAYER_EYE_HEIGHT * 0.5), glm.floor(self.position.z))
            voxel_body, *_ = self.app.scene.world.voxel_handler.get_voxel_id(body_pos)
            
            # Check if player feet are in water
            feet_block_pos = glm.ivec3(glm.floor(self.feet_pos.x), glm.floor(self.feet_pos.y), glm.floor(self.feet_pos.z))
            voxel_feet, *_ = self.app.scene.world.voxel_handler.get_voxel_id(feet_block_pos)
            
            self.in_water = (voxel_body == WATER) or (voxel_feet == WATER)

            # Check if player HEAD is in water
            head_pos = glm.ivec3(glm.floor(self.position.x), glm.floor(self.position.y), glm.floor(self.position.z))
            voxel_head, *_ = self.app.scene.world.voxel_handler.get_voxel_id(head_pos)
            self.head_in_water = (voxel_head == WATER)

            if self.on_ground and not was_on_ground:
                self.app.sounds.play_jump(voxel_under)
                
                # Apply fall damage
                fall_dist = self.highest_y - self.position.y
                if self.spawn_immunity:
                    self.spawn_immunity = False
                else:
                    if fall_dist > FALL_DAMAGE_THRESHOLD and not self.in_water:
                        damage = int(math.floor(fall_dist - FALL_DAMAGE_THRESHOLD))
                        if damage > 0:
                            self.take_damage(damage)
                self.highest_y = self.position.y

            # Update highest Y for fall damage
            if self.velocity.y > 0 or self.in_water:
                self.highest_y = self.position.y
            elif self.position.y > self.highest_y:
                self.highest_y = self.position.y

            # View Bobbing
            bob_offset = 0.0
            # Calculate actual horizontal distance moved to prevent footsteps when stuck against a wall
            actual_move_dist = glm.length(glm.vec2(self.feet_pos.x - prev_feet_pos.x, self.feet_pos.z - prev_feet_pos.z))
            is_walking = self.on_ground and actual_move_dist > 0.0001
            if is_walking:
                self.step_counter += actual_move_dist * VIEW_BOBBING_STEP_FREQUENCY
                bob_offset = glm.sin(self.step_counter) * VIEW_BOBBING_AMPLITUDE
                
                # Drain hunger
                hunger_drain = (HUNGER_DRAIN_SPRINT if self.is_sprinting else HUNGER_DRAIN_WALK) * self.app.delta_time
                self.hunger = max(0.0, self.hunger - hunger_drain)

                current_time = pg.time.get_ticks()
                if current_time - self.last_step_time > 400: # ms between steps
                    self.app.sounds.play_walk(voxel_under)
                    self.last_step_time = current_time
                    
            # Dynamic FOV for sprinting
            base_fov = glm.radians(self.app.config['fov'])
            # Use horizontal movement instead of is_walking so FOV doesn't snap when going up/down blocks
            is_moving_horizontally = actual_move_dist > 0.0001
            target_fov = base_fov + glm.radians(SPRINT_FOV_BOOST) if self.is_sprinting and is_moving_horizontally else base_fov
            # Cap the lerp factor to 1.0 to prevent mathematical overshoot/camera shaking on lower framerates!
            self.fov += (target_fov - self.fov) * min(1.0, SPRINT_FOV_LERP_SPEED * self.app.delta_time)
            self.m_proj = glm.perspective(self.fov, ASPECT_RATIO, NEAR, FAR)
            h_fov = 2 * math.atan(math.tan(self.fov * 0.5) * ASPECT_RATIO)
            self.frustum.update_factors(self.fov, h_fov)

            self.position = self.feet_pos + glm.vec3(0, PLAYER_EYE_HEIGHT + bob_offset, 0)
            
            if self.app.game_state == 'IN_GAME':
                self.handle_interaction()

            # Oxygen & Drowning Logic
            current_time = pg.time.get_ticks()
            if self.head_in_water:
                if current_time - self.oxygen_timer > OXYGEN_LOSE_TIMER:
                    self.oxygen -= 1
                    self.oxygen_timer = current_time
                    if self.oxygen < 0:
                        self.oxygen = 0
                        self.take_damage(1)
            else:
                if self.oxygen < self.max_oxygen and current_time - self.oxygen_timer > OXYGEN_GAIN_TIMER:
                    self.oxygen += 1
                    self.oxygen_timer = current_time

            # Void Fall Damage
            if self.position.y < VOID_DEATH_Y:
                if current_time - self.last_damage_time > VOID_DAMAGE_INTERVAL: # Take damage every half second
                    self.take_damage(VOID_DAMAGE)
                    self.last_damage_time = current_time
        super().update()

    def handle_event(self, event):
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_f:
                self.game_mode = SURVIVAL if self.game_mode == CREATIVE else CREATIVE
                if self.game_mode == CREATIVE:
                    # sync feet to camera when entering creative
                    self.feet_pos = glm.vec3(self.position)
                    self.velocity = glm.vec3(0)
                else:
                    # sync camera to feet when exiting creative
                    self.feet_pos = glm.vec3(self.position)
                    self.velocity = glm.vec3(0)
                self.highest_y = self.position.y
            
            # Hotbar numeric keys
            if pg.K_1 <= event.key <= pg.K_1 + HOTBAR_SIZE - 1:
                self.hotbar_index = event.key - pg.K_1
                
        # adding and removing voxels with clicks
        if event.type == pg.MOUSEBUTTONDOWN:
            voxel_handler = self.app.scene.world.voxel_handler
            if event.button == 3: # Right click to place
                voxel_handler.set_voxel(mode='add')
                self.interaction_timer = pg.time.get_ticks()
            if event.button == 4:  # Scroll Up
                self.hotbar_index = (self.hotbar_index - 1) % HOTBAR_SIZE
            if event.button == 5:  # Scroll Down
                self.hotbar_index = (self.hotbar_index + 1) % HOTBAR_SIZE

    def mouse_control(self):
        mouse_dx, mouse_dy = pg.mouse.get_rel()
        sens = self.app.config['sensitivity']
        if mouse_dx:
            self.rotate_yaw(delta_x=mouse_dx * sens)
        if mouse_dy:
            self.rotate_pitch(delta_y=mouse_dy * sens)

    def handle_interaction(self):
        mouse_pressed = pg.mouse.get_pressed()
        voxel_handler = self.app.scene.world.voxel_handler
        
        current_time = pg.time.get_ticks()
        
        # Mining logic (Left click)
        if mouse_pressed[0] and voxel_handler.voxel_id:
            if self.target_voxel_pos == voxel_handler.voxel_world_pos:
                self.mining_time += self.app.delta_time
                self.app.sounds.play_breaking(voxel_handler.voxel_id, self.mining_time, self.mining_duration)
                if self.mining_time >= self.mining_duration and current_time - self.interaction_timer > self.interaction_delay:
                    voxel_handler.set_voxel(mode='remove')
                    self.mining_time = 0.0
                    self.interaction_timer = current_time
            else:
                self.target_voxel_pos = voxel_handler.voxel_world_pos
                self.mining_time = 0.0
                hardness = BLOCK_HARDNESS.get(voxel_handler.voxel_id, 600.0)
                held_id = self.inventory[self.hotbar_index]
                
                if voxel_handler.voxel_id in (STONE, COBBELSTONE):
                    if held_id == WOODEN_PICKAXE:
                        hardness /= PICKAXE_MINING_MULTIPLIER # 5x faster WITH a pickaxe!
                    else:
                        hardness *= BAREHAND_MINING_PENALTY # 5x slower without a pickaxe!
                        
                self.mining_duration = 0.0 if self.game_mode == CREATIVE else hardness
                self.app.sounds.play_breaking(voxel_handler.voxel_id, self.mining_time, self.mining_duration)
                
                if self.mining_time >= self.mining_duration and current_time - self.interaction_timer > self.interaction_delay:
                    voxel_handler.set_voxel(mode='remove')
                    self.mining_time = 0.0
                    self.interaction_timer = current_time
        else:
            self.mining_time = 0.0
            
        # Placing logic (Right click)
        if mouse_pressed[2]:
            if current_time - self.interaction_timer > self.interaction_delay:
                voxel_handler.set_voxel(mode='add')
                self.interaction_timer = current_time

    def keyboard_control(self):
        if self.game_mode == CREATIVE:
            key_state = pg.key.get_pressed()
            vel = PLAYER_SPEED * 5 * self.app.delta_time
            if key_state[pg.K_w]:
                self.move_forward(vel)
            if key_state[pg.K_s]:
                self.move_back(vel)
            if key_state[pg.K_d]:
                self.move_right(vel)
            if key_state[pg.K_a]:
                self.move_left(vel)
            if key_state[pg.K_SPACE]:
                self.move_up(vel)
            if key_state[pg.K_LSHIFT]:
                self.move_down(vel)
        else:
            keys = pg.key.get_pressed()
            speed = PLAYER_SPEED
            self.is_sprinting = False
            move_dir = glm.vec3(0)
            flat_forward = glm.vec3(self.forward.x, 0, self.forward.z)
            if glm.length(flat_forward) > 0:
                flat_forward = glm.normalize(flat_forward)
            if keys[pg.K_w]:
                move_dir += flat_forward
            if keys[pg.K_s]:
                move_dir -= flat_forward
            if keys[pg.K_d]:
                move_dir += self.right
            if keys[pg.K_a]:
                move_dir -= self.right
            if glm.length(move_dir):
                move_dir = glm.normalize(move_dir)
            if keys[pg.K_LSHIFT]:
                speed *= PLAYER_SPRINT_MULTIPLIER
                self.is_sprinting = True
            self.velocity.x = move_dir.x * speed
            self.velocity.z = move_dir.z * speed
            
            if self.in_water:
                self.velocity.x *= PLAYER_WATER_DRAG_MULTIPLIER # Water drag
                self.velocity.z *= PLAYER_WATER_DRAG_MULTIPLIER
                if self.on_ground and keys[pg.K_SPACE]:
                    self.velocity.y = JUMP_VELOCITY
                    self.on_ground = False
                elif keys[pg.K_SPACE]:
                    # Dolphin leap out of water if near the surface, otherwise normal swim!
                    if not getattr(self, 'head_in_water', False):
                        self.velocity.y = max(self.velocity.y, JUMP_VELOCITY * PLAYER_DOLPHIN_LEAP_MULTIPLIER)
                    else:
                        self.velocity.y = max(self.velocity.y, JUMP_VELOCITY * 0.8) # Swim up
            else:
                if self.on_ground and keys[pg.K_SPACE]:
                    self.velocity.y = JUMP_VELOCITY
                    self.on_ground = False

    def apply_gravity(self):
        if self.in_water:
            self.velocity.y += GRAVITY * PLAYER_UNDERWATER_GRAVITY_MULTIPLIER * self.app.delta_time
            self.velocity.y *= max(0.0, 1.0 - PLAYER_VERTICAL_WATER_DRAG * self.app.delta_time) # vertical water drag
        else:
            self.velocity.y += GRAVITY * self.app.delta_time

    def move_and_collide(self):
        # X axis
        # self.position.x += self.velocity.x
        self.feet_pos.x += self.velocity.x * self.app.delta_time
        self.resolve_axis('x')
        # Y axis
        # self.position.y += self.velocity.y
        self.feet_pos.y += self.velocity.y * self.app.delta_time
        self.resolve_axis('y')
        # Z axis
        # self.position.z += self.velocity.z
        self.feet_pos.z += self.velocity.z * self.app.delta_time
        self.resolve_axis('z')

    def resolve_axis(self, axis):
        aabb_min, aabb_max = self.get_aabb()
        min_x = int(glm.floor(aabb_min.x))
        max_x = int(glm.floor(aabb_max.x))
        min_y = int(glm.floor(aabb_min.y))
        max_y = int(glm.floor(aabb_max.y))
        min_z = int(glm.floor(aabb_min.z))
        max_z = int(glm.floor(aabb_max.z))
        world = self.app.scene.world
        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                for z in range(min_z, max_z + 1):
                    voxel_id, *_ = world.voxel_handler.get_voxel_id(glm.ivec3(x, y, z))
                    if not voxel_id or voxel_id == WATER:
                        continue
                    voxel_min = glm.vec3(x, y, z)
                    voxel_max = voxel_min + 1
                    if self.aabb_intersect(aabb_min, aabb_max, voxel_min, voxel_max):
                        if axis == 'x':
                            if self.velocity.x > 0:
                                # self.position.x = voxel_min.x - PLAYER_HALF_W
                                self.feet_pos.x = voxel_min.x - PLAYER_HALF_W
                            else:
                                # self.position.x = voxel_max.x + PLAYER_HALF_W
                                self.feet_pos.x = voxel_max.x + PLAYER_HALF_W
                            self.velocity.x = 0
                        elif axis == 'y':
                            if self.velocity.y > 0:
                                # self.position.y = voxel_min.y - PLAYER_HEIGHT
                                self.feet_pos.y = voxel_min.y - PLAYER_HEIGHT
                            else:
                                # self.position.y = voxel_max.y
                                self.feet_pos.y = voxel_max.y
                                self.on_ground = True
                            self.velocity.y = 0
                        elif axis == 'z':
                            if self.velocity.z > 0:
                                # self.position.z = voxel_min.z - PLAYER_HALF_W
                                self.feet_pos.z = voxel_min.z - PLAYER_HALF_W
                            else:
                                # self.position.z = voxel_max.z + PLAYER_HALF_W
                                self.feet_pos.z = voxel_max.z + PLAYER_HALF_W
                            self.velocity.z = 0
                        aabb_min, aabb_max = self.get_aabb()

    def get_aabb(self):
        min_v = glm.vec3(
            # self.position.x - PLAYER_HALF_W,
            self.feet_pos.x - PLAYER_HALF_W,
            # self.position.y,
            self.feet_pos.y,
            # self.position.z - PLAYER_HALF_W
            self.feet_pos.z - PLAYER_HALF_W
        )
        max_v = glm.vec3(
            # self.position.x + PLAYER_HALF_W,
            self.feet_pos.x + PLAYER_HALF_W,
            # self.position.y + PLAYER_HEIGHT,
            self.feet_pos.y + PLAYER_HEIGHT,
            # self.position.z + PLAYER_HALF_W
            self.feet_pos.z + PLAYER_HALF_W
        )
        return min_v, max_v

    @staticmethod
    def aabb_intersect(a_min, a_max, b_min, b_max):
        return (
            a_min.x < b_max.x and a_max.x > b_min.x and
            a_min.y < b_max.y and a_max.y > b_min.y and
            a_min.z < b_max.z and a_max.z > b_min.z
        )

    def add_item(self, voxel_id):
        # Check if we already have a stack of this item
        for i in range(36): # Only check the main 36 storage slots
            if self.inventory[i] == voxel_id and self.inventory_counts[i] < 64:
                self.inventory_counts[i] += 1
                return True
        # Find an empty slot
        for i in range(36):
            if self.inventory[i] == 0:
                self.inventory[i] = voxel_id
                self.inventory_counts[i] = 1
                return True
        return False # Inventory is full!

    def take_damage(self, amount):
        if self.game_mode == CREATIVE:
            return
        self.health -= amount
        self.app.sounds.play_walk(GRASS) # Generic damage sound
        if self.health <= 0:
            self.respawn()

    def respawn(self):
        self.health = self.max_health
        self.hunger = self.max_hunger
        self.oxygen = self.max_oxygen
        
        self.feet_pos = self.find_spawn_position()
        self.position = self.feet_pos + glm.vec3(0, PLAYER_EYE_HEIGHT, 0)
        self.velocity = glm.vec3(0)
        self.highest_y = self.position.y
        self.spawn_immunity = True

import pygame as pg
import glm
import math
from camera import Camera
from settings import *


class Player(Camera):
    def __init__(self, app, position=PLAYER_POS, yaw=-90, pitch=0):
        self.app = app
        super().__init__(position, yaw, pitch)
        # physics state
        self.velocity = glm.vec3(0)
        self.on_ground = False
        self.feet_pos = glm.vec3(position)
        self.free_fly = False
        self.step_counter = 0
        self.interaction_timer = 0
        self.interaction_delay = 150 # ms delay for continuous mining/placing
        self.last_step_time = 0
        
        self.target_voxel_pos = None
        self.mining_time = 0.0
        self.mining_duration = 0.0 # updated dynamically
        
        self.hotbar = [0] * 9 # 0 means empty slot
        self.hotbar_counts = [0] * 9
        self.hotbar_index = 0
        
        self.fov = V_FOV
        self.is_sprinting = False

    def update(self):
        self.mouse_control()
        if self.free_fly:
            # free camera mode — NO PHYSICS
            self.keyboard_control()
        else:
            # player mode — physics + collisions
            was_on_ground = self.on_ground
            self.keyboard_control()
            self.apply_gravity()
            self.on_ground = False
            
            prev_feet_pos = glm.vec3(self.feet_pos)
            self.move_and_collide()
            
            # Get block under player
            block_under_pos = glm.ivec3(glm.floor(self.feet_pos.x), glm.floor(self.feet_pos.y - 0.05), glm.floor(self.feet_pos.z))
            voxel_under, *_ = self.app.scene.world.voxel_handler.get_voxel_id(block_under_pos)
            if not voxel_under: 
                voxel_under = GRASS

            if self.on_ground and not was_on_ground:
                self.app.sounds.play_jump(voxel_under)

            # View Bobbing
            bob_offset = 0.0
            # Calculate actual horizontal distance moved to prevent footsteps when stuck against a wall
            actual_move_dist = glm.length(glm.vec2(self.feet_pos.x - prev_feet_pos.x, self.feet_pos.z - prev_feet_pos.z))
            is_walking = self.on_ground and actual_move_dist > 0.0001
            if is_walking:
                self.step_counter += actual_move_dist * 2.5
                bob_offset = glm.sin(self.step_counter) * 0.05

                current_time = pg.time.get_ticks()
                if current_time - self.last_step_time > 400: # ms between steps
                    self.app.sounds.play_hit(voxel_under)
                    self.last_step_time = current_time
                    
            # Dynamic FOV for sprinting
            target_fov = V_FOV + glm.radians(10.0) if self.is_sprinting and is_walking else V_FOV
            self.fov += (target_fov - self.fov) * 0.08 * self.app.delta_time
            self.m_proj = glm.perspective(self.fov, ASPECT_RATIO, NEAR, FAR)
            h_fov = 2 * math.atan(math.tan(self.fov * 0.5) * ASPECT_RATIO)
            self.frustum.update_factors(self.fov, h_fov)

            self.position = self.feet_pos + glm.vec3(0, PLAYER_EYE_HEIGHT + bob_offset, 0)
            
            self.handle_interaction()

            # Void fall prevention
            if self.position.y < -20:
                self.feet_pos = glm.vec3(PLAYER_POS)
                self.position = self.feet_pos + glm.vec3(0, PLAYER_EYE_HEIGHT, 0)
                self.velocity = glm.vec3(0)
        super().update()

    def handle_event(self, event):
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_f:
                self.free_fly = not self.free_fly
                if self.free_fly:
                    # sync feet to camera when entering free fly
                    self.feet_pos = glm.vec3(self.position)
                    self.velocity = glm.vec3(0)
                else:
                    # sync camera to feet when exiting free fly
                    self.feet_pos = glm.vec3(self.position)
                    self.velocity = glm.vec3(0)
            
            # Hotbar numbers 1-9
            if pg.K_1 <= event.key <= pg.K_9:
                self.hotbar_index = event.key - pg.K_1
                
        # adding and removing voxels with clicks
        if event.type == pg.MOUSEBUTTONDOWN:
            voxel_handler = self.app.scene.world.voxel_handler
            if event.button == 3: # Right click to place
                voxel_handler.set_voxel(mode='add')
                self.interaction_timer = pg.time.get_ticks()
            if event.button == 4:  # Scroll Up
                self.hotbar_index = (self.hotbar_index - 1) % 9
            if event.button == 5:  # Scroll Down
                self.hotbar_index = (self.hotbar_index + 1) % 9

    def mouse_control(self):
        mouse_dx, mouse_dy = pg.mouse.get_rel()
        if mouse_dx:
            self.rotate_yaw(delta_x=mouse_dx * MOUSE_SENSITIVITY)
        if mouse_dy:
            self.rotate_pitch(delta_y=mouse_dy * MOUSE_SENSITIVITY)

    def handle_interaction(self):
        mouse_pressed = pg.mouse.get_pressed()
        voxel_handler = self.app.scene.world.voxel_handler
        
        current_time = pg.time.get_ticks()
        
        # Mining logic (Left click)
        if mouse_pressed[0] and voxel_handler.voxel_id:
            if self.target_voxel_pos == voxel_handler.voxel_world_pos:
                self.mining_time += self.app.delta_time
                self.app.sounds.play_mining(voxel_handler.voxel_id, self.mining_time, self.mining_duration)
                if self.mining_time >= self.mining_duration:
                    voxel_handler.set_voxel(mode='remove')
                    self.mining_time = 0.0
            else:
                self.target_voxel_pos = voxel_handler.voxel_world_pos
                self.mining_time = 0.0
                self.mining_duration = BLOCK_HARDNESS.get(voxel_handler.voxel_id, 600.0)
                self.app.sounds.play_mining(voxel_handler.voxel_id, self.mining_time, self.mining_duration)
        else:
            self.mining_time = 0.0
            
        # Placing logic (Right click)
        if mouse_pressed[2]:
            if current_time - self.interaction_timer > self.interaction_delay:
                voxel_handler.set_voxel(mode='add')
                self.interaction_timer = current_time

    def keyboard_control(self):
        if self.free_fly:
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
            if key_state[pg.K_q]:
                self.move_up(vel)
            if key_state[pg.K_e]:
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
                speed *= 1.5
                self.is_sprinting = True
            self.velocity.x = move_dir.x * speed
            self.velocity.z = move_dir.z * speed
            if self.on_ground and keys[pg.K_SPACE]:
                self.velocity.y = JUMP_VELOCITY
                self.on_ground = False

    def apply_gravity(self):
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
                    if not voxel_id:
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
        for i in range(9):
            if self.hotbar[i] == voxel_id:
                self.hotbar_counts[i] += 1
                return True
        # Find an empty slot
        for i in range(9):
            if self.hotbar[i] == 0:
                self.hotbar[i] = voxel_id
                self.hotbar_counts[i] = 1
                return True
        return False # Inventory is full!

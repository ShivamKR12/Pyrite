import re

with open('src/player.py', 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
cleaned_lines = []
for line in lines:
    if re.match(r'^\s*#\s*=+\s*$', line):
        continue
    if re.match(r'^\s*#\s*REAL-WORLD CONTEXT:\s*', line):
        continue
    cleaned_lines.append(line)

content = '\n'.join(cleaned_lines)

new_methods = '''    def move_and_collide(self) -> None:
        """
        Moves the player incrementally along the X, Y, and Z axes,
        resolving collision clipping individually for each axis.
        """
        # Step 1: Apply velocity along the X-axis by multiplying by the frame delta time.
        # This isolates horizontal movement to independently solve X-axis collisions.
        self.feet_pos.x += self.velocity.x * self.app.delta_time
        self.resolve_axis('x')

        # Step 2: Apply velocity along the Y-axis (gravity/jumping).
        # We process Y independently so that a player can slide along a wall (X/Z) while falling (Y).
        self.feet_pos.y += self.velocity.y * self.app.delta_time
        self.resolve_axis('y')

        # Step 3: Apply velocity along the Z-axis.
        # This completes the 3D movement step by checking depth collisions.
        self.feet_pos.z += self.velocity.z * self.app.delta_time
        self.resolve_axis('z')

    @global_profiler.profile_func('Player_ResolveAxis')
    def resolve_axis(self, axis: str) -> None:
        """
        Checks for intersection between the player's AABB and the surrounding
        solid voxels. Stops the player's velocity along the tested axis if
        a collision is detected to prevent clipping.
        """
        # If the player is not moving along this axis, there is no new collision to resolve.
        if getattr(self.velocity, axis) == 0:
            return

        aabb_min: Any
        aabb_max: Any
        # Retrieve the player's current Axis-Aligned Bounding Box (AABB) using the updated position.
        # The AABB is defined by a minimum corner (x,y,z) and a maximum corner (x,y,z).
        aabb_min, aabb_max = self.get_aabb()

        # To find which grid voxels the player's continuous (float) AABB overlaps, we apply the floor function.
        # glm.floor() maps float coordinates down to the nearest integer grid coordinates.
        # This restricts our collision check to the discrete set of voxel coordinates the player touches.
        min_x: int = int(glm.floor(aabb_min.x))
        max_x: int = int(glm.floor(aabb_max.x))
        min_y: int = int(glm.floor(aabb_min.y))
        max_y: int = int(glm.floor(aabb_max.y))
        min_z: int = int(glm.floor(aabb_min.z))
        max_z: int = int(glm.floor(aabb_max.z))

        # We optimize the search volume by only checking the leading face of the player's AABB
        # along the axis of movement. If moving positively, we only check the 'max' face.
        if axis == 'x':
            if self.velocity.x > 0:
                min_x = max_x
            else:
                max_x = min_x
        elif axis == 'y':
            if self.velocity.y > 0:
                min_y = max_y
            else:
                max_y = min_y
        elif axis == 'z':
            if self.velocity.z > 0:
                min_z = max_z
            else:
                max_z = min_z

        world: Any = self.app.scene.world

        # Iterate strictly over the calculated subset of voxels that could potentially cause a collision.
        # This reduces our collision tests from millions of voxels down to usually 1-4 per axis.
        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                for z in range(min_z, max_z + 1):
                    voxel_id: int
                    # Query the global world array to get the block ID at this integer coordinate.
                    voxel_id, *_ = world.voxel_handler.get_voxel_id(glm.ivec3(x, y, z))

                    # If the block is empty (air/None) or non-solid (WATER), it does not cause collision.
                    if not voxel_id or voxel_id == WATER:
                        continue

                    # Define the voxel's AABB. Since voxels are 1x1x1 cubes on integer grids,
                    # the min bounds are exactly (x, y, z) and max bounds are exactly (x+1, y+1, z+1).
                    voxel_min: Any = glm.vec3(x, y, z)
                    voxel_max: Any = voxel_min + 1

                    # Check mathematically if the player's AABB overlaps with the voxel's AABB.
                    if self.aabb_intersect(aabb_min, aabb_max, voxel_min, voxel_max):
                        # If a collision occurred on the X-axis...
                        if axis == 'x':
                            if self.velocity.x > 0:
                                # We are moving right. Snap the player's feet_pos precisely outside the left face
                                # of the voxel by subtracting PLAYER_HALF_W.
                                self.feet_pos.x = voxel_min.x - PLAYER_HALF_W
                            else:
                                # We are moving left. Snap the player's feet_pos outside the right face.
                                self.feet_pos.x = voxel_max.x + PLAYER_HALF_W
                            # Nullify the velocity so the player stops penetrating the block.
                            self.velocity.x = 0

                        # If a collision occurred on the Y-axis...
                        elif axis == 'y':
                            if self.velocity.y > 0:
                                # Moving up (jumping). Snap position just below the ceiling block's bottom face.
                                self.feet_pos.y = voxel_min.y - PLAYER_HEIGHT
                            else:
                                # Moving down (falling). Snap position perfectly atop the floor block.
                                self.feet_pos.y = voxel_max.y
                                # Because we hit the floor, update state so the player can jump again.
                                self.on_ground = True
                            # Cancel Y velocity (gravity stops accumulating when standing).
                            self.velocity.y = 0

                        # If a collision occurred on the Z-axis...
                        elif axis == 'z':
                            if self.velocity.z > 0:
                                # Moving forward. Snap position behind the voxel's front face.
                                self.feet_pos.z = voxel_min.z - PLAYER_HALF_W
                            else:
                                # Moving backward. Snap position in front of the voxel's back face.
                                self.feet_pos.z = voxel_max.z + PLAYER_HALF_W
                            # Cancel Z velocity to halt depth penetration.
                            self.velocity.z = 0

                        # After resolving the collision and shifting feet_pos, recalculate the AABB.
                        # This updated bounding box is essential if the loop continues, as the player
                        # might still be penetrating other blocks (e.g. corner cases).
                        aabb_min, aabb_max = self.get_aabb()'''

pattern = re.compile(
    r'    def move_and_collide.*?(?=    @global_profiler\.profile_func\(' 'Player_GetAABB' r'\))', re.DOTALL
)
content = pattern.sub(new_methods + '\n\n', content)

with open('src/player.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated player.py successfully!')

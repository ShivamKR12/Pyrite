"""
3D Camera representation and mathematical matrix manipulation.

This module handles the player's perspective, generating the View and Projection
matrices required by OpenGL to render the world. It provides movement vectors
and rotational controls for exploring the 3D voxel space.
"""

from typing import Any

from frustum import Frustum
from profiler import global_profiler
from settings import ASPECT_RATIO, FAR, NEAR, PITCH_MAX, VERTICAL_FOV, glm


class Camera:
    """
    Represents a 3D camera in the world.

    Handles position, orientation (yaw/pitch), view matrix calculation,
    and movement direction vectors for navigating the voxel environment.

    Args:
        position (Any): Initial (x, y, z) 3D coordinate vector.
        yaw (float): Initial horizontal rotation in degrees.
        pitch (float): Initial vertical rotation in degrees.
    """

    @global_profiler.profile_func('Camera_Init')
    def __init__(self, position: Any, yaw: float, pitch: float) -> None:
        """
        Initializes the camera at a given position and orientation, and creates
        the perspective projection matrix and viewing frustum.
        """
        self.position: Any = glm.vec3(position)
        self.yaw: float = float(glm.radians(yaw))
        self.pitch: float = float(glm.radians(pitch))

        self.up: Any = glm.vec3(0, 1, 0)
        self.right: Any = glm.vec3(1, 0, 0)
        self.forward: Any = glm.vec3(0, 0, -1)

        self.m_proj: Any = glm.perspective(VERTICAL_FOV, ASPECT_RATIO, NEAR, FAR)
        self.m_view: Any = glm.mat4()

        self.frustum: Frustum = Frustum(self)

    @global_profiler.profile_func('Camera_Update')
    def update(self) -> None:
        """
        Updates the camera's directional vectors and view matrix for the current frame.
        """
        self.update_vectors()
        self.update_view_matrix()

    @global_profiler.profile_func('Camera_UpdateViewMatrix')
    def update_view_matrix(self) -> None:
        """
        Calculates the OpenGL lookAt view matrix based on the camera's position and forward vector.
        """
        self.m_view = glm.lookAt(self.position, self.position + self.forward, self.up)

    # ============================================================================
    # Euler Angles & Spherical Coordinates (3D Camera Math)
    # ============================================================================
    # How does moving the mouse translate into a 3D looking direction?
    # This function converts "Euler Angles" (Yaw and Pitch in radians) into a 
    # 3D directional vector (self.forward) using Spherical Coordinates trigonometry.
    #
    # How it works:
    # 1. Forward Vector: We use `cos()` and `sin()` to project a 3D sphere onto
    #    the X, Y, and Z axes based on where the player is looking. 
    # 2. Right Vector: We use a "Cross Product" between our new Forward vector 
    #    and the absolute World Up vector (0, 1, 0). The cross product mathematically 
    #    returns a 3D vector that is perfectly perpendicular to both, giving us 
    #    our "Right" direction!
    # 3. Up Vector: We do one last cross product between Right and Forward to get
    #    the camera's local "Up" direction.
    #
    # References:
    # - Camera Math Tutorial: https://learnopengl.com/Getting-started/Camera
    # - Cross Product visualizer: https://en.wikipedia.org/wiki/Cross_product
    # ============================================================================
    @global_profiler.profile_func('Camera_UpdateVectors')
    def update_vectors(self) -> None:
        """
        Recalculates the forward, right, and up vectors using spherical coordinates
        derived from the current yaw and pitch.
        """
        # ====================================================================
        # SPHERICAL TO CARTESIAN CONVERSION (X-AXIS)
        # To find how much we are looking left/right (X), we use `cos(yaw)`. 
        # But if we look straight up or down, the X length should shrink to 0. 
        # So we multiply it by `cos(pitch)`.
        # ====================================================================
        self.forward.x = glm.cos(self.yaw) * glm.cos(self.pitch)
        
        # ====================================================================
        # SPHERICAL TO CARTESIAN CONVERSION (Y-AXIS)
        # The vertical Y axis is purely controlled by the Pitch (looking up/down). 
        # `sin(pitch)` returns exactly 1.0 when looking straight up (90 degrees), 
        # 0.0 when looking flat (0 degrees), and -1.0 when looking down.
        # ====================================================================
        self.forward.y = glm.sin(self.pitch)
        
        # ====================================================================
        # SPHERICAL TO CARTESIAN CONVERSION (Z-AXIS)
        # Similar to X, the Z (depth) axis is controlled by `sin(yaw)`. 
        # It must also be scaled by `cos(pitch)` so that looking straight up/down 
        # completely nullifies depth movement.
        # ====================================================================
        self.forward.z = glm.sin(self.yaw) * glm.cos(self.pitch)

        # ====================================================================
        # VECTOR NORMALIZATION
        # `glm.normalize` ensures the Forward vector's total length is exactly 1.0. 
        # If we didn't normalize, moving diagonally might be faster than moving straight!
        # ====================================================================
        self.forward = glm.normalize(self.forward)
        
        # ====================================================================
        # THE CROSS PRODUCT (CALCULATING 'RIGHT')
        # We know which way we are looking (Forward), and we know which way is 
        # the sky (World Up: 0, 1, 0). The `cross` product of these two vectors 
        # generates a 3rd vector that is exactly perpendicular (90 degrees) to both.
        # This gives us our exact 'Right' vector for strafing left/right!
        # ====================================================================
        self.right = glm.normalize(glm.cross(self.forward, glm.vec3(0, 1, 0)))
        
        # ====================================================================
        # THE CROSS PRODUCT (CALCULATING 'LOCAL UP')
        # We cross 'Right' and 'Forward' to get our Local 'Up' vector. 
        # This is used so if we look down, 'Up' correctly points behind our head 
        # instead of straight into the sky. This is crucial for the OpenGL lookAt matrix.
        # ====================================================================
        self.up = glm.normalize(glm.cross(self.right, self.forward))

    @global_profiler.profile_func('Camera_RotatePitch')
    def rotate_pitch(self, delta_y: float) -> None:
        """
        Adjusts the camera's pitch (up/down rotation), clamping it to prevent flipping over.
        """
        self.pitch -= delta_y
        self.pitch = float(glm.clamp(self.pitch, -PITCH_MAX, PITCH_MAX))

    @global_profiler.profile_func('Camera_RotateYaw')
    def rotate_yaw(self, delta_x: float) -> None:
        """
        Adjusts the camera's yaw (left/right rotation).
        """
        self.yaw += delta_x

    @global_profiler.profile_func('Camera_MoveLeft')
    def move_left(self, velocity: float) -> None:
        """
        Translates the camera leftward along its right vector.
        """
        self.position -= self.right * velocity

    @global_profiler.profile_func('Camera_MoveRight')
    def move_right(self, velocity: float) -> None:
        """
        Translates the camera rightward along its right vector.
        """
        self.position += self.right * velocity

    @global_profiler.profile_func('Camera_MoveUp')
    def move_up(self, velocity: float) -> None:
        """
        Translates the camera upward along its up vector.
        """
        self.position += self.up * velocity

    @global_profiler.profile_func('Camera_MoveDown')
    def move_down(self, velocity: float) -> None:
        """
        Translates the camera downward along its up vector.
        """
        self.position -= self.up * velocity

    @global_profiler.profile_func('Camera_MoveForward')
    def move_forward(self, velocity: float) -> None:
        """
        Translates the camera forward along its forward vector.
        """
        self.position += self.forward * velocity

    @global_profiler.profile_func('Camera_MoveBack')
    def move_back(self, velocity: float) -> None:
        """
        Translates the camera backward along its forward vector.
        """
        self.position -= self.forward * velocity

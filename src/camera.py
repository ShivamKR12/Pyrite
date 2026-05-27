from settings import *
from frustum import Frustum
from profiler import global_profiler


class Camera:
    """
    Represents a 3D camera in the world.
    Handles position, orientation (yaw/pitch), view matrix calculation,
    and movement direction vectors.
    """
    @global_profiler.profile_func("Camera_Init")
    def __init__(self, position, yaw, pitch):
        """
        Initializes the camera at a given position and orientation, and creates 
        the perspective projection matrix and viewing frustum.
        """
        self.position = glm.vec3(position)
        self.yaw = glm.radians(yaw)
        self.pitch = glm.radians(pitch)

        self.up = glm.vec3(0, 1, 0)
        self.right = glm.vec3(1, 0, 0)
        self.forward = glm.vec3(0, 0, -1)

        self.m_proj = glm.perspective(V_FOV, ASPECT_RATIO, NEAR, FAR)
        self.m_view = glm.mat4()

        self.frustum = Frustum(self)

    @global_profiler.profile_func("Camera_Update")
    def update(self):
        """
        Updates the camera's directional vectors and view matrix for the current frame.
        """
        self.update_vectors()
        self.update_view_matrix()

    @global_profiler.profile_func("Camera_UpdateViewMatrix")
    def update_view_matrix(self):
        """
        Calculates the OpenGL lookAt view matrix based on the camera's position and forward vector.
        """
        self.m_view = glm.lookAt(self.position, self.position + self.forward, self.up)

    @global_profiler.profile_func("Camera_UpdateVectors")
    def update_vectors(self):
        """
        Recalculates the forward, right, and up vectors using spherical coordinates
        derived from the current yaw and pitch.
        """
        self.forward.x = glm.cos(self.yaw) * glm.cos(self.pitch)
        self.forward.y = glm.sin(self.pitch)
        self.forward.z = glm.sin(self.yaw) * glm.cos(self.pitch)

        self.forward = glm.normalize(self.forward)
        self.right = glm.normalize(glm.cross(self.forward, glm.vec3(0, 1, 0)))
        self.up = glm.normalize(glm.cross(self.right, self.forward))

    @global_profiler.profile_func("Camera_RotatePitch")
    def rotate_pitch(self, delta_y):
        """
        Adjusts the camera's pitch (up/down rotation), clamping it to prevent flipping over.
        """
        self.pitch -= delta_y
        self.pitch = glm.clamp(self.pitch, -PITCH_MAX, PITCH_MAX)

    @global_profiler.profile_func("Camera_RotateYaw")
    def rotate_yaw(self, delta_x):
        """
        Adjusts the camera's yaw (left/right rotation).
        """
        self.yaw += delta_x

    @global_profiler.profile_func("Camera_MoveLeft")
    def move_left(self, velocity):
        """
        Translates the camera leftward along its right vector.
        """
        self.position -= self.right * velocity

    @global_profiler.profile_func("Camera_MoveRight")
    def move_right(self, velocity):
        """
        Translates the camera rightward along its right vector.
        """
        self.position += self.right * velocity

    @global_profiler.profile_func("Camera_MoveUp")
    def move_up(self, velocity):
        """
        Translates the camera upward along its up vector.
        """
        self.position += self.up * velocity

    @global_profiler.profile_func("Camera_MoveDown")
    def move_down(self, velocity):
        """
        Translates the camera downward along its up vector.
        """
        self.position -= self.up * velocity

    @global_profiler.profile_func("Camera_MoveForward")
    def move_forward(self, velocity):
        """
        Translates the camera forward along its forward vector.
        """
        self.position += self.forward * velocity

    @global_profiler.profile_func("Camera_MoveBack")
    def move_back(self, velocity):
        """
        Translates the camera backward along its forward vector.
        """
        self.position -= self.forward * velocity

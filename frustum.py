from settings import *


class Frustum:
    def __init__(self, camera):
        self.cam: Camera = camera # type: ignore
        self.update_factors(V_FOV, H_FOV)
        
    def update_factors(self, v_fov, h_fov):
        self.factor_y = 1.0 / math.cos(half_y := v_fov * 0.5)
        self.tan_y = math.tan(half_y)

        self.factor_x = 1.0 / math.cos(half_x := h_fov * 0.5)
        self.tan_x = math.tan(half_x)

    def is_on_frustum(self, chunk):
        # vector to sphere center
        sphere_vec = chunk.center - self.cam.position

        # outside the NEAR and FAR planes?
        sz = glm.dot(sphere_vec, self.cam.forward)
        if not (NEAR - CHUNK_SPHERE_RADIUS <= sz <= FAR + CHUNK_SPHERE_RADIUS):
            return False

        # outside the TOP and BOTTOM planes?
        sy = glm.dot(sphere_vec, self.cam.up)
        dist = self.factor_y * CHUNK_SPHERE_RADIUS + sz * self.tan_y
        if not (-dist <= sy <= dist):
            return False

        # outside the LEFT and RIGHT planes?
        sx = glm.dot(sphere_vec, self.cam.right)
        dist = self.factor_x * CHUNK_SPHERE_RADIUS + sz * self.tan_x
        if not (-dist <= sx <= dist):
            return False

        return True

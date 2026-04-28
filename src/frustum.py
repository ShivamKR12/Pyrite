from settings import *
from numba import njit, prange
import numpy as np
from pyglm import glm


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


@njit(cache=True, fastmath=True, parallel=True)
def frustum_cull_fast(chunk_centers, cam_pos, cam_forward, cam_right, cam_up, tan_y, tan_x, factor_y, factor_x):
    n = len(chunk_centers)
    is_visible = np.empty(n, dtype=np.bool_)

    cpx, cpy, cpz = cam_pos[0], cam_pos[1], cam_pos[2]
    cfx, cfy, cfz = cam_forward[0], cam_forward[1], cam_forward[2]
    crx, cry, crz = cam_right[0], cam_right[1], cam_right[2]
    cux, cuy, cuz = cam_up[0], cam_up[1], cam_up[2]

    radius_sq = (CHUNK_SPHERE_RADIUS * 1.2) ** 2

    for i in prange(n):
        svx = chunk_centers[i, 0] - cpx
        svy = chunk_centers[i, 1] - cpy
        svz = chunk_centers[i, 2] - cpz
        
        dist_sq = svx*svx + svy*svy + svz*svz
        if dist_sq < radius_sq:
            is_visible[i] = True
            continue

        sz = svx * cfx + svy * cfy + svz * cfz
        if not (NEAR - CHUNK_SPHERE_RADIUS <= sz <= FAR + CHUNK_SPHERE_RADIUS):
            is_visible[i] = False
            continue
            
        sz = max(0.0, sz)

        sy = svx * cux + svy * cuy + svz * cuz
        dist_y = factor_y * CHUNK_SPHERE_RADIUS + sz * tan_y
        if not (-dist_y <= sy <= dist_y):
            is_visible[i] = False
            continue

        sx = svx * crx + svy * cry + svz * crz
        dist_x = factor_x * CHUNK_SPHERE_RADIUS + sz * tan_x
        if not (-dist_x <= sx <= dist_x):
            is_visible[i] = False
            continue
            
        is_visible[i] = True
            
    return is_visible

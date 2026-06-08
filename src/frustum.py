"""
Frustum culling for efficient 3D rendering.

This module provides both an object-oriented Frustum class for individual
tests and a highly optimized, Numba-compiled vectorized function for
testing thousands of chunks simultaneously against the camera's view frustum.
"""

import math
from typing import Any

from numba import njit, prange
from pyglm import glm

from profiler import global_profiler
from settings import CHUNK_SPHERE_RADIUS, FAR, H_FOV, NEAR, V_FOV


class Frustum:
    """
    Calculates the camera's viewing frustum planes and boundaries dynamically
    based on the Field of View and Aspect Ratio.

    Args:
        camera (Any): The main camera instance tracking the player's perspective.
    """

    @global_profiler.profile_func('Frustum_Init')
    def __init__(self, camera: Any) -> None:
        """
        Initialize the Frustum for a given camera instance.

        Computes and stores precomputed tangent/factor values used for
        frustum checks and keeps a reference to the camera object.
        """
        self.cam: Any = camera
        self.factor_y: float = 0.0
        self.tan_y: float = 0.0
        self.factor_x: float = 0.0
        self.tan_x: float = 0.0
        self.update_factors(V_FOV, H_FOV)

    @global_profiler.profile_func('Frustum_UpdateFactors')
    def update_factors(self, v_fov: float, h_fov: float) -> None:
        """
        Recalculate cached tangent/factor values from vertical and horizontal FOV.

        Args:
            v_fov: Vertical field-of-view in radians.
            h_fov: Horizontal field-of-view in radians.
        """
        self.factor_y = 1.0 / math.cos(half_y := v_fov * 0.5)
        self.tan_y = math.tan(half_y)

        self.factor_x = 1.0 / math.cos(half_x := h_fov * 0.5)
        self.tan_x = math.tan(half_x)

    @global_profiler.profile_func('Frustum_IsOnFrustum')
    def is_on_frustum(self, chunk: Any) -> bool:
        """
        Determine whether the given chunk's bounding sphere intersects the view frustum.

        Args:
            chunk: Object with a `center` attribute representing 3D position.

        Returns:
            True if the chunk is (partially) inside the camera frustum, False otherwise.
        """
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


@njit(cache=True, fastmath=True, parallel=True, nogil=True)
def frustum_cull_fast(
    chunk_centers: Any,
    out_mask: Any,
    cam_pos: Any,
    cam_forward: Any,
    cam_right: Any,
    cam_up: Any,
    tan_y: float,
    tan_x: float,
    factor_y: float,
    factor_x: float,
) -> Any:
    """
    Numba-optimized vectorized frustum culling.

    Args:
        chunk_centers: Nx3 array of chunk center coordinates.
        out_mask: Preallocated boolean array that will be written with visibility flags.
        cam_pos: Camera position (3,) array.
        cam_forward: Camera forward vector (3,) array.
        cam_right: Camera right vector (3,) array.
        cam_up: Camera up vector (3,) array.
        tan_y: Tangent of half-vertical FOV.
        tan_x: Tangent of half-horizontal FOV.
        factor_y: Precomputed vertical factor used for bounds checks.
        factor_x: Precomputed horizontal factor used for bounds checks.

    Returns:
        The `out_mask` array with booleans indicating visibility for each center.
    """
    n = len(chunk_centers)

    cpx, cpy, cpz = cam_pos[0], cam_pos[1], cam_pos[2]
    cfx, cfy, cfz = cam_forward[0], cam_forward[1], cam_forward[2]
    crx, cry, crz = cam_right[0], cam_right[1], cam_right[2]
    cux, cuy, cuz = cam_up[0], cam_up[1], cam_up[2]

    radius_sq = (CHUNK_SPHERE_RADIUS * 1.2) ** 2

    for i in prange(n):
        svx = chunk_centers[i, 0] - cpx
        svy = chunk_centers[i, 1] - cpy
        svz = chunk_centers[i, 2] - cpz

        dist_sq = svx * svx + svy * svy + svz * svz
        if dist_sq < radius_sq:
            out_mask[i] = True
            continue

        sz = svx * cfx + svy * cfy + svz * cfz
        if not (NEAR - CHUNK_SPHERE_RADIUS <= sz <= FAR + CHUNK_SPHERE_RADIUS):
            out_mask[i] = False
            continue

        sz = max(0.0, sz)

        sy = svx * cux + svy * cuy + svz * cuz
        dist_y = factor_y * CHUNK_SPHERE_RADIUS + sz * tan_y
        if not (-dist_y <= sy <= dist_y):
            out_mask[i] = False
            continue

        sx = svx * crx + svy * cry + svz * crz
        dist_x = factor_x * CHUNK_SPHERE_RADIUS + sz * tan_x
        if not (-dist_x <= sx <= dist_x):
            out_mask[i] = False
            continue

        out_mask[i] = True

    return out_mask

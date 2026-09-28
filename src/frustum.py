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
from settings import CHUNK_SPHERE_RADIUS, FAR, HORIZONTAL_FOV, NEAR, VERTICAL_FOV


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
        # Variable assignments
        self.cam: Any = camera
        self.factor_y: float = 0.0
        self.tangent_y: float = 0.0
        self.factor_x: float = 0.0
        self.tangent_x: float = 0.0
        # Execute expressions
        self.update_factors(VERTICAL_FOV, HORIZONTAL_FOV)

    @global_profiler.profile_func('Frustum_UpdateFactors')
    def update_factors(self, vertical_fov: float, horizontal_fov: float) -> None:
        """
        Recalculate cached tangent/factor values from vertical and horizontal FOV.

        Args:
            vertical_fov: Vertical field-of-view in radians.
            horizontal_fov: Horizontal field-of-view in radians.
        """
        # Variable assignments
        self.factor_y = 1.0 / math.cos(half_y := vertical_fov * 0.5)
        self.tangent_y = math.tan(half_y)

        self.factor_x = 1.0 / math.cos(half_x := horizontal_fov * 0.5)
        self.tangent_x = math.tan(half_x)

    @global_profiler.profile_func('Frustum_IsOnFrustum')
    def is_on_frustum(self, chunk: Any) -> bool:
        """
        Determine whether the given chunk's bounding sphere intersects the view frustum.

        Args:
            chunk: Object with a `center` attribute representing 3D position.

        Returns:
            True if the chunk is (partially) inside the camera frustum, False otherwise.
        """
        # Variable assignments
        sphere_vec = chunk.center - self.cam.position

        sz = glm.dot(sphere_vec, self.cam.forward)
        # Conditional logic
        if not (NEAR - CHUNK_SPHERE_RADIUS <= sz <= FAR + CHUNK_SPHERE_RADIUS):
            # Return result
            return False

        # Variable assignments
        sy = glm.dot(sphere_vec, self.cam.up)
        dist = self.factor_y * CHUNK_SPHERE_RADIUS + sz * self.tangent_y
        # Conditional logic
        if not (-dist <= sy <= dist):
            # Return result
            return False

        # Variable assignments
        sx = glm.dot(sphere_vec, self.cam.right)
        dist = self.factor_x * CHUNK_SPHERE_RADIUS + sz * self.tangent_x
        # Conditional logic
        if not (-dist <= sx <= dist):
            # Return result
            return False

        # Return result
        return True


# ============================================================================
# REAL-WORLD CONTEXT: Camera Frustum Culling (3D Math)
# ============================================================================
# This function determines which chunks the player can actually see so we don't
# waste time rendering chunks behind their head.
#
# How it works:
# The "Frustum" is a 3D pyramid shape representing the camera's field of view.
# To check if a chunk is inside this pyramid, we calculate the dot product of
# the vector pointing from the camera to the chunk against the camera's Up,
# Right, and Forward vectors.
#
# Using basic trigonometry (tangent of the Field of View), we define planes
# for the Left, Right, Top, Bottom, Near, and Far boundaries. If the chunk's
# bounding sphere is completely outside any of these planes, it gets "culled"
# (removed from the render queue).
#
# References:
# - Dot Product in 3D: https://en.wikipedia.org/wiki/Dot_product
# - Frustum Culling Math: https://learnopengl.com/Guest-Articles/2021/Scene/Frustum-Culling
# ============================================================================


@njit(cache=True, fastmath=True, parallel=True, nogil=True)
def frustum_cull_fast(
    chunk_centers: Any,
    out_mask: Any,
    camera_position: Any,
    camera_forward: Any,
    camera_right: Any,
    camera_up: Any,
    tangent_y: float,
    tangent_x: float,
    factor_y: float,
    factor_x: float,
) -> Any:
    """
    Numba-optimized vectorized frustum culling.

    Args:
        chunk_centers: Nx3 array of chunk center coordinates.
        out_mask: Preallocated boolean array that will be written with visibility flags.
        camera_position: Camera position (3,) array.
        camera_forward: Camera forward vector (3,) array.
        camera_right: Camera right vector (3,) array.
        camera_up: Camera up vector (3,) array.
        tangent_y: Tangent of half-vertical FOV.
        tangent_x: Tangent of half-horizontal FOV.
        factor_y: Precomputed vertical factor used for bounds checks.
        factor_x: Precomputed horizontal factor used for bounds checks.

    Returns:
        The `out_mask` array with booleans indicating visibility for each center.
    """
    # Variable assignments
    n = len(chunk_centers)

    cpx, cpy, cpz = camera_position[0], camera_position[1], camera_position[2]
    cfx, cfy, cfz = camera_forward[0], camera_forward[1], camera_forward[2]
    crx, cry, crz = camera_right[0], camera_right[1], camera_right[2]
    cux, cuy, cuz = camera_up[0], camera_up[1], camera_up[2]

    radius_sq = (CHUNK_SPHERE_RADIUS * 1.2) ** 2

    # Loop processing
    for i in prange(n):
        # Variable assignments
        svx = chunk_centers[i, 0] - cpx
        svy = chunk_centers[i, 1] - cpy
        svz = chunk_centers[i, 2] - cpz

        dist_sq = svx * svx + svy * svy + svz * svz
        # Conditional logic
        if dist_sq < radius_sq:
            # Variable assignments
            out_mask[i] = True
            # Loop control
            continue

        # Variable assignments
        sz = svx * cfx + svy * cfy + svz * cfz
        # Conditional logic
        if not (NEAR - CHUNK_SPHERE_RADIUS <= sz <= FAR + CHUNK_SPHERE_RADIUS):
            # Variable assignments
            out_mask[i] = False
            # Loop control
            continue

        # Variable assignments
        sz = max(0.0, sz)

        sy = svx * cux + svy * cuy + svz * cuz
        dist_y = factor_y * CHUNK_SPHERE_RADIUS + sz * tangent_y
        # Conditional logic
        if not (-dist_y <= sy <= dist_y):
            # Variable assignments
            out_mask[i] = False
            # Loop control
            continue

        # Variable assignments
        sx = svx * crx + svy * cry + svz * crz
        dist_x = factor_x * CHUNK_SPHERE_RADIUS + sz * tangent_x
        # Conditional logic
        if not (-dist_x <= sx <= dist_x):
            # Variable assignments
            out_mask[i] = False
            # Loop control
            continue

        # Variable assignments
        out_mask[i] = True

    # Return result
    return out_mask

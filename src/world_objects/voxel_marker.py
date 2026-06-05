"""
Dynamic 3D cursor block highlighting.

This module tracks the player's active raycast target via the voxel handler and
renders a real-time floating 3D wireframe box. It shifts its position dynamically
based on whether the player is currently aiming to break a block or place a new
one attached to a targeted face.
"""

from typing import Any
from pyglm import glm

from meshes.cube_mesh import CubeMesh
from profiler import global_profiler


class VoxelMarker:
    """
    Renders a 3D wireframe highlight around the voxel currently targeted by the player.

    It tracks the voxel handler's targeted position and visually outlines it.
    The marker adapts its position dynamically based on the interaction mode (breaking vs. placing).

    Args:
        voxel_handler (Any): The world's voxel handler instance tracking player raycasts.
    """

    @global_profiler.profile_func('VoxelMarker_Init')
    def __init__(self, voxel_handler: Any) -> None:
        """
        Initializes the voxel marker, binding it to the world's voxel handler
        and preparing its wireframe cube mesh.
        """
        self.app: Any = voxel_handler.app
        self.handler: Any = voxel_handler
        self.position: Any = glm.vec3(0)
        self.m_model: Any = self.get_model_matrix()
        self.mesh: Any = CubeMesh(self.app)

    @global_profiler.profile_func('VoxelMarker_Update')
    def update(self) -> None:
        """
        Updates the marker's 3D position to match the currently targeted voxel.
        Adjusts position based on whether the player is aiming to break or place a block.
        """
        if self.handler.voxel_id:
            if self.handler.interaction_mode:
                self.position = self.handler.voxel_world_pos + self.handler.voxel_normal
            else:
                self.position = self.handler.voxel_world_pos

    @global_profiler.profile_func('VoxelMarker_SetUniform')
    def set_uniform(self) -> None:
        """
        Sends the interaction mode and the calculated model transformation matrix
        to the voxel marker's shader program.
        """
        self.mesh.program['mode_id'] = self.handler.interaction_mode
        self.mesh.program['m_model'].write(self.get_model_matrix())

    @global_profiler.profile_func('VoxelMarker_GetModelMatrix')
    def get_model_matrix(self) -> Any:
        """
        Calculates the transformation matrix required to position the wireframe
        marker correctly at the targeted voxel's world space coordinates.
        """
        m_model: Any = glm.translate(glm.mat4(), glm.vec3(self.position))
        return m_model

    @global_profiler.profile_func('VoxelMarker_Render')
    def render(self) -> None:
        """
        Issues the draw call for the wireframe cube if the player is actively
        targeting a valid block in the world.
        """
        if self.handler.voxel_id:
            self.set_uniform()
            self.mesh.render()

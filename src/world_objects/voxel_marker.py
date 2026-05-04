from settings import *
from meshes.cube_mesh import CubeMesh


class VoxelMarker:
    """
    Renders a 3D wireframe highlight around the voxel currently targeted by the player.
    It tracks the voxel handler's targeted position and visually outlines it.
    """
    def __init__(self, voxel_handler):
        """
        Initializes the voxel marker, binding it to the world's voxel handler
        and preparing its wireframe cube mesh.
        """
        self.app = voxel_handler.app
        self.handler = voxel_handler
        self.position = glm.vec3(0)
        self.m_model = self.get_model_matrix()
        self.mesh = CubeMesh(self.app)

    def update(self):
        """
        Updates the marker's 3D position to match the currently targeted voxel.
        Adjusts position based on whether the player is aiming to break or place a block.
        """
        if self.handler.voxel_id:
            if self.handler.interaction_mode:
                self.position = self.handler.voxel_world_pos + self.handler.voxel_normal
            else:
                self.position = self.handler.voxel_world_pos

    def set_uniform(self):
        """
        Sends the interaction mode and the calculated model transformation matrix
        to the voxel marker's shader program.
        """
        self.mesh.program['mode_id'] = self.handler.interaction_mode
        self.mesh.program['m_model'].write(self.get_model_matrix())

    def get_model_matrix(self):
        """
        Calculates the transformation matrix required to position the wireframe
        marker correctly at the targeted voxel's world space coordinates.
        """
        m_model = glm.translate(glm.mat4(), glm.vec3(self.position))
        return m_model

    def render(self):
        """
        Issues the draw call for the wireframe cube if the player is actively
        targeting a valid block in the world.
        """
        if self.handler.voxel_id:
            self.set_uniform()
            self.mesh.render()

"""
Procedural skybox and atmospheric background rendering.

This module generates the geometry for a full-screen quad that acts as the
canvas for the sky shader. The shader itself handles rendering the dynamic
day/night cycle, sun, moon, and stars directly behind all other 3D geometry.
"""

import numpy as np
import moderngl as mgl
from typing import Any, Tuple
from numpy.typing import NDArray

from meshes.base_mesh import BaseMesh
from profiler import global_profiler


class SkyMesh(BaseMesh):
    """
    Generates the geometry for the skybox, represented as a full-screen 2D quad.

    This mesh does not require complex 3D geometry because the sky is procedurally
    generated entirely in the fragment shader using ray direction calculations.

    Args:
        app (Any): The main application instance providing the ModernGL context.
    """

    @global_profiler.profile_func('SkyMesh_Init')
    def __init__(self, app: Any) -> None:
        """
        Initializes the sky mesh, binding it to the shader program responsible
        for rendering the atmosphere, sun, moon, and stars.
        """
        super().__init__()
        self.app: Any = app
        self.ctx: Any = app.ctx
        self.program: Any = app.shader_program.sky
        self.vbo_format: str = '2f'
        self.attrs: Tuple[str, ...] = ('in_position',)
        self.vao: Any = self.get_vao()

    @global_profiler.profile_func('SkyMesh_GetVertexData')
    def get_vertex_data(self) -> NDArray[np.float32]:
        """
        Returns the vertex coordinates for a full-screen quad spanning
        normalized device coordinates.
        """
        # Full screen quad spanning normalized device coordinates [-1, 1]
        return np.array([(-1.0, -1.0), (1.0, -1.0), (1.0, 1.0), (-1.0, -1.0), (1.0, 1.0), (-1.0, 1.0)], dtype='float32')


class Sky:
    """
    Manages the skybox object, handling the rendering of the atmospheric
    background and celestial bodies.

    Args:
        app (Any): The main application instance providing the ModernGL context.
    """

    @global_profiler.profile_func('Sky_Init')
    def __init__(self, app: Any) -> None:
        """
        Initializes the sky object and creates its associated full-screen quad mesh.
        """
        self.app: Any = app
        self.mesh: Any = SkyMesh(app)

    @global_profiler.profile_func('Sky_Render')
    def render(self) -> None:
        """
        Issues the draw call for the skybox. Temporarily disables depth testing
        to ensure the sky is drawn strictly behind all other 3D geometry.
        """
        self.app.ctx.disable(mgl.DEPTH_TEST)
        self.mesh.render()
        self.app.ctx.enable(mgl.DEPTH_TEST)

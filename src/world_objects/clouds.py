"""
Procedural skybox and cloud layer management.

This module initializes the dynamic sky environment and is responsible for
continuously passing updated session-time shader uniforms to animate the
wind-swept traversal of the volumetric cloud geometry.
"""

from typing import Any

from meshes.cloud_mesh import CloudMesh
from profiler import global_profiler


class Clouds:
    """
    Manages the procedural 3D cloud layer in the sky.

    Handles updating the time for cloud movement and rendering the cloud mesh.
    Provides the visual atmospheric layer that scrolls across the world origin.

    Args:
        app (Any): The main application instance providing the ModernGL context.
    """

    @global_profiler.profile_func('Clouds_Init')
    def __init__(self, app: Any) -> None:
        """
        Initializes the clouds object and generates its associated procedural mesh.
        """
        self.app: Any = app
        self.mesh: Any = CloudMesh(app)

    @global_profiler.profile_func('Clouds_Update')
    def update(self) -> None:
        """
        Updates the 'u_time' uniform in the cloud shader to animate their movement.
        """
        self.mesh.program['u_time'] = self.app.world_session_time

    @global_profiler.profile_func('Clouds_Render')
    def render(self) -> None:
        """
        Issues the draw call to render the 3D clouds.
        """
        self.mesh.render()

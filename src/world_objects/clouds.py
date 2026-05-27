from settings import *
from meshes.cloud_mesh import CloudMesh
from profiler import global_profiler


class Clouds:
    """
    Manages the procedural 3D cloud layer in the sky.
    Handles updating the time for cloud movement and rendering the cloud mesh.
    """
    @global_profiler.profile_func("Clouds_Init")
    def __init__(self, app):
        """
        Initializes the clouds object and generates its associated procedural mesh.
        """
        self.app = app
        self.mesh = CloudMesh(app)

    @global_profiler.profile_func("Clouds_Update")
    def update(self):
        """
        Updates the 'u_time' uniform in the cloud shader to animate their movement.
        """
        self.mesh.program['u_time'] = self.app.world_session_time

    @global_profiler.profile_func("Clouds_Render")
    def render(self):
        """
        Issues the draw call to render the 3D clouds.
        """
        self.mesh.render()

from settings import *
from meshes.cloud_mesh import CloudMesh


class Clouds:
    """
    Manages the procedural 3D cloud layer in the sky.
    Handles updating the time for cloud movement and rendering the cloud mesh.
    """
    def __init__(self, app):
        """
        Initializes the clouds object and generates its associated procedural mesh.
        """
        self.app = app
        self.mesh = CloudMesh(app)

    def update(self):
        """
        Updates the 'u_time' uniform in the cloud shader to animate their movement.
        """
        self.mesh.program['u_time'] = self.app.world_session_time

    def render(self):
        """
        Issues the draw call to render the 3D clouds.
        """
        self.mesh.render()

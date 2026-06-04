"""
ModernGL definitions for 2D User Interface element geometries.

This module implements the underlying mathematical layouts (vertices and UV coordinates)
for generating screen-space flat meshes. It provides the geometry structures for rendering 
the crosshair, the 2D scaled block inventory icons, text fonts, and solid-color backgrounds 
that compose the Pyrite game overlay.
"""

from typing import Any, Tuple
import numpy as np
from numpy.typing import NDArray

from meshes.base_mesh import BaseMesh
from profiler import global_profiler
from settings import ASPECT_RATIO


class CrosshairMesh(BaseMesh):
    """
    Generates the geometry for the on-screen crosshair.
    
    Draws a simple '+' sign directly in the center of the player's view,
    utilizing aspect-ratio scaling to remain perfectly proportioned.
    
    Args:
        app (Any): The main application context containing shaders and window properties.
    """
    @global_profiler.profile_func("CrosshairMesh_Init")
    def __init__(self, app: Any) -> None:
        """
        Initializes the crosshair mesh, binding it to the solid-color quad shader.
        """
        super().__init__()
        self.app: Any = app
        self.ctx: Any = self.app.ctx
        self.program: Any = self.app.shader_program.quad
        self.vbo_format: str = '3f 3f'
        self.attrs: Tuple[str, ...] = ('in_position', 'in_color')
        self.vao: Any = self.get_vao()

    @global_profiler.profile_func("CrosshairMesh_GetVertexData")
    def get_vertex_data(self) -> NDArray[np.float32]:
        """
        Calculates the vertex coordinates and color data needed to form the 
        horizontal and vertical lines of the crosshair, scaling it properly 
        to match the window's aspect ratio.
        """
        w = 0.015
        h = w * ASPECT_RATIO
        
        # Creates a perfect '+' sign in the center of the screen
        vertices = [
            # Horizontal line
            (-w, -0.002 * ASPECT_RATIO, 0.0), (w, -0.002 * ASPECT_RATIO, 0.0), (w, 0.002 * ASPECT_RATIO, 0.0),
            (-w, -0.002 * ASPECT_RATIO, 0.0), (w, 0.002 * ASPECT_RATIO, 0.0), (-w, 0.002 * ASPECT_RATIO, 0.0),
            # Vertical line
            (-0.002, -h, 0.0), (0.002, -h, 0.0), (0.002, h, 0.0),
            (-0.002, -h, 0.0), (0.002, h, 0.0), (-0.002, h, 0.0)
        ]
        
        colors = [(0.9, 0.9, 0.9) for _ in vertices]
        
        return np.hstack([vertices, colors]).astype('float32')


class BlockIconMesh(BaseMesh):
    """
    Handles the rendering geometry for 2D flat representations of 3D blocks.
    
    Used extensively in the Hotbar and Inventory UI slots. Produces a basic
    texture-mapped quad that the shader transforms dynamically into slots.
    
    Args:
        app (Any): The main application context.
    """
    @global_profiler.profile_func("BlockIconMesh_Init")
    def __init__(self, app: Any) -> None:
        """
        Initializes the block icon mesh and connects it to the block UI shader.
        """
        super().__init__()
        self.app: Any = app
        self.ctx: Any = self.app.ctx
        self.program: Any = self.app.shader_program.ui_block
        self.vbo_format: str = '2f 2f'
        self.attrs: Tuple[str, ...] = ('in_position', 'in_tex_coord')
        self.vao: Any = self.get_vao()

    @global_profiler.profile_func("BlockIconMesh_GetVertexData")
    def get_vertex_data(self) -> NDArray[np.float32]:
        """
        Returns the vertices and texture coordinates for a standard full-screen quad,
        which is later scaled and positioned by the shader based on uniform offsets.
        """
        # Standard normalized quad [-1, 1]
        vertices = [
            (-1.0, -1.0), ( 1.0, -1.0), ( 1.0,  1.0),
            (-1.0, -1.0), ( 1.0,  1.0), (-1.0,  1.0)
        ]
        
        tex_coords = [(0, 0), (1, 0), (1, 1), (0, 0), (1, 1), (0, 1)]
        
        return np.hstack([vertices, tex_coords]).astype('float32')


class UIColorMesh(BaseMesh):
    """
    Provides the geometry for rendering solid-color geometric elements in the UI.
    
    Used for rendering non-textured components such as backgrounds, frames, 
    selection highlights, and dimming overlays using flat-color shaders.
    
    Args:
        app (Any): The main application context.
    """
    @global_profiler.profile_func("UIColorMesh_Init")
    def __init__(self, app: Any) -> None:
        """
        Initializes the UI color mesh, attaching it to a simple shader that applies 
        flat color uniforms instead of textures.
        """
        super().__init__()
        self.app: Any = app
        self.ctx: Any = self.app.ctx
        self.program: Any = self.app.shader_program.ui_color
        self.vbo_format: str = '2f'
        self.attrs: Tuple[str, ...] = ('in_position',)
        self.vao: Any = self.get_vao()

    @global_profiler.profile_func("UIColorMesh_GetVertexData")
    def get_vertex_data(self) -> NDArray[np.float32]:
        """
        Returns the raw vertex positions for a 2D quad without texture coordinates, 
        as the shape relies solely on color uniforms.
        """
        vertices = [
            (-1.0, -1.0), ( 1.0, -1.0), ( 1.0,  1.0),
            (-1.0, -1.0), ( 1.0,  1.0), (-1.0,  1.0)
        ]
        
        return np.array(vertices, dtype='float32')


class UITextMesh(BaseMesh):
    """
    Generates the geometry required to display text strings on the screen.
    
    Acts as a surface to map dynamically generated text textures onto, utilizing 
    alpha-blended shaders to properly draw fonts over the background elements.
    
    Args:
        app (Any): The main application context.
    """
    @global_profiler.profile_func("UITextMesh_Init")
    def __init__(self, app: Any) -> None:
        """
        Initializes the UI text mesh, binding it to the text shader which handles 
        transparency and alpha blending for clean font rendering.
        """
        super().__init__()
        self.app: Any = app
        self.ctx: Any = self.app.ctx
        self.program: Any = self.app.shader_program.ui_text
        self.vbo_format: str = '2f 2f'
        self.attrs: Tuple[str, ...] = ('in_position', 'in_tex_coord')
        self.vao: Any = self.get_vao()

    @global_profiler.profile_func("UITextMesh_GetVertexData")
    def get_vertex_data(self) -> NDArray[np.float32]:
        """
        Returns the standard set of vertices and UV coordinates mapping a full 
        texture onto a simple 2D rectangular quad.
        """
        vertices = [
            (-1.0, -1.0), ( 1.0, -1.0), ( 1.0,  1.0),
            (-1.0, -1.0), ( 1.0,  1.0), (-1.0,  1.0)
        ]
        
        tex_coords = [(0, 0), (1, 0), (1, 1), (0, 0), (1, 1), (0, 1)]
        
        return np.hstack([vertices, tex_coords]).astype('float32')

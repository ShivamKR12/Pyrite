"""
Base class architecture for OpenGL mesh generation.

This module provides the foundational `BaseMesh` class that all 2D and 3D 
renderable objects in Pyrite inherit from. It standardizes the creation 
of Vertex Array Objects (VAOs) and Vertex Buffer Objects (VBOs) through 
the ModernGL pipeline.
"""

import numpy as np
from typing import Any, Tuple


class BaseMesh:
    """
    Abstract base class for all OpenGL geometry meshes.
    
    Subclasses must implement the `get_vertex_data` method to supply the raw 
    Numpy array data. The base class automatically handles uploading this data 
    to the GPU and configuring the vertex attributes for the shader program.
    """
    def __init__(self) -> None:
        """
        Initializes the empty mesh attributes. Subclasses should override these 
        with their specific ModernGL contexts, shaders, and VBO formats.
        """
        # OpenGL context
        self.ctx: Any = None
        
        # shader program
        self.program: Any = None
        
        # vertex buffer data type format: "3f 3f"
        self.vbo_format: str = ""
        
        # attribute names according to the format: ("in_position", "in_color")
        self.attrs: Tuple[str, ...] = ()
        
        # vertex array object
        self.vao: Any = None

    def get_vertex_data(self) -> Any:
        """
        Abstract method to be overridden by subclasses. Should return a contiguous 
        Numpy array containing the vertex data formatted according to `self.vbo_format`.
        """
        ...

    def get_vao(self) -> Any:
        """
        Constructs the OpenGL Vertex Buffer Object (VBO) and Vertex Array Object (VAO) 
        by pulling the geometry data from `get_vertex_data()`.
        """
        vertex_data: Any = self.get_vertex_data()
        
        vbo: Any = self.ctx.buffer(vertex_data)
        
        vao: Any = self.ctx.vertex_array(
            self.program, [(vbo, self.vbo_format, *self.attrs)], skip_errors=True
        )
        
        return vao

    def render(self) -> None:
        """
        Issues the draw call to the GPU for this mesh's geometry.
        """
        self.vao.render()

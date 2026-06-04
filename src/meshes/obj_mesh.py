"""
Wavefront OBJ and MTL 3D model parsing and mesh generation.

This module reads standard `.obj` files to extract vertices, UVs, normals, 
and faces, along with parsing `.mtl` files for diffuse color mappings. 
It automatically triangulates polygons and centers the resulting geometry 
for rendering custom 3D tools and entities in the world.
"""

import numpy as np
from typing import Any, Dict, List, Optional, Tuple
from numpy.typing import NDArray
from meshes.base_mesh import BaseMesh
import os
from profiler import global_profiler


class ObjMesh(BaseMesh):
    """
    Generates rendering geometry by parsing and loading standard 3D Wavefront (.obj) files.
    
    Supports parsing material files (.mtl) for vertex colors and automatically centers 
    the imported geometry around the origin.
    
    Args:
        app (Any): The main application instance providing the ModernGL context.
        obj_path (str): The absolute or relative file path to the `.obj` file.
        tex_id (Optional[int]): The OpenGL texture ID to bind during rendering, if applicable.
    """
    @global_profiler.profile_func("ObjMesh_Init")
    def __init__(self, app: Any, obj_path: str, tex_id: Optional[int] = None) -> None:
        """
        Initializes the OBJ mesh, preparing its shader program, vertex attributes,
        and loading the requested object file from the disk.
        """
        super().__init__()
        self.app: Any = app
        self.ctx: Any = self.app.ctx
        self.program: Any = self.app.shader_program.obj
        self.vbo_format: str = '3f 2f 3f 3f'
        self.attrs: Tuple[str, ...] = ('in_position', 'in_tex_coord', 'in_normal', 'in_color')
        self.obj_path: str = obj_path
        self.tex_id: Optional[int] = tex_id
        self.vao: Any = self.get_vao()
        
    @global_profiler.profile_func("ObjMesh_Render")
    def render(self) -> None:
        """
        Issues the draw call to the GPU for this model. Optionally enables and binds 
        an associated OpenGL texture if a texture ID was provided during initialization.
        """
        self.program['u_use_texture'] = self.tex_id is not None
        
        if self.tex_id is not None:
            self.program['u_texture_0'] = self.tex_id
        
        self.vao.render()

    @global_profiler.profile_func("ObjMesh_ParseMTL")
    def parse_mtl(self, mtl_path: str) -> Dict[str, Dict[str, List[float]]]:
        """
        Reads a Wavefront material (.mtl) file and extracts the diffuse color (Kd) 
        values for each material, allowing the OBJ to render with its assigned base colors.
        """
        materials: Dict[str, Dict[str, List[float]]] = {}
        current_material: Optional[str] = None
        
        try:
            with open(mtl_path, 'r', encoding='utf-8') as f:
                for line in f:
        
                    if line.startswith('newmtl'):
                        current_material = line.split()[1]
                        materials[current_material] = {}
        
                    elif current_material and line.startswith('Kd'):
                        materials[current_material]['Kd'] = [float(x) for x in line.split()[1:]]
        
        except FileNotFoundError:
            print(f"MTL file not found: {mtl_path}")
        
        return materials

    @global_profiler.profile_func("ObjMesh_GetVertexData")
    def get_vertex_data(self) -> NDArray[np.float32]:
        """
        Parses the .obj file line by line to extract vertices, texture coordinates, 
        and normals. Triangulates complex polygons using a triangle fan approach and 
        mathematically centers the entire assembled geometry around the origin (0, 0, 0).
        """
        vertices: List[List[float]] = []
        tex_coords: List[List[float]] = []
        normals: List[List[float]] = []
        vertex_data: List[float] = []
        materials: Dict[str, Dict[str, List[float]]] = {}
        current_material_color: List[float] = [1.0, 1.0, 1.0]
        
        try:
            obj_dir: str = os.path.dirname(self.obj_path)
            with open(self.obj_path, 'r', encoding='utf-8') as f:
                for line in f:
        
                    if line.startswith('mtllib'):
                        mtl_filename: str = line.split()[1]
                        mtl_path: str = os.path.join(obj_dir, mtl_filename)
                        materials = self.parse_mtl(mtl_path)
        
                    elif line.startswith('usemtl'):
                        material_name: str = line.split()[1]
        
                        if material_name in materials and 'Kd' in materials[material_name]:
                            current_material_color = materials[material_name]['Kd']
        
                    elif line.startswith('v '):
                        vertices.append([float(x) for x in line.split()[1:]])
        
                    elif line.startswith('vt '):
                        tex_coords.append([float(x) for x in line.split()[1:]])
        
                    elif line.startswith('vn '):
                        normals.append([float(x) for x in line.split()[1:]])
        
                    elif line.startswith('f '):
                        face_vertices: List[str] = line.split()[1:]
                        # Triangulate polygons (quads/n-gons) into triangles using a triangle fan
        
                        for i in range(1, len(face_vertices) - 1):
                            for face in (face_vertices[0], face_vertices[i], face_vertices[i+1]):
        
                                parts: List[str] = face.split('/')
        
                                v_idx: int = int(parts[0]) - 1
                                vt_idx: int = int(parts[1]) - 1 if len(parts) > 1 and parts[1] else -1
                                vn_idx: int = int(parts[2]) - 1 if len(parts) > 2 and parts[2] else -1
        
                                vertex_data.extend(vertices[v_idx])
                                vertex_data.extend(tex_coords[vt_idx] if vt_idx != -1 and tex_coords else [0.0, 0.0])
                                vertex_data.extend(normals[vn_idx] if vn_idx != -1 and normals else [0.0, 1.0, 0.0])
                                vertex_data.extend(current_material_color)
        
        except FileNotFoundError:
            print(f"ObjMesh warning: '{self.obj_path}' not found. Rendering fallback triangle.")
        
            return np.array([
                0,0,0, 0,0, 0,1,0, 1,1,1,
                0,1,0, 0,1, 0,1,0, 1,1,1,
                1,0,0, 1,0, 0,1,0, 1,1,1
            ], dtype='float32')
            
        vd_array: NDArray[np.float32] = np.array(vertex_data, dtype='float32')
        
        # Automatically center the geometry around the origin (0, 0, 0)
        # This prevents models from orbiting wildly when rotated if their Blender origin was off-center!
        if len(vd_array) > 0:
            x_coords = vd_array[0::11] # Grab every 11th float starting at index 0 (X)
            y_coords = vd_array[1::11] # Grab every 11th float starting at index 1 (Y)
            z_coords = vd_array[2::11] # Grab every 11th float starting at index 2 (Z)
            
            center_x: float = float((np.max(x_coords) + np.min(x_coords)) / 2.0)
            center_y: float = float((np.max(y_coords) + np.min(y_coords)) / 2.0)
            center_z: float = float((np.max(z_coords) + np.min(z_coords)) / 2.0)
            
            vd_array[0::11] -= center_x
            vd_array[1::11] -= center_y
            vd_array[2::11] -= center_z
            
        return vd_array

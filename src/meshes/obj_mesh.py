import numpy as np
from meshes.base_mesh import BaseMesh
import os


class ObjMesh(BaseMesh):
    def __init__(self, app, obj_path, tex_id=None):
        super().__init__()
        self.app = app
        self.ctx = self.app.ctx
        self.program = self.app.shader_program.obj
        self.vbo_format = '3f 2f 3f 3f'
        self.attrs = ('in_position', 'in_tex_coord', 'in_normal', 'in_color')
        self.obj_path = obj_path
        self.tex_id = tex_id
        self.vao = self.get_vao()
        
    def render(self):
        self.program['u_use_texture'] = self.tex_id is not None
        if self.tex_id is not None:
            self.program['u_texture_0'] = self.tex_id
        self.vao.render()

    def parse_mtl(self, mtl_path):
        materials = {}
        current_material = None
        try:
            with open(mtl_path, 'r') as f:
                for line in f:
                    if line.startswith('newmtl'):
                        current_material = line.split()[1]
                        materials[current_material] = {}
                    elif current_material and line.startswith('Kd'):
                        materials[current_material]['Kd'] = [float(x) for x in line.split()[1:]]
        except FileNotFoundError:
            print(f"MTL file not found: {mtl_path}")
        return materials

    def get_vertex_data(self):
        vertices = []
        tex_coords = []
        normals = []
        vertex_data = []
        materials = {}
        current_material_color = [1.0, 1.0, 1.0]
        
        try:
            obj_dir = os.path.dirname(self.obj_path)
            with open(self.obj_path, 'r') as f:
                for line in f:
                    if line.startswith('mtllib'):
                        mtl_filename = line.split()[1]
                        mtl_path = os.path.join(obj_dir, mtl_filename)
                        materials = self.parse_mtl(mtl_path)
                    elif line.startswith('usemtl'):
                        material_name = line.split()[1]
                        if material_name in materials and 'Kd' in materials[material_name]:
                            current_material_color = materials[material_name]['Kd']
                    elif line.startswith('v '):
                        vertices.append([float(x) for x in line.split()[1:]])
                    elif line.startswith('vt '):
                        tex_coords.append([float(x) for x in line.split()[1:]])
                    elif line.startswith('vn '):
                        normals.append([float(x) for x in line.split()[1:]])
                    elif line.startswith('f '):
                        face_vertices = line.split()[1:]
                        # Triangulate polygons (quads/n-gons) into triangles using a triangle fan
                        for i in range(1, len(face_vertices) - 1):
                            for face in (face_vertices[0], face_vertices[i], face_vertices[i+1]):
                                parts = face.split('/')
                                v_idx = int(parts[0]) - 1
                                vt_idx = int(parts[1]) - 1 if len(parts) > 1 and parts[1] else -1
                                vn_idx = int(parts[2]) - 1 if len(parts) > 2 and parts[2] else -1
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
            
        vertex_data = np.array(vertex_data, dtype='float32')
        
        # Automatically center the geometry around the origin (0, 0, 0)
        # This prevents models from orbiting wildly when rotated if their Blender origin was off-center!
        if len(vertex_data) > 0:
            x_coords = vertex_data[0::11] # Grab every 11th float starting at index 0 (X)
            y_coords = vertex_data[1::11] # Grab every 11th float starting at index 1 (Y)
            z_coords = vertex_data[2::11] # Grab every 11th float starting at index 2 (Z)
            
            center_x = (np.max(x_coords) + np.min(x_coords)) / 2.0
            center_y = (np.max(y_coords) + np.min(y_coords)) / 2.0
            center_z = (np.max(z_coords) + np.min(z_coords)) / 2.0
            
            vertex_data[0::11] -= center_x
            vertex_data[1::11] -= center_y
            vertex_data[2::11] -= center_z
            
        return vertex_data
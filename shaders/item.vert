#version 330 core

layout (location = 0) in vec3 in_position;
layout (location = 1) in vec2 in_tex_coord;
layout (location = 2) in float in_face_id;

uniform mat4 m_proj;
uniform mat4 m_view;
uniform mat4 m_model;
uniform vec3 u_sun_direction;

out vec2 uv;
flat out int face_id;
out float shading;

const vec3 face_normals[6] = vec3[6](
    vec3( 0.0,  1.0,  0.0), vec3( 0.0, -1.0,  0.0), vec3( 1.0,  0.0,  0.0),
    vec3(-1.0,  0.0,  0.0), vec3( 0.0,  0.0, -1.0), vec3( 0.0,  0.0,  1.0)
);

void main() {
    uv = in_tex_coord;
    face_id = int(in_face_id);
    
    mat3 normal_matrix = transpose(inverse(mat3(m_model)));
    vec3 world_normal = normalize(normal_matrix * face_normals[face_id]);
    float diffuse = max(0.0, dot(world_normal, u_sun_direction));
    shading = max(0.05, 0.3 * (u_sun_direction.y + 0.5)) + diffuse * 0.7;

    gl_Position = m_proj * m_view * m_model * vec4(in_position - 0.5, 1.0); // Center at origin
}
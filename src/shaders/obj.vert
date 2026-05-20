#version 330 core

layout (location = 0) in vec3 in_position;
layout (location = 1) in vec2 in_tex_coord;
layout (location = 2) in vec3 in_normal;
layout (location = 3) in vec3 in_color;

uniform mat4 m_proj;
uniform mat4 m_view;
uniform mat4 m_model;
uniform vec3 u_sun_direction;

out vec2 uv;
out float shading;
out vec3 frag_color;


void main() {
    uv = in_tex_coord;
    frag_color = in_color;
    
    mat3 normal_matrix = transpose(inverse(mat3(m_model)));
    vec3 world_normal = normalize(normal_matrix * in_normal);
    float diffuse = max(0.0, dot(world_normal, u_sun_direction));
    shading = max(0.05, 0.3 * (u_sun_direction.y + 0.5)) + diffuse * 0.7;

    gl_Position = m_proj * m_view * m_model * vec4(in_position, 1.0);
}

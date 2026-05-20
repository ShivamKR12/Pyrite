#version 330 core

layout (location = 0) in vec2 in_position;

out vec3 view_dir;

uniform mat4 m_inv_proj;
uniform mat4 m_inv_view;


void main() {
    gl_Position = vec4(in_position, 1.0, 1.0);
    
    // Calculate the view ray direction for this specific pixel
    vec4 t = m_inv_proj * vec4(in_position, 1.0, 1.0);
    view_dir = (m_inv_view * vec4(t.xyz, 0.0)).xyz; // 0.0 ignores translation, keeping only rotation
}

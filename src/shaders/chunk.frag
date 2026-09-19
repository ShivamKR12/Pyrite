#version 330 core

// Output variable for the final fragment color to be written to the framebuffer
layout (location = 0) out vec4 fragColor;

// The standard gamma curve value (2.2) used for gamma correction to map linear light to sRGB space
const vec3 gamma = vec3(2.2);
// The inverse gamma value (1.0 / 2.2) used to map sRGB colors back into linear light space for math
const vec3 inv_gamma = 1 / gamma;

// The 2D texture array containing all of the block textures mapped by their respective IDs
uniform sampler2DArray u_texture_array_0;
// The background sky color used to blend with the fog at far distances
uniform vec3 bg_color;
// Boolean flag indicating if the camera is underwater, used to apply a blue color tint
uniform bool u_underwater_tint;
// The density of the fog, determining how quickly the fog thickens based on distance
uniform float u_fog_density;
// The maximum opacity the fog can reach, preventing the screen from becoming entirely fog-colored
uniform float u_fog_max_opacity;
// The elapsed time since the game started, used to animate the water texture offsets
uniform float u_time;
// The normalized directional vector of the sun, used for day/night lighting calculations
uniform vec3 u_sun_direction;
// An array mapping internal voxel IDs to their corresponding texture slice index in the texture array
uniform int u_texture_map[256];

// The interpolated texture coordinates from the vertex shader (in pixel space, not 0-1)
in vec2 uv;
// The pre-calculated shading value from the vertex shader (ambient + diffuse + ambient occlusion)
in float shading;
// The fragment's world-space position vector, interpolated from the vertex positions
in vec3 frag_world_pos;
// The interpolated sunlight level reaching this fragment (0.0 to 1.0)
in float sun_light;
// The interpolated block light level reaching this fragment (0.0 to 1.0)
in float block_light;

// The non-interpolated integer representing the face of the block (0 to 5)
flat in int face_id;
// The non-interpolated integer representing the voxel's block type ID
flat in int voxel_id;
// Boolean integer (1 or 0) indicating if this block borders water
flat in int is_water_neighbor;

void main() {
    // Calculate the partial derivative of the UV coordinates with respect to the screen's X axis
    vec2 dx = dFdx(uv);
    // Calculate the partial derivative of the UV coordinates with respect to the screen's Y axis
    vec2 dy = dFdy(uv);

    // Extract the fractional part of the UVs to wrap coordinates between 0.0 and 1.0 for each block face
    vec2 face_uv = fract(uv);
    
    // Check if the current voxel is water (ID 11)
    if (voxel_id == 11) {
        // Offset the fractional UVs based on time and re-apply fract() to create a continuous flowing animation
        face_uv = fract(face_uv + vec2(u_time * 0.2, u_time * 0.2));
    }
    
    // Shrink the UV width to 1/3rd and shift it based on the face ID to sample from a 3-part composite texture map
    face_uv.x = face_uv.x / 3.0 - min(face_id, 2) / 3.0;
    
    // Retrieve the actual texture array slice index for this block type from the uniform mapping array
    int tex_id = u_texture_map[voxel_id];
    
    // Sample the texture array using explicit gradients (dx/3, dy) to prevent mipmap artifacting at block edges
    vec4 tex_sample = textureGrad(u_texture_array_0, vec3(face_uv, tex_id), vec2(dx.x / 3.0, dx.y), vec2(dy.x / 3.0, dy.y));
    
    // Check if the alpha channel of the sampled texture is below 0.1 (transparent)
    if (tex_sample.a < 0.1) {
        // Discard the fragment entirely so it doesn't write to the depth or color buffers
        discard;
    }
    
    // Extract the RGB color channels from the texture sample
    vec3 tex_col = tex_sample.rgb;
    // Apply gamma correction (pow 2.2) to convert the sRGB texture color into linear color space for accurate lighting math
    tex_col = pow(tex_col, gamma);
    
    // Calculate daylight intensity by taking the sun's Y direction (height), boosting it by 0.2, and clamping to a minimum of 0.05
    float day_light = max(0.05, u_sun_direction.y + 0.2); 
    
    // Multiply the local sunlight level by the global daylight level, then take the maximum of that and the local block light
    float final_light = max(sun_light * day_light, block_light);
    // Raise the final light value to the power of 1.5 to create a non-linear falloff (gamma curve) for natural-looking darkness, clamped at 0.02
    final_light = max(0.02, pow(final_light, 1.5));

    // Multiply the linear texture color by the vertex shading factor and the computed final light level
    tex_col *= shading * final_light;

    // Check if underwater tinting is active, the block touches water, and the block itself is not water
    if (u_underwater_tint && is_water_neighbor == 1 && voxel_id != 11) {
        // Multiply the color by a bluish tint vector to simulate light filtering through water
        tex_col *= vec3(0.0, 0.3, 1.0);
    }

    // Apply inverse gamma correction (pow 1/2.2) to convert the linear color back to sRGB space for the monitor display
    tex_col = pow(tex_col, inv_gamma);

    // Calculate the normalized device coordinate depth (Z / W) to get the non-linear distance from the camera
    float fog_dist = gl_FragCoord.z / gl_FragCoord.w;
    // Calculate the fog factor using an exponential squared function (1 - 2^(-density * dist^2)), capped by max opacity
    float fog_factor = min(1.0 - exp2(-u_fog_density * fog_dist * fog_dist), u_fog_max_opacity);
    
    // Linearly interpolate between the shaded texture color and the sky background color using the calculated fog factor
    tex_col = mix(tex_col, bg_color, fog_factor);

    // Default the alpha transparency value to fully opaque (1.0)
    float alpha = 1.0;
    // Check if the current block is water
    if (voxel_id == 11) {
        // Linearly interpolate the water alpha from 0.5 (near) to 0.0 (far) based on the inverse exponential fog density
        alpha = mix(0.5, 0.0, 1.0 - exp(-u_fog_density * fog_dist * fog_dist));
    }

    // Output the final computed RGB color and alpha value to the framebuffer
    fragColor = vec4(tex_col, alpha);
}

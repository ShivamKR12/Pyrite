import sys

with open('d:/Pyrite/src/frustum.py', 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if '# ==================' in line and 'Frustum Culling' in line:
        line = line.replace('# ================== ', '# ')
        line = line.replace(' ==================\n', '\n')

    if line.strip() == 'n = len(chunk_centers)':
        new_lines.append('    # Total number of chunks we need to evaluate in parallel\n')

    if line.strip() == 'cpx, cpy, cpz = cam_pos[0], cam_pos[1], cam_pos[2]':
        new_lines.append(
            "    # Extract the camera's world-space position into scalar variables for fast parallel access\n"
        )

    if line.strip() == 'cfx, cfy, cfz = cam_forward[0], cam_forward[1], cam_forward[2]':
        new_lines.append("    # Extract the camera's forward-pointing normal vector\n")

    if line.strip() == 'crx, cry, crz = cam_right[0], cam_right[1], cam_right[2]':
        new_lines.append("    # Extract the camera's right-pointing normal vector\n")

    if line.strip() == 'cux, cuy, cuz = cam_up[0], cam_up[1], cam_up[2]':
        new_lines.append("    # Extract the camera's up-pointing normal vector\n")

    if line.strip() == 'radius_sq = (CHUNK_SPHERE_RADIUS * 1.2) ** 2':
        new_lines.append(
            '    # Precalculate the squared radius of the chunk bounding sphere.\n    # Multiplying by 1.2 adds a 20% margin of error to prevent popping artifacts at the edge of the screen.\n'
        )

    if line.strip() == 'for i in prange(n):':
        new_lines.append("    # Loop over all chunk centers using Numba's prange for multithreading\n")

    if line.strip() == 'svx = chunk_centers[i, 0] - cpx':
        new_lines.append(
            '        # Calculate the direction vector from the camera to the chunk center (sphere center)\n'
        )

    if line.strip() == 'dist_sq = svx * svx + svy * svy + svz * svz':
        new_lines.append('        # Calculate the squared distance (magnitude squared) from the camera to the chunk\n')

    if line.strip() == 'if dist_sq < radius_sq:':
        new_lines.append(
            '        # If the chunk is so close to the camera that it lies within its bounding sphere radius,\n        # it is trivially visible and we can skip the plane checks entirely\n'
        )

    if line.strip() == 'sz = svx * cfx + svy * cfy + svz * cfz':
        new_lines.append(
            "        # Project the sphere vector onto the camera's forward vector using the dot product.\n        # This gives us the scalar depth of the chunk relative to the camera's facing direction.\n"
        )

    if line.strip() == 'if not (NEAR - CHUNK_SPHERE_RADIUS <= sz <= FAR + CHUNK_SPHERE_RADIUS):':
        new_lines.append(
            "        # Check against the near and far planes of the frustum.\n        # If the chunk's depth minus its radius is farther than the FAR plane,\n        # or its depth plus its radius is closer than the NEAR plane, it's outside.\n"
        )

    if line.strip() == 'sz = max(0.0, sz)':
        new_lines.append(
            '        # Clamp the depth to 0.0 to prevent inverted frustum culling when chunks are behind the camera\n'
        )

    if line.strip() == 'sy = svx * cux + svy * cuy + svz * cuz':
        new_lines.append(
            "        # Project the sphere vector onto the camera's up vector (dot product) to get its local Y position\n"
        )

    if line.strip() == 'dist_y = factor_y * CHUNK_SPHERE_RADIUS + sz * tan_y':
        new_lines.append(
            "        # Calculate the half-height of the frustum at the chunk's depth (sz * tan_y).\n        # We add the bounding sphere radius (scaled by factor_y) to expand the top/bottom planes.\n"
        )

    if line.strip() == 'if not (-dist_y <= sy <= dist_y):':
        new_lines.append(
            "        # Check if the chunk's local Y position falls outside the expanded top or bottom planes\n"
        )

    if line.strip() == 'sx = svx * crx + svy * cry + svz * crz':
        new_lines.append(
            "        # Project the sphere vector onto the camera's right vector (dot product) to get its local X position\n"
        )

    if line.strip() == 'dist_x = factor_x * CHUNK_SPHERE_RADIUS + sz * tan_x':
        new_lines.append(
            "        # Calculate the half-width of the frustum at the chunk's depth (sz * tan_x).\n        # We add the bounding sphere radius (scaled by factor_x) to expand the left/right planes.\n"
        )

    if line.strip() == 'if not (-dist_x <= sx <= dist_x):':
        new_lines.append(
            "        # Check if the chunk's local X position falls outside the expanded left or right planes\n"
        )

    if (
        line.strip() == 'out_mask[i] = True' and 'if dist_sq' not in lines[lines.index(line) - 1]
    ):  # A bit hacky but we just want the last one
        if 'continue' in new_lines[-1] or 'continue' in lines[lines.index(line) - 1]:
            new_lines.append(
                '        # If the chunk passed all plane intersection tests, it is inside the frustum and visible\n'
            )

    new_lines.append(line)

with open('d:/Pyrite/src/frustum.py', 'w') as f:
    f.writelines(new_lines)

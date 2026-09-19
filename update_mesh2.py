import sys

with open('d:/Pyrite/src/meshes/chunk_mesh_builder.py', 'r') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    if '# ==================' in line and 'PLANES' in line:
        # replace borders
        line = line.replace('# ================== ', '# ')
        line = line.replace(' ==================\n', '\n')

    if 'flip_id = ((l1 >> 4) + (l1 & 15) + ao[1])' in line:
        new_lines.append(
            '                    # Determine if the quad should be flipped to prevent anisotropic lighting artifacts.\n'
        )
        new_lines.append(
            '                    # We compare the total lighting (sun + block + ao) of the two diagonals.\n'
        )
        new_lines.append(
            '                    # The diagonal with the higher total light is split to create smoother gradients.\n'
        )

    if 'mask0[' in line and ' = (' in line and 'np.uint64' in lines[i + 1]:
        new_lines.append(
            '                    # Pack all vertex attributes (voxel ID, 4 light values, 4 AO values, and flip ID)\n'
        )
        new_lines.append(
            '                    # into a single 64-bit integer mask for efficient greedy meshing later.\n'
        )
        new_lines.append(
            '                    # 41: voxel_id, 33: l0, 25: l1, 17: l2, 9: l3, 7: ao0, 5: ao1, 3: ao2, 1: ao3, 0: flip_id\n'
        )

    if 'mask1[' in line and ' = (' in line and 'np.uint64' in lines[i + 1]:
        new_lines.append(
            '                    # Pack all vertex attributes (voxel ID, 4 light values, 4 AO values, and flip ID)\n'
        )
        new_lines.append(
            '                    # into a single 64-bit integer mask for efficient greedy meshing later.\n'
        )
        new_lines.append(
            '                    # 41: voxel_id, 33: l0, 25: l1, 17: l2, 9: l3, 7: ao0, 5: ao1, 3: ao2, 1: ao3, 0: flip_id\n'
        )

    if 'while x + w < CHUNK_SIZE and mask0[x + w, z] == val:' in line:
        new_lines.append(
            '                    # Greedy meshing: Find the maximum width (w) this face can extend along the first axis\n'
        )
        new_lines.append(
            '                    # where all faces share the exact same attributes (voxel ID, lighting, AO, etc).\n'
        )

    if 'while z + h < CHUNK_SIZE:' in line and 'done =' in lines[i - 3]:
        new_lines.append(
            '                    # Greedy meshing: Now try to extend this combined face along the second axis (height)\n'
        )

    if 'v0 = pack_data' in line and 'ao0' in line:
        if 'v_id = int((val >> 41)' not in lines[i - 1]:  # prevent duplicate if multiple pack_datas
            new_lines.append(
                '                    # Pack the final geometric vertex data (position, voxel_id, face_id, etc) into a 32-bit int.\n'
            )

    if 'v_id = int((val >> 41)' in line:
        new_lines.append('                    # Unpack the chunked face attributes from the 64-bit mask value\n')

    new_lines.append(line)

with open('d:/Pyrite/src/meshes/chunk_mesh_builder.py', 'w') as f:
    f.writelines(new_lines)

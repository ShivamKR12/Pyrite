import re

with open('d:/Pyrite/src/meshes/chunk_mesh_builder.py', 'r') as f:
    content = f.read()

# Remove remaining ====
content = re.sub(r'# ================== (.+?) ==================', r'# \1', content)

# Add comments to flip_id calculation
flip_id_repl = """# Determine if the quad should be flipped to prevent anisotropic lighting artifacts.
                    # We compare the total lighting (sun + block + ao) of the two diagonals.
                    # The diagonal with the higher total light is split to create smoother gradients.
                    flip_id = ((l1 >> 4) + (l1 & 15) + ao[1]) + ((l3 >> 4) + (l3 & 15) + ao[3]) > (
                        (l0 >> 4) + (l0 & 15) + ao[0]
                    ) + ((l2 >> 4) + (l2 & 15) + ao[2])"""
content = re.sub(
    r'flip_id = \(\(l1 >> 4\) \+ \(l1 & 15\) \+ ao\[1\]\) \+ \(\(l3 >> 4\) \+ \(l3 & 15\) \+ ao\[3\]\) > \(\n\s+\(l0 >> 4\) \+ \(l0 & 15\) \+ ao\[0\]\n\s+\) \+ \(\(l2 >> 4\) \+ \(l2 & 15\) \+ ao\[2\]\)',
    flip_id_repl,
    content,
)


# Add comments to mask assignment
def repl_mask(match):
    mask_name = match.group(1)
    x_var = match.group(2)
    z_var = match.group(3)
    return f"""# Pack all vertex attributes (voxel ID, 4 light values, 4 AO values, and flip ID)
                    # into a single 64-bit integer mask for efficient greedy meshing later.
                    {mask_name}[{x_var}, {z_var}] = (
                        (np.uint64(v_id) << 41)       # Voxel ID (shifted 41 bits)
                        | (np.uint64(l0) << 33)       # Vertex 0 Light (shifted 33 bits)
                        | (np.uint64(l1) << 25)       # Vertex 1 Light (shifted 25 bits)
                        | (np.uint64(l2) << 17)       # Vertex 2 Light (shifted 17 bits)
                        | (np.uint64(l3) << 9)        # Vertex 3 Light (shifted 9 bits)
                        | (np.uint64(ao[0]) << 7)     # Vertex 0 AO (shifted 7 bits)
                        | (np.uint64(ao[1]) << 5)     # Vertex 1 AO (shifted 5 bits)
                        | (np.uint64(ao[2]) << 3)     # Vertex 2 AO (shifted 3 bits)
                        | (np.uint64(ao[3]) << 1)     # Vertex 3 AO (shifted 1 bit)
                        | np.uint64(flip_id)          # Quad flip ID (lowest bit)
                    )"""


content = re.sub(
    r'(mask[01])\[([xyz]), ([xyz])\] = \(\n\s+\(np\.uint64\(v_id\) << 41\)\n\s+\| \(np\.uint64\(l0\) << 33\)\n\s+\| \(np\.uint64\(l1\) << 25\)\n\s+\| \(np\.uint64\(l2\) << 17\)\n\s+\| \(np\.uint64\(l3\) << 9\)\n\s+\| \(np\.uint64\(ao\[0\]\) << 7\)\n\s+\| \(np\.uint64\(ao\[1\]\) << 5\)\n\s+\| \(np\.uint64\(ao\[2\]\) << 3\)\n\s+\| \(np\.uint64\(ao\[3\]\) << 1\)\n\s+\| np\.uint64\(flip_id\)\n\s+\)',
    repl_mask,
    content,
)


# Add comments to greedy meshing loop
greedy_mesh_repl = """# Greedy meshing: Find the maximum width (w) this face can extend along the first axis
                    # where all faces share the exact same attributes (voxel ID, lighting, AO, etc).
                    w, h = 1, 1

                    while x + w < CHUNK_SIZE and \\1[x + w, z] == val:
                        w += 1

                    done = False

                    # Greedy meshing: Now try to extend this combined face along the second axis (height)
                    while z + h < CHUNK_SIZE:
                        for ix in range(w):
                            if \\1[x + ix, z + h] != val:
                                done = True
                                break

                        if done:
                            break"""

content = re.sub(
    r'w, h = 1, 1\n\n\s+while x \+ w < CHUNK_SIZE and (mask[01])\[x \+ w, z\] == val:\n\s+w \+= 1\n\n\s+done = False\n\n\s+while z \+ h < CHUNK_SIZE:\n\s+for ix in range\(w\):\n\s+if \1\[x \+ ix, z \+ h\] != val:\n\s+done = True\n\s+break\n\n\s+if done:\n\s+break',
    greedy_mesh_repl,
    content,
)

with open('d:/Pyrite/src/meshes/chunk_mesh_builder.py', 'w') as f:
    f.write(content)

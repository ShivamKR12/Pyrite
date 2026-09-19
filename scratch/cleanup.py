import os
import re

files = [
    'src/lighting.py',
    'src/voxel_handler.py',
    'src/camera.py',
    'src/main.py',
    'src/world.py',
    'src/textures.py',
    'src/player.py',
]

for filepath in files:
    if not os.path.exists(filepath):
        continue
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        if re.match(r'^\s*#\s*=+\s*$', line):
            continue
        if re.match(r'^\s*#\s*REAL-WORLD CONTEXT:\s*$', line):
            continue

        new_line = re.sub(r'REAL-WORLD CONTEXT:\s*', '', line)
        new_lines.append(new_line)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

print('Cleanup complete!')

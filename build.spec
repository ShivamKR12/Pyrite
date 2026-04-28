# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_dynamic_libs

block_cipher = None

a = Analysis(
    ['run.py'],
    pathex=['src'],
    # Manually include Numba's TBB libraries and other potential missing DLLs
    binaries=collect_dynamic_libs('numba'),
    datas=[('assets', 'assets'), ('src/shaders', 'src/shaders')],
    # Add scipy hidden imports as a fallback for numpy dependencies
    hiddenimports=['numba', 'llvmlite', 'noise', 'glm', 'moderngl', 'pygame', 'scipy.linalg.cython_blas', 'scipy.linalg.cython_lapack'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Pyrite',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True, # Set to False in the future to hide the background terminal window!
    icon='assets/icon-nobg.ico',
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Pyrite',
)
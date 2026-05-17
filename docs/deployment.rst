.. _deployment:

Deployment and Builds
=====================

This chapter covers building Pyrite for distribution, CI/CD automation, and release management.

PyInstaller Setup
-----------------

Pyrite is compiled into standalone executables using PyInstaller.

**Install PyInstaller**::

    pip install pyinstaller

**Build Specification (build.spec)**

The ``build.spec`` file configures compilation:: 

    # build.spec
    a = Analysis(
        ['run.py'],
        pathex=[],
        binaries=[],
        datas=[
            ('assets', 'assets'),
            ('src/shaders', 'src/shaders'),
        ],
        hiddenimports=[
            'numba',
            'moderngl',
            'glm',
            'numpy',
            'numpy.core.multiarray',
            'opensimplex',
        ],
        hookspath=[],
        runtime_hooks=[],
        excludedimports=[
            'scipy',
            'pandas',
            'matplotlib',
        ],
        win_no_prefer_redirects=False,
        win_private_assemblies=False,
        cipher=None,
    )
    
    pyz = PYZ(a.pure, a.zipped_data, cipher=cipher)
    
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
        console=False,  # No console window
        icon='assets/icon.ico',
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

**Build Executable**::

    pyinstaller build.spec --distpath ./dist --buildpath ./build

Output: ``dist/Pyrite/Pyrite.exe`` (Windows), ``dist/Pyrite/Pyrite`` (Linux/Mac)

Size: ~150-200 MB (includes Python, NumPy, ModernGL, dependencies)

Platform-Specific Considerations
-----------------------------------

**Windows (.exe)**

Issues:

- OpenGL 3.3 driver requirements (Intel HD 630+, NVIDIA GT 1030+, AMD RX 560+)
- MSVC Redistributables (Visual C++ 2015 Redistributable Update 3)
- DLL dependencies (OpenGL, audio libraries)

Solution: Bundle MSVC runtime in installer::

    # In build.spec: add to binaries
    binaries=[
        ('C:\\Program Files (x86)\\Microsoft Visual C++ Build Tools\\...\\msvcr120.dll', '.'),
    ]

**macOS (.app)**

Create macOS bundle::

    # PyInstaller generates .app automatically on macOS
    pyinstaller build.spec --distpath ./dist --osx-bundle-identifier com.pyrite.game

Output: ``dist/Pyrite.app/`` (distributable app)

Automated CI/CD Pipeline
------------------------

**GitHub Actions Workflow** (``.github/workflows/build.yml``)

Automate builds for all platforms::

    name: Build and Release
    
    on:
      push:
        tags:
          - 'v*.*.*'  # Trigger on version tag
    
    jobs:
      build-windows:
        runs-on: windows-latest
        steps:
          - uses: actions/checkout@v3
          - uses: actions/setup-python@v4
            with:
              python-version: '3.11'
          
          - name: Install dependencies
            run: |
              python -m pip install -r requirements.txt
              python -m pip install pyinstaller
          
          - name: Build Windows executable
            run: |
              pyinstaller build.spec --distpath ./dist --buildpath ./build
          
          - name: Upload to release
            uses: softprops/action-gh-release@v1
            with:
              files: dist/Pyrite/Pyrite.exe
            env:
              GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      
      build-linux:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v3
          - uses: actions/setup-python@v4
            with:
              python-version: '3.11'
          
          - name: Install dependencies
            run: |
              sudo apt-get install -y libgl1-mesa-glx
              python -m pip install -r requirements.txt
              python -m pip install pyinstaller
          
          - name: Build Linux executable
            run: |
              pyinstaller build.spec --distpath ./dist --buildpath ./build
          
          - name: Upload to release
            uses: softprops/action-gh-release@v1
            with:
              files: dist/Pyrite/*
            env:
              GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      
      build-macos:
        runs-on: macos-latest
        steps:
          - uses: actions/checkout@v3
          - uses: actions/setup-python@v4
            with:
              python-version: '3.11'
          
          - name: Install dependencies
            run: |
              python -m pip install -r requirements.txt
              python -m pip install pyinstaller
          
          - name: Build macOS app
            run: |
              pyinstaller build.spec --distpath ./dist --osx-bundle-identifier com.pyrite.game
          
          - name: Upload to release
            uses: softprops/action-gh-release@v1
            with:
              files: dist/Pyrite.app/**/*
            env:
              GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

**Run with GitHub CLI**::

    # Tag and push release
    git tag v1.0.0
    git push origin v1.0.0
    
    # GitHub Actions automatically builds and releases

Result: Executables uploaded to GitHub Releases automatically.

Version Management
-------------------

**Semantic Versioning**

Version format: **Major.Minor.Patch**

- **Major**: Breaking engine changes (0 → 1: multiplayer mode added)
- **Minor**: New features (1.0 → 1.1: new biome added)
- **Patch**: Bug fixes (1.1.0 → 1.1.1: collision fix)

Update ``build.spec``::

    exe = EXE(
        ...,
        name='Pyrite-1.2.3',
        ...
    )

**Version Changelog (CHANGELOG.md)**

Document all changes::

    # Changelog
    
    ## [1.0.0] - 2024-01-15
    
    ### Added
    - Initial release
    - 4 biomes (desert, snow, forest, grassland)
    - Survival mechanics (health, hunger, oxygen)
    - Crafting system (16 recipes)
    - Dynamic lighting (sunlight + blocklight)
    
    ### Fixed
    - Collision detection edge cases
    - Lighting propagation through water
    
    ### Changed
    - Greedy meshing now 40% faster with Numba JIT
    
    ## [0.9.0] - 2023-12-01
    
    ### Added
    - Beta terrain generation
    - Basic UI and inventory

Launch Checklist
----------------

Before releasing to the public:

✓ **Code Quality**
  - Run pytest: all tests pass
  - Run cProfile: no obvious bottlenecks
  - Coverage >80% for critical systems (terrain, mesh, physics)

✓ **Build Verification**
  - Test on Windows 10/11 (clean install)
  - Test on Ubuntu 20.04 LTS
  - Test on macOS 12+ (Intel and Apple Silicon)
  - Verify all assets load (textures, sounds, models)

✓ **Performance**
  - FPS >30 on low-end GPU (Intel HD 630)
  - RAM usage <1GB on default render distance
  - Chunk load time <100ms average

✓ **Documentation**
  - API reference complete (dev.md)
  - Tutorial replication checklist passed
  - README updated with new features

✓ **Release**
  - Tag version (v1.x.x)
  - Push to GitHub
  - CI/CD builds automatically
  - Upload to itch.io / Steam (if desired)
  - Announce on social media

Distribution Platforms
-----------------------

**GitHub Releases** (Recommended)

- Free, unlimited hosting
- Automatic CI/CD integration
- User-friendly download page
- Changelog tracking

**itch.io**

- Indie game community
- One-click download + launcher
- User reviews and ratings
- Revenue sharing

Upload::

    # Create itch.io project: Pyrite
    # Upload build:
    butler push dist/Pyrite/Pyrite.exe <username>/pyrite:windows-latest
    butler push dist/Pyrite/Pyrite <username>/pyrite:linux-latest
    butler push dist/Pyrite.app <username>/pyrite:macos-latest

Troubleshooting Builds
----------------------

**Issue: "ModuleNotFoundError: No module named 'numba'"**

Solution: Add to build.spec hiddenimports::

    hiddenimports=['numba', 'numba.core.types', 'numba.cuda']

**Issue: "OpenGL 3.3 not supported"**

Solution: Requires GPU drivers update or fallback to OpenGL 3.1::

    # In shader_program.py
    version = (3, 3)  # Minimum requirement

**Issue: "DLL load failed: The specified module could not be found"**

Typically missing MSVC runtime. Solution::

    # Redistribute MSVC libraries
    # Or use Visual Studio 2019 Redistributable installer

**Issue: Executable runs but window doesn't appear**

Solution: Check console output::

    # Run from terminal to see errors
    Pyrite.exe

Add to build.spec::

    exe = EXE(..., console=True)  # Show console for debugging

**Issue: Game crashes on startup (NVIDIA/AMD)**

Solution: Update GPU drivers::

    # NVIDIA: GeForce Experience → Driver updates
    # AMD: Radeon Software → Update drivers

Minimum Requirements
---------------------

**Minimum Spec** (Playable at 24 FPS)

- CPU: Intel Core i3-6100 (2015, 2 cores)
- RAM: 4 GB
- GPU: Intel HD 530 (OpenGL 3.3)
- OS: Windows 10, Ubuntu 18.04, macOS 10.12
- Storage: 300 MB SSD

**Recommended Spec** (60 FPS)

- CPU: Intel Core i5-8400 (2017, 6 cores)
- RAM: 8 GB
- GPU: NVIDIA GTX 1060 (OpenGL 4.6)
- OS: Windows 11, Ubuntu 22.04, macOS 12
- Storage: 500 MB SSD

**High-End Spec** (120 FPS, max distance)

- CPU: Intel Core i9-12900K (2021, 16 cores)
- RAM: 16 GB
- GPU: NVIDIA RTX 3080 (OpenGL 4.6)
- OS: Windows 11, Ubuntu 22.04
- Storage: 500 MB NVMe

Replication Checklist
---------------------

✓ Configure build.spec with all assets and hidden imports

✓ Build on Windows, Linux, macOS (3 platforms)

✓ Test each executable on clean system (no dev tools)

✓ Verify OpenGL 3.3 support or show graceful error

✓ Create GitHub Actions workflow (automatic builds)

✓ Set up semantic versioning and changelog

✓ Document minimum/recommended hardware specs

✓ Test on GPU with lowest support tier (Intel HD)

✓ Release on GitHub Releases (or itch.io)

✓ Monitor crashes/feedback from users

See :ref:`testing` for CI/CD integration with tests.

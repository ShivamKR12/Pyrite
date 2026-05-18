.. _setup:

Installation and Setup Guide
=============================

This guide details how to set up Pyrite from scratch, including all dependencies, environment configuration, and build processes.

Prerequisites
-------------

**Operating System:** Windows 10+, macOS, or Linux (Ubuntu 18+)

**System Requirements:**

- GPU: NVIDIA/AMD/Intel with OpenGL 3.3+ support
- CPU: Multi-core processor (4+ cores recommended for 60+ FPS)
- RAM: 4GB minimum (8GB recommended for larger worlds)
- Storage: 500MB for installation + variable for world saves

**Python Version:** 3.9 or higher

Python Dependencies
-------------------

Core dependencies are specified in ``requirements.txt``:

.. code-block:: text

    pygame==2.1.3              # Windowing, events, multimedia
    moderngl==5.8.2            # Low-level OpenGL wrapper
    numpy==1.24.0              # Array operations, numerical computing
    numba==0.57.0              # JIT compilation (Numba nogil for CPU parallelization)
    glm==3.4.0                 # Math library (vectors, matrices, quaternions)
    opensimplex==0.4.3         # Procedural noise generation (Perlin-like noise)

**Development Dependencies** (in ``requirements-dev.txt``) are optional:

.. code-block:: text

    pyinstaller==6.18.0        # Build standalone executables
    pytest==7.0.0              # Unit testing framework
    sphinx==5.0.0              # Documentation generation
    sphinx-rtd-theme==1.0.0    # Read the Docs theme

Installation Steps
------------------

1. **Clone or Download Repository**

   .. code-block:: bash

       git clone https://github.com/ShivamKR12/Pyrite.git
       cd Pyrite

2. **Create Virtual Environment**

   Isolate dependencies to avoid conflicts:

   .. code-block:: bash

       python -m venv venv
       
   Activate:
   
   - **Windows (PowerShell):**
   
   .. code-block:: powershell

       .\venv\Scripts\Activate.ps1
   
   - **Windows (CMD):**
   
   .. code-block:: batch

       venv\Scripts\activate.bat
   
   - **macOS/Linux (Bash):**
   
   .. code-block:: bash

       source venv/bin/activate

3. **Install Dependencies**

   .. code-block:: bash

       pip install -r requirements.txt

4. **Install Development Dependencies (Optional)**

   For running tests and building documentation:

   .. code-block:: bash

       pip install -r requirements-dev.txt

5. **Verify Installation**

   Run a quick test to ensure all imports work:

   .. code-block:: bash

       python -c "import pygame, moderngl, numpy, numba, glm, opensimplex; print('All dependencies loaded successfully!')"

Configuration
--------------

**config.json**

Pyrite reads user preferences from ``config.json`` in the root directory at startup. If not present, defaults are used.

Structure:

.. code-block:: json

    {
        "fov": 50,
        "sensitivity": 0.002,
        "volume": 10,
        "render_distance": 4,
        "underwater_tint": false
    }

**Key Fields:**

- ``fov``: Vertical field of view in degrees. Typical values are ``30`` to ``110``.
- ``sensitivity``: Mouse input sensitivity. Typical values are ``0.001`` to ``0.01``.
- ``volume``: Global sound volume. Valid range is ``0`` to ``100``.
- ``render_distance``: Number of chunks loaded around the player. Higher values increase memory and GPU usage.
- ``underwater_tint``: Apply a blue underwater color filter when submerged.

Running the Engine
-------------------

**Standard Run (Main Game)**

.. code-block:: bash

    python run.py

Starts the Pyrite application and opens the main menu. World selection and world creation are handled from the in-game menu; ``run.py`` does not automatically create a default world on first launch.

**Run Options**

``run.py`` currently has no command-line arguments. The launcher is intended to start the engine normally rather than act as a direct subsystem test harness.

**Testing Notes**

The engine does not expose a documented public ``World(48, 5, 48)`` / ``init_chunks_at()`` sequence through ``run.py``. World loading is managed internally by ``Pyrite.init_game_session()`` and the ``Scene``/``World`` startup flow.

Building the Engine
-------------------

**Executable via PyInstaller**

Compile to a standalone ``.exe`` (Windows) or app bundle:

1. **Install PyInstaller:**

   .. code-block:: bash

       pip install pyinstaller

2. **Build Configuration**

   Edit ``build.spec`` (auto-generated, or use existing):

   .. code-block:: python

       a = Analysis(
           ['run.py'],
           pathex=['D:\\Pyrite'],
           binaries=[],
           datas=[('src', 'src'), ('assets', 'assets')],
           hiddenimports=['numba', 'moderngl', 'glm'],
           hookspath=[],
           runtime_hooks=[],
           excludedimports=[],
           win_no_prefer_redirects=False,
           win_private_assemblies=False,
           cipher=None,
           noarchive=False,
       )
       
       exe = EXE(
           pyz,
           a.scripts,
           a.binaries,
           a.zipfiles,
           a.datas,
           [],
           name='Pyrite',
           debug=False,
           bootloader_ignore_signals=False,
           strip=False,
           upx=True,
           upx_exclude=[],
           runtime_tmpdir=None,
           console=False,
       )

3. **Build:**

   .. code-block:: bash

       pyinstaller build.spec

   Output: ``dist/Pyrite.exe`` (or ``dist/Pyrite`` on macOS/Linux)

**GitHub Actions CI/CD**

Automated builds via ``.github/workflows/build.yml`` (on push/release). Generates platform-specific executables.

Documentation Building
-----------------------

Build HTML docs locally:

.. code-block:: bash

    cd docs
    sphinx-build . _build/html

Open ``_build/html/index.html`` in a browser.

Troubleshooting
---------------

**"ModuleNotFoundError: No module named 'moderngl'"**

   Ensure virtual environment is activated and ``pip install -r requirements.txt`` was run.

**"OpenGL 3.3 not supported"**

   GPU lacks OpenGL 3.3 support. Update drivers or use a newer GPU. Test with:

   .. code-block:: python

       import moderngl
       ctx = moderngl.create_standalone_context(require=330)  # Will error if unsupported

**"ImportError: DLL load failed"** (Windows)

   Missing Visual C++ runtime. Download from Microsoft or reinstall Python.

**Low FPS / Frame Drops**

   - Reduce ``render_distance`` in ``config.json``
   - Lower ``MESH_BUILD_LIMIT_INGAME`` in ``settings.py`` (slower chunk loading)
   - Disable ``underwater_tint`` and other effects

**Crashes on World Load**

   - Verify ``requirements.txt`` versions match. Some Numba/NumPy combos are incompatible.
   - Delete worlds from ``saves/`` folder and regenerate.

Development Workflow
---------------------

1. **Activate Venv:** Always start with ``.\venv\Scripts\Activate.ps1`` (or bash equivalent)
2. **Run Tests:** ``pytest tests/`` (see testing.rst)
3. **Edit Code:** Modify ``src/`` modules. Changes are live (no recompilation needed in Python)
4. **Iterate:** Test behavior, commit changes

Performance Tuning
------------------

**Memory Optimization:**

- Reduce ``WORLD_W``, ``WORLD_H``, ``WORLD_D`` in ``settings.py`` to limit chunk count
- Reduce ``VBO_POOL_CAP`` to recycle GPU buffers faster

**CPU Optimization:**

- Increase ``MESH_BUILD_LIMIT_INGAME`` for faster chunk meshing (costs frames)
- Reduce ``LIGHTING_QUEUE_SIZE`` if BFS propagation is slow (may miss light areas)

**GPU Optimization:**

- Use lower resolution (e.g., 1280x720 instead of 1920x1080)
- Reduce texture resolution by editing asset pipeline
- Disable occlusion queries in ``shader_program.py`` if ineffective

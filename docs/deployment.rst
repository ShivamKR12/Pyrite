.. _deployment:

=====================
Deployment and Builds
=====================

This chapter covers building Pyrite for distribution, CI/CD automation, and release management.

PyInstaller Setup
-----------------

Pyrite is compiled into standalone executables using PyInstaller.

**Install PyInstaller**

.. code-block:: bash

    pip install pyinstaller

**Build Specification (build.spec)**

The build configuration is maintained in the ``build.spec`` file located in the root directory of the repository. It automatically resolves hidden imports (like ``numba``, ``moderngl``, and ``opensimplex``) and bundles the required ``assets/`` and ``src/shaders/`` directories into the final build.

**Build Executable**

.. code-block:: bash

    pyinstaller build.spec --distpath ./dist --buildpath ./build

Output: ``dist/Pyrite/Pyrite.exe`` (Windows), ``dist/Pyrite/Pyrite`` (Linux/Mac)

Size: ~150-200 MB (includes Python, NumPy, ModernGL, dependencies)

Automated CI/CD Pipeline
------------------------

**GitHub Actions Workflow**

The CI/CD pipeline is defined in ``.github/workflows/build.yml``.

The workflow runs across a matrix of operating systems (Windows, Ubuntu, macOS) utilizing Python 3.13. It is triggered automatically when a new GitHub Release is **published**, or manually via a ``workflow_dispatch``.

Instead of compiling raw standalone files, the workflow executes the PyInstaller build and automatically zips the output directories (e.g., ``Pyrite_Windows.zip``, ``Pyrite_Linux.zip``) before attaching them directly to the GitHub Release.

**Triggering a Build**

To release a new version, simply draft a new release on GitHub and publish it. The Actions workflow will automatically compile, zip, and attach the executables to your release.

Version Management
-------------------

**Semantic Versioning**

Version format: **Major.Minor.Patch**

- **Major**: Breaking engine changes (0 → 1: multiplayer mode added)
- **Minor**: New features (1.0 → 1.1: new biome added)
- **Patch**: Bug fixes (1.1.0 → 1.1.1: collision fix)

Next Steps
----------

Congratulations! You have reached the end of the Pyrite engine documentation. Return to the :doc:`index` to review specific subsystems or API references.

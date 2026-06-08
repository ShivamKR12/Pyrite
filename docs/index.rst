Welcome to Pyrite's Engine Documentation!
=========================================

Pyrite is a highly-optimized, procedural 3D Voxel Engine written entirely in Python.

Unlike standard Python projects, Pyrite heavily utilizes Just-In-Time (JIT) LLVM compilation via Numba to bypass the Global Interpreter Lock (GIL) and achieve near C++ performance.

This documentation breaks down the core systems of the engine, explaining how terrain is generated, how light propagates, and how millions of voxels are rendered smoothly at 60+ FPS.

.. toctree::
   :maxdepth: 2
   :caption: Getting Started:

   setup
   main

.. toctree::
   :maxdepth: 2
   :caption: Engine Architecture:

   architecture
   rendering
   lighting
   shaders

.. toctree::
   :maxdepth: 2
   :caption: Core Systems:

   meshes
   terrain
   player
   ui
   persistence
   survival
   assets
   audio

.. toctree::
   :maxdepth: 2
   :caption: Learning and Reference:

   tutorials

.. toctree::
   :maxdepth: 2
   :caption: Development:

   testing
   deployment
   profiling
   api/modules

* :ref:`search`

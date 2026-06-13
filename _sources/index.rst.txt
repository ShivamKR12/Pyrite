Introduction
============
Welcome to Pyrite's Documentation!

Pyrite is a highly-optimized, procedural 3D Voxel Engine written entirely in Python.
This section provides a high-level overview of the engine, its underlying technologies, and its core systems.

Overview
--------
Pyrite is built to bypass standard Python limitations, achieving near C++ speeds for complex tasks such as chunk generation, vectorized noise math, and frustum culling. The engine relies heavily on concurrency and Just-In-Time (JIT) compilation to maintain a stutter-free experience while managing massive amounts of 3D data.

Technologies
------------
The engine leverages several key technologies to deliver its performance and visual fidelity:

* **Python:** The core language used for all game logic and engine architecture.
* **Numba:** A JIT compiler that translates Python functions to optimized machine code at runtime, utilizing LLVM. It is used extensively to bypass the Global Interpreter Lock (GIL) and vectorize math operations.
* **ModernGL:** A high-performance Python binding for OpenGL 3.3+, responsible for hardware occlusion queries, custom shaders, and all GPU rendering pipelines.
* **PyGLM:** A fast OpenGL Mathematics (GLM) library for matrix and vector operations.
* **SQLite:** Used for persistent world storage with Write-Ahead Logging (WAL) for async-like high-performance disk writing.
* **Pygame:** Handles window creation, input events, and audio playback.

Systems and Sub-systems
-----------------------
Pyrite is composed of several interdependent systems, each handling specific aspects of the engine's functionality:

* **Engine Core:** The foundational layer that initializes the application window, manages the game loop, and orchestrates the interaction between all other systems. It handles state transitions, configuration loading, and overall execution flow.
* **World Management:** Responsible for the dynamic streaming of terrain chunks. This system monitors player movement and coordinates the loading of new chunks and the unloading of distant ones to manage memory footprint effectively.
* **Procedural Generation:** Utilizes 3D Simplex noise to deterministically generate infinite terrain based on a seed. This system calculates heightmaps, biome structures, caves, and natural features like trees before any blocks are rendered.
* **Lighting Engine:** A highly optimized Breadth-First Search (BFS) volumetric lighting system. It calculates sunlight propagation and block-light emissions (like torches), managing light spill across chunk boundaries using 64-bit integer bit-packing for speed.
* **Rendering Pipeline:** Manages the transformation of voxel data into visual geometry. It employs Greedy Meshing to drastically reduce the number of polygons and GPU draw calls. Vectorized Frustum Culling and Hardware Occlusion Queries ensure that only visible terrain is drawn to the screen.
* **Multithreading and Concurrency:** A ThreadPoolExecutor-based system that offloads heavy computations—such as terrain generation, lighting calculations, and database reads—to background CPU cores, keeping the main render thread smooth and responsive.
* **Storage and Persistence:** Manages the saving and loading of the voxel world, player inventory, and metadata. By caching chunk data, lightmaps, and entities in an SQLite database, it skips expensive recalculations during subsequent load operations.
* **Survival and Physics:** Handles the rules of the game world, including player health, hunger, oxygen, and inventory mechanics. It also manages entity physics, such as gravity, collisions, and the dropping of mined blocks as 3D items.

Explanation
===========

The following sections delve into how Pyrite achieves its high performance and manages its complex systems under the hood.

.. toctree::
   :maxdepth: 2
   :caption: Explanation:

   Application Entry and Core Loop <main>
   Engine Initialization and Settings <setup>
   World Architecture and Multithreading <architecture>
   Persistence Systems and SQLite Storage <persistence>
   Terrain Systems and Procedural Generation <terrain>
   Shader Systems and GLSL Breakdown <shaders>
   Lighting Systems and BFS Propagation <lighting>
   Meshing Systems and Greedy Geometry <meshes>
   Rendering Pipeline and Camera <rendering>
   Player Systems and Physics Controller <player>
   Survival Mechanics and Statistics <survival>
   UI Systems and 2D Overlays <ui>
   Audio Systems and Spatial Mixing <audio>
   Asset Systems and Texture Atlases <assets>
   Telemetry Systems and Profiling Breakdown <profiling>
   Testing Framework and CI/CD <testing>
   Deployment and Build Guides <deployment>

API Reference
=============

The API documentation is automatically generated from the source code docstrings.

.. toctree::
   :maxdepth: 2
   :caption: API Reference:

   API Reference <api/modules>

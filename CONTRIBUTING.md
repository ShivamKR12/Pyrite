# Contributing to Pyrite

Thank you for your interest in Pyrite! This project is a highly concurrent, custom-built voxel engine. Because the engine bypasses standard Python limitations to achieve high framerates, maintaining performance requires strict adherence to specific architectural rules.

By submitting a Pull Request, you agree to follow the code quality and structural guidelines outlined below.

---

## 🐛 Reporting Bugs & Requesting Features

Before writing any code, please ensure there is an open issue for your planned work.
* **Bugs**: Use the **Bug Report** template. Include your OS, Python version, and crash logs (`crash_log.txt`).
* **Features**: Use the **Feature Request** template. Major architectural changes should be discussed with maintainers before you spend time implementing them.
* **Claiming Issues**: Comment on an existing issue if you want to work on it so others know it's being handled.

---

## ️ Developer Setup

1. Fork the repository and clone it locally.
2. Create and activate a Python 3.13 virtual environment.
3. Install all required development, testing, and core dependencies:
   ```bash
   pip install -r requirements-dev.txt -r requirements.txt
   ```
4. Install the pre-commit hooks, which will automatically format and lint your code before each commit:
   ```bash
   pre-commit install
   ```
5. Verify your setup by running the engine locally:
   ```bash
   python run.py
   ```

---

## ⚖️ Strict Architectural Constraints

Pyrite achieves its performance through specific technical choices. Your contributions must not degrade these systems.

### 1. Numba JIT Compilation
Performance-critical loops (greedy meshing, terrain generation, BFS light propagation) are compiled directly to LLVM using Numba.
* **Decorators**: All mathematical operations in these loops MUST use the `@njit(cache=True, nogil=True)` decorator. Use `fastmath=True` and `parallel=True` (with `prange`) only when vectorization and threading are mathematically safe and proven to provide a performance benefit without adding unnecessary overhead.
* **No Python Objects**: Do NOT introduce standard Python objects (`list`, `dict`, `set`, objects) inside Numba-compiled functions. You must stick to primitive types (`int`, `float`) and flat Numpy arrays.
* **Memory Allocation**: Never allocate large Numpy arrays *inside* a Numba loop. Pre-allocate arrays in Python and pass them into the `@njit` function by reference.

#### 📊 Numba JIT Benchmarks (WIP)
To ensure we only use compilation flags when they genuinely provide a performance boost, we are actively benchmarking all Numba-compiled functions.

| Module / Group | Parent Profiler Target | Baseline (Min / Avg / Max ms) | Fastmath (Min / Avg / Max ms) | Parallel | Maxed Out | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Frustum** | `Frustum_Culling` | 0.039 / 0.151 / 31.022 | 0.032 / 0.148 / 21.836 | *prange* | *prange* | 🟢 Maxed Out |
| **Lighting** | `Lighting_InitChunkLighting` | 0.228 / 20.597 / 11104.132 | 0.179 / 22.567 / 10933.398 | FAILED 🔴 | N/A | 🟢 Baseline |
| **Lighting** | `Lighting_StitchChunkLighting` | 1.085 / 14.132 / 2234.682 | 0.831 / 13.749 / 1830.661 | FAILED 🔴 | N/A | 🟢 Baseline |
| **Lighting** | `Lighting_PlaceLightBlock` | 0.012 / 55.414 / 2949.791 | 0.015 / 82.090 / 3322.618 | FAILED 🔴 | N/A | 🟢 Baseline |
| **Lighting** | `Lighting_RemoveLightBlock` | 0.010 / 29.663 / 1405.207 | 0.013 / 34.778 / 1537.964 | FAILED 🔴 | N/A | 🟢 Baseline |
| **Terrain** | `Fetch_Or_Generate_Voxels` | 0.726 / 5.893 / 105.641 | 1.111 / 5.601 / 59.103 | FAILED 🔴 | N/A | 🟢 Fastmath |
| **Chunk Mesh** | `ChunkMesh_GetVertexData` | 2.053 / 35.142 / 321.168 | 2.040 / 36.756 / 254.382 | FAILED 🔴 | N/A | 🟢 Baseline |
| **Cloud Mesh** | `CloudMesh_GetVertexData` | 2502.452 / 2502.452 / 2502.452 | 2312.611 / 2312.611 / 2312.611 | *prange* | *prange* | 🟢 Maxed Out |

#### ⚠️ Why `parallel=True` and `prange` are Restricted
Do **not** attempt to force `parallel=True` by changing standard `range` loops to `prange` in terrain generation, lighting, or meshing. Doing so will instantly corrupt world data and crash the engine due to:
1. **Shared Counter Race Conditions**: Queues and mesh builders rely on dynamic index counters (e.g., `index += 1`). Multiple threads writing to the same index simultaneously will overwrite data.
2. **Overlapping Memory Writes**: Terrain structures like trees span multiple blocks. If two threads generate adjacent columns concurrently, they will attempt to write to the same shared memory addresses simultaneously, causing memory corruption or segmentation faults.
3. **While Loop Constraints**: Our volumetric lighting relies on Breadth-First Search (BFS) `while` loops. Numba cannot parallelize dynamic loops because the exact iteration count must be known before execution begins.

*Note: Multi-threading is already safely handled at the Python level via the `ThreadPoolExecutor`, which dispatches completely independent chunks to different CPU cores without memory overlaps.*

### 2. Threading and Concurrency
Chunk generation, lighting BFS queues, and database reads are offloaded to a `ThreadPoolExecutor`.
* **Zero Blocking**: Never introduce a locking mechanism (`threading.Lock`) that stalls or halts the main Pygame render loop.
* **Database Safety**: SQLite reads in the background MUST utilize `threading.local()` cursors to prevent connection overlap crashes.
* **Batch Processing**: Ensure tasks submitted to the executor are batched appropriately. Avoid submitting thousands of micro-tasks.

### 3. Memory Management
* **VBO/VAO Pooling:** NEVER instantiate unmanaged OpenGL Vertex Array Objects for chunks. You must ALWAYS recycle buffers through the `world.vbo_pool` `deque` to prevent VRAM leaks during rapid chunk streaming.
* **Garbage Collection**: If you create a dynamic ModernGL texture or buffer (e.g., UI Textures, dynamically generated FBOs), you MUST call `.release()` on it when it is no longer needed. Python's GC will not clear VRAM fast enough!
* **Data Packing:** Maintain the 64-bit and 32-bit integer bit-packing logic for the BFS lighting queues to minimize memory bandwidth usage.

### 4. Asset Guidelines
* **Retro Aesthetic**: All textures and UI elements must adhere to the engine's 16-bit retro visual style.
* **Texture Dimensions**: Base block textures must be exactly 16x16 pixels.
* **OBJ Models**: Custom `.obj` models must only contain vertex (`v`), UV (`vt`), normal (`vn`), and face (`f`) data. Quads are not supported; models must be triangulated.

---

## 🎨 Code Quality & Typing

We use **Ruff** for hyper-fast formatting/linting and **Mypy** for strict static type checking. Your code must pass these checks to be accepted.

By installing the pre-commit hooks (from the setup guide), these checks will run automatically on every commit. However, you can also run them manually:

```bash
# Format code, fix linting errors, and run type checks all at once
pre-commit run --all-files
```

Our style guide is defined in `pyproject.toml` and enforces a 120-character line limit and the use of **single quotes** for strings.

*Note: Due to our use of highly optimized C-extensions (`pyglm`, `moderngl`, `numba`, `pygame`), `mypy` is configured with `ignore_missing_imports = true`. You may use `Any` as a type hint when interacting directly with these libraries, but please use specific types wherever possible.*

### Documentation & Docstrings
All code must be thoroughly documented using **Google Style** docstrings. Proper documentation ensures the engine remains approachable for new contributors and seamlessly integrates with our Sphinx automated documentation builder.

* **Module Docstrings**: Every `.py` file MUST start with a module-level docstring summarizing its overarching purpose, mechanics, and any major systems it interacts with.
* **Class Docstrings**: MUST explain the entity's role in the engine. Include an `Args:` section documenting the parameters required to initialize the object (document parameters at the class level, not under `__init__`).
* **Function & Method Docstrings**: MUST begin with a clear, descriptive action verb (e.g., "Calculates the...", "Renders the..."). Include `Args:` and `Returns:` sections when the logic is complex or when type hints (like `Any`) do not provide enough context.
* **Maintenance & Updates**: If your Pull Request modifies a function's parameters, return type, or core logic, you **MUST** update its associated docstring to reflect the new behavior.

---

## 🧪 Automated Testing

All new logic, UI meshes, mechanics, and terrain features must be accompanied by a suite of tests in the `tests/` directory.
We use `pytest` for unit testing, `pytest-cov` for test coverage, and `mutmut` for mutation testing.

### 1. Writing Meaningful Tests
A test that passes under every condition is a false safety net. Your tests must be designed to break when production code breaks.
* **Test-Driven Development (TDD)**: Try to write the test *before* the logic. Watch it fail (Red), write the minimum code to pass (Green), then Refactor.
* **Audit Your Assertions**: Avoid "No Assertion" tests where you just run a function to see if it crashes without validating the output. Assert specific state changes, and do not mock out so much behavior that you are only testing the mock itself.
* **Boundary Value Analysis**: Push code to its limits. If testing terrain boundaries, test the exact chunk borders (e.g., `x=0`, or maximum world height) rather than just the "happy path" center.

### 2. GUI & Headless Testing
Because Pyrite relies heavily on OpenGL and Pygame event loops, testing mechanics requires a headless approach:
* **Separate Logic from View**: Keep pure data processing (Player health, logic, inventory) separated from visual rendering elements.
* **Mocking Events**: Simulate UI interactions programmatically. Instead of physically opening a window, use `unittest.mock.MagicMock` to construct fake Pygame events (e.g., `event.key = pg.K_f`) and pass them directly to `handle_event()`.

### 3. Coverage vs. Mutation Testing
* **Test Coverage**: Measures the quantitative percentage of source code executed by your tests. Our GitHub Actions CI automatically tracks this using `pytest-cov`. High coverage guarantees your code was run, but doesn't prove the tests actually validate the logic.
* **Mutation Testing (The Ultimate Proof)**: To mathematically verify test quality, we use **Mutmut**. It deliberately injects tiny bugs (mutations) into the source code (like flipping `<` to `>`). If your tests still pass despite the injected bug, your assertions are weak or missing. You can manually trigger the Mutation Testing pipeline in the GitHub Actions tab.

### Running Tests Locally
Before opening a PR, ensure all tests pass. The `pytest` command will automatically use the configurations in `pyproject.toml` to generate a coverage report.
```bash
pytest
```

---

## 🚀 Branches, Commits, and Pull Requests

### 1. Branch Naming
Keep the repository clean by utilizing our standardized branch naming conventions:

| Branch Prefix | Purpose | Example |
| :--- | :--- | :--- |
| **feature/** | Introducing new mechanics or engine capabilities. | `feature/ambient-occlusion` |
| **fix/** | Patching crashes, VRAM leaks, or broken logic. | `fix/chunk-unload-leak` |
| **docs/** | Updating documentation or markdown files. | `docs/lighting-api` |
| **perf/** | Refactoring code specifically to increase framerate or lower memory. | `perf/vectorize-culling` |
| **test/** | Adding or refactoring automated tests. | `test/ui-meshes` |

### 2. Conventional Commits
Please format your commit messages using the Conventional Commits standard. A well-structured commit message is crucial for project maintainability.

#### Anatomy of a Well-Structured Commit Message
A professional commit is broken down into three key metadata fields:

```text
type(scope): subject

body

breakdown
```

*   **SUBJECT LINE:** A short summary (<50 chars) with a lowercase prefix `type` and an optional `(scope)`.
*   **BODY:** (Optional) Provides deep technical context, explaining the "Why" and "What" of the change, rather than the "How".
*   **BREAKDOWN:** (Optional) A detailed bulleted list of specific module side-effects or changes.

**Example:**
```
test: expand test coverage and strengthen assertions

- **UI Meshes**: Replaced loose `.assert_called()` checks with specific `assertEqual` validations for vertex data to catch rendering regressions.
- **Base Mesh**: Added `test_base_mesh.py` to independently verify VBO/VAO lifecycle management and prevent VRAM leaks.
- **Noise Engine**: Added `test_noise.py` to prove that OpenSimplex generates deterministic values from the same seed.
- **Telemetry**: Added `test_profiler.py` to guarantee thread-safe report generation during crashes.
```

#### Commit Types
The commit `type` in the subject line is mandatory and categorizes the change.

| Type | Purpose | Example |
| :--- | :--- | :--- |
| **`feat`** | Introduces a brand new feature or component to the engine. | `feat(world): Implement persistence for dropped items` |
| **`fix`** | Repairs a bug, memory leak, or crash. | `fix(typing): resolve Mypy attribute and module import errors` |
| **`test`** | Adds new tests or hardens/refactors existing test coverage. | `test: clear capsys buffer between profiler report test cases` |
| **`docs`** | Modifies documentation files, Readmes, or internal code docstrings. | `docs(readme): update test coverage badge` |
| **`ci`** | Updates automated workflow configuration files (GitHub Actions). | `ci(workflows): add mutmut results summary to mutation workflow` |
| **`perf`** | Code changes exclusively focused on improving runtime execution speed or memory footprint. | `perf: Optimize chunk loading, VBO pooling, and culling` |
| **`style`** | Changes that do not affect the meaning of the code (whitespace, formatting, linter fixes). | `style(linting): resolve Ruff formatting and whitespace errors` |
| **`refactor`** | A code change that neither fixes a bug nor adds a feature, but improves code cleanliness. | `refactor(assets): Reorganize asset directory structure` |
| **`chore`** | Routine upkeep tasks like updating tooling configs or local dependencies. | `chore(tooling): implement pre-commit hooks for local code validation` |
| **`build`** | Changes that affect the build system or external dependencies. | `build(deps): Bump Ruff and Mypy to latest versions...` |

### 3. Pull Request Requirements
When opening a Pull Request, your description must include:
* The specific Issue ID being addressed (e.g., `Fixes #12`).
* A summary of the implementation approach.
* A checked-off completion of the PR Template checklist (Performance constraints, Ruff, Mypy, and Pytest verifications).

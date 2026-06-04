## Description
<!-- Please include a summary of the change and which issue is addressed. -->
<!-- Provide a summary of the approach taken to implement the feature or fix the bug. -->

Fixes # (issue number)

## Type of change
<!-- Please check the options that apply: -->
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Performance optimization (refactoring specifically to increase framerate or lower memory)

## ⚖️ Architectural Constraints Checklist
<!-- Pyrite has strict performance rules. Please check all that apply to your PR. -->
- [ ] **Numba**: If I modified performance-critical loops, I maintained `@njit(cache=True, nogil=True)` and avoided standard Python objects.
- [ ] **Concurrency**: If I added multithreading/background tasks, I did not introduce locks (`threading.Lock`) that stall the main Pygame render loop.
- [ ] **Memory**: If I added OpenGL geometry, I ensured buffers are recycled through the `vbo_pool` to prevent VRAM leaks.
- [ ] **Assets**: My textures and UI elements match the 16-bit retro aesthetic.

## 🎨 Code Quality Checklist
<!-- As per CONTRIBUTING.md, ensure these checks pass before submitting. -->
- [ ] I have run `ruff format .` locally to auto-format the code layout.
- [ ] I have run `ruff check --fix .` locally and resolved all linting/logical errors.
- [ ] I have run `mypy src/` locally without errors.
- [ ] I have run the test suite `pytest tests/` and all core mechanics tests pass.

## 🚀 Additional Notes
<!-- Add any other context about your pull request here. -->

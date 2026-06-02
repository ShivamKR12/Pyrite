.. _testing:

Testing
=======

This project uses pytest. The repository includes a minimal test in ``tests/test_engine.py`` that imports top-level modules, so run tests from the repository root.

Quickstart
----------

- Create and activate a virtual environment:

  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1   # PowerShell (Windows)
  source .venv/bin/activate        # macOS / Linux
  ```

- Install test dependencies:

  ```bash
  pip install -r requirements-dev.txt
  pip install -r requirements.txt
  ```

- Run the full test suite:

  ```bash
  pytest -q
  ```

- Run a single test file:

  ```bash
  pytest -q tests/test_engine.py
  ```

Useful options
--------------

- `-q` : quiet output (use `-v` for verbose)
- `--maxfail=1` : stop on first failure
- `--cov=src` : require `pytest-cov` to collect coverage
- `-n auto` : run tests in parallel with `pytest-xdist` installed

Continuous integration
----------------------

There is a GitHub Actions workflow at ``.github/workflows/test.yml`` that runs the test job on push and pull requests. The workflow uses `actions/setup-python` and currently specifies Python 3.13; adjust the workflow if you need a different Python version (the code targets Python 3.9+).

Notes
-----

- Run tests from the repository root so imports like `from settings import ...` work correctly.
- If tests fail due to missing native extensions, ensure the development environment has required build tools and that `requirements-dev.txt` is installed.
- For profiling, use `pytest --durations=10` or Python profilers directly; profiling guidance belongs in a separate section when needed.


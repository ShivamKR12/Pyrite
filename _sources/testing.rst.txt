.. _testing:

Testing and Profiling
=====================

This chapter covers unit testing, integration testing, and performance profiling strategies for Pyrite.

Testing Framework Setup
-----------------------

Pyrite uses **pytest** for automated testing. Install with::

    pip install pytest pytest-cov pytest-xdist

Create a test file structure in ``tests/`` directory::

    tests/
        test_engine.py

Run tests with::

    pytest tests/ -v                    # Verbose output
    pytest tests/ -v --cov=src          # With coverage report
    pytest tests/ -v -n 4               # Parallel (4 workers)

Engine Tests
------------

Currently, Pyrite includes basic initialization and state tests within ``test_engine.py``. As the test suite grows, additional tests will be added to this directory.

Continuous Integration
----------------------

**GitHub Actions Workflow Example**

Refer to ``.github/workflows/test.yml``::

    name: Tests
    
    on:
      push:
        branches: [ master, main ]
      pull_request:
        branches: [ master, main ]
    
    jobs:
      test:
        runs-on: ubuntu-latest
        
        steps:
        - uses: actions/checkout@v4
        - name: Set up Python
          uses: actions/setup-python@v5
          with:
            python-version: '3.13'
        
        - name: Install dependencies and test
          run: |
            pip install -r requirements.txt pytest
            pytest tests/

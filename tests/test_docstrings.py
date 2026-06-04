"""
Unit tests to enforce documentation standards.

This ensures that all modules within the source directory strictly adhere 
to the CONTRIBUTING.md guidelines by containing valid module-level docstrings.
"""

import os
import ast
import pytest

def test_module_docstrings() -> None:
    """
    Scans the src/ directory and uses Python's Abstract Syntax Tree (AST)
    to verify that every .py file has a module-level docstring.
    """
    src_dir = 'src'
    if not os.path.exists(src_dir):
        pytest.skip("Source directory not found. Skipping docstring tests.")
        
    missing_docstrings = []
    
    for root, _, files in os.walk(src_dir):
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read(), filename=file)
                    if not ast.get_docstring(tree):
                        missing_docstrings.append(file)
                        
    assert not missing_docstrings, f"Docstring Guideline Violation: The following modules are missing module-level docstrings: {', '.join(missing_docstrings)}"
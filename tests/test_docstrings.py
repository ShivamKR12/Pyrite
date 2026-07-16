"""
Unit tests to enforce documentation standards.

This ensures that all modules within the source directory strictly adhere
to the CONTRIBUTING.md guidelines by containing valid module-level docstrings.
"""

import ast
import os

import pytest


def _add_parent_references(tree: ast.AST) -> None:
    """Annotates each AST node with a reference to its parent."""
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            child.parent = parent  # type: ignore[attr-defined]


def test_module_docstrings() -> None:
    """
    Scans the src/ directory and uses Python's Abstract Syntax Tree (AST)
    to verify that every .py file has a module-level docstring.
    """
    src_dir = 'src'
    if not os.path.exists(src_dir):
        pytest.skip('Source directory not found. Skipping docstring tests.')

    missing_docstrings = []

    for root, _, files in os.walk(src_dir):
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read(), filename=file)
                    if not ast.get_docstring(tree):
                        missing_docstrings.append(file)

    assert not missing_docstrings, (
        f'Docstring Guideline Violation: The following modules are missing module-level docstrings: {", ".join(missing_docstrings)}'
    )


def test_class_docstrings() -> None:
    """
    Scans the src/ directory and verifies that every class definition
    has a class-level docstring.
    """
    src_dir = 'src'
    if not os.path.exists(src_dir):
        pytest.skip('Source directory not found. Skipping class docstring tests.')

    missing_docstrings = []

    for root, _, files in os.walk(src_dir):
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                path = os.path.join(root, file)

                with open(path, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read(), filename=file)

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        if not ast.get_docstring(node):
                            missing_docstrings.append(f'{file}: class {node.name}')

    assert not missing_docstrings, (
        'Docstring Guideline Violation: '
        'The following classes are missing class-level docstrings:\n' + '\n'.join(missing_docstrings)
    )


def test_function_and_method_docstrings() -> None:
    """
    Scans the src/ directory and verifies that every function and method
    has a docstring.
    """
    src_dir = 'src'
    if not os.path.exists(src_dir):
        pytest.skip('Source directory not found. Skipping function docstring tests.')

    missing_docstrings = []

    for root, _, files in os.walk(src_dir):
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                path = os.path.join(root, file)

                with open(path, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read(), filename=file)

                _add_parent_references(tree)

                for node in ast.walk(tree):
                    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue

                    if ast.get_docstring(node):
                        continue

                    parent = node.parent  # type: ignore[union-attr]

                    # Top-level function
                    if isinstance(parent, ast.Module):
                        missing_docstrings.append(f'{file}: function {node.name}()')

                    # Class method
                    elif isinstance(parent, ast.ClassDef):
                        missing_docstrings.append(f'{file}: {parent.name}.{node.name}()')

                    # Ignore nested functions

    assert not missing_docstrings, (
        'Docstring Guideline Violation: '
        'The following functions/methods are missing docstrings:\n' + '\n'.join(missing_docstrings)
    )

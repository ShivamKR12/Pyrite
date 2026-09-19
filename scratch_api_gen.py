import ast
import os
from pathlib import Path


def get_annotation_str(node):
    if node is None:
        return ''
    if hasattr(ast, 'unparse'):
        return ast.unparse(node)
    return ''


def generate():
    out_dir = Path('.agents/skills/pyrite-api')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / 'SKILL.md'

    lines = []
    lines.append('---')
    lines.append('name: pyrite-api')
    lines.append('description: >-')
    lines.append(
        '  The exact, working code API reference for the Pyrite engine. Contains all classes, methods, and signatures. You MUST read this skill before making any modifications to the codebase to prevent hallucinations.'
    )
    lines.append('---')
    lines.append('')
    lines.append('# Pyrite Working API Reference')
    lines.append(
        'This document contains the exact, AST-parsed API signatures of the Pyrite project. Always refer to these signatures rather than guessing.'
    )

    src_dir = Path('src')
    for py_file in sorted(src_dir.rglob('*.py')):
        filepath = str(py_file.as_posix())
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read(), filename=filepath)
        except Exception:
            continue

        file_lines = []
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                file_lines.append(f'### Class `{node.name}`')
                doc = ast.get_docstring(node)
                if doc:
                    file_lines.append(f'> {doc.splitlines()[0]}')
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        args = []
                        # handle self, and other args
                        for a in item.args.args:
                            ann = get_annotation_str(a.annotation)
                            args.append(f'{a.arg}: {ann}' if ann else a.arg)
                        ret = get_annotation_str(item.returns)
                        ret_str = f' -> {ret}' if ret else ''
                        file_lines.append(f'- `def {item.name}({", ".join(args)}){ret_str}`')
            elif isinstance(node, ast.FunctionDef):
                args = []
                for a in node.args.args:
                    ann = get_annotation_str(a.annotation)
                    args.append(f'{a.arg}: {ann}' if ann else a.arg)
                ret = get_annotation_str(node.returns)
                ret_str = f' -> {ret}' if ret else ''
                file_lines.append(f'### `def {node.name}({", ".join(args)}){ret_str}`')
                doc = ast.get_docstring(node)
                if doc:
                    file_lines.append(f'> {doc.splitlines()[0]}')

        if file_lines:
            lines.append(f'\n## `{filepath}`\n')
            lines.extend(file_lines)

    with open(out_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


if __name__ == '__main__':
    generate()

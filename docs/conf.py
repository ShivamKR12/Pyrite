"""
Sphinx configuration file for the Pyrite documentation.
"""

import os
import sys

# Add the src directory to the path so Sphinx can find your modules if needed later
sys.path.insert(0, os.path.abspath('../src'))

project = 'Pyrite'
copyright = '2026, ShivamKR12'
author = 'ShivamKR12'
version = '1.0'
release = '1.0.0'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.mathjax',
    'sphinx.ext.intersphinx',
    'sphinxcontrib.mermaid',
    'sphinx.ext.graphviz',
    'sphinxcontrib.plantuml',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# The Read the Docs theme provides the collapsible sidebar, search, and next/prev links!
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_css_files = ['custom.css']

html_theme_options = {
    'navigation_depth': 4,
    'collapse_navigation': False,
}

# MathJax for formula rendering
mathjax_path = 'https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js'

# Output file base name for HTML build
html_logo = None

# Docstring processing
autodoc_typehints = 'description'
autodoc_member_order = 'bysource'

# Mermaid version for GitHub Pages compatibility
mermaid_version = "10.9.0"

# Intersphinx mapping for external documentation
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'pygame': ('https://www.pyga.me/docs/', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
}

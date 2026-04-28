import os
import sys

# Add the src directory to the path so Sphinx can find your modules if needed later
sys.path.insert(0, os.path.abspath('../src'))

project = 'Pyrite'
copyright = '2026, ShivamKR12'
author = 'ShivamKR12'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
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
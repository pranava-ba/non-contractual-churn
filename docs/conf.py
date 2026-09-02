import os
import sys
sys.path.insert(0, os.path.abspath('../src'))

project = 'Pareto/NBD Extension'
copyright = '2026, Pranava BA, Vyasa R Rajeswaran'
author = 'Pranava BA, Vyasa R Rajeswaran'
release = '1.0.0'

extensions = [
    'myst_parser',
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.mathjax',
    'sphinx.ext.viewcode',
]

source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

master_doc = 'index'
templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_theme_options = {
    'navigation_depth': 4,
    'titles_only': False,
}

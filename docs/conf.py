import os
import sys

sys.path.insert(0, os.path.abspath("../src"))  # or wherever your code lives

# -- Project information -----------------------------------------------------

project = "llm_parse"
author = "Srikanth Sripada"
release = "0.1.0"

# -- General configuration ---------------------------------------------------

extensions = [
    "myst_parser",  # For Markdown support
    "sphinx.ext.autodoc",  # Pull in docstrings
    "sphinx.ext.napoleon",  # Google/NumPy-style docstrings
    "sphinx.ext.viewcode",  # Add links to source code
]

templates_path = ["_templates"]
exclude_patterns = []

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# -- HTML output -------------------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

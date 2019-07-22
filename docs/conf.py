# -*- coding: utf-8 -*-
import sys
import os
import shutil
import datetime

now = datetime.datetime.now()

#### Actualize _apidoc
if os.path.exists('api'):
    shutil.rmtree('api')
os.system('sphinx-apidoc -fo api ../gdshelpers/ ../gdshelpers/test* ../gdshelpers/export/blender_import.py')

sys.path.insert(0, os.path.abspath('../.'))

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.coverage',
    'sphinx.ext.imgmath',
    'matplotlib.sphinxext.plot_directive',
    'sphinx.ext.graphviz',
]

plot_rcparams = {'savefig.bbox': 'tight'}
plot_apply_rcparams = True  # if context option is used

templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'
# General information about the project.
project = u'gdshelpers'
copyright = str(now.year) + u', QPIT Münster'
author = u'QPIT Münster'

import gdshelpers

version = gdshelpers.__version__
release = gdshelpers.__version__

language = None
exclude_patterns = ['_build']

pygments_style = 'sphinx'
todo_include_todos = False

html_theme = 'sphinx_rtd_theme'

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
# html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
# html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
# html_logo = None

# The name of an image file (relative to this directory) to use as a favicon of
# the docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
# html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
# html_extra_path = []

html_sidebars = {'**': ['globaltoc.html', 'relations.html', 'sourcelink.html', 'searchbox.html'], }
html_show_sourcelink = False

htmlhelp_basename = 'gsdhelpersdoc'

latex_elements = {
    'figure_align': 'H'
}

latex_documents = [
    (master_doc, 'GDSHelpers.tex', u'GDSHelpers Documentation',
     author, 'manual'),
]

# latex_logo = None
# latex_use_parts = False
# latex_show_pagerefs = False
latex_show_urls = 'False'
# latex_domain_indices = True


man_pages = [
    (master_doc, 'gdshelpers', u'GDSHelpers Documentation',
     [author], 1)
]

man_show_urls = False

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (master_doc, 'GDSHelpers', u'GDSHelpers Documentation',
     author, 'GDSHelpers', 'A simple Python package for creating or reading GDSII layout files.',
     'Miscellaneous'),
]

autodoc_mock_imports = ['bpy', 'bmesh', 'gdsCAD']
suppress_warnings = ['ref.python']

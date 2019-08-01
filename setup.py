# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
from os import path

import gdshelpers

with open(path.join(path.abspath(path.dirname(__file__)), 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='gdsHelpers',
    version=gdshelpers.__version__,
    author='Helge Gehring, Matthias Blaicher, Wladick Hartmann, Wolfram Pernice',
    author_email='helge.gehring@uni-muenster.de',
    project_urls={
        "Documentation": "https://gdshelpers.readthedocs.io/en/latest/",
        "Bug Tracker": "https://github.com/HelgeGehring/gdshelpers/issues",
        "Source Code": "https://github.com/HelgeGehring/gdshelpers",
    },
    packages=find_packages(),
    platforms='All',
    python_requires='>=3.5',
    license='LGPLv3',
    description='A simple Python package for creating or reading GDSII/OASIS layout files.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    install_requires=['matplotlib', 'numpy', 'shapely', 'scipy'],
    extras_require={
        'gdspy_export': ['gdspy(>=1.3.1)'],
        'gdscad_export': ['gdscad'],
        'oasis_export': ['fatamorgana'],
        'image_import': ['imageio'],
        'image_export': ['descartes'],
        'mesh_export': ['trimesh']
    },
    test_suite='gdshelpers.tests.test_suite',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)',
        'Topic :: Scientific/Engineering :: Physics',
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)'
    ]
)

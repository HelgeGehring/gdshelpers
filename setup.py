# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

import gdshelpers

setup(
    name='gdsHelpers',
    version=gdshelpers.__version__,
    author='Helge Gehring, Matthias Blaicher, Wladick Hartmann, Wolfram Pernice',
    author_email='helge.gehring@uni-muenster.de, matthias@blaicher.com, wladick.hartmann@uni-muenster.de, wolfram.pernice@uni-muenster.de',
    packages=find_packages(),
    platforms='All',
    license='LGPLv3',
    description='A simple Python package for creating or reading GDSII/OASIS layout files.',
    requires=['matplotlib', 'numpy', 'shapely', 'scipy'],
    extras_require={'gdspy_export': ['gdspy(>=1.3.1)'], 'gdscad_export': ['gdscad'], 'oasis_export': ['fatamorgana'],
                    'image_export': ['descartes'], 'mesh_export': ['trimesh']},
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

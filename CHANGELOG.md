Changelog
=========

1.1.1
-----
* Removed \_\_future\_\_ imports and (object) in class definitions for Python 2
* create_holes_for_under_etching now allows ovals and rectangles
* add_route_single_circle_to_port now tapers the waveguide to match the width of the port
* Bugfixes

1.1.0
-----
* Added support for slot waveguides and coplanar waveguides
* Direct GDSII-export is now the standard GDSII-writer
* Added function for generating vortex traps
* Improved shape generation performance of waveguide
* Strip to slot mode converter added
* Bugfixes

1.0.4
-----
* Added part for GDSII-import
* Added direct GDSII-export
* Added DXF-export
* bugfixes

1.0.3
-----
* Structures in Cell are now converted individually for pattern export
* annotate_write_fields now works with Cells instead of gdscad.Cells
* fixed some bugs

1.0.2
-----
* Dependencies are now installed automatically

1.0.1
-----
* Project description now visible on PyPI

1.0.0
-----
* Public release

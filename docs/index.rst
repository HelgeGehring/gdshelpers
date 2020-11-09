*****************************************
Welcome to the gdshelpers' documentation!
*****************************************

The gdshelpers-package is a design framework for lithography-pattern files, developed primarily for integrated optics.
It builds on the shoulder of the `Shapely <http://toblerity.org/shapely/index.html>`_ project.
Please make sure that you have an initial understanding of this.
Afterwards this package should be simple to understand.

It includes adapters to convert any Shapely objects to gdsCAD/gdspy objects - including correct fracturing of polygons and
lines in elements with less than 200 points. An archaic restriction of the GDII file format.
Furthermore, it allows to save the design in the more recent OASIS-format using the fatamorgana-library, which allows smaller files-sizes and has less restrictions.
The user can use an abstraction layer above these libraries, which allows convenient exchange of the underlying library and therefore changing the export-format by a parameter.

In addition it includes a growing selection of optical and superconducting parts, including:

* A waveguide part, allowing easy chaining of bends and straight waveguides.

  - Includes parameterized paths and Bézier curves.
  - Automatic smooth connection to a target point/port
  - The size of the waveguide can be tapered (linear or by a user defined function), which can e.g. be used for optical edge coupling or electronic contact pads
  - Allows to design slot-waveguides and coplanar waveguides (with arbitrary number of rails)
* Different types of splitters:

  - Y-splitter
  - MMI-splitters
  - Directional splitter
* Couplers

  - Grating couplers (allowing apodized gratings)
  - Tapers for hybrid 3D-integration
* Ring and racetrack resonators
* Mach-Zehnder interferometers
* Spirals
* Superconducting nanowire single photon detectors (SNSPDs)
* Superconducting nanoscale Transistors (NTRONs)
* Different types of markers
* QRcodes
* A possibility to include images
* Text-elements for labeling the structures
* GDSII-import

The library itself is designed to be as simple to use as possible:

.. plot::
    :include-source:

    import numpy as np

    from gdshelpers.geometry.chip import Cell
    from gdshelpers.parts.waveguide import Waveguide
    from gdshelpers.parts.coupler import GratingCoupler
    from gdshelpers.parts.resonator import RingResonator
    from gdshelpers.parts.splitter import Splitter
    from gdshelpers.parts.logo import KITLogo, WWULogo
    from gdshelpers.parts.optical_codes import QRCode
    from gdshelpers.parts.text import Text
    from gdshelpers.parts.marker import CrossMarker

    # Generate a coupler with parameters from the coupler database
    coupler1 = GratingCoupler.make_traditional_coupler_from_database([0, 0], 1, 'sn330', 1550)
    coupler2 = GratingCoupler.make_traditional_coupler_from_database([150, 0], 1, 'sn330', 1550)

    coupler1_desc = coupler1.get_description_text(side='left')
    coupler2_desc = coupler2.get_description_text(side='right')

    # And add a simple waveguide to it
    wg1 = Waveguide.make_at_port(coupler1.port)
    wg1.add_straight_segment(10)
    wg1.add_bend(-np.pi/2, 10, final_width=1.5)

    res = RingResonator.make_at_port(wg1.current_port, gap=0.1, radius=20,
                                     race_length=10, res_wg_width=0.5)

    wg2 = Waveguide.make_at_port(res.port)
    wg2.add_straight_segment(30)
    splitter = Splitter.make_at_root_port(wg2.current_port, total_length=20, sep=10, wg_width_branches=1.0)

    wg3 = Waveguide.make_at_port(splitter.right_branch_port)
    wg3.add_route_single_circle_to_port(coupler2.port)

    # Add a marker just for fun
    marker = CrossMarker.make_traditional_paddle_markers(res.center_coordinates)

    # The fancy stuff
    kit_logo = KITLogo([25, 0], 10)
    wwu_logo = WWULogo([100, 30], 30, 2)
    qr_code = QRCode([25, -40], 'https://www.uni-muenster.de/Physik.PI/Pernice', 1.0)
    dev_label = Text([100, 0], 10, 'A0', alignment='center-top')

    # Create a Cell to hold the objects
    cell = Cell('EXAMPLE')

    # Convert parts to gdsCAD polygons
    cell.add_to_layer(1, coupler1, wg1, res, wg2, splitter, wg3, coupler2)
    cell.add_to_layer(2, wwu_logo, kit_logo, qr_code, dev_label)
    cell.add_to_layer(2, marker)
    cell.add_to_layer(3, coupler1_desc, coupler2_desc)
    cell.show()


Citing GDSHelpers
_________________
We would appreciate if you cite the following paper in your publications for which you used GDSHelpers:

Helge Gehring, Matthias Blaicher, Wladick Hartmann, and Wolfram H. P. Pernice,
`"Python based open source design framework for integrated nanophotonic and superconducting circuitry with 2D-3D-hybrid integration" <https://www.osapublishing.org/osac/abstract.cfm?uri=osac-2-11-3091>`_
OSA Continuum 2, 3091-3101 (2019)

Support
_______
If you have problems using GDSHelpers don't hesitate to contact us using
`Discussions <https://github.com/HelgeGehring/gdshelpers/discussions>`_ or `send me a mail <https://github.com/HelgeGehring>`_

Table of contents
_________________

.. toctree::
   :maxdepth: 2

   install_guide/guide
   tutorial/tutorial
   parts/parts
   modifier/modifier
   api/modules


.. only:: html

   Indices and tables
   ==================

   * :ref:`genindex`
   * :ref:`modindex`
   * :ref:`search`

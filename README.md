GDSHelpers
==========

![](https://raw.githubusercontent.com/HelgeGehring/gdshelpers/master/index-1.png)

GDSHelpers in an open-source package for automatized pattern generation for nano-structuring.
It allows exporting the pattern in the GDSII-format and OASIS-format, which are currently mainly used for describing 2D-masks.
Currently the focus is mainly on photonic and superconducting circuitry.
The library consists of growing list of parts, which can be composed into larger circuits.
Currently the following parts are implemented:

* A waveguide part, allowing easy chaing of bends and straight waveguides.
  - Includes parameterized paths and Bézier curves.
  - Automatic smooth connection to a target point/port
* Different types of splitters:
  - Y-splitter
  - MMI-splitters
  - Directional splitter
* Couplers
  - Grating couplers
  - Tapers for hybrid 3D-integration
* Ring and racetrack resonators
* Mach-Zehnder interferometer
* Spirals
* Superconducting nanowire single photon detectors (SNSPDs)
* Superconducting nanoscale Transistors (NTRONs)
* Different types of markers
* QRcodes
* A possibility to include images
* Text-elements for labeling the structures

Besides this it also allows to perform conveniently operations on the design, like:

* Convert the pattern for usage of positive resist
* Create holes around the circuitry, which is e.g. necessary for under-etching

Finally, there are also different formats in which the pattern can be exported:

* The GDSII-format, which is quite often used for (electron beam/...)-lithography
* The OASIS-format, which one of the successors of the GDSII-format
* To an 2D-image
* To stl-objects which are useful e.g. for 3D-renderings
* Directly to a blender-file or an rendered 3D-image

## Documentation
You can find the [documentation on readthedocs](https://gdshelpers.readthedocs.io)

from gdshelpers.geometry import geometric_union

import numpy as np


def convert_to_positive_resist(parts, buffer_radius, outer_resolution=None):
    """
    Convert a list of parts and shapely objects to a positive resist design by
    adding a buffer around the actual design.

    :param parts: List of parts and shapely objects.
    :param buffer_radius: Buffer radius
    :param outer_resolution: Outer buffer circumference resolution. Defaults to one 20th of the buffer radius.
    :return: Converted Shapely geometry.
    :rtype: shapely.base.BaseGeometry
    """
    outer_resolution = buffer_radius / 20. if outer_resolution is None else outer_resolution

    assert buffer_radius > 0, 'The buffer radius must be positive.'
    assert outer_resolution >= 0, 'Resolution must be positive or zero.'

    parts = (parts,) if not isinstance(parts, (tuple, list)) else parts

    # First merge all parts into one big shapely object
    union = geometric_union(parts)

    # Sometimes those polygons do not touch correctly and have micro gaps due to
    # floating point precision. We work around this by inflating the object a tiny bit.
    fixed_union = union.buffer(np.finfo(np.float32).eps, resolution=0)

    # Generate the outer polygon and simplify if required
    outer_poly = union.buffer(buffer_radius)

    if outer_resolution:
        outer_poly = outer_poly.simplify(outer_resolution)

    # Substract the original parts from outer poly
    inverted = outer_poly.difference(fixed_union)

    return inverted

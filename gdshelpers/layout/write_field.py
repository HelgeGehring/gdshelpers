import numpy as np

import shapely.geometry
from gdshelpers.helpers import StandardLayers


def annotate_write_fields(cell, origin='left-top', end='right-bottom', size=100, layer=StandardLayers.wflayer):
    """
    Add write field marker lines to a cell.

    Write fields are rectangular and typically start at the upper left part of a structure. This function adds
    write field lines to a given cell. The bounds are either found automatically or can be given as (x, y) tuple.

    Alignment options are given as ``-`` separated tuple, allowing for combinations of ``left``, ``right``
    with ``bottom``, ``top``.

    :param cell: The cell in which the lines will be added.
    :param origin: Origin of the write field markers.
    :param end: End of the write field markes. Must not be aligned to the write field, however.
    :param size: Size of the write field squares.
    :param layer: Layer on which the write field lines are added.
    """
    corner_labels = {
        'left-top': lambda c: (c.bounds[0], c.bounds[3]),
        'right-to': lambda c: (c.bounds[2], c.bounds[3]),
        'left-bottom': lambda c: (c.bounds[0], c.bounds[1]),
        'right-bottom': lambda c: (c.bounds[2], c.bounds[1])
    }

    assert type(origin) in [list, tuple] or origin in corner_labels.keys(), \
        'origin must either be a tuple or one of %s' % corner_labels.keys()
    assert type(end) in [list, tuple] or end in corner_labels.keys(), \
        'origin must either be a tuple or one of %s' % corner_labels.keys()
    assert size > 0, 'Write field alignment must be a number greater 0'

    # Map string values to true coordinates
    origin = corner_labels[origin](cell) if origin in corner_labels else np.asarray(origin)
    end = corner_labels[end](cell) if end in corner_labels else float(end)

    # Calculate wf x and y positions
    x_begin = origin[0]
    # x_end = (end[0] // size) * (size + (1 if end[0] > origin[0] else -1))
    x_end = end[0]
    x_increasing = x_begin < x_end
    x_pos = np.arange(x_begin, x_end, size) if x_increasing else np.arange(x_begin, x_end, -size)[::-1]

    y_begin = origin[1]
    # y_end = (end[1] // size) * (size + (1 if end[1] > origin[1] else -1))
    y_end = end[1]
    y_increasing = y_begin < y_end
    y_pos = np.arange(y_begin, y_end, size) if y_increasing else np.arange(y_begin, y_end, -size)[::-1]

    x_size = size * (1 if x_increasing else -1)
    y_size = size * (1 if y_increasing else -1)
    for x in x_pos:
        for y in y_pos:
            cell.add_to_layer(layer, shapely.geometry.box(x, y, x + x_size, y + y_size))

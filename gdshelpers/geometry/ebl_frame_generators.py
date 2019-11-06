from itertools import product

from gdshelpers.parts.marker import SquareMarker


def raith_marker_frame(bounds, padding=100, pitch=200, size=20, n=5):
    """
    Generates a list of markers markers in each corner around the given bounding box.
    In each corner the markers are arranged in an L shape. This allows to have more
    markers (for exposure of many steps sometimes more than four markers are necessary)
    with larger distance between the markers (minimize risk of wrong markers being
    found by the EBL) without taking up too much space.

    :param bounds: The bounds around which the markers will be arranged (the marker centers will be inside these bounds)
    :param padding: Spacing between the given bounds and the markers.
        Can also be negative to place the markers inside the bounding box.
    :param pitch: Pitch between two adjacent markers
    :param size: The marker size
    :param n: This determines the number of markers: There will be (2*n)+1 markers in each corner.
    """
    marker_offsets = [(0, 0)] + [(0, (i + 1) * pitch) for i in range(n)] + [((i + 1) * pitch, 0) for i in range(n)]
    signs = product([-1, 1], repeat=2)
    x, y = 0.5 * (bounds[0] + bounds[2]), 0.5 * (bounds[1] + bounds[3])
    half_width, half_height = 0.5 * (bounds[2] - bounds[0]) + padding, 0.5 * (bounds[3] - bounds[1]) + padding

    return [SquareMarker((x + (half_width - off[0]) * sign[0], y + (half_height - off[1]) * sign[1]), size)
            for sign, off in product(signs, marker_offsets)]

from itertools import product

from gdshelpers.parts.marker import SquareMarker


def raith_marker_frame(bounds, padding=100, distance=200, size=20):
    d1 = padding + distance / 2
    d2 = distance / 2

    return (SquareMarker((x + offset_x, y + offset_y), size)
            for x, y, offset_x, offset_y in
            product([bounds[0] - d1, bounds[2] + d1], [bounds[1] - d1, bounds[3] + d1], [-d2, d2], [-d2, d2]))

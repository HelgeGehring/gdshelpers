import numpy as np
from shapely.ops import unary_union
from shapely.prepared import prep
from shapely.geometry import Point, LineString, MultiPolygon

from gdshelpers.geometry import geometric_union


def surround_with_holes(geometry, hole_spacing, hole_radius, padding, max_distance):
    """
    Surrounds the given geometry with holes, which are arranged in a square lattice around the structure.
    This can be used for generating vortex traps like presented in https://doi.org/10.1103/PhysRevApplied.11.064053

    :param geometry: The geometry around which the holes are generated
    :param hole_spacing: Spacing between the holes
    :param hole_radius: Radius of the holes
    :param padding: Padding around the geometry
    :param max_distance: Maximum distance of a hole from the geometry
    :return: Shapely object, which describes the holes
    """
    geometry = geometric_union(geometry if isinstance(geometry, (tuple, list)) else (geometry,))
    buffer_around_waveguide = geometry.buffer(max_distance)
    area_for_holes = prep(buffer_around_waveguide.difference(geometry.buffer(hole_radius + padding)))
    area = buffer_around_waveguide.bounds
    points = (Point(x, y) for x in np.arange(area[0], area[2], hole_spacing) for y in
              np.arange(area[1], area[3], hole_spacing))
    return MultiPolygon([point.buffer(hole_radius) for point in points if area_for_holes.contains(point)])


def fill_waveguide_with_holes_in_honeycomb_lattice(waveguide, spacing, padding, hole_radius):
    """
    Fills a given waveguide with holes which are arranged in a honeycomb structure
    This can be used for generating vortex traps like presented in https://doi.org/10.1103/PhysRevApplied.11.064053

    :param waveguide: Waveguide to be filled
    :param spacing: Spacing between the holes
    :param padding: Minimum distance from the edge of the waveguide to the holes
    :param hole_radius: Radius of the holes
    :return: Shapely object, which describes the holes
    """
    center_coordinates = LineString(waveguide.center_coordinates)
    outline = prep(waveguide.get_shapely_outline().buffer(hole_radius).buffer(-padding - 2 * hole_radius))
    area_for_holes = prep(waveguide.get_shapely_object().buffer(hole_radius).buffer(-padding - 2 * hole_radius))
    circles = []

    offset = 0
    new_circles = True
    while new_circles:
        new_circles = False
        for i, pos in enumerate(np.arange(padding, center_coordinates.length - padding, np.sqrt(3 / 4) * spacing)):
            xy = np.array(center_coordinates.interpolate(pos))
            diff = np.array(center_coordinates.interpolate(pos + padding / 2)) - np.array(
                center_coordinates.interpolate(pos - padding / 2))
            d1 = np.array((-diff[1], diff[0])) / np.linalg.norm(diff)
            for direction in [-1, 1]:
                point = Point(xy + direction * (offset + spacing / 2 * (i % 2)) * d1)
                if outline.contains(point):
                    new_circles = True
                if area_for_holes.contains(point):
                    circles.append(point.buffer(hole_radius))
        offset += spacing
    return unary_union(circles)


if __name__ == '__main__':
    from gdshelpers.geometry.chip import Cell
    from gdshelpers.parts.waveguide import Waveguide

    wg = Waveguide((0, 0), 0, [3, 3, 3, 3, 3])
    wg.add_straight_segment(5)
    wg.add_bend(np.pi / 2, 20)
    wg.width = 15
    wg.add_straight_segment(4)
    wg.add_bend(-np.pi / 2, 20)

    cell = Cell('vortex_traps')
    cell.add_to_layer(1, wg)
    cell.add_to_layer(2, fill_waveguide_with_holes_in_honeycomb_lattice(wg, 1, .1, .15))
    cell.add_to_layer(2, surround_with_holes(wg.get_shapely_outline(), 3, 1, 1, 15))
    cell.show()
    cell.save()

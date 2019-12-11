import numpy as np
from shapely.geometry import LineString, CAP_STYLE

from gdshelpers.geometry import geometric_union, shapely_adapter
from gdshelpers.parts.coupler import GratingCoupler


def create_holes_for_under_etching(underetch_parts, complete_structure, hole_radius, hole_distance, hole_spacing,
                                   hole_length=0, cap_style='round'):
    """
    Creates holes around given parts which can be used for underetching processes

    :param underetch_parts: List of gdshelpers parts around which the holes shall be placed
    :param complete_structure: geometric union of the complete structure, needed to avoid collisions between
        underetching holes and other structures, e.g. waveguides
    :param hole_radius: Radius of the holes in microns
    :param hole_distance: Distance between the holes edges from the the structures in microns
    :param hole_spacing: Distance between the holes in microns
    :param hole_length: Length of the holes (if 0 creates circles, else rectangle like)
    :param cap_style: CAP_STYLE of the holes (i.e. 'round' or 'square', see Shapely Docs)
    :return: Geometric union of the created holes
    """
    cap_style = {'round': CAP_STYLE.round, 'square': CAP_STYLE.square}[cap_style]
    union = geometric_union(underetch_parts)
    no_hole_zone = complete_structure.buffer(0.9 * (hole_distance + hole_radius), resolution=32, cap_style=3)
    poly = union.buffer(hole_distance + hole_radius, resolution=32, cap_style=CAP_STYLE.square)

    base_polygon = shapely_adapter.shapely_collection_to_basic_objs(poly)

    holes = []
    for obj in base_polygon:
        for interior in [obj.exterior] + list(obj.interiors):
            dist = 0
            while dist < interior.length:
                if hole_length == 0:
                    hole = interior.interpolate(distance=dist)
                    dist += hole_spacing + 2 * hole_radius
                else:
                    positions = [interior.interpolate(distance=d) for d in
                                 np.linspace(dist - hole_length / 2 + hole_radius, dist + hole_length / 2 - hole_radius,
                                             10)]
                    dist += hole_spacing + hole_length

                    hole = LineString(positions)
                if not no_hole_zone.contains(hole):
                    holes.append(hole.buffer(hole_radius, cap_style=cap_style))

    return geometric_union(holes)


def _example():
    from gdshelpers.geometry.chip import Cell
    from gdshelpers.parts.waveguide import Waveguide
    from gdshelpers.parts.resonator import RingResonator

    # ==== create some sample structures (straight line with ring resonator)
    wg = Waveguide(origin=(0, 0), angle=np.deg2rad(-90), width=1)
    wg.add_straight_segment(length=5)
    wg.add_bend(np.pi / 2, 5)
    wg2 = Waveguide.make_at_port(wg.current_port)
    wg2.add_straight_segment(15)
    reso = RingResonator.make_at_port(port=wg2.current_port, gap=0.2, radius=5)
    wg2.add_straight_segment(length=15)
    coupler2 = GratingCoupler.make_traditional_coupler_from_database_at_port(wg2.current_port, db_id='si220',
                                                                             wavelength=1550)

    underetching_parts = geometric_union([wg2, reso, coupler2])
    structure = geometric_union([underetching_parts, wg])
    # create the holes with a radius of 0.5 microns, a distance of 2 microns to the structure borders and
    # a distance of 2 microns between the holes
    holes = create_holes_for_under_etching(underetch_parts=underetching_parts, complete_structure=structure,
                                           hole_radius=0.5, hole_distance=2, hole_spacing=3, hole_length=3)

    # create a cell with the structures in layer 1 and the holes in layer 2
    cell = Cell('CELL')
    cell.add_to_layer(1, structure)
    cell.add_to_layer(2, holes)
    # Show the cell
    cell.show()


if __name__ == '__main__':
    _example()

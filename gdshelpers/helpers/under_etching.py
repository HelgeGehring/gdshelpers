import numpy as np
from gdshelpers.geometry import geometric_union, shapely_adapter
from gdshelpers.parts.coupler import GratingCoupler


def create_holes_for_under_etching(underetch_parts, complete_structure, hole_radius, hole_distance, hole_spacing):
    """
    Creates holes around given parts which can be used for underetching processes

    :param underetch_parts: List of gdshelpers parts around which the holes shall be placed
    :param complete_structure: geometric union of the complete structure, needed to avoid collisions between
        underetching holes and other structures, e.g. waveguides
    :param hole_radius: Radius of the holes in microns
    :param hole_distance: Distance of the holes center from the the structures in microns
    :param hole_spacing: Distance between the holes in microns
    :return: Geometric union of the created holes
    """

    union = geometric_union(underetch_parts)
    no_hole_zone = complete_structure.buffer(0.9 * hole_distance, resolution=32, cap_style=3)
    poly = union.buffer(hole_distance, resolution=32, cap_style=3)

    base_polygon = shapely_adapter.shapely_collection_to_basic_objs(poly)

    holes = []
    for obj in base_polygon:
        ext = obj.exterior
        for dist in np.arange(0, ext.length, hole_spacing):
            pos = ext.interpolate(distance=dist)
            if not no_hole_zone.contains(pos):
                holes.append(pos.buffer(hole_radius))
        for interior in obj.interiors:
            for dist in np.arange(0, interior.length, hole_spacing):
                pos = interior.interpolate(distance=dist)
                if not no_hole_zone.contains(pos):
                    holes.append(pos.buffer(hole_radius))

    return geometric_union(holes)


if __name__ == '__main__':
    import gdsCAD.core
    from gdshelpers.parts.waveguide import Waveguide
    from gdshelpers.parts.resonator import RingResonator
    from gdshelpers.geometry import convert_to_gdscad

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
                                           hole_radius=0.5, hole_distance=2, hole_spacing=3)

    # create a cell with the structures in layer 1 and the holes in layer 2
    cell = gdsCAD.core.Cell('CELL')
    cell.add(convert_to_gdscad(structure, layer=1))
    cell.add(convert_to_gdscad(holes, layer=2))
    # Show the cell
    cell.show()

from __future__ import print_function, division

import math
import numpy as np
import shapely.geometry
import shapely.affinity

from gdshelpers.parts import Port
from gdshelpers.geometry import geometric_union
from gdshelpers.parts.waveguide import Waveguide


class CNT(object):
    """
    Creates a CNT source (Electrodes + tapered waveguide) at waveguide port.

    This class implements the electrodes and tapered waveguide for an integrated CNT source.
    It provides the electrodes ports and the connecting waveguide port.
    The Electrode is made up of three part: the round head (defined by the radius) followed by a
    straight fine line of length el_l_fine, followed by a taper to final_width with length el_l_taper and
    a box with length el_l_straight.

    :param origin: Origin of the resonator, which is the start of the input waveguide.
    :param angle: Angle of the input waveguide.
    :param width: Width of the angle waveguide.
    :param gap: Gap between electrode tip and waveguide.
    :param l_taper: length of the waveguide taper used before and after the cnt. i.a. 2*l_taper will be
        added to the waveguide
    :param w_taper: width of waveguide at the cnts position
    :param el_l_straight: length of electrode part with largest thickness
    :param el_l_taper: length over which 2*el_radius is tapered to el_final_width
    :param el_final_width: largest width of the electrode
    :param el_l_fine: length of small strip to the tip of the electrode
    :param el_radius: radius of electrodes tip
    :param n_points: number of points used to make electrode tip polygon
    """

    def __init__(self, origin, angle, width, gap=0.15, l_taper=10, w_taper=0.9, el_l_straight=8, el_l_taper=2.5,
                 el_final_width=2, el_l_fine=1.4,
                 el_radius=0.1, n_points=128):
        assert gap >= 0, 'Gap must not be negative'
        assert el_radius > 0, 'The electrode radius must not be negative'

        self._origin_port = Port(origin, angle, width)
        cnt_port = self._origin_port.copy().longitudinal_offset(l_taper)
        cnt_port.width = w_taper
        self._cnt_port = cnt_port
        self._out_port = self._origin_port.copy().longitudinal_offset(2 * l_taper)

        self.gap = gap
        self.points = n_points
        self.el_l_taper = el_l_taper
        self.radius = el_radius
        self.el_l_straight = el_l_straight
        self.final_width = el_final_width
        self.el_l_fine = el_l_fine
        self.l_taper = l_taper

        self.el_shift_x = 0
        self.el_shift_y = self._cnt_port.width / 2 + self.gap + self.radius
        self.angle = self._origin_port.angle + math.pi / 2
        self.sample_distance = 0.015

        self.electrodes = None
        self.waveguide = []

        self._make_waveguide()
        self._make_electrodes()

    @classmethod
    def make_at_port(cls, port, **kwargs):
        default_port_param = dict(port.get_parameters())
        default_port_param.update(kwargs)
        del default_port_param['origin']
        del default_port_param['angle']
        del default_port_param['width']

        return cls(port.origin, port.angle, port.width, **default_port_param)

    @property
    def left_electrode_port(self):
        offset = self.el_shift_y + self.el_l_fine + self.el_l_taper + self.el_l_straight
        port = self._cnt_port.parallel_offset(offset)
        port.width = self.final_width
        port.angle = self.angle
        return port

    @property
    def right_electrode_port(self):
        offset = -(self.el_shift_y + self.el_l_fine + self.el_l_taper + self.el_l_straight)
        port = self._cnt_port.parallel_offset(offset)
        port.width = self.final_width
        port.angle = self.angle + math.pi
        return port

    @property
    def out_port(self):
        return self._out_port.copy()

    @property
    def in_port(self):
        return self._origin_port.copy().inverted_direction

    def _make_waveguide(self):
        wg = Waveguide.make_at_port(self._origin_port)
        wg.add_bezier_to_port(self._cnt_port.inverted_direction, 3, sample_distance=self.sample_distance)
        wg.add_bezier_to_port(self._out_port.inverted_direction, 3, sample_distance=self.sample_distance)
        self.waveguide.append(wg)

    def _make_electrodes(self):
        phi = np.linspace(math.pi, 2 * math.pi, self.points)

        circle_points = np.array([self.radius * np.cos(phi), self.radius * np.sin(phi)]).T

        first_part_points = [circle_points[0], (-self.radius, self.el_l_fine), (self.radius, self.el_l_fine),
                             circle_points[-1]]

        taper_points = [first_part_points[1], (-self.final_width / 2, self.el_l_fine + self.el_l_taper),
                        (self.final_width / 2, self.el_l_fine + self.el_l_taper), first_part_points[-2]]

        last_part_points = [taper_points[1],
                            (-self.final_width / 2, self.el_l_fine + self.el_l_taper + self.el_l_straight),
                            (self.final_width / 2, self.el_l_fine + self.el_l_taper + self.el_l_straight),
                            taper_points[-2]]

        cirlce_polygon = shapely.geometry.Polygon(circle_points)
        first_part_polygon = shapely.geometry.Polygon(first_part_points)
        taper_polygon = shapely.geometry.Polygon(taper_points)
        last_part_polygon = shapely.geometry.Polygon(last_part_points)

        polygon = geometric_union([cirlce_polygon, taper_polygon, first_part_polygon, last_part_polygon])

        upper_electrode = shapely.affinity.translate(polygon, self.el_shift_x, self.el_shift_y)
        lower_electrode = shapely.affinity.scale(upper_electrode, xfact=-1, yfact=-1, origin=(0, 0))

        electrode = geometric_union([lower_electrode, upper_electrode])
        electrode = shapely.affinity.rotate(electrode, self._cnt_port.angle, use_radians=True)
        electrode = shapely.affinity.translate(electrode, self._cnt_port.origin[0], self._cnt_port.origin[1])
        self.electrodes = electrode

    def get_shapely_object(self):
        return geometric_union(self.waveguide)


def _cnt_example():
    import gdsCAD.core
    from gdshelpers.geometry import convert_to_gdscad
    from gdshelpers.parts.waveguide import Waveguide

    # photonics
    start_port = Port((0, 0), 0, 1.1)
    wg = Waveguide.make_at_port(start_port)
    wg.add_straight_segment(20)
    cnt_port = wg.current_port
    cnt = CNT.make_at_port(cnt_port, gap=0.4, l_taper=100, w_taper=0.1)
    wg2 = Waveguide.make_at_port(cnt.out_port)
    wg2.add_bend(np.pi / 4, 100)

    cnt2 = CNT.make_at_port(wg2.current_port, gap=0.15)

    union = geometric_union([wg, cnt, wg2, cnt2])

    # electrodes
    el1_l = Waveguide.make_at_port(cnt.left_electrode_port)
    el1_l.add_straight_segment(100, 100)
    el1_r = Waveguide.make_at_port(cnt.right_electrode_port)
    # el1_r.add_straight_segment(100)

    port = cnt2.left_electrode_port
    port.width = 20
    el2_l = Waveguide.make_at_port(port)
    el2_l.add_straight_segment(30)

    el = geometric_union([cnt.electrodes, cnt2.electrodes, el1_l, el1_r, el2_l])

    cell = gdsCAD.core.Cell('test')
    cell.add(convert_to_gdscad(union))
    cell.add(convert_to_gdscad(el, layer=2))
    layout = gdsCAD.core.Layout()
    layout.add(cell)
    layout.show()
    layout.save('CNT_Device_Test.gds')


if __name__ == '__main__':
    _cnt_example()

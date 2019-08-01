import numpy as np
import shapely.geometry
import shapely.affinity
from shapely.geometry import Polygon, Point

from gdshelpers.geometry import geometric_union
from gdshelpers.parts import Port
from gdshelpers.parts.waveguide import Waveguide
from gdshelpers.geometry.chip import Cell


class SNSPD(object):
    def __init__(self, origin, angle, width, nw_width, nw_gap, nw_length, wing_span, wing_height, electrodes_pitch,
                 electrodes_gap, electrodes_height, waveguide_tapering, n_points=128):
        assert nw_gap > 0., 'Nanowire gap must be a positive value'
        assert nw_length > 0., 'Nanowire length must be a positive value'
        assert nw_width > 0., 'Nanowire width must be a positive value'

        # Let's directly create a port object. This simplifies later creation of the geometry
        # as well as checking the user parameters while creating the port.
        self._origin_port = Port(origin, angle, width)

        # Remember all the other stuff we got
        self.nw_gap = nw_gap
        self.nw_width = nw_width
        self.points = n_points
        self.nw_length = nw_length
        self.wing_span = wing_span
        self.wing_height = wing_height
        self.electrodes_pitch = electrodes_pitch
        self.electrodes_gap = electrodes_gap
        self.electrodes_height = electrodes_height
        self.waveguide_tapering = waveguide_tapering
        self.make_nanowire()
        self.make_waveguide()
        self.make_electrodes()

    @classmethod
    def make_at_port(cls, port, nw_width, nw_gap, nw_length, wing_span, wing_height, electrodes_pitch, electrodes_gap,
                     electrodes_height, waveguide_tapering, *kwargs):
        default_port_param = dict(port.get_parameters())
        default_port_param.update(kwargs)
        del default_port_param['origin']
        del default_port_param['angle']
        del default_port_param['width']
        return cls(port.origin, port.angle, port.width, nw_width, nw_gap, nw_length, wing_span, wing_height,
                   electrodes_pitch, electrodes_gap, electrodes_height, waveguide_tapering, **default_port_param)

    @staticmethod
    def _cub_bezier(origin, destination, aux_orig, aux_dest, n_points=200):
        x0, y0 = origin[0], origin[1]
        x1, y1 = aux_orig[0], aux_orig[1]
        x2, y2 = aux_dest[0], aux_dest[1]
        x3, y3 = destination[0], destination[1]

        a = x3 - 3 * x2 + 3 * x1 - x0
        b = 3 * x2 - 6 * x1 + 3 * x0
        c = 3 * x1 - 3 * x0
        d = x0

        e = y3 - 3 * y2 + 3 * y1 - y0
        f = 3 * y2 - 6 * y1 + 3 * y0
        g = 3 * y1 - 3 * y0
        h = y0

        points = []
        for t in range(n_points):
            t = t / float(n_points - 1)
            x = a * (t ** 3) + b * (t ** 2) + c * t + d
            y = e * (t ** 3) + f * (t ** 2) + g * t + h
            points.append([x, y])
        return points

    def get_shapely_object(self):
        return self.nw

    def make_nanowire(self):
        # U-shaped nanowire
        self.nanowire_port = Port(origin=(0, 0), angle=0, width=self.nw_width)
        nw = Waveguide.make_at_port(self.nanowire_port, width=self.nw_width)
        tip_radius = 0.5 * self.nw_gap + 0.5 * self.nw_width
        nw.add_bend(0.5 * np.pi, tip_radius)
        nw.add_straight_segment(self.nw_length - tip_radius)

        # Wing Square Pads which will overlap with the contact pads
        wing_tapering_origin = np.array(nw.current_port.origin)
        self.wing_pad_bottom_left = wing_tapering_origin + (
            (0.5 * self.wing_span - (self.nw_width + 0.5 * self.nw_gap)), 0.5 * self._origin_port.width)
        self.wing_pad_bottom_right = self.wing_pad_bottom_left + (0.5 * self.wing_span, 0)
        self.wing_pad_top_right = self.wing_pad_bottom_right + (0, self.wing_height)
        self.wing_pad_top_left = self.wing_pad_bottom_left + (0, self.wing_height)
        wing_pad = Polygon(
            [self.wing_pad_bottom_left, self.wing_pad_bottom_right, self.wing_pad_top_right, self.wing_pad_top_left])

        # Bezier tapering from nanowire to wing pads
        nw_left_side_coord = wing_tapering_origin - (0.5 * self.nw_width, 0)
        nw_right_side_coord = wing_tapering_origin + (0.5 * self.nw_width, 0)

        self.aux_origin_top_line = nw_left_side_coord + np.array(
            [0, 0.2 * (self.wing_pad_top_left[1] - nw_left_side_coord[1])])
        self.aux_dest_top_line = nw_left_side_coord + np.array(
            [0.8 * (self.wing_pad_top_left[0] - nw_left_side_coord[0]),
             0.4 * (self.wing_pad_top_left[1] - nw_left_side_coord[1])])

        wing_tapering_top_line = self._cub_bezier(nw_left_side_coord, self.wing_pad_top_left, self.aux_origin_top_line,
                                                  self.aux_dest_top_line)

        self.aux_origin_bottom_line = nw_right_side_coord + np.array(
            [0.1 * (self.wing_pad_bottom_left[0] - nw_right_side_coord[0]),
             self.wing_pad_bottom_left[1] - nw_right_side_coord[1]])
        self.aux_dest_bottom_line = nw_right_side_coord + np.array(
            [0, 0.5 * (self.wing_pad_bottom_left[1] - nw_right_side_coord[1])])
        wing_tapering_bottom_line = self._cub_bezier(self.wing_pad_bottom_left, nw_right_side_coord,
                                                     self.aux_origin_bottom_line, self.aux_dest_bottom_line)

        wing_tapering = Polygon(wing_tapering_top_line + wing_tapering_bottom_line)

        wing = geometric_union([wing_pad, wing_tapering])

        nw = geometric_union([nw, wing])
        nw_l = shapely.affinity.scale(nw, xfact=-1.0, yfact=1.0, zfact=1.0,
                                      origin=[self.nanowire_port.origin[0], self.nanowire_port.origin[1], 0])
        nw = geometric_union([nw, nw_l])
        nw = shapely.affinity.translate(nw, yoff=0.5 * self.nw_width)
        nw = shapely.affinity.rotate(nw, self._origin_port.angle - 0.5 * np.pi, origin=[0, 0], use_radians=True)
        self.nw = shapely.affinity.translate(nw, xoff=self._origin_port.origin[0], yoff=self._origin_port.origin[1])

        re_origin = self._origin_port.origin
        re_angle = self._origin_port.angle - 0.5 * np.pi
        rep = Port(origin=re_origin, angle=re_angle, width=self.wing_height)
        self.rep = rep.longitudinal_offset(self.wing_pad_bottom_left[0] + 0.25 * self.wing_span).parallel_offset(
            self.wing_pad_bottom_left[1] + 0.5 * self.wing_height)
        self.lep = self.rep.longitudinal_offset(-1.5 * self.wing_span).rotated(np.pi)

    def make_waveguide(self):
        wg = Waveguide.make_at_port(self._origin_port)
        wg.add_straight_segment(self.nw_length + 0.5 * self.nw_width + self.wing_height)
        if self.waveguide_tapering:
            wg.add_straight_segment(2. * self._origin_port.width, final_width=0.01)
        self.waveguide_port = wg.current_port
        wg = geometric_union([wg])
        nw = self.nw.difference(wg)
        buffer = nw.buffer(.2)
        self.wg = geometric_union([wg, buffer])

    def make_electrodes(self):
        bottom_left = self.nanowire_port.origin + np.array([0.5 * self.electrodes_gap, self.nw_length + 25.])
        top_left = bottom_left + (0, self.electrodes_height)
        electrode_width = self.electrodes_pitch - self.electrodes_gap
        top_right = top_left + (electrode_width, 0)
        bottom_right = (top_right[0], bottom_left[1])
        bottom_middle = np.array((bottom_right[0] - 0.5 * electrode_width, self.wing_pad_bottom_left[1]))
        pad = Polygon(
            [self.wing_pad_bottom_left, self.wing_pad_top_left, self.wing_pad_top_right, bottom_left, top_left,
             top_right, bottom_right, bottom_middle])
        pad = geometric_union([pad])
        pad = shapely.affinity.translate(pad, yoff=0.5 * self.nw_width)
        pad_l = shapely.affinity.scale(pad, xfact=-1.0, yfact=1.0, zfact=1.0, origin=[0, 0, 0])
        pad = geometric_union([pad, pad_l])

        pad = shapely.affinity.rotate(pad, self._origin_port.angle - 0.5 * np.pi,
                                      origin=[0, 0],
                                      use_radians=True)
        self.pad = shapely.affinity.translate(pad, xoff=self._origin_port.origin[0], yoff=self._origin_port.origin[1])

    def get_waveguide(self):
        return self.wg

    def get_electrodes(self):
        return self.pad

    def get_passivation_layer(self, passivation_buffer=0.1):
        buffer = self.nw.buffer(passivation_buffer)
        passivation_layer = geometric_union([buffer])
        return passivation_layer

    def get_aux_top(self):
        return self.aux_origin_top_line, self.aux_dest_top_line

    def get_aux_bottom(self):
        return self.aux_origin_bottom_line, self.aux_dest_bottom_line

    @property
    def right_electrode_port(self):
        return self.rep

    @property
    def left_electrode_port(self):
        return self.lep

    @property
    def current_port(self):
        return self.waveguide_port


snspd_parameters = {
    'nw_width': 0.1,
    'nw_gap': 0.1,
    'nw_length': 70.,
    'wing_span': 10.,
    'wing_height': 5.,
    'electrodes_pitch': 125.,
    'electrodes_gap': 45.,
    'electrodes_height': 600.,
    'waveguide_tapering': False,
}


def example():
    start_port = Port((0, 0), 0.5 * np.pi, 1.)
    wg1 = Waveguide.make_at_port(start_port)
    wg1.add_straight_segment(100.)
    # wg1.add_bend(0, 60.)
    detector = SNSPD.make_at_port(wg1.current_port, **snspd_parameters)
    wg = detector.get_waveguide()
    electrodes = detector.get_electrodes()
    pl = detector.get_passivation_layer(passivation_buffer=0.2)

    wg2 = Waveguide.make_at_port(detector.current_port)
    wg2.add_straight_segment(50.)
    # cell = gdsCAD.core.Cell('test')
    cell = Cell('test')
    cell.add_to_layer(3, Point(detector.get_aux_top()[0]).buffer(0.05))
    cell.add_to_layer(4, Point(detector.get_aux_top()[1]).buffer(0.05))
    cell.add_to_layer(3, Point(detector.get_aux_bottom()[0]).buffer(0.05))
    cell.add_to_layer(4, Point(detector.get_aux_bottom()[1]).buffer(0.05))
    cell.add_to_layer(3, wg1)

    cell.add_to_layer(1, detector)
    cell.add_to_layer(2, detector.get_waveguide())
    cell.add_to_layer(6, detector.get_electrodes())
    cell.add_to_layer(5, pl)

    # cell.add_to_layer(6, detector.right_electrode_port.debug_shape)
    # cell.add_to_layer(6, detector.left_electrode_port.debug_shape)
    cell.add_to_layer(3, wg2)
    cell.save('SNSPD_test.gds')
    cell.show()


if __name__ == '__main__':
    example()

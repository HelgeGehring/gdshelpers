import numpy as np
from shapely.affinity import rotate, translate
from shapely.geometry import Polygon
from itertools import chain

from gdshelpers.geometry import convert_to_gdscad
from gdshelpers.helpers.bezier import CubicBezierCurve
from gdshelpers.geometry import geometric_union
from gdshelpers.parts.port import Port
from gdshelpers.parts.waveguide import Waveguide


class Ntron(object):
    def __init__(self, origin, angle, gate_width_1, gate_width_2, choke_width_1, choke_width_2, choke_length_2,
                 choke_length_3, choke_point_2=(1.0 / 2, 0), choke_point_3=(1, 1.0 / 2), points_per_curve=1000,
                 gate_start=0, gate_point_2=(1.0 / 3, 0), gate_point_3=(2.0 / 3, 1), channel_point_2=(1.0 / 3, 0),
                 channel_point_3=(2.0 / 3, 0), channel_length=2.5, outer_channel_width=0.4, inner_channel_width=0.2,
                 channel_position=0.5, gate_length=0.5, choke_start=0.5, gate_choke_length=0.2):
        """
        Superconducting nanoscale Transistor, for instance to amplify SNSPD signals or creating logical circuits.

        Link: https://pubs.acs.org/doi/10.1021/nl502629x
        All standard parameters are taken from paper above.
        Link Bezier explanation: https://javascript.info/bezier-curve

        :param origin: device origin coordinate (x,y)
        :param angle: device angle (gate to x axis)
        :param gate_width_1: outer width of the gate port
        :param gate_width_2: connection gate-choke, should be same as choke width_1
        :param choke_width_1: outer width of the choke
        :param choke_width_2: Inner choke width, which is the bottleneck and the most important parameter
        :param choke_length_2: length of the gate sided choke bezier shape
        :param choke_length_3: length of the channel sided choke bezier shape
        :param choke_point_2: 2nd bezier point in a rectangle (Look Bezier explanation above)
        :param choke_point_3: 3rd bezier point in a rectangle (Look Bezier explanation above)
        :param points_per_curve: number of of points per Bezier curve used to create a shapely geometry
        :param gate_start: starting x pos of the gate section, should be zero
        :param gate_point_2: 2nd bezier point in a rectangle (Look Bezier explanation above)
        :param gate_point_3: 3rd bezier point in a rectangle (Look Bezier explanation above)
        :param channel_point_2: 2nd bezier point in a rectangle (Look Bezier explanation above)
        :param channel_point_3: 3rd bezier point in a rectangle (Look Bezier explanation above)
        :param channel_length: length of the channel
        :param outer_channel_width: starting width of the channel at the gates
        :param inner_channel_width: end width in the middle of the channel
        :param channel_position: channel position corresponding to the _gate, for 0 choke is on the bottom, for 1 on the top
        :param gate_length: the length of the bezier calculated shape of the gate
        :param choke_start: starting x pos of the choke section, should be equal to gate_length
        :param gate_choke_length:
        """

        self._origin = origin
        self._angle = angle
        self._points_per_curve = points_per_curve
        # Gate parameters
        self._gate_start = gate_start
        self._gate_width_1 = gate_width_1
        self._gate_width_2 = gate_width_2
        self._gate_length = gate_length
        self._gate_point_2 = gate_point_2
        self._gate_point_3 = gate_point_3

        # Choke parameters
        self._choke_start = choke_start
        self._choke_width_1 = choke_width_1
        self._choke_width_2 = choke_width_2
        self._gate_choke_length = gate_choke_length
        self._choke_length_2 = choke_length_2
        self._choke_length_3 = choke_length_3
        self._choke_point_2 = choke_point_2
        self._choke_point_3 = choke_point_3

        # Channel parameter
        self._channel_length = channel_length
        self._outer_channel_width = outer_channel_width
        self._inner_channel_width = inner_channel_width
        self._channel_point_2 = channel_point_2
        self._channel_point_3 = channel_point_3
        self._channel_position = channel_position

    # symmetric bezier shaped polygon
    def _bezier_guide_symm(self, start, width_1, width_2, length, p2, p3):
        top_curve = CubicBezierCurve(
            *[(start, width_1 / 2), (start + p2[0] * length, width_1 / 2 - p2[1] * width_2 / 2),
              (start + p3[0] * length, width_1 / 2 - p3[1] * (width_1 / 2 - width_2 / 2)),
              (start + length, width_2 / 2)])

        bottom_curve = CubicBezierCurve(
            *[(start, -width_1 / 2), (start + p2[0] * length, -width_1 / 2 + p2[1] * width_2 / 2),
              (start + p3[0] * length, -width_1 / 2 + p3[1] * (width_1 / 2 - width_2 / 2)),
              (start + length, -width_2 / 2)])

        y_bottom = bottom_curve.evaluate(np.linspace(1, 0, self._points_per_curve))
        y_top = top_curve.evaluate(np.linspace(0, 1, self._points_per_curve))

        return Polygon(chain(zip(y_top[0], y_top[1]), zip(y_bottom[0], y_bottom[1])))

    # one side flat and one side bezier shaped polygon
    def _bezier_guide_channel(self, start, outer_width, inner_width, length, p2, p3):
        top_curve = CubicBezierCurve(
            (start, outer_width), (start + p2[0] * length / 2., outer_width - p2[1] * inner_width),
            (start + p3[0] * length / 2., inner_width + p3[1] * (outer_width - inner_width)),
            (start + length / 2., inner_width))
        bottom_curve = CubicBezierCurve((start + length / 2., inner_width),
                                        (start + length / 2. + p2[0] * length / 2., inner_width + p2[1] * inner_width),
                                        (start + length / 2. + p3[0] * length / 2.,
                                         outer_width - p3[1] * (outer_width - inner_width)),
                                        (start + length, outer_width))

        return Polygon(
            chain(zip(*top_curve.evaluate(np.linspace(0, 1, self._points_per_curve))), zip(*bottom_curve.evaluate(
                np.linspace(0, 1, self._points_per_curve))), ([(length, 0), (0, 0)])))

    # Creating the different par polygons
    def _gate(self):
        return self._bezier_guide_symm(self._gate_start, self._gate_width_1, self._gate_width_2, self._gate_length,
                                       self._gate_point_2, self._gate_point_3)

    def _choke_channel(self):
        return self._bezier_guide_symm(self._choke_start, self._choke_width_1, self._choke_width_1,
                                       self._gate_choke_length, self._gate_point_2, self._gate_point_2)

    def _choke_left(self):
        return self._bezier_guide_symm(self._choke_start + self._gate_choke_length, self._choke_width_1,
                                       self._choke_width_2, self._choke_length_2, self._gate_point_2,
                                       self._gate_point_3)

    def _choke_right(self):
        return self._bezier_guide_symm(self._gate_length + self._gate_choke_length + self._choke_length_2,
                                       self._choke_width_2, self._choke_width_1, self._choke_length_3,
                                       self._choke_point_2,
                                       self._choke_point_3)

    def _channel(self):
        channel_object = self._bezier_guide_channel(0, self._outer_channel_width, self._inner_channel_width,
                                                    self._channel_length, self._channel_point_2, self._channel_point_3)
        x_offset = (self._gate_length + self._gate_choke_length + self._choke_length_2 + self._choke_length_3)
        y_offset = (1 - self._channel_position) * self._channel_length
        return translate(rotate(channel_object, -np.pi / 2, (0, 0), True), x_offset, y_offset, 0)

    # Unite and translate the polygons parts
    def get_shapely_object(self):
        object = geometric_union(
            [self._gate(), self._choke_channel(), self._choke_left(), self._choke_right(), self._channel()])
        rotated_object = rotate(object, self._angle, (0, 0), True)
        return translate(rotated_object, self._origin[0], self._origin[1], 0)

    @classmethod
    def make_at_port_(cls, port, gate_width_1, gate_width_2, choke_width_1, choke_width_2, choke_length_2,
                      choke_length_3, choke_point_2=(1.0 / 2, 0), choke_point_3=(1, 1.0 / 2), points_per_curve=1000,
                      gate_start=0, gate_point_2=(1.0 / 3, 0), gate_point_3=(2.0 / 3, 1), channel_point_2=(1.0 / 3, 0),
                      channel_point_3=(2.0 / 3, 0), channel_length=2.5, outer_channel_width=0.4,
                      inner_channel_width=0.2,
                      channel_position=0.3, gate_length=0.5, choke_start=0.5, gate_choke_length=0.2, target='_gate'):
        """
        Class method to directly place a ntron to a given port, connected to a chosen port

        :param port: port from the connecting structure
        :param gate_width_1: outer width of the _gate port
        :param gate_width_2: connection gate-choke, should be same as choke_width_1
        :param choke_width_1: outer width of the choke
        :param choke_width_2: Inner choke width, which is the bottleneck and the most important parameter
        :param choke_length_2: length of the gate sided choke bezier shape
        :param choke_length_3: length of the channel sided choke bezier shape
        :param choke_point_2: 2nd bezier point in a rectangle (Look Bezier explanation above)
        :param choke_point_3: 3rd bezier point in a rectangle (Look Bezier explanation above)
        :param points_per_curve: number of of points per Bezier curve used to create a shapely geometry
        :param gate_start: starting x pos of the gate section, should be zero
        :param gate_point_2: 2nd bezier point in a rectangle (Look Bezier explanation above)
        :param gate_point_3: 3rd bezier point in a rectangle (Look Bezier explanation above)
        :param channel_point_2: 2nd bezier point in a rectangle (Look Bezier explanation above)
        :param channel_point_3: 3rd bezier point in a rectangle (Look Bezier explanation above)
        :param channel_length: length of the channel
        :param outer_channel_width: starting width of the channel at the gates
        :param inner_channel_width: end width in the middle of the channel
        :param channel_position: channel position corresponding to the gate, for 0 choke is on the bottom, for 1 on the top
        :param gate_length: the length of the bezier calculated shape of the gate
        :param choke_start: starting x pos of the choke section, should be equal to gate_length
        :param gate_choke_length:
        :param target: the ntron port to connect to
        :return:
        """

        # Calculation of the target relative parameters
        if target == 'gate':
            return cls(port.origin, port.angle, gate_width_1, gate_width_2, choke_width_1, choke_width_2,
                       choke_length_2,
                       choke_length_3, choke_point_2, choke_point_3, points_per_curve, gate_start, gate_point_2,
                       gate_point_3, channel_point_2, channel_point_3, channel_length, outer_channel_width,
                       inner_channel_width, channel_position, gate_length, choke_start, gate_choke_length)
        if target == 'source':
            x = (channel_position * channel_length)
            y = (gate_length + gate_choke_length + choke_length_2 + choke_length_3 + outer_channel_width / 2)

            x_off = port.origin[0] + np.cos(port.angle) * x - np.sin(port.angle) * y
            y_off = port.origin[1] + np.sin(port.angle) * x + np.cos(port.angle) * y

            return cls(
                (x_off, y_off), port.angle - np.pi / 2, gate_width_1, gate_width_2, choke_width_1, choke_width_2,
                choke_length_2,
                choke_length_3)
        if target == 'drain':
            x = (1 - channel_position) * channel_length
            y = -gate_length - gate_choke_length - choke_length_2 - choke_length_3 - outer_channel_width / 2

            x_off = port.origin[0] + np.cos(port.angle) * x - np.sin(port.angle) * y
            y_off = port.origin[1] + np.sin(port.angle) * x + np.cos(port.angle) * y

            return cls((x_off, y_off), port.angle + np.pi / 2, gate_width_1, gate_width_2, choke_width_1, choke_width_2,
                       choke_length_2, choke_length_3)

    @property
    def origin(self):
        return self._origin

    @property
    def angle(self):
        return self._angle

    @property
    def width(self):
        return self._gate_width_1

    @property
    def port_drain(self):
        x = (self._gate_length + self._gate_choke_length + self._choke_length_2 +
             self._choke_length_3 + self._outer_channel_width / 2.)
        y = ((1 - self._channel_position) * self._channel_length)

        x_off = self.origin[0] + np.cos(self._angle) * x - np.sin(self._angle) * y
        y_off = self.origin[1] + np.sin(self._angle) * x + np.cos(self._angle) * y

        return Port((x_off, y_off), self._angle + np.pi / 2., self._outer_channel_width)

    @property
    def port_gate(self):
        return Port(self.origin, self._angle + np.pi, self._gate_width_1)

    @property
    def port_source(self):
        x = (self._gate_length + self._gate_choke_length + self._choke_length_2 + self._choke_length_3
             + self._outer_channel_width / 2.)
        y = (-self._channel_position * self._channel_length)

        x_off = self.origin[0] + np.cos(self._angle) * x - np.sin(self._angle) * y
        y_off = self.origin[1] + np.sin(self._angle) * x + np.cos(self._angle) * y

        return Port((x_off, y_off), self._angle - np.pi / 2, self._outer_channel_width)


if __name__ == '__main__':
    import gdsCAD.core

    part1 = Ntron(origin=(5, -5), angle=0, gate_width_1=0.3, gate_width_2=0.06, choke_width_1=0.06, choke_width_2=0.015,
                  choke_length_2=0.06, choke_length_3=0.03)
    wgdrain = Waveguide.make_at_port(part1.port_drain)
    wgdrain.add_straight_segment(0.5)
    wggate = Waveguide.make_at_port(part1.port_gate)
    wggate.add_straight_segment(0.5)
    wgsource = Waveguide.make_at_port(part1.port_source)
    wgsource.add_straight_segment(0.5)
    cell = gdsCAD.core.Cell('_channel')
    cell.add(convert_to_gdscad([part1], layer=1))
    cell.show()

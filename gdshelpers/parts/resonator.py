"""
Ring and race track resonators
"""

from __future__ import print_function, division

import math

import numpy as np

from gdshelpers.geometry import geometric_union
from gdshelpers.parts import Port
from gdshelpers.parts.waveguide import Waveguide


class RingResonator(object):
    """
    A simple Ring / Race track resonator.

    This part implements a super simple ring resonator with optional race tracks. Several
    helper functions are available to calculate points and ports of interest. The width of the
    feeding waveguide and the ring waveguide may differ.


    :param origin: Origin of the resonator, which is the start of the input waveguide.
    :param angle: Angle of the input waveguide.
    :param width: Width of the angle waveguide.
    :param gap: Gap between ring and waveguide. If positive, the ring will be on the left, and on the right side for
                negative gap values. Can also be a 2-tuple, if input and output gap should be different.
    :param radius: Radius of the bends.
    :param race_length: Length of the race track. Defaults to zero.
    :param draw_opposite_side_wg: If True, draw the opposing waveguides, (a.k.a. drop ports.)
    :param res_wg_width: Width of the resonator waveguide. If None, the width of the input waveguide is assumend.
    :param n_points: Number of points used per quarter circle. If None, it uses the bend default.
    :param straight_feeding: Add straight connections on both sides of the resonator.
    :param vertical_race_length: Length of a vertical race track section. Defaults to zero.
    """

    def __init__(self, origin, angle, width, gap, radius, race_length=0, draw_opposite_side_wg=False,
                 res_wg_width=None, n_points=None, straight_feeding=False, vertical_race_length=0):
        assert race_length >= 0, 'The race track length must not be negative'
        assert vertical_race_length >= 0, 'The vertical race track length must not be negative'
        assert radius > 0, 'The bend radius must not be negative'

        # Let's directly create a port object. This simplifies later creation of the geometry
        # as well as checking the user parameters while creating the port.
        self._origin_port = Port(origin, angle, width)

        # Ring gap
        try:
            self.gap, self.opposite_gap = gap
            if np.sign(self.gap) != np.sign(self.opposite_gap):
                raise ValueError
        except TypeError:
            self.gap = gap
            self.opposite_gap = gap

        # Remember all the other stuff we got
        self.radius = radius
        self.race_length = race_length
        self.res_wg_width = res_wg_width if res_wg_width else width
        self.points = n_points
        self.draw_opposite_side_wg = draw_opposite_side_wg
        self.straight_feeding = straight_feeding
        self.vertical_race_length = vertical_race_length

    @classmethod
    def make_at_port(cls, port, gap, radius, **kwargs):
        default_port_param = dict(port.get_parameters())
        default_port_param.update(kwargs)
        del default_port_param['origin']
        del default_port_param['angle']
        del default_port_param['width']

        return cls(port.origin, port.angle, port.width, gap, radius, **default_port_param)

    ###
    # Let's allow the user to change the values
    # hidden in _origin_port. Hence the internal use
    # of a Port is transparent.
    @property
    def origin(self):
        return self._origin_port.origin

    @origin.setter
    def origin(self, origin):
        self._origin_port.origin = origin

    @property
    def angle(self):
        return self._origin_port.angle

    @angle.setter
    def angle(self, angle):
        self._origin_port.angle = angle

    @property
    def width(self):
        return self._origin_port.width

    @width.setter
    def width(self, width):
        self._origin_port.width = width

    ####
    # Now, lets get to the functions the user is actually
    # interested in.
    @property
    def port(self):
        offset = self.race_length + 2 * self.radius if self.straight_feeding else 0
        return self._origin_port.longitudinal_offset(offset)

    out_port = port

    @property
    def opposite_side_port_out(self):
        return self.port.parallel_offset(np.copysign(2 * self.radius + self.vertical_race_length, self.opposite_gap)
                                         + self._offset + self._offset_opposite)

    @property
    def opposite_side_port_in(self):
        return self._origin_port.parallel_offset(
            np.copysign(2 * self.radius + self.vertical_race_length, self.opposite_gap)
            + self._offset + self._offset_opposite).inverted_direction

    # Conventional naming of ports
    @property
    def in_port(self):
        return self._origin_port.inverted_direction

    @property
    def add_port(self):
        return self.opposite_side_port_out

    @property
    def drop_port(self):
        return self.opposite_side_port_in

    @property
    def through_port(self):
        return self.port

    @property
    def center_coordinates(self):
        return self._origin_port.longitudinal_offset(self.race_length / 2.).parallel_offset(
            self._offset + np.copysign(self.radius + 0.5 * self.vertical_race_length, self.gap)).origin

    @property
    def _offset(self):
        return math.copysign(abs(self.gap) + (self.width + self.res_wg_width) / 2., self.gap)

    @property
    def _offset_opposite(self):
        return math.copysign(abs(self.opposite_gap) + (self.width + self.res_wg_width) / 2., self.opposite_gap)

    @property
    def circumference(self):
        return 2 * np.pi * self.radius + 2 * self.race_length

    def get_shapely_object(self):
        wg = Waveguide.make_at_port(self._origin_port)
        opposite_wg = Waveguide.make_at_port(self.opposite_side_port_in.inverted_direction)

        if self.straight_feeding:
            wg.add_straight_segment(self.radius)
            if self.draw_opposite_side_wg:
                opposite_wg.add_straight_segment(self.radius)

        ring_port = wg.current_port.parallel_offset(self._offset)
        ring_port.width = self.res_wg_width
        ring = Waveguide.make_at_port(ring_port)

        if self.race_length:
            wg.add_straight_segment(self.race_length)

            if self.draw_opposite_side_wg:
                opposite_wg.add_straight_segment(self.race_length)

        if self.straight_feeding:
            wg.add_straight_segment(self.radius)
            if self.draw_opposite_side_wg:
                opposite_wg.add_straight_segment(self.radius)

        # Build the ring
        bend_angle = math.copysign(0.5 * np.pi, self.gap)
        if self.race_length:
            ring.add_straight_segment(self.race_length)

        ring.add_bend(bend_angle, self.radius, n_points=self.points)
        if self.vertical_race_length:
            ring.add_straight_segment(self.vertical_race_length)

        ring.add_bend(bend_angle, self.radius, n_points=self.points)
        if self.race_length:
            ring.add_straight_segment(self.race_length)

        ring.add_bend(bend_angle, self.radius, n_points=self.points)
        if self.vertical_race_length:
            ring.add_straight_segment(self.vertical_race_length)

        ring.add_bend(bend_angle, self.radius, n_points=self.points)

        return geometric_union([ring, wg, opposite_wg])


def example():
    from gdshelpers.geometry import convert_to_gdscad
    import gdsCAD

    cell = gdsCAD.core.Cell('test')

    wg1 = Waveguide.make_at_port(Port((0, 0), 0, 1.))
    wg1.add_straight_segment(100)
    ring1 = RingResonator.make_at_port(wg1.current_port, 1., 50., race_length=30, straight_feeding=True,
                                       draw_opposite_side_wg=True)

    wg2 = Waveguide.make_at_port(ring1.port)
    wg2.add_straight_segment(100)
    ring2 = RingResonator.make_at_port(wg2.current_port, 1., 50., vertical_race_length=30, straight_feeding=True,
                                       draw_opposite_side_wg=True)

    wg3 = Waveguide.make_at_port(ring2.port)
    wg3.add_straight_segment(100)
    ring3 = RingResonator.make_at_port(wg3.current_port, -1., 50., vertical_race_length=30, straight_feeding=True,
                                       draw_opposite_side_wg=True)

    cell.add(convert_to_gdscad([wg1, ring1, wg2, ring2, wg3, ring3], layer=1))
    cell.show()


if __name__ == '__main__':
    example()

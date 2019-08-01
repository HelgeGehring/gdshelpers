import numpy as np

from gdshelpers.geometry import geometric_union
from gdshelpers.parts import Port
from gdshelpers.parts.waveguide import Waveguide


class Spiral:
    def __init__(self, origin, angle, width, num, gap, inner_gap):
        """
        Creates a Spiral around the given origin

        :param origin: position of the center of the spiral
        :param angle: angle of the outer two waveguides
        :param width: width of the waveguide
        :param num: number of turns
        :param gap: gap between two waveguides
        :param inner_gap: inner radius of the spiral
        """
        self._origin_port = Port(origin, angle, width)
        self.gap = gap
        self.inner_gap = inner_gap
        self.num = num
        self.wg_in = None
        self.wg_out = None

    @classmethod
    def make_at_port(cls, port, num, gap, inner_gap, **kwargs):
        default_port_param = dict(port.get_parameters())
        default_port_param.update(kwargs)
        del default_port_param['origin']
        del default_port_param['angle']
        del default_port_param['width']

        return cls(port.parallel_offset(-num * (port.width + gap) - inner_gap).origin,
                   port.angle, port.width, num, gap, inner_gap, **default_port_param)

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

    @property
    def in_port(self):
        return self._origin_port.inverted_direction.parallel_offset(
            -self.num * (self._origin_port.width + self.gap) - self.inner_gap)

    @property
    def out_port(self):
        return self._origin_port.parallel_offset(
            -self.num * (self._origin_port.width + self.gap) - self.inner_gap)

    @property
    def length(self):
        if not self.wg_in or not self.wg_out:
            self._generate()
        return self.wg_in.length + self.wg_out.length

    def _generate(self):
        def path(a):
            return (self.num * (self.width + self.gap) * np.abs(1 - a) + self.inner_gap) * np.array(
                (np.sin(np.pi * a * self.num), np.cos(np.pi * a * self.num)))

        self.wg_in = Waveguide.make_at_port(self._origin_port)
        self.wg_in.add_parameterized_path(path)

        self.wg_out = Waveguide.make_at_port(self._origin_port.inverted_direction)
        self.wg_out.add_parameterized_path(path)

        self.wg_in.add_route_single_circle_to_port(self._origin_port.rotated(-np.pi * (self.num % 2)))
        self.wg_in.add_route_single_circle_to_port(self.wg_out.port)

    def get_shapely_object(self):
        if not self.wg_in or not self.wg_out:
            self._generate()
        return geometric_union([self.wg_in, self.wg_out])


def _example():
    from gdshelpers.geometry.chip import Cell

    wg = Waveguide((0, 0), 1, 1)
    wg.add_straight_segment(30)
    spiral = Spiral.make_at_port(wg.current_port, 2, 5, 50)
    wg2 = Waveguide.make_at_port(spiral.out_port)
    wg2.add_straight_segment(100)

    print(spiral.length)

    cell = Cell('Spiral')
    cell.add_to_layer(1, wg, spiral, wg2)
    cell.show()


if __name__ == '__main__':
    _example()

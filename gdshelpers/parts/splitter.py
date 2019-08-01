from __future__ import print_function, division

import math

import shapely.geometry
import shapely.affinity

import numpy as np
from gdshelpers.parts.port import Port
from gdshelpers.parts.waveguide import Waveguide
from gdshelpers.geometry import geometric_union


class Splitter(object):
    def __init__(self, origin, angle, total_length, wg_width_root, sep, wg_width_branches=None, n_points=50,
                 implement_cadence_bug=False):
        self._origin = origin
        self._angle = angle
        self._total_length = total_length
        self._wl = wg_width_root
        self._wr = wg_width_branches or wg_width_root
        self._sep = sep
        self._n_points = n_points
        self._implement_cadence_bug = implement_cadence_bug

        self._polygon = None
        self._ports = dict()

        self._generate()

    @classmethod
    def make_at_root_port(cls, port, total_length, sep, **kwargs):
        default_port_param = dict(port.get_parameters())
        default_port_param.update(kwargs)
        del default_port_param['origin']
        del default_port_param['angle']
        del default_port_param['width']

        return cls(port.origin, port.angle, total_length, port.width, sep, **default_port_param)

    @classmethod
    def make_at_left_branch_port(cls, port, total_length, sep, wavelength_root=None, **kwargs):
        wavelength_root = wavelength_root or port.width

        origin = shapely.geometry.Point(-sep / 2, total_length)
        origin = shapely.affinity.rotate(origin, -np.pi / 2 + port.angle, origin=[0, 0], use_radians=True)
        origin_offset = np.array(origin.coords[0])

        default_port_param = dict(port.get_parameters())
        default_port_param.update(kwargs)
        del default_port_param['origin']
        del default_port_param['angle']
        del default_port_param['width']

        return cls(origin_offset + port.origin, port.angle + np.pi, total_length, wavelength_root, sep, port.width,
                   **default_port_param)

    @classmethod
    def make_at_right_branch_port(cls, port, total_length, sep, wavelength_root=None, **kwargs):
        wavelength_root = wavelength_root or port.width

        origin = shapely.geometry.Point(sep / 2, total_length)
        origin = shapely.affinity.rotate(origin, -np.pi / 2 + port.angle, origin=[0, 0], use_radians=True)
        origin_offset = np.array(origin.coords[0])

        default_port_param = dict(port.get_parameters())
        default_port_param.update(kwargs)
        del default_port_param['origin']
        del default_port_param['angle']
        del default_port_param['width']

        return cls(origin_offset + port.origin, port.angle + np.pi, total_length, wavelength_root, sep, port.width,
                   **default_port_param)

    def _generate(self):
        if self._sep < self._wr:
            raise ValueError('The separation gap must be larger than the branch width.')

        if self._implement_cadence_bug:
            v1 = Splitter._connect_two_points([self._wl / 2, 0], [self._sep / 2 + self._wr / 2, self._total_length],
                                              self._n_points)
            if self._wl < 2 * self._wr:
                v2 = (v1 - [self._wr, 0])[::-1, :]
            else:
                # NOTE: In this obscure case, the generated splitter looks different than the cadence version.
                #       But probably it is better, since the paths are all smooth and curvy instead of just painting a
                #       triangle.
                v2 = Splitter._connect_two_points([-self._wr / 2, 0],
                                                  [self._sep / 2 - self._wr / 2, self._total_length],
                                                  self._n_points)[::-1, :]

            v = np.vstack((v1, v2))
            polygon1 = shapely.geometry.Polygon(v)
            polygon1 = polygon1.difference(shapely.geometry.box(-self._sep / 2, 0, 0, self._total_length))
            polygon2 = shapely.affinity.scale(polygon1, xfact=-1, origin=[0, 0, 0])

            polygon = polygon1.union(polygon2)

            polygon = shapely.affinity.rotate(polygon, -np.pi / 2 + self._angle, origin=[0, 0], use_radians=True)
            polygon = shapely.affinity.translate(polygon, self._origin[0], self._origin[1])

            # Keep track of the ports
            port_points = shapely.geometry.MultiPoint([(0, 0),
                                                       (-self._sep / 2, self._total_length),
                                                       (+self._sep / 2, self._total_length)])
            port_points = shapely.affinity.rotate(port_points, -np.pi / 2 + self._angle, origin=[0, 0],
                                                  use_radians=True)
            port_points = shapely.affinity.translate(port_points, self._origin[0], self._origin[1])

            self._polygon = polygon
            self._ports['root'] = Port(port_points[0].coords[0], self._angle + np.pi, width=self._wl)
            self._ports['left_branch'] = Port(port_points[1].coords[0], self._angle, width=self._wr)
            self._ports['right_branch'] = Port(port_points[2].coords[0], self._angle, width=self._wr)

        else:
            # Simpler version which also cares for a constant wave guide width
            alpha = np.arctan(
                4.0 * self._total_length * self._sep / (4.0 * self._total_length ** 2.0 - self._sep ** 2.0))
            radius = 1.0 / 8.0 * (4.0 * self._total_length ** 2.0 + self._sep ** 2.0) / self._sep

            root_port = Port(self._origin, self._angle, self._wl)
            half_final_width = (self._wl + self._wr) / 2.

            upper_wg = Waveguide.make_at_port(root_port)
            upper_wg.add_bend(alpha, radius, final_width=half_final_width)
            upper_wg.add_bend(-alpha, radius, final_width=self._wr)

            lower_wg = Waveguide.make_at_port(root_port)
            lower_wg.add_bend(-alpha, radius, final_width=half_final_width)
            lower_wg.add_bend(alpha, radius, final_width=self._wr)

            self._polygon = geometric_union([upper_wg, lower_wg])
            self._ports['root'] = root_port.inverted_direction
            self._ports['left_branch'] = upper_wg.current_port
            self._ports['right_branch'] = lower_wg.current_port

    @property
    def root_port(self):
        return self._ports['root']

    @property
    def left_branch_port(self):
        return self._ports['left_branch']

    @property
    def right_branch_port(self):
        return self._ports['right_branch']

    @staticmethod
    def _connect_two_points(p1, p2, n_points=20):
        if p1[0] > p2[0]:
            reverse = True
            p1, p2 = p2, p1
        else:
            reverse = False

        ht = - (p2[0] - p1[0])
        tl = p2[1] - p1[1]

        b = math.sqrt(ht ** 2 + tl ** 2) / 4
        alpha = math.atan(ht / tl)
        r = b / math.sin(alpha)

        phi = np.linspace(0, 2 * alpha, n_points)
        lower_half = [np.cos(phi) * r - r + p1[0], np.sin(phi) * r + p1[1]]

        phi = np.linspace(np.pi + 2 * alpha, np.pi, n_points)
        upper_half = [np.cos(phi) * r - ht + r + p1[0], np.sin(phi) * r + tl + p1[1]]

        points = np.hstack((lower_half, upper_half)).T

        if reverse:
            return points[::-1, :]
        else:
            return points

    def get_shapely_object(self):
        return self._polygon


class DirectionalCoupler(object):
    def __init__(self, origin, angle, wg_width, length, gap, bend_radius, bend_angle=np.pi / 5.):
        """
        Creates a directional coupler
        :param origin: position of the first right port
        :param angle: direction from the first right port
        :param wg_width: width of the waveguide
        :param length: coupling length
        :param gap: gap between the waveguides in the coupling area
        :param bend_radius: radius of the curves
        :param bend_angle: angle of the curves
        """
        self._origin = origin
        self._angle = angle
        self._length = length
        self._wg_width = wg_width
        self._gap = gap
        self._bend_radius = bend_radius
        self._bend_angle = bend_angle

        self._wgs = []

        self.total_length = 0
        self.left_ports = []
        self.right_ports = []

        self._generate()

    @classmethod
    def make_at_port(cls, port, length, gap, bend_radius, bend_angle=np.pi / 5., which=0):
        """
        Creates a dc coupler starting at the port
        :param port: starting port
        :param length: coupling length
        :param gap: gap between the waveguides in the coupling area
        :param bend_radius: radius of the curves
        :param bend_angle: angle of the curves
        :param which: decides on which side to start, either left or right
        :return:
        """
        if which == 0:
            return cls(port.origin, port.angle, port.width, length, gap, bend_radius, bend_angle)
        elif which == 1:
            offset = shapely.geometry.Point(0, -4 * (1 - np.cos(bend_angle)) * bend_radius - gap - port.width)
            offset = shapely.affinity.rotate(offset, port.angle, origin=[0, 0], use_radians=True)
            return cls(port.origin + offset, port.angle, port.width, length, gap, bend_radius, bend_angle)
        else:
            raise ValueError('which must be either 0 or 1')

    def _generate(self):
        self.left_ports.append(Port(self._origin, self._angle, self._wg_width))
        wg = Waveguide.make_at_port(self.left_ports[0])
        wg.add_bend(angle=self._bend_angle, radius=self._bend_radius)
        wg.add_bend(angle=-self._bend_angle, radius=self._bend_radius)
        wg.add_straight_segment(self._length)
        wg.add_bend(angle=-self._bend_angle, radius=self._bend_radius)
        wg.add_bend(angle=self._bend_angle, radius=self._bend_radius)
        self._wgs.append(wg)
        self.right_ports.append(wg.current_port)

        self.left_ports.append(self.left_ports[0].parallel_offset(
            4 * (self._bend_radius - np.cos(self._bend_angle) * self._bend_radius) + self._wg_width + self._gap))
        wg = Waveguide.make_at_port(self.left_ports[1])
        wg.add_bend(angle=-self._bend_angle, radius=self._bend_radius)
        wg.add_bend(angle=self._bend_angle, radius=self._bend_radius)
        wg.add_straight_segment(self._length)
        wg.add_bend(angle=self._bend_angle, radius=self._bend_radius)
        wg.add_bend(angle=-self._bend_angle, radius=self._bend_radius)
        self._wgs.append(wg)
        self.right_ports.append(wg.current_port)

        self.total_length = wg.length

        self.left_ports = [port.inverted_direction for port in self.left_ports]

    def get_shapely_object(self):
        return geometric_union(self._wgs)


class MMI:
    def __init__(self, origin, angle, wg_width, length, width, num_inputs, num_outputs, taper_width=2, taper_length=10):
        """
        Creates a Multimode Interference Coupler
        :param origin: center of the left side of the multimode area
        :param angle: angle of the coupler
        :param wg_width: width of the waveguides
        :param length: length of the multimode area
        :param width: width of the multimode area
        :param num_inputs: number of input ports
        :param num_outputs: number of output ports
        :param taper_width: width of the tapers at the multimode area
        :param taper_length: length of the tapers
        """
        self._origin = origin
        self._angle = angle
        self._wg_width = wg_width
        self._length = length
        self._width = width
        self.num_inputs = num_inputs
        self.num_outputs = num_outputs
        self._taper_width = taper_width
        self._taper_length = taper_length
        self._sep = None

        self._wgs = []

        self.input_ports = []
        self.output_ports = []

        self._generate()

    @classmethod
    def make_at_port(cls, port, length, width, num_inputs, num_outputs, pos='i0', taper_width=2, taper_length=10):
        """
        Creates a Multimode Interference Coupler at the given port
        :param port: port to make the coupler at
        :param length: length of the multimode area
        :param width: width of the multimode area
        :param num_inputs: number of input ports
        :param num_outputs: number of output ports
        :param pos: port, that has to be connected to the given port, first letter-> i=input/o=output,
        second letter->number of the input/output
        :param taper_width: width of the tapers at the multimode area
        :param taper_length: length of the tapers
        :return:
        """
        input_positions, output_positions = cls._calculate_positions(num_inputs, num_outputs)
        positions = input_positions if pos[0] == 'i' else output_positions
        offset = shapely.geometry.Point(taper_length + (0 if pos[0] == 'i' else length), width * positions[int(pos[1])])
        offset = shapely.affinity.rotate(offset, port.angle, origin=[0, 0], use_radians=True)
        return cls(port.origin + offset, port.angle + (np.pi if pos[0] == 'o' else 0), port.width, length, width,
                   num_inputs, num_outputs, taper_width, taper_length)

    @classmethod
    def _calculate_positions(cls, num_inputs, num_outputs):
        if num_inputs > 2 or num_outputs > 2:
            # TODO Are the positions correct for N>2?
            raise NotImplementedError("Positions may not be correct -> checking needed")

        if num_inputs == 2 and num_outputs == 2:
            input_positions = [-1. / 6, 1. / 6]
            output_positions = [-1. / 6, 1. / 6]
            # todo: check if pos is right
            # output_positions = 1. / num_outputs * np.linspace(.5 - .5 * num_outputs, -.5 + .5 * num_outputs,
            #                                                  num_outputs)

        else:
            input_positions = 1. / num_inputs * np.linspace(.5 - .5 * num_inputs, -.5 + .5 * num_inputs, num_inputs)
            output_positions = 1. / num_outputs * np.linspace(.5 - .5 * num_outputs, -.5 + .5 * num_outputs,
                                                              num_outputs)

        return input_positions, output_positions

    def _generate(self):
        left = Port(self._origin, self._angle, self._wg_width)
        wg = Waveguide.make_at_port(left, width=self._width)
        wg.add_straight_segment(self._length)
        self._wgs.append(wg)
        right = wg.current_port

        input_positions, output_positions = self._calculate_positions(self.num_inputs, self.num_outputs)

        self._sep = input_positions[-1] - input_positions[0]

        for pos in input_positions:
            wg = Waveguide([self._origin[0] - pos * self._width * np.sin(self._angle),
                            self._origin[1] + pos * self._width * np.cos(self._angle)],
                           angle=self._angle - np.pi, width=self._taper_width)
            wg.add_straight_segment(self._taper_length, final_width=self._wg_width)
            self._wgs.append(wg)
            self.input_ports.append(wg.current_port)

        for pos in output_positions:
            wg = Waveguide([right.origin[0] - pos * self._width * np.sin(self._angle),
                            right.origin[1] + pos * self._width * np.cos(self._angle)],
                           angle=self._angle, width=self._taper_width)
            wg.add_straight_segment(self._taper_length, final_width=self._wg_width)
            self._wgs.append(wg)
            self.output_ports.append(wg.current_port)

    def get_shapely_object(self):
        return geometric_union(self._wgs)

    @property
    def left_branch_port(self):
        """
        Returns the leftmost output port (like a Y-Splitter)

        :return: leftmost Port
        """
        return self.output_ports[-1]

    @property
    def right_branch_port(self):
        """
        Returns the rightmost output port (like a Y-Splitter)

        :return: rightmost Port
        """
        return self.output_ports[0]

    @property
    def separation(self):
        return self._sep * self._width


def _example_mmi():
    import gdsCAD.core
    from gdshelpers.geometry import convert_to_gdscad

    mmi = MMI((80, 0), 0, 1, 20, 10, 2, 2)

    cell = gdsCAD.core.Cell('Splitter')
    cell.add(convert_to_gdscad(geometric_union([mmi])))
    cell.show()


def _example():
    import gdsCAD.core
    from gdshelpers.geometry import convert_to_gdscad

    dc = DirectionalCoupler((0, 0), np.pi / 4, 1, 10, 1, 10)
    dc2 = DirectionalCoupler.make_at_port(dc.right_ports[1], 5, 2, 10, which=0)
    wg = Waveguide.make_at_port(dc.left_ports[1])
    wg.add_straight_segment(12)
    wg2 = Waveguide.make_at_port(dc2.right_ports[0])
    wg2.add_straight_segment(12)

    mmi = MMI((80, 0), 0, 1, 20, 10, 2, 1)
    mmi2 = MMI.make_at_port(dc2.right_ports[1], 10, 10, 2, 2, 'i1')

    cell = gdsCAD.core.Cell('Splitter')
    cell.add(convert_to_gdscad(geometric_union((dc, dc2, wg, wg2, mmi, mmi2))))
    cell.show()


if __name__ == '__main__':
    # _example()
    _example_mmi()

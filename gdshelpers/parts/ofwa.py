"""
Parts for Optical Field Writable Arrays (OFWA)
"""

import numpy as np

from gdshelpers.parts import Port
from gdshelpers.parts.waveguide import Waveguide
from gdshelpers.parts.marker import DLWMarker

from gdshelpers.geometry import geometric_union
from gdshelpers.helpers import normalize_phase


class MultiPortSwitch(object):
    def __init__(self, origin, angle, in_ports, out_ports, port_spacing, taper_length, taper_function, radius,
                 wg_bend_radius, displacement=0., minimal_final_spacing=None):
        self._origin = origin
        self._angle = angle
        self._in_ports = in_ports
        self._out_ports = out_ports
        self._port_spacing = port_spacing
        self._taper_length = taper_length
        self._taper_function = taper_function
        self._taper_options = {}
        self._radius = radius
        self._wg_bend_radius = wg_bend_radius
        self._displacement = displacement
        self._minimal_final_spacing = minimal_final_spacing

        self._in_wgs = None
        self._out_wgs = None

    @classmethod
    def make_at_in_port(cls, port, in_port_idx, **kwargs):
        tmp_mps = cls([0, 0], port.angle, **kwargs)
        return cls(-tmp_mps.get_in_port(in_port_idx).origin + port.origin, port.angle, **kwargs)

    @classmethod
    def make_at_out_port(cls, port, out_port_idx, **kwargs):
        tmp_mps = cls([0, 0], port.inverted_direction.angle, **kwargs)
        return cls(-tmp_mps.get_out_port(out_port_idx).origin + port.origin, port.inverted_direction.angle, **kwargs)

    @property
    def origin(self):
        return np.array(self._origin)

    @property
    def angle(self):
        return self._angle

    @property
    def _angular_spacing(self):
        return self._port_spacing / self._radius

    def _calculate(self, do_in_wgs=True, do_out_wgs=True):
        angular_spacing = self._angular_spacing
        assert angular_spacing * self._out_ports < np.pi, 'Not enough space for output ports'
        assert angular_spacing * self._in_ports < np.pi, 'Not enough space for input ports'

        if do_out_wgs:
            # Do the output side
            out_origin_port = Port(self._origin, self._angle, 1.).longitudinal_offset(-self._displacement / 2)
            out_fanout_wgs = [Waveguide.make_at_port(out_origin_port.rotated(angle).longitudinal_offset(self._radius))
                              for angle in (np.arange(self._out_ports) - (self._out_ports - 1) / 2.) * angular_spacing]

            for wg in out_fanout_wgs:
                wg.add_parameterized_path(path=lambda t: [t * self._taper_length, np.zeros_like(t)],
                                          path_derivative=lambda t: [np.ones_like(t) * self._taper_length,
                                                                     np.zeros_like(t)],
                                          path_function_supports_numpy=True,
                                          width=self._taper_function, **self._taper_options)

            if self._minimal_final_spacing is None:
                for wg in out_fanout_wgs:
                    wg.add_bend(normalize_phase(-wg.angle + self._angle), self._wg_bend_radius)

            else:
                offsets = (np.arange(self._out_ports) - (self._out_ports - 1) / 2.) * self._minimal_final_spacing
                final_port_heights = [out_origin_port.parallel_offset(offset) for offset in offsets]

                for wg, final_port_height, offset in zip(out_fanout_wgs, final_port_heights, offsets):
                    if np.isclose(offset, 0):
                        continue

                    try:
                        wg.add_route_single_circle_to_port(final_port_height.inverted_direction, on_line_only=True)
                    except AssertionError:
                        # No curve possible, use normal bend
                        wg.add_bend(normalize_phase(-wg.angle + self._angle), self._wg_bend_radius)

            final_ports = [wg.current_port for wg in out_fanout_wgs]
            for wg in out_fanout_wgs:
                wg.add_straight_segment_until_level_of_port(final_ports)
            self._out_wgs = out_fanout_wgs

        if do_in_wgs:
            # Do the input side
            in_origin_port = Port(self._origin, self._angle + np.pi, 1.).longitudinal_offset(-self._displacement / 2)
            in_fanout_wgs = [Waveguide.make_at_port(in_origin_port.rotated(angle).longitudinal_offset(self._radius))
                             for angle in (np.arange(self._in_ports) - (self._in_ports - 1) / 2.) * angular_spacing]

            for wg in in_fanout_wgs:
                wg.add_parameterized_path(path=lambda t: [t * self._taper_length, np.zeros_like(t)],
                                          path_derivative=lambda t: [np.ones_like(t) * self._taper_length,
                                                                     np.zeros_like(t)],
                                          path_function_supports_numpy=True,
                                          width=self._taper_function, **self._taper_options)

            if self._minimal_final_spacing is None:
                for wg in in_fanout_wgs:
                    wg.add_bend(normalize_phase(-wg.angle + self._angle - np.pi), self._wg_bend_radius)

            else:
                offsets = (np.arange(self._in_ports) - (self._in_ports - 1) / 2.) * self._minimal_final_spacing
                final_port_heights = [in_origin_port.parallel_offset(offset) for offset in offsets]

                for wg, final_port_height, offset in zip(in_fanout_wgs, final_port_heights, offsets):
                    if np.isclose(offset, 0):
                        continue

                    # wg.add_route_single_circle_to_port(final_port_height.inverted_direction, on_line_only=True)

                    try:
                        wg.add_route_single_circle_to_port(final_port_height.inverted_direction, on_line_only=True)
                    except AssertionError:
                        # No curve possible, use normal bend
                        wg.add_bend(normalize_phase(-wg.angle + self._angle - np.pi), self._wg_bend_radius)

            final_ports = [wg.current_port for wg in in_fanout_wgs]
            for wg in in_fanout_wgs:
                wg.add_straight_segment_until_level_of_port(final_ports)

            self._in_wgs = in_fanout_wgs

    def get_in_port(self, idx):
        if not self._in_wgs:
            self._calculate(do_in_wgs=True, do_out_wgs=False)

        assert 0 <= idx <= self._in_ports, 'Invalid input port number'
        return self._in_wgs[idx].current_port

    def get_out_port(self, idx):
        if not self._out_wgs:
            self._calculate(do_in_wgs=False, do_out_wgs=True)

        assert 0 <= idx <= self._out_ports, 'Invalid input port number'
        return self._out_wgs[idx].current_port

    def get_dlw_in_port(self, idx):
        if not self._in_wgs:
            self._calculate(do_in_wgs=True, do_out_wgs=False)

        assert 0 <= idx <= self._in_ports, 'Invalid input port number'
        return self._in_wgs[idx].in_port

    def get_dlw_out_port(self, idx):
        if not self._out_wgs:
            self._calculate(do_in_wgs=False, do_out_wgs=True)

        assert 0 <= idx <= self._out_ports, 'Invalid input port number'
        return self._out_wgs[idx].in_port

    @property
    def in_ports(self):
        return list((self.get_in_port(idx) for idx in range(self._in_ports)))

    @property
    def out_ports(self):
        return list((self.get_out_port(idx) for idx in range(self._out_ports)))

    @property
    def dlw_in_ports(self):
        return list((self.get_dlw_in_port(idx) for idx in range(self._in_ports)))

    @property
    def dlw_out_ports(self):
        return list((self.get_dlw_out_port(idx) for idx in range(self._out_ports)))

    @property
    def marker_positions(self):
        center_port = Port(self._origin, self._angle, 1.)

        angle = max((2 + max(self._in_ports, self._out_ports)) / 2. * self._angular_spacing, np.pi / 4)
        radius = max(self._radius, 40)
        return [center_port.rotated(angle).longitudinal_offset(radius).origin,
                center_port.rotated(angle).longitudinal_offset(-radius).origin,
                center_port.rotated(-angle).longitudinal_offset(radius).origin,
                center_port.rotated(-angle).longitudinal_offset(-radius).origin]

    def get_shapely_object(self):
        if not self._in_wgs or not self._out_wgs:
            self._calculate(do_in_wgs=True, do_out_wgs=True)

        markers = [DLWMarker(pos) for pos in self.marker_positions]

        return geometric_union(self._out_wgs + self._in_wgs + markers)


def _example():
    import gdsCAD.core
    from gdshelpers.geometry import convert_to_gdscad
    from gdshelpers.parts.waveguide import Waveguide

    mpsv2 = MultiPortSwitch(origin=[0, 0],
                            angle=np.deg2rad(0.),
                            in_ports=4, out_ports=7,
                            port_spacing=10,
                            taper_length=40, taper_function=lambda t: t * (1.0 - 0.05) + 0.05,
                            radius=50., displacement=0.,
                            wg_bend_radius=40., minimal_final_spacing=20)

    wg = Waveguide([100, 100], np.pi / 4, 1)
    wg.add_straight_segment(100)

    # mpsv2_2 = MultiPortSwitch.make_at_out_port(wg.current_port, 3,
    #                                            in_ports=2, out_ports=7,
    #                                            port_spacing=10,
    #                                            taper_length=10, taper_function=lambda t: t * (1.0 - 0.05) + 0.05,
    #                                            radius=50., displacement=00.,
    #                                            wg_bend_radius=40., )

    cell = gdsCAD.core.Cell('TEST')
    cell.add(convert_to_gdscad([mpsv2, wg, ]))
    cell.show()


if __name__ == '__main__':
    _example()

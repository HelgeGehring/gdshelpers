import numpy as np

from gdshelpers.geometry import geometric_union
from gdshelpers.parts import Port
from gdshelpers.parts.waveguide import Waveguide


class SNSPD:
    def __init__(self, origin, angle, width, nano_wire_width, nano_wire_gap, nano_wire_length, waveguide_tapering,
                 passivation_buffer):
        if nano_wire_width <= 0:
            raise ValueError("The nano-wire width must be greater than 0")
        if nano_wire_length < 0:
            raise ValueError("The nano-wire length must be positive")
        if nano_wire_gap <= 0:
            raise ValueError("The nano-wire gap must be greater than 0")
        if nano_wire_length < 0:
            raise ValueError("The distance for the passivation layer must be positive")

        self._origin_port = Port(origin, angle, width)
        self.nano_wire_gap = nano_wire_gap
        self.nano_wire_width = nano_wire_width
        self.nano_wire_length = nano_wire_length
        self.waveguide_tapering = waveguide_tapering
        self.passivation_buffer = passivation_buffer

        self._waveguide = None
        self._nano_wire = None
        self._wings = None

    @classmethod
    def make_at_port(cls, port, nw_width, nw_gap, nw_length, waveguide_tapering, passivation_buffer):
        return cls(port.origin, port.angle, port.width, nw_width, nw_gap, nw_length, waveguide_tapering,
                   passivation_buffer)

    def _generate(self):
        tip_radius = 0.5 * (self.nano_wire_gap + self.nano_wire_width)
        nano_wire_port = self._origin_port \
            .longitudinal_offset(self.nano_wire_length + tip_radius + self.passivation_buffer) \
            .parallel_offset(tip_radius)

        self._nano_wire = Waveguide.make_at_port(nano_wire_port.inverted_direction, width=self.nano_wire_width)
        self._nano_wire.add_straight_segment(self.nano_wire_length - tip_radius)
        self._nano_wire.add_bend(np.pi, tip_radius)
        self._nano_wire.add_straight_segment(self.nano_wire_length - tip_radius)

        self._wings = []
        for sign, port in [(1, self._nano_wire.current_port), (-1, self._nano_wire.in_port)]:
            wing_outer_port = port.longitudinal_offset(14).parallel_offset(-sign * 10).rotated(sign * 0.75 * np.pi)
            wing_outer_port.width = 5
            wing_inner_port = wing_outer_port.longitudinal_offset(10)
            wing_inner_port.width = 0.5

            self._wings.append(Waveguide.make_at_port(port)
                               .add_bezier_to_port(port=wing_inner_port, bend_strength=2.5)
                               .add_bezier_to_port(port=wing_outer_port, bend_strength=6)
                               .add_straight_segment(1))

        self._waveguide = Waveguide.make_at_port(self._origin_port)
        self._waveguide.add_straight_segment_until_level_of_port(self._wings[0].current_port.rotated(-0.75 * np.pi))
        if self.waveguide_tapering:
            self._waveguide.add_straight_segment(5. * self._origin_port.width, final_width=0.01)

    def get_shapely_object(self):
        if not self._nano_wire or not self._wings:
            self._generate()
        return geometric_union([self._nano_wire] + self._wings)

    def get_waveguide(self):
        if not self._waveguide or not self._wings:
            self._generate()
        return geometric_union([self._waveguide] + [wing.get_shapely_object().buffer(.2) for wing in self._wings])

    def get_passivation_layer(self):
        if not self._nano_wire or not self._wings:
            self._generate()
        return geometric_union([self._nano_wire] + self._wings).buffer(self.passivation_buffer)

    @property
    def right_electrode_port(self):
        if not self._wings:
            self._generate()
        return self._wings[0].current_port.longitudinal_offset(-1)

    @property
    def left_electrode_port(self):
        if not self._wings:
            self._generate()
        return self._wings[1].current_port.longitudinal_offset(-1)

    @property
    def current_port(self):
        if not self._waveguide:
            self._generate()
        return self._waveguide.current_port


def _example():
    from gdshelpers.geometry.chip import Cell

    cell = Cell('test')

    wg1 = Waveguide((0, 0), 0.5 * np.pi, 1.)
    wg1.add_straight_segment(10.)
    cell.add_to_layer(3, wg1)

    detector = SNSPD.make_at_port(wg1.current_port, nw_width=0.1, nw_gap=0.1, nw_length=70, passivation_buffer=0.2,
                                  waveguide_tapering=True)
    cell.add_to_layer(1, detector)
    cell.add_to_layer(2, detector.get_waveguide())
    cell.add_to_layer(5, detector.get_passivation_layer())

    # cell.add_to_layer(6, detector.right_electrode_port.debug_shape)
    # cell.add_to_layer(6, detector.left_electrode_port.debug_shape)
    wg2 = Waveguide.make_at_port(detector.current_port)
    wg2.add_straight_segment(20.)
    cell.add_to_layer(3, wg2)
    cell.save('SNSPD_test.gds')
    cell.show()


if __name__ == '__main__':
    _example()

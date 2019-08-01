import numpy as np
from gdshelpers.parts import Port
from gdshelpers.geometry import convert_to_gdscad
from gdshelpers.parts.waveguide import Waveguide
from gdshelpers.parts.splitter import Splitter, MMI

from gdshelpers.geometry import geometric_union


class MachZehnderInterferometer(object):
    """
    A simple Mach-Zehnder interferometer based on Y-splitters.

    :param origin: Start of the interferometer.
    :type origin: tuple
    :param angle: Angle of the interferometer in rad.
    :type angle: float
    :param width: Waveguide width.
    :type width: float
    :param splitter_length: Length of the splitter
    :type splitter_length: float
    :param splitter_separation: Separation of the slitter branches.
    :type splitter_separation: float
    :param bend_radius: Bend radius.
    :type bend_radius: float
    :param upper_vertical_length: Straight length of the upper branch.
    :type upper_vertical_length: float
    :param lower_vertical_length: Straight length of the lower branch.
    :type lower_vertical_length: float
    :param horizontal_length: Straight horizontal length for both branches.
    :type horizontal_length: float
    """

    def __init__(self, origin, angle, width, splitter_length, splitter_separation, bend_radius,
                 upper_vertical_length, lower_vertical_length, horizontal_length):
        self.origin = origin
        self.angle = angle
        self.width = width
        self.splitter_length = splitter_length
        self.splitter_separation = splitter_separation
        self.bend_radius = bend_radius
        self.upper_vertical_length = upper_vertical_length
        self.lower_vertical_length = lower_vertical_length
        self.horizontal_length = horizontal_length
        self.dev_width = 2 * self.splitter_length + 4 * self.bend_radius + self.horizontal_length + 20

    @classmethod
    def make_at_port(cls, port, splitter_length, splitter_separation, bend_radius,
                     upper_vertical_length, lower_vertical_length, horizontal_length):
        return cls(port.origin, port.angle, port.width, splitter_length, splitter_separation, bend_radius,
                   upper_vertical_length, lower_vertical_length, horizontal_length)

    @property
    def port(self):
        port = Port(self.origin, self.angle, self.width)
        return port.longitudinal_offset(2 * self.splitter_length + 4 * self.bend_radius + self.horizontal_length)

    def get_shapely_object(self):
        splitter1 = Splitter(self.origin, self.angle, self.splitter_length, self.width, self.splitter_separation)

        upper_wg = Waveguide.make_at_port(splitter1.left_branch_port)
        upper_wg.add_bend(np.deg2rad(90), self.bend_radius)
        upper_wg.add_straight_segment(self.upper_vertical_length)
        upper_wg.add_bend(np.deg2rad(-90), self.bend_radius)
        upper_wg.add_straight_segment(self.horizontal_length)
        upper_wg.add_bend(np.deg2rad(-90), self.bend_radius)
        upper_wg.add_straight_segment(self.upper_vertical_length)
        upper_wg.add_bend(np.deg2rad(90), self.bend_radius)

        lower_wg = Waveguide.make_at_port(splitter1.right_branch_port)
        lower_wg.add_bend(np.deg2rad(-90), self.bend_radius)
        lower_wg.add_straight_segment(self.lower_vertical_length)
        lower_wg.add_bend(np.deg2rad(90), self.bend_radius)
        lower_wg.add_straight_segment(self.horizontal_length)
        lower_wg.add_bend(np.deg2rad(90), self.bend_radius)
        lower_wg.add_straight_segment(self.lower_vertical_length)
        lower_wg.add_bend(np.deg2rad(-90), self.bend_radius)

        splitter2 = Splitter.make_at_right_branch_port(upper_wg.current_port, self.splitter_length,
                                                       self.splitter_separation)

        return geometric_union([splitter1, splitter2, upper_wg, lower_wg])

    @property
    def device_width(self):
        return self.dev_width


class MachZehnderInterferometerMMI(object):
    """
        A simple Mach-Zehnder interferometer based on Y-splitters.

        :param origin: Start of the interferometer.
        :type origin: tuple
        :param angle: Angle of the interferometer in rad.
        :type angle: float
        :param width: Waveguide width.
        :type width: float
        :param splitter_length: Length of the splitter
        :type splitter_length: float
        :param splitter_separation: Separation of the slitter branches.
        :type splitter_separation: float
        :param bend_radius: Bend radius.
        :type bend_radius: float
        :param upper_vertical_length: Straight length of the upper branch.
        :type upper_vertical_length: float
        :param lower_vertical_length: Straight length of the lower branch.
        :type lower_vertical_length: float
        :param horizontal_length: Straight horizontal length for both branches.
        :type horizontal_length: float
    """

    def __init__(self, origin, angle, width, splitter_length, splitter_width, bend_radius,
                 upper_vertical_length, lower_vertical_length, horizontal_length):
        self.origin = origin
        self.angle = angle
        self.width = width
        self.splitter_length = splitter_length
        self.splitter_width = splitter_width
        self.bend_radius = bend_radius
        self.upper_vertical_length = upper_vertical_length
        self.lower_vertical_length = lower_vertical_length
        self.horizontal_length = horizontal_length
        self.dev_width = 2 * self.splitter_length + 4 * self.bend_radius + self.horizontal_length + 20

    @classmethod
    def make_at_port(cls, port, splitter_length, splitter_width, bend_radius,
                     upper_vertical_length, lower_vertical_length, horizontal_length):
        return cls(port.origin, port.angle, port.width, splitter_length, splitter_width, bend_radius,
                   upper_vertical_length, lower_vertical_length, horizontal_length)

    @property
    def port(self):
        port = Port(self.origin, self.angle, self.width)
        return port.longitudinal_offset(2 * self.splitter_length + 4 * self.bend_radius + self.horizontal_length + 20)

    @property
    def device_width(self):
        return self.dev_width

    def get_shapely_object(self):
        splitter1 = MMI(origin=self.origin, angle=self.angle, wg_width=self.width, length=self.splitter_length,
                        width=self.splitter_width, num_inputs=1, num_outputs=2)
        print(splitter1.output_ports)
        upper_wg = Waveguide.make_at_port(splitter1.left_branch_port)
        upper_wg.add_bend(np.deg2rad(90), self.bend_radius)
        upper_wg.add_straight_segment(self.upper_vertical_length)
        upper_wg.add_bend(np.deg2rad(-90), self.bend_radius)
        upper_wg.add_straight_segment(self.horizontal_length)
        upper_wg.add_bend(np.deg2rad(-90), self.bend_radius)
        upper_wg.add_straight_segment(self.upper_vertical_length)
        upper_wg.add_bend(np.deg2rad(90), self.bend_radius)

        lower_wg = Waveguide.make_at_port(splitter1.right_branch_port)
        lower_wg.add_bend(np.deg2rad(-90), self.bend_radius)
        lower_wg.add_straight_segment(self.lower_vertical_length)
        lower_wg.add_bend(np.deg2rad(90), self.bend_radius)
        lower_wg.add_straight_segment(self.horizontal_length)
        lower_wg.add_bend(np.deg2rad(90), self.bend_radius)
        lower_wg.add_straight_segment(self.lower_vertical_length)
        lower_wg.add_bend(np.deg2rad(-90), self.bend_radius)

        splitter2 = MMI(origin=[self.origin[0] + self.dev_width, self.origin[1]], angle=self.angle + np.pi,
                        wg_width=self.width, length=self.splitter_length,
                        width=self.splitter_width, num_inputs=1, num_outputs=2)
        print(splitter2.input_ports)

        return geometric_union([splitter1, splitter2, upper_wg, lower_wg])


def main():
    import gdsCAD

    devicename = 'MZI'

    mzi = MachZehnderInterferometer(origin=(0, 0), angle=0, width=1.2, splitter_length=10, splitter_separation=5,
                                    bend_radius=50, upper_vertical_length=50, lower_vertical_length=0,
                                    horizontal_length=0)
    mzi_mmi = MachZehnderInterferometerMMI(origin=(0, 0), angle=0, width=1.2, splitter_length=33, splitter_width=7.7,
                                           bend_radius=50, upper_vertical_length=50, lower_vertical_length=0,
                                           horizontal_length=0)
    print(mzi_mmi.device_width)

    wg = Waveguide.make_at_port(mzi_mmi.port)
    wg.add_straight_segment(length=50)

    cell = gdsCAD.core.Cell(devicename)
    cell.add(convert_to_gdscad(mzi_mmi, layer=1))
    cell.add(convert_to_gdscad(wg, layer=1))

    layout = gdsCAD.core.Layout()
    layout.add(cell=cell)
    layout.save('%s.gds' % devicename)
    layout.show()


if __name__ == '__main__':
    main()

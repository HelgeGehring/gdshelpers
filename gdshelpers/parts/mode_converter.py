import numpy as np

from gdshelpers.parts.waveguide import Waveguide
from gdshelpers.parts import Port


class StripToSlotModeConverter:
    """
    Generates a strip to slot mode converter as presented by Palmer et. al https://doi.org/10.1109/JPHOT.2013.2239283.
    If the input port width is a scalar und the final width is an array, a strip to slot mode converter is generated.
    On the other hand, if the input port width is an array and the final width is a scaler, a slot to strip mode
    converter is generated.

    """

    def __init__(self, origin, angle, width, taper_length, final_width, pre_taper_length, pre_taper_width):
        """

        :param origin: origin of the mode converter
        :param angle: angle of the mode converter
        :param width: width of the mdoe converter. Scalar if strip to slot, array if slot to strip
        :param taper_length: length of the taper
        :param final_width: final width of the mode converter. Array if strip to slot, scalar if slot to strip
        :param pre_taper_length: length of the pre taper
        :param pre_taper_width: width of the pre taper
        """
        self._taper_length = taper_length
        self._in_port = Port(origin, angle, width)
        self._final_width = final_width
        self._pre_taper_length = pre_taper_length
        self._pre_taper_width = pre_taper_width
        self._waveguide = None

    @classmethod
    def make_at_port(cls, port, taper_length, final_width, pre_taper_length, pre_taper_width):
        """

        :param port: port of the taper (origin, angle, width)
        :param taper_length: length of the taper
        :param final_width: final width of the mode converter. Array if strip to slot, scalar if slot to strip
        :param pre_taper_length: length of the pre taper
        :param pre_taper_width:  width of the pre taper
        :return:
        """
        return cls(port.origin, port.angle, port.width, taper_length, final_width, pre_taper_length,
                   pre_taper_width)

    @property
    def in_port(self):
        """
        Returns the input port of the mode converter

        :return: port
        """
        return self._in_port.copy()

    @property
    def out_port(self):
        """
        Returns the output port of the mode converter

        :return: port
        """
        port = self._in_port.longitudinal_offset(self._taper_length + self._pre_taper_length)
        port.width = self._final_width
        return port

    def get_shapely_object(self):
        """
        Generates the mode converter. If the input port width is a scalar und the final width is an array, a strip to
        slot mode converter is generated. On the other hand, if the input port width is an array and the final width is
        a scaler, a slot to strip mode converter is generated.

        :return: shapely object
        """
        if self._waveguide:
            return self._waveguide.get_shapely_object()

        if np.array(self._in_port.width).size == 1:
            # strip to slot mode converter
            strip_width = self.in_port.width
            slot_width = self._final_width
        else:
            # slot to strip mode converter
            slot_width = self.in_port.width
            strip_width = self._final_width

        def pre_taper_width(t):
            return [
                slot_width[0] * t + self._pre_taper_width * (1 - t),
                slot_width[1] + (slot_width[0] - self._pre_taper_width) * (1 - t),
                strip_width,
                slot_width[0] + slot_width[1]
            ]

        def taper_width(t):
            return [slot_width[0], slot_width[1],
                    slot_width[2] * t + strip_width * (1 - t),
                    (slot_width[0] + slot_width[1]) * (1 - t)
                    ]

        self._waveguide = Waveguide.make_at_port(self._in_port)

        if np.array(self._in_port.width).size == 1:
            # strip to slot mode converter
            self._waveguide.add_parameterized_path(lambda t: [t * self._pre_taper_length, 0], width=pre_taper_width)
            self._waveguide.add_parameterized_path(lambda t: [t * self._taper_length, 0], width=taper_width)
        else:
            # slot to strip mode converter
            self._waveguide.add_parameterized_path(lambda t: [t * self._taper_length, 0],
                                                   width=lambda t: taper_width(1 - t))
            self._waveguide.add_parameterized_path(lambda t: [t * self._pre_taper_length, 0],
                                                   width=lambda t: pre_taper_width(1 - t))

        return self._waveguide.get_shapely_object()


def _example():
    from gdshelpers.geometry.chip import Cell
    from gdshelpers.parts.port import Port
    from gdshelpers.parts.waveguide import Waveguide
    from gdshelpers.parts.mode_converter import StripToSlotModeConverter

    wg_1 = Waveguide.make_at_port(Port(origin=(0, 0), angle=0, width=1.2))  # scalar as width -> strip waveguide
    wg_1.add_straight_segment(5)

    mc_1 = StripToSlotModeConverter.make_at_port(wg_1.current_port, 5, [0.4, 0.2, 0.4], 2,
                                                 0.2)  # array as width -> slot waveguide

    wg_2 = Waveguide.make_at_port(mc_1.out_port)
    wg_2.add_bend(angle=np.pi, radius=5)

    mc_2 = StripToSlotModeConverter.make_at_port(wg_2.current_port, 5, 1, 2, 0.2)  # scalar as width -> strip waveguide

    wg_3 = Waveguide.make_at_port(mc_2.out_port)
    wg_3.add_straight_segment(5)

    cell = Cell('CELL')
    cell.add_to_layer(1, wg_1, mc_1, wg_2, mc_2, wg_3)
    cell.show()


if __name__ == '__main__':
    _example()

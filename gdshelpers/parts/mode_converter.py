import numpy as np

from gdshelpers.parts.waveguide import Waveguide
from gdshelpers.parts import Port


class StripToSlotModeConverter(object):
    def __init__(self, origin, angle, width, taper_length, final_width):
        self._taper_length = taper_length
        self._in_port = Port(origin, angle, width)
        self._final_width = final_width
        self._length_taper_front = 1
        self._width_taper_front = 0.2

        self._waveguide = None

    @classmethod
    def make_at_port(cls, port, taper_length, final_width):
        return cls(port.origin, port.angle, port.width, taper_length, final_width)

    @property
    def in_port(self):
        return self._in_port.copy()

    @property
    def out_port(self):
        port = self._in_port.longitudinal_offset(self._taper_length + self._length_taper_front)
        port.width = self._final_width
        return port

    def get_shapely_object(self):
        if self._waveguide:
            return self._waveguide.get_shapely_object()

        if np.array(self._in_port.width).size == 1:
            strip_width = self.in_port.width
            slot_width = self._final_width
        else:
            slot_width = self.in_port.width
            strip_width = self._final_width

        def pre_taper_width(t):
            return [
                slot_width[0] * t + self._width_taper_front * (1 - t),
                slot_width[1] + (slot_width[0] - self._width_taper_front) * (1 - t),
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
            self._waveguide.add_parameterized_path(lambda t: [t * self._length_taper_front, 0], width=pre_taper_width)
            self._waveguide.add_parameterized_path(lambda t: [t * self._taper_length, 0], width=taper_width)
        else:
            self._waveguide.add_parameterized_path(lambda t: [t * self._taper_length, 0],
                                                   width=lambda t: taper_width(1 - t))
            self._waveguide.add_parameterized_path(lambda t: [t * self._length_taper_front, 0],
                                                   width=lambda t: pre_taper_width(1 - t))

        return self._waveguide.get_shapely_object()

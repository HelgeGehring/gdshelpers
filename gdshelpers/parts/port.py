import math
import numpy as np

from gdshelpers.helpers import normalize_phase


class Port:
    """
    Abstraction of a waveguide port.

    Other objects might dock to a port. It is simply a helper object
    to allow easy chaining of parts.

    :param origin: Origin of the port.
    :param angle: Angle of the port.
    :param width: Width of the port.
    :type width: float
    """

    def __init__(self, origin, angle, width):
        self.origin = origin
        self.angle = angle
        self.width = width

    def copy(self):
        """
        Create a copy if the port.

        :return: A copy of the port.
        :rtype: Port
        """
        return Port(self.origin, self.angle, self.width)

    def __getitem__(self, item):
        if isinstance(item, slice):
            start = item.start if item.start >= 0 else len(self.width[::2]) + item.start + 1
            stop = item.stop if item.stop >= 0 else len(self.width[::2]) + item.stop + 1
            start, stop = 2 * start, 2 * stop
        else:
            item = item if item >= 0 else len(self.width[::2]) + item
            start, stop = 2 * item, 2 * item + 1

        port = self.parallel_offset((np.sum(self.width[:stop]) + np.sum(self.width[:start])) / 2 - self.total_width / 2)
        port.width = self.width[start:stop]
        return port

    def get_parameters(self):
        """
        Get a dictionary representation of the port properties.

        :return: A dictionary containing the ``origin``, ``angle`` and ``width`` of the port.
        :rtype: dict
        """
        return {key: getattr(self, key) for key in ('origin', 'angle', 'width')}

    def set_port_properties(self, **kwargs):
        """
        Set port parameters via named keyword arguments.

        :param kwargs: The keywords to set.

        :return: The modified port
        :rtype: Port
        """
        for key, value in kwargs.items():
            assert key in ('origin', 'angle', 'width'), '"%s" is not a valid property' % key
            setattr(self, key, value)

        return self

    @property
    def inverted_direction(self):
        """
        Get a port which points in the opposite direction.

        :return: A copy of this port, pointing in the opposite direction.
        :rtype: Port
        """
        inverted_port = self.copy()
        inverted_port.angle = inverted_port.angle + math.pi
        return inverted_port

    @property
    def origin(self):
        """
        The origin coordinates of this port.

        When reading it is guarantied to be a 2-dim numpy array.
        """
        return self._origin

    # noinspection PyAttributeOutsideInit
    @origin.setter
    def origin(self, origin):
        assert len(origin) == 2, 'origin must be a 2D coordinate'
        self._origin = np.array(origin, dtype=float)

    @property
    def x(self):
        return self._origin[0]

    @x.setter
    def x(self, x):
        self._origin[0] = x

    @property
    def y(self):
        return self._origin[1]

    @y.setter
    def y(self, y):
        self._origin[1] = y

    @property
    def angle(self):
        """
        The angle of the port.
        """
        return normalize_phase(self._angle)

    # noinspection PyAttributeOutsideInit
    @angle.setter
    def angle(self, angle):
        self._angle = angle % (2 * math.pi)

    @property
    def width(self):
        """
        The width of the port. E.g. for slot waveguides it can also be an array in the format [width, gap, width, ...],
        where each width describe the width of each rail and the gap defines the gap in between.
        This array can also end with a gap, which facilitates e.g. the design of adiabatic mode converters.
        """
        return self._width

    @property
    def total_width(self):
        """
        The total width of the port.

        Guarantied to be a positive float.
        """
        return np.sum(self._width)

    # noinspection PyAttributeOutsideInit
    @width.setter
    def width(self, width):
        assert np.sum(width) > 0, 'Port width must be larger than zero'
        self._width = np.array(width) if np.array(width).size > 1 else float(width)

    def parallel_offset(self, offset):
        """
        Returns a new port, which offset in parallel from this port.

        :param offset: Offset from the center of the port. Positive is left of the port.
        :type offset: float
        :return: The new offset port
        :rtype: Port
        """
        port = self.copy()
        offset = [offset * np.cos(self.angle + np.pi / 2), offset * np.sin(self.angle + np.pi / 2)]
        port.origin = port.origin + offset
        return port

    def longitudinal_offset(self, offset):
        """
        Returns a new port, which offset in in direction of this port.

        :param offset: Offset from the end of the port. Positive is the direction, the port is pointing.
        :type offset: float
        :return: The new offset port
        :rtype: Port
        """

        port = self.copy()
        offset = [offset * np.cos(self.angle), offset * np.sin(self.angle)]
        port.origin = port.origin + offset
        return port

    def rotated(self, angle):
        """
        Returns a new port, which is rotated by the given angle.

        :param angle: Angle to rotate.
        :type angle: float
        :return: The new rotated port
        :rtype: Port
        """

        port = self.copy()
        port.angle += angle
        return port

    def with_width(self, width):
        """
        Returns a new port, of which the width is set to the new value

        :param width: Width of the resulting port
        :return: The new port
        :rtype: Port
        """

        port = self.copy()
        port.width = width
        return port

    @property
    def debug_shape(self):
        from gdshelpers.parts.waveguide import Waveguide
        d = self.total_width / 5
        wg = Waveguide.make_at_port(self.longitudinal_offset(-d), width=self.total_width * 10)
        wg.add_straight_segment(d)
        wg.width = self.width
        wg.add_straight_segment(4 * self.total_width)
        wg.width = self.width * 5
        wg.add_straight_segment(self.total_width * 5, final_width=self.total_width * 0.1)
        return wg.get_shapely_object()

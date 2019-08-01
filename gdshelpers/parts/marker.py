import numpy as np
import shapely.geometry
import shapely.affinity

from gdshelpers.geometry import geometric_union


class SquareMarker(object):
    def __init__(self, origin, size):
        """
        Creates a square marker

        :param origin: (x,y), center of square
        :type origin: tuple
        :param size: length
        :type size: float or int
        """
        assert (size >= 0)
        self.origin = np.asarray(origin)
        self.size = size

    @classmethod
    def make_marker(cls, origin, size=20):
        return cls(origin, size)

    def get_shapely_object(self):
        x, y = self.origin
        size = self.size
        box = shapely.geometry.box(0, 0, size, size)
        return shapely.affinity.translate(box, x - size / 2, y - size / 2)


class CrossMarker(object):
    """
    Simple cross type marker with support for paddles.

    This code is an adapted version of Nico's marker.
    """

    def __init__(self, origin, cross_length, cross_width, paddle_length, paddle_width):
        assert (cross_length >= 0) and (cross_width >= 0) and (paddle_length >= 0) and (paddle_width >= 0)

        self.origin = np.asarray(origin)
        self.paddle_length = paddle_length
        self.paddle_width = paddle_width
        self.cross_length = cross_length
        self.cross_width = cross_width

    @classmethod
    def make_simple_cross(cls, origin, cross_length, cross_width):
        return cls(origin, cross_length, cross_width, 0., 0.)

    @classmethod
    def make_traditional_paddle_markers(cls, origin, scale=1.,
                                        cross_length_factor=2.0, cross_width_factor=0.1,
                                        paddle_length_factor=3.0, paddle_width_factor=0.5):
        wp = paddle_width_factor * scale
        wc = cross_width_factor * scale
        lp = paddle_length_factor * scale
        lc = cross_length_factor * scale
        return cls(origin, lc, wc, lp, wp)

    def get_shapely_object(self):
        x, y = self.origin
        lp, wp, lc, wc = self.paddle_length, self.paddle_width, self.cross_length, self.cross_width

        points = [(x + wc, y + wc), (x + wc, y + lc), (x + wp, y + lc),
                  (x + wp, y + lc + lp), (x - wp, y + lc + lp), (x - wp, y + lc),
                  (x - wc, y + lc), (x - wc, y + wc), (x - lc, y + wc),
                  (x - lc, y + wp), (x - lc - lp, y + wp), (x - lc - lp, y - wp),
                  (x - lc, y - wp), (x - lc, y - wc), (x - wc, y - wc), (x - wc, y - lc),
                  (x - wp, y - lc), (x - wp, y - lc - lp), (x + wp, y - lc - lp), (x + wp, y - lc),
                  (x + wc, y - lc), (x + wc, y - wc), (x + lc, y - wc), (x + lc, y - wp),
                  (x + lc + lp, y - wp), (x + lc + lp, y + wp), (x + lc, y + wp), (x + lc, y + wc)]

        return shapely.geometry.Polygon(points)


class DLWMarker(object):
    def __init__(self, origin, box_size=2.5):
        self.origin = np.asarray(origin)
        self.box_size = box_size

    def get_shapely_object(self):
        x, y = self.origin
        upper_box = shapely.geometry.box(x, y, x + self.box_size, y + self.box_size)
        lower_box = shapely.geometry.box(x - self.box_size, y - self.box_size, x, y)
        return shapely.geometry.MultiPolygon([upper_box, lower_box])


class DLWPrecisionMarker(object):
    """
    A specific marker to test the writing accuracy/alignment of the Nanoscribe DLW machine.

    :param origin: Position of the marker.
    :param size: Size of the marker.
    :param frame_width: Size of the marker frame.
    """

    def __init__(self, origin, size, frame_width):
        self.origin = origin
        self.size = size
        self.frame_width = frame_width

    def get_shapely_object(self):
        size_half = self.size / 2.
        p1 = shapely.geometry.Polygon(
            [(-size_half, size_half + self.frame_width), (size_half, size_half + self.frame_width),
             (0, size_half)])
        p2 = shapely.geometry.Polygon([(size_half, size_half), (size_half, size_half + self.frame_width),
                                       (size_half + self.frame_width, size_half)])

        one_side = geometric_union([p1, p2])

        marker = geometric_union([shapely.affinity.rotate(one_side, phi, (0, 0)) for phi in (0, 90, 180, 270)])
        return shapely.affinity.translate(marker, self.origin[0], self.origin[1])


class AutoStigmationMarker(object):
    def __init__(self, origin, maximum_feature_size=3., minimum_feature_size=0.1, reduction_factor=1.2, resolution=16):
        self.origin = origin
        self.maximum_feature_size = maximum_feature_size
        self.minimum_feature_size = minimum_feature_size
        self.reduction_factor = reduction_factor
        self.resolution = resolution

    def get_shapely_object(self):
        radius = self.minimum_feature_size / 2
        feature_size = self.minimum_feature_size

        center_point = shapely.geometry.Point(self.origin[0], self.origin[1])
        objs = list()

        # The inner object is a circle
        objs.append(center_point.buffer(self.minimum_feature_size / 2., resolution=self.resolution))

        while feature_size < self.maximum_feature_size:
            feature_size *= self.reduction_factor
            radius += feature_size * 2

            ring = center_point.buffer(radius + feature_size, self.resolution).difference(
                center_point.buffer(radius, self.resolution))
            objs.append(ring)

        return shapely.geometry.MultiPolygon(objs)

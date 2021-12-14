import collections.abc

import numpy as np
import numpy.linalg as linalg
import scipy.interpolate
import shapely.geometry
import shapely.affinity
import shapely.ops
import shapely.validation

from gdshelpers.parts import Port
from gdshelpers.helpers import find_line_intersection, normalize_phase
from gdshelpers.helpers.bezier import CubicBezierCurve
from gdshelpers.helpers.positive_resist import convert_to_positive_resist


class Waveguide:
    def __init__(self, origin, angle, width):
        self._current_port = Port(origin, angle, width)
        self._in_port = self._current_port.inverted_direction.copy()
        self._segments = list()

    @classmethod
    def make_at_port(cls, port, **kargs):
        port_param = port.copy()
        port_param.set_port_properties(**kargs)
        return cls(**port_param.get_parameters())

    @property
    def x(self):
        return self._current_port.origin[0]

    @property
    def y(self):
        return self._current_port.origin[1]

    @property
    def origin(self):
        return self._current_port.origin

    @property
    def angle(self):
        return self._current_port.angle

    @property
    def width(self):
        return self._current_port.width

    @width.setter
    def width(self, width):
        self._current_port.width = width

    @property
    def current_port(self):
        return self._current_port.copy()

    # Add alias for current port
    port = current_port

    @property
    def in_port(self):
        return self._in_port.copy()

    @property
    def length(self):
        return sum((length for port, obj, outline, length, center_coordinates in self._segments))

    @property
    def length_last_segment(self):
        if not len(self._segments):
            return 0
        return self._segments[-1][3]

    @property
    def center_coordinates(self):
        return np.concatenate([center_coordinates for port, obj, outline, length, center_coordinates in self._segments])

    def get_shapely_object(self):
        """
        Get a shapely object which forms this path.
        """
        return shapely.ops.unary_union([obj for port, obj, outline, length, center_coordinates in self._segments])

    def get_shapely_outline(self):
        """
        Get a shapely object which forms the outline of the path.
        """
        return shapely.ops.unary_union(
            [outline for port, obj, outline, length, center_coordinates in self._segments])

    def get_segments(self):
        """
        Returns the list of tuples, containing their ports and shapely objects.
        """
        return [(port.copy(), obj, length) for port, obj, outline, length, center_coordinates in self._segments]

    def add_straight_segment(self, length, final_width=None, **kwargs):
        self._current_port.set_port_properties(**kwargs)
        final_width = final_width if final_width is not None else self.width

        if not np.isclose(length, 0):
            assert length >= 0, 'Length of straight segment must not be negative'

            self.add_parameterized_path(path=lambda t: [t * length, 0],
                                        path_derivative=lambda t: [1, 0],
                                        width=lambda t: np.array(self.width) * (1 - t) + np.array(final_width) * t,
                                        sample_points=2, sample_distance=0)
        return self

    def add_arc(self, final_angle, radius, final_width=None, n_points=128, shortest=True, **kwargs):
        delta = final_angle - self.angle
        if not np.isclose(normalize_phase(delta), 0):
            if shortest:
                delta = normalize_phase(delta)
            self.add_bend(delta, radius, final_width, n_points, **kwargs)
        return self

    def add_bend(self, angle, radius, final_width=None, n_points=128, **kwargs):
        # If number of points is None, default to 128
        n_points = n_points if n_points else 128

        self._current_port.set_port_properties(**kwargs)
        sample_points = max(int(abs(angle) / (np.pi / 2) * n_points), 2)
        final_width = final_width if final_width is not None else self.width

        angle = normalize_phase(angle, zero_to_two_pi=True) - (0 if angle > 0 else 2 * np.pi)

        self.add_parameterized_path(
            path=lambda t: [radius * np.sin(abs(angle) * t), np.sign(angle) * -radius * (np.cos(angle * t) - 1)],
            path_function_supports_numpy=True,
            path_derivative=lambda t: [radius * np.cos(abs(angle) * t) * abs(angle),
                                       np.sign(angle) * radius * (np.sin(angle * t) * angle)],
            width=lambda t: np.outer(1 - t, np.array(self.width)) + np.outer(t, np.array(final_width)),
            width_function_supports_numpy=True,
            sample_points=sample_points, sample_distance=0)

        return self

    def add_parameterized_path(self, path, width=None, sample_distance=0.50, sample_points=100, path_derivative=None,
                               path_function_supports_numpy=False, width_function_supports_numpy=False):
        """
        Generate a parameterized path.

        The path coordinate system is the origin and rotation of the current path. So if you want to continue your path
        start at (0, 0) in y-direction.

        Note, that path is either a list of (x,y) coordinate tuples or a callable function which takes one float
        parameter between 0 and 1. If you use a parameterized function, its first derivative must be continuous.
        When using a list of coordinates, these points will be connected by straight lines. They must be sufficiently
        close together to simulate a first derivative continuous path.

        This function will try to space the final points of the curve equidistantly. To achieve this, it will first
        sample the function and find its first derivative. Afterwards it can calculate the cumulative sum of the length
        of the first derivative. This allows to sample the function nearly equidistantly in a second step. This
        approach might be wasteful for paths like (x**2, y). You can suppress resampling for length by passing zero or
        none as sample_distance parameter.

        The width of the generated waveguide may be constant when passing a number, or variable along the path
        when passing an array or a callable function, using the same parameter as the path.
        For generating slot/coplanar/... waveguides, start with a `Port` which has an array of the form
        `[rail_width_1, gap_width_1, rail_width_2, ...]` set as `width` and which defines the width of each
        rail and the gaps between the rails. This array is also allowed to end with a gap_width for positioning the
        rails asymmetrically to the path which can be useful e.g. for strip-to-slot mode converters.

        Note, that your final direction of the path might not be what you expected. This is caused by the numerical
        procedure which generates numerical errors when calculating the first derivative. You can either append another
        arc to the waveguide to get to you a correct angle or you can also supply a function which is the algebraic
        first derivative. The returned vector is not required to be normed.

        By default, for each parameter point t, the parameterized functions are call. You will notice that this is
        rather slow. To achieve the best performance, write your functions in such a way, that they can handle a
        numpy array as parameter *t*. Once the *path_function_supports_numpy* option is set to True, the function will
        be called only once, speeding up the calculation considerable.

        :param path:
        :param width:
        :param sample_distance:
        :param sample_points:
        :param path_derivative:
        :param path_function_supports_numpy:
        :param width_function_supports_numpy:
        """

        if callable(path):
            presample_t = np.linspace(0, 1, sample_points)

            if path_function_supports_numpy:
                presample_coordinates = np.array(path(presample_t)).T
            else:
                presample_coordinates = np.array([path(x) for x in presample_t])

            if sample_distance:
                # # Calculate the derivative
                # if path_derivative:
                #     assert callable(path_derivative), 'The derivative of the path function must be callable'
                #     presample_coordinates_d1 = np.array([path_derivative(x) for x in presample_t[:-1]])
                # else:
                #     presample_coordinates_d1 = np.diff(presample_coordinates, axis=0)
                presample_coordinates_d1 = np.diff(presample_coordinates, axis=0)
                presample_coordinates_d1_norm = np.linalg.norm(presample_coordinates_d1, axis=1)
                presample_coordinates_d1__cum_norm = np.insert(np.cumsum(presample_coordinates_d1_norm), 0, 0)

                lengths = np.linspace(presample_coordinates_d1__cum_norm[0],
                                      presample_coordinates_d1__cum_norm[-1],
                                      int(presample_coordinates_d1__cum_norm[-1] / sample_distance))

                # First get the spline representation. This is needed since we manipulate these directly for roots
                # finding.
                spline_rep = scipy.interpolate.splrep(presample_t, presample_coordinates_d1__cum_norm, s=0)

                def find_y(y):
                    interp_result = scipy.interpolate.sproot((spline_rep[0], spline_rep[1] - y, spline_rep[2]), mest=1)
                    return interp_result[0] if len(interp_result) else None

                # We need a small hack here and exclude lengths[0]==0 since it finds no root there
                sample_t = np.array([0, ] + [find_y(length) for length in lengths[1:-1]] + [1, ])

                if path_function_supports_numpy:
                    sample_coordinates = np.array(path(sample_t)).T
                else:
                    sample_coordinates = np.array([path(x) for x in sample_t])
            else:
                sample_coordinates = presample_coordinates
                sample_t = presample_t
        else:
            # If we do not have a sample function, we need to "invent a sampling parameter"
            sample_coordinates = np.array(path)
            sample_t = np.linspace(0, 1, sample_coordinates.shape[0])

        rotation_matrix = np.array(((np.cos(self._current_port.angle), -np.sin(self._current_port.angle)),
                                    (np.sin(self._current_port.angle), np.cos(self._current_port.angle))))
        sample_coordinates = self._current_port.origin + np.einsum('ij,kj->ki', rotation_matrix, sample_coordinates)

        # Calculate the derivative
        if callable(path_derivative):
            if path_function_supports_numpy:
                sample_coordinates_d1 = np.array(path_derivative(sample_t)).T
            else:
                sample_coordinates_d1 = np.array([path_derivative(x) for x in sample_t])
            sample_coordinates_d1 = np.einsum('ij,kj->ki', rotation_matrix, sample_coordinates_d1)
        else:
            if path_derivative is None:
                sample_coordinates_d1 = np.vstack((rotation_matrix[:, 0], np.diff(sample_coordinates, axis=0)))
            else:
                sample_coordinates_d1 = np.array(path_derivative)
                sample_coordinates_d1 = np.einsum('ij,kj->ki', rotation_matrix, sample_coordinates_d1)

        sample_coordinates_d1_norm = np.linalg.norm(sample_coordinates_d1, axis=1)
        sample_coordinates_d1_normed = sample_coordinates_d1 / sample_coordinates_d1_norm[:, None]

        # Find the orthogonal vectors to the derivative
        sample_coordinates_d1_normed_ortho = np.vstack((sample_coordinates_d1_normed[:, 1],
                                                        -sample_coordinates_d1_normed[:, 0])).T

        # Calculate the width of the waveguide at the given positions
        if callable(width):
            if width_function_supports_numpy:
                sample_width = width(sample_t)
            else:
                sample_width = np.array([width(x) for x in sample_t])
            if sample_width.ndim == 1:  # -> width returned a scalar for each x
                sample_width = sample_width[..., np.newaxis]
        else:
            if width is None:
                sample_width = np.atleast_1d(self._current_port.width)
                sample_width = sample_width[np.newaxis, ...]  # width constant -> new axis along path
            else:
                sample_width = np.atleast_1d(width)
                if sample_width.ndim == 1:  # -> width is a scalar for each x
                    sample_width = sample_width[..., np.newaxis]

        # Now we have everything to calculate the polygon
        polygons = []
        half_width = np.sum(sample_width, axis=-1) / 2
        for i in range((sample_width.shape[-1] + 1) // 2):
            start = np.sum(sample_width[:, :(2 * i)], axis=-1) - half_width
            stop = start + sample_width[:, 2 * i]
            poly_path_1 = sample_coordinates + start[..., None] * sample_coordinates_d1_normed_ortho
            poly_path_2 = sample_coordinates + stop[..., None] * sample_coordinates_d1_normed_ortho
            poly_path = np.concatenate([poly_path_1, poly_path_2[::-1, :]])

            assert shapely.geometry.LineString(poly_path).is_simple, \
                'Outer lines of parameterized wg intersect. Try using larger bend radii or smaller a smaller wg'

            # Now add the shapely objects and do book keeping
            polygon = shapely.geometry.Polygon(poly_path)
            assert polygon.is_valid, 'Generated polygon path is not valid: %s' % \
                                     shapely.validation.explain_validity(polygon)
            polygons.append(polygon)
        polygon = shapely.geometry.MultiPolygon(polygons)

        outline_poly_path_1 = sample_coordinates - np.sum(sample_width,
                                                          axis=-1)[..., None] / 2 * sample_coordinates_d1_normed_ortho
        outline_poly_path_2 = sample_coordinates + np.sum(sample_width,
                                                          axis=-1)[..., None] / 2 * sample_coordinates_d1_normed_ortho
        outline = shapely.geometry.Polygon(np.concatenate([outline_poly_path_1, outline_poly_path_2[::-1, :]]))

        length = np.sum(np.linalg.norm(np.diff(sample_coordinates, axis=0), axis=1))
        self._segments.append((self._current_port.copy(), polygon, outline, length, sample_coordinates))

        self._current_port.origin = sample_coordinates[-1]
        # If the width does not need to be a list, convert it back to a scalar
        self._current_port.width = sample_width[-1]
        self._current_port.angle = np.arctan2(sample_coordinates_d1[-1][1], sample_coordinates_d1[-1][0])
        return self

    def add_cubic_bezier_path(self, p0, p1, p2, p3, width=None, **kwargs):
        """
        Add a cubic bezier path to the waveguide.

        Coordinates are in the "waveguide tip coordinate system", so the first point will probably be p0 == (0, 0).
        Note that your bezier curve undergoes the same restrictions as a parameterized path. Don't self-intersect it and
        don't use small bend radii.

        :param p0: 2 element tuple like coordinates
        :param p1: 2 element tuple like coordinates
        :param p2: 2 element tuple like coordinates
        :param p3: 2 element tuple like coordinates
        :param width: Width of the waveguide, as passed to :func:add_parameterized_path
        :param kwargs: Optional keyword arguments, passed to :func:add_parameterized_path
        :return: Changed waveguide
        :rtype: Waveguide
        """

        bezier_curve = CubicBezierCurve(p0, p1, p2, p3)

        self.add_parameterized_path(path=bezier_curve.evaluate, path_derivative=bezier_curve.evaluate_d1, width=width,
                                    path_function_supports_numpy=True, **kwargs)
        return self

    def add_bezier_to(self, final_coordinates, final_angle, bend_strength, width=None, **kwargs):

        try:
            bs1, bs2 = float(bend_strength[0]), float(bend_strength[1])
        except (KeyError, TypeError):
            bs1 = bs2 = float(bend_strength)

        final_port = Port(final_coordinates, final_angle, self.width)
        p0 = (0, 0)
        p1 = self._current_port.longitudinal_offset(bs1).origin - self._current_port.origin
        p2 = final_port.longitudinal_offset(-bs2).origin - self._current_port.origin
        p3 = final_coordinates - self._current_port.origin

        tmp_wg = Waveguide.make_at_port(self._current_port.copy().set_port_properties(angle=0))
        tmp_wg.add_cubic_bezier_path(p0, p1, p2, p3, width=width, **kwargs)

        self._segments.append(
            (self._current_port.copy(), tmp_wg.get_shapely_object(), tmp_wg.get_shapely_outline(), tmp_wg.length,
             tmp_wg.center_coordinates))
        self._current_port = tmp_wg.current_port

        return self

    def add_bezier_to_port(self, port, bend_strength, width=None, **kwargs):
        if not width and not np.isclose(np.array(self.width), np.array(port.width)):
            def width(t):
                return t * (port.width - self.width) + self.width

            supports_numpy = True
        else:
            supports_numpy = False

        kwargs['width_function_supports_numpy'] = kwargs.get('width_function_supports_numpy', supports_numpy)

        self.add_bezier_to(port.origin, port.inverted_direction.angle, bend_strength, width, **kwargs)
        return self

    def add_route_single_circle_to(self, final_coordinates, final_angle, final_width=None, max_bend_strength=None,
                                   on_line_only=False):

        """
        Connect two points by straight lines and one circle.

        Works for geometries like round edges and others. The final straight line can also be omitted so that
        the waveguide only end on the line described by the support vector and angle.

        By default, this method tries to route to the target with the greatest possible circle. But the valid
        bending range may be limited via the `max_bend_strength` parameter.

        This method does not work for geometries which cannot be connected only by straight lines and one
        circle, such as parallel lines etc.

        Still, this method can prove extremely useful for routing to i.e. grating couplers etc.

        :param final_coordinates: Final destination point.
        :param final_angle: Final angle of the waveguide.
        :param final_width: Final width of the waveguide.
        :param max_bend_strength: The maximum allowed bending radius.
        :param on_line_only: Omit the last straight line and only route to described line.
        """
        # We are given an out angle, but the internal math is for inward pointing lines
        final_angle = normalize_phase(final_angle) + np.pi
        final_width = final_width if final_width is not None else self.width
        # We need to to some linear algebra. We first find the intersection of the two waveguides
        r1 = self._current_port.origin
        r2 = np.array(final_coordinates)
        intersection_point, distance = find_line_intersection(r1, self.angle, r2, final_angle)

        assert distance[0] >= 0, 'Origin waveguide is too close to target. No curve possible'
        assert on_line_only or distance[1] >= 0, 'Target position is too close to target. No curve possible'

        # Calculate the angle bisector
        u1 = np.array([np.cos(self.angle), np.sin(self.angle)])
        u2 = np.array([np.cos(final_angle), np.sin(final_angle)])
        u_half = u1 + u2
        half_angle = np.arctan2(u_half[1], u_half[0])
        diff_angle = normalize_phase(self.angle - final_angle - np.pi)

        _, r1 = find_line_intersection(r1, self.angle + np.pi / 2, intersection_point, half_angle)

        if not on_line_only:
            max_poss_radius = min(
                np.abs([r1[0], distance[0] / np.tan(diff_angle / 2), distance[1] / np.tan(diff_angle / 2)]))
        else:
            max_poss_radius = min(np.abs([r1[0], distance[0] / np.tan(diff_angle / 2)]))

        radius = min([max_bend_strength, max_poss_radius]) if max_bend_strength is not None else max_poss_radius
        d = abs(radius * np.tan(diff_angle / 2))
        if on_line_only:
            segments = [distance[0] - d, radius * diff_angle]
        else:
            segments = [distance[0] - d, radius * diff_angle, distance[1] - d]
        segment_ratio = np.cumsum(segments / sum(segments))
        segment_widths = [(final_width - self.current_port.width) * ratio + self.current_port.width for ratio
                          in segment_ratio]
        tmp_wg = Waveguide.make_at_port(self._current_port)
        tmp_wg.add_straight_segment(length=distance[0] - d, final_width=segment_widths[0])
        tmp_wg.add_bend(-diff_angle, radius, final_width=segment_widths[1])
        if not on_line_only:
            tmp_wg.add_straight_segment(distance[1] - d, final_width=segment_widths[2])

        self._segments.append(
            (self._current_port.copy(), tmp_wg.get_shapely_object(), tmp_wg.get_shapely_outline(), tmp_wg.length,
             tmp_wg.center_coordinates))
        self._current_port = tmp_wg.current_port

        return self

    def add_route_single_circle_to_port(self, port, max_bend_strength=None, on_line_only=False):
        """
        Connect to port by straight lines and one circle.

        Helper function to conveniently call add_route_single_circle_to.
        :param port: Target port.
        :param max_bend_strength: The maximum allowed bending radius.
        :param on_line_only: Omit the last straight line and only route to line described by port.
        """
        self.add_route_single_circle_to(port.origin, port.inverted_direction.angle, port.width, max_bend_strength,
                                        on_line_only)
        return self

    def add_route_straight_to_port(self, port):
        """
        Add a straight segment to a given port. The added segment will keep
        the angle of the current port at the start and use the angle of the
        target port at the end. If the ports are laterally shifted, this
        will result in a trapezoidal shape.

        The width will be linearly tapered to that of the target port.

        :param port: Target port.
        """
        start_width = np.array(self.current_port.width)
        final_width = np.array(port.width)

        c, s = np.cos(-self.current_port.angle), np.sin(-self.current_port.angle)
        R = np.array([[c, -s], [s, c]])
        end_point = R @ (np.array(port.origin) - np.array(self.current_port.origin))

        angle_diff = port.inverted_direction.angle - self.current_port.angle
        start_deriv = np.array([1, 0])
        end_deriv = np.array([np.cos(angle_diff), np.sin(angle_diff)])

        self.add_parameterized_path(path=lambda t: np.array([0, 0]) * (1 - t) + end_point * t,
                                    width=lambda t: start_width * (1 - t) + final_width * t,
                                    path_derivative=lambda t: start_deriv * (1 - t) + end_deriv * t,
                                    sample_points=2, sample_distance=0)

        return self

    def add_straight_segment_to_intersection(self, line_origin, line_angle, **line_kw):
        """
        Add a straight line until it intersects with an other line.

        The other line is described by the support vector and the line angle.

        :param line_origin: Intersection line support vector.
        :param line_angle: Intersection line angle.
        :param line_kw: Parameters passed on to add_straight_segment.
        :raise ArithmeticError: When there is no intersection due to being parallel or if
                                the intersection is behind the waveguide.
        """
        r1 = self._current_port.origin
        r2 = np.array(line_origin)

        try:
            intersection_point, distance = find_line_intersection(r1, self.angle, r2, line_angle)
            if np.isclose(distance[0], 0):
                return self
            elif distance[0] < 0:
                raise ArithmeticError('No forward intersection of waveguide with given line')
            self.add_straight_segment(distance[0], **line_kw)
        except linalg.LinAlgError:
            # We do not find an intersection if lines are parallel
            raise ArithmeticError('There is no intersection with the given line')
        return self

    def add_straight_segment_until_x(self, x, **line_kw):
        """
        Add straight segment until the given x value is reached.

        :param x: value
        :param line_kw: Parameters passed on to add_straight_segment.
        """
        self.add_straight_segment_to_intersection([x, 0], np.pi / 2, **line_kw)
        return self

    def add_straight_segment_until_y(self, y, **line_kw):
        """
        Add straight segment until the given y value is reached.

        :param y: value
        :param line_kw: Parameters passed on to add_straight_segment.
        """
        self.add_straight_segment_to_intersection([0, y], 0, **line_kw)
        return self

    def add_straight_segment_until_level_of_port(self, port, **line_kw):
        """
        Add a straight line until it is on the same level as the given port. If several ports are given in a list,
        the most distant port is chosen.

        In this context "on the same level" means the intersection of the waveguide with the line
        orthogonal to the given port.

        :param port: The port or a list of ports.
        :param line_kw:
        """

        if isinstance(port, collections.abc.Iterable):
            direction = (np.cos(self.angle), np.sin(self.angle))
            distances = np.array([np.dot(p.origin, direction) for p in port])
            furthest_port_idx = distances.argmax()
            port = port[furthest_port_idx]

        self.add_straight_segment_to_intersection(port.origin, port.angle - np.pi / 2, **line_kw)
        return self

    def add_left_bend(self, radius, angle=np.pi/2):
        """
        Add a left turn (90° or as defined by angle) with the given bend radius
        """
        return self.add_bend(angle, radius)

    def add_right_bend(self, radius, angle=np.pi/2):
        """
        Add a right turn (90° or as defined by angle) with the given bend radius
        """
        return self.add_bend(-angle, radius)


def _example():
    from gdshelpers.geometry.chip import Cell
    from gdshelpers.parts.splitter import Splitter
    from gdshelpers.parts.coupler import GratingCoupler

    port = Port([0, 0], 0, 1)
    path = Waveguide.make_at_port(port)

    path.add_straight_segment(10)
    path.add_bend(np.pi / 2, 10, final_width=0.5)
    path.add_bend(-np.pi / 2, 10, final_width=1)
    path.add_arc(np.pi * 3 / 4, 10, )

    splitter = Splitter.make_at_root_port(path.current_port, 30, 10)
    path2 = Waveguide.make_at_port(splitter.right_branch_port)
    path2.add_bend(-np.pi / 4, 10)

    n = 10
    path2.add_parameterized_path(lambda t: (n * 10 * t, np.cos(n * 2 * np.pi * t) - 1),
                                 path_derivative=lambda t: (n * 10, -n * 2 * np.pi * np.sin(n * 2 * np.pi * t)),
                                 width=lambda t: np.cos(n * 2 * np.pi * t) * 0.2 + np.exp(-t) * 0.3 + 0.5,
                                 width_function_supports_numpy=True)
    path2.add_straight_segment(10, width=[.5, .5, .5])
    print(path2.length)
    print(path2.length_last_segment)

    path2.add_cubic_bezier_path((0, 0), (5, 0), (10, 10), (5, 10))
    path2.add_bend(-np.pi, 40)

    coupler1 = GratingCoupler([100, 50], 0, 1, np.deg2rad(30), [10, 0.1, 2, 0.1, 2], start_radius_absolute=True)

    path3 = Waveguide((0, -50), np.deg2rad(0), 1)
    path3.add_bezier_to(coupler1.port.origin, coupler1.port.inverted_direction.angle, bend_strength=50)

    splitter2 = Splitter.make_at_left_branch_port(splitter.left_branch_port, 30, 10, wavelength_root=2)

    path4 = Waveguide.make_at_port(splitter2.root_port)
    path4.add_straight_segment(20)
    path4.width = 1
    path4.add_straight_segment(20)

    empty_path = Waveguide.make_at_port(path4.current_port)

    whole_layout = (path, splitter, path2, splitter2, coupler1, path3, path4, empty_path)

    layout = Cell('LIBRARY')
    cell = Cell('TOP')
    cell.add_to_layer(1, *whole_layout)
    cell.add_to_layer(2, empty_path)
    cell.add_to_layer(4, splitter.root_port.debug_shape)

    layout.add_cell(cell)

    cell_df = Cell('TOP_DF')
    cell_df.add_to_layer(1, convert_to_positive_resist(whole_layout, buffer_radius=1.5))
    layout.add_cell(cell_df)

    layout.save('output.gds')
    cell.show()


if __name__ == '__main__':
    _example()

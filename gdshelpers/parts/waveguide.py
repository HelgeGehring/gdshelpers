from __future__ import print_function, division

import collections

import shapely.geometry
import shapely.affinity
import shapely.ops
import shapely.validation

from gdshelpers.parts import Port
from gdshelpers.helpers import find_line_intersection, normalize_phase
from gdshelpers.helpers.bezier import CubicBezierCurve
from gdshelpers.helpers.positive_resist import convert_to_positive_resist

import numpy as np
import numpy.linalg as linalg
import scipy.interpolate


class Waveguide(object):
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
        return sum((length for port, obj, length in self._segments))

    @property
    def length_last_segment(self):
        if not len(self._segments):
            return 0
        return self._segments[-1][2]

    def get_shapely_object(self):
        """
        Get a shapely object which forms this path.
        """
        return shapely.ops.cascaded_union([obj for port, obj, length in self._segments])

    def get_segments(self):
        """
        Returns the list of tuples, containing their ports and shapely objects.
        """
        return [(port.copy(), obj, length) for port, obj, length in self._segments]

    def add_straight_segment(self, length, final_width=None, **kargs):
        self._current_port.set_port_properties(**kargs)
        final_width = final_width or self.width

        endpoint = shapely.geometry.Point(length, 0)

        if not np.isclose(length, 0):
            assert length >= 0, 'Length of straight segment must not be negative'
            polygon = shapely.geometry.Polygon(([0, self.width / 2], [length, final_width / 2],
                                                [length, -final_width / 2], [0, -self.width / 2]))
            polygon = shapely.affinity.rotate(polygon, self.angle, origin=[0, 0], use_radians=True)
            polygon = shapely.affinity.translate(polygon, self.x, self.y)
            self._segments.append((self._current_port.copy(), polygon, length))

        endpoint = shapely.affinity.rotate(endpoint, self.angle, origin=[0, 0], use_radians=True)
        endpoint = shapely.affinity.translate(endpoint, self.x, self.y)

        self._current_port.origin = endpoint.coords[0]
        self._current_port.width = final_width
        return self

    def add_arc(self, final_angle, radius, final_width=None, n_points=128, shortest=True, **kwargs):
        delta = final_angle - self.angle
        if not np.isclose(normalize_phase(delta), 0):
            if shortest:
                delta = normalize_phase(delta)
            self.add_bend(delta, radius, final_width, n_points, **kwargs)
        return self

    def add_bend(self, angle, radius, final_width=None, n_points=128, **kargs):
        # If number of points is None, default to 128
        n_points = n_points if n_points else 128

        self._current_port.set_port_properties(**kargs)
        final_width = final_width or self.width

        angle = normalize_phase(angle, zero_to_two_pi=True) - (0 if angle > 0 else 2 * np.pi)

        if not np.isclose(radius, 0) and not np.isclose(angle, 0) and radius > 0:
            if angle > 0:
                circle_center = (-np.sin(self.angle) * radius, np.cos(self.angle) * radius) + self.current_port.origin
                start_angle = -np.pi / 2 + self.angle
            else:
                circle_center = (np.sin(self.angle) * radius, -np.cos(self.angle) * radius) + self.current_port.origin
                start_angle = np.pi / 2 + self.angle

            end_angle = start_angle + angle

            # Calculate the points needed for this angle
            points = max(int(abs(end_angle - start_angle) / (np.pi / 2) * n_points), 2)

            phi = np.linspace(start_angle, end_angle, points)
            upper_radius_points = np.linspace(radius - self.width / 2, radius - final_width / 2, points)
            upper_line_points = np.array([upper_radius_points * np.cos(phi),
                                          upper_radius_points * np.sin(phi)]).T + circle_center

            lower_radius_points = np.linspace(radius + self.width / 2, radius + final_width / 2, points)
            lower_line_points = np.array([lower_radius_points * np.cos(phi),
                                          lower_radius_points * np.sin(phi)]).T + circle_center

            polygon = shapely.geometry.Polygon(np.concatenate([upper_line_points, lower_line_points[::-1, :]]))
            self._segments.append((self._current_port.copy(), polygon, abs(angle) * radius))

            endpoint = shapely.geometry.Point(radius * np.cos(end_angle) + circle_center[0],
                                              radius * np.sin(end_angle) + circle_center[1])
            self._current_port.origin = endpoint.coords[0]

        self._current_port.width = final_width
        self._current_port.angle += angle

        # assert self._segments[-1][1].is_valid, \
        #     'Invalid polygon generated: %s' % shapely.validation.explain_validity(self._segments[-1][1])

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

        The width of the generated waveguide may either be constant when passing a number or also be a callable
        function, using the same parameter as the path.

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

        path_callable = callable(path)
        if path_callable:
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
                presample_coordinates_d1_norm = np.apply_along_axis(linalg.norm, 1, presample_coordinates_d1)
                presample_coordinates_d1__cum_norm = np.insert(np.cumsum(presample_coordinates_d1_norm), 0, 0)

                lengths = np.linspace(presample_coordinates_d1__cum_norm[0],
                                      presample_coordinates_d1__cum_norm[-1],
                                      presample_coordinates_d1__cum_norm[-1] // sample_distance)

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

        # Calculate the derivative
        if path_derivative:
            assert callable(path_derivative), 'The derivative of the path function must be callable'
            if path_function_supports_numpy:
                sample_coordinates_d1 = np.array(path_derivative(sample_t)).T
            else:
                sample_coordinates_d1 = np.array([path_derivative(x) for x in sample_t])
        else:
            sample_coordinates_d1 = np.vstack(([1, 0], np.diff(sample_coordinates, axis=0)))

        sample_coordinates_d1_norm = np.apply_along_axis(linalg.norm, 1, sample_coordinates_d1)
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
        else:
            sample_width = np.array([(width if width else self.current_port.width), ])

        # Now we have everything to calculate the polygon
        poly_path_1 = sample_coordinates + sample_width[:, None] / 2 * sample_coordinates_d1_normed_ortho
        poly_path_2 = sample_coordinates - sample_width[:, None] / 2 * sample_coordinates_d1_normed_ortho

        assert shapely.geometry.LineString(np.concatenate([poly_path_1, poly_path_2[::-1, :]])).is_simple, \
            'Outer lines of parameterized wg intersect. Try using lower bend radii or smaller a smaller wg'

        # Now add the shapely objects and do book keeping
        polygon = shapely.geometry.Polygon(np.concatenate([poly_path_1, poly_path_2[::-1, :]]))
        assert polygon.is_valid, 'Generated polygon path is not valid: %s' % \
                                 shapely.validation.explain_validity(polygon)

        polygon = shapely.affinity.rotate(polygon, self.angle, origin=[0, 0], use_radians=True)
        polygon = shapely.affinity.translate(polygon, self.x, self.y)

        length = np.sum(np.apply_along_axis(linalg.norm, 1, np.diff(sample_coordinates, axis=0)))
        self._segments.append((self._current_port.copy(), polygon, length))

        endpoint = shapely.geometry.Point(sample_coordinates[-1][0], sample_coordinates[-1][1])
        endpoint = shapely.affinity.rotate(endpoint, self.angle, origin=[0, 0], use_radians=True)
        endpoint = shapely.affinity.translate(endpoint, self.x, self.y)
        self._current_port.origin = endpoint.coords[0]

        self._current_port.width = sample_width[-1] if callable(width) else sample_width
        self._current_port.angle += np.arctan2(sample_coordinates_d1[-1][1], sample_coordinates_d1[-1][0])
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
        p1 = self.current_port.longitudinal_offset(bs1).origin - self.current_port.origin
        p2 = final_port.longitudinal_offset(-bs2).origin - self.current_port.origin
        p3 = final_coordinates - self.current_port.origin

        tmp_wg = Waveguide.make_at_port(self.current_port.copy().set_port_properties(angle=0))
        tmp_wg.add_cubic_bezier_path(p0, p1, p2, p3, width=width, **kwargs)

        self._segments.append((self._current_port.copy(), tmp_wg.get_shapely_object(), tmp_wg.length))
        self._current_port = tmp_wg.current_port

        return self

    def add_bezier_to_port(self, port, bend_strength, width=None, **kwargs):
        if not width and not np.isclose(self.width, port.width):
            width = lambda t: t * (port.width - self.width) + self.width
            supports_numpy = True
        else:
            supports_numpy = False

        kwargs['width_function_supports_numpy'] = kwargs.get('width_function_supports_numpy', supports_numpy)

        self.add_bezier_to(port.origin, port.inverted_direction.angle, bend_strength, width, **kwargs)
        return self

    def add_route_single_circle_to(self, final_coordinates, final_angle, max_bend_strength=None,
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
        :param max_bend_strength: The maximum allowed bending radius.
        :param on_line_only: Omit the last straight line and only route to described line.
        """
        # We are given an out angle, but the internal math is for inward pointing lines
        final_angle = normalize_phase(final_angle) + np.pi

        # We need to to some linear algebra. We first find the intersection of the two waveguides
        r1 = self.current_port.origin
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

        tmp_wg = Waveguide.make_at_port(self.current_port)
        tmp_wg.add_straight_segment(distance[0] - d)
        tmp_wg.add_bend(-diff_angle, radius)

        self._segments.append((self._current_port.copy(), tmp_wg.get_shapely_object(), tmp_wg.length))
        self._current_port = tmp_wg.current_port

        if not on_line_only:
            self.add_straight_segment(distance[1] - d)

        return self

    def add_route_single_circle_to_port(self, port, max_bend_strength=None, on_line_only=False):
        """
        Connect to port by straight lines and one circle.

        Helper function to conveniently call add_route_single_circle_to.
        :param port: Target port.
        :param max_bend_strength: The maximum allowed bending radius.
        :param on_line_only: Omit the last straight line and only route to line described by port.
        """
        self.add_route_single_circle_to(port.origin, port.inverted_direction.angle, max_bend_strength, on_line_only)
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
        r1 = self.current_port.origin
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

        if isinstance(port, collections.Iterable):
            direction = (np.cos(self.angle), np.sin(self.angle))
            distances = np.array([np.dot(p.origin, direction) for p in port])
            furthest_port_idx = distances.argmax()
            port = port[furthest_port_idx]

        self.add_straight_segment_to_intersection(port.origin, port.angle - np.pi / 2, **line_kw)
        return self


def _example():
    import gdsCAD
    import gdsCAD.templates

    from gdshelpers.geometry import convert_to_gdscad, geometric_union
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
    path2.add_straight_segment(10)
    print(path2.length)
    print(path2.length_last_segment)

    path2.add_cubic_bezier_path((0, 0), (5, 0), (10, 10), (5, 10))

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

    layout = gdsCAD.core.Layout('LIBRARY')
    cell = gdsCAD.core.Cell('TOP')
    cell.add(convert_to_gdscad(whole_layout))
    cell.add(convert_to_gdscad(empty_path, layer=2))
    cell.add(convert_to_gdscad(splitter.root_port.debug_shape, layer=4))

    layout.add(cell)

    cell_df = gdsCAD.core.Cell('TOP_DF')
    cell_df.add(convert_to_gdscad(convert_to_positive_resist(whole_layout, buffer_radius=1.5)))
    layout.add(cell_df)

    layout.save('output.gds')
    cell.show()


if __name__ == '__main__':
    _example()

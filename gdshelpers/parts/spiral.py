import numpy as np

from gdshelpers.geometry import geometric_union
from gdshelpers.parts.waveguide import Waveguide
from gdshelpers.parts.port import Port


class Spiral:
    def __init__(self, origin, angle, width, num, gap, inner_gap):
        """
        Creates a Spiral around the given origin

        :param origin: position of the center of the spiral
        :param angle: angle of the outer two waveguides
        :param width: width of the waveguide
        :param num: number of turns
        :param gap: gap between two waveguides
        :param inner_gap: inner radius of the spiral
        """
        self._origin_port = Port(origin, angle, width)
        self.gap = gap
        self.inner_gap = inner_gap
        self.num = num
        self.wg_in = None
        self.wg_out = None

    @classmethod
    def make_at_port(cls, port, num, gap, inner_gap):
        """
        Creates a Spiral around the given port

        :param port: port at which the spiral starts
        :param num: number of turns
        :param gap: gap between two waveguides
        :param inner_gap: inner radius of the spiral
        """
        return cls(port.parallel_offset(-num * (port.total_width + gap) - inner_gap).origin,
                   port.angle, port.width, num, gap, inner_gap)

    ###
    # Let's allow the user to change the values
    # hidden in _origin_port. Hence the internal use
    # of a Port is transparent.
    @property
    def origin(self):
        return self._origin_port.origin

    @origin.setter
    def origin(self, origin):
        self._origin_port.origin = origin

    @property
    def angle(self):
        return self._origin_port.angle

    @angle.setter
    def angle(self, angle):
        self._origin_port.angle = angle

    @property
    def width(self):
        return self._origin_port.width

    @width.setter
    def width(self, width):
        self._origin_port.width = width

    @property
    def in_port(self):
        return self._origin_port.inverted_direction.parallel_offset(
            -self.num * (self._origin_port.total_width + self.gap) - self.inner_gap)

    @property
    def out_port(self):
        return self._origin_port.parallel_offset(
            -self.num * (self._origin_port.total_width + self.gap) - self.inner_gap)

    @property
    def length(self):
        if not self.wg_in or not self.wg_out:
            self._generate()
        return self.wg_in.length + self.wg_out.length

    def _generate(self):
        def path(a):
            return (self.num * (self._origin_port.total_width + self.gap) * np.abs(1 - a) + self.inner_gap) * np.array(
                (np.sin(np.pi * a * self.num), np.cos(np.pi * a * self.num)))

        self.wg_in = Waveguide.make_at_port(self._origin_port)
        self.wg_in.add_parameterized_path(path)

        self.wg_out = Waveguide.make_at_port(self._origin_port.inverted_direction)
        self.wg_out.add_parameterized_path(path)

        self.wg_in.add_route_single_circle_to_port(self._origin_port.rotated(-np.pi * (self.num % 2)))
        self.wg_in.add_route_single_circle_to_port(self.wg_out.port)

    def get_shapely_object(self):
        if not self.wg_in or not self.wg_out:
            self._generate()
        return geometric_union([self.wg_in, self.wg_out])


def _example_old():
    from gdshelpers.geometry.chip import Cell

    wg = Waveguide((0, 0), 1, 1)
    wg.add_straight_segment(30)
    spiral = Spiral.make_at_port(wg.current_port, 2, 5, 50)
    print(spiral.out_port.origin)
    wg2 = Waveguide.make_at_port(spiral.out_port)
    wg2.add_straight_segment(100)

    print(spiral.length)

    cell = Cell('Spiral')
    cell.add_to_layer(1, wg, spiral, wg2)
    cell.show()


def _arc_length_indefinite_integral(theta, a, b):
    """
    The indefinite integral 

    .. math::
        \f{x} = \int r^2 + \frac{\,dr}{\,d\theta}\,d\theta
        
    which is needed to calculate the arc length of a spiral.
    """
    return np.sqrt( np.square((a + b * theta)) + np.square(b) ) * (a+b*theta) / (2*b) + \
        0.5 * b * np.log(np.sqrt( np.square(a + b*theta) + np.square(b) ) + a + b*theta )

def _arc_length_integral(theta, a, b, offset):
    return _arc_length_indefinite_integral(theta, a, b) - _arc_length_indefinite_integral(0, a, b)

def _spiral_length_angle(theta, a, b, offset, out_angle):
    _, _, circle_length = _circle_segment_params(a, b)
    return (_arc_length_integral(theta, a - offset, b, offset) + # Inward spiral
        2*circle_length + #2 *np.pi * a + # Two semi-circles in the center
        _arc_length_integral(theta + out_angle, a + offset, b, offset)) # Outward spiral

def _spiral_length_inline(theta, a, b, offset):
    return (_spiral_length_angle(theta, a, b, 0, offset) +
        (a + b*(theta+0.5*np.pi)) - (0.5 * a) +
        np.pi * (0.5 * a) + # two bends
        (2*(a + b * theta) - 2*(0.5 * a)))  # from endpoint to startpoint height

def _spiral_length_inline_rel(theta, a, b, offset):
    return (_spiral_length_inline(theta, a, b, offset) -
        (a + b * (theta + 0.5 * np.pi) + (0.5 * a))) # subtract the direct path from input to output

def _spiral_theta(length, wg_width, gap, min_bend_radius, offset, length_function, *args):
    """
    Numerically calculate the theta that is needed for a given spiral variant (length_function) in order
    to have the desired length.

    :param length_function: A function which takes theta, a, b, offset plus arbitrary *args.
    """
    from scipy.optimize import fsolve
    a = 2*min_bend_radius
    b = 2*(np.sum(wg_width) + gap) / (2.*np.pi)
    return fsolve(lambda x: length_function(x, a, b, offset, *args) - length, 20*np.pi)

def _circle_segment_params(a, b):
    """
    Calculate the inner semi-circle segments.
    Since the facet of the spiral in the center has a slightly different angle than the tangent of a circle with the min_bend_radius
    we don't use a full semi circle, but only start the part of the semi circle at the point where the tangent matches the spiral tangent.
    This semi-circle segment needs to be extended in height by a straight piece (missing_height) to connect the spiral with it's center point.

    Returns circ_angle, missing_height, circ_length
    """
    rot_in_1 = np.arctan2(b, a)
    circ_angle = 0.5 * np.pi - rot_in_1
    circ_seg_height = a * np.sin(circ_angle) # = 2 * min_bend_radius * sin(angle / 2), since full_angle = 2*circ_angle
    missing_height = a - circ_seg_height
    return circ_angle, missing_height, circ_angle * a + missing_height

def _spiral_out_path(t, a, b, max_theta, theta_offset=0, direction=-1):
    theta = t * max_theta
    r = a + b * theta
    #return np.array([r*np.sin(theta + theta_offset), -r*direction*np.cos(theta + theta_offset) + direction*a])# + np.array([0, direction*a])[:, None]
    return np.array([r*np.sin(theta + theta_offset), -r*direction*np.cos(theta + theta_offset)])# + np.array([0, direction*a])[:, None]

def _d_spiral_out_path(t, a, b, max_theta, theta_offset=0, direction=-1):
    """
    The derivative of the spiral.
    Note that, unlike a circle, the y-component is not 0 for theta = n*2pi
    """
    theta = t * max_theta
    r = a + b * theta
    return r * max_theta * np.array([np.cos(theta + theta_offset), direction*np.sin(theta + theta_offset)]) +\
            b * max_theta * np.array([np.sin(theta + theta_offset), -direction*np.cos(theta + theta_offset)])


class Spiral2:
    """
    An archimedean spiral, where the length can be numerically calculated.

    Options for the output position are:

        * `inline`
            Output on the same height and direction as input.

        * `inline_rel`
            Output on the same height and direction as input, but the considered length is only the difference of the spiral compared to a straight path.
            This is useful when building MZIs, where the other path is parallel to the spiral.

        * `opposite`
            Output at opposite direction as input

        * `single_inside`
            The spiral will only do a single turn and stop in the inside

        * `single_outside`
            The spiral will only do a single turn, but start in the inside and stop at the outside

        * <phi>, where phi is the angle where the output should be located
    """

    def __init__(self, origin, angle, width, gap, min_bend_radius, theta, output_type='opposite', offset=0, winding_direction='right', sample_distance=0.50, sample_points=100):
        """
        Create an archimedean spiral following the spiral equation :math:`r = a + b \theta`.
        
        :param origin:
        :param angle:
        :param width:
        :param gap: Gap between the waveguide. Since this is an archimedean spiral, the gap is constant across the whole spiral.
        :param min_bend_radius: The minimum bend radius. This will set the bend of the two semi-circles in the center.
                                It follows that `a = 2 * min_bend_radius`, where `a` as defined in the spiral equation above.
        :param theta: The total angle to turn
        """
        self._origin_port = Port(origin, angle, width)
        self.gap = gap
        self.min_bend_radius = min_bend_radius
        self.total_theta = theta
        self._wg = None
        self.sample_points = sample_points
        self.sample_distance = sample_distance
        self.output_type = output_type
        self.winding_direction = -1 if winding_direction == "left" else 1
        self.offset = offset

        if self.output_type == "inline" or self.output_type == "inline_rel":
            self.out_theta = self.total_theta
        elif self.output_type == "opposite":
            self.out_theta = self.total_theta
        elif self.output_type == "single_inside" or self.output_type == "single_outside":
            self.out_theta = self.total_theta
        else:
            self.out_theta = self.total_theta + self.output_type

    @classmethod
    def make_at_port(cls, port, **kwargs):
        default_port_param = dict(port.get_parameters())
        default_port_param.update(kwargs)
        del default_port_param['origin']
        del default_port_param['angle']
        del default_port_param['width']

        return cls(port.origin, port.angle, port.width, **default_port_param)

    @classmethod
    def make_at_port_with_length(cls, port, gap, min_bend_radius, target_length, output_type='opposite', offset=0, **kwargs):
        if output_type == "inline":
            length_fn = [_spiral_length_inline]
        elif output_type == "inline_rel":
            length_fn = [_spiral_length_inline_rel]
        elif output_type == "opposite":
            length_fn = [_spiral_length_angle, 0]
        elif output_type == "single_inside" or output_type == "single_outside":
            length_fn = [_arc_length_integral]
        else:
            length_fn = [_spiral_length_angle, output_type]

        theta = float(_spiral_theta(target_length, port.width, gap, min_bend_radius, offset, *length_fn))
        return cls.make_at_port(port, gap=gap, min_bend_radius=min_bend_radius, theta=theta, output_type=output_type, offset=offset, **kwargs)

    @property
    def width(self):
        return self._origin_port.width

    @property
    def wg(self):
        if not self._wg:
            self._generate()
        return self._wg

    @property
    def length(self):
        return self.wg.length

    @property
    def out_port(self):
        return self.wg.current_port

    def _generate(self):
        self._wg = Waveguide.make_at_port(self._origin_port)
        a = 2*self.min_bend_radius
        a_in, a_out = a - self.winding_direction * self.offset, a + self.winding_direction * self.offset
        b = 2*(np.sum(self.width) + self.gap) / (2.*np.pi)
        
        # Rotate the spiral such that the input facet of the spiral has an [1,0] normal vector
        in_args = dict(a=a_in, b=b, max_theta=self.total_theta, theta_offset=0, direction=self.winding_direction)
        d_in_args = dict(a=a, b=b, max_theta=self.total_theta, theta_offset=0, direction=self.winding_direction)
        d_in_0 = _d_spiral_out_path(1, **d_in_args)
        rot_in = np.arctan2(d_in_0[1], d_in_0[0])
        in_args['theta_offset'] -= rot_in
        d_in_args['theta_offset'] -= rot_in
        in_offset = -_spiral_out_path(1, **in_args)

        # ...same for the output spiral
        out_args = dict(a=a_out, b=b, max_theta=self.out_theta, theta_offset=0, direction=self.winding_direction)
        dout_args = dict(a=a, b=b, max_theta=self.out_theta, theta_offset=0, direction=self.winding_direction)
        d_out_0 = _d_spiral_out_path(0, **dout_args)
        rot_out = np.arctan2(d_out_0[1], d_out_0[0])
        out_args['theta_offset'] -= rot_out
        dout_args['theta_offset'] -= rot_out
        out_offset = _spiral_out_path(0, **out_args)

        # Generate the spiral
        if self.output_type != "single_outside":
            self._wg.add_parameterized_path(lambda x: -_spiral_out_path(1-x, **in_args) - in_offset[:, None], sample_distance=self.sample_distance, sample_points=self.sample_points,
                                            path_derivative=lambda x: _d_spiral_out_path(1-x, **d_in_args),
                                            path_function_supports_numpy=True)

        if self.output_type != "single_inside" and self.output_type != "single_outside":
            r = self.min_bend_radius - self.winding_direction*self.offset
            circ_angle, missing_height, _ = _circle_segment_params(a, b)
            self._wg.add_bend(-self.winding_direction*circ_angle, r)
            self._wg.add_straight_segment(missing_height)
            self._wg.add_bend(-self.winding_direction*circ_angle, r)

            r = self.min_bend_radius + self.winding_direction*self.offset
            circ_angle, missing_height, _ = _circle_segment_params(a, b)
            self._wg.add_bend(self.winding_direction*circ_angle, r)
            self._wg.add_straight_segment(missing_height)
            self._wg.add_bend(self.winding_direction*circ_angle, r)

        if self.output_type != "single_inside":
            self._wg.add_parameterized_path(lambda x: _spiral_out_path(x, **out_args) - out_offset[:, None], sample_distance=self.sample_distance, sample_points=self.sample_points,
                                            path_derivative=lambda x: _d_spiral_out_path(x, **dout_args),
                                            path_function_supports_numpy=True)

        if self.output_type == "inline" or self.output_type == "inline_rel":
            outer_r = (a + b*self.total_theta)
            self._wg.add_straight_segment(a + b*(self.out_theta+0.5*np.pi) - self.min_bend_radius)
            self._wg.add_bend(0.5*self.winding_direction*np.pi, self.min_bend_radius)
            self._wg.add_straight_segment((2*outer_r - 2 * self.min_bend_radius))
            self._wg.add_bend(-0.5*self.winding_direction*np.pi, self.min_bend_radius)

    def get_shapely_object(self):
        return self.wg.get_shapely_object()


if __name__ == '__main__':
    from gdshelpers.geometry.chip import Cell
    from gdshelpers.parts.text import Text
    cell = Cell('Spiral')

    def demo_spiral(origin, output_type, target_length, gap, port_y_offset=0, width=1):
        wg = Waveguide(origin + np.array([0, port_y_offset]), 0, width)
        wg.add_straight_segment(30)
        spiral = Spiral2.make_at_port_with_length(wg.current_port, gap=gap, min_bend_radius=35., target_length=target_length, output_type=output_type, sample_distance=1)
        text = Text(np.array([150, -130]) + origin, 20, "output: {}\n\nlength: {} um\nreal_length: {:.4f}um".format(output_type, target_length, spiral.length))
        spiral.wg.add_straight_segment(30)
        cell.add_to_layer(1, wg, spiral)
        cell.add_to_layer(2, text)

    # Create normal demo spirals
    
    for i,output_type in enumerate(['opposite', 'inline', 'inline_rel', -0.5*np.pi, 0.25*np.pi, np.pi]):
        demo_spiral(((i//4)*700, (i%4)*250), output_type, 5000, gap=3., width=1)

    # Create spirals with single turn
    demo_spiral((1*700, 2*250), 'single_inside', 2000, gap=1.5)
    demo_spiral((1*700, 3*250), 'single_outside', 2000, gap=1.5, port_y_offset=-150)
    

    """wg = Waveguide(np.array([0, 0]), 0, 1.3)
    wg.add_straight_segment(30)
    spiral = Spiral2.make_at_port_with_length(wg.current_port, gap=80., min_bend_radius=35., target_length=20000, output_type='opposite', sample_distance=10)
    #spiral.wg.add_straight_segment(30)
    cell.add_to_layer(1, wg, spiral)"""

    demo_spiral((2000, 0), 'inline', 11000, gap=10., width=1)
    demo_spiral((2000, 600), 'inline', 11000, gap=18., width=1)
    demo_spiral((2000, 1200), 'inline', 11000, gap=20., width=1)
    demo_spiral((2000, 3*800), 'inline', 11000, gap=21., width=[1,5,1,5,1])
    demo_spiral((2000, 4*800), 'inline', 11000, gap=54., width=1)

    cell.show()
    cell.save("spiral_test")

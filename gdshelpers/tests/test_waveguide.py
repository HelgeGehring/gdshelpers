import unittest
import math

from gdshelpers.parts.waveguide import Waveguide
from gdshelpers.parts.port import Port


class WaveguideTestCase(unittest.TestCase):
    def test_waveguide_construction(self):
        wg = Waveguide([0, 0], 0, 1)
        self.assertAlmostEqual(wg.length, 0)

        # Add straight waveguide
        wg.add_straight_segment(10)
        self.assertAlmostEqual(wg.x, 10)
        self.assertAlmostEqual(wg.y, 0)
        self.assertAlmostEqual(wg.angle, 0)
        self.assertAlmostEqual(wg.length, 10)

        # Add upwards 90 degree bend
        wg.add_bend(math.pi / 2, 5)
        self.assertAlmostEqual(wg.current_port.origin[0], 15)
        self.assertAlmostEqual(wg.current_port.origin[1], 5)
        self.assertAlmostEqual(wg.current_port.angle, math.pi / 2)
        self.assertAlmostEqual(wg.length_last_segment, math.pi / 2 * 5, delta=10e-5)

        # Add another arc, so that we are finally pointing 180 degree backwards
        wg.add_arc(math.pi, 5)
        self.assertAlmostEqual(wg.current_port.origin[0], 10)
        self.assertAlmostEqual(wg.current_port.origin[1], 10)
        self.assertAlmostEqual(abs(wg.current_port.angle), math.pi)

    def test_waveguide_multiple_widths(self):
        widths = [1, 2, 1]

        wg = Waveguide([0, 0], 0, widths)
        wg.add_straight_segment(100)
        wg.add_parameterized_path(lambda t: [10 * t, t])
        wg.get_shapely_object()

    def test_waveguide_width_array(self):
        from shapely.geometry import Polygon

        wg = Waveguide.make_at_port(Port([0, 0], 0, 1))
        # passing a list of widths to add_parameterized_path should be
        # interpreded as sample points, not as a slot waveguide
        wg.add_parameterized_path(path=[[0, 0], [2, 0], [4, 0], [7, 0]],
                                  width=[1, 1, 2, 3],
                                  sample_distance=None)

        test_poly = Polygon([(0.0, 0.5), (2.0, 0.5), (4.0, 1.0),
                             (7.0, 1.5), (7.0, -1.5), (4.0, -1.0),
                             (2.0, -0.5), (0.0, -0.5), (0.0, 0.5)])
        diff = test_poly - wg.get_shapely_object()
        self.assertAlmostEqual(0, diff.area)

    def test_waveguide_add_route_straight_to_port(self):
        import numpy as np
        start_port = Port([0, 0], 0.5*np.pi, 1)

        test_data = [
            (Port([10, 10], 0.5*np.pi, 3), (10, 12)),
            (Port([10, 10], 0, 3), (12, 10)),
            (Port([10, 10], 0.25*np.pi, 3), (10+np.sqrt(2), 10+np.sqrt(2)))
        ]

        waveguides = []
        for end_port, target_pos in test_data:
            wg = Waveguide.make_at_port(start_port)
            wg.add_straight_segment(2)
            wg.add_route_straight_to_port(end_port.inverted_direction)
            wg.add_straight_segment(2)

            waveguides.append(wg)

            self.assertAlmostEqual(wg.current_port.angle, end_port.angle)
            self.assertAlmostEqual(wg.current_port.width, end_port.width)
            self.assertAlmostEqual(wg.current_port.origin[0], target_pos[0])
            self.assertAlmostEqual(wg.current_port.origin[1], target_pos[1])

        # Enable to generate output
        """from gdshelpers.geometry.chip import Cell
        cell = Cell("test")
        for i, wg in enumerate(waveguides):
            cell.add_to_layer(1+i, wg)
        cell.save("wgtest.gds")"""

    def test_route_to_port_functions(self):
        """
        Test consistency of route functions of the Waveguide class.
        Verify that the port to be routed to points in the direction
        of the waveguide to route from.
        """
        import numpy as np

        xmax = 200

        start_port = Port([0, 0], 0.5*np.pi, 1)
        target_port = Port([xmax, 200], 0, 1)

        wg1 = Waveguide.make_at_port(start_port)
        wg1.add_route_single_circle_to_port(target_port.inverted_direction)

        wg2 = Waveguide.make_at_port(start_port)
        wg2.add_bezier_to_port(target_port.inverted_direction, bend_strength=50)

        wg3 = Waveguide.make_at_port(start_port)
        wg3.add_route_straight_to_port(target_port.inverted_direction)

        # Check that they are all within the bounding box (to prevent routing from the wrong side)
        # (This would fail, for example, for add_bezier_to_port if routed to target_port instead of
        # target_port.inverted_direction, which both works)
        for wg in [wg1, wg2, wg3]:
            bounds = wg.get_shapely_object().bounds
            print(bounds)
            self.assertLessEqual(bounds[2], xmax)

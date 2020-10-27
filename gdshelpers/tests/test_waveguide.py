import unittest
import math

from gdshelpers.parts.waveguide import Waveguide


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
        
        some_path = lambda t: [10 * t, t]
        # some_path_d = lambda t: [10, 10]
        
        wg = Waveguide([0, 0], 0, widths)
        wg.add_straight_segment(100)
        wg.add_parameterized_path(some_path)
        wg.get_shapely_object()

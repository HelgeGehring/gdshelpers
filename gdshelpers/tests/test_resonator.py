import unittest
from gdshelpers.parts.resonator import RingResonator


class RingResonatorTestCase(unittest.TestCase):
    def test_asymmetric_gap(self):
        radius = 50.
        wg_width = 1.
        gaps = (0.1, 0.5)

        splitter = RingResonator([0, 0], 0, wg_width, gaps, radius)
        self.assertAlmostEqual(splitter.port.origin[1], 0)
        self.assertAlmostEqual(splitter.opposite_side_port_out.origin[1],
                               2. * wg_width + gaps[0] + gaps[1] + 2. * radius)

    def test_symmetric_gap(self):
        radius = 50.
        wg_width = 1.
        gap = 0.5

        splitter = RingResonator([0, 0], 0, wg_width, gap, radius)
        self.assertAlmostEqual(splitter.port.origin[1], 0)
        self.assertAlmostEqual(splitter.opposite_side_port_out.origin[1], 2. * wg_width + 2. * gap + 2. * radius)

    def test_asymmetric_gap_inconsistent_values(self):
        self.assertRaises(ValueError, RingResonator, [0, 0], 0, 1., (0.5, -0.5), 50)
        self.assertRaises(ValueError, RingResonator, [0, 0], 0, 1., (-0.5, 0.5), 50)
        self.assertRaises(ValueError, RingResonator, [0, 0], 0, 1., (1, 2, 3), 50)


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(RingResonatorTestCase)

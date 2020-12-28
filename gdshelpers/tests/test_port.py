import unittest
import numpy as np

from gdshelpers.parts.port import Port


class PortTestCase(unittest.TestCase):
    def test_getitem(self):
        origin = (1, 1)
        widths = [2, 1, 2, 1, 2]

        port = Port(origin, 0, widths)

        self.assertAlmostEqual(port[0].origin[1], 1 - 3)
        self.assertAlmostEqual(port[1].origin[1], 1)
        self.assertAlmostEqual(port[2].origin[1], 1 + 3)

        for i, width in enumerate(widths[::2]):
            self.assertAlmostEqual(port[i].width, width)

        self.assertAlmostEqual(port[0:1].origin[1], 1 - 2.5)
        self.assertAlmostEqual(port[0:3].origin[1], 1)
        self.assertAlmostEqual(port[1:3].origin[1], 1 + 1.5)

        for widths in [[2, 1, 2, 1, 2], [2, 1, 2, 1, 2, 1]]:
            port = Port(origin, 0, widths)
            np.testing.assert_almost_equal(port[2].origin, port[-1].origin)
            np.testing.assert_almost_equal(port[1].origin, port[-2].origin)
            np.testing.assert_almost_equal(port[1:3].origin, port[1:-1].origin)
            np.testing.assert_almost_equal(port[1:3].width, port[1:-1].width)
            np.testing.assert_almost_equal(port[2:3].origin, port[-2:-1].origin)
            np.testing.assert_almost_equal(port[2:3].width, port[-2:-1].width)

    def test_with_width(self):
        origin = (1, 1)
        widths = [2, 1, 2, 1, 2]
        widths2 = [1, 2, 3]

        port1 = Port(origin, 0, widths)
        port2 = port1.with_width(widths2)
        np.testing.assert_almost_equal(port1.origin, port2.origin)
        np.testing.assert_almost_equal(port1.angle, port2.angle)
        np.testing.assert_almost_equal(port1.width, widths)
        np.testing.assert_almost_equal(port2.width, widths2)

import unittest
import numpy as np

from gdshelpers.parts.waveguide import Waveguide
from gdshelpers.helpers.positive_resist import convert_to_positive_resist


class PositiveResistTestCase(unittest.TestCase):
    def test_positive_resist(self):
        distance = 1e-3

        waveguide = Waveguide([0, 0], 0, 1)
        for i_bend in range(9):
            waveguide.add_bend(angle=np.pi, radius=60 + i_bend * 40)

        waveguide_positive = convert_to_positive_resist(waveguide, 1)

        self.assertFalse(waveguide.get_shapely_object().buffer(-distance).intersects(waveguide_positive))
        self.assertTrue(waveguide.get_shapely_object().buffer(distance).intersects(waveguide_positive))
        self.assertTrue(waveguide_positive.convex_hull.contains(waveguide.get_shapely_object()))

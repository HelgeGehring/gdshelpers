import unittest
import numpy as np

from gdshelpers.parts.spiral import ArchSpiral
from gdshelpers.parts.waveguide import Waveguide


class ArchSpiralTestCase(unittest.TestCase):
    def test_inline(self):
        start_origin = [0, 0]

        wg = Waveguide(np.array(start_origin), 0, 1.3)
        wg.add_straight_segment(30)
        spiral = ArchSpiral.make_at_port_with_length(wg.current_port, gap=80., min_bend_radius=35., target_length=20000, output_type='inline', sample_distance=50)
        spiral.wg.add_straight_segment(30)
        
        self.assertAlmostEqual(spiral.out_port.origin[1], start_origin[1])


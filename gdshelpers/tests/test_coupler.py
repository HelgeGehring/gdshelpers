import unittest

from gdshelpers.parts.coupler import GratingCoupler
from gdshelpers.geometry.chip import Cell
import numpy as np


class GratingCouplerTestCase(unittest.TestCase):
    def test_coupler_apodized_period(self):
        coupler1 = GratingCoupler.make_traditional_coupler(
            origin=[0, 0],
            width=1,
            full_opening_angle=np.deg2rad(40),
            grating_period=3,
            grating_ff=0.5,
            n_gratings=22,
            ap_max_ff=0.25,
            n_ap_gratings=10,
            taper_length=22,
            angle=-0.5 * np.pi,
            ap_start_period=1.,
        )

        coupler2 = GratingCoupler.make_traditional_coupler(
            origin=[100, 0],
            width=1,
            full_opening_angle=np.deg2rad(40),
            grating_period=3,
            grating_ff=0.5,
            n_gratings=22,
            ap_max_ff=0.25,
            n_ap_gratings=10,
            taper_length=22,
            angle=-0.5 * np.pi,
            ap_start_period=3.,
        )

        coupler3 = GratingCoupler.make_traditional_coupler(
            origin=[200, 0],
            width=1,
            full_opening_angle=np.deg2rad(40),
            grating_period=3,
            grating_ff=0.5,
            n_gratings=22,
            ap_max_ff=0.25,
            n_ap_gratings=10,
            taper_length=22,
            angle=-0.5 * np.pi,
            ap_start_period=None,
        )

        self.assertAlmostEqual(coupler2.maximal_radius, coupler3.maximal_radius)

        layout = Cell('LIBRARY')
        cell = Cell('TOP')
        cell.add_to_layer(1, coupler1)
        cell.add_to_layer(1, coupler2)
        cell.add_to_layer(1, coupler3)
        layout.add_cell(cell)

        # cell.save('test_coupler')

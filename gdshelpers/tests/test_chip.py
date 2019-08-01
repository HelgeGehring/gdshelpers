import unittest
from gdshelpers.geometry.chip import Cell
from gdshelpers.parts.waveguide import Waveguide
from shapely.geometry import box
from shapely.geometry.point import Point
from shapely.geometry.linestring import LineString
import numpy as np


class DeviceTestCase(unittest.TestCase):
    def test_cell_bounds(self):
        cell = Cell('test_cell')

        wg1 = Waveguide([0, 0], 0, 1)
        wg1.add_straight_segment(10)
        cell.add_to_layer(1, wg1)

        wg2 = Waveguide([40, 0], 0, 1)
        wg2.add_straight_segment(10)
        cell.add_to_layer(2, wg2)

        cell.add_region_layer(100, [1])
        cell.add_region_layer(101, [1, 2])

        self.assertTrue(100 in cell.layer_dict)
        self.assertEqual(cell.bounds, (0.0, -0.5, 50.0, 0.5))

        subcell = Cell('subcell')
        subcell.add_to_layer(3, box(0, 0, 60, 70))

        self.assertEqual(subcell.bounds, (0.0, 0, 60.0, 70))

        # add subcell
        cell.add_cell(subcell, origin=(0, 0))
        self.assertEqual(cell.bounds, (0.0, -0.5, 60.0, 70.))

        subcell2 = Cell('subcell2')
        subcell2.add_to_layer(3, box(0, 0, 60, 70))

        # add subcell at different origin
        cell.add_cell(subcell2, origin=(20, 0))
        self.assertEqual(cell.bounds, (0.0, -0.5, 80.0, 70.))

        # add object to subcell after adding the subcell to cell
        subcell2.add_to_layer(4, box(60, 0, 70, 10))
        self.assertEqual(subcell2.bounds, (0.0, 0, 70.0, 70))
        self.assertEqual(cell.bounds, (0.0, -0.5, 90.0, 70.))

        # check total region layer
        cell.add_region_layer(102)
        self.assertTrue(102 in cell.layer_dict)
        self.assertEqual(cell.get_bounds(layers=[102]), cell.bounds)

        # cell.save('test_cell_bounds')

    def test_empty_cell(self):
        # An empty cell should have 'None' as bounding box
        cell = Cell('test_cell')
        # self.assertEqual(cell.bounds, None)
        cell.add_to_layer(4, box(60, 0, 70, 10))
        self.assertEqual(cell.bounds, (60, 0, 70, 10))

        subcell = Cell('subcell')
        cell.add_cell(subcell, origin=(0, 0))
        # bounding box of cell should still be the the original bbox
        self.assertEqual(cell.bounds, (60, 0, 70, 10))

    def test_point(self):
        # An Point should give a valid bounding box
        cell = Cell('test_point')
        cell.add_to_layer(4, Point(10, 20))
        self.assertEqual(cell.bounds, (10, 20, 10, 20))

    def test_collection(self):
        # An empty collection should lead to 'None' as bounding box
        cell = Cell('test_collection')
        cell.add_to_layer(4, LineString())
        self.assertEqual(cell.bounds, None)

    def test_bounds_rotation(self):
        import numpy.testing as np_testing

        cell1 = Cell('test_cell')
        cell1.add_to_layer(1, box(10, 10, 30, 20))
        np_testing.assert_almost_equal(cell1.bounds, (10, 10, 30, 20))

        cell2 = Cell('root_cell')
        cell2.add_cell(cell1, angle=0.5 * np.pi)
        np_testing.assert_almost_equal(cell2.bounds, (-20, 10, -10, 30))

        cell3 = Cell('root_cell')
        cell3.add_cell(cell1, angle=1.5 * np.pi)
        np_testing.assert_almost_equal(cell3.bounds, (10, -30, 20, -10))

        cell4 = Cell('root_cell')
        cell4.add_cell(cell1, angle=1 * np.pi)
        np_testing.assert_almost_equal(cell4.bounds, (-30, -20, -10, -10))

        # For manually testing the bounds rotation, uncomment the following code and look at the resulting GDS
        """
        cell5 = Cell('root_cell')
        cell5.add_cell(cell1, angle=0.5*np.pi)
        cell5.add_region_layer()
        cell5.save('test_bounds_rotation')
        """

    def test_region_layers(self):
        cell = Cell("test_device")

        wg1 = Waveguide([0, 0], 0, 1)
        wg1.add_straight_segment(10)
        wg1_shapely = wg1.get_shapely_object()
        cell.add_to_layer(1, wg1)

        wg2 = Waveguide([40, 0], 0, 1)
        wg2.add_straight_segment(10)
        wg2_shapely = wg2.get_shapely_object()
        cell.add_to_layer(2, wg2)

        cell.add_region_layer(100)
        cell.add_region_layer(101, [1])
        cell.add_region_layer(102, [1, 2])

        self.assertTrue(100 in cell.layer_dict)
        self.assertTrue(cell.layer_dict[100][0].contains(wg1_shapely))
        self.assertTrue(cell.layer_dict[100][0].contains(wg2_shapely))

        self.assertTrue(101 in cell.layer_dict)
        self.assertTrue(cell.layer_dict[101][0].contains(wg1_shapely))
        self.assertFalse(cell.layer_dict[101][0].contains(wg2_shapely))

        self.assertTrue(102 in cell.layer_dict)
        self.assertTrue(cell.layer_dict[102][0].contains(wg1_shapely))
        self.assertTrue(cell.layer_dict[102][0].contains(wg2_shapely))

    def test_frame(self):
        # Add frame 
        cell = Cell('test_frame')
        cell.add_to_layer(4, box(0, 0, 10, 10))
        cell.add_frame(padding=10, line_width=1., frame_layer=5)
        self.assertEqual(cell.bounds, (-11, -11, 21, 21))
        self.assertEqual(cell.get_bounds(layers=[4]), (0, 0, 10, 10))
        self.assertEqual(cell.get_bounds(layers=[5]), (-11, -11, 21, 21))

        cell.add_frame(padding=10, line_width=1., frame_layer=99, bbox=(0, 0, 2, 3))
        self.assertEqual(cell.get_bounds(layers=[99]), (-11, -11, 13, 14))


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(DeviceTestCase)

import filecmp
import unittest

import numpy as np
from shapely.affinity import translate, rotate

from gdshelpers.parts.waveguide import Waveguide
from gdshelpers.geometry.chip import Cell
from gdshelpers.parts.coupler import GratingCoupler
from gdshelpers.parts.port import Port
from gdshelpers.parts.pattern_import import GDSIIImport


def make_test_cell(args):
    # Helper function for the test case 'test_parallel'.
    # Needs to be global so that it can be pickled for parallel execution
    i, gc_cell, port = args
    cell = Cell('complex_cell_{}'.format(i))
    cell.add_to_layer(1, Waveguide.make_at_port(port).add_straight_segment(10))
    cell.add_cell(gc_cell, [0, 0])
    return i, cell


class GdsTestCase(unittest.TestCase):
    def test_export_import(self):
        waveguide = Waveguide([0, 0], 0, 1)
        for i_bend in range(9):
            waveguide.add_bend(angle=np.pi, radius=60 + i_bend * 40)
        offset = (10, 10)
        angle = np.pi

        cell = Cell('test')
        cell.add_to_layer(1, waveguide)

        sub_cell = Cell('sub_cell')
        sub_cell.add_to_layer(2, waveguide)
        cell.add_cell(sub_cell, origin=(0, 0), angle=0)

        sub_cell2 = Cell('sub_cell2')
        sub_cell2.add_to_layer(3, waveguide)
        cell.add_cell(sub_cell2, origin=offset, angle=angle)

        cell.save(grid_steps_per_micron=10000)

        def assert_almost_equal_shapely(a, b, tolerance=2e-4):
            self.assertTrue(a.buffer(tolerance).contains(b))
            self.assertTrue(b.buffer(tolerance).contains(a))

        assert_almost_equal_shapely(
            waveguide.get_shapely_object(), GDSIIImport('test.gds', 'test', 1).get_shapely_object())

        assert_almost_equal_shapely(
            waveguide.get_shapely_object(), GDSIIImport('test.gds', 'test', 2).get_shapely_object())

        assert_almost_equal_shapely(
            translate(rotate(waveguide.get_shapely_object(), angle, use_radians=True, origin=(0, 0)),
                      *offset), GDSIIImport('test.gds', 'test', 3).get_shapely_object())

        self.assertTrue(GDSIIImport('test.gds', 'test', 1, 2).get_shapely_object().is_empty)

    def test_parallel_export(self):
        waveguide = Waveguide([0, 0], 0, 1)
        for i_bend in range(9):
            waveguide.add_bend(angle=np.pi, radius=60 + i_bend * 40)

        cells = [Cell('main')]
        for i in range(10):
            cell = Cell('sub_cell_' + str(i))
            cell.add_to_layer(waveguide)
            cells[-1].add_cell(cell, (10, 10))

        cells[0].save('serial.gds', parallel=False)
        cells[0].save('parallel.gds', parallel=True)

        self.assertTrue(filecmp.cmp('serial.gds', 'parallel.gds'))

    def test_parallel_cell_reuse(self):
        """
        This test case tests if it is possible to generate Cells in parallel when they
        reuse a common sub cell.
        This can be useful when creating a cell is an expensive operation and should
        be parallelized, but some components (such as grating couplers) can be reused.
        """
        from concurrent.futures import ProcessPoolExecutor
        port = Port([0, 0], 0, 1.)

        # Create a common cell for grating couplers, which is reused
        gc_cell = Cell("gc")
        gc = GratingCoupler.make_traditional_coupler_at_port(port.inverted_direction,
                                                             full_opening_angle=np.deg2rad(40),
                                                             grating_period=1.13,
                                                             grating_ff=0.85,
                                                             n_gratings=20)
        gc_cell.add_to_layer(1, gc)

        top_cell = Cell("top")
        with ProcessPoolExecutor(max_workers=4) as executor:
            for i, cell in executor.map(make_test_cell, [(i, gc_cell, port) for i in range(8)]):
                top_cell.add_cell(cell, origin=[i*100, 0])

        top_cell.save("test_parallel.gds")

        # However, adding two different cells with the same name should still be prohibited
        top_cell.add_cell(Cell("foo"))
        top_cell.add_cell(Cell("foo"))

        with self.assertRaises(AssertionError):
            top_cell.save("test_parallel.gds")

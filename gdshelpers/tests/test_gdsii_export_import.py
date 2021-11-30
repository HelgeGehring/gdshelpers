import filecmp
import unittest

import numpy as np
from shapely.affinity import translate, rotate

from gdshelpers.parts.waveguide import Waveguide
from gdshelpers.geometry.chip import Cell
from gdshelpers.parts.pattern_import import GDSIIImport


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

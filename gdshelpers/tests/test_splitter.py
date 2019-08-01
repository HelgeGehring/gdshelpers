import unittest
from gdshelpers.parts.splitter import Splitter


class SplitterTestCase(unittest.TestCase):
    def test_splitter_same_wg_width(self):
        total_length = 10
        wg_width = 1
        sep = 5

        splitter = Splitter([0, 0], 0, total_length, wg_width, sep)
        self.assertAlmostEqual(splitter.root_port.width, wg_width)
        self.assertAlmostEqual(splitter.left_branch_port.width, wg_width)
        self.assertAlmostEqual(splitter.left_branch_port.width, wg_width)

        self.assertAlmostEqual(splitter.root_port.origin[0], 0)
        self.assertAlmostEqual(splitter.root_port.origin[1], 0)


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(SplitterTestCase)

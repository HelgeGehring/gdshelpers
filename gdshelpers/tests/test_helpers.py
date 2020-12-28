import unittest
import numpy as np
import numpy.testing as npt

from gdshelpers.helpers import int_to_alphabet, id_to_alphanumeric, find_line_intersection
from gdshelpers.helpers.small import alphanumeric_to_id


class HelpersTestCase(unittest.TestCase):
    def test_int_to_alphabet(self):
        self.assertEqual(int_to_alphabet(0), 'A')
        self.assertEqual(int_to_alphabet(25), 'Z')
        self.assertEqual(int_to_alphabet(26), 'AA')
        self.assertEqual(int_to_alphabet(26 + 25), 'AZ')

    def test_id_to_alphanumeric(self):
        self.assertEqual(id_to_alphanumeric(4, 26 + 25), 'AZ4')

    def test_alphanumeric_to_id(self):
        self.assertEqual((4, 26 + 25), alphanumeric_to_id('AZ4'))

        for pair in [(0, 0), (0, 10), (0, 100), (100, 0), (100, 100)]:
            self.assertEqual(pair, alphanumeric_to_id(id_to_alphanumeric(*pair)))

    def test_find_line_intersection(self):
        test_intersection = find_line_intersection(np.array((2, 0)), np.pi / 2, np.array((0, 1)), 0)
        npt.assert_almost_equal(test_intersection[0], (2, 1))
        npt.assert_almost_equal(test_intersection[1], (1, 2))

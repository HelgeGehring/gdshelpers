import unittest

from gdshelpers.helpers.alignment import Alignment


class AlignmentTestCase(unittest.TestCase):
    def test_calculate_offset(self):
        alignment = Alignment('left-bottom')
        self.assertTupleEqual(tuple(alignment.calculate_offset(((1, 2), (11, 12)))), (-1, -2))
        alignment = Alignment('center-bottom')
        self.assertTupleEqual(tuple(alignment.calculate_offset(((1, 2), (11, 12)))), (-6, -2))
        alignment = Alignment('right-center')
        self.assertTupleEqual(tuple(alignment.calculate_offset(((1, 2), (11, 12)))), (-11, -7))
        alignment = Alignment('right-top')
        self.assertTupleEqual(tuple(alignment.calculate_offset(((1, 2), (11, 12)))), (-11, -12))


if __name__ == '__main__':
    unittest.main()

import unittest
from gdshelpers.helpers import int_to_alphabet, id_to_alphanumeric


class HelpersTestCase(unittest.TestCase):
    def test_int_to_alphabet(self):
        self.assertEqual(int_to_alphabet(0), 'A')
        self.assertEqual(int_to_alphabet(25), 'Z')
        self.assertEqual(int_to_alphabet(26), 'AA')
        self.assertEqual(int_to_alphabet(26 + 25), 'AZ')

    def test_id_to_alphanumeric(self):
        self.assertEqual(id_to_alphanumeric(4, 26 + 25), 'AZ4')


def test_suite():
    return unittest.TestLoader().loadTestsFromTestCase(HelpersTestCase)

from unittest import TestSuite

from . import test_splitter
from . import test_waveguide
from . import test_helpers
from . import test_resonator
from . import test_chip


def test_suite():
    suite = TestSuite()
    suite.addTest(test_splitter.test_suite())
    suite.addTest(test_waveguide.test_suite())
    suite.addTest(test_helpers.test_suite())
    suite.addTest(test_resonator.test_suite())
    suite.addTest(test_chip.test_suite())

    return suite

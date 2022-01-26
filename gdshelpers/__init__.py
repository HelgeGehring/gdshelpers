# noinspection PyProtectedMember
from gdshelpers._global_configuration import _Configuration
import sys

if sys.version_info < (3, 6, 0):
    import warnings

    warnings.warn(
        'The installed Python version reached its end-of-life. Please upgrade to a newer Python version for receiving '
        'further gdshelpers updates.', Warning)

configuration = _Configuration()

__version__ = '1.2.1'

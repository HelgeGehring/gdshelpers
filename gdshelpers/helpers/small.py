import string
import numpy as np
import numpy.linalg as linalg


def raith_eline_dosefactor_to_datatype(dose_factor):
    """
    Convert a dose factor to a GDS datatype for Raith E-Beam writer.

    :param dose_factor: The dose factor.
    :type dose_factor: float
    :return: GDS datatype number
    :rtype: int
    """
    assert dose_factor >= 0
    return int(dose_factor * 1000)


def int_to_alphabet(num):
    """
    Convert an integer number to an alphabetic representation.

    Numbers of 0 to 25 are mapped to ``A``-``Z``, higher numbers 'count' like ``AA``, ``AB``, ..., ``AZ``, ``BA``.
    There is no upper limit on the converted number.

    :param num: Number to convert
    :return: Converted string.
    :rtype: str
    """
    assert num >= 0, 'Cannot convert negative numbers'
    numerals = string.ascii_uppercase
    b = len(numerals)
    return (num < b and numerals[num]) or int_to_alphabet((num // b) - 1) + numerals[(num % b)]


def id_to_alphanumeric(column, row):
    """
    Convert a *column*, *row* pair to an alphanumeric representation.

    :param column: Column
    :type column: int
    :param row: Row
    :type row: int
    :return: Alphanumeric representation.
    :rtype: str
    """
    return int_to_alphabet(row) + str(int(column))


def normalize_phase(phase, zero_to_two_pi=False):
    """
    Normalize a phase to be within +/- pi.

    :param phase: Phase to normalize.
    :type phase: float
    :param zero_to_two_pi: True ->  0 to 2*pi, False -> +/- pi
    :type zero_to_two_pi: bool
    :return: Normalized phase within +/- pi or 0 to 2*pi
    :rtype: float
    """

    if not zero_to_two_pi:
        return (phase + np.pi) % (2 * np.pi) - np.pi
    else:
        return (phase + 2 * np.pi) % (2 * np.pi)


def find_line_intersection(r1, angle1, r2, angle2):
    """
    Find intersection between two lines defined by point and direction.

    :param r1: Origin of the first line.
    :param angle1: Angle of the first line.
    :param r2: Origin of the second line.
    :param angle2: Angle of the second line.
    :return: Tuple of point of intersection and distances from the origins.
    :rtype: tuple
    """
    u1 = np.array([np.cos(angle1), np.sin(angle1)])
    u2 = np.array([np.cos(angle2), np.sin(angle2)])

    a = np.array([[u1[0], -u2[0]], [u1[1], -u2[1]]])
    b = r2 - r1

    # noinspection PyTypeChecker
    x = linalg.solve(a, b)
    return r1 + u1 * x[0], x

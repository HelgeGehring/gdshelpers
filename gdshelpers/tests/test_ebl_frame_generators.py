import unittest
from gdshelpers.geometry.ebl_frame_generators import raith_marker_frame


class MarkerFrameTestCase(unittest.TestCase):
    def test_raith_marker_frame(self):
        bounds = (0, 0, 1000, 1000)

        markers = raith_marker_frame(bounds, padding=50, pitch=50, size=10, n=0)
        self.assertEqual(len(markers), 4)

        markers = raith_marker_frame(bounds, padding=50, pitch=30, size=10, n=1)
        self.assertEqual(len(markers), 12)
        markerpositions = set([tuple(m.origin) for m in markers])
        expected_markerpositions = {(-50, -50), (-50, -20), (-20, -50), (1050, 1050), (1050, 1020), (1020, 1050),
                                    (-50, 1050), (-50, 1020), (-20, 1050), (1050, -50), (1050, -20), (1020, -50)}

        self.assertEqual(markerpositions, expected_markerpositions)

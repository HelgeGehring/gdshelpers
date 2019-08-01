# Generate qrcodes
# - Requires the python-qrcode module from https://github.com/lincolnloop/python-qrcode

try:
    # noinspection PyUnresolvedReferences
    import qrcode
    import qrcode.image.base
except ImportError:
    raise ImportError('python-qrcode package needed for QR code generation')

from gdshelpers.helpers.alignment import Alignment
import shapely.geometry
import shapely.ops
import shapely.affinity
import numpy as np


class ShapelyImageFactory(qrcode.image.base.BaseImage):
    """
    Output factory for qrcode, generating Shapely polygons.

    Probably you will not need to use it directly. The :class:`.QRCode` class provides a simple to use part
    based on this image factory.
    """
    kind = "shapely"

    # noinspection PyAttributeOutsideInit
    def new_image(self, origin=(0, 0), scale_factor=1.0e-3, **kwargs):
        img = list()
        self._idr = img
        self._origin = origin
        self._scale_factor = scale_factor
        return img

    @property
    def origin(self):
        return np.asarray(self._origin)

    @property
    def size(self):
        pixels = self.width + 2 * self.border
        return np.ones((2,)) * pixels * self._scale_factor

    def drawrect(self, row, col):
        origin = self._origin

        box_coords = np.array(self.pixel_box(row, col)) * self._scale_factor
        box = shapely.geometry.box(box_coords[0][0] + origin[0],
                                   self.size[1] - box_coords[0][1] + origin[1],
                                   box_coords[1][0] + self._scale_factor + origin[0],
                                   self.size[1] - box_coords[1][1] - self._scale_factor + origin[1])
        self._idr.append(box)

    def get_shapely_object(self):
        return shapely.ops.cascaded_union(self._idr)


class QRCode(object):
    """
    Quick Response (QR) code part.

    This part is a simple wrapper around the qrcode library using the ShapelyImageFactory. If you need more
    flexibility this class might be extended or you can use the shapely output factory ShapelyImageFactory
    and qrcode directly.

    :param origin: Lower left corner of the QR code.
    :param data: Data which is to be encoded into the QR code.
    :param box_size: Size of each box.
    :param version: QR code version.
    :param error_correction: Level of error correction.
    :param border: Size of the surrounding free border.
    """
    # noinspection PyUnresolvedReferences
    from qrcode import ERROR_CORRECT_L, ERROR_CORRECT_H, ERROR_CORRECT_M, ERROR_CORRECT_Q

    def __init__(self, origin, data, box_size, version=None, error_correction=ERROR_CORRECT_M, border=0,
                 alignment='left-bottom'):
        self._qr_code = qrcode.QRCode(image_factory=ShapelyImageFactory, error_correction=error_correction,
                                      border=border, box_size=1, version=version)
        self._qr_code.add_data(data)
        self._alignment = Alignment(alignment)

        self.box_size = box_size
        self.origin = origin

    def get_shapely_object(self):
        self._qr_code.make(fit=True)
        shapely_code = self._qr_code.make_image(origin=self.origin, scale_factor=self.box_size)

        offset = self._alignment.calculate_offset(((0, 0), shapely_code.size))
        return shapely.affinity.translate(shapely_code.get_shapely_object(), *offset)


def _example():
    qr_code = QRCode([0, 0], 'A0.0', 1.0, version=1, error_correction=QRCode.ERROR_CORRECT_M)

    from gdshelpers.geometry.chip import Cell

    device = Cell('test')
    device.add_to_layer(1, qr_code)

    device.show()

    chip = Cell('optical_codes')
    chip.add_cell(device)
    chip.start_viewer()
    chip.save()


if __name__ == '__main__':
    _example()

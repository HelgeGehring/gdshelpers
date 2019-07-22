import imageio
import shapely.geometry
import shapely.ops
import numpy as np


class GdsImage(object):
    """
    An image represented as GDS parts.

    :param origin: Lower left corner of the image.
    :param filename: Filename of the image.
    :param pixel_size: Size of one pixel.
    """

    def __init__(self, origin, filename, pixel_size):
        self.imgdata = imageio.imread(filename, pilmode="1")
        ysize = np.size(self.imgdata, 0)
        self.pixel_size = pixel_size
        self.origin = origin

        self.pixels = list()
        for (y, x), c in np.ndenumerate(self.imgdata):
            if not c:
                box = shapely.geometry.box(x * pixel_size + origin[0],
                                           (ysize - y) * pixel_size + origin[1],
                                           (x + 1) * pixel_size + origin[0],
                                           (ysize - y - 1) * pixel_size + origin[1])
                self.pixels.append(box)

    def get_shapely_object(self):
        return shapely.ops.cascaded_union(self.pixels)


def _example():
    import gdsCAD.core
    from gdshelpers.geometry import convert_to_gdscad

    img = GdsImage([0, 0], "wolfram_monochrome_100.png", 10)

    cell = gdsCAD.core.Cell('TEST_IMAGE')
    cell.add(convert_to_gdscad(img))
    cell.show()
    return cell


if __name__ == '__main__':
    _example()

import numpy as np
import shapely.geometry
import shapely.ops
import shapely.affinity

from gdshelpers.parts import _fonts
from gdshelpers.helpers import normalize_phase
from gdshelpers.helpers.alignment import Alignment


class Text(object):
    def __init__(self, origin, height, text='', alignment='left-bottom', angle=0, font='stencil', line_spacing=1.5,
                 true_bbox_alignment=False):
        self.origin = origin
        self.height = height
        self.text = str(text)
        self._alignment = Alignment(alignment)
        self.angle = normalize_phase(angle)
        self.font = font
        self.line_spacing = height * line_spacing
        self.true_bbox_alignment = true_bbox_alignment
        self._bbox = None

    def _invalidate(self):
        self._bbox = None

    @property
    def origin(self):
        return self._origin

    # noinspection PyAttributeOutsideInit
    @origin.setter
    def origin(self, origin):
        self._invalidate()
        self._origin = np.array(origin)
        assert self._origin.shape == (2,), 'origin not valid'

    @property
    def height(self):
        return self._height

    # noinspection PyAttributeOutsideInit
    @height.setter
    def height(self, height):
        self._invalidate()
        assert height > 0, 'Height must be positive'
        self._height = height

    @property
    def font(self):
        return self._font

    # noinspection PyAttributeOutsideInit
    @font.setter
    def font(self, font):
        self._invalidate()
        assert font in _fonts.FONTS, 'Font is "%s" unknown, must be one of %s' % (font, _fonts.FONTS.keys())
        self._font = font

    @property
    def alignment(self):
        return self._alignment.alignment

    @alignment.setter
    def alignment(self, alignment):
        self._invalidate()
        self._alignment = alignment

    @property
    def bounding_box(self):
        # FIXME: Does not include offset and rotation!
        if self._bbox is None:
            self.get_shapely_object()

        return self._bbox

    def get_shapely_object(self):
        # Let's do the actual rendering

        polygons = list()

        special_handling_chars = '\n'
        font = _fonts.FONTS[self.font]

        # Check the text
        for char in self.text:
            if char in special_handling_chars:
                continue
            assert char in font, 'Character "%s" is not supported by font "%s"' % (char, self.font)

        max_x = 0
        cursor_x, cursor_y = 0, 0
        for i, char in enumerate(self.text):
            if char == '\n':
                cursor_x, cursor_y = 0, cursor_y - self.line_spacing
                continue

            char_font = font[char]
            cursor_x += char_font['width'] / 2 * self.height

            for line in char_font['lines']:
                points = np.array(line).T * self.height + (cursor_x, cursor_y)
                polygons.append(shapely.geometry.Polygon(points))

            # Add kerning
            if i < len(self.text) - 1 and self.text[i + 1] not in special_handling_chars:
                kerning = char_font['kerning'][self.text[i + 1]]
                cursor_x += (char_font['width'] / 2 + kerning) * self.height

            max_x = max(max_x, cursor_x + char_font['width'] / 2 * self.height)

        merged_polygon = shapely.ops.cascaded_union(polygons)

        # Handle the alignment, translation and rotation
        if not self.true_bbox_alignment:
            bbox = np.array([[0, max_x],
                             [cursor_y, self.height]]).T
        else:
            bbox = np.array(merged_polygon.bounds).reshape(2, 2)

        offset = self._alignment.calculate_offset(bbox)
        self._bbox = bbox + offset

        if not np.isclose(normalize_phase(self.angle), 0):
            aligned_text = shapely.affinity.translate(merged_polygon, *offset)
            rotated_text = shapely.affinity.rotate(aligned_text, self.angle, origin=[0, 0], use_radians=True)
            final_text = shapely.affinity.translate(rotated_text, *self.origin)
        else:
            final_text = shapely.affinity.translate(merged_polygon, *(offset + self.origin))

        return final_text


def _example():
    text = Text([100, 100], 10, 'The quick brown fox jumps over the lazy dog\n123\n4567',
                alignment='left-bottom')
    print(text.bounding_box)

    import gdsCAD.core
    from gdshelpers.geometry import convert_to_gdscad

    cell = gdsCAD.core.Cell('FONTS')
    cell.add(convert_to_gdscad(text))
    cell.show()


if __name__ == '__main__':
    _example()

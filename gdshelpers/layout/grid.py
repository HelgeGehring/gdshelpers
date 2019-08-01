import numpy as np
import shapely.geometry
from shapely.affinity import translate

from gdshelpers.geometry.chip import Cell
from gdshelpers.helpers import StandardLayers
from gdshelpers.parts.text import Text
from gdshelpers.helpers.alignment import Alignment


class GridLayout(object):
    """
    A grid layout class.

    This class arranges cells in an ordered matter. It is useful if you want to place several independent devices
    next to each other.

    :param title: Title to be put on the top of the grid layout.
    :type title: str
    :param tight: Pack all devices as close as possible along the x-axis.
    :type tight: bool
    :param region_layer_type: One of ``None``, ``'layout'`` or ``cell``.
    :type region_layer_type: None, str
    :param region_layer_on_labels: Put a region layer around the labels as well when in ``cell`` mode.
    :type region_layer_on_labels: bool
    :param vertical_spacing: Minimum vertical spacing between devices. The true spacing will be bigger in most
                             cases, since it will align to the next write field.
    :type vertical_spacing: float
    :param vertical_alignment: Vertical alignment, typically the write field size.
    :type vertical_alignment: float
    :param horizontal_spacing: Minimum horizontal spacing between devices. The true spacing will be bigger in most
                               cases, since it will align to the next write field.
    :type horizontal_spacing: float
    :param horizontal_alignment: Horizontal alignment, typically the write field size.
    :type horizontal_alignment: float
    :param text_size: Size of the title text.
    :type text_size: float
    :param row_text_size: Size of text placed in the rows.
    :type row_text_size: float
    :param line_width: Width of the frame.
    :type line_width: float
    :param frame_layer: Layer of the frame. If set to zero, the frame will not be drawn.
    :type frame_layer: int
    :param text_layer: Layer of text
    :type text_layer: int
    :param region_layer: Layer of the region layer boxes.
    :type region_layer: int
    """

    def __init__(self, title=None, tight=False, region_layer_type='layout', region_layer_on_labels=False,
                 vertical_spacing=10, vertical_alignment=100, horizontal_spacing=10,
                 horizontal_alignment=100, text_size=40, row_text_size=30, line_width=1,
                 align_title_line=True,
                 frame_layer=StandardLayers.framelayer, text_layer=StandardLayers.patnamelayer,
                 region_layer=StandardLayers.regionlayer):
        self.title = title
        self.tight = tight
        self.vertical_spacing = vertical_spacing
        self.vertical_alignment = vertical_alignment
        self.horizontal_spacing = horizontal_spacing
        self.horizontal_alignment = horizontal_alignment
        self.text_size = text_size
        self.row_text_size = row_text_size
        self.line_width = line_width
        self.align_title_line = align_title_line
        self.frame_layer = frame_layer
        self.text_layer = text_layer
        self.region_layer = region_layer
        self.region_layer_type = region_layer_type
        self.region_layer_on_labels = region_layer_on_labels
        self._rows = list()
        self._current_row = None

    @property
    def region_layer_type(self):
        return self._region_layer_type

    # noinspection PyAttributeOutsideInit,PyShadowingBuiltins
    @region_layer_type.setter
    def region_layer_type(self, type):
        assert type in (None, 'layout', 'cell')
        self._region_layer_type = type

    def begin_new_row(self, row_label=None):
        """
        Begin a new row.

        :param row_label: Label of the row.
        :type row_label: str
        """
        self._finish_row()

        self._current_row = {'row_label': row_label,
                             'items': list()}

        self.add_label_to_row(row_label)

    def add_to_row(self, cell=None, bbox=None, alignment='left-bottom', realign=True, unique_id=None,
                   allow_region_layer=True):
        """
        Add a new cell to the row.

        The dimensions of the cell will either be determined directly or can be given via *bbox*. They determined
        bounding box always assumes a start at (0, 0) to preserve write field alignment.

        If *realign* is activated, the cell will be shifted, so that the it starts in the first write field quadrant.
        So if your cell contains structures as (-70, 10) and the write field size is 100, the cell will be shifted to
        (30, 10).

        The alignment of the cell can also be changed, but note that only 'left-bottom' guarantees write field
        alignment. When the region layers are used, these will force an alignment again, though.

        The position of each added cell inside the grid can be traced when passing a *unique_id* while adding the cell.

        :param cell: Cell to add.
        :type: gdsCAD.core.Cell
        :param bbox: Bounding box. If None, it will be determined based on *cell*.
        :param alignment: Alignment of the cell inside the grid.
        :param realign: Realign the cell, so that it starts in the first positive write field.
        :param unique_id: ID to trace where the cell was placed in the final layout.
        :param allow_region_layer: Allow a region layer around the cell.
        :type allow_region_layer: bool
        """
        assert self._current_row, 'Start a new row first'

        if cell is None:
            self._current_row['items'].append({'cell': None,
                                               'bbox': np.zeros([2, 2]),
                                               'offset': np.zeros(2),
                                               'id': unique_id,
                                               'alignment': Alignment(alignment),
                                               'allow_region_layer': False})
            return

        cell_bbox = np.reshape(cell.bounds, (2, 2)) if bbox is None else bbox

        if realign:
            offset = [self._remove_multiple_y_align(cell_bbox[0][i]) - cell_bbox[0][i] for i in (0, 1)]
            cell_bbox += offset
        else:
            offset = (0, 0)

        if bbox is None:
            cell_bbox[0, :] = 0

        bbox = cell_bbox

        self._current_row['items'].append({'cell': cell,
                                           'bbox': bbox,
                                           'offset': offset,
                                           'id': unique_id,
                                           'alignment': Alignment(alignment),
                                           'allow_region_layer': allow_region_layer})

    def add_label_to_row(self, text, size=None, origin=None, alignment='left-center'):
        """
        Add a label to the current row.

        :param text: Text of the label.
        :type text: str
        :param size: Size of the label. Defaults to *row_text_size*.
        :type size: float
        :param origin: Origin of the text.
        :param alignment: Alignment.
        """
        if text:
            size = size if size else self.row_text_size
            origin = origin if origin is not None else (0, 0)

            lab = Text(origin, size, text, true_bbox_alignment=True)
            elements = lab.get_shapely_object()
        else:
            elements = None
        self.add_to_row(elements, alignment=alignment, realign=False,
                        allow_region_layer=self.region_layer_on_labels)

    def add_column_label_row(self, labels, row_label=None, size=None, alignment='center-top'):
        """
        Start a new row, containing only labels.

        :param labels: List of labels for each column.
        :type labels: tuple, list
        :param row_label: Row label of the new row.
        :type: str, None
        :param size: Size of the text.
        :type size: float
        :param alignment: Alignment of the labels.
        """
        size = size if size else self.row_text_size

        self.begin_new_row(row_label=row_label)

        if isinstance(labels, str):
            labels = (labels,)

        for label in labels:
            self.add_label_to_row(label, size=size, alignment=alignment)

    def _finish_row(self):
        if self._current_row:
            self._rows.append(self._current_row)
            self._current_row = None

    def _remove_multiple_y_align(self, y):
        y %= self.vertical_alignment
        y = y + self.vertical_alignment if y < 0 else y
        return y

    def _remove_multiple_x_align(self, x):
        x %= self.horizontal_alignment
        x = x + self.horizontal_alignment if x < 0 else x
        return x

    def _next_y_align(self, y):
        if np.isclose(y % self.vertical_alignment, 0):
            return y

        if self.vertical_alignment:
            return (y // self.vertical_alignment + 1) * self.vertical_alignment
        else:
            return y

    def _next_x_align(self, x):
        if np.isclose(x % self.horizontal_alignment, 0):
            return x

        if self.horizontal_alignment:
            return (x // self.horizontal_alignment + 1) * self.horizontal_alignment
        else:
            return x

    def generate_layout(self):
        """
        Generate a layout cell.

        :return: Tuple of a cell, containing the layout and a dictionary mapping each unique id to the position inside
                 the cell.
        """
        self._finish_row()

        max_columns = 0
        column_properties = dict()
        row_properties = dict()
        # Find limits
        for row_id, row_dict in enumerate(self._rows):
            row_properties[row_id] = {'max_height': 0}

            for column_id, item in enumerate(row_dict['items']):
                max_columns = max(column_id, max_columns)

                if column_id not in column_properties:
                    column_properties[column_id] = {'max_width': 0}

                column_properties[column_id]['max_width'] = max(column_properties[column_id]['max_width'],
                                                                item['bbox'][1][0])
                row_properties[row_id]['max_height'] = max(row_properties[row_id]['max_height'],
                                                           item['bbox'][1][1])

        layout_cell = Cell('GRID_LAYOUT')
        pos = [0, self.vertical_spacing]
        limits = [0., 0.]
        mapping = dict()
        for row_id, row_dict in enumerate(self._rows):
            pos[0] = self.horizontal_spacing
            pos[1] = self._next_y_align(pos[1])

            max_height = row_properties[row_id]['max_height']
            for column_id, item in enumerate(row_dict['items']):
                max_width = column_properties[column_id]['max_width'] if not self.tight else item['bbox'][1][0]
                free_space_box = np.array(((0, 0), (max_width, max_height))) + pos

                offset = (item['alignment'].calculate_offset(item['bbox'])
                          - item['alignment'].calculate_offset(free_space_box))

                origin = offset + item['offset']

                item_unique_id = item['id']
                if item_unique_id is not None:
                    assert item_unique_id not in mapping, 'Recurring cell id, use unique values!'
                    mapping[item_unique_id] = origin

                if self.region_layer_type == 'cell' and item['allow_region_layer']:
                    # rl_box = shapely.geometry.box(pos[0], pos[1],
                    #                               self._next_x_align(pos[0] + max_width),
                    #                               self._next_y_align(pos[1] + max_height))
                    new_bbox = item['bbox'] + offset
                    delta = new_bbox[1, :] - new_bbox[0, :]
                    delta_x = self._next_x_align(delta[0])
                    delta_y = self._next_y_align(delta[1])

                    rl_box = shapely.geometry.box(new_bbox[0][0], new_bbox[0][1],
                                                  new_bbox[0][0] + delta_x, new_bbox[0][1] + delta_y)
                    layout_cell.add_to_layer(self.region_layer, rl_box)

                if item['cell']:
                    if isinstance(item['cell'], Cell):
                        layout_cell.add_cell(item['cell'], origin=origin)
                    else:
                        layout_cell.add_to_layer(self.text_layer, translate(item['cell'], *origin))

                next_x_pos = pos[0] + max_width + self.horizontal_spacing
                limits[0] = max(next_x_pos, limits[0])
                pos[0] = self._next_x_align(next_x_pos)

            next_y_pos = pos[1] + max_height + self.vertical_spacing
            limits[1] = max(next_y_pos, limits[1])
            pos[1] = next_y_pos

        if self.title:
            # If there is enough space for the title text until next alignment, use it
            tmp_text_obj = Text([0, 0], self.text_size, self.title).get_shapely_object()
            title_vertical_space = (tmp_text_obj.bounds[3] + 0.7 * self.text_size) + self.line_width
            title_horizontal_space = (tmp_text_obj.bounds[2] + self.text_size) + self.line_width
            limits[0] = max(limits[0], title_horizontal_space)

            if self.align_title_line:
                title_vertical_space = self._next_y_align(title_vertical_space) - self.line_width / 2.

            if (self._next_y_align(pos[1]) - limits[1]) >= title_vertical_space:
                limits[1] = pos[1] - title_vertical_space
            else:
                pos[1] = self._next_y_align(limits[1] + title_vertical_space)
                limits[1] = pos[1] - title_vertical_space

            # Paint vertical line
            if self.frame_layer:
                line = shapely.geometry.LineString([(self.line_width, limits[1]),
                                                    (self._next_x_align(limits[0]) - self.line_width, limits[1])])
                line = line.buffer(self.line_width)
                layout_cell.add_to_layer(self.frame_layer, line)

            title = Text([self.horizontal_spacing, (pos[1] + limits[1]) / 2.],
                         self.text_size, self.title, alignment='left-center')
            layout_cell.add_to_layer(self.text_layer, title)
        else:
            pos[1] = self._next_y_align(pos[1] + self.line_width)

        # Draw the frame
        if self.frame_layer:
            frame = shapely.geometry.box(0, 0, self._next_x_align(limits[0]), pos[1])
            frame = frame.difference(frame.buffer(-self.line_width))
            layout_cell.add_to_layer(self.frame_layer, frame)

        if self.region_layer_type == 'layout':
            frame = shapely.geometry.box(0, 0, self._next_x_align(limits[0]), pos[1])
            layout_cell.add_to_layer(self.region_layer, frame)

        return layout_cell, mapping


# noinspection PyPep8
def _example():
    layout = GridLayout('Test layout\nwith very cool features' + 'long! ' * 50, tight=False, region_layer_type=None)

    layout.add_column_label_row(['c0', 'c1'], 'col_labels')

    layout.begin_new_row('row1')

    test_cell_1 = Cell('TC1')
    test_cell_1.add_to_layer(1, shapely.geometry.box(0, 00, 335, 125))

    test_cell_2 = Cell('TC2')
    # test_cell_2.add_to_layer(1, shapely.geometry.box(101, 101, 335, 125))
    test_cell_2.add_to_layer(1, shapely.geometry.box(0, 0, 600, 400))

    layout.add_to_row(test_cell_1, realign=False)  # , alignment='left-bottom')
    layout.add_to_row(test_cell_1, realign=True)  # , alignment='center-center')

    layout.begin_new_row('row2')
    layout.add_to_row(test_cell_2, realign=True)  # , alignment='left-bottom')
    layout.add_to_row(test_cell_2, realign=True)  # , alignment='left-bottom')
    layout.add_to_row(test_cell_2, realign=True)  # , alignment='left-bottom')
    layout.add_to_row(test_cell_2, realign=True)  # , alignment='left-bottom')
    layout.add_to_row(test_cell_2, realign=True)  # , alignment='left-bottom')
    layout.add_to_row(test_cell_2, realign=True)  # , alignment='left-bottom')
    layout.add_to_row(test_cell_2, realign=True)  # , alignment='left-bottom')

    layout.begin_new_row('row3')
    layout.add_to_row(test_cell_2, realign=True)  # , alignment='left-bottom')
    layout.add_to_row(test_cell_2, realign=True)  # , alignment='left-bottom')
    layout.add_to_row(test_cell_2, realign=True)  # , alignment='left-bottom')
    layout.add_to_row(test_cell_2, realign=True)  # , alignment='left-bottom')
    layout.add_to_row(test_cell_2, realign=True)  # , alignment='left-bottom')
    layout.add_to_row(test_cell_2, realign=True)  # , alignment='left-bottom')
    layout.add_to_row(test_cell_2, realign=True)  # , alignment='left-bottom')

    # layout.add_to_row(test_cell_1, realign=True)#, alignment='left-bottom')

    layout_cell, mapping = layout.generate_layout()

    layout_cell.show()
    layout_cell.save()


if __name__ == '__main__':
    _example()

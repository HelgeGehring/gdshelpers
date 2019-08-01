import numpy as np


class Alignment(object):
    """
    Alignment helper class.

    Given a bounding box in the form of ``((min_x, min_y), (max_x, max_y))``, this class
    returns special points of this box::

        (max_y)    top +------+------+
                     |      |      |
                     |      |      |
             center  +------+------+
                     |      |      |
                     |      |      |
        (min_y) bottom +------+------+
                  (min_x)         (max_x)
                    Left  Center   Right

    Alignment options are given as ``-`` separated tuple, allowing for combinations of
    ``left``, ``center``, ``right`` with ``bottom``, ``center``, ``top``.
    """
    _ALIGNMENT = {
        'x': {
            'left': lambda coord: coord[0][0],
            'center': lambda coord: np.mean(coord[:, 0]),
            'right': lambda coord: coord[1][0],
        },
        'y': {
            'bottom': lambda coord: coord[0][1],
            'center': lambda coord: np.mean(coord[:, 1]),
            'top': lambda coord: coord[1][1],
        }
    }

    def __init__(self, alignment='bottom-left'):
        self.alignment = alignment

    @property
    def alignment(self):
        """
        Property holding the current alignment.

        :return: Alignment string, i.e. ``'bottom-left'``.
        :rtype: str
        """
        return self._alignment

    # noinspection PyAttributeOutsideInit
    @alignment.setter
    def alignment(self, alignment):
        assert type(alignment) == str, 'Alignment must be a string'

        options = [option.strip() for option in alignment.split('-')]
        assert len(options) == 2, 'Alignment option string must be two options separated by a dash'
        assert options[0] in self._ALIGNMENT['x'], 'x-axis alignment option must be one of %s' % \
                                                   self._ALIGNMENT['x'].keys()
        assert options[1] in self._ALIGNMENT['y'], 'y-axis alignment option must be one of %s' % \
                                                   self._ALIGNMENT['y'].keys()

        self._alignment = '-'.join(options)

    @property
    def alignment_functions(self):
        """
        Returns a 2-tuple of functions, calculating the offset coordinates for a given bounding box.

        :return: Tuple of functions.
        :rtype: tuple
        """
        options = self.alignment.split('-')
        return self._ALIGNMENT['x'][options[0]], self._ALIGNMENT['y'][options[1]]

    def calculate_offset(self, bbox):
        """
        Calculate the coordinates of the current alignment for the given bounding box *bbox*.
        
        :param bbox: Bounding box in the ``((min_x, min_y), (max_x, max_y))`` format.
        :return: (x, y) offset coordinates.
        :rtype: np.array
        """
        bbox = np.asarray(bbox)
        alignment_fun = self.alignment_functions
        offset = np.array([-alignment_fun[i](bbox) for i in [0, 1]])
        return offset

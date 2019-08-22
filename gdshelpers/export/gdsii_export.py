"""
For documentation of GDSII see: http://www.buchanan1.net/stream_description.html
"""

import math
import datetime
from struct import pack
from io import BytesIO
import numpy as np


def _real_to_8byte(value):
    if value == 0:
        return b'\x00' * 8
    exponent = int((math.log(abs(value), 16) + 1) // 1)
    mantissa = int(abs(value) * 16. ** (14 - exponent))
    return ((((0b1 if value < 0 else 0b0) + exponent + 64) << 56) + mantissa).to_bytes(8, 'big')


def _write_cell(cell, grid_steps_per_unit, max_points, max_line_points, timestamp):
    with BytesIO() as b:
        b.write(pack('>14H', 28, 0x0502, *timestamp.timetuple()[:6] * 2))
        # BGNSTR INTEGER_2 time_modification time_last_access
        name = cell.name + '\0' * (len(cell.name) % 2)
        b.write(pack('>2H', 4 + len(name), 0x0606) + name.encode('ascii'))  # STRNAME STRING cell_name

        for layer, polygons in cell.get_fractured_layer_dict(max_points, max_line_points).items():
            for polygon in polygons:
                if polygon.interiors:
                    raise RuntimeError('GDSII only supports polygons without holes')
                xy = np.round(np.array(polygon.exterior.coords) * grid_steps_per_unit).astype('>i4')
                b.write(pack('>10H', 4, 0x0800,  # BOUNDARY NO_DATA
                             6, 0x0D02, layer,  # LAYER INTEGER_2 layer
                             6, 0x0E02, layer,  # DATATYPE INTEGER_2 datatype
                             4 + 8 * len(xy), 0x1003))  # XY INTEGER_4
                b.write(xy.tobytes())  # coords of polygon
                b.write(pack('>2H', 4, 0x1100))  # ENDEL NO_DATA

        for ref in cell.cells:
            name = ref['cell'].name + '\0' if len(ref['cell'].name) % 2 != 0 else ref['cell'].name
            b.write(pack('>2H', 4, 0x0A00))  # SREF NO_DATA
            b.write(pack('>2H', 4 + len(name), 0x1206) + name.encode('ascii'))  # SNAME STRING ref_cell_name
            if (ref['angle'] is not None) or (ref['magnification'] is not None) or ref['x_reflection']:
                b.write(pack('>3H', 6, 0x1A01, 1 << 15 if ref['x_reflection'] else 0))  # STRANS BIT_ARRAY bit15=1
                if ref['magnification'] is not None:
                    b.write(pack('>2H', 12, 0x1B05) + _real_to_8byte(ref['magnification']))  # MAG REAL_8
                if ref['angle'] is not None:
                    b.write(pack('>2H', 12, 0x1C05) + _real_to_8byte(np.rad2deg(ref['angle'])))  # ANGLE REAL_8
            b.write(pack('>2H', 12, 0x1003) + np.round(np.array(ref['origin']) * grid_steps_per_unit).astype(
                '>i4').tobytes())  # XY INTEGER_8 origin
            b.write(pack('>2H', 4, 0x1100))  # ENDEL NO_DATA

        b.write(pack('>2H', 4, 0x0700))  # ENDEST NO_DATA

        return b.getvalue()


def write_cell_to_gds_file(outfile, cell, unit=1e-6, grid_steps_per_unit=1000, max_points=4000, max_line_points=4000,
                           timestamp=None):
    name = 'gdshelpers_exported_library'
    grid_step_unit = unit / grid_steps_per_unit
    timestamp = datetime.datetime.now() if timestamp is None else timestamp

    cells = []
    cell_names = []

    def add_cells_to_unique_list(start_cell):
        cells.append(start_cell)
        cell_names.append(start_cell.name)
        for c in start_cell.cells:
            if c not in cells:
                if c['cell'].name in cell_names:
                    raise RuntimeError(
                        'Each cell name must be unique, "{}" is used more than once'.format(c['cell'].name))
                add_cells_to_unique_list(c['cell'])

    add_cells_to_unique_list(cell)

    name = name + '\0' * (len(name) % 2)  # Strings always have even length
    outfile.write(pack('>3H', 6, 0x0002, 0x258))  # HEADER INTEGER_2 v6.0
    outfile.write(pack('>14H', 28, 0x0102, *timestamp.timetuple()[:6] * 2))
    # BGNLIB INTEGER_2 time_modification time_last_access
    outfile.write(pack('>2H', 4 + len(name), 0x0206) + name.encode('ascii'))  # LIBNAME STRING libname
    outfile.write(pack('>2H', 20, 0x0305) + _real_to_8byte(grid_step_unit / unit) + _real_to_8byte(grid_step_unit))
    # UNITS REAL_8 1/grid_steps_per_unit grid_step_unit
    for c in cells:
        outfile.write(_write_cell(c, grid_steps_per_unit, max_points, max_line_points, timestamp))
    outfile.write(pack('>2H', 4, 0x0400))  # ENDLIB N0_DATA


if __name__ == '__main__':
    from gdshelpers.parts.port import Port
    from gdshelpers.parts.waveguide import Waveguide
    from gdshelpers.geometry.chip import Cell

    device_cell = Cell('cell')
    start_port = Port(origin=(10, 0), width=1, angle=0)
    waveguide = Waveguide.make_at_port(start_port)
    for i_bend in range(9):
        waveguide.add_bend(angle=np.pi, radius=60 + i_bend * 40)
    device_cell.add_dlw_taper_at_port('A', 2, waveguide.in_port, 30)
    device_cell.add_dlw_taper_at_port('B', 2, waveguide.current_port, 30)
    device_cell.add_to_layer(1, waveguide)

    sub_cell = Cell('sub_cell')
    sub_cell.add_to_layer(1, waveguide)

    device_cell.add_cell(sub_cell, origin=(10, 10), angle=np.pi / 2)

    with open('gdsii_export.gds', 'wb') as file:
        write_cell_to_gds_file(file, device_cell)

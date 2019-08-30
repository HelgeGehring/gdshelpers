from itertools import chain

import numpy as np
import ezdxf


def _add_cell_to_dxf(block, cell, max_points, max_line_points):
    for layer, polygons in cell.get_fractured_layer_dict(max_points, max_line_points).items():
        for polygon in polygons:
            if polygon.interiors:
                raise RuntimeError('DXF only supports polygons without holes')
            block.add_lwpolyline(chain(polygon.exterior.coords, polygon.exterior.coords[0:1]),
                                 dxfattribs={'layer': '{:d}-{:d}'.format(layer, layer)})

    for ref in cell.cells:
        dxfattribs = {}
        if ref['angle'] is not None:
            dxfattribs['rotation'] = np.rad2deg(ref['angle'])
        if ref['magnification'] is not None:
            dxfattribs['xscale'] = dxfattribs['yscale'] = ref['magnification']
        if ref['x_reflection']:
            raise NotImplementedError('X_Reflection for dxf_export is not implemented')
        block.add_blockref(ref['cell'].name, ref['origin'], dxfattribs)


def write_cell_to_dxf_file(outfile, cell, max_points=4000, max_line_points=4000, parallel=False):
    """
    Writes the cell to a dxf-file

    :param outfile: file to write to
    :param cell: cell to export
    :param max_points: maximum number of points for a polygon
    :param max_line_points: maximum number of points for a line
    :param parallel: export if parallelized if true
    :return:
    """
    cells = []
    cell_names = []
    layers_and_datatypes = {}

    dxf = ezdxf.new('R2010')
    msp = dxf.modelspace()
    msp.add_blockref(cell.name, (0, 0))

    def add_cells_to_unique_list(start_cell):
        cells.append(start_cell)
        cell_names.append(start_cell.name)
        for c in start_cell.cells:
            if c not in cells:
                if c['cell'].name in cell_names:
                    raise RuntimeError(
                        'Each cell name must be unique, "{}" is used more than once'.format(c['cell'].name))
                add_cells_to_unique_list(c['cell'])
                for layer in c['cell'].layer_dict.keys():
                    if layer not in layers_and_datatypes:
                        layers_and_datatypes[layer] = {layer}  # second "layer" refers to the datatype
                    elif layer not in layers_and_datatypes[layer]:
                        layers_and_datatypes[layer].add(layer)  # second "layer" refers to the datatype

    add_cells_to_unique_list(cell)

    for layer, datatypes in layers_and_datatypes.items():
        for datatype in datatypes:
            dxf.layers.new(name='{:d}-{:d}'.format(layer, datatype))

    if parallel:
        import warnings
        warnings.warn('Parallel dxf-export is not yet implemented, ignoring parallel flag.')
    for c in cells[::-1]:
        block = dxf.blocks.new(c.name)
        _add_cell_to_dxf(block, c, max_points, max_line_points)
    dxf.write(outfile)


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

    with open('dxf_export.dxf', 'w') as file:
        write_cell_to_dxf_file(file, device_cell, parallel=True)

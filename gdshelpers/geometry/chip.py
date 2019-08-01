import itertools
import json
import numpy as np
from collections import defaultdict
from shapely.affinity import translate, rotate
from shapely.geometry import box

from gdshelpers.geometry.shapely_adapter import convert_to_layout_objs, bounds_union, transform_bounds
from gdshelpers.parts.waveguide import Waveguide
from gdshelpers.parts.marker import DLWMarker
from gdshelpers.parts.text import Text
from gdshelpers.geometry import geometric_union
import gdshelpers.helpers.layers as std_layers

gds_library = None
try:
    import gdspy

    gds_library = 'gdspy'
except ImportError:
    pass  # Error will come when trying to use get_gdspy_cell
try:
    import gdsCAD

    gds_library = 'gdscad'
except ImportError:
    pass  # Error will come when trying to use get_gdscad_cell

try:
    import fatamorgana
    import fatamorgana.records
except ImportError:
    pass


class Cell:
    def __init__(self, name):
        """
        Creates a new Cell named `name` at `origin`

        :param name: Name of the cell, needs to be unique
        """
        self.name = name
        self.cells = []
        self.layer_dict = defaultdict(lambda: [])
        self.dlw_data = {}
        self.desc = {'dlw': self.dlw_data, 'desc': {}, 'ebl': []}
        self.cell_gdspy = None
        self.cell_gdscad = None
        self.cell_oasis = None
        self._bounds = None
        # Only contains the bounds of items in `layer_dict`.
        # Children cells have to be queried each time, since there is no way of knowing when they got changed.
        # self._bounds is None if the bounds need to be recalculated or if the cell is empty (in which case
        # recalculating them is cheap and we don't need to cache them)

    @property
    def bounds(self):
        """
        The outer bounding box of the cell. Returns `None` if it is empty.
        """
        return self.get_bounds(layers=None)

    def get_bounds(self, layers=None):
        """
        Calculates and returns the envelope for the given layers.
        Returns `None` if it is empty.
        """
        # Go through all layers
        bounds = []
        if layers is None and self._bounds is not None:
            bounds += [self._bounds]
        else:
            for layer in layers or self.layer_dict.keys():
                for geo in self.layer_dict.get(layer, []):
                    geo_bounds = geo.get_shapely_object().bounds if hasattr(geo, 'get_shapely_object') else geo.bounds
                    if geo_bounds is not ():  # Some shapely geometries (collections) can return empty bounds
                        bounds.append(geo_bounds)

            # Cache envelope if we have the global envelope
            if layers is None:
                self._bounds = bounds_union(bounds) if len(bounds) > 0 else None

        # Merge envelopes of children cells
        for cell in self.cells:
            cell_bounds = cell['cell'].get_bounds(layers)
            if cell_bounds is not None:
                bounds.append(transform_bounds(cell_bounds, cell['origin'], rotation=cell['angle'] or 0))

        return bounds_union(bounds) if len(bounds) > 0 else None

    @property
    def size(self):
        bounds = self.bounds
        if bounds is None:
            return 0, 0
        else:
            return bounds[2] - bounds[0], bounds[3] - bounds[1]

    def add_to_layer(self, layer, *geometry):
        """
        Adds a shapely geometry to a the layer

        :param layer: id of the layer
        :param geometry: shapely geometry
        """
        self._bounds = None
        self.layer_dict[layer] += geometry

    def add_dlw_data(self, dlw_type, dlw_id, data):
        """
        Adds data for 3D-hybrid-integration to the Cell. This is usually only done by using the Device

        :param dlw_type: type of the represented object
        :param dlw_id: id of the represented object
        :param data: data of the object
        """
        if dlw_type not in self.dlw_data:
            self.dlw_data[dlw_type] = {}
        if dlw_id in self.dlw_data[dlw_type]:
            raise ValueError('ID "{:s}" already used'.format(dlw_id))
        self.dlw_data[dlw_type][dlw_id] = data

    def add_cell(self, cell, origin=(0, 0), angle=None):
        """
        Adds a Cell to this cell

        :param cell: Cell to add
        :param origin: position where to add the cell
        :param angle:
        """
        if cell.name in [cell['cell'].name for cell in self.cells]:
            import warnings
            warnings.warn(
                'Cell name "{cell_name:s}" added multiple times to {self_name:s}.'
                ' Can be problematic for desc/dlw-files'.format(cell_name=cell.name, self_name=self.name))
        self.cells.append(dict(cell=cell, origin=origin, angle=angle))

    def add_region_layer(self, region_layer=std_layers.regionlayer, layers=None):
        """
        Generate a region layer around all objects on `layers` and place it on layer `region_layer`.
        If `layers` is None, all layers are used.
        """
        self.add_to_layer(region_layer, box(*self.get_bounds(layers)))

    def add_frame(self, padding=30., line_width=1., frame_layer=std_layers.framelayer, bbox=None):
        """
        Generates a rectangular frame around the contents of the cell.

        :param padding: Add a padding of the given value around the contents of the cell
        :param line_width: Width of the frame line
        :param frame_layer: Layer to put the frame on.
        :param bbox: Optionally, an explicit extent can be passed to the function. If `None` (default),
                     the current extent of the cell will be chosen.
        """
        padding = padding + line_width
        bbox = bbox or self.bounds

        frame = box(bbox[0] - padding, bbox[1] - padding, bbox[2] + padding, bbox[3] + padding)
        frame = frame.difference(frame.buffer(-line_width))
        self.add_to_layer(frame_layer, frame)

    def add_ebl_marker(self, layer, marker):
        """
        Adds an Marker to the layout

        :param layer: layer on which the marker should be positioned
        :param marker: marker, that should be added (from gdshelpers.parts.markers)
        """
        self.add_to_layer(layer, marker)
        self.desc['ebl'].append(list(marker.origin))

    def add_ebl_frame(self, layer, frame_generator, **kwargs):
        """
        Adds global markers to the layout

        :param layer:  layer on which the markers should be positioned
        :param frame_generator: either a method, which returns a list of the markers, which should be added or the name
            of a generator from the gdshelpers.geometry.ebl_frame_generators package
        :param kwargs: Parameters which are directly passed to the frame generator
        """
        from gdshelpers.geometry import ebl_frame_generators
        frame_generator = frame_generator if callable(frame_generator) else getattr(ebl_frame_generators,
                                                                                    frame_generator)
        for marker in frame_generator(self.bounds, **kwargs):
            self.add_ebl_marker(layer, marker)

    def add_to_desc(self, key, data):
        """
        Adds data to the .desc-file can be used for any data related to the cells, e.g. the swept parameters/...

        :param key: name of the entry
        :param data: data which are added to the .desc-file, the data have to be serializable by json
        """
        self.desc['desc'][key] = data

    def get_dlw_data(self):
        dlw_data = self.dlw_data.copy()
        for sub_cell in self.cells:
            cell, origin = sub_cell['cell'], sub_cell['origin']

            for dlw_type, dlw_type_data in cell.get_dlw_data().items():
                for dlw_id, data in dlw_type_data.items():
                    data = data.copy()
                    data['origin'] = (np.array(origin) + data['origin']).tolist()
                    if dlw_type not in dlw_data:
                        dlw_data[dlw_type] = {}
                    dlw_data[dlw_type][cell.name + '.' + dlw_id] = data

        return dlw_data

    def get_desc(self):
        desc = self.desc.copy()
        desc['cells'] = {cell['cell'].name: dict(offset=tuple(cell['origin']), angle=cell['angle'] or 0,
                                                 **cell['cell'].get_desc()) for cell in self.cells}
        return desc

    def get_gdspy_cell(self, executor=None):
        if self.cell_gdspy is None:
            self.cell_gdspy = gdspy.Cell(self.name)
            for sub_cell in self.cells:
                angle = np.rad2deg(sub_cell['angle']) if sub_cell['angle'] is not None else None
                self.cell_gdspy.add(
                    gdspy.CellReference(sub_cell['cell'].get_gdspy_cell(executor), origin=sub_cell['origin'],
                                        rotation=angle))
            for layer, geometries in self.layer_dict.items():
                for geometry in geometries:
                    if executor:
                        executor.submit(convert_to_layout_objs, geometry, layer, library='gdspy') \
                            .add_done_callback(lambda future: self.cell_gdspy.add(future.result()))
                    else:
                        self.cell_gdspy.add(convert_to_layout_objs(geometry, layer, library='gdspy'))
        return self.cell_gdspy

    def get_gdscad_cell(self, executor=None):
        if self.cell_gdscad is None:
            self.cell_gdscad = gdsCAD.core.Cell(self.name)
            for sub_cell in self.cells:
                angle = np.rad2deg(sub_cell['angle']) if sub_cell['angle'] is not None else None
                self.cell_gdscad.add(
                    gdsCAD.core.CellReference(sub_cell['cell'].get_gdscad_cell(executor), origin=sub_cell['origin'],
                                              rotation=angle))
            for layer, geometries in self.layer_dict.items():
                for geometry in geometries:
                    if executor:
                        executor.submit(convert_to_layout_objs, geometry, layer, library='gdscad') \
                            .add_done_callback(lambda future: self.cell_gdscad.add(future.result()))
                    else:
                        self.cell_gdscad.add(convert_to_layout_objs(geometry, layer, library='gdscad'))
        return self.cell_gdscad

    def get_oasis_cells(self, grid_steps_per_micron=1000, executor=None):
        if self.cell_oasis is None:
            self.cell_oasis = fatamorgana.Cell(fatamorgana.NString(self.name))
            for sub_cell in self.cells:
                x, y = sub_cell['origin']
                x, y = round(x * grid_steps_per_micron), round(y * grid_steps_per_micron)
                angle = np.rad2deg(sub_cell['angle']) if sub_cell['angle'] is not None else None
                self.cell_oasis.placements.append(
                    fatamorgana.records.Placement(False, name=fatamorgana.NString(sub_cell['cell'].name), x=x, y=y,
                                                  angle=angle))
            for layer, geometries in self.layer_dict.items():
                for geometry in geometries:
                    if executor:
                        executor.submit(convert_to_layout_objs, geometry, layer, library='oasis',
                                        grid_steps_per_micron=grid_steps_per_micron, max_points=np.inf,
                                        max_points_line=np.inf) \
                            .add_done_callback(lambda future: self.cell_oasis.geometry.extend(future.result()))
                    else:
                        self.cell_oasis.geometry.extend(
                            convert_to_layout_objs(geometry, layer, library='oasis',
                                                   grid_steps_per_micron=grid_steps_per_micron,
                                                   max_points=np.inf, max_points_line=np.inf))
        return [self.cell_oasis] + [oasis_cell for sub_cell in self.cells for oasis_cell in
                                    sub_cell['cell'].get_oasis_cells(grid_steps_per_micron, executor)]

    def get_gdspy_lib(self):
        self.get_gdspy_cell()
        return gdspy.current_library

    def start_viewer(self):
        gdspy.LayoutViewer(library=self.get_gdspy_lib(), depth=10)

    def save(self, name=None, library=None, grid_steps_per_micron=1000, parallel=False):
        """
        Exports the layout and creates an DLW-file, if DLW-features are used.

        :param name: Optionally, the filename of the saved file (without ending).
        :param library: Name of the used library.
            Currently, for gds-export gdspy and gdscad are supported, for oasis-export fatamorgana is supported.
        :param grid_steps_per_micron: Defines the resolution
        :param parallel: Defines if palatalization is used (only supported in Python 3).
            Standard value will be changed to True in a future version.
            Deactivating can be useful for debugging reasons.
        """

        if not name:
            name = self.name
        elif name.endswith('.gds'):
            name = name[:-4]
            library = library or gds_library
        elif name.endswith('.oasis'):
            name = name[:-6]
            library = library or 'fatamorgana'

        library = library or gds_library

        if library == 'gdspy':
            if parallel:
                from concurrent.futures import ProcessPoolExecutor
                with ProcessPoolExecutor() as pool:
                    self.get_gdspy_cell(pool)
            else:
                self.get_gdspy_cell()

            self.get_gdspy_lib().precision = self.get_gdspy_lib().unit / grid_steps_per_micron
            gdspy_cells = self.get_gdspy_lib().cell_dict.values()
            if parallel:
                from concurrent.futures import ProcessPoolExecutor
                with ProcessPoolExecutor() as pool:
                    binary_cells = pool.map(gdspy.Cell.to_gds, gdspy_cells, [grid_steps_per_micron] * len(gdspy_cells))
            else:
                binary_cells = map(gdspy.Cell.to_gds, gdspy_cells, [grid_steps_per_micron] * len(gdspy_cells))

            self.get_gdspy_lib().write_gds(name + '.gds', cells=[], binary_cells=binary_cells)
        elif library == 'gdscad':
            layout = gdsCAD.core.Layout(precision=1e-6 / grid_steps_per_micron)
            if parallel:
                from concurrent.futures import ProcessPoolExecutor
                with ProcessPoolExecutor() as pool:
                    layout.add(self.get_gdscad_cell(pool))
            else:
                layout.add(self.get_gdscad_cell())
            layout.save(name + '.gds')
        elif library == 'fatamorgana':
            layout = fatamorgana.OasisLayout(grid_steps_per_micron)

            if parallel:
                from concurrent.futures import ProcessPoolExecutor
                with ProcessPoolExecutor() as pool:
                    cells = self.get_oasis_cells(grid_steps_per_micron, pool)
            else:
                cells = self.get_oasis_cells(grid_steps_per_micron)

            layout.cells = [cells[0]] + list(set(cells[1:]))

            # noinspection PyUnresolvedReferences
            def replace_names_by_ids(oasis_layout):
                name_id = {}
                for cell_id, cell in enumerate(oasis_layout.cells):
                    if cell.name.string in name_id:
                        raise RuntimeError(
                            'Each cell name should be unique, name "' + cell.name.string + '" is used multiple times')
                    name_id[cell.name.string] = cell_id
                    cell.name = cell_id
                for cell in oasis_layout.cells:
                    for placement in cell.placements:
                        placement.name = name_id[placement.name.string]

                oasis_layout.cellnames = {v: k for k, v in name_id.items()}

            # improves performance for reading oasis file and workaround for fatamorgana-bug
            replace_names_by_ids(layout)

            with open(name + '.oas', 'wb') as f:
                layout.write(f)
        else:
            raise ValueError('library must be either "gdscad", "gdspy" or "fatamorgana"')

        dlw_data = self.get_dlw_data()
        if dlw_data:
            with open(name + '.dlw', 'w') as f:
                json.dump(dlw_data, f, indent=True)

        with open(name + '.desc', 'w') as f:
            json.dump(self.get_desc(), f, indent=True)

    def get_reduced_layer(self, layer):
        def translate_and_rotate(geometry, offset, angle):
            if not geometry:
                return geometry
            return translate(rotate(geometry, angle if angle else 0, use_radians=True, origin=(0, 0)), *offset)

        return geometric_union(
            (self.layer_dict[layer] if layer in self.layer_dict else []) +
            [translate_and_rotate(cell['cell'].get_reduced_layer(layer), cell['origin'], cell['angle'])
             for cell in self.cells])

    def export_mesh(self, filename, layer_defs):
        from functools import reduce
        from trimesh.primitives import Extrusion
        from trimesh.transformations import translation_matrix

        reduce(lambda a, b: a + b, (Extrusion(polygon=geometry, height=min_max[1] - min_max[0],
                                              transform=translation_matrix((0, 0, min_max[0])))
                                    for layer, min_max in layer_defs.items()
                                    for geometry in self.get_reduced_layer(layer))).export(filename)

    def get_patches(self, origin=(0, 0), angle_sum=0, angle=0, layers=None):
        from descartes import PolygonPatch

        def rotate_pos(pos, rotation_angle):
            if rotation_angle is None:
                return pos
            c, s = np.cos(rotation_angle), np.sin(rotation_angle)
            result = np.array([[c, -s], [s, c]]).dot(pos)
            return result

        own_patches = [
            PolygonPatch(
                translate(rotate(geometric_union(geometry), angle_sum, use_radians=True, origin=(0, 0)), *origin),
                color=['red', 'green', 'blue', 'teal', 'pink'][(layer - 1) % 5], linewidth=0)
            for layer, geometry in self.layer_dict.items() if (layers is None or layer in layers)]
        sub_cells_patches = [p for cell_dict in self.cells for p in
                             cell_dict['cell'].get_patches(
                                 np.array(origin) + rotate_pos(cell_dict['origin'], angle),
                                 angle_sum=angle_sum + (cell_dict['angle'] or 0), angle=cell_dict['angle'],
                                 layers=layers)]

        return own_patches + sub_cells_patches

    def show(self, layers=None, padding=5):
        """
        Shows the current cell

        :param layers: List of the layers to be shown, passing None shows all layers
        :param padding: padding around the structure
        """
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots()
        for patch in self.get_patches(layers=layers):
            ax.add_patch(patch)

        bounds = self.get_bounds(layers)
        ax.set_xlim(bounds[0] - padding, bounds[2] + padding)
        ax.set_ylim(bounds[1] - padding, bounds[3] + padding)
        ax.set_aspect(1)
        fig.show()

    def add_dlw_marker(self, label, layer, origin):
        """
        Adds a marker for 3D-hybrid integration

        :param label: Name of the marker, needs to be unique within the device
        :param layer: Layer at which the marker and markers should be written
        :param origin: Position of the marker
        """
        self.add_to_layer(layer, DLWMarker(origin))
        self.add_to_layer(std_layers.parnamelayer1, Text(origin, 2, label, alignment='center-center'))

        self.add_dlw_data('marker', label, {'origin': origin.tolist()})

    def add_dlw_taper_at_port(self, label, layer, port, taper_length, tip_width=.01, with_markers=True):
        """
        Adds a taper for 3D-hybrid-integration at a certain port

        :param label: Name of the port, needs to be unique within the device
        :param layer: Layer at which the taper and markers should be written
        :param port: Port to which the taper should be attached
        :param taper_length: length of the taper
        :param tip_width: final width of the tip
        :param with_markers: for recognizing the taper markers near to the taper are necessary.
            In certain designs the standard positions are not appropriate and
            can therefore be disabled and manually added
        """
        taper_port = port.longitudinal_offset(taper_length)
        if taper_length > 0:
            wg = Waveguide.make_at_port(port)
            wg.add_straight_segment(taper_length, final_width=tip_width)
            self.add_to_layer(layer, wg.get_shapely_object())
        self.add_to_layer(std_layers.parnamelayer1, Text(taper_port.origin, 2, label, alignment='center-center'))

        self.add_dlw_data('taper', str(label), {'origin': taper_port.origin.tolist(), 'angle': port.angle,
                                                'starting_width': port.width, 'taper_length': taper_length})
        if with_markers:
            for i, (v, l) in enumerate(itertools.product((-20, 20), (taper_length, 0))):
                self.add_dlw_marker(str(label) + '-' + str(i), layer,
                                    port.parallel_offset(v).longitudinal_offset(l).origin)


if __name__ == '__main__':
    from gdshelpers.parts.port import Port
    from gdshelpers.parts.waveguide import Waveguide
    from gdshelpers.geometry.chip import Cell

    # Create a cell-like object that offers a save output command '.save' which creates the .gds or .oas file by using
    # gdsCAD,gdspy or fatamorgana
    device_cell = Cell('my_cell')
    # Create a port to connect waveguide structures to
    port = Port(origin=(0, 0), width=1, angle=0)
    waveguide = Waveguide.make_at_port(port)
    for i in range(9):
        waveguide.add_bend(angle=np.pi, radius=60 + i * 40)
    # Add direct laser writing taper and alignment marker for postprocessing with a dlw printer to the cell-like object.
    # The cell dlw files will be saved with the cell.
    device_cell.add_dlw_taper_at_port('A0', 2, port.inverted_direction, 30)
    device_cell.add_dlw_taper_at_port('A1', 2, waveguide.current_port, 30)
    device_cell.add_to_layer(1, waveguide)
    device_cell.show()
    # Creates the output file by using gdspy,gdsCAD or fatamorgana. To use the implemented parallell processing, set
    # parallel=True.
    device_cell.save(name='my_design', parallel=True, library='gdspy')

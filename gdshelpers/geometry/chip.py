import itertools
import json
import numpy as np
from typing import List, Optional
from shapely.affinity import translate, rotate
from shapely.geometry import box

from gdshelpers.geometry.shapely_adapter import convert_to_layout_objs, bounds_union, transform_bounds
from gdshelpers.export.gdsii_export import write_cell_to_gdsii_file
from gdshelpers.geometry import geometric_union
from gdshelpers.parts.port import Port
import gdshelpers.helpers.layers as std_layers


class Cell:
    def __init__(self, name: str):
        """
        Creates a new Cell named `name` at `origin`

        :param name: Name of the cell, needs to be unique
        """
        self.name = name
        self.cells = []
        self.layer_dict = {}
        self.dlw_data = {}
        self.desc = {'dlw': self.dlw_data, 'desc': {}, 'ebl': []}
        self.cell_gdspy = None
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

    def get_bounds(self, layers: Optional[List[int]] = None):
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
                    if geo_bounds != ():  # Some shapely geometries (collections) can return empty bounds
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
        """
        Returns the size of the cell
        """
        bounds = self.bounds
        if bounds is None:
            return 0, 0
        else:
            return bounds[2] - bounds[0], bounds[3] - bounds[1]

    def add_to_layer(self, layer: int, *geometry):
        """
        Adds a shapely geometry to a the layer

        :param layer: id of the layer, a tuple (layer, datatype) can also be passed to define the datatype as well
        :param geometry: shapely geometry
        """

        self._bounds = None
        if layer not in self.layer_dict:
            self.layer_dict[layer] = []
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

    def add_cell(self, cell, origin=(0, 0), angle: Optional[float] = None, columns=1, rows=1, spacing=None):
        """
        Adds a Cell to this cell

        :param cell: Cell to add
        :param origin: position where to add the cell
        :param angle: defines the rotation of the cell
        :param columns: Number of columns
        :param rows: Number of rows
        :param spacing: Spacing between the cells, should be an array in the form [x_spacing, y_spacing]
        """
        if cell.get_dlw_data() and cell.name in [cell_dict['cell'].name for cell_dict in self.cells]:
            raise ValueError(
                'Cell name "{cell_name:s}" added multiple times to {self_name:s}.'
                ' This is not allowed for cells containing DLW data.'.format(
                    cell_name=cell.name, self_name=self.name
                )
            )
        self.cells.append(
            dict(cell=cell, origin=origin, angle=angle, magnification=None, x_reflection=False, columns=columns,
                 rows=rows, spacing=spacing))

    def add_region_layer(self, region_layer: int = std_layers.regionlayer, layers: Optional[List[int]] = None):
        """
        Generate a region layer around all objects on `layers` and place it on layer `region_layer`.
        If `layers` is None, all layers are used.
        """
        self.add_to_layer(region_layer, box(*self.get_bounds(layers)))

    def add_frame(self, padding=30., line_width=1., frame_layer: int = std_layers.framelayer, bounds=None):
        """
        Generates a rectangular frame around the contents of the cell.

        :param padding: Add a padding of the given value around the contents of the cell
        :param line_width: Width of the frame line
        :param frame_layer: Layer to put the frame on.
        :param bounds: Optionally, an explicit extent in the form (min_x, min_y, max_x, max_y) can be passed to
            the function. If `None` (default), the current extent of the cell will be chosen.
        """
        padding = padding + line_width
        bounds = bounds or self.bounds

        frame = box(bounds[0] - padding, bounds[1] - padding, bounds[2] + padding, bounds[3] + padding)
        frame = frame.difference(frame.buffer(-line_width))
        self.add_to_layer(frame_layer, frame)

    def add_ebl_marker(self, layer: int, marker):
        """
        Adds an Marker to the layout

        :param layer: layer on which the marker should be positioned
        :param marker: marker, that should be added (from gdshelpers.parts.markers)
        """
        self.add_to_layer(layer, marker)
        self.desc['ebl'].append(list(marker.origin))

    def add_ebl_frame(self, layer: int, frame_generator, bounds=None, **kwargs):
        """
        Adds global markers to the layout

        :param layer:  layer on which the markers should be positioned
        :param frame_generator: either a method, which returns a list of the markers, which should be added or the name
            of a generator from the gdshelpers.geometry.ebl_frame_generators package
        :param bounds: Optionally the bounds to use can be provided in the form (min_x, min_y, max_x, max_y). If None,
            the standard cell bounds will be used.
        :param kwargs: Parameters which are directly passed to the frame generator (other than the bounds parameter)
        """
        from gdshelpers.geometry import ebl_frame_generators
        frame_generator = frame_generator if callable(frame_generator) else getattr(ebl_frame_generators,
                                                                                    frame_generator)
        bounds = bounds or self.bounds

        for marker in frame_generator(bounds, **kwargs):
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
                    if sub_cell['angle'] is not None:
                        c, s = np.cos(sub_cell['angle']), np.sin(sub_cell['angle'])
                        data['origin'] = np.array([[c, -s], [s, c]]).dot(data['origin'])
                        data['angle'] += sub_cell['angle']
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

    def get_fractured_layer_dict(self, max_points=4000, max_line_points=4000):
        from gdshelpers.geometry.shapely_adapter import shapely_collection_to_basic_objs, fracture_intelligently
        fractured_layer_dict = {}
        for layer, geometries in self.layer_dict.items():
            fractured_geometries = []
            for geometry in geometries:
                geometry = geometry.get_shapely_object() if hasattr(geometry, 'get_shapely_object') else geometry
                if type(geometry) in [list, tuple]:
                    geometry = geometric_union(geometry)
                geometry = shapely_collection_to_basic_objs(geometry)
                geometry = itertools.chain(
                    *[fracture_intelligently(geo, max_points, max_line_points) for geo in geometry if not geo.is_empty])
                fractured_geometries.append(geometry)
            fractured_layer_dict[layer] = itertools.chain(*fractured_geometries)
        return fractured_layer_dict

    def get_gdspy_cell(self, executor=None):
        import gdspy
        if self.cell_gdspy is None:
            self.cell_gdspy = gdspy.Cell(self.name)
            for sub_cell in self.cells:
                angle = np.rad2deg(sub_cell['angle']) if sub_cell['angle'] is not None else None
                if sub_cell['columns'] == 1 and sub_cell['rows'] == 1 and not sub_cell['spacing']:
                    self.cell_gdspy.add(
                        gdspy.CellReference(sub_cell['cell'].get_gdspy_cell(executor), origin=sub_cell['origin'],
                                            rotation=angle, magnification=sub_cell['magnification'],
                                            x_reflection=sub_cell['x_reflection']))
                else:
                    self.cell_gdspy.add(
                        gdspy.CellArray(sub_cell['cell'].get_gdspy_cell(executor), origin=sub_cell['origin'],
                                        rotation=angle, magnification=sub_cell['magnification'],
                                        x_reflection=sub_cell['x_reflection'], columns=sub_cell['columns'],
                                        rows=sub_cell['rows'], spacing=sub_cell['spacing']))
            for layer, geometries in self.layer_dict.items():
                for geometry in geometries:
                    if executor:
                        executor.submit(convert_to_layout_objs, geometry, layer, library='gdspy') \
                            .add_done_callback(lambda future: self.cell_gdspy.add(future.result()))
                    else:
                        self.cell_gdspy.add(convert_to_layout_objs(geometry, layer, library='gdspy'))
        return self.cell_gdspy

    def get_oasis_cells(self, grid_steps_per_micron=1000, executor=None):
        import fatamorgana
        import fatamorgana.records
        if self.cell_oasis is None:
            self.cell_oasis = fatamorgana.Cell(fatamorgana.NString(self.name))
            for sub_cell in self.cells:
                x, y = sub_cell['origin']
                x, y = round(x * grid_steps_per_micron), round(y * grid_steps_per_micron)
                angle = np.rad2deg(sub_cell['angle']) if sub_cell['angle'] is not None else None
                repetition = None
                if not (sub_cell['columns'] == 1 and sub_cell['rows'] == 1 and not sub_cell['spacing']):
                    repetition = fatamorgana.basic.GridRepetition(
                        [round(sub_cell['spacing'][0] * grid_steps_per_micron), 0],
                        sub_cell['columns'],
                        [0, round(sub_cell['spacing'][1] * grid_steps_per_micron)],
                        sub_cell['rows'])
                self.cell_oasis.placements.append(
                    fatamorgana.records.Placement(False, name=fatamorgana.NString(sub_cell['cell'].name), x=x, y=y,
                                                  angle=angle, repetition=repetition))
            for layer, geometries in self.layer_dict.items():
                for geometry in geometries:
                    if executor:
                        executor.submit(convert_to_layout_objs, geometry,
                                        (layer if isinstance(layer, int) else layer[0]),
                                        datatype=(None if isinstance(layer, int) else layer[1]), library='oasis',
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
        import gdspy
        self.get_gdspy_cell()
        return gdspy.current_library

    def start_viewer(self):
        import gdspy
        gdspy.LayoutViewer(library=self.get_gdspy_lib(), depth=10)

    def save(self, name=None, library=None, grid_steps_per_micron=1000, parallel=False, max_workers=None):
        """
        Exports the layout and creates an DLW-file, if DLW-features are used.

        :param name: The filename of the saved file. The ending of the filename defines the format.
            Currently .gds, .oasis and .dxf are supported.
        :param library: Name of the used library.
            Should stay `None` in order to select the library depending on the file-ending.
            The use of this parameter is deprecated and this parameter will be removed in a future release.
        :param grid_steps_per_micron: Defines the resolution
        :param parallel: Defines if parallelization is used (only supported in Python 3).
            Standard value will be changed to True in a future version.
            Deactivating can be useful for debugging reasons.
        :param max_workers: If parallel is True, this can be used to limit the number of parallel processes.
            This can be useful if you run into out-of-memory errors otherwise.
        """

        if library is not None:
            import warnings
            warnings.warn('The use of the `library` parameter is deprecated. '
                          'Instead, define the format by the file ending of the filename.', DeprecationWarning)

        if not name:
            name = self.name
        elif name.endswith('.gds'):
            name = name[:-4]
            library = library or 'gdshelpers'
        elif name.endswith('.oas'):
            name = name[:-4]
            library = library or 'fatamorgana'
        elif name.endswith('.dxf'):
            name = name[:-4]
            library = library or 'ezdxf'

        library = library or 'gdshelpers'

        if library == 'gdshelpers':
            from tempfile import NamedTemporaryFile
            import shutil

            with NamedTemporaryFile('wb', delete=False) as tmp:
                write_cell_to_gdsii_file(tmp, self, grid_steps_per_unit=grid_steps_per_micron, parallel=parallel,
                                         max_workers=max_workers)
            shutil.move(tmp.name, name + '.gds')

        elif library == 'gdspy':
            import gdspy

            if parallel:
                from concurrent.futures import ProcessPoolExecutor
                with ProcessPoolExecutor(max_workers=max_workers) as pool:
                    self.get_gdspy_cell(pool)
            else:
                self.get_gdspy_cell()

            self.get_gdspy_lib().precision = self.get_gdspy_lib().unit / grid_steps_per_micron
            gdspy_cells = self.get_gdspy_lib().cell_dict.values()
            if parallel:
                from concurrent.futures import ProcessPoolExecutor
                with ProcessPoolExecutor(max_workers=max_workers) as pool:
                    binary_cells = pool.map(gdspy.Cell.to_gds, gdspy_cells, [grid_steps_per_micron] * len(gdspy_cells))
            else:
                binary_cells = map(gdspy.Cell.to_gds, gdspy_cells, [grid_steps_per_micron] * len(gdspy_cells))

            self.get_gdspy_lib().write_gds(name + '.gds', cells=[], binary_cells=binary_cells)
        elif library == 'fatamorgana':
            import fatamorgana
            layout = fatamorgana.OasisLayout(grid_steps_per_micron)

            if parallel:
                from concurrent.futures import ProcessPoolExecutor
                with ProcessPoolExecutor(max_workers=max_workers) as pool:
                    cells = self.get_oasis_cells(grid_steps_per_micron, pool)
            else:
                cells = self.get_oasis_cells(grid_steps_per_micron)

            layout.cells = [cells[0]] + list(set(cells[1:]))

            with open(name + '.oas', 'wb') as f:
                layout.write(f)
        elif library == 'ezdxf':
            from gdshelpers.export.dxf_export import write_cell_to_dxf_file
            with open(name + '.dxf', 'w') as f:
                write_cell_to_dxf_file(f, self, grid_steps_per_micron, parallel=parallel)
        else:
            raise ValueError('library must be either "gdshelpers", "gdspy", "fatamorgana" or "ezdxf"')

        dlw_data = self.get_dlw_data()
        if dlw_data:
            with open(name + '.dlw', 'w') as f:
                json.dump(dlw_data, f, indent=True)

    def save_desc(self, filename: str):
        """
        Saves a description file for the layout. The file format is not final yet and might change in a future release.

        :param filename: name of the file the description data will be written to
        """
        if not filename.endswith('.desc'):
            filename += '.desc'
        with open(filename, 'w') as f:
            json.dump(self.get_desc(), f, indent=True)

    def get_reduced_layer(self, layer: int):
        """
        Returns a single shapely object containing the structures on a certain layer from this cell and all added cells.

        :param layer: the layer whose structures will be returned
        :return: a single shapely-geometry
        """

        def translate_and_rotate(geometry, offset, angle):
            if not geometry:
                return geometry
            return translate(rotate(geometry, angle if angle else 0, use_radians=True, origin=(0, 0)), *offset)

        return geometric_union(
            (self.layer_dict[layer] if layer in self.layer_dict else []) +
            [translate_and_rotate(cell['cell'].get_reduced_layer(layer), cell['origin'], cell['angle'])
             for cell in self.cells])

    def export_mesh(self, filename: str, layer_defs):
        """
        Saves the current geometry as a mesh-file.

        :param filename: Name of the file which will be created. The file ending determines the format.
        :param layer_defs: Definition of the layers, should be a list like [(layer,(z_min,z_max)),...]
        """
        from functools import reduce
        from trimesh.primitives import Extrusion
        from trimesh.transformations import translation_matrix

        reduce(lambda a, b: a + b, (Extrusion(polygon=geometry, height=min_max[1] - min_max[0],
                                              transform=translation_matrix((0, 0, min_max[0])))
                                    for layer, min_max in layer_defs.items()
                                    for geometry in (lambda x: x if hasattr(x, '__iter__') else [x, ])(
            self.get_reduced_layer(layer)))).export(filename)

    def get_patches(self, origin=(0, 0), angle_sum=0, angle=0, layers: Optional[List[int]] = None):
        from descartes import PolygonPatch

        def rotate_pos(pos, rotation_angle):
            if rotation_angle is None:
                return pos
            c, s = np.cos(rotation_angle), np.sin(rotation_angle)
            result = np.array([[c, -s], [s, c]]).dot(pos)
            return result

        own_patches = []
        for layer, geometry in self.layer_dict.items():
            if layers is not None and layer not in layers:
                continue
            geometry = geometric_union(geometry)
            if geometry.is_empty:
                continue
            geometry = translate(rotate(geometry, angle_sum, use_radians=True, origin=(0, 0)), *origin)
            own_patches.append(
                PolygonPatch(geometry, color=['red', 'green', 'blue', 'teal', 'pink'][(np.sum(layer) - 1) % 5],
                             linewidth=0))

        sub_cells_patches = [p for cell_dict in self.cells for p in
                             cell_dict['cell'].get_patches(
                                 np.array(origin) + rotate_pos(cell_dict['origin'], angle),
                                 angle_sum=angle_sum + (cell_dict['angle'] or 0), angle=cell_dict['angle'],
                                 layers=layers)]

        return own_patches + sub_cells_patches

    def save_image(self, filename: str, layers: Optional[List[int]] = None, antialiased=True, resolution=1.,
                   ylim=(None, None), xlim=(None, None), scale=1.):
        """
           Save cell object as an image.

           You can either use a rasterized file format such as png but also formats such as SVG or PDF.

           :param filename: Name of the image file.
           :param layers: Layers to show im the image
           :param resolution: Rasterization resolution in GDSII units.
           :param antialiased: Whether to use a anti-aliasing or not.
           :param ylim: Tuple of (min_x, max_x) to export.
           :param xlim: Tuple of (min_y, max_y) to export.
           :param scale: Defines the scale of the image
           """
        import matplotlib.pyplot as plt

        # For vector graphics, map 1um to {resolution} mm instead of inch.
        is_vector = filename.split('.')[-1] in ('svg', 'svgz', 'eps', 'ps', 'emf', 'pdf')
        scale *= 5 / 127. if is_vector else 1.

        fig, ax = plt.subplots()
        for patch in self.get_patches(layers=layers):
            patch.set_antialiased(antialiased)
            ax.add_patch(patch)

        # Autoscale, then change the axis limits and read back what is actually displayed
        ax.autoscale(True, tight=True)
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        actual_ylim, actual_xlim = ax.get_ylim(), ax.get_xlim()
        fig.set_size_inches(np.asarray((actual_xlim[1] - actual_xlim[0], actual_ylim[1] - actual_ylim[0])) * scale)

        ax.set_aspect(1)
        ax.axis('off')

        fig.set_dpi(1 / resolution)
        plt.savefig(filename, transparent=True, bbox_inches='tight', dpi=1 / resolution)
        plt.close()

    def show(self, layers: Optional[List[int]] = None, padding=5):
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
        plt.show()

    def add_dlw_marker(self, label: str, layer: int, origin, box_size=2.5):
        """
        Adds a marker for 3D-hybrid integration

        :param label: Name of the marker, needs to be unique within the device
        :param layer: Layer at which the marker and markers should be written
        :param origin: Position of the marker
        :param box_size: Size of the box of the marker
        """
        from gdshelpers.parts.marker import DLWMarker
        from gdshelpers.parts.text import Text

        self.add_to_layer(layer, DLWMarker(origin, box_size=box_size))
        self.add_to_layer(std_layers.parnamelayer1, Text(origin, 2, label, alignment='center-center'))

        self.add_dlw_data('marker', label, {'origin': list(origin), 'angle': 0})

    def add_dlw_taper_at_port(self, label: str, layer: int, port: Port, taper_length: float, tip_width=.01,
                              with_markers=True, box_size=2.5):
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
        :param box_size: Size of the box of the markers
        """
        from gdshelpers.parts.text import Text

        taper_port = port.longitudinal_offset(taper_length)
        if taper_length > 0:
            from gdshelpers.parts.waveguide import Waveguide
            wg = Waveguide.make_at_port(port)
            wg.add_straight_segment(taper_length, final_width=tip_width)
            self.add_to_layer(layer, wg.get_shapely_object())
        self.add_to_layer(std_layers.parnamelayer1, Text(taper_port.origin, 2, label, alignment='center-center'))

        self.add_dlw_data('taper', str(label), {'origin': taper_port.origin.tolist(), 'angle': port.angle,
                                                'starting_width': port.width, 'taper_length': taper_length})
        if with_markers:
            for i, (v, l) in enumerate(itertools.product((-20, 20), (taper_length, 0))):
                self.add_dlw_marker(str(label) + '-' + str(i), layer,
                                    port.parallel_offset(v).longitudinal_offset(l).origin, box_size=box_size)


if __name__ == '__main__':
    from gdshelpers.parts.port import Port
    from gdshelpers.parts.waveguide import Waveguide

    # Create a cell-like object that offers a save output command '.save' which creates the .gds or .oas file by using
    # gdspy or fatamorgana
    device_cell = Cell('my_cell')
    # Create a port to connect waveguide structures to
    start_port = Port(origin=(0, 0), width=1, angle=0)
    waveguide = Waveguide.make_at_port(start_port)
    for i_bend in range(9):
        waveguide.add_bend(angle=np.pi, radius=60 + i_bend * 40)
    # Add direct laser writing taper and alignment marker for postprocessing with a dlw printer to the cell-like object.
    # The cell dlw files will be saved with the cell.
    device_cell.add_dlw_taper_at_port('A0', (1, 2), start_port.inverted_direction, 30)
    device_cell.add_dlw_taper_at_port('A1', (1, 2), waveguide.current_port, 30)
    device_cell.add_to_layer(1, waveguide)
    device_cell.show()
    device_cell.save_image('chip.pdf')
    # Creates the output file by using gdspy or fatamorgana. To use the implemented parallel processing, set
    # parallel=True.
    print('gds')
    device_cell.save(name='my_design', parallel=True)
    print('oas')
    device_cell.save(name='my_design.oas', parallel=True)
    print('stl')
    device_cell.export_mesh('my_design.stl', layer_defs={(1, 2): (0, 1)})
    print('array')
    array_cell = Cell('Array')
    array_cell.add_cell(device_cell, rows=2, columns=2, spacing=(1000, 1000))
    array_cell.save()

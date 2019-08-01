from __future__ import division, print_function

import itertools

import shapely.topology
import shapely.ops
import shapely.geometry
import shapely.geos
import shapely.validation

import numpy as np

import warnings
import gdshelpers
from gdshelpers.helpers import raith_eline_dosefactor_to_datatype


def shapely_collection_to_basic_objs(collection):
    """
    Convert the object or the collection to a list of basic shapely objects.

    :param collection:
    :return: :rtype:
    """

    if isinstance(collection, (tuple, list)):
        objs = list()

        for col in collection:
            objs.extend(shapely_collection_to_basic_objs(col))
    else:
        objs = hasattr(collection, 'geoms') and collection.geoms or [collection, ]
    return objs


def cut_shapely_object(obj, x_axis=None, y_axis=None, other_side=False):
    """
    Cut a shapely object into two halves.

    If both x_axis and y_axis are None, they are assumed to be
    the center of the bounding box.

    If only one of the axis is given, and the other axis is None,
    the object is cut at the given axis.

    If both values are given, or inferred to be the center of the bounding
    box due to being both None, the object is cut along its longer side.

    :param obj: Basically any shapely object
    :type obj: shapely.base.BaseGeometry
    :param x_axis: x-axis cut value.
    :type x_axis: float, None
    :param y_axis: y-axis cut value.
    :param other_side: If the cut axis is determined automatically, use the other direction.
    :return: A tuple of two shapely objects.
    :rtype: list
    """
    _safety_overlap = 1.
    bbox = np.array(obj.bounds).reshape(2, -1)
    bbox += ((-_safety_overlap, -_safety_overlap),
             (_safety_overlap, _safety_overlap))

    if (x_axis is None) and (y_axis is None):
        cut_center = bbox.mean(0)
    else:
        cut_center = x_axis, y_axis

    if not ((x_axis is None) ^ (y_axis is None)):
        if ((bbox[1] - bbox[0]).argmax() == 0) != other_side:
            # X-Direction is largest, cut vertically
            x_axis = cut_center[0]
            y_axis = None
        else:
            # Y-Direction is largest, cut horizontally
            x_axis = None
            y_axis = cut_center[1]

    if x_axis is not None:
        cut_boxes = [shapely.geometry.box(bbox[0][0], bbox[0][1], x_axis, bbox[1][1]),
                     shapely.geometry.box(x_axis, bbox[0][1], bbox[1][0], bbox[1][1])]
    else:
        cut_boxes = [shapely.geometry.box(bbox[0][0], bbox[0][1], bbox[1][0], y_axis),
                     shapely.geometry.box(bbox[0][0], y_axis, bbox[1][0], bbox[1][1])]

    try:
        out_polygons = list()
        for cut_box in cut_boxes:
            cut_polygon = obj.intersection(cut_box)
            out_polygons.extend(hasattr(cut_polygon, 'geoms') and list(cut_polygon.geoms) or [cut_polygon, ])
    except shapely.geos.TopologicalError:
        # In case of invalid geometries, try to fix them and refracture
        warnings.warn('Trying to cut an invalid polygon (possibly during gdsCAD conversion).')
        warnings.warn('We\'ll try to fix the polygon for you now, but try and figure out what\'s wrong, please.')
        return cut_shapely_object(obj.buffer(0), x_axis, y_axis, other_side=other_side)

    # If the original object was a polygon we may not create lines!
    if isinstance(obj, shapely.geometry.Polygon):
        out_polygons = [shape for shape in out_polygons if not isinstance(shape, (shapely.geometry.LinearRing,
                                                                                  shapely.geometry.LineString,))]

    return out_polygons


def _number_of_points(poly):
    """
    Returns the number of points in a Shapely geometry.

    :param poly: Shapely geometry object.
    :return: Number of points int the Shapely object.
    :rtype: int
    """
    if hasattr(poly, '_gdsh_n_points'):
        return poly._gdsh_n_points

    elif hasattr(poly, 'geoms'):
        poly._gdsh_n_points = sum(_number_of_points(p) for p in poly.geoms)

    elif type(poly) == shapely.geometry.Polygon:
        poly._gdsh_n_points = len(poly.exterior.coords) + sum([len(shapely.geometry.LinearRing(x).coords) for x
                                                               in list(poly.interiors)])
    else:
        poly._gdsh_n_points = len(poly.coords)

    return poly._gdsh_n_points


def heal(objs, max_points, max_interior=0):
    """
    Heal a list of Shapely geometries.

    All elements touching each other will be merged as long as the number of points remains below *max_points*.

    :param objs: List Shapely geometries.
    :type objs: list, tuple
    :param max_points: Maximum number of points.
    :type max_points: int
    :return: List of healed Shapely geometries.
    :rtype: list
    """

    segments_joined = True
    while segments_joined:
        segments_joined = False
        for i, polygon in enumerate(objs):
            if type(polygon) != shapely.geometry.Polygon:
                continue

            polygon_points = _number_of_points(polygon)

            for j, polygon2 in enumerate(objs):
                if polygon == polygon2:
                    continue
                if type(polygon2) != shapely.geometry.Polygon:
                    continue

                if max_points and polygon_points + _number_of_points(polygon2) >= (max_points - 2):
                    continue

                if polygon.touches(polygon2):
                    joined_poly = polygon.union(polygon2)

                    if type(joined_poly) != shapely.geometry.Polygon:
                        continue

                    if len(joined_poly.interiors) > max_interior:
                        continue

                    if max_points and _number_of_points(joined_poly) >= max_points:
                        continue

                    objs.append(joined_poly)
                    segments_joined = True
                    if i > j:
                        del objs[i]
                        del objs[j]
                    else:
                        del objs[j]
                        del objs[i]

                    break
    return objs


def fracture(obj, max_points_poly, max_points_line, max_interior=0):
    out_polygons = [obj, ]

    done_counter = 0
    while done_counter < len(out_polygons):
        current_polygon = out_polygons[done_counter]

        max_points = max_points_poly if type(current_polygon) == shapely.geometry.Polygon else max_points_line

        if type(current_polygon) == shapely.geometry.Polygon and len(current_polygon.interiors) > max_interior:
            uncut_polygon = out_polygons.pop(done_counter)
            cut_point = current_polygon.interiors[0].centroid.coords[0]
            shapes = cut_shapely_object(uncut_polygon, cut_point[0], cut_point[1])
            extended_shapes = shapely_collection_to_basic_objs(shapes)
            out_polygons.extend(extended_shapes)

        elif max_points and _number_of_points(current_polygon) > max_points > 0:
            uncut_polygon = out_polygons.pop(done_counter)
            shapes = cut_shapely_object(uncut_polygon)
            extended_shapes = shapely_collection_to_basic_objs(shapes)
            out_polygons.extend(extended_shapes)
        else:
            done_counter += 1

    return out_polygons


def fracture_intelligently(obj, max_points, max_points_line, over_fracture_factor=1):
    if over_fracture_factor >= 1:
        fractured_obj = fracture(obj, max_points / over_fracture_factor, max_points_line)

        # Now that the polygons have been fractured, we might be able to join them back
        # into bigger segments.
        return heal(fractured_obj, max_points)
    else:
        return fracture(obj, max_points, max_points_line)


def geometric_union(objs):
    """
    Join a list of Parts and/or Shapely objects to one big Shapely object.

    :param objs: List of Parts and Shapely objects.
    :return: Merged Shapely geometry.
    :rtype: shapely.base.BaseGeometry
    """
    objs = [obj.get_shapely_object() if hasattr(obj, 'get_shapely_object') else obj for obj in objs]
    return shapely.ops.cascaded_union(objs)


def convert_to_gdscad(objs, layer=1, datatype=None, path_width=1.0, path_pathtype=0, max_points=None,
                      over_fracture_factor=1, max_points_line=None):
    """
    Convert any shapely or list of shapely objects to a list of gdsCAD objects.

    Since Shapely objects do not contain layer information nor line width for Shapely lines, you have to specify
    these during conversion. Typically, you will only convert polygons and specify the *layer*.

    Export options such as *datatype* and maximum number of points per Polygon/Line default to the current module
    default.

    On special feature is the *over_fracture_factor*. The polygons will be fractured into
    *max_points*/*over_fracture_factor* points and then healed again - which results in better fragmentation of some
    geometries. An *over_fracture_factor* of 0 will suppress healing.

    :param objs: Part or Shapely object or list of Parts and/or Shapely objects.
    :param layer: Layer on which to put the objects.
    :type layer: int
    :param datatype: GDS datatype of the converted objects. Defaults to module wide settings.
    :type datatype: int
    :param path_width: With of GDS path, converted from Shapely lines.
    :type path_width: float
    :param path_pathtype: GDS path end type.
    :type path_pathtype: int
    :param max_points: Maximum number of points. Defaults to module wide settings.
    :type max_points: int, None
    :param max_points_line: Maximum number of points for lines. Defaults to module wide settings.
    :type max_points_line: int, None
    :param over_fracture_factor: Break polygons in *over_fracture_factor* times smaller objects first. Then merge them
                                 again. May result in better fracturing but high numbers increase conversion time.

                                 When *over_fracture_factor* is set to 0, no additional healing is done.
    :type over_fracture_factor: int
    """

    return convert_to_layout_objs(objs, layer, datatype, path_width, path_pathtype, max_points, over_fracture_factor,
                                  max_points_line, library='gdscad')


def convert_to_layout_objs(objs, layer=1, datatype=None, path_width=1.0, path_pathtype=0, max_points=None,
                           over_fracture_factor=1, max_points_line=None, library='gdscad', grid_steps_per_micron=1000):
    """
    Convert any shapely or list of shapely objects to a list of gdsCAD objects.

    Since Shapely objects do not contain layer information nor line width for Shapely lines, you have to specify
    these during conversion. Typically, you will only convert polygons and specify the *layer*.

    Export options such as *datatype* and maximum number of points per Polygon/Line default to the current module
    default.

    On special feature is the *over_fracture_factor*. The polygons will be fractured into
    *max_points*/*over_fracture_factor* points and then healed again - which results in better fragmentation of some
    geometries. An *over_fracture_factor* of 0 will suppress healing.

    :param objs: Part or Shapely object or list of Parts and/or Shapely objects.
    :param layer: Layer on which to put the objects.
    :type layer: int
    :param datatype: GDS datatype of the converted objects. Defaults to module wide settings.
    :type datatype: int
    :param path_width: With of GDS path, converted from Shapely lines.
    :type path_width: float
    :param path_pathtype: GDS path end type.
    :type path_pathtype: int
    :param max_points: Maximum number of points. Defaults to module wide settings.
    :type max_points: int, None
    :param max_points_line: Maximum number of points for lines. Defaults to module wide settings.
    :type max_points_line: int, None
    :param over_fracture_factor: Break polygons in *over_fracture_factor* times smaller objects first. Then merge them
                                 again. May result in better fracturing but high numbers increase conversion time.

                                 When *over_fracture_factor* is set to 0, no additional healing is done.
    :type over_fracture_factor: int
    :param library: Defines the used library, either gdscad or gdspy
    :type library: str
    :param grid_steps_per_micron: Number of steps of the grid per micron, defaults to 1000 steps per micron
    :type grid_steps_per_micron: int
    """
    if library == 'gdscad':
        import gdsCAD
    elif library == 'gdspy':
        import gdspy
    elif library == 'oasis':
        import fatamorgana.records
    else:
        raise AssertionError('library must be either "gdscad" or "gdspy"')

    # If number of maximum points is not specified, default to the current profile default
    max_points = max_points if max_points is not None else gdshelpers.configuration.point_limit
    max_points_line = max_points_line if max_points_line is not None else gdshelpers.configuration.point_limit_line

    # If datatype is not specified, set it the same as layer
    if datatype is None:
        policy = gdshelpers.configuration.datatype_policy
        if policy == gdshelpers.configuration.DefaultDatatype.zero:
            datatype = 0
        elif policy == gdshelpers.configuration.DefaultDatatype.aslayer:
            datatype = layer
        elif policy == gdshelpers.configuration.DefaultDatatype.dose_factor:
            datatype = raith_eline_dosefactor_to_datatype(gdshelpers.configuration.dose_factor)

    objs = objs.get_shapely_object() if hasattr(objs, 'get_shapely_object') else objs

    # Convert a list of objects to a true shapely object or collection first
    if type(objs) in [list, tuple]:
        objs = geometric_union(objs)

    # Convert the object or the collection to a list of basic shapely objects
    objs = shapely_collection_to_basic_objs(objs)

    fractured_objs = itertools.chain(*[fracture_intelligently(obj, max_points=max_points,
                                                              max_points_line=max_points_line,
                                                              over_fracture_factor=over_fracture_factor)
                                       for obj in objs if not obj.is_empty])

    exports_objs = list()
    for obj in fractured_objs:
        if type(obj) == shapely.geometry.Point:
            # raise TypeError('Shapely points are not supported to be converted.')
            pass
        elif type(obj) == shapely.geometry.LineString:
            if path_width:
                if library == 'gdscad':
                    exports_objs.append(gdsCAD.core.Path(obj.coords, layer=layer, datatype=datatype, width=path_width,
                                                         pathtype=path_pathtype))
                elif library == 'gdspy':
                    exports_objs.append(gdspy.PolyPath(obj.coords, layer=layer, datatype=datatype, width=path_width,
                                                       ends=path_pathtype))
                elif library == 'oasis':
                    rounded_coords = np.multiply(obj.coords, grid_steps_per_micron).astype(np.int)
                    exports_objs.append(
                        fatamorgana.records.Path((rounded_coords[1:] - rounded_coords[:-1]).tolist(), layer=layer,
                                                 datatype=datatype, half_width=int(path_width * grid_steps_per_micron),
                                                 extension_start=path_pathtype, extension_end=path_pathtype,
                                                 x=rounded_coords[0][0], y=rounded_coords[0][1]))

        elif type(obj) == shapely.geometry.Polygon:
            assert len(obj.interiors) <= 1, 'No polygons with more than one hole allowed, got %i' % len(obj.interiors)
            if library == 'gdscad':
                exports_objs.append(gdsCAD.core.Boundary(obj.exterior.coords, layer=layer, datatype=datatype))
            elif library == 'gdspy':
                exports_objs.append(gdspy.Polygon(obj.exterior.coords, layer=layer, datatype=datatype))
            elif library == 'oasis':
                rounded_coords = np.multiply(obj.exterior.coords, grid_steps_per_micron).astype(np.int)
                exports_objs.append(
                    fatamorgana.records.Polygon((rounded_coords[1:] - rounded_coords[:-1]).tolist(),
                                                layer=layer, datatype=datatype, x=rounded_coords[0][0],
                                                y=rounded_coords[0][1]))

        else:
            raise TypeError('Unhandled type "%s"' % type(obj))
    return exports_objs


def bounds_union(bound_list):
    """
    Calculates the bounding box of all bounding boxes in the given list.
    Each bbox has to be given as (xmin, ymin, xmax, ymax) tuple.

    :param bound_list: List of tuples containing all bounding boxes to be merged
    """
    bounds_array = np.array(bound_list)
    return (np.min(bounds_array[:, 0]), np.min(bounds_array[:, 1]),
            np.max(bounds_array[:, 2]), np.max(bounds_array[:, 3]))


def transform_bounds(bounds, origin, rotation=0, scale=1.):
    """
    Transform a bounds tuple (xmin, ymin, xmax, ymax) by the given offset, rotation and scale.
    """
    bounds = scale * np.array(bounds).reshape(2, 2) + origin
    if rotation != 0:
        center = 0.5 * (bounds[0, :] + bounds[1, :])
        size = np.abs(bounds[1, :] - bounds[0, :])
        c, s = np.cos(rotation), np.sin(rotation)
        rot_matrix = np.array([[c, -s], [s, c]])  # rotation matrix
        new_half_size = 0.5 * np.abs(rot_matrix).dot(size)
        new_center = rot_matrix.dot(center)
        bounds = np.array([new_center - new_half_size, new_center + new_half_size])

    return bounds.flatten()

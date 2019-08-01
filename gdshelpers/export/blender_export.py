import os

from gdshelpers.geometry import shapely_adapter


class Shapely3d(object):
    """
    This class saves the values which will be given to blender
    and it also provides a method for output these values
    """

    def __init__(self, poly, extrude_val_min, extrude_val_max, rgb=(255, 255, 255)):
        if type(poly) in (list, tuple):
            self.poly = shapely_adapter.geometric_union(poly)
        self.poly = shapely_adapter.shapely_collection_to_basic_objs(poly)
        self.rgb = rgb
        self.extrude_val_min = extrude_val_min
        self.extrude_val_max = extrude_val_max

    def to_temp(self, scale, index):
        b3d_lines = []
        for obj in self.poly:
            vertices = ["{:f} {:f}\n".format(coord[0], coord[1]) for coord in obj.exterior.coords]
            b3d_lines.extend(["{:d};{:d};{:f};{:f};{:f};{:d};{:d};{:d}\n".format(index, len(vertices),
                                                                                 self.extrude_val_min,
                                                                                 self.extrude_val_max, scale,
                                                                                 self.rgb[0], self.rgb[1],
                                                                                 self.rgb[2])] + vertices)

        return b3d_lines


def save_as_blend(shapely_3d_list, filename, scale=0.1, resolution_x=1980, resolution_y=1080, resolution_percentage=100,
                  render_engine='CYCLES', camera_position_y='above', camera_position_x='right'):
    """
    writes the 'filename.blend' file

    :param shapely_3d_list: a list of the meshes to export
    :param filename: the name of the .blend and .tmp file
    :param scale: size factor
    :param resolution_x: set x resolution for a later render process
    :param resolution_y: set y resolution for a later render process
    :param resolution_percentage: set resolution percentage
    :param render_engine: set the render engine
    :param camera_position_y: decides if the camera is placed 'above' or 'under' the device
    :param camera_position_x: decides if the camera is places 'right' or 'left' of the device
    :return: nothing
    """

    filename = filename[:-6] if filename.endswith('.blend') else filename
    _write_data_and_start_blender(shapely_3d_list, filename, scale, False, True, resolution_x, resolution_y,
                                  resolution_percentage, render_engine, camera_position_y, camera_position_x)


def render_image(shapely_3d_list, filename, scale=0.1, resolution_x=1980, resolution_y=1080, resolution_percentage=100,
                 render_engine='CYCLES', camera_position_y='above', camera_position_x='right'):
    """
    writes the 'filename.png' file

    :param shapely_3d_list: a list of the meshes to export
    :param filename: the name of the .png and .tmp file
    :param scale: size factor
    :param resolution_x: set x resolution for a later render process
    :param resolution_y: set y resolution for a later render process
    :param resolution_percentage: set resolution percentage
    :param render_engine: set the render engine
    :param camera_position_y: decides if the camera is placed 'above' or 'under' the device
    :param camera_position_x: decides if the camera is places 'right' or 'left' of the device
    :return: nothing
    """

    filename = filename[:-4] if filename.endswith('.png') else filename
    _write_data_and_start_blender(shapely_3d_list, filename, scale, True, False,
                                  resolution_x, resolution_y, resolution_percentage,
                                  render_engine, camera_position_y, camera_position_x)


def render_image_and_save_as_blend(shapely_3d_list, filename, scale=0.1, resolution_x=1980, resolution_y=1080,
                                   resolution_percentage=100, render_engine='CYCLES', camera_position_y='above',
                                   camera_position_x='right'):
    """
    writes the 'filename.png' and 'filename.blend' file

    :param shapely_3d_list: a list of the meshes to export
    :param filename: the name of the .png, .blend and .tmp file
    :param scale: size factor
    :param resolution_x: set x resolution for a later render process
    :param resolution_y: set y resolution for a later render process
    :param resolution_percentage: set resolution percentage
    :param render_engine: set the render engine
    :param camera_position_y: decides if the camera is placed 'above' or 'under' the device
    :param camera_position_x: decides if the camera is places 'right' or 'left' of the device
    :return: nothing
    """

    filename = filename[:-4] if filename.endswith('.png') else filename
    _write_data_and_start_blender(shapely_3d_list, filename, scale, True, True, resolution_x, resolution_y,
                                  resolution_percentage, render_engine, camera_position_y, camera_position_x)


def _write_data_and_start_blender(shapely_3d_list, filename, scale, render, save_as_blend_file, resolution_x,
                                  resolution_y, resolution_percentage, render_engine, camera_position_y,
                                  camera_position_x):
    """
    handles the file operation

    :param shapely_3d_list: a list of the meshes to export
    :param filename: the name of the .png, .blend and .tmp file
    :param scale: size factor
    :param resolution_x: set x resolution for a later render process
    :param resolution_y: set y resolution for a later render process
    :param resolution_percentage: set resolution percentage
    :param render_engine: set the render engine
    :param camera_position_y: decides if the camera is placed 'above' or 'under' the device
    :param camera_position_x: decides if the camera is places 'right' or 'left' of the device
    :return: nothing
    """
    with open(filename + ".tmp", "w") as f_out:
        f_out.write("{:b};{:b};{:d};{:d};{:d};{:s};{:s};{:s}".format(render, save_as_blend_file, resolution_x,
                                                                     resolution_y, resolution_percentage, render_engine,
                                                                     camera_position_y, camera_position_x))
        f_out.write('\n')
        for index, s3d in enumerate(shapely_3d_list):
            f_out.writelines([line for line in s3d.to_temp(scale, index)])

    directory = os.path.dirname(os.path.abspath(__file__))

    os.system("blender --background --python {:s}{:s}blender_import.py -- {:s}".format(directory, os.sep, filename))


def _example_i():
    from gdshelpers.parts.splitter import MMI

    mmi1 = MMI((0, 0), 0, 1, 42, 7.7, 2, 2)
    mmi2 = MMI((0, 10), 0, 1, 42, 7.7, 2, 2)
    mmi3 = MMI((0, -10), 0, 1, 42, 7.7, 2, 2)

    shapely_objects = []
    s3d1 = Shapely3d(mmi1.get_shapely_object(), 0.0, 0.7, (0, 0, 0))
    s3d2 = Shapely3d(mmi2.get_shapely_object(), 0.0, 0.7, (0, 255, 0))
    s3d3 = Shapely3d(mmi3.get_shapely_object(), 0.0, 0.7, (255, 0, 0))
    shapely_objects.append(s3d1)
    shapely_objects.append(s3d2)
    shapely_objects.append(s3d3)

    render_image_and_save_as_blend(shapely_objects, "mmi1")


def _example_ii():
    from gdshelpers.parts.splitter import MMI
    from gdshelpers.geometry import geometric_union

    mmi1 = MMI((0, 0), 0, 1, 42, 7.7, 2, 2)
    mmi2 = MMI((0, 10), 0, 1, 42, 7.7, 2, 2)
    mmi3 = MMI((0, -10), 0, 1, 42, 7.7, 2, 2)

    mmi4 = MMI((0, -20), 0, 1, 42, 7.7, 2, 2)
    mmi5 = MMI((0, -30), 0, 1, 42, 7.7, 2, 2)

    shapely_objects = []

    s3d1 = Shapely3d(geometric_union([mmi1.get_shapely_object(), mmi2.get_shapely_object(), mmi3.get_shapely_object()]),
                     0.0, 0.7, (255, 0, 0))

    s3d2 = Shapely3d(geometric_union([mmi4.get_shapely_object(), mmi5.get_shapely_object()]), 0.0, 0.7, (0, 255, 0))

    shapely_objects.append(s3d1)
    shapely_objects.append(s3d2)

    render_image_and_save_as_blend(shapely_objects, "mmi2")


def _example_iii():
    from gdshelpers.parts.waveguide import Waveguide
    from gdshelpers.parts.coupler import GratingCoupler
    from gdshelpers.geometry import geometric_union
    import numpy as np

    coupler1 = GratingCoupler.make_traditional_coupler((250 / 2, 0), 1.3, np.deg2rad(40), 1.13, 0.85, 20,
                                                       taper_length=16, ap_max_ff=0.985, n_ap_gratings=10)
    wave_guide = Waveguide.make_at_port(coupler1.port)
    wave_guide.add_straight_segment(20)
    wave_guide.add_bend(0.5 * np.pi, 40)
    wave_guide.add_straight_segment(250 - 2 * 40)
    wave_guide.add_bend(0.5 * np.pi, 40)
    wave_guide.add_straight_segment(20)
    coupler2 = GratingCoupler.make_traditional_coupler((wave_guide.current_port.origin[0],
                                                        wave_guide.current_port.origin[1]), 1.3, np.deg2rad(40), 1.13,
                                                       0.85, 20, taper_length=16, ap_max_ff=0.985, n_ap_gratings=10)

    shapely_objects = [Shapely3d(geometric_union([coupler1.get_shapely_object(), wave_guide.get_shapely_object(),
                                                  coupler2.get_shapely_object()]), 0.0, 0.7, (255, 255, 255))]

    render_image_and_save_as_blend(shapely_objects, "test_device_under_right", camera_position_y='under',
                                   camera_position_x='right')

    render_image_and_save_as_blend(shapely_objects, "test_device_above_left", camera_position_y='above',
                                   camera_position_x='left')

    render_image_and_save_as_blend(shapely_objects, "test_device_under_left", camera_position_y='under',
                                   camera_position_x='left')

    render_image_and_save_as_blend(shapely_objects, "test_device_above_right", camera_position_y='above',
                                   camera_position_x='right')


if __name__ == '__main__':
    _example_i()
    _example_ii()
    _example_iii()

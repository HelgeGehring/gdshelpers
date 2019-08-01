import matplotlib.pyplot as plt
import matplotlib.patches
import matplotlib.text

import numpy as np


def save_as_image(obj, file_path, resolution=1., antialiased=True, include_text=False,
                  ylim=(None, None), xlim=(None, None)):
    """
    Save any gdsCAD object as an image.

    You can either use a rasterized file format such as png but also formats such as SVG or PDF.

    :param obj: Any gdsCAD object
    :param file_path: Path of the image file.
    :param resolution: Rasterization resolution in GDSII units.
    :param antialiased: Whether to use a anti-aliasing or not.
    :param include_text: Include text in the output.
    :param ylim: Tuple of (min_x, max_x) to export.
    :param xlim: Tuple of (min_y, max_y) to export.
    """

    # For vector graphics, map 1um to {resolution} mm instead of inch.
    is_vector = file_path.split('.')[-1] in ('svg', 'svgz', 'eps', 'ps', 'emf', 'pdf')
    scale = 5 / 127. if is_vector else 1.

    dpi = 1. / resolution

    fig = plt.figure(frameon=False)
    fig.patch.set_visible(False)

    ax = fig.add_subplot(1, 1, 1)
    ax.set_aspect('equal')
    # ax.margins(0.1)
    ax.axis('off')

    artists = obj.artist()
    for a in artists:
        if not include_text and isinstance(a, matplotlib.text.Text):
            continue

        if hasattr(a, 'set_antialiased'):
            a.set_antialiased(antialiased)

        a.set_transform(a.get_transform() + ax.transData)
        if isinstance(a, matplotlib.patches.Patch):
            ax.add_patch(a)
        elif isinstance(a, matplotlib.lines.Line2D):
            ax.add_line(a)
        else:
            ax.add_artist(a)

    plt.subplots_adjust(left=0., right=1., top=1., bottom=0.)

    # Autoscale, then change the axis limits and read back what is actually displayed
    ax.autoscale(True, tight=True)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    actual_ylim, actual_xlim = ax.get_ylim(), ax.get_xlim()

    fig.set_size_inches(np.asarray((actual_xlim[1] - actual_xlim[0], actual_ylim[1] - actual_ylim[0])) * scale)
    fig.set_dpi(dpi)
    fig.savefig(file_path, transparent=True, dpi=dpi)
    plt.close(fig)


def add_jeol_helpers(cell):
    def extract_special(cell):
        return {
            'cells': [extract_special(ref.ref_cell) for ref in cell.references],
            'elements': [e for e in cell.elements if (hasattr(e, 'is_special') and e.is_special)]
        }

    from pprint import pprint
    pprint(extract_special(cell))


def _example():
    import gdsCAD.core
    from math import pi
    from gdshelpers.geometry import convert_to_gdscad
    from gdshelpers.parts.waveguide import Waveguide
    from gdshelpers.parts.coupler import GratingCoupler

    left_coupler = GratingCoupler.make_traditional_coupler_from_database([0, 0], 1, 'sn330', 1550)
    wg = Waveguide.make_at_port(left_coupler.port)
    wg.add_straight_segment(length=10)
    wg.add_bend(-pi / 2, radius=50)
    wg.add_straight_segment(length=150)
    wg.add_bend(-pi / 2, radius=50)
    wg.add_straight_segment(length=10)
    right_coupler = GratingCoupler.make_traditional_coupler_from_database_at_port(wg.current_port, 'sn330', 1550)

    cell = gdsCAD.core.Cell('SIMPLE_DEVICE')
    cell.add(convert_to_gdscad([left_coupler, wg, right_coupler], layer=1))
    cell.add(convert_to_gdscad([left_coupler.get_description_text(side='right'),
                                right_coupler.get_description_text(side='left')], layer=2))

    save_as_image(cell, '/tmp/test.png', resolution=1)
    save_as_image(cell, '/tmp/test.pdf')
    save_as_image(cell, '/tmp/test.svg')


if __name__ == '__main__':
    _example()

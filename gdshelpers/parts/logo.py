from __future__ import division

import numpy as np

from math import sqrt
from shapely.affinity import rotate, translate, scale
from shapely.geometry import Polygon, box
from shapely.ops import cascaded_union


class KITLogo(object):
    """
    A simplified logo of the Karlsruhe Institute of Technology (KIT).

    :param origin: Tuple specifying the lower left corner of the logo.
    :param height: Height of the logo.
    :param min_radius_fraction: To avoid steep angles, the rays are cut at the minimum radius fraction.
    """

    def __init__(self, origin, height, min_radius_fraction=0.05):
        self.origin = origin
        self.height = height
        self.min_radius_fraction = min_radius_fraction

    def get_shapely_object(self):
        # Start with the "rays"
        # noinspection PyTypeChecker
        ray_angles = np.linspace(0, np.pi / 2, 8) + np.pi / 2
        outer_ray_positions = (np.array([np.cos(ray_angles), np.sin(ray_angles)]) * self.height).T + (self.height, 0)
        inner_ray_positions = (np.array([np.cos(ray_angles), np.sin(ray_angles)])
                               * self.height * self.min_radius_fraction).T + (self.height, 0)

        polygons = list()
        for outer, inner in zip(outer_ray_positions.reshape(-1, 2, 2), inner_ray_positions.reshape(-1, 2, 2)):
            polygons.append(Polygon([outer[0], outer[1], inner[1], inner[0]]))
            pass

        # Draw the letters
        d = self.height * 0.077

        k_upper_branch = rotate(box(0, -d, sqrt(2) * self.height / 2 + sqrt(2) * d, d), 45, origin=(0, 0))
        k_lower_branch = scale(k_upper_branch, yfact=-1., origin=(0, 0))
        k_uncut = k_upper_branch.union(k_lower_branch)
        k_unscaled = k_uncut.intersection(box(0, -self.height / 2., self.height / 2. + sqrt(2) * d, self.height / 2.))
        k = scale(k_unscaled, 0.8, origin=(0, 0))
        polygons.append(translate(k, self.height * 1.05, self.height / 2.))

        i = box(0, 0, 2 * d, self.height)
        polygons.append(translate(i, self.height * 1.6))

        t_overlap = 2
        t = box(-d, 0, d, self.height).union(
            box(-d * (1 + t_overlap), self.height - 2 * d, d * (1 + t_overlap), self.height))
        polygons.append(translate(t, self.height * 2.05))

        logo = cascaded_union(polygons)

        return translate(logo, *self.origin)


class WWULogo(object):
    """
    WWU Logo with WWU written next to it

    :param origin: Tuple specifying the lower left corner of the logo.
    :param height: Height of the logo.
    :param text: 0 no text, 1 text right of logo, 2 text below logo
    """

    def __init__(self, origin, height, text):
        self.origin = origin
        self.height = height
        self.text = text

    def get_shapely_object(self):
        # define WWU Logo measures.
        w = (120 + 96 + 120)
        h = 16 + 59 + 8 + 26 + 16 + 14 + 16 + 23 + 8 + 8 + 16

        h1 = 16  # height of box1
        s1 = 59  # vertical spacing between box1 & 2

        h2 = 8
        s2 = 26

        h3 = 16
        w3 = 120
        s3 = 14

        h4 = 16
        w4 = 51
        s4 = 23

        h5 = 8
        w5 = 30
        s5 = 8

        h6 = 16
        w6 = 8

        # calculate scaling factor to match given height
        # M = self.height/h  # scaling factor

        # each Box's lower left corner xi,yi
        x1, y1 = 0, 0
        x2, y2 = x1, y1 + (h1 + s1)
        x3l, y3 = x2, y2 + (h2 + s2)
        x3r = x2 + 120 + 96
        x4, y4 = x1 + (w - w4) / 2, y3 + (h3 + s3)
        x5, y5 = x1 + (w - w5) / 2, y4 + (h4 + s4)
        x6, y6 = x1 + (w - w6) / 2, y5 + (h5 + s5)

        # define boxes
        boxes = [
            box(x1, y1, x1 + w, y1 + h1),  # box1
            box(x2, y2, x2 + w, y2 + h2),  # ...
            box(x3l, y3, x3l + w3, y3 + h3),
            box(x3r, y3, x3r + w3, y3 + h3),
            box(x4, y4, x4 + w4, y4 + h4),
            box(x5, y5, x5 + w5, y5 + h5),
            box(x6, y6, x6 + w6, y6 + h6)  # box6
        ]

        logo_unscaled = cascaded_union(boxes)

        # write WWU
        # create W
        x_W = [-40.58, -13.7, 1.05, 16.86, 40.05, 68.51, 45.06, 29.78, 13.17, -11.33, -28.19, -43.21, -66.93]
        y_W = [0, 0, 78.26, 0, 0, 114, 114, 33.46, 114, 114, 33.46, 114, 114]
        W_coords = zip(x_W, y_W)
        W = Polygon(W_coords)

        # create U
        # ellipse w=82=2a, h=58=2b
        # parametrisierung x=a*cos(t), y=b*sin(t), t=0..2pi
        num = 20
        a = 41
        b = 29

        t = np.linspace(np.pi, 2 * np.pi, num)
        xb = a * np.cos(t)  # bottom coordinates
        yb = b * np.sin(t)

        # right box
        xr = [max(xb), max(xb) - 25]
        yr = [114 + min(yb), 114 + min(yb)]

        xt = (a - 25) * np.cos(t)  # top coordinates
        yt = (b - 20) * np.sin(t)
        # left box
        xl = [min(xb) + 25, min(xb)]
        yl = yr

        x = np.concatenate((xb, xr, xt[::-1], xl))
        y = np.concatenate((yb, yr, yt[::-1], yl))

        u_coord = zip(x, y)
        U = Polygon(u_coord)

        WWU_unscaled = cascaded_union([W, translate(W, 139), translate(U, 261, 29)])

        # create whole logo
        if self.text == 0:
            # no text
            # calculate scaling of logo and WWU for set height
            M = self.height / h  # scaling factor

            logo_complete = scale(logo_unscaled, M, M, origin=(0, 0))
        elif self.text == 1:
            # text right of logo
            # calculate scaling of logo and WWU for set height
            M = self.height / h  # scaling factor
            M2 = (y3 + h3) * M / 114

            logo_complete = cascaded_union([scale(logo_unscaled, M, M, origin=(0, 0)),
                                            translate(scale(WWU_unscaled, M2, M2, origin=(0, 0)),
                                                      (x1 + w) * M + 80 * M2)])
        else:
            # text under logo
            # calculate scaling of logo and WWU with sum equal to set height
            # WWU width = 368.93 = 369     *M2 == w
            # box width unscaled = w = 336
            M2 = w / 369.  # scale width of WWU to width of logo
            M = self.height / (h + 10 + 114)  # scaling factor height

            logo_complete_unscaled = cascaded_union(
                [scale(translate(WWU_unscaled, 67, 0), M2, M2, origin=(0, 0)), translate(logo_unscaled, 0, (114 + 10))])
            logo_complete = scale(logo_complete_unscaled, M, M, origin=(0, 0))

        return translate(logo_complete, *self.origin)


def _example():
    import gdsCAD.core
    from gdshelpers.geometry import convert_to_gdscad

    kit_logo = KITLogo([0, 0], 1)
    wwu_logo = WWULogo([0, 0], 1, 1)

    cell = gdsCAD.core.Cell('LOGOS')
    cell.add(convert_to_gdscad(kit_logo))
    cell.add(convert_to_gdscad(translate(wwu_logo.get_shapely_object(), 2.5)))
    cell.show()


if __name__ == '__main__':
    _example()

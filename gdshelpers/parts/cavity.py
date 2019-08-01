import numpy as np
from gdshelpers.parts.waveguide import Waveguide
from shapely.geometry import Point
from gdshelpers.parts.port import Port
import shapely.geometry
from gdshelpers.helpers import StandardLayers


class PhotonicCrystalCavity:
    """
    class to implement standard Photonic Crystal Cavity devices with GDS helpers
    see below for examples how to implement cavities with
    1. constant hole diameters/distances
    2. varying hole diameters/distances
    3. tapered waveguide width (set cavity length to - holediameter)
    """

    def __init__(self, origin, angle, width, lengthofcavity, numberofholes=14, holediameters=.5, holedistances=0.5,
                 tapermode=None, finalwidth=None, taperlength=None,
                 samplepoints=1000, holeparams=None, underetching=True, markers=True):
        """
        PhotonicCrystal Cavity

        :param origin: vector, Position of the center of the Photonic Crystal cavity
        :param angle: angle of the roation
        :param width: width of the waveguide
        :param lengthofcavity:  float, distance between the central two points, set to -1*holediameters for hole centered cavities
        :param numberofholes:  int, number of holes on each side
        :param holediameters: float or List of the diameters of the holes on each side. In case of linear increase use e.g. np.linespace
        :param holedistances: float or List of the distances of the holes on each side. In case of linear increase use e.g. np.linespace
        :param tapermode: None for constant widht, 'quadratic' for quadratic tapering
        :param finalwidth: width in the the center of the cavity
        :param taperlength: length over which the cavity will be tapered
        :param samplepoints: number of samplepoints to set the smoothness of the tapering
        """
        if holeparams:
            holetot2 = np.concatenate(
                [np.linspace(holeparams['mindia'], holeparams['maxdia'], holeparams['numholestap']),
                 np.linspace(holeparams['maxdia'], holeparams['maxdia'], holeparams['numholesmir'])])
            distot2 = np.concatenate(
                [np.linspace(holeparams['mindist'], holeparams['maxdist'], holeparams['numholestap']),
                 np.linspace(holeparams['maxdist'], holeparams['maxdist'], (holeparams['numholesmir'] - 1))])
            holediameters = holetot2
            holedistances = distot2
            numberofholes = holeparams['numholestap'] + holeparams['numholesmir']

        self.origin = origin
        self.allholes = list()
        self.width = width
        self.angle = angle
        self._center_portr = Port(origin, angle, self.width)
        self._center_portl = Port(origin, (angle + np.pi), self.width)

        self.widthdiff = finalwidth - width if finalwidth else 0
        self.tapermode = tapermode
        self.lenofcav = lengthofcavity
        if type(holedistances) is float:
            meanholed = holedistances
            holedistances = [holedistances] * (numberofholes - 1)
        else:
            meanholed = np.mean(holedistances)

        if type(holediameters) is float:
            holediameters = [holediameters] * numberofholes

        lenoffset = holediameters[0] + holediameters[-1]

        self.holediameters = holediameters
        self.holedistances = holedistances
        self.numberofholes = len(holediameters)
        self.devlen = lengthofcavity + 2 * ((self.numberofholes - 1) * meanholed) + lenoffset
        self.taperlength = taperlength if taperlength else self.devlen / 2
        self.samplepoints = samplepoints
        self.underetchspace = 10
        self.invertmarker = False
        self.markersize = 20
        self.markerdistancex = 100
        self.markerdistancey = 100

        self.layer_photonic = []
        self.layer_photonic_cavity = []
        self.layer_underetch = []
        self.layer_marker = []
        if len(holediameters) != len(holedistances) + 1:
            print('dimension of holediameters should be 1 more than holedistances!')
            np.append(holediameters, [holediameters[-1]])
        self._generate()
        if underetching:
            self.generate_underetch()
        if markers == True:
            self.generate_marker()
        if markers == 'inverse':
            self.invertmarker = True
            self.generate_marker()

    def _generate(self):
        if not self.tapermode:
            width_func = lambda x: self.width
            restlength = 0
        elif self.tapermode == 'quadratic':
            width_func = lambda x: (self.widthdiff) * ((1 - x) ** 2) + self.width
            restlength = self.devlen / 2 - self.taperlength

        wgcavl = Waveguide.make_at_port(self._center_portl)
        wgcavl.add_parameterized_path(path=lambda x: (self.taperlength * x, 0),
                                      width=width_func,
                                      sample_points=self.samplepoints, sample_distance=None)
        wgcavl.add_straight_segment(length=restlength)
        self.leftport = wgcavl.current_port
        wgcavr = Waveguide.make_at_port(self._center_portr)
        wgcavr.add_parameterized_path(path=lambda x: (self.taperlength * x, 0),
                                      width=width_func,
                                      sample_points=self.samplepoints, sample_distance=None)
        wgcavr.add_straight_segment(length=restlength)
        self.rightport = wgcavr.current_port
        positionl = [self.origin[0] - (self.lenofcav + self.holediameters[0]) / 2 * np.cos(self.angle),
                     self.origin[1] - (self.lenofcav + self.holediameters[0]) / 2 * np.sin(self.angle)]
        positionr = [self.origin[0] + (self.lenofcav + self.holediameters[0]) / 2 * np.cos(self.angle),
                     self.origin[1] + (self.lenofcav + self.holediameters[0]) / 2 * np.sin(self.angle)]
        wgcavl = wgcavl.get_shapely_object()
        wgcavr = wgcavr.get_shapely_object()
        pointsl = Point(positionl).buffer(distance=self.holediameters[0] / 2)
        wgcavl = wgcavl.difference(pointsl)
        pointsr = Point(positionr).buffer(distance=self.holediameters[0] / 2)
        self.allholes.append(pointsl)
        self.allholes.append(pointsr)
        wgcavr = wgcavr.difference(pointsr)

        for i in range(1, self.numberofholes - 1):
            positionl = [positionl[0] - self.holedistances[i] * np.cos(self.angle),
                         positionl[1] - self.holedistances[i] * np.sin(self.angle)]
            pointsl = Point(positionl).buffer(distance=self.holediameters[i + 1] / 2)
            self.allholes.append(pointsl)
            wgcavl = wgcavl.difference(pointsl)
            positionr = [positionr[0] + self.holedistances[i] * np.cos(self.angle),
                         positionr[1] + self.holedistances[i] * np.sin(self.angle)]
            pointsr = Point(positionr).buffer(distance=self.holediameters[i + 1] / 2)
            self.allholes.append(pointsr)
            wgcavr = wgcavr.difference(pointsr)

        self.layer_photonic_cavity.extend([wgcavl, wgcavr])

    def generate_underetch(self):
        or_r = self.devlen + self.origin[0]  # self.rightport.origin[0]
        or_l = -self.devlen + self.origin[0]  # self.leftport.origin[0]
        underetchbox = shapely.geometry.box(or_l - self.underetchspace,
                                            -(self.width + self.widthdiff + self.underetchspace) + self.origin[1],
                                            or_r + self.underetchspace,
                                            (self.width + self.widthdiff + self.underetchspace) + self.origin[1])

        self.layer_underetch.append((underetchbox))

    def generate_marker(self):
        sign = 1
        if self.invertmarker == True:
            sign = -1

        markerdistancex = sign * self.markerdistancex / 2
        markerdistancey = sign * self.markerdistancey / 2
        marker_tr = shapely.geometry.box(markerdistancex + self.origin[0] + self.markersize / 2,
                                         markerdistancey + self.origin[1] + self.markersize / 2,
                                         markerdistancex + self.origin[0] - self.markersize / 2,
                                         markerdistancey + self.origin[1] - self.markersize / 2)
        marker_tl = shapely.geometry.box(-markerdistancex + self.origin[0] + self.markersize / 2,
                                         markerdistancey + self.origin[1] + self.markersize / 2,
                                         -markerdistancex + self.origin[0] - self.markersize / 2,
                                         markerdistancey + self.origin[1] - self.markersize / 2)
        marker_b = shapely.geometry.box(self.origin[0] + self.markersize / 2,
                                        -markerdistancey + self.origin[1] + self.markersize / 2,
                                        self.origin[0] - self.markersize / 2,
                                        -markerdistancey + self.origin[1] - self.markersize / 2)

        self.layer_marker.extend([marker_tr, marker_tl, marker_b])

    def get_left_port(self):
        # somehow only works for tapered cavities...
        return self.leftport

    def get_right_port(self):
        # somehow only works for tapered cavities...
        return self.rightport

    def get_holes_list(self):
        # returns a list of all the holes as objects
        return self.allholes

    @classmethod
    def make_at_port(cls, port, **kwargs):
        cavityparameter = dict(kwargs)
        cavityparameter.__delitem__('angle')
        cavityparameter.__delitem__('origin')

        devlen = cavityparameter['lengthofcavity'] + 2 * (
                (cavityparameter['numberofholes'] - 1) * np.mean(cavityparameter['holedistances'])) + (
                     cavityparameter['holediameters']) + (cavityparameter['holediameters'])
        return cls(
            origin=[port.origin[0] + devlen / 2 * np.cos(port.angle), port.origin[1] + devlen / 2 * np.sin(port.angle)],
            angle=port.angle, **cavityparameter)


def main():
    import gdsCAD
    from gdshelpers.geometry import convert_to_gdscad

    devicename = 'Cavity'
    cavitiyparameter_const = {'origin': [0, 0], 'angle': 0, 'width': 0.726, 'lengthofcavity': 0.26, 'numberofholes': 17,
                              'holediameters': 0.416, 'holedistances': 0.53}
    cavitiyparameter_lin = {'origin': [100, 500], 'angle': 0, 'width': 0.726, 'lengthofcavity': 0.26,
                            'numberofholes': 17,
                            'holediameters': np.linspace(0.233, 0.416, 17),
                            'holedistances': np.linspace(0.53, 0.605, 16)}
    taperlength = 15 * 0.414
    cavitiyparameter_tap_width = {'origin': [-50, -30], 'angle': np.pi, 'width': 1.1, 'numberofholes': 25,
                                  'taperlength': taperlength,
                                  'lengthofcavity': -0.414, 'finalwidth': 1.55, 'tapermode': 'quadratic',
                                  'holediameters': 0.414,
                                  'holedistances': 0.620}
    holeparams_bg = {'mindia': 0.267, 'maxdia': 0.267, 'mindist': 0.512, 'maxdist': 0.512, 'numholestap': 1,
                     'numholesmir': 10}
    bandgapparameter = {'origin': [0, 0], 'angle': 0,
                        'width': 1.015, 'lengthofcavity': -0.512 / 2,
                        'holeparams': holeparams_bg}

    # pccav1 = PhotonicCrystalCavity(**cavitiyparameter_const)
    bandgap = PhotonicCrystalCavity(**bandgapparameter)

    port1 = Port(origin=[10, 10], angle=np.pi / 2, width=1)
    # cav2 = PhotonicCrystalCavity.make_at_port(port=port1, **cavitiyparameter_tap_width)
    pccav3 = PhotonicCrystalCavity(**cavitiyparameter_tap_width)
    wg = Waveguide.make_at_port(port1.inverted_direction)
    wg.add_straight_segment(length=5)

    cell = gdsCAD.core.Cell(devicename)
    # cell.add(convert_to_gdscad(pccav1.layer_photonic_cavity, layer=1))
    # cell.add(convert_to_gdscad(pccav2.layer_marker, layer=StandardLayers.lmarklayer))
    # cell.add(convert_to_gdscad(pccav2.layer_underetch, layer=StandardLayers.masklayer1))
    # cell.add(convert_to_gdscad(pccav2.layer_photonic_cavity, layer=StandardLayers.nanolayer))
    # cell.add(convert_to_gdscad(pccav3.layer_marker, layer=StandardLayers.lmarklayer))
    # cell.add(convert_to_gdscad(pccav3.layer_underetch, layer=StandardLayers.masklayer1))
    cell.add(convert_to_gdscad(bandgap.layer_underetch, layer=StandardLayers.masklayer1))
    cell.add(convert_to_gdscad(bandgap.layer_photonic_cavity, layer=StandardLayers.nanolayer))

    # cell.add(convert_to_gdscad(pccav2.layer_photonic_cavity, layer=1))
    # cell.add(convert_to_gdscad(pccav3.get_holes_list()))
    holes = pccav3.get_holes_list()

    layout = gdsCAD.core.Layout()
    layout.add(cell=cell)
    layout.show()


if __name__ == '__main__':
    main()

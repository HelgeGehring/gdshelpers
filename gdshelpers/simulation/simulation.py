import numpy as np
import meep as mp
import matplotlib.pyplot as plt
import shapely.geometry
import shapely.prepared
import shapely.ops

from gdshelpers.geometry.shapely_adapter import geometric_union

import warnings

warnings.warn('\n'
              'This simulation-module is currently under development.\n'
              'Therefore, the API and the interpretation of the commands is subject to change without prior notice.\n'
              'Feedback is highly appreciated.\n')


class Simulation:
    def __init__(self, resolution, padding=(4, 4, 1), pml_thickness=None, reduce_to_2d=False):
        self.structures = []
        self.resolution = resolution
        self.padding = np.array(padding)
        self.pml_thickness = pml_thickness if pml_thickness is not None else 4 / resolution
        self.reduce_to_2d = reduce_to_2d

        self.sources = []
        self.sim = None
        self.center = None
        self.size = None

    def add_structure(self, structure=(), extra_structures=(), material=None, refractive_index=None, z_min=None,
                      z_max=None):
        """
        Adds structures to the simulation. The refractive index of the structure with is added first for a certain
        location will be used for the simulation.

        Adding a substrate/cladding is also possible by leaving structure and extra_structure empty.
        In this case the whole area will be filled with the given refractive index/material.

        :param structure: The structure which is added to the simulation. The extends of the simulation are calculated
            by the size of these structures.
        :param extra_structures: Additional structures which are added to the simulation. These will not be taken into
            account for calculating the extends of the simulation. This is e.g. useful for waveguides which should go
            into the PML
        :param material:
            Meep-material for the structures
        :param refractive_index:
            Refractive index of the structures
        :param z_min:
            Starting z-position for the layer-structure
        :param z_max:
            Ending z-position for the layer-structure
        """
        if material is None and refractive_index is None:
            raise ValueError('Either a material or a refractive index must be provided')
        self.structures.append(
            dict(structure=structure, extra_structures=extra_structures,
                 material=material or mp.Medium(index=refractive_index),
                 refractive_index=refractive_index, z_min=z_min, z_max=z_max))

    def init_sim(self, use_material=False, oversample_factor=1, **kwargs):
        z_min, z_max = [np.min([structure[z_] for structure in self.structures]) for z_ in ['z_min', 'z_max']]

        bounds = geometric_union((geometric_union(x['structure']) for x in self.structures)).bounds
        size = np.array((bounds[2] - bounds[0], bounds[3] - bounds[1], (z_max - z_min)))
        self.center = [(bounds[2] + bounds[0]) / 2, (bounds[3] + bounds[1]) / 2, (z_max + z_min) / 2]
        self.size = size + self.padding + self.pml_thickness * 2
        if self.reduce_to_2d:
            size[2] = self.center[2] = self.size[2] = 0

        def epsilon_function():
            from shapely.vectorized import contains
            coords = [np.linspace(self.center[i] - self.size[i] / 2, self.center[i] + self.size[i] / 2,
                                  int(self.size[i] * self.resolution * oversample_factor)) for i in
                      range(2 if self.reduce_to_2d else 3)]
            xyz = np.meshgrid(*coords, indexing='ij')
            eps = np.full([len(c) for c in coords], 1)

            for structure in reversed(self.structures):
                if structure['refractive_index'] is None:
                    raise RuntimeError('Either supply an refractive index for each structure or use materials')

                structures = structure['structure'] + structure['extra_structures']
                inside = contains(geometric_union(structures), xyz[0], xyz[1]) if structures else True
                if not self.reduce_to_2d:
                    inside *= (xyz[2] >= structure['z_min']) * (xyz[2] <= structure['z_max'])
                eps = np.where(inside, structure['refractive_index'] ** 2, eps)
            return eps

        prepared_structures = [dict(**structure, prepared_structure=shapely.prepared.prep(
            geometric_union(structure['structure'] + structure['extra_structures']))) for structure in self.structures]

        def material_function(vec):
            for structure in reversed(prepared_structures):
                if structure['prepared_structure'].contains(shapely.geometry.Point(vec.x, vec.y)):
                    return structure['material']
            return mp.air

        self.sim = mp.Simulation(mp.Vector3(*self.size), self.resolution,
                                 material_function=material_function if use_material else None,
                                 default_material=epsilon_function() if not use_material else None,
                                 geometry_center=mp.Vector3(*self.center),
                                 sources=self.sources,
                                 boundary_layers=[mp.PML(self.pml_thickness)], **kwargs)
        self.sim.init_sim()

    def plot(self, fields):
        self.sim.plot2D(fields=fields, field_parameters={'alpha': 0.5, 'cmap': 'RdBu', 'interpolation': 'none'},
                        boundary_parameters={'hatch': 'o', 'linewidth': 1.5, 'facecolor': 'y', 'edgecolor': 'b',
                                             'alpha': 0.3})
        plt.xlabel(r'$x$ [$\mathrm{\mu m}$]')
        plt.ylabel(r'$y$ [$\mathrm{\mu m}$]')
        plt.savefig('plot.pdf', transparent=True, bbox_inches='tight')
        plt.show()

    def run(self, *args, **kwargs):
        self.sim.run(*args, **kwargs)

    def add_source(self, src, component, port, z=None):
        source = mp.Source(src, component, mp.Vector3(*port.origin, z))
        self.sources.append(source)
        return source

    def add_eigenmode_source(self, src, port, eig_band=1, z=None, height=None):
        size = [0, port.total_width * 2] if port.angle % np.pi < np.pi / 4 else [port.total_width * 2, 0]
        source = mp.EigenModeSource(src, mp.Vector3(*port.origin, z), size=mp.Vector3(*size, height), eig_band=eig_band)
        self.sources.append(source)
        return source

    def add_eigenmode_monitor(self, port, wavelength, fwidth, nfreq, z=None, height=None):
        size = [0, port.total_width * 2] if port.angle % np.pi < np.pi / 4 else [port.total_width * 2, 0]
        monitor = self.sim.add_mode_monitor(1 / wavelength, fwidth, nfreq,
                                            mp.FluxRegion(mp.Vector3(*port.origin, z), size=mp.Vector3(*size, height)))
        return monitor

    def get_eigenmode_coeffs(self, monitor, bands):
        return self.sim.get_eigenmode_coefficients(monitor, bands)


def example_mmi():
    from gdshelpers.parts.splitter import DirectionalCoupler, MMI, Splitter
    from gdshelpers.parts.waveguide import Waveguide

    # mp.quiet(True)

    # mmi = DirectionalCoupler((0, 0), np.pi / 2, 1.3, length=52, gap=.45, bend_radius=20, bend_angle=np.pi / 10)
    mmi = MMI((0, 0), 0, 1.3, length=42, width=7.7, num_inputs=2, num_outputs=2)  # , taper_width=3)
    # mmi = Splitter((0, 0), 0, wg_width_root=1.15, sep=5, total_length=40)
    mmi.input_ports = [mmi.input_ports[0]]
    mmi.output_ports = [mmi.left_branch_port, mmi.right_branch_port]

    wgs = [Waveguide.make_at_port(port).add_straight_segment(4) for port in [mmi.input_ports[0]] + mmi.output_ports]

    sim = Simulation(resolution=15, reduce_to_2d=True)
    sim.add_structure([mmi], wgs, mp.Medium(index=1.666), refractive_index=1.666, z_min=0, z_max=.33)

    source = sim.add_eigenmode_source(mp.ContinuousSource(wavelength=1.55, width=2),
                                      mmi.input_ports[0].longitudinal_offset(1), z=0.33 / 2, height=1, eig_band=2)

    sim.init_sim(oversample_factor=1)
    # plt.imshow(sim.sim.get_epsilon().T)
    # plt.show()
    # sim.sim.plot3D()

    monitors_out = [
        sim.add_eigenmode_monitor(mmi.output_ports[i].longitudinal_offset(1), 1.55, 2, 1, z=0.33 / 2, height=1) for i in
        range(2)]

    sim.plot(mp.Hz)

    sim.run(until=150)

    # plt.imshow(sim.sim.get_epsilon().T)
    # plt.imshow(sim.sim.get_tot_pwr().T, alpha=.5)
    # plt.show()

    sim.plot(mp.Hz)

    phase_difference = np.angle(sim.get_eigenmode_coeffs(monitors_out[0], [2]).alpha[0, 0, 0] /
                                sim.get_eigenmode_coeffs(monitors_out[1], [2]).alpha[0, 0, 0]) / np.pi

    transmissions = [
        np.abs(sim.get_eigenmode_coeffs(monitors_out[i], [2]).alpha[0, 0, 0]) ** 2 / source.eig_power(1 / 1.55) for i in
        range(2)]

    print('phase difference between outputs: {:.3f}π'.format(phase_difference))

    print('transmission to monitor 1: {:.3f}'.format(transmissions[0]))
    print('transmission to monitor 2: {:.3f}'.format(transmissions[1]))


def example_cavity():
    from gdshelpers.parts.waveguide import Waveguide
    from shapely.geometry import Point

    wg = Waveguide((-6, 0), 0, 1.2)
    start_port = wg.current_port
    wg.add_straight_segment(12)
    wgs = [Waveguide.make_at_port(port).add_straight_segment(4) for port in
           [start_port.inverted_direction, wg.current_port]]
    holes = geometric_union(
        [Point(x * sign, 0).buffer(.36) for x in [1.4 / 2 + x * 1 for x in range(3)] for sign in [-1, 1]])

    sim = Simulation(resolution=20, reduce_to_2d=True, padding=2)
    sim.add_structure([wg.get_shapely_object().difference(holes)], wgs, mp.Medium(epsilon=13),
                      refractive_index=np.sqrt(13), z_min=0, z_max=.33)

    sim.add_eigenmode_source(mp.GaussianSource(wavelength=1 / .25, fwidth=.35), start_port, z=0.33 / 2, height=1,
                             eig_band=2)

    sim.init_sim(oversample_factor=10)
    monitors_out = [sim.add_eigenmode_monitor(port.longitudinal_offset(1), 1 / .25, .2, 500, z=0.33 / 2, height=1) for
                    port in [start_port, wg.current_port.inverted_direction]]

    sim.plot(mp.Hz)
    sim.run(until=1500)
    sim.plot(mp.Hz)

    frequencies = np.array(mp.get_eigenmode_freqs(monitors_out[0]))
    transmissions = [np.abs(sim.get_eigenmode_coeffs(monitors_out[i], [2]).alpha[0, :, 0]) ** 2 for i in range(2)]

    plt.plot(frequencies, transmissions[1] / transmissions[0])
    plt.show()


def example_cavity_harminv():
    from gdshelpers.parts.waveguide import Waveguide
    from shapely.geometry import Point

    wg = Waveguide((-6, 0), 0, 1.2)
    start_port = wg.current_port
    wg.add_straight_segment(6)
    center_port = wg.current_port
    wg.add_straight_segment(6)
    wgs = [Waveguide.make_at_port(port).add_straight_segment(4) for port in
           [start_port.inverted_direction, wg.current_port]]
    holes = geometric_union(
        [Point(x * sign, 0).buffer(.36) for x in [1.4 / 2 + x * 1 for x in range(3)] for sign in [-1, 1]])

    sim = Simulation(resolution=20, reduce_to_2d=True, padding=2, pml_thickness=1)
    sim.add_structure([wg.get_shapely_object().difference(holes)], wgs, mp.Medium(epsilon=13),
                      refractive_index=np.sqrt(13), z_min=0, z_max=.33)

    sim.add_source(mp.GaussianSource(wavelength=1 / .25, fwidth=.2), mp.Hz, center_port, z=0)

    sim.init_sim()

    sim.plot(fields=mp.Hz)

    mp.simulation.display_run_data = lambda *args, **kwargs: None
    harminv = mp.Harminv(mp.Hz, mp.Vector3(), .25, .2)

    sim.run(mp.after_sources(harminv._collect_harminv()(harminv.c, harminv.pt)), until_after_sources=300)
    sim.plot(fields=mp.Hz)

    print(harminv._analyze_harminv(sim.sim, 100))


if __name__ == '__main__':
    example_mmi()

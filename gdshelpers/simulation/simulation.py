import numpy as np
import meep as mp
import matplotlib.pyplot as plt

from gdshelpers.geometry.shapely_adapter import geometric_union, fracture_intelligently, \
    shapely_collection_to_basic_objs

import warnings

warnings.warn('\n'
              'This simulation-module is currently under development.\n'
              'Therefore, the API and the interpretation of the commands is subject to change without prior notice.\n'
              'Feedback is highly appreciated.\n')


class Simulation:
    def __init__(self, resolution, padding=(4, 4, 1), pml_thickness=None, reduce_to_2d=False):
        """
        Class for simulating planar circuitry. starting with an empty simulation, the user adds structures and
        sources/monitors, initializes the simulation itself afterwards and finally runs it.

        :param resolution: Resolution used for the simulations. Defined as cells per unit.
        :param padding: Distance between the structure and the PML
        :param pml_thickness: Thickness of the PML, can be None for no PML, a number for the same thickness in all
            directions or an array with three elements with the thicknesses in x-/y- and z-direction.
        :param reduce_to_2d: Defines if the final simulation should be reduced to a 2D-simulation.
        """
        self.structures = []
        self.resolution = resolution
        self.padding = np.array(padding)
        self.pml_thickness = pml_thickness if pml_thickness is not None else 4 / resolution
        self.reduce_to_2d = reduce_to_2d

        self.sources = []
        self.sim = None
        self.center = None
        self.size = None

    def add_structure(self, structure=(), extra_structures=(), material=None, z_min=None, z_max=None):
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
        :param z_min:
            Starting z-position for the layer-structure
        :param z_max:
            Ending z-position for the layer-structure
        """
        self.structures.append(
            dict(structure=structure, extra_structures=extra_structures, material=material, z_min=z_min, z_max=z_max))

    def init_sim(self, **kwargs):
        """
        Initializes the simulation. This has to be done after adding all structures in order to correctly determine the
        size of the simulation.

        :param kwargs: Parameters which are directly passed to Meep
        """
        z_min = np.min([structure['z_min'] for structure in self.structures if structure['structure']])
        z_max = np.max([structure['z_max'] for structure in self.structures if structure['structure']])

        bounds = geometric_union((geometric_union(x['structure']) for x in self.structures)).bounds
        size = np.array((bounds[2] - bounds[0], bounds[3] - bounds[1], (z_max - z_min)))
        self.center = np.round([(bounds[2] + bounds[0]) / 2, (bounds[3] + bounds[1]) / 2, (z_max + z_min) / 2])
        self.size = np.ceil(size + self.padding * 2 + self.pml_thickness * 2)
        if self.reduce_to_2d:
            self.center[2] = self.size[2] = 0

        structures = []
        for structure in self.structures:
            polygon = geometric_union(structure['structure'] + structure['extra_structures']) \
                .buffer(np.finfo(np.float32).eps, resolution=0).simplify(np.finfo(np.float32).eps)
            objs = shapely_collection_to_basic_objs(polygon)

            for obj in objs:
                if obj.is_empty:
                    continue
                for polygon in fracture_intelligently(obj, np.inf, np.inf):
                    structures += [
                        mp.Prism(vertices=[
                            mp.Vector3(*point, 0 if self.reduce_to_2d else structure['z_min'])
                            for point in polygon.exterior.coords[:-1]],
                            material=structure['material'], height=structure['z_max'] - structure['z_min'])]

        self.sim = mp.Simulation(mp.Vector3(*self.size), self.resolution,
                                 geometry=structures,
                                 geometry_center=mp.Vector3(*self.center),
                                 sources=self.sources,
                                 boundary_layers=[mp.PML(self.pml_thickness)], **kwargs)
        self.sim.init_sim()

    def plot(self, fields):
        self.sim.plot2D(fields=fields, field_parameters={'alpha': 0.5, 'cmap': 'RdBu', 'interpolation': 'none'},
                        boundary_parameters={'hatch': 'o', 'linewidth': 1.5, 'facecolor': 'y', 'edgecolor': 'b',
                                             'alpha': 0.3}, frequency=0)
        plt.xlabel(r'$x$ [$\mathrm{\mu m}$]')
        plt.ylabel(r'$y$ [$\mathrm{\mu m}$]')
        plt.savefig('plot.pdf', transparent=True, bbox_inches='tight')
        plt.show()

    def run(self, *args, **kwargs):
        """
        Just forwards the parameters to Meep's run-function

        :param args:
        :param kwargs:
        :return:
        """
        self.sim.run(*args, **kwargs)

    def add_source(self, src, component, port, z=None):
        """
        Adds a point source at a given port.

        :param src: Meep-Source (e.g. GaussianSource or ContinuousSource)
        :param component: The component which should be excited
        :param port: Port at which the point source is added
        :param z: Z-position of the source
        :return: Added Meep-Source
        """
        source = mp.Source(src, component, mp.Vector3(*port.origin, z))
        self.sources.append(source)
        return source

    def add_eigenmode_source(self, src, port, eig_band=1, eig_parity=mp.NO_PARITY, z=None, height=None):
        """
        Adds an eigenmode source at the given port.

        :param src: Meep-Source (e.g. GaussianSource or ContinuousSource)
        :param port: Port at which the source is added
        :param eig_band: Number of the excited mode. The mode with the highest eigenvalue has the number 1
        :param eig_parity: Parity of the eigenmodes
        :param z: Z-position of the source
        :param height: Height of the area for calculating the eigenmode
        :return: Added Meep-Source
        """

        size = [0, port.total_width * 2] if port.angle % np.pi < np.pi / 4 else [port.total_width * 2, 0]
        source = mp.EigenModeSource(src, mp.Vector3(*port.origin, z), size=mp.Vector3(*size, height), eig_band=eig_band, eig_parity=eig_parity)
        self.sources.append(source)
        return source

    def add_eigenmode_monitor(self, port, wavelength, fwidth, nfreq, z=None, height=None):
        """
        Adds an eigenmode monitor at the given port.

        :param port: Port at which the monitor is added
        :param wavelength: Center wavelength of the monitored spectrum
        :param fwidth: Width of the monitored spectrum
        :param nfreq: Number of monitored wavelengths
        :param z: Z-position of the monitor
        :param height: Height of the area for calculating the eigenmode
        :return: Added Meep-Monitor
        """

        size = [0, port.total_width * 2] if port.angle % np.pi < np.pi / 4 else [port.total_width * 2, 0]
        monitor = self.sim.add_mode_monitor(1 / wavelength, fwidth, nfreq,
                                            mp.FluxRegion(mp.Vector3(*port.origin, z), size=mp.Vector3(*size, height)))
        return monitor

    def get_eigenmode_coefficients(self, monitor, bands, eig_parity=mp.NO_PARITY):
        return self.sim.get_eigenmode_coefficients(monitor, bands, eig_parity=eig_parity)


def example_mmi():
    from gdshelpers.parts.splitter import MMI
    from gdshelpers.parts.waveguide import Waveguide

    # mp.quiet(True)

    mmi = MMI((0, 0), 0, 1.3, length=42, width=7.7, num_inputs=2, num_outputs=2)  # , taper_width=3)
    # mmi = Splitter((0, 0), 0, wg_width_root=1.15, sep=5, total_length=40)
    mmi.input_ports = [mmi.input_ports[0]]
    mmi.output_ports = [mmi.left_branch_port, mmi.right_branch_port]
    wgs = [Waveguide.make_at_port(port).add_straight_segment(4) for port in [mmi.input_ports[0]] + mmi.output_ports]

    sim = Simulation(resolution=15, reduce_to_2d=True)
    sim.add_structure([mmi], wgs, mp.Medium(index=1.666), z_min=0, z_max=.33)

    source = sim.add_eigenmode_source(mp.GaussianSource(wavelength=1.55, width=2),
                                      mmi.input_ports[0].longitudinal_offset(1), z=0.33 / 2, height=1, eig_band=2)

    sim.init_sim()
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

    phase_difference = np.angle(sim.get_eigenmode_coefficients(monitors_out[0], [2]).alpha[0, 0, 0] /
                                sim.get_eigenmode_coefficients(monitors_out[1], [2]).alpha[0, 0, 0]) / np.pi

    transmissions = [
        np.abs(sim.get_eigenmode_coefficients(monitors_out[i], [2]).alpha[0, 0, 0]) ** 2 / source.eig_power(1 / 1.55)
        for i in
        range(2)]

    print('phase difference between outputs: {:.3f}π'.format(phase_difference))

    print('transmission to monitor 1: {:.3f}'.format(transmissions[0]))
    print('transmission to monitor 2: {:.3f}'.format(transmissions[1]))


def example_directional_coupler():
    from gdshelpers.parts.splitter import DirectionalCoupler
    from gdshelpers.parts.waveguide import Waveguide

    # mp.quiet(True)

    splitter = DirectionalCoupler((0, 0), 0, wg_width=1., length=20, gap=.33, bend_radius=20, bend_angle=np.pi / 10)
    wgs = [Waveguide.make_at_port(port).add_straight_segment(4) for port in splitter.left_ports + splitter.right_ports]

    sim = Simulation(resolution=25, reduce_to_2d=True, padding=2, pml_thickness=.5)
    # Simplify splitter as the bend has quite a lot of points which slows subpixel averaging down
    sim.add_structure([splitter.get_shapely_object().simplify(.05)], wgs, mp.Medium(index=1.666), z_min=0, z_max=.33)
    # GaussianSource or ContinousSource
    source = sim.add_eigenmode_source(mp.GaussianSource(wavelength=1.55, width=2),
                                      splitter.left_ports[0].longitudinal_offset(1), z=0.33 / 2, height=1, eig_band=2)
    sim.init_sim()

    monitors_out = [
        sim.add_eigenmode_monitor(splitter.right_ports[i].longitudinal_offset(1), 1.55, 2, 1, z=0.33 / 2, height=1) for
        i in range(2)]

    sim.plot(mp.Hz)

    sim.run(until=200)

    sim.plot(mp.Hz)

    phase_difference = np.angle(sim.get_eigenmode_coefficients(monitors_out[0], [2]).alpha[0, 0, 0] /
                                sim.get_eigenmode_coefficients(monitors_out[1], [2]).alpha[0, 0, 0]) / np.pi

    transmissions = [
        np.abs(sim.get_eigenmode_coefficients(monitors_out[i], [2]).alpha[0, 0, 0]) ** 2 / source.eig_power(1 / 1.55)
        for i in range(2)]
    print('phase difference between outputs: {:.3f}π'.format(phase_difference))
    print('transmission to monitor 1: {:.3f}'.format(transmissions[0]))
    print('transmission to monitor 2: {:.3f}'.format(transmissions[1]))


def example_bend():
    from gdshelpers.parts.waveguide import Waveguide

    bend = Waveguide((0, 0), 0, width=1)
    bend.add_bend(angle=np.pi / 2, radius=20, n_points=30)
    wgs = [Waveguide.make_at_port(port).add_straight_segment(4) for port in [bend.in_port, bend.current_port]]

    sim = Simulation(resolution=25, reduce_to_2d=True, padding=2, pml_thickness=.5)
    sim.add_structure([bend], wgs, mp.Medium(index=1.666), z_min=0, z_max=.33)
    # GaussianSource or ContinousSource
    source = sim.add_eigenmode_source(mp.GaussianSource(wavelength=1.55, width=2),
                                      bend.in_port.longitudinal_offset(1), z=0.33 / 2, height=1, eig_band=2)
    sim.init_sim(subpixel_maxeval=0)  # subpixel_maxeval=0 for quick testing
    monitor_out = sim.add_eigenmode_monitor(bend.current_port.longitudinal_offset(1), 1.55, 2, 1, z=0.33 / 2, height=1)

    # sim.plot(mp.Hz)
    sim.run(until=150)
    sim.plot(mp.Hz)

    transmission = np.abs(sim.get_eigenmode_coefficients(monitor_out, [2]).alpha[0, 0, 0]) ** 2 / source.eig_power(
        1 / 1.55)
    print('transmission to monitor 1: {:.3f}'.format(transmission))


def example_bend_coupling():
    from gdshelpers.parts.waveguide import Waveguide

    waveguide_straight = Waveguide((0, 0), 0, width=1)
    waveguide_straight.add_straight_segment(5)
    bend_port = waveguide_straight.current_port.parallel_offset(1.1)
    waveguides_bend_1 = Waveguide.make_at_port(bend_port)
    waveguides_bend_1.add_bend(angle=np.pi / 2, radius=15, n_points=30)
    waveguides_bend_2 = Waveguide.make_at_port(bend_port.inverted_direction)
    waveguides_bend_2.add_bend(angle=-np.pi / 5, radius=15, n_points=20)
    waveguide_straight.add_straight_segment(5)

    wgs = [Waveguide.make_at_port(port).add_straight_segment(40) for port in
           [waveguide_straight.in_port, waveguide_straight.current_port,
            waveguides_bend_1.current_port, waveguides_bend_2.current_port]]

    sim = Simulation(resolution=20, reduce_to_2d=True, padding=2, pml_thickness=.5)
    sim.add_structure([waveguide_straight, waveguides_bend_1], wgs + [waveguides_bend_2],
                      mp.Medium(index=1.666), z_min=0, z_max=.33)
    # GaussianSource or ContinousSource
    source = sim.add_eigenmode_source(mp.ContinuousSource(wavelength=1.55, width=2),
                                      waveguide_straight.in_port.longitudinal_offset(1), z=0.33 / 2, height=1,
                                      eig_band=2)
    sim.init_sim(subpixel_maxeval=0)  # subpixel_maxeval=0 for quick testing
    monitors_out = [sim.add_eigenmode_monitor(port, 1.55, 2, 1, z=0.33 / 2, height=1) for port in
                    [waveguide_straight.current_port, waveguides_bend_1.current_port]]

    # sim.plot(mp.Hz)
    sim.run(until=150)
    sim.plot(mp.Hz)

    transmissions = [
        np.abs(sim.get_eigenmode_coefficients(monitors_out[i], [2]).alpha[0, 0, 0]) ** 2 / source.eig_power(1 / 1.55)
        for i in range(2)]
    print('transmission in bus waveguide: {:.3f}'.format(transmissions[0]))
    print('transmission to bent waveguide: {:.3f}'.format(transmissions[1]))


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
                      z_min=0, z_max=.33)

    sim.add_eigenmode_source(mp.GaussianSource(wavelength=1 / .25, fwidth=.35), start_port, z=0.33 / 2, height=1,
                             eig_band=2)

    sim.init_sim()
    monitors_out = [sim.add_eigenmode_monitor(port.longitudinal_offset(1), 1 / .25, .2, 500, z=0.33 / 2, height=1) for
                    port in [start_port, wg.current_port.inverted_direction]]

    sim.plot(mp.Hz)
    sim.run(until=1500)
    sim.plot(mp.Hz)

    frequencies = np.array(mp.get_eigenmode_freqs(monitors_out[0]))
    transmissions = [np.abs(sim.get_eigenmode_coefficients(monitors_out[i], [2]).alpha[0, :, 0]) ** 2 for i in range(2)]

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
                      z_min=0, z_max=.33)

    sim.add_source(mp.GaussianSource(wavelength=1 / .25, fwidth=.2), mp.Hz, center_port, z=0)

    sim.init_sim()

    sim.plot(fields=mp.Hz)

    mp.simulation.display_run_data = lambda *args, **kwargs: None
    harminv = mp.Harminv(mp.Hz, mp.Vector3(), .25, .2)

    sim.run(mp.after_sources(harminv._collect_harminv()(harminv.c, harminv.pt)), until_after_sources=300)
    sim.plot(fields=mp.Hz)

    print(harminv._analyze_harminv(sim.sim, 100))


if __name__ == '__main__':
    example_bend_coupling()

import numpy as np
from astropy import units as u
from elisa.binary_system import utils as butils

from elisa.base.container import StarContainer
from elisa.binary_system.container import OrbitalPositionContainer
from elisa.const import BINARY_POSITION_PLACEHOLDER

from elisa import utils, const, graphics, units


class Plot(object):
    """
    universal plot interface for binary system class, more detailed documentation for each value of descriptor is
    available in graphics library

                        `orbit` - plots orbit in orbital plane
                        `equipotential` - plots crossections of surface Hill planes in xy,yz,zx planes
                        `mesh` - plot surface points
                        `surface` - plot stellar surfaces
    :return:
    """

    def __init__(self, instance):
        self._self = instance

    def orbit(self, **kwargs):
        """
        Function for quick 2D plot of the orbital motion in the orbital plane.

        :param kwargs:
        :**kwargs options**:
            * **start_phase** * -- float; starting phase for the plot
            * **stop_phase** * -- float; finishing phase for the plot
            * **number_of_points** * -- int; number of points in the plot
            * **axis_units** * -- astropy.unit or 'str'; specifying axis unit, use astropy units or `dimensionless` or
            `SMA` (semi-major axis) units for axis scale
            * **frame_of_reference** * -- str; `barycentric` or `primary`
        :return:
        """
        all_kwargs = ['start_phase', 'stop_phase', 'number_of_points', 'axis_units', 'frame_of_reference']
        utils.invalid_kwarg_checker(kwargs, all_kwargs, self._self)

        start_phase = kwargs.get('start_phase', 0.0)
        stop_phase = kwargs.get('stop_phase', 1.0)
        number_of_points = kwargs.get('number_of_points', 300)

        kwargs['axis_units'] = kwargs.get('axis_units', u.solRad)
        kwargs['frame_of_reference'] = kwargs.get('frame_of_reference', 'primary')

        if kwargs['axis_units'] == 'dimensionless' or 'SMA':
            kwargs['axis_units'] = u.dimensionless_unscaled

        # orbit calculation for given phases
        phases = np.linspace(start_phase, stop_phase, number_of_points)
        ellipse = self._self.orbit.orbital_motion(phase=phases)
        # if axis are without unit a = 1
        if kwargs['axis_units'] != u.dimensionless_unscaled:
            a = self._self.semi_major_axis * units.DISTANCE_UNIT.to(kwargs['axis_units'])
            radius = a * ellipse[:, 0]
        else:
            radius = ellipse[:, 0]
        azimuth = ellipse[:, 1]
        x, y = utils.polar_to_cartesian(radius=radius, phi=azimuth - const.PI / 2.0)
        if kwargs['frame_of_reference'] == 'barycentric':
            kwargs['x1_data'] = - self._self.mass_ratio * x / (1 + self._self.mass_ratio)
            kwargs['y1_data'] = - self._self.mass_ratio * y / (1 + self._self.mass_ratio)
            kwargs['x2_data'] = x / (1 + self._self.mass_ratio)
            kwargs['y2_data'] = y / (1 + self._self.mass_ratio)
        elif kwargs['frame_of_reference'] == 'primary':
            kwargs['x_data'], kwargs['y_data'] = x, y
        graphics.orbit(**kwargs)

    def equipotential(self, **kwargs):
        """
        Function for quick 2D plot of equipotential cross-section.
        :param kwargs:
        :**kwargs options**:
            * **plane** * -- string; (`xy`, `yz` or `xz`) specifying what plane cross-section to display default is `xy`
            * **phase** * -- float; phase at which to plot cross-section
        """
        all_kwargs = ['plane', 'phase']
        utils.invalid_kwarg_checker(kwargs, all_kwargs, self.equipotential)

        kwargs['phase'] = kwargs.get('phase', 0.0)
        kwargs['plane'] = kwargs.get('plane', 'xy')

        # relative distance between components (a = 1)
        if utils.is_plane(kwargs['plane'], 'xy') or utils.is_plane(
                kwargs['plane'], 'yz') or utils.is_plane(kwargs['plane'], 'zx'):
            components_distance = self._self.orbit.orbital_motion(phase=kwargs['phase'])[0][0]
            points_primary, points_secondary = \
                self._self.compute_equipotential_boundary(components_distance=components_distance,
                                                          plane=kwargs['plane'])
        else:
            raise ValueError('Invalid choice of crossection plane, use only: `xy`, `yz`, `zx`.')

        kwargs['points_primary'] = points_primary
        kwargs['points_secondary'] = points_secondary

        graphics.equipotential(**kwargs)

    def mesh(self, **kwargs):
        """
        Function plots 3D scatter plot of the surface points

        :param kwargs:
        :**kwargs options**:
            * **phase** * -- float; phase at which to construct plot
            * **components_to_plot** * -- str; component to plot `primary`, `secondary` or `both`(default)
            * **plot_axis** * -- bool; switch the plot axis on/off
            * **inclination** * -- float; elevation of the camera (in degrees)
            * **azimuth** * -- float; azimuth of the camera (in degrees)
        :return:
        """
        all_kwargs = ['phase', 'components_to_plot', 'plot_axis', 'inclination', 'azimuth']
        utils.invalid_kwarg_checker(kwargs, all_kwargs, self.mesh)

        kwargs['phase'] = kwargs.get('phase', 0)
        kwargs['components_to_plot'] = kwargs.get('components_to_plot', 'both')
        kwargs['plot_axis'] = kwargs.get('plot_axis', True)
        kwargs['inclination'] = kwargs.get('inclination', np.degrees(self._self.inclination))

        components_distance, azim = self._self.orbit.orbital_motion(phase=kwargs['phase'])[0][:2]
        kwargs['azimuth'] = kwargs.get('azimuth', np.degrees(azim) - 90)

        orbital_position_container = OrbitalPositionContainer(
            primary=StarContainer.from_properties_container(self._self.primary.to_properties_container()),
            secondary=StarContainer.from_properties_container(self._self.secondary.to_properties_container()),
            position=BINARY_POSITION_PLACEHOLDER(*(0, 1.0, 0.0, 0.0, 0.0)),
            **self._self.properties_serializer()
        )
        orbital_position_container.build_mesh(components_distance=components_distance)
        if kwargs['components_to_plot'] in ['primary', 'both']:
            kwargs['points_primary'], _ = orbital_position_container.primary.get_flatten_points_map()

        if kwargs['components_to_plot'] in ['secondary', 'both']:
            kwargs['points_secondary'], _ = orbital_position_container.secondary.get_flatten_points_map()

        graphics.binary_mesh(**kwargs)

    def wireframe(self, **kwargs):
        """
        Function displays wireframe model of the stellar surface

        :param kwargs:
        :**kwargs options**:
            * **phase** * -- float; phase at which to construct plot
            * **components_to_plot** * -- str; component to plot `primary`, `secondary` or `both`(default)
            * **plot_axis** * -- bool; switch the plot axis on/off
            * **inclination** * -- float; elevation of the camera (in degrees)
            * **azimuth** * -- float; azimuth of the camera (in degrees)
        :return:
        """
        all_kwargs = ['phase', 'components_to_plot', 'plot_axis', 'inclination', 'azimuth']
        utils.invalid_kwarg_checker(kwargs, all_kwargs, self.wireframe)

        kwargs['phase'] = kwargs.get('phase', 0)
        kwargs['components_to_plot'] = kwargs.get('components_to_plot', 'both')
        kwargs['plot_axis'] = kwargs.get('plot_axis', True)
        kwargs['inclination'] = kwargs.get('inclination', np.degrees(self._self.inclination))

        components_distance, azim = self._self.orbit.orbital_motion(phase=kwargs['phase'])[0][:2]
        kwargs['azimuth'] = kwargs.get('azimuth', np.degrees(azim) - 90)

        orbital_position_container = OrbitalPositionContainer(
            primary=StarContainer.from_properties_container(self._self.primary.to_properties_container()),
            secondary=StarContainer.from_properties_container(self._self.secondary.to_properties_container()),
            position=BINARY_POSITION_PLACEHOLDER(*(0, 1.0, 0.0, 0.0, 0.0)),
            **self._self.properties_serializer()
        )

        orbital_position_container.build_mesh(components_distance=components_distance)
        orbital_position_container.build_faces(components_distance=components_distance)
        if kwargs['components_to_plot'] in ['primary', 'both']:
            kwargs['points_primary'], kwargs['primary_triangles'] = \
                orbital_position_container.primary.surface_serializer()

        if kwargs['components_to_plot'] in ['secondary', 'both']:
            kwargs['points_secondary'], kwargs['secondary_triangles'] = \
                orbital_position_container.secondary.surface_serializer()

        graphics.binary_wireframe(**kwargs)

    def surface(self, **kwargs):
        """
        function creates plot of binary system components

        :param kwargs:
            phase: float - phase at which plot the system, important for eccentric orbits
            components_to_plot: str - `primary`, `secondary` or `both`(default),
            normals: bool - plot normals of the surface phases as arrows
            edges: bool - highlight edges of surface faces
            colormap: str - 'gravity_acceleration`, `temperature` or None(default)
            plot_axis: bool - if False, axis will be hidden
            face_mask_primary - bool array: mask to select which faces to display
            face_mask_secondary - bool array: mask to select which faces to display
            inclination: float in degree - elevation of camera
            azimuth: camera azimuth
            units: str - units of gravity acceleration colormap  `SI` or `cgs`
            scale: str; `linear` or `log`
            axis_units: astropy.unit or dimensionless - axis units
            colorbar_orientation: str - `horizontal` or `vertical`(default)
            colorbar: bool - colorabar on/off switchic
        :return:
        """
        all_kwargs = ['phase', 'components_to_plot', 'normals', 'edges', 'colormap', 'plot_axis', 'face_mask_primary',
                      'face_mask_secondary', 'inclination', 'azimuth', 'units', 'axis_unit', 'colorbar_orientation',
                      'colorbar', 'scale']
        utils.invalid_kwarg_checker(kwargs, all_kwargs, self.surface)

        kwargs['phase'] = kwargs.get('phase', 0)
        kwargs['components_to_plot'] = kwargs.get('components_to_plot', 'both')
        kwargs['normals'] = kwargs.get('normals', False)
        kwargs['edges'] = kwargs.get('edges', False)
        kwargs['colormap'] = kwargs.get('colormap', None)
        kwargs['plot_axis'] = kwargs.get('plot_axis', True)
        kwargs['face_mask_primary'] = kwargs.get('face_mask_primary', None)
        kwargs['face_mask_secondary'] = kwargs.get('face_mask_secondary', None)
        kwargs['inclination'] = kwargs.get('inclination', np.degrees(self._self.inclination))
        kwargs['units'] = kwargs.get('units', 'cgs')
        kwargs['scale'] = kwargs.get('scale', 'linear')
        kwargs['axis_unit'] = kwargs.get('axis_unit', u.dimensionless_unscaled)
        kwargs['colorbar_orientation'] = kwargs.get('colorbar_orientation', 'vertical')
        kwargs['colorbar'] = kwargs.get('colorbar', 'True')

        components_distance, azim = self._self.orbit.orbital_motion(phase=kwargs['phase'])[0][:2]
        kwargs['azimuth'] = kwargs.get('azimuth', np.degrees(azim) - 90)
        kwargs['morphology'] = self._self.morphology
        kwg = {'suppress_parallelism': False}

        # recalculating spot latitudes
        # TODO: implement latitude recalculation once the functions will be relocated
        # spots_longitudes = geo.calculate_spot_longitudes(self._self, kwargs['phase'], component="all")
        # geo.assign_spot_longitudes(self._self, spots_longitudes, index=None, component="all")

        orbital_position_container = OrbitalPositionContainer(
            primary=StarContainer.from_properties_container(self._self.primary.to_properties_container()),
            secondary=StarContainer.from_properties_container(self._self.secondary.to_properties_container()),
            position=BINARY_POSITION_PLACEHOLDER(*(0, 1.0, 0.0, 0.0, 0.0)),
            **self._self.properties_serializer()
        )

        orbital_position_container.build(components_distance=components_distance,
                                         components=kwargs['components_to_plot'])
        # this part decides if both components need to be calculated at once (due to reflection effect)
        components = butils.component_to_list(kwargs['components_to_plot'])
        for component in components:
            star_container = getattr(orbital_position_container, component)
            kwargs['points_' + component], kwargs[component + '_triangles'] = star_container.surface_serializer()

            if kwargs['colormap'] == 'gravity_acceleration':
                log_g = star_container.flatten_parameter('log_g')
                value = log_g if kwargs['units'] == 'SI' else log_g + 2
                kwargs[component + '_cmap'] = value if kwargs['scale'] == 'log' else np.power(10, value)
            elif kwargs['colormap'] == 'temperature':
                temperatures = star_container.flatten_parameter('temperatures')
                kwargs[component+'_cmap'] = temperatures if kwargs['scale'] == 'linear' else \
                    np.log10(temperatures)

            if kwargs['face_mask_' + component] is not None:
                kwargs[component + '_triangles'] = kwargs[component + '_triangles'][kwargs['face_mask_' + component]]
                kwargs[component + '_cmap'] = kwargs[component + '_cmap'][kwargs['face_mask_' + component]]

            if kwargs['normals']:
                kwargs[component+'_centres'] = star_container.face_centres
                kwargs[component+'_arrows'] = star_container.normals

            if kwargs['axis_unit'] != u.dimensionless_unscaled and kwargs['axis_unit'] != 'SMA':
                sma = (self._self.semi_major_axis*units.DISTANCE_UNIT).to(kwargs['axis_unit']).value
                kwargs['points_'+component] *= sma
                kwargs['points_'+component] *= sma
                if kwargs['normals']:
                    kwargs[component+'_centres'] *= sma
                    kwargs[component+'_centres'] *= sma

        graphics.binary_surface(**kwargs)

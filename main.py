from elisa.engine.binary_system.system import BinarySystem
from elisa.engine.base.star import Star
from astropy import units as u
import numpy as np
import matplotlib.pyplot as plt
from elisa.engine import utils
from elisa.engine import const as c
from time import time
import logging
from elisa.engine.binary_system import geo


contact_pot = 2.2
start_time = time()

spots_metadata = {
    "primary":
        [
            {"longitude": 90,
             "latitude": 58,
             # "angular_density": 1,
             "angular_diameter": 5,
             "temperature_factor": 0.50},
            # {"longitude": 90,
            #  "latitude": 57,
            #  # "angular_density": 2,
            #  "angular_diameter": 30,
            #  "temperature_factor": 0.65},
            # {"longitude": 60,
            #  "latitude": 90,
            #  # "angular_density": 2,
            #  "angular_diameter": 30,
            #  "temperature_factor": 0.7},
        ],

    "secondary":
        [
            {"longitude": 10,
             "latitude": 45,
             # "angular_density": 3,
             "angular_diameter": 28,
             "temperature_factor": 0.55},
            {"longitude": 30,
             "latitude": 65,
             # "angular_density": 3,
             "angular_diameter": 45,
             "temperature_factor": 0.5},
        ]
}

primary = Star(mass=1.514*u.solMass,
               surface_potential=contact_pot,
               synchronicity=1.0,
               t_eff=6900*u.K,
               gravity_darkening=1.0,
               discretization_factor=3,
               albedo=0.6,
               metallicity=0,
               )
secondary = Star(mass=0.327*u.solMass,
                 surface_potential=contact_pot,
                 synchronicity=1.0,
                 t_eff=6969*u.K,
                 gravity_darkening=1.0,
                 albedo=0.6,
                 metallicity=0,
                 spots=spots_metadata['secondary']
                )

bs = BinarySystem(primary=primary,
                  secondary=secondary,
                  argument_of_periastron=0*u.deg,
                  gamma=-41.7*u.km/u.s,
                  period=0.7949859*u.d,
                  eccentricity=0.0,
                  inclination=86.39*u.deg,
                  primary_minimum_time=2440862.60793*u.d,
                  phase_shift=0.0,
                  )

components_min_distance = 1
kwargs = {'suppress_parallelism': False}
bs.build_surface(components_distance=components_min_distance, **kwargs)
# # bs.build_surface(components_distance=components_min_distance, component='primary')
# # bs.build_surface(components_distance=components_min_distance, component='secondary')
bs.build_surface_map(colormap='temperature', components_distance=components_min_distance)
# bs.build_surface_map(colormap='temperature', component='primary', components_distance=components_min_distance)
# bs.build_surface_map(colormap='temperature', component='secondary', components_distance=components_min_distance)

line_of_sight = np.array([1, 0, 0])
bs.secondary.points = utils.axis_rotation(45, bs.secondary.points, 'z', False, True)

bs.plot.surface(
        phase=0.4,
        # components_to_plot='primary',
        components_to_plot='secondary',
        edges=True,
        # normals=True,
        # colormap='gravity_acceleration',
        colormap='temperature',
        # plot_axis=False,
        # face_mask_primary=a,
        # face_mask_secondary=b,
        # inclination=crit_incl,
        # azimuth=azim[0],
        units='SI'
        )

from engine.binary_system import BinarySystem
from engine.single_system import SingleSystem
from engine.star import Star
from engine.planet import Planet
from astropy import units as u
import numpy as np
import matplotlib.pyplot as plt
from engine import utils
from engine import const as c
from time import time
from engine.physics import Physics
import logging


logging.basicConfig(level=logging.DEBUG)

from conf import config

from scipy.spatial import distance_matrix

spots_metadata = {
    "primary":
        [
            {"longitude": 90,
             "latitude": 58,
             # "angular_density": 1,
             "angular_diameter": 17,
             "temperature_factor": 0.9},
            {"longitude": 90,
             "latitude": 57,
             # "angular_density": 2,
             "angular_diameter": 30,
             "temperature_factor": 1.05},
            # {"longitude": 45,
            #  "latitude": 90,
            #  # "angular_density": 2,
            #  "angular_diameter": 30,
            #  "temperature_factor": 0.95},
        ],

    "secondary":
        [
            {"longitude": 30,
             "latitude": 65,
             # "angular_density": 3,
             "angular_diameter": 45,
             "temperature_factor": 0.9},
            {"longitude": 45,
             "latitude": 3,
             # "angular_density": 3,
             "angular_diameter": 10,
             "temperature_factor": 0.98}
        ]
}

pulsations_metadata = {'primary': [{'l': 4, 'm': 3, 'amplitude': 1000 * u.K, 'frequency': 15 / u.d},
                                   # {'l': 3, 'm': 2, 'amplitude': 50*u.K, 'frequency': 20/u.d},
                                   ],
                       'secondary': [{'l': 5, 'm': 5, 'amplitude': 300 * u.K, 'frequency': 15 / u.d},
                                     ]
                       }

physics = Physics(reflection_effect=True,
                  reflection_effect_iterations=2)

contact_pot = 2.96657
start_time = time()

# combo = {"primary_mass": 2.0, "secondary_mass": 1.0,
#          "primary_surface_potential": 3.869707694558656, "secondary_surface_potential": 4.04941512902796,
#          # "primary_surface_potential": 5, "secondary_surface_potential": 5,
#          "primary_synchronicity": 1, "secondary_synchronicity": 4,
#          "argument_of_periastron": c.HALF_PI * u.rad, "gamma": 0.0, "period": 1.0,
#          "eccentricity": 0.3, "inclination": 90.0 * u.deg, "primary_minimum_time": 0.0,
#          "phase_shift": 0.0,
#          "primary_t_eff": 5000, "secondary_t_eff": 5000,
#          "primary_gravity_darkening": 1.0, "secondary_gravity_darkening": 1.0
#          }  # rotationally squashed compact spherical components
#
# primary = Star(mass=combo["primary_mass"], surface_potential=combo["primary_surface_potential"],
#                synchronicity=combo["primary_synchronicity"],
#                t_eff=combo["primary_t_eff"], gravity_darkening=combo["primary_gravity_darkening"])
#
# secondary = Star(mass=combo["secondary_mass"], surface_potential=combo["secondary_surface_potential"],
#                  synchronicity=combo["secondary_synchronicity"],
#                  t_eff=combo["secondary_t_eff"], gravity_darkening=combo["secondary_gravity_darkening"],
#                  spots=spots_metadata['secondary']
#                  )
#
# bs = BinarySystem(primary=primary,
#                   secondary=secondary,
#                   argument_of_periastron=combo["argument_of_periastron"],
#                   gamma=combo["gamma"],
#                   period=combo["period"],
#                   eccentricity=combo["eccentricity"],
#                   inclination=combo["inclination"],
#                   primary_minimum_time=combo["primary_minimum_time"],
#                   phase_shift=combo["phase_shift"])
primary = Star(mass=1.5*u.solMass,
               surface_potential=4.6758014080477235,
               # surface_potential=contact_pot,
               spots=spots_metadata['primary'],
               # pulsations=pulsations_metadata['primary'],
               synchronicity=2.0,
               t_eff=6500*u.K,
               gravity_darkening=1.0,
               discretization_factor=3,
               )
secondary = Star(mass=1.0*u.solMass,
                 surface_potential=4.419393783692257,
                 # surface_potential=contact_pot,
                 synchronicity=1.5,
                 t_eff=10000*u.K,
                 gravity_darkening=1.0,
                 discretization_factor=3,
                 spots=spots_metadata['secondary'],
                 # pulsations=pulsations_metadata['primary'],
                )

bs = BinarySystem(primary=primary,
                  secondary=secondary,
                  argument_of_periastron=90*u.deg,
                  gamma=0*u.km/u.s,
                  period=1*u.d,
                  eccentricity=0.3,
                  inclination=90*u.deg,
                  primary_minimum_time=0.0*u.d,
                  phase_shift=0.0,
                  )


components_min_distance = 1 - bs.eccentricity

# bs.build_surface(components_distance=1)
# bs.build_surface(components_distance=1, component='primary')
# bs.build_surface(components_distance=1, component='secondary')
# bs.build_surface_map(colormap='temperature', components_distance=1)
# bs.build_surface_map(colormap='temperature', component='primary', components_distance=1)
# bs.build_surface_map(colormap='temperature', component='secondary', components_distance=1)
# bs.build_temperature_distribution(components_distance=1.0)
# bs.evaluate_normals()
# bs.build_surface(components_distance=1)

start_time = time()

# a, b = bs.reflection_effect(components_distance=1)
# print(np.shape(a))
# dists, dist_vect = utils.calculate_distance_matrix(points1=bs.primary.points, points2=bs.secondary.points,
#                                                    return_distance_vector_matrix=True)
# print(np.shape(dists), np.shape(dist_vect))
# dists = distance_matrix(bs.primary.points, bs.secondary.points)
# print(np.shape(dists))

print('Elapsed time: {0:.5f} s.'.format(time() - start_time))
crit_primary_potential = bs.critical_potential('primary', components_distance=components_min_distance)
print('Critical potential for primary component: {}'.format(crit_primary_potential))

crit_secondary_potential = bs.critical_potential('secondary', components_distance=components_min_distance)
print('Critical potential for secondary component: {}'.format(crit_secondary_potential))

# bs.plot('orbit', frame_of_reference='primary_component', axis_unit='dimensionless')
# bs.plot('orbit', frame_of_reference='barycentric')
bs.plot('equipotential', plane="zx", phase=bs.orbit.periastron_phase)

# bs.plot(descriptor='mesh',
#         # components_to_plot='primary',
#         components_to_plot='secondary',
#         plot_axis=False
#         )
# bs.plot(descriptor='wireframe',
#         # components_to_plot='primary',
#         components_to_plot='secondary',
#         # plot_axis=False
#         )

# bs.plot(descriptor='surface',
#         phase=0,
#         # components_to_plot='primary',
#         components_to_plot='secondary',
#         edges=True,
#         # normals=True,
#         # colormap='gravity_acceleration',
#         colormap='temperature',
#         # plot_axis=False,
#         # face_mask_primary=a,
#         # face_mask_secondary=b,
#         )


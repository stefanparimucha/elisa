import unittest
import numpy as np
from engine.binary_system import BinarySystem
from engine.star import Star
import engine.const as c
from astropy import units as u
from numpy.testing import assert_array_almost_equal


# class TestBinarySystemProperties(unittest.TestCase):
#
#     def test_orbit_change(self):
#         bs = BinarySystem(primary=None, secondary=None)
#
#         bs.period = 10.0
#         self.assertEqual(bs.orbit.period, 10)
#
#         bs.eccentricity = 0.6
#         self.assertEqual(bs.orbit.eccentricity, 0.6)
#
#         bs.inclination = 0.25
#         self.assertEqual(bs.orbit.inclination, 0.25)
#
#         bs.periastron = 0.2345
#         self.assertEqual(bs.orbit.periastron, 0.2345)
#
#     def test_binary_system_unit(self):
#         bs = BinarySystem(primary=None, secondary=None)
#
#         bs.period = 432000 * u.s
#         self.assertEqual(bs.period, 5)
#         with self.assertRaises(TypeError):
#             bs.period = '0000'
#
#         bs.inclination = 90 * u.deg
#         self.assertEqual(bs.inclination, 0.5 * np.pi)
#         with self.assertRaises(TypeError):
#             bs.inclination = '0000'
#
#         bs.periastron = 45 * u.deg
#         self.assertEqual(bs.periastron, np.pi * 0.25)
#         with self.assertRaises(TypeError):
#             bs.inclination = '0000'
#
#
#         # add all
#
#     def test_binary_change(self):
#         bs = BinarySystem(primary=None, secondary=None)
#
#         bs.period = 12.0
#         self.assertEqual(bs.period, 12)
#
#         bs.gamma = 2.556
#         self.assertEqual(bs.gamma, 2.556)

class TestBinarySystem(unittest.TestCase):

    def setUp(self):
        self.params_combination = [{"primary_mass": 2.0, "secondary_mass": 1.0,
                                    "primary_surface_potential": 100.0, "secondary_surface_potential": 100.0,
                                    "primary_synchronicity": 1.0, "secondary_synchronicity": 1.0,
                                    "argument_of_periastron": np.pi / 2.0, "gamma": 0.0, "period": 0.9,
                                    "eccentricity": 0.0, "inclination": c.HALF_PI, "primary_minimum_time": 0.0,
                                    "phase_shift": 0.0},

                                   {"primary_mass": 2.0, "secondary_mass": 1.0,
                                    "primary_surface_potential": 100.0, "secondary_surface_potential": 100.0,
                                    "primary_synchronicity": 1.7, "secondary_synchronicity": 1.3,
                                    "argument_of_periastron": c.PI, "gamma": 0.0, "period": 1.0,
                                    "eccentricity": 0.1, "inclination": 85.0 * u.deg, "primary_minimum_time": 0.0,
                                    "phase_shift": 0.0}]

    def test_critical_potential(self):
        phases_to_use = [0.0, 0.218222142892]
        expected_potentials = [[2.87584463214, 2.87584463214],
                               [3.47688032078, 3.20273942184]]
        obtained_potentials = []

        for i, combo in enumerate(self.params_combination):
            primary = Star(mass=combo["primary_mass"], surface_potential=combo["primary_surface_potential"],
                           synchronicity=combo["primary_synchronicity"])

            secondary = Star(mass=combo["secondary_mass"], surface_potential=combo["secondary_surface_potential"],
                             synchronicity=combo["secondary_synchronicity"])

            bs = BinarySystem(primary=primary,
                              secondary=secondary,
                              argument_of_periastron=combo["argument_of_periastron"],
                              gamma=combo["gamma"],
                              period=combo["period"],
                              eccentricity=combo["eccentricity"],
                              inclination=combo["inclination"],
                              primary_minimum_time=combo["primary_minimum_time"],
                              phase_shift=combo["phase_shift"])

            primary_cp = bs.critical_potential(component="primary", phase=phases_to_use[i])
            secondary_cp = bs.critical_potential(component="secondary", phase=phases_to_use[i])
            obtained_potentials.append([round(primary_cp, 10), round(secondary_cp, 10)])
        assert_array_almost_equal(expected_potentials, obtained_potentials)


    def test_lagrangian_points(self):

        expected_points = [[-0.8030279607, 0.5707515715, 1.5823807222],
                           [-0.7857030576, 0.5221432499, 1.5315280946]]

        obtained_points = []

        for i, combo in enumerate(self.params_combination):
            primary = Star(mass=combo["primary_mass"], surface_potential=combo["primary_surface_potential"],
                           synchronicity=combo["primary_synchronicity"])

            secondary = Star(mass=combo["secondary_mass"], surface_potential=combo["secondary_surface_potential"],
                             synchronicity=combo["secondary_synchronicity"])

            bs = BinarySystem(primary=primary,
                              secondary=secondary,
                              argument_of_periastron=combo["argument_of_periastron"],
                              gamma=combo["gamma"],
                              period=combo["period"],
                              eccentricity=combo["eccentricity"],
                              inclination=combo["inclination"],
                              primary_minimum_time=combo["primary_minimum_time"],
                              phase_shift=combo["phase_shift"])

            obtained_points.append([round(p, 10) for p in bs.lagrangian_points()])

        self.assertAlmostEquals(expected_points, obtained_points)

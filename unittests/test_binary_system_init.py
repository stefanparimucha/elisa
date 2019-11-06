import numpy as np

from copy import copy
from astropy import units as u
from numpy.testing import assert_array_equal

from elisa import const as c, units
from elisa.base.star import Star
from elisa.binary_system.system import BinarySystem
from unittests.utils import ElisaTestCase, prepare_binary_system


class BinarySystemInitTestCase(ElisaTestCase):
    def setUp(self):
        self.params_combination = [
            {"primary_mass": 2.0, "secondary_mass": 1.0,
             "primary_surface_potential": 100.0, "secondary_surface_potential": 100.0,
             "primary_synchronicity": 1.0, "secondary_synchronicity": 1.0,
             "argument_of_periastron": c.HALF_PI * u.rad, "gamma": 0.0, "period": 2.0,
             "eccentricity": 0.0, "inclination": c.HALF_PI * u.rad, "primary_minimum_time": 0.0,
             "phase_shift": 0.0,
             "primary_t_eff": 5000, "secondary_t_eff": 5000,
             "primary_gravity_darkening": 1.0, "secondary_gravity_darkening": 1.0,
             "primary_albedo": 0.6, "secondary_albedo": 0.6,
             },  # compact spherical components on circular orbit

            {"primary_mass": 2.0, "secondary_mass": 1.0,
             "primary_surface_potential": 100.0, "secondary_surface_potential": 80.0,
             "primary_synchronicity": 400, "secondary_synchronicity": 550,
             "argument_of_periastron": c.HALF_PI * u.rad, "gamma": 0.0, "period": 3.0,
             "eccentricity": 0.0, "inclination": 90.0 * units.deg, "primary_minimum_time": 0.0,
             "phase_shift": 0.0,
             "primary_t_eff": 5000, "secondary_t_eff": 5000,
             "primary_gravity_darkening": 1.0, "secondary_gravity_darkening": 1.0,
             "primary_albedo": 0.6, "secondary_albedo": 0.6
             },  # rotationally squashed compact spherical components

            {"primary_mass": 2.0, "secondary_mass": 1.0,
             "primary_surface_potential": 3.5, "secondary_surface_potential": 3.0,
             "primary_synchronicity": 1.5, "secondary_synchronicity": 1.2,
             "argument_of_periastron": c.HALF_PI, "gamma": 0.0, "period": 1.0,
             "eccentricity": 0.0, "inclination": 90.0 * units.deg, "primary_minimum_time": 0.0,
             "phase_shift": 0.0,
             "primary_t_eff": 5000, "secondary_t_eff": 5000,
             "primary_gravity_darkening": 1.0, "secondary_gravity_darkening": 1.0,
             "primary_albedo": 0.6, "secondary_albedo": 0.6
             },  # close tidally deformed components with asynchronous rotation on circular orbit

            {"primary_mass": 2.0, "secondary_mass": 1.0,
             "primary_surface_potential": 4.8, "secondary_surface_potential": 4.0,
             "primary_synchronicity": 1.5, "secondary_synchronicity": 1.2,
             "argument_of_periastron": c.HALF_PI * u.rad, "gamma": 0.0, "period": 1.0,
             "eccentricity": 0.3, "inclination": 90.0 * units.deg, "primary_minimum_time": 0.0,
             "phase_shift": 0.0,
             "primary_t_eff": 5000, "secondary_t_eff": 5000,
             "primary_gravity_darkening": 1.0, "secondary_gravity_darkening": 1.0,
             "primary_albedo": 0.6, "secondary_albedo": 0.6
             },  # close tidally deformed components with asynchronous rotation on eccentric orbit

            {"primary_mass": 2.0, "secondary_mass": 1.0,
             "primary_surface_potential": 2.875844632141054,
             "secondary_surface_potential": 2.875844632141054,
             "primary_synchronicity": 1.0, "secondary_synchronicity": 1.0,
             "argument_of_periastron": c.HALF_PI * u.rad, "gamma": 0.0, "period": 1.0,
             "eccentricity": 0.0, "inclination": 90.0 * units.deg, "primary_minimum_time": 0.0,
             "phase_shift": 0.0,
             "primary_t_eff": 5000, "secondary_t_eff": 5000,
             "primary_gravity_darkening": 1.0, "secondary_gravity_darkening": 1.0,
             "primary_albedo": 0.6, "secondary_albedo": 0.6
             },  # synchronous contact system

            {"primary_mass": 2.0, "secondary_mass": 1.0,
             "primary_surface_potential": 3.159639848886489,
             "secondary_surface_potential": 3.229240544834036,
             "primary_synchronicity": 1.5, "secondary_synchronicity": 2.0,
             "argument_of_periastron": c.HALF_PI * u.rad, "gamma": 0.0, "period": 1.0,
             "eccentricity": 0.0, "inclination": 90.0 * units.deg, "primary_minimum_time": 0.0,
             "phase_shift": 0.0,
             "primary_t_eff": 5000, "secondary_t_eff": 5000,
             "primary_gravity_darkening": 1.0, "secondary_gravity_darkening": 1.0,
             "primary_albedo": 0.6, "secondary_albedo": 0.6
             },  # asynchronous contact system (improbable but whatever...)

            {"primary_mass": 2.0, "secondary_mass": 1.0,
             "primary_surface_potential": 2.7,
             "secondary_surface_potential": 2.7,
             "primary_synchronicity": 1.0, "secondary_synchronicity": 1.0,
             "argument_of_periastron": 90 * units.deg, "gamma": 0.0, "period": 1.0,
             "eccentricity": 0.0, "inclination": 90.0 * units.deg, "primary_minimum_time": 0.0,
             "phase_shift": 0.0,
             "primary_t_eff": 5000, "secondary_t_eff": 5000,
             "primary_gravity_darkening": 1.0, "secondary_gravity_darkening": 1.0,
             "primary_albedo": 0.6, "secondary_albedo": 0.6
             }  # over-contact system
        ]

    def prepare_systems(self):
        return [prepare_binary_system(combo) for combo in self.params_combination]

    def test_calculate_semi_major_axis(self):
        expected = [6702758048.0, 8783097736.0, 4222472978.0, 4222472978.0, 4222472978.0, 4222472978.0, 4222472978.0]
        obtained = list()

        for bs in self.prepare_systems():
            obtained.append(np.round(bs.semi_major_axis, 0))
        assert_array_equal(expected, obtained)

    def test_setup_periastron_components_radii(self):
        expected_potentials = np.round(np.array([
            [2.875844632141054, 2.875844632141054],
            [93.717106763853593, 73.862399105365014],
            [3.159639848886489, 2.935086409515319],
            [4.027577786299736, 3.898140726941630],
            [2.875844632141054, 2.875844632141054],
            [3.159639848886489, 3.229240544834036],
            [2.875844632141054, 2.875844632141054]
        ]), 5)
        obtained_potentials = list()
        for bs in self.prepare_systems():
            obtained_potentials.append([bs.primary.critical_surface_potential, bs.secondary.critical_surface_potential])
        obtained_potentials = np.round(np.array(obtained_potentials), 5)
        assert_array_equal(expected_potentials, obtained_potentials)

    def test_compute_morphology(self):
        expected = ['detached', 'detached', 'detached', 'detached', 'semi-detached', 'double-contact', 'over-contact']
        obtained = [bs.morphology for bs in self.prepare_systems()]
        assert_array_equal(expected, obtained)

    def test_setup_components_radii(self):
        radii = ["forward_radius", "side_radius", "equatorial_radius", "backward_radius", "polar_radius"]
        obtained = dict()

        expected = {
            "primary": {
                "forward_radius": [0.01005, 0.01229, 0.3783, 0.26257, 0.57075, 0.53029, np.nan],
                "side_radius": [0.01005, 0.01229, 0.35511, 0.24859, 0.43994, 0.41553, 0.48182],
                "equatorial_radius": [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan],
                "backward_radius": [0.01005, 0.01229, 0.36723, 0.25608, 0.46794, 0.44207, 0.52573],
                "polar_radius": [0.01005, 0.01005, 0.33055, 0.24242, 0.41427, 0.37162, 0.44577]
            },
            "secondary": {
                "forward_radius": [0.00506, 0.00763, 0.34966, 0.25693, 0.42925, 0.36743, np.nan],
                "side_radius": [0.00506, 0.00763, 0.29464, 0.21419, 0.31288, 0.28094, 0.35376],
                "equatorial_radius": [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan],
                "backward_radius": [0.00506, 0.00763, 0.32018, 0.23324, 0.34537, 0.30842, 0.41825],
                "polar_radius": [0.00506, 0.00635, 0.2798, 0.20994, 0.29977, 0.2489, 0.33306]
            }
        }

        for component in ["primary", "secondary"]:
            obtained[component] = dict()
            for radius in radii:
                obtained[component][radius] = list()
                for i, bs in enumerate(self.prepare_systems()):
                    value = np.round(getattr(getattr(bs, component), radius), 5) \
                        if hasattr(getattr(bs, component), radius) else np.nan
                    assert_array_equal([value], [expected[component][radius][i]])

    def test_lagrangian_points(self):

        expected_points = np.round(np.array([
            [-0.80302796065835425, 0.57075157151852673, 1.5823807222136623],
            [-0.80302796065835425, 0.57075157151852673, 1.5823807222136623],
            [-0.80302796065835425, 0.57075157151852673, 1.5823807222136623],
            [-0.7308068505479407, 0.41566688133312363, 1.4990376377419574],
            [-0.80302796065835425, 0.57075157151852673, 1.5823807222136623],
            [-0.80302796065835425, 0.57075157151852673, 1.5823807222136623],
            [-0.80302796065835425, 0.57075157151852673, 1.5823807222136623]
        ]), 5)

        obtained_points = []
        for bs in self.prepare_systems():
            obtained_points.append(bs.lagrangian_points())

        obtained_points = np.round(np.array(obtained_points), 5)
        assert_array_equal(expected_points, obtained_points)

    def test_components(self):
        bs = self.prepare_systems()[0]
        self.assertTrue(hasattr(bs, "components"))
        self.assertTrue(bs.components["primary"])
        self.assertTrue(bs.components["secondary"])


class ValidityTestCase(ElisaTestCase):
    MANDATORY_KWARGS = ['gamma', 'inclination', 'period', 'eccentricity', 'argument_of_periastron', 'phase_shift']

    def setUp(self):
        self._initial_params = {
            "primary_mass": 2.0, "secondary_mass": 1.0,
            "primary_surface_potential": 100.0, "secondary_surface_potential": 100.0,
            "primary_synchronicity": 1.0, "secondary_synchronicity": 1.0,
            "argument_of_periastron": c.HALF_PI * u.rad, "gamma": 0.0, "period": 1.0,
            "eccentricity": 0.0, "inclination": c.HALF_PI * units.deg, "primary_minimum_time": 0.0,
            "phase_shift": 0.0,
            "primary_t_eff": 5000, "secondary_t_eff": 5000,
            "primary_gravity_darkening": 1.0, "secondary_gravity_darkening": 1.0,
            "primary_albedo": 1.0, "secondary_albedo": 1.0,
        }

        self._primary = Star(mass=self._initial_params["primary_mass"],
                             surface_potential=self._initial_params["primary_surface_potential"],
                             synchronicity=self._initial_params["primary_synchronicity"],
                             t_eff=self._initial_params["primary_t_eff"],
                             gravity_darkening=self._initial_params["primary_gravity_darkening"],
                             albedo=self._initial_params['primary_albedo'],
                             metallicity=0.0)

        self._secondary = Star(mass=self._initial_params["secondary_mass"],
                               surface_potential=self._initial_params["secondary_surface_potential"],
                               synchronicity=self._initial_params["secondary_synchronicity"],
                               t_eff=self._initial_params["secondary_t_eff"],
                               gravity_darkening=self._initial_params["secondary_gravity_darkening"],
                               albedo=self._initial_params['secondary_albedo'],
                               metallicity=0.0)

    def test__star_params_validity_check(self):
        with self.assertRaises(Exception) as context:
            BinarySystem(primary=69,
                         secondary=self._secondary,
                         argument_of_periastron=self._initial_params["argument_of_periastron"],
                         gamma=self._initial_params["gamma"],
                         period=self._initial_params["period"],
                         eccentricity=self._initial_params["eccentricity"],
                         inclination=self._initial_params["inclination"],
                         primary_minimum_time=self._initial_params["primary_minimum_time"],
                         phase_shift=self._initial_params["phase_shift"])

        self.assertTrue('Component `primary` is not instance of class' in str(context.exception))

        star_mandatory_kwargs = ['mass', 'surface_potential', 'synchronicity',
                                 'albedo', 'metallicity', 'gravity_darkening']

        for kw in star_mandatory_kwargs[:1]:
            p = copy(self._primary)
            setattr(p, f"{kw}", None)

            with self.assertRaises(Exception) as context:
                BinarySystem(primary=p,
                             secondary=self._secondary,
                             argument_of_periastron=self._initial_params["argument_of_periastron"],
                             gamma=self._initial_params["gamma"],
                             period=self._initial_params["period"],
                             eccentricity=self._initial_params["eccentricity"],
                             inclination=self._initial_params["inclination"],
                             primary_minimum_time=self._initial_params["primary_minimum_time"],
                             phase_shift=self._initial_params["phase_shift"])

            self.assertTrue(f'Mising argument(s): `{kw}`' in str(context.exception))

    def test_invalid_kwarg_checker(self):
        with self.assertRaises(Exception) as context:
            BinarySystem(primary=self._primary,
                         secondary=self._secondary,
                         argument_of_periastron=self._initial_params["argument_of_periastron"],
                         gamma=self._initial_params["gamma"],
                         period=self._initial_params["period"],
                         eccentricity=self._initial_params["eccentricity"],
                         inclination=self._initial_params["inclination"],
                         primary_minimum_time=self._initial_params["primary_minimum_time"],
                         phase_shift=self._initial_params["phase_shift"],
                         adhoc_param="xxx")
        self.assertTrue('Invalid keyword argument(s): adhoc_param' in str(context.exception))

    def test_check_missing_kwargs(self):
        initial_kwargs = dict(primary=self._primary,
                              secondary=self._secondary,
                              argument_of_periastron=self._initial_params["argument_of_periastron"],
                              gamma=self._initial_params["gamma"],
                              period=self._initial_params["period"],
                              eccentricity=self._initial_params["eccentricity"],
                              inclination=self._initial_params["inclination"],
                              primary_minimum_time=self._initial_params["primary_minimum_time"],
                              phase_shift=self._initial_params["phase_shift"])

        for kw in self.MANDATORY_KWARGS:
            kwargs = copy(initial_kwargs)
            del (kwargs[kw])
            with self.assertRaises(Exception) as context:
                BinarySystem(**kwargs)
            self.assertTrue(f'Missing argument(s): `{kw}`' in str(context.exception))


class BinarySystemSerializersTestCase(ElisaTestCase):
    def setUp(self):
        self.params_combination = [
            {"primary_mass": 2.0, "secondary_mass": 1.0,
             "primary_surface_potential": 100.0, "secondary_surface_potential": 100.0,
             "primary_synchronicity": 1.0, "secondary_synchronicity": 1.0,
             "argument_of_periastron": c.HALF_PI * u.rad, "gamma": 0.0, "period": 1.0,
             "eccentricity": 0.0, "inclination": c.HALF_PI * units.deg, "primary_minimum_time": 0.0,
             "phase_shift": 0.0,
             "primary_t_eff": 5000, "secondary_t_eff": 5000,
             "primary_gravity_darkening": 1.0, "secondary_gravity_darkening": 1.0,
             "primary_albedo": 0.6, "secondary_albedo": 0.6,
             },
            # compact spherical components on circular orbit

            {"primary_mass": 2.0, "secondary_mass": 1.0,
             "primary_surface_potential": 4.8, "secondary_surface_potential": 4.0,
             "primary_synchronicity": 1.5, "secondary_synchronicity": 1.2,
             "argument_of_periastron": c.HALF_PI * u.rad, "gamma": 0.0, "period": 1.0,
             "eccentricity": 0.3, "inclination": 90.0 * units.deg, "primary_minimum_time": 0.0,
             "phase_shift": 0.0,
             "primary_t_eff": 5000, "secondary_t_eff": 5000,
             "primary_gravity_darkening": 1.0, "secondary_gravity_darkening": 1.0,
             "primary_albedo": 0.6, "secondary_albedo": 0.6
             }  # close tidally deformed components with asynchronous rotation on eccentric orbit
        ]

        self._binaries = self.prepare_systems()

    def prepare_systems(self):
        return [prepare_binary_system(combo) for combo in self.params_combination]

    def test_kwargs_serializer(self):
        bs = self._binaries[-1]
        obtained = bs.kwargs_serializer()

        expected = dict(
            gamma=0.0,
            inclination=c.HALF_PI,
            period=1.0,
            eccentricity=0.3,
            argument_of_periastron=c.HALF_PI,
            primary_minimum_time=0.0,
            phase_shift=0.0
        )

        obtained_array, expectedd_array = list(), list()

        for o_key, e_key in zip(obtained, expected):
            if isinstance(obtained[o_key], u.Quantity):
                obtained[o_key] = obtained[o_key].value
            obtained_array.append(round(obtained[o_key], 5))
            expectedd_array.append(round(expected[e_key], 5))

        assert_array_equal(expectedd_array, obtained_array)

    def test_properties_serializer(self):
        bs = self._binaries[-1]
        obtained = bs.properties_serializer()
        expected = ["semi_major_axis", "morphology", "mass_ratio"]
        for e in expected:
            self.assertTrue(e in obtained)
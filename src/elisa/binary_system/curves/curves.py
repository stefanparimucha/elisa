import numpy as np
from copy import copy

from elisa.conf import config
from elisa import ld, const
from elisa.logger import getLogger
from elisa.binary_system import (
    dynamic,
    surface
)
from elisa.binary_system.curves import (
    utils as crv_utils,
    curves_mp,
    curve_approx
)
from elisa.binary_system.container import OrbitalPositionContainer
from elisa.observer.mp import manage_observations


logger = getLogger('binary_system.curves.shared')


# TODO: soon to be removed
def _calculate_lc_point(band, ld_cfs, normal_radiance, coverage, cosines):
    """
    Calculates point on the light curve for given band.

    :param band: str; name of the photometric band
    :param ld_cfs: Dict[str, Dict[str, pandas.DataFrame]];
    :param normal_radiance: Dict[str, Dict[str, numpy.array]];
    :param coverage: Dict[str, Dict[str, numpy.array]];
    :param cosines: Dict[str, Dict[str, numpy.array]];
    :return: float;
    """
    ld_law_cfs_columns = config.LD_LAW_CFS_COLUMNS[config.LIMB_DARKENING_LAW]
    ld_cors = {
        component: ld.limb_darkening_factor(coefficients=ld_cfs[component][band][ld_law_cfs_columns].values,
                                            limb_darkening_law=config.LIMB_DARKENING_LAW,
                                            cos_theta=cosines[component])
        for component in config.BINARY_COUNTERPARTS
    }
    flux = {
        component:
            np.sum(normal_radiance[component][band] * cosines[component] * coverage[component] * ld_cors[component])
        for component in config.BINARY_COUNTERPARTS
    }

    flux = (flux['primary'] + flux['secondary'])
    return flux


def resolve_curve_method(system, fn_array):
    """
    Resolves which curve calculating method to use based on the type of the system.

    :param system: elisa.binary_system.BinarySystem;
    :param fn_array: tuple; list of curve calculating functions in specific order
    (circular synchronous or circular assynchronous without spots,
     circular assynchronous with spots,
     eccentric synchronous or eccentric assynchronous without spots,
     eccentric assynchronous with spots)
    :return: curve calculating method chosen from `fn_array`
    """
    is_circular = system.eccentricity == 0
    is_eccentric = 1 > system.eccentricity > 0
    assynchronous_spotty_p = system.primary.synchronicity != 1 and system.primary.has_spots()
    assynchronous_spotty_s = system.secondary.synchronicity != 1 and system.secondary.has_spots()
    assynchronous_spotty_test = assynchronous_spotty_p or assynchronous_spotty_s

    spotty_test_eccentric = system.primary.has_spots() or system.secondary.has_spots()

    if is_circular:
        if not assynchronous_spotty_test and not system.has_pulsations():
            logger.debug('Calculating curve for circular binary system without pulsations and without '
                         'asynchronous spotty components.')
            return fn_array[0]
        else:
            logger.debug('Calculating curve for circular binary system with pulsations or with asynchronous '
                         'spotty components.')
            return fn_array[1]
    elif is_eccentric:
        if spotty_test_eccentric:
            logger.debug('Calculating curve for eccentric binary system with spotty components.')
            return fn_array[2]
        else:
            logger.debug('Calculating curve for eccentric binary system without spotty '
                         'components.')
            return fn_array[3]

    raise NotImplementedError("Orbit type not implemented or invalid")


def prep_initial_system(binary):
    """
    Prepares base binary system from which curves will be calculated in case of circular synchronous binaries.

    :param binary: elisa.binary_system.system.BinarySystem
    :return: elisa.binary_system.container.OrbitalPositionContainer
    """
    from_this = dict(binary_system=binary, position=const.Position(0, 1.0, 0.0, 0.0, 0.0))
    initial_system = OrbitalPositionContainer.from_binary_system(**from_this)
    initial_system.build(components_distance=1.0)

    return initial_system


def produce_circ_sync_curves(binary, initial_system, phases, curve_fn, crv_labels, **kwargs):
    """
    Auxiliary function to produce curve from circular synchronous binary system

    :param binary: elisa.binary_system.system.BinarySystem;
    :param initial_system: elisa.binary_system.container.OrbitalPositionContainer
    :param phases: numpy.array
    :param curve_fn: function to calculate given type of the curve
    :param crv_labels: labels of the calculated curves (passbands, components,...)
    :param kwargs: Dict;
            * ** passband ** * - Dict[str, elisa.observer.PassbandContainer]
            * ** left_bandwidth ** * - float
            * ** right_bandwidth ** * - float
            * ** atlas ** * - str
            * ** position_method** * - function definition; to evaluate orbital positions
            * ** phases ** * - numpy.array
    :return: dict; calculated curves
    """

    crv_utils.prep_surface_params(initial_system.flatt_it(), return_values=False, write_to_containers=True, **kwargs)

    fn_args = (binary, initial_system, crv_labels, curve_fn)

    curves = manage_observations(fn=curves_mp.produce_circ_sync_curves_mp,
                                 fn_args=fn_args,
                                 position=phases,
                                 **kwargs)

    return curves


def produce_circ_spotty_async_curves(binary, curve_fn, crv_labels, **kwargs):
    """
    Function returns curve of assynchronous systems with circular orbits and spots.

    :param binary: elisa.binary_system.system.BinarySystem;
    :param curve_fn: curve function
    :param crv_labels: labels of the calculated curves (passbands, components,...)
    :param kwargs: Dict;
    :**kwargs options**:
        * ** passband ** * - Dict[str, elisa .observer.PassbandContainer]
        * ** left_bandwidth ** * - float
        * ** right_bandwidth ** * - float
        * ** atlas ** * - str
    :return: Dict; curves
    """
    phases = kwargs.pop("phases")
    position_method = kwargs.pop("position_method")
    orbital_motion = position_method(input_argument=phases, return_nparray=False, calculate_from='phase')
    ecl_boundaries = dynamic.get_eclipse_boundaries(binary, 1.0)

    from_this = dict(binary_system=binary, position=const.Position(0, 1.0, 0.0, 0.0, 0.0))
    initial_system = OrbitalPositionContainer.from_binary_system(**from_this)

    points = dict()
    for component in config.BINARY_COUNTERPARTS:
        star = getattr(initial_system, component)
        _a, _b, _c, _d = surface.mesh.mesh_detached(initial_system, 1.0, component, symmetry_output=True)
        points[component] = _a
        setattr(star, "points", copy(_a))
        setattr(star, "point_symmetry_vector", _b)
        setattr(star, "base_symmetry_points_number", _c)
        setattr(star, "inverse_point_symmetry_matrix", _d)

    fn_args = binary, initial_system, points, ecl_boundaries, crv_labels, curve_fn

    band_curves = manage_observations(fn=curves_mp.produce_circ_spotty_async_curves_mp,
                                      fn_args=fn_args,
                                      position=orbital_motion,
                                      **kwargs)

    return band_curves


def produce_ecc_curves_no_spots(binary, curve_fn, crv_labels, **kwargs):
    """
    Function for generating curves of binaries with eccentric orbit and no spots where different curve
    integration approximations are evaluated and performed.

    :param binary: elisa.binary_system.system.BinarySystem;
    :param curve_fn: curve generator function
    :param crv_labels: labels of the calculated curves (passbands, components,...)
    :param kwargs: Dict;
    :**kwargs options**:
        * ** passband ** * - Dict[str, elisa .observer.PassbandContainer]
        * ** left_bandwidth ** * - float
        * ** right_bandwidth ** * - float
        * ** atlas ** * - str
    :return: Dict; curves
    """
    phases = kwargs.pop("phases")

    # this condition checks if even to attempt to utilize apsidal line symmetry approximations
    # curve has to have enough point on orbit and have to span at least in 0.8 phase
    phases_span_test = np.max(phases) - np.min(phases) >= 0.8

    position_method = kwargs.pop("position_method")

    try_to_find_appx = curve_approx.look_for_approximation(not binary.has_pulsations())

    curve_fn_list = [integrate_eccentric_curve_exactly, curve_approx.integrate_eccentric_curve_appx_one]

    appx_uid, run = curve_approx.resolve_ecc_approximation_method(binary, phases, position_method, try_to_find_appx,
                                                                  phases_span_test, curve_fn_list, crv_labels, curve_fn,
                                                                  **kwargs)

    logger_messages = {
        'zero': 'curve will be calculated in a rigorous `phase to phase manner` without approximations',
        'one': 'one half of the curve points on the one side of the apsidal line will be interpolated',
        'two': 'geometry of the stellar surface on one half of the apsidal '
               'line will be copied from their symmetrical counterparts',
        'three': 'surface geometry at some orbital positions will not be recalculated due to similarities to previous '
                 'orbital positions'
    }
    logger.info(logger_messages.get(appx_uid))
    return run()


def integrate_eccentric_curve_exactly(binary, orbital_motion, phases, crv_labels, curve_fn, **kwargs):
    """
    Function calculates curves for eccentric orbit for selected filters.
    Curve is calculated exactly for each OrbitalPosition.
    It is very slow and it should be used only as a benchmark.

    :param binary: elisa.binary_system.system.BinarySystem; instance
    :param orbital_motion: list of all OrbitalPositions at which curve will be calculated
    :param phases: phases in which the phase curve will be calculated
    :param kwargs: kwargs taken from `produce_eccentric_curve` function
    :param crv_labels: labels of the calculated curves (passbands, components,...)
    :param curve_fn: curve function
    :return: Dict; dictionary of fluxes for each filter
    """
    # surface potentials with constant volume of components
    potentials = binary.correct_potentials(phases, component="all", iterations=2)
    fn_args = (binary, potentials, crv_labels, curve_fn)

    band_curves = manage_observations(fn=curves_mp.integrate_eccentric_curve_exactly,
                                      fn_args=fn_args,
                                      position=orbital_motion,
                                      **kwargs)
    return band_curves

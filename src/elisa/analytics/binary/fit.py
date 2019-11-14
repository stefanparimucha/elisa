import functools
import numpy as np

from copy import copy
from typing import List
from scipy.optimize import least_squares

from elisa.atm import atm_file_prefix_to_quantity_list
from elisa.binary_system.system import BinarySystem
from elisa.conf import config
from elisa.observer.observer import Observer
from elisa.logger import getLogger

from elisa.analytics.binary import (
    utils as analutils,
    model
)
from elisa.analytics.binary.utils import (
    renormalize_value,
    normalize_value,
    x0_vectorize,
    x0_to_fixed_kwargs
)

logger = getLogger('analytics.binary.fit')

ALL_PARAMS = ['inclination',
              'eccentricity',
              'argument_of_periastron'
              'gamma',
              'p__mass',
              'p__t_eff',
              'p__surface_potential',
              'p__gravity_darkening',
              'p__albedo',
              'p__metallicity',
              's__mass',
              's__t_eff',
              's__surface_potential',
              's__gravity_darkening',
              's__albedo',
              's__metallicity']

TEMPERATURES = atm_file_prefix_to_quantity_list("temperature", config.ATM_ATLAS)
METALLICITY = atm_file_prefix_to_quantity_list("metallicity", config.ATM_ATLAS)


NORMALIZATION_MAP = {
    'inclination': (0, 180),
    'eccentricity': (0, 1),
    'argument_of_periastron': (0, 360),
    'gamma': (0, 1e6),
    'p__mass': (0.5, 20),
    's__mass': (0.5, 20),
    'p__t_eff': (np.min(TEMPERATURES), np.max(TEMPERATURES)),
    's__t_eff': (np.min(TEMPERATURES), np.max(TEMPERATURES)),
    'p__metallicity': (np.min(METALLICITY), np.max(METALLICITY)),
    's__metallicity': (np.min(METALLICITY), np.max(METALLICITY)),
    'p__surface_potential': (2.0, 50.0),
    's__surface_potential': (2.0, 50.0),
    'p__albedo': (0, 1),
    's__albedo': (0, 1),
    'p__gravity_darkening': (0, 1),
    's__gravity_darkening': (0, 1)
}


def update_normalization_map(update):
    """
    Update module normalization map with supplied dict.

    :param update: Dict;
    """
    NORMALIZATION_MAP.update(update)


def param_renormalizer(x, kwords):
    """
    Renormalize values from `x` to their native form.

    :param x: Iterable[float]; iterable of normalized parameter values
    :param kwords: Iterable[str]; related parmaeter names from `x`
    :return: List[float];
    """
    return [renormalize_value(_x, *get_param_boundaries(_kword)) for _x, _kword in zip(x, kwords)]


def param_normalizer(x: List, kwords: List) -> List:
    """
    Normalize values from `x` to value between (0, 1).

    :param x: Iterable[float]; iterable of values in their native form
    :param kwords: Iterable[str]; iterable str of names related to `x`
    :return: List[float];
    """
    return [normalize_value(_x, *get_param_boundaries(_kword)) for _x, _kword in zip(x, kwords)]


def get_param_boundaries(param):
    """
    Return normalization boundaries for given parmeter.

    :param param: str; name of parameter to get boundaries for
    :return: Tuple[float, float];
    """
    return NORMALIZATION_MAP[param]


def serialize_param_boundaries(x0):
    """
    Serialize boundaries of parameters if exists and parameter is not fixed.

    :param x0: List[Dict[str, Union[float, str, bool]]]; initial parmetres in JSON form
    :return: Dict[str, Tuple[float, float]]
    """
    return {record['param']: (record.get('min', NORMALIZATION_MAP[record['param']][0]),
                              record.get('max', NORMALIZATION_MAP[record['param']][1]))
            for record in x0 if not record['fixed']}


def logger_decorator(suppress_logger=False):
    def do(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not suppress_logger:
                logger.info(f'current xn value: {kwargs}')
            return func(*args, **kwargs)
        return wrapper
    return do


def lc_r_squared(synthetic, *args, **x):
    """
    Compute R^2 (coefficient of determination).

    :param synthetic: callable; synthetic method
    :param args: Tuple;
    :**args*::
        * **xs** * -- numpy.array; phases
        * **ys** * -- numpy.array; supplied fluxes (lets say fluxes from observation) normalized to max value
        * **period** * -- float;
        * **passband** * -- Union[str, List[str]];
        * **discretization** * -- flaot;
    :param x: Dict;
    :** x options**: kwargs of current parameters to compute binary system
    :return: float;
    """
    xs, ys, period, passband, discretization = args
    observed_means = np.array([np.repeat(np.mean(ys[band]), len(xs)) for band in ys])
    variability = np.sum([np.sum(np.power(ys[band] - observed_means, 2)) for band in ys])

    observer = Observer(passband=passband, system=None)
    observer._system_cls = BinarySystem
    synthetic = synthetic(xs, period, discretization, observer, **x)

    synthetic = analutils.normalize_lightcurve_to_max(synthetic)
    residual = np.sum([np.sum(np.power(synthetic[band] - ys[band], 2)) for band in ys])
    return 1.0 - (residual / variability)


def rv_r_squared(synthetic, *args, **x):
    xs, ys, period, on_normalized = args
    observed_means = np.array([np.repeat(np.mean(ys[comp]), len(xs)) for comp in config.BINARY_COUNTERPARTS])
    variability = np.sum([np.sum(np.power(ys[comp] - observed_means, 2)) for comp in config.BINARY_COUNTERPARTS])

    observer = Observer(passband='bolometric', system=None)
    observer._system_cls = BinarySystem
    synthetic = synthetic(xs, period, observer, **x)
    if on_normalized:
        synthetic = analutils.normalize_rv_curve_to_max(synthetic)
    synthetic = {"primary": synthetic[0], "secondary": synthetic[1]}

    residual = np.sum([np.sum(np.power(synthetic[comp] - ys[comp], 2)) for comp in config.BINARY_COUNTERPARTS])
    return 1.0 - (residual / variability)


def fit_data_initializer(x0, passband=None):
    boundaries = serialize_param_boundaries(x0)
    update_normalization_map(boundaries)

    fixed = x0_to_fixed_kwargs(x0)
    x0_vectorized, kwords = x0_vectorize(x0)
    x0 = param_normalizer(x0_vectorized, kwords)

    observer = Observer(passband='bolometric' if passband is None else passband, system=None)
    observer._system_cls = BinarySystem

    return x0, kwords, fixed, observer


class CircularSyncLightCurve(object):
    @staticmethod
    def circular_sync_model_to_fit(x, *args):
        """
        Molde to find minimum.

        :param x: Iterable[float];
        :param args: Tuple;
         :**args*::
            * **xs** * -- numpy.array; phases
            * **ys** * -- numpy.array; supplied fluxes (lets say fluxes from observation) normalized to max value
            * **period** * -- float;
            * **discretization** * -- flaot;
            * **suppress_logger** * -- bool;
            * **passband** * -- Iterable[str];
            * **observer** * -- elisa.observer.observer.Observer;
        :return: float;
        """
        xs, ys, period, kwords, fixed, discretization, suppress_logger, passband, observer = args
        x = param_renormalizer(x, kwords)
        kwargs = {k: v for k, v in zip(kwords, x)}
        kwargs.update(fixed)
        fn = model.circular_sync_synthetic
        synthetic = logger_decorator(suppress_logger)(fn)(xs, period, discretization, observer, **kwargs)
        synthetic = analutils.normalize_lightcurve_to_max(synthetic)
        return np.array([np.sum(np.power(synthetic[band] - ys[band], 2)) for band in synthetic])

    @staticmethod
    def fit(xs, ys, period, x0, passband, discretization, xtol=1e-15, max_nfev=None, suppress_logger=False):
        initial_x0 = copy(x0)
        x0, kwords, fixed, observer = fit_data_initializer(x0, passband=passband)
        args = (xs, ys, period, kwords, fixed, discretization, suppress_logger, passband, observer)

        logger.info("fitting circular synchronous system...")
        func = CircularSyncLightCurve.circular_sync_model_to_fit
        result = least_squares(func, x0, bounds=(0, 1), args=args, max_nfev=max_nfev, xtol=xtol)
        logger.info("fitting finished")

        result = param_renormalizer(result.x, kwords)
        result_dict = {k: v for k, v in zip(kwords, result)}
        result_dict.update(x0_to_fixed_kwargs(initial_x0))

        r_squared_args = xs, ys, period, passband, discretization
        r_squared_result = lc_r_squared(model.circular_sync_synthetic, *r_squared_args, **result_dict)
        logger.info(f'r_squared: {r_squared_result}')

        return result_dict


class CentralRadialVelocity(object):
    @staticmethod
    def centarl_rv_model_to_fit(x, *args):
        xs, ys, period, kwords, fixed, suppress_logger, observer, on_normalized = args
        x = param_renormalizer(x, kwords)
        kwargs = {k: v for k, v in zip(kwords, x)}
        kwargs.update(fixed)
        fn = model.central_rv_synthetic
        synthetic = logger_decorator(suppress_logger)(fn)(xs, period, observer, **kwargs)
        if on_normalized:
            synthetic = analutils.normalize_rv_curve_to_max(synthetic)
        synthetic = {"primary": synthetic[0], "secondary": synthetic[1]}
        return np.array([np.sum(np.power(synthetic[comp] - ys[comp], 2)) for comp in config.BINARY_COUNTERPARTS])

    @staticmethod
    def fit(xs, ys, period, x0, xtol=1e-15, max_nfev=None, suppress_logger=False, on_normalized=False):
        initial_x0 = copy(x0)
        x0, kwords, fixed, observer = fit_data_initializer(x0)

        args = (xs, ys, period, kwords, fixed, suppress_logger, observer, on_normalized)
        logger.info("fitting radial velocity light curve...")
        func = CentralRadialVelocity.centarl_rv_model_to_fit
        result = least_squares(func, x0, bounds=(0, 1), args=args, max_nfev=max_nfev, xtol=xtol)
        logger.info("fitting finished")

        result = param_renormalizer(result.x, kwords)
        result_dict = {k: v for k, v in zip(kwords, result)}
        result_dict.update(x0_to_fixed_kwargs(initial_x0))

        r_squared_args = xs, ys, period, on_normalized
        r_squared_result = rv_r_squared(model.central_rv_synthetic, *r_squared_args, **result_dict)
        logger.info(f'r_squared: {r_squared_result}')

        return result_dict


circular_sync = CircularSyncLightCurve()
central_rv = CentralRadialVelocity()

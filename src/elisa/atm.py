import itertools
import logging
import os
import sys
import warnings

from queue import Queue
from threading import Thread

import numpy as np
import pandas as pd
from copy import deepcopy
from scipy import integrate, interpolate
from pandas import DataFrame

from elisa.conf import config
from elisa.conf.config import ATM_MODEL_DATAFRAME_FLUX, ATM_MODEL_DATAFRAME_WAVE
from elisa.conf.config import PASSBAND_DATAFRAME_WAVE, PASSBAND_DATAFRAME_THROUGHPUT
from elisa import utils, const
from typing import Iterable


config.set_up_logging()
__logger__ = logging.getLogger("atm")


# * 1e-7 * 1e4 * 1e10 * (1.0/np.pi)

ATLAS_TO_ATM_FILE_PREFIX = {
    "castelli": "ck",
    "castelli-kurucz": "ck",
    "ck": "ck",
    "ck04": "ck",
    "kurucz": "k",
    "k": "k",
    "k93": "k"
}

ATLAS_TO_BASE_DIR = {
    "castelli": config.CK04_ATM_TABLES,
    "castelli-kurucz": config.CK04_ATM_TABLES,
    "ck": config.CK04_ATM_TABLES,
    "ck04": config.CK04_ATM_TABLES,
    "kurucz": config.K93_ATM_TABLES,
    "k": config.K93_ATM_TABLES,
    "k93": config.K93_ATM_TABLES
}

ATM_DOMAIN_QUANTITY_TO_VARIABLE_SUFFIX = {
    "temperature": "TEMPERATURE_LIST_ATM",
    "gravity": "GRAVITY_LIST_ATM",
    "metallicity": "METALLICITY_LIST_ATM"
}


class AtmDataContainer(object):
    def __init__(self, model, temperature, log_g, metallicity, fpath=''):
        self._model = pd.DataFrame([])
        self.temperature = temperature
        self.log_g = log_g
        self.metallicity = metallicity
        self.flux_unit = "flam"
        self.wave_unit = "angstrom"
        # in case this np.pi will stay here, there will be rendundant multiplication in intensity integration
        self.flux_to_si_mult = 1e-7 * 1e4 * 1e10  # * (1.0/np.pi)
        self.wave_to_si_mult = 1e-10
        self.left_bandwidth = np.nan
        self.right_bandwidth = np.nan
        self.fpath = fpath

        setattr(self, 'model', model)

    def is_empty(self):
        """
        Find out wheter model container which carries DataFrame of atmospheric model::

            pd.DataFrame({
                <intensity>: numpy.ndarray([float])
                <wavelength>: numpy.ndarray([float])
            })

        AmtDatContainer instance is empty when model pandas DataFrame container is empty.

        :return: bool
        """
        return self._model.empty

    @property
    def model(self):
        """
        return atmospheric model DataFrame::

            pd.DataFrame({
                <intensity>: numpy.ndarray([float])
                <wavelength>: numpy.ndarray([float])
            })

        :return: pandas.DataFrame
        """
        return self._model

    @model.setter
    def model(self, df):
        """
        Setup model container which carries DataFrame of atmospheric model::

            pd.DataFrame({
                <intensity>: numpy.ndarray([float])
                <wavelength>: numpy.ndarray([float])
            })

        and left and right bandwidth of such container.

        :param df: pandasDataFrame
        :return:
        """
        self._model = df
        self.left_bandwidth = df[ATM_MODEL_DATAFRAME_WAVE].min()
        self.right_bandwidth = df[ATM_MODEL_DATAFRAME_WAVE].max()


class IntensityContainer(object):
    """
    Intended to keep information about integrated radiance for given params.
    """
    def __init__(self, intensity, temperature, log_g, metallicity):
        """
        Initialise container with given parametres.

        :param intensity: float
        :param temperature: float
        :param log_g: float
        :param metallicity: float
        """
        self.intensity = intensity
        self.temperature = temperature
        self.log_g = log_g
        self.metallicity = metallicity


class NaiveInterpolatedAtm(object):
    @staticmethod
    def radiance(temperature, log_g, metallicity, atlas, **kwargs):
        """
        Compute radiance for given atmospheric parametres with regards to given passbands.

        :param temperature: numpy.ndarray
        :param log_g: numpy.ndarray
        :param metallicity: float
        :param atlas: str
        :param kwargs:
        :**kwargs options**:
                * **left_bandwidth** * -- float; maximal allowed wavelength from left
                * **right_bandwidth** * -- float; maximal allowed wavelength from right
                * **passband** * -- Dict[str, elisa.observer.observer.PassbandContainer]
        :return: list
        """
        # fixme: uncomment following line
        # validate_atm(temperature, log_g, metallicity, atlas)
        l_bandw, r_bandw = kwargs["left_bandwidth"], kwargs["right_bandwidth"]
        passband_containers = kwargs["passband"]
        # related atmospheric files for each face (upper and lower)
        atm_files = NaiveInterpolatedAtm.atm_files(temperature, log_g, metallicity, atlas)
        # find unique atmosphere data files
        unique_atms, containers_map = read_unique_atm_tables(atm_files)
        # get multiplicators to transform containers from any units to si
        flux_mult, wave_mult = find_atm_si_multiplicators(unique_atms)
        # common wavelength coverage of atmosphere models
        global_left, global_right = find_global_atm_bandwidth(unique_atms)
        # strip unique atmospheres to passbands coverage
        unique_atms = strip_atm_containers_by_bandwidth(unique_atms, l_bandw, r_bandw,
                                                        global_left=global_left, global_right=global_right)

        # alignement of atmosphere containers wavelengths for convenience
        unique_atms = arange_atm_to_same_wavelength(unique_atms)
        passbanded_atm_containers = apply_passband(unique_atms, passband_containers,
                                                   global_left=global_left, global_right=global_right)

        flux_matrices = remap_passbanded_unique_atms_to_matrix(passbanded_atm_containers, containers_map)
        atm_containers = remap_passbanded_unique_atms_to_origin(passbanded_atm_containers, containers_map)
        localized_atms = NaiveInterpolatedAtm.interpolate_spectra(atm_containers, flux_matrices,
                                                                  temperature=temperature)

        return compute_normal_intensities(localized_atms, flux_mult=flux_mult, wave_mult=wave_mult)

    @staticmethod
    def compute_interpolation_weights(temperatures, top_atm_containers, bottom_atm_containers):
        """
        Compute interpolation weights between two models of atmoshperes.
        Weights are computet as::

            (temperatures - bottom_temperatures) / (top_temperatures - bottom_temperatures)

        what means we use linear approach.
        If there is np.nan (it cames from same surounded values), such value is replaced with 1.0.
        1.0 is choosen to fit interpolation method and return correct atmosphere.

        :param temperatures: numpy.ndarray[float]
        :param top_atm_containers: numpy.ndarray[AtmDataContainer]
        :param bottom_atm_containers: numpy.ndarray[AtmDataContainer]
        :return: numpy.ndarray[float]
        """
        top_temperatures = np.array([a.temperature for a in top_atm_containers])
        bottom_temperatures = np.array([a.temperature for a in bottom_atm_containers])
        result = (temperatures - bottom_temperatures) / (top_temperatures - bottom_temperatures)
        result[np.isnan(result)] = 1.0
        return result

    @staticmethod
    def compute_unknown_intensity_from_surounded_containers(weight, top_atm_container: AtmDataContainer,
                                                            bottom_atm_container: AtmDataContainer):
        """
        Depends on weight will compute (interpolate) intensities from surounded intensities
        related to given temperature.
        ! Top and bottom atmosphere model are have to be defined in same wavelengths !

        :param weight: Iterable[float]
        :param top_atm_container: AtmDataContainer
        :param bottom_atm_container: AtmDataContainer
        :return: Tuple[numpy.ndarray, numpy.ndarray]; (flux, wave)
        """
        if bottom_atm_container is None:
            return top_atm_container.model[ATM_MODEL_DATAFRAME_FLUX], top_atm_container.model[ATM_MODEL_DATAFRAME_WAVE]

        # reset index is neccessary; otherwise add/mult/... method od DataFrame
        # leads to nan if left and right frame differ in indices
        top_atm_container.model.reset_index(drop=True, inplace=True)
        bottom_atm_container.model.reset_index(drop=True, inplace=True)

        intensity = weight * (
            top_atm_container.model[ATM_MODEL_DATAFRAME_FLUX] - bottom_atm_container.model[ATM_MODEL_DATAFRAME_FLUX]
        ) + bottom_atm_container.model[ATM_MODEL_DATAFRAME_FLUX]

        return intensity, top_atm_container.model[ATM_MODEL_DATAFRAME_WAVE]

    @staticmethod
    def compute_unknown_intensity_from_surounded_flux_matrices(weights, top_flux_matrix, bottom_flux_matrix):
        return (weights * (top_flux_matrix.T - bottom_flux_matrix.T) + bottom_flux_matrix.T).T

    @staticmethod
    def interpolate_spectra(passbanded_atm_containers, flux_matrices, temperature):
        """
        From supplied AtmDataContainer's, `flux_matrices` and `temeprature`.
        Interpolation is computed in vector form::

            (weights * (top_flux_matrix.T - bottom_flux_matrix.T) + bottom_flux_matrix.T).T

        where `top_flux_matrix` and `bottom_flux_matrix`, are entire matrix where rows are represented by fluxes.
        It also means, to be able do such interpolation, fluxes have to be on same wavelengths for each row.

        :param flux_matrices: Dict[str, numpy.ndarray];

        ::

            {"passband": numpy.ndarray (matrix)}

        :param passbanded_atm_containers: Dict[str, AtmDataContainers]
        :param temperature: numpy.ndarray[float]
        :return: Dict[str, numpy.ndarray];
        """

        interp_band = dict()
        for band, flux_matrix in flux_matrices.items():
            band_atm = passbanded_atm_containers[band]
            bottom_flux, top_flux = flux_matrix[:len(flux_matrix) // 2], flux_matrix[len(flux_matrix) // 2:]
            bottom_atm, top_atm = band_atm[:len(band_atm) // 2], band_atm[len(band_atm) // 2:]

            __logger__.debug(f"computing atmosphere interpolation weights for band: {band}")
            interpolation_weights = NaiveInterpolatedAtm.compute_interpolation_weights(temperature, top_atm, bottom_atm)
            flux = NaiveInterpolatedAtm.compute_unknown_intensity_from_surounded_flux_matrices(
                interpolation_weights, top_flux, bottom_flux
            )
            interp_band[band] = {
                ATM_MODEL_DATAFRAME_FLUX: flux, ATM_MODEL_DATAFRAME_WAVE: find_atm_defined_wavelength(top_atm)
            }
        return interp_band

    @staticmethod
    def atm_tables(fpaths):
        """
        Read atmosphere tables as pandas.DataFrame's.

        :param fpaths: Iterable, Iterable of paths which points desired atm csv files
        :return: List[AtmDataContainer] of pandas.DataFrame`s
        """
        result_queue = multithread_atm_tables_reader_runner(fpaths)
        models = [qval for qval in utils.IterableQueue(result_queue)]
        models = [val[1] for val in sorted(models, key=lambda x: x[0])]
        return models

    @staticmethod
    def atm_files(temperature, log_g, metallicity, atlas):
        """
        For given parameters will find out related atm csv tables and return list of paths to this csv files.

        :param temperature: Iterable[float]
        :param log_g: Iterable[float]
        :param metallicity: float
        :param atlas: str
        :return: List[str]
        """
        atlas = validated_atlas(atlas)

        g_array = np.array(atm_file_prefix_to_quantity_list("gravity", atlas))
        m_array = np.array(atm_file_prefix_to_quantity_list("metallicity", atlas))
        t_array = np.array(atm_file_prefix_to_quantity_list("temperature", atlas))

        g = utils.find_nearest_value_as_matrix(g_array, log_g)[0]
        m = utils.find_nearest_value_as_matrix(m_array, metallicity)[0][0]
        t = utils.find_surrounded_as_matrix(t_array, temperature)

        domain_df = DataFrame({
            # "temp": list(t[0]) + list(t[1]),
            "temp": t.flatten('F'),
            "log_g": np.tile(g, 2),
            "mh": np.repeat(m, len(g) * 2)
        })
        directory = get_atm_directory(m, atlas)
        fnames = str(atlas) + \
            domain_df["mh"].apply(lambda x: utils.numeric_metallicity_to_string(x)) + "_" + \
            domain_df["temp"].apply(lambda x: str(int(x))) + "_" + \
            domain_df["log_g"].apply(lambda x: utils.numeric_logg_to_string(x))

        return list(os.path.join(str(ATLAS_TO_BASE_DIR[atlas]), str(directory)) + os.path.sep + fnames + ".csv")


def arange_atm_to_same_wavelength(atm_containers):
    """
    Function aligns all atmosphere profiles to the same wavelengths.

    :param atm_containers: Iterable[AtmDataContainer]; atmosphere containers which wavelengths should be aligned
    :return: Iterable[AtmDataContainer]; wavelength aligned atmospheric containers
    """
    wavelengths = np.unique(np.array([atm.model[ATM_MODEL_DATAFRAME_WAVE] for atm in atm_containers]).flatten())
    wavelengths.sort()
    result = list()

    # this code checks if the containers are already alligned
    s_size = sys.maxsize
    for atm in atm_containers:
        s_size = len(atm.model) if len(atm.model) < s_size else s_size

    # if yes, interpolation is unnecessary
    if s_size == len(wavelengths):
        return atm_containers

    # otherwise interpolation is utilized
    for atm in atm_containers:
        i = interpolate.Akima1DInterpolator(atm.model[ATM_MODEL_DATAFRAME_WAVE], atm.model[ATM_MODEL_DATAFRAME_FLUX])
        df = DataFrame({
            ATM_MODEL_DATAFRAME_WAVE: wavelengths,
            ATM_MODEL_DATAFRAME_FLUX: i(wavelengths),
        })
        atm.model = df.fillna(0.0)
        result.append(atm)
    return result


def strip_atm_containers_by_bandwidth(atm_containers, left_bandwidth, right_bandwidth, **kwargs):
    """
    Strip all loaded atm models to common wavelength coverage.

    :param atm_containers: List[AtmDataContainer]
    :param left_bandwidth: float
    :param right_bandwidth: float
    :param kwargs:
    :**kwargs options**:
            * **global_left** * -- float; global wavelength from left where flux for all supllied atmposhperes exist
            * **global_right** * -- float; global wavelength from right where flux for all supllied atmposhperes exist
    :return: List[AtmDataContainer]
    """
    return [strip_atm_container_by_bandwidth(atm_container, left_bandwidth, right_bandwidth, **kwargs)
            for atm_container in atm_containers]


def strip_atm_container_by_bandwidth(atm_container: AtmDataContainer, left_bandwidth, right_bandwidth, **kwargs):
    """
    Strip atmosphere container model by given bandwidth.
    Usually is model in container defined somewhere in between of left and right bandwidth, never exactly in such
    wavelength. To strip container exactly on bandwidth wavelength, interpolation has to be done. In case, when
    model of any atmosphere has smaller real bandwidth, than bandwidth defined by arguments `right_bandwidth` and
    `left_bandwidth` (it happens in case of bolometric passband), global bandwidth of given atmospheres is used.
    Right gloal bandwidth is obtained as min of all maximal wavelengts from all models and left is max of all mins.


    :param atm_container: AtmDataContainer
    :param left_bandwidth: float
    :param right_bandwidth: float
    :param kwargs:
    :**kwargs options**:
            * **global_left** * -- float; global wavelength from left where flux for all supllied atmposhperes exist
            * **global_right** * -- float; global wavelength from right where flux for all supllied atmposhperes exist
            * **inplace** * -- bool; if set to True; instead of creation of new DataFrames in AtmDataContainers,
                                     just existing is inplaced (changed)

    :return: AtmDataContainer
    """
    inplace = kwargs.get('inplace', False)
    if atm_container.is_empty():
        ValueError('Atmosphere container is empty.')

    # evaluate whether use argument bandwidth or global bandwidth
    # use case when use global bandwidth is in case of bolometric `filter`, where bandwidth in observer
    # is set as generic left = 0 and right sys.float.max
    atm_df = atm_container.model
    wave_col = ATM_MODEL_DATAFRAME_WAVE

    if atm_df[wave_col].min() > left_bandwidth or atm_df[wave_col].max() < right_bandwidth:
        mi, ma = find_global_atm_bandwidth([atm_container])
        left_bandwidth, right_bandwidth = kwargs.get("global_left", mi), kwargs.get("global_right", ma)
        warnings.warn('You attempt to strip an atmosphere model to bandwidth which at least partially outside '
                      'original atmosphere model wavelength coverage. This may cause problems.')

        if not kwargs.get('global_left') or not kwargs.get('global_right'):
            warnings.warn(f"argument bandwidth is out of bound for supplied atmospheric model\n"
                          f"to avoid interpolation error in boundary wavelength, bandwidth was defined as "
                          f"max {ma} and min {mi} of wavelengt in given model table\n"
                          f"it might leads to error in atmosphere interpolation\n"
                          f"to avoid this problem, please specify global_left and global_right bandwidth as "
                          f"kwargs for given method and make sure all models wavelengths "
                          f"are greater or equal to such limits")
    return strip_to_bandwidth(atm_container, left_bandwidth, right_bandwidth, inplace=inplace)


def strip_to_bandwidth(atm_container, left_bandwidth, right_bandwidth, inplace=False):
    """
    Function directly strips atm container to given bandwidth.

    :param atm_container: AtmDataContainer; atm container to strip
    :param left_bandwidth: float
    :param right_bandwidth: float
    :param inplace: if True `atm_container' is overwritten by striped atmosphere container
    :return: AtmDataContainer
    """
    # indices in bandwidth
    valid_indices = list(
        atm_container.model.index[
            atm_container.model[ATM_MODEL_DATAFRAME_WAVE].between(left_bandwidth, right_bandwidth, inclusive=False)
        ])
    # extend left  and right index (left - 1 and right + 1)
    left_extention_index = valid_indices[0] - 1 if valid_indices[0] >= 1 else 0
    right_extention_index = valid_indices[-1] + 1 \
        if valid_indices[-1] < atm_container.model.last_valid_index() else valid_indices[-1]
    atm_cont = atm_container if inplace else deepcopy(atm_container)
    atm_cont.model = atm_cont.model.iloc[
        np.unique([left_extention_index] + valid_indices + [right_extention_index])
    ]
    return extend_atm_container_on_bandwidth_boundary(atm_cont, left_bandwidth, right_bandwidth)


def find_global_atm_bandwidth(atm_containers):
    """
    Function finds common wavelength coverage of the atmosphere models.

    :param atm_containers: AtmDataContainer
    :return: Tuple[float, float]; minimum, maximum wavelength of common coverage (in Angstrom)
    """
    bounds = np.array([
        [atm.model[ATM_MODEL_DATAFRAME_WAVE].min(),
         atm.model[ATM_MODEL_DATAFRAME_WAVE].max()] for atm in atm_containers])
    return bounds[:, 0].max(), bounds[:, 1].min()


def extend_atm_container_on_bandwidth_boundary(atm_container, left_bandwidth, right_bandwidth):
    """
    Function crops the wavelength boundaries of the atmosphere model to the precise boundaries defined by
    `left_bandwidth` and `right_bandwidth`.

    :param atm_container: AtmDataContainer
    :param left_bandwidth: float
    :param right_bandwidth: float
    :return: AtmDataContainer
    """
    interpolator = interpolate.Akima1DInterpolator(atm_container.model[ATM_MODEL_DATAFRAME_WAVE],
                                                   atm_container.model[ATM_MODEL_DATAFRAME_FLUX])

    # interpolating values precisely on the border of the filter(s) coverage
    on_border_flux = interpolator([left_bandwidth, right_bandwidth])
    if np.isin(np.nan, on_border_flux):
        raise ValueError('Interpolation on bandwidth boundaries led to NaN value.')
    df: DataFrame = atm_container.model

    df.values[[0, -1], :] = np.array([[on_border_flux[0], left_bandwidth], [on_border_flux[1], right_bandwidth]])
    df.values[:, 1] = np.round(df.values[:, 1], 10)

    df.reset_index(drop=True, inplace=True)
    atm_container.model = df
    return atm_container


def apply_passband(atm_containers, passband, **kwargs):
    """
    Function applies passband response functions to the stripped atmosphere models.

    :param atm_containers: AtmDataContainer
    :param passband: Dict[str, PassbandContainer]
    :return: Dict[str, AtmDataContainer]
    """
    passbanded_atm_containers = dict()
    __logger__.debug("applying passband functions on given atmospheres")
    for band, band_container in passband.items():
        passbanded_atm_containers[band] = list()
        for atm_container in atm_containers:
            # strip atm container on passband bandwidth (reason to do it is, that container
            # is stripped on maximal bandwidth defined by all bands, not just by given single band)
            atm_container = strip_to_bandwidth(
                atm_container=deepcopy(atm_container),
                left_bandwidth=band_container.left_bandwidth,
                right_bandwidth=band_container.right_bandwidth,
                inplace=False
            )
            # found passband throughput on atm defined wavelength
            passband_df = DataFrame(
                {
                    PASSBAND_DATAFRAME_THROUGHPUT: band_container.akima(atm_container.model[ATM_MODEL_DATAFRAME_WAVE]),
                    PASSBAND_DATAFRAME_WAVE: atm_container.model[ATM_MODEL_DATAFRAME_WAVE]
                }
            )
            passband_df.fillna(0.0, inplace=True)
            atm_container.model[ATM_MODEL_DATAFRAME_FLUX] *= passband_df[PASSBAND_DATAFRAME_THROUGHPUT]
            passbanded_atm_containers[band].append(atm_container)
    __logger__.debug("passband application finished")
    return passbanded_atm_containers


def build_atm_validation_hypertable(atlas):
    """
    Prepare validation hypertable to validate atmospheric model (whether is in interpolation bounds).

    :param atlas: str
    :return: Dict
    """
    atlas = validated_atlas(atlas)
    all_files = get_list_of_all_atm_tables(atlas)
    filenames = (os.path.basename(f) for f in all_files)
    quantities = sorted([parse_domain_quantities_from_atm_table_filename(f) for f in filenames], key=lambda x: x[0])
    temp_qroups = itertools.groupby(quantities, key=lambda x: x[0])
    hypertable = {
        str(int(temp_qroup[0])):
            {
                "gravity": sorted(set(np.array(list(temp_qroup[1])).T[1])),
                # mettalicity is stored in this dict just because of consitency
                "metallicity": atm_file_prefix_to_quantity_list("metallicity", atlas)
            }
        for temp_qroup in temp_qroups
    }
    return hypertable


def is_out_of_bound(in_arr, values, tolerance):
    """
    Figure out whether `values` are in `in_arr`. Use `tolerance` if you there is allowed.

    :param in_arr: numpy.ndarray
    :param values: numpy.ndarray
    :param tolerance: float
    :return: List[bool]
    """
    values = [values] if not isinstance(values, Iterable) else values
    top, bottom = max(in_arr) + tolerance, min(in_arr) - tolerance
    return [False if bottom <= val <= top else True for val in values]


# pay attention to those methods bellow
# in the future for different atm model might happen that function won't be valid anymore
def validate_temperature(temperature, atlas, _raise=True):
    """
    Validate `temperature`s for existing `atlas`.

    :param temperature: numpy.ndarray
    :param atlas: str
    :param _raise: bool; if True, raise ValueError
    :return: bool
    """
    atlas = validated_atlas(atlas)
    allowed = sorted(atm_file_prefix_to_quantity_list("temperature", atlas))
    invalid = any([True if (allowed[-1] < t or t < allowed[0]) else False for t in temperature])
    if invalid:
        if _raise:
            raise ValueError("any temperature in system atmosphere is out of bound; "
                             "it is usually caused by invalid physical model")
        return False
    return True


def validate_metallicity(metallicity, atlas, _raise=True):
    """
    Validate `metallicity`s for existing `atlas`.

    :param metallicity: float
    :param atlas: float
    :param _raise: bool; if True, raise ValueError
    :return: bool
    """
    out_of_bound_tol = 0.1  # how far `out of bound` can any value of metallicity runs
    atlas = validated_atlas(atlas)
    allowed = sorted(atm_file_prefix_to_quantity_list("metallicity", atlas))
    out_of_bound = is_out_of_bound(allowed, metallicity, out_of_bound_tol)
    if any(out_of_bound):
        if _raise:
            raise ValueError(f"any metallicity in system atmosphere is out of bound, allowed values "
                             f"are in range <{min(allowed) - out_of_bound_tol}, {max(allowed) + out_of_bound_tol}>; "
                             f"it is usually caused by invalid physical model")
        return False
    return True


def validate_logg(log_g, atlas: str):
    # not implemented, naive implementation is uselles
    # proper `like` implementaion is _validate_logg
    pass


def _validate_logg(temperature, log_g, atlas, _raise=True):
    """
    Validate `logg`s for existing `atlas` and `temperature`.

    :param temperature: numpy.ndarray
    :param log_g: numpy.ndarray
    :param atlas: str
    :param _raise: bool; if True, raise ValueError
    :return: bool
    """
    # it has a different name because there is a different interface
    validation_hypertable = build_atm_validation_hypertable(atlas)
    allowed = sorted(atm_file_prefix_to_quantity_list("temperature", atlas))

    invalid = [
        is_out_of_bound(validation_hypertable[
                            str(int(utils.find_nearest_value(allowed, t)[0]))
                        ]["gravity"], [g], 0.1)[0] for t, g in zip(temperature, log_g)]
    if any(invalid):
        if _raise:
            raise ValueError("any gravity (log_g) in system atmosphere is out of bound; "
                             "it is usually caused by invalid physical model")
        return False
    return True


def validate_atm(temperature, log_g, metallicity, atlas, _raise=True):
    """
    Validate atmosphere.
    Run methods::

        validate_temperature
        validate_metallicity
        _validate_logg

    If anything is not right and `_raise` set to True, raise ValueError.

    :param temperature: numpy.ndarray
    :param log_g: numpy.ndarray
    :param metallicity: float
    :param atlas: str
    :param _raise: bool; if True, raise ValueError
    :return: bool
    """
    try:
        metallicity = [metallicity] * len(temperature) if not isinstance(metallicity, Iterable) else metallicity
        validate_temperature(temperature, atlas)
        validate_metallicity(metallicity, atlas)
        _validate_logg(temperature, log_g, atlas)
    except ValueError:
        if not _raise:
            return False
        raise
    return True


def atm_file_prefix_to_quantity_list(qname: str, atlas: str):
    """
    Get list of available values for given atm domain quantity, e.g. list of temperatures available in atlas CK04.

    :param qname: str; e.g. `temperature`, `metallicity`, `gravity`
    :param atlas: str; e.g. `castelli` or `ck04`
    :return: List
    """
    atlas = validated_atlas(atlas)
    return getattr(const, f"{str(atlas).upper()}_{str(ATM_DOMAIN_QUANTITY_TO_VARIABLE_SUFFIX[qname])}")


def validated_atlas(atlas):
    """
    Get validated atm atlas, e.g. `castelli` or `ck04` transform to `ck`, it matches folder
    and file prefix for given atlas.

    :param atlas: str; e.g. `castelli` or `ck04`
    :return: str
    """
    try:
        return ATLAS_TO_ATM_FILE_PREFIX[atlas]
    except KeyError:
        raise KeyError(f'Incorrect atlas. Following are allowed: {", ".join(ATLAS_TO_ATM_FILE_PREFIX.keys())}')


def parse_domain_quantities_from_atm_table_filename(filename: str):
    """
    Parse filename to given quantities, e.g. ckm05_3500_g15.csv parse to tuple (-0.5, 3500, 1.5)

    :param filename: str
    :return: Tuple[float, float, float]
    """
    return get_temperature_from_atm_table_filename(filename), get_logg_from_atm_table_filename(
        filename), get_metallicity_from_atm_table_filename(filename)


def get_metallicity_from_atm_table_filename(filename):
    """
    Get metallicity as number from filename / directory.

    :param filename: str
    :return: float
    """
    m = str(filename).split("_")[0][-3:]
    sign = 1 if str(m).startswith("p") else -1
    value = float(m[1:]) / 10.0
    return value * sign


def get_temperature_from_atm_table_filename(filename):
    """
    Get temperature from filename / directory name.

    :param filename: str
    :return: float
    """
    return float(str(filename).split("_")[1])


def get_logg_from_atm_table_filename(filename):
    """
    Get logg from filename / directory name.

    :param filename: str
    :return: float
    """
    filename = filename if not str(filename).endswith(".csv") else str(filename).replace('.csv', '')
    g = str(filename).split("_")[2][1:]
    return int(g) / 10.0


def get_atm_table_filename(temperature, log_g, metallicity, atlas):
    """
    Get filename based on given descriptive values.

    :param temperature: float
    :param log_g: float
    :param metallicity: float
    :param atlas: str; e.g. `castelli` or `ck04`
    :return: str
    """
    prefix = validated_atlas(atlas)
    return \
        f"{prefix}{utils.numeric_metallicity_to_string(metallicity)}_" \
        f"{int(temperature)}_{utils.numeric_logg_to_string(log_g)}.csv"


def get_atm_directory(metallicity, atlas):
    """
    Get table directory name based on given descriptive values.

    :param metallicity: float
    :param atlas: str; e.g. `castelli` or `ck04`
    :return: str
    """
    prefix = validated_atlas(atlas)
    return f"{prefix}{utils.numeric_metallicity_to_string(metallicity)}"


def get_atm_table(temperature, log_g, metallicity, atlas):
    """
    Get dataframe for flux and wavelengths for given values and atlas.
    (Read csv file)

    :param temperature: float
    :param log_g: float
    :param metallicity: float
    :param atlas: str - e.g. `castelli` or `ck04`
    :return: pandas.DataFrame
    """
    directory = get_atm_directory(metallicity, atlas)
    filename = get_atm_table_filename(temperature, log_g, metallicity, atlas)
    path = os.path.join(ATLAS_TO_BASE_DIR[atlas], directory, filename) if directory is not None else \
        os.path.join(ATLAS_TO_BASE_DIR[atlas], filename)

    if not os.path.isfile(path):
        raise FileNotFoundError(f"there is no file like {path}")
    return pd.read_csv(path, dtype=config.ATM_MODEL_DATAFARME_DTYPES)


def get_list_of_all_atm_tables(atlas):
    """
    Get list of all available atm table files stored in configured location.

    :param atlas: str; e.g. `castelli` or `ck04`
    :return: List[str]
    """
    source = ATLAS_TO_BASE_DIR[validated_atlas(atlas)]
    matches = list()
    for root, dirnames, filenames in os.walk(source):
        for filename in filenames:
            if filename.endswith(('.csv',)):
                matches.append(os.path.join(root, filename))
    return matches


def multithread_atm_tables_reader(path_queue, error_queue, result_queue):
    """
    Multithread reader of atmosphere csv files.

    :param path_queue: Queue
    :param error_queue: Queue
    :param result_queue: Queue
    :return:
    """
    while True:
        args = path_queue.get(timeout=1)
        if args == "TERMINATOR":
            break
        if not error_queue.empty():
            break
        index, file_path = args
        if file_path is None:
            # consider put here an empty container
            result_queue.put((index, None))
            continue
        try:
            t, l, m = parse_domain_quantities_from_atm_table_filename(os.path.basename(file_path))
            atm_container = AtmDataContainer(pd.read_csv(file_path), t, l, m, file_path)
            result_queue.put((index, atm_container))
        except Exception as we:
            error_queue.put(we)
            break


def multithread_atm_tables_reader_runner(fpaths):
    """
    Run multithread reader of csv files containing atmospheric models.

    :param fpaths: Iterable[str]
    :return: Queue
    """
    n_threads = config.NUMBER_OF_THREADS

    path_queue = Queue(maxsize=len(fpaths) + n_threads)
    result_queue = Queue()
    error_queue = Queue()

    threads = list()
    try:
        for index, fpath in enumerate(fpaths):
            if not os.path.isfile(fpath):
                raise FileNotFoundError(f"file {fpath} doesn't exist. it seems your model could be not physical")
            path_queue.put((index, fpath))

        for _ in range(n_threads):
            path_queue.put("TERMINATOR")

        __logger__.debug("initialising multithread atm table reader")
        for _ in range(n_threads):
            t = Thread(target=multithread_atm_tables_reader, args=(path_queue, error_queue, result_queue))
            threads.append(t)
            t.daemon = True
            t.start()

        for t in threads:
            t.join()
        __logger__.debug("atm multithread reader finished all jobs")
    except KeyboardInterrupt:
        raise
    finally:
        if not error_queue.empty():
            raise error_queue.get()
    return result_queue


def compute_normal_intensities(matrices_dict, flux_mult=1.0, wave_mult=1.0):
    """
    Run `compute_normal_intensity` method for each band in `matrices_dict`.

    :param matrices_dict: Dict
    :param flux_mult: float
    :param wave_mult: float
    :return: Dict[str, float]
    """
    return {
        band: compute_normal_intensity(
            spectral_flux=dflux[ATM_MODEL_DATAFRAME_FLUX],
            wavelength=dflux[ATM_MODEL_DATAFRAME_WAVE],
            flux_mult=flux_mult,
            wave_mult=wave_mult
        )
        for band, dflux in matrices_dict.items()
    }


def compute_normal_intensity(spectral_flux, wavelength, flux_mult=1.0, wave_mult=1.0):
    """
    Calculates normal flux for all surface faces.

    :param spectral_flux: numpy.ndarray; interpolated atmosphere models for each face (N_face x wavelength)
    :param wavelength: numpy.ndarray or Series; wavelengths of atmosphere models
    :param flux_mult: float;
    :param wave_mult: float;
    :return: numpy.ndarray
    """
    return np.pi * flux_mult * wave_mult * integrate.simps(spectral_flux, wavelength, axis=1)


def compute_integral_si_intensity_from_passbanded_dict(passbaned_dict):
    return {
        band: compute_integral_si_intensity_from_atm_data_containers(passbanded_atm)
        for band, passbanded_atm in passbaned_dict.items()
    }


def compute_integral_si_intensity_from_atm_data_containers(atm_data_containers):
    """
    Returns intensity from given atmosphere models.
    If models are already strip by passband, result is also striped

    :param atm_data_containers: Iterable[AtmDataContainer]
    :return: List[AtmDataContainer]; integrated `flux` from each AtmDataContainer on `wave` in given container
    """
    return [
        IntensityContainer(
            intensity=np.pi * integrate.simps(adc.model[ATM_MODEL_DATAFRAME_FLUX] * adc.flux_to_si_mult,
                                              adc.model[ATM_MODEL_DATAFRAME_WAVE] * adc.wave_to_si_mult),
            temperature=adc.temperature,
            log_g=adc.log_g,
            metallicity=adc.metallicity
        )
        for adc in atm_data_containers
    ]


def unique_atm_fpaths(fpaths):
    """
    Group atm table names and return such set and map to origin list.

    :param fpaths: List[str]
    :return: Tuple[str, Dict];

    ::

        (path set - set of unique atmosphere file names,
         map - dict where every unique atm file has listed indices where it occures)
    """
    fpaths_set = set(fpaths)
    fpaths_map = {key: list() for key in fpaths_set}
    for idx, key in enumerate(fpaths):
        fpaths_map[key].append(idx)
    return fpaths_set, fpaths_map


def remap_passbanded_unique_atms_to_origin(passbanded_containers, fpaths_map):
    """
    Remap atm containers in supplied order by `fpaths_map`.

    :param passbanded_containers: Dict[str, AtmDataContainer]
    :param fpaths_map: Dict[str, List[int]]; map
    :return: Dict[str, List]
    """
    return {band: remap_unique_atm_container_to_origin(atm, fpaths_map) for band, atm in passbanded_containers.items()}


def remap_unique_atm_container_to_origin(models, fpaths_map):
    """
    Remap atm container in supplied order by `fpaths_map`.

    :warnign: assigned containers are mutable, if you will change content of any container, changes will affect
    any other container with same reference

    :param models: List[AtmDatContainer]
    :param fpaths_map: :param fpaths_map: Dict[str, List[int]]; map
    :return: List[AtmDataContainer]
    """
    models_arr = np.empty(max(list(itertools.chain.from_iterable(fpaths_map.values()))) + 1, dtype='O')
    for model in models:
        models_arr[fpaths_map[model.fpath]] = model
    return models_arr


def read_unique_atm_tables(fpaths):
    """
    Returns atmospheric spectra from table files which encompass the range of surface parameters on the component's
    surface

    :parma fpaths; List[str]
    :return: Tuple[AtmDataContainers, Dict[str, List]];

    ::

        (List of unique AtmDataContainers, map - dict where every unique atm file has listed indices where it occures)
    """
    fpaths, fpaths_map = unique_atm_fpaths(fpaths)
    result_queue = multithread_atm_tables_reader_runner(fpaths)
    models = [qval[1] for qval in utils.IterableQueue(result_queue) if qval[1] is not None]
    return models, fpaths_map


def find_atm_si_multiplicators(atm_containers):
    """
    Get atm flux and wavelength multiplicator from `atm_containers`.
    It assume, all containers have the same multiplicators, so it returns values from first one.

    :param atm_containers: List[AtmDatacontainer]
    :return: Tuple[float, float]

    ::

        (flux multiplicator, wavelength multiplicator)

    """
    for atm_container in atm_containers:
        return atm_container.flux_to_si_mult, atm_container.wave_to_si_mult
    raise ValueError('No valid atmospheric container has been supplied to method.')


def find_atm_defined_wavelength(atm_containers):
    """
    Get wavelength from first container from `atm_containers` list.
    It assume all containers has already aligned wavelengths to same.

    :param atm_containers: Iterable[AtmDataContainer]
    :return: numpy.ndarray[float]
    """
    for atm_container in atm_containers:
        return atm_container.model[ATM_MODEL_DATAFRAME_WAVE]
    raise ValueError('No valid atmospheric container has been supplied to method.')


def remap_passbanded_unique_atms_to_matrix(passbanded_containers, fpaths_map):
    """
    Run `remap_passbanded_unique_atm_to_matrix` for reach container in `passbanded_containers`.

    :param passbanded_containers: List[]
    :param fpaths_map: Dict[str, List[int]]; map - atmosphere container to faces
    :return: Dict[str, numpy.ndarray]
    """
    return {band: remap_passbanded_unique_atm_to_matrix(atm, fpaths_map) for band, atm in passbanded_containers.items()}


def remap_passbanded_unique_atm_to_matrix(atm_containers, fpaths_map):
    """
    Creating matrix of atmosphere models for each face.

    :param atm_containers: List[AtmDataContainer]; list of unique atmosphere containers from tables
    :param fpaths_map: Dict[str, List[int]]; map - atmosphere container to faces
    :return: numpy.ndarray; matrix of atmosphere models
    """
    total = max(list(itertools.chain.from_iterable(fpaths_map.values()))) + 1
    wavelengths_defined = find_atm_defined_wavelength(atm_containers)
    wavelengths_length = len(wavelengths_defined)
    models_matrix = np.zeros((total, wavelengths_length))

    for atm_container in atm_containers:
        models_matrix[fpaths_map[atm_container.fpath]] = atm_container.model[ATM_MODEL_DATAFRAME_FLUX]
    return models_matrix


if __name__ == "__main__":
    pass

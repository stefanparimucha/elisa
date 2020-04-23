from elisa.conf.config import BINARY_COUNTERPARTS, PASSBANDS
from elisa.base.transform import TransformProperties
from elisa.analytics.dataset.base import RVData, LCData


class AnalyticsProperties(TransformProperties):
    @staticmethod
    def radial_velocities(value):
        if isinstance(value, dict):
            for key, val in value.items():
                if key not in BINARY_COUNTERPARTS:
                    raise ValueError(f'{key} is invalid designation for radial velocity dataset. '
                                     f'Please choose from {BINARY_COUNTERPARTS.keys()}')
                elif not isinstance(val, RVData):
                    raise TypeError(f'{val} is not of instance of RVData class.')
            return value
        raise TypeError('`radial_velocities` are not of type `dict`')

    @staticmethod
    def light_curves(value):
        if isinstance(value, dict):
            for key, val in value.items():
                if key not in PASSBANDS:
                    raise ValueError(f'{key} is invalid passband. Please choose '
                                     f'from available passbands: \n{PASSBANDS}')
                elif not isinstance(val, LCData):
                    raise TypeError(f'{val} is not of instance of LCData class.')
            return value
        raise TypeError('`light_curves` are not of type `dict`')

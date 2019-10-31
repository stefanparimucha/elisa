import numpy as np

from astropy import units as au
from elisa import units, const
from elisa.base.transform import SystemProperties, WHEN_FLOAT64, quantity_transform


class SingleSystemProperties(SystemProperties):
    @staticmethod
    def rotation_period(value):
        """
        Transform and validate rotational period of star in single star system, if unit is not specified, default period
        unit is assumed
        :param value: quantity or float; rotation period
        :return:
        """
        return quantity_transform(value, units.PERIOD_UNIT, WHEN_FLOAT64)

    @staticmethod
    def reference_time(value):
        """
        Transform and validity check for reference time.

        :param value: (numpy.)int, (numpy.)float, astropy.unit.quantity.Quantity
        :return: float
        """
        return quantity_transform(value, units.PERIOD_UNIT, WHEN_FLOAT64)

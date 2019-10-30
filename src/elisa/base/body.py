import numpy as np

from copy import copy
from abc import (
    ABCMeta,
    abstractmethod
)
from elisa.utils import is_empty
from elisa.base.spot import Spot
from elisa import (
    logger,
    units,
    umpy as up
)


class Body(metaclass=ABCMeta):
    """
    Abstract class that defines bodies that can be modelled by this software.
    Units are imported from astropy.units module::

        see documentation http://docs.astropy.org/en/stable/units/
    """

    ID = 1

    def __init__(self, name, logger_name=None, suppress_logger=False, **kwargs):
        """
        Properties of abstract class Body.
        """
        # initial kwargs
        self.kwargs = copy(kwargs)
        self._suppress_logger = suppress_logger
        self._logger = logger.getLogger(logger_name or self.__class__.__name__, suppress=self._suppress_logger)

        if is_empty(name):
            self.name = str(Body.ID)
            self._logger.debug(f"name of class instance {self.__class__.__name__} set to {self.name}")
            Body.ID += 1
        else:
            self.name = str(name)

        # initializing parmas to default values
        self.synchronicity = np.nan
        self.mass = np.nan
        self.albedo = np.nan
        self.discretization_factor = up.radians(3)
        self.t_eff = np.nan
        self.polar_radius = np.nan
        self._spots = dict()
        self.equatorial_radius = np.nan

    @abstractmethod
    def transform_input(self, *args, **kwargs):
        pass

    @property
    def spots(self):
        """
        :return: Dict[int, Spot]
        """
        return self._spots

    @spots.setter
    def spots(self, spots):
        # todo: update example
        """
        example of defined spots

        ::

            [
                 {"longitude": 90,
                  "latitude": 58,
                  "angular_radius": 15,
                  "temperature_factor": 0.9},
                 {"longitude": 85,
                  "latitude": 80,
                  "angular_radius": 30,
                  "temperature_factor": 1.05},
                 {"longitude": 45,
                  "latitude": 90,
                  "angular_radius": 30,
                  "temperature_factor": 0.95},
             ]

        :param spots: Iterable[Dict]; definition of spots for given object
        :return:
        """
        self._spots = {idx: Spot(**spot_meta) for idx, spot_meta in enumerate(spots)} if not is_empty(spots) else dict()
        for spot_idx, spot_instance in self.spots.items():
            self.setup_spot_instance_discretization_factor(spot_instance, spot_idx)

    def has_spots(self):
        """
        Find whether object has defined spots.

        :return: bool
        """
        return len(self._spots) > 0

    def remove_spot(self, spot_index: int):
        """
        Remove n-th spot index of object.

        :param spot_index: int
        :return:
        """
        del (self._spots[spot_index])

    def setup_spot_instance_discretization_factor(self, spot_instance, spot_index):
        """
        Setup discretization factor for given spot instance based on defined rules::

            - used Star discretization factor if not specified in spot
            - if spot_instance.discretization_factor > 0.5 * spot_instance.angular_diameter then factor is set to
              0.5 * spot_instance.angular_diameter
        :param spot_instance: Spot
        :param spot_index: int; spot index (has no affect on process, used for logging)
        :return:
        """
        # component_instance = getattr(self, component)
        if is_empty(spot_instance.discretization_factor):
            self._logger.debug(f'angular density of the spot {spot_index} on {self.name} component was not supplied '
                               f'and discretization factor of star {self.discretization_factor} was used.')
            spot_instance.discretization_factor = (0.9 * self.discretization_factor * units.ARC_UNIT).value
        if spot_instance.discretization_factor > spot_instance.angular_radius:
            self._logger.debug(f'angular density {self.discretization_factor} of the spot {spot_index} on {self.name} '
                               f'component was larger than its angular radius. Therefore value of angular density was '
                               f'set to be equal to 0.5 * angular diameter')
            spot_instance.discretization_factor = spot_instance.angular_radius * units.ARC_UNIT

        return spot_instance

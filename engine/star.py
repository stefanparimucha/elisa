from engine.body import Body
from astropy import units as u
import numpy as np


class Star(Body):

    KWARGS = ['mass', 't_eff', 'vertices',
              'faces', 'normals', 'temperatures',
              'synchronicity', 'albedo', 'polar_radius',
              'surface_potential', 'backward_radius', 'gravity_darkening']

    def __init__(self, name=None, **kwargs):
        self.is_property(kwargs)
        super(Star, self).__init__(name=name, **kwargs)

        # default values of properties
        self._surface_potential = None  # float64
        self._backward_radius = None  # float64
        self._gravity_darkening = None  # float

        # values of properties
        for kwarg in Star.KWARGS:
            if kwarg in kwargs:
                setattr(self, kwarg, kwargs[kwarg])

    @property
    def surface_potential(self):
        """
        returns surface potential of Star
        usage: xy.Star

        :return: float64
        """
        return self._surface_potential

    @surface_potential.setter
    def surface_potential(self,potential):
        """
        setter for surface potential
        usage: xy.surface_potential = new_potential

        :param potential: float64
        """
        self._surface_potential = np.float64(potential)

    @property
    def backward_radius(self):
        """
        returns value of backward radius of an object in default unit
        usage: xy.backward_radius

        :return: float64
        """
        return self._backward_radius

    @backward_radius.setter
    def backward_radius(self, backward_radius):
        """
        backward radius setter
        accepts values in default distance units
        usage: xy.backward_radius = new_backward_radius

        :param backward_radius: float64
        """
        self._backward_radius = np.float64(backward_radius)

    @property
    def gravity_darkening(self):
        """
        returns gravity darkening
        usage: xy.gravity_darkening

        :return: float64
        """
        return self._backward_radius

    @gravity_darkening.setter
    def gravity_darkening(self, gravity_darkening):
        """
        setter for gravity darkening
        accepts values of gravity darkening in range (0, 1)

        :param gravity_darkening: float64
        """
        if 0 <= gravity_darkening <= 1:
            self._gravity_darkenings = np.float64(gravity_darkening)
        else:
            raise ValueError('Parameter gravity darkening = {} is out of range (0, 1)'.format(gravity_darkening))

    @classmethod
    def is_property(cls, kwargs):
        is_not = ['`{}`'.format(k) for k in kwargs if k not in cls.KWARGS]
        if is_not:
            raise AttributeError('Arguments {} are not valid {} properties.'.format(', '.join(is_not), cls.__name__))
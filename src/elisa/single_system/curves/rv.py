from ... import umpy as up

from ... base.curves import rv_point
from . import c_router


def com_radial_velocity(single, **kwargs):
    """
    Calculates radial velocity curves of the `single` system using radial velocity of centres of masses.

    :param single: elisa.single_system.
    :return:
    """
    phases = kwargs.pop("phases")
    return {'star': single.gamma * up.ones(phases.shape[0])}


def compute_rv_curve_without_pulsations(single, **kwargs):
    """
    Function for calculation radial velocity curves with radiometric methods for single system without pulsations.

    :param single:
    :param kwargs:
    :return:
    """
    initial_system = c_router.prep_initial_system(single)
    rv_labels = ['star', ]
    return c_router.produce_curves_wo_pulsations(single, initial_system, kwargs.pop("phases"),
                                                 rv_point.compute_rv_at_pos, rv_labels, **kwargs)


def compute_rv_curve_with_pulsations(single, **kwargs):
    pass


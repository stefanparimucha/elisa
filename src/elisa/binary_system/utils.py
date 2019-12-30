import numpy as np

from pypex.poly2d.polygon import Polygon
from jsonschema import (
    validate,
    ValidationError
)

from elisa import units, const
from elisa.base.error import YouHaveNoIdeaError
from ..conf.config import SCHEMA_REGISTRY
from ..binary_system import model
from ..utils import is_empty
from .. import (
    umpy as up,
    utils
)


def potential_from_radius(component, radius, phi, theta, component_distance, mass_ratio, synchronicity):
    """
    Calculate potential given spherical coordinates radius, phi, theta.

    :param component: 'primary` or `secondary`;
    :param radius: float;
    :param phi: float;
    :param theta: float;
    :param component_distance: float;
    :param mass_ratio: float;
    :param synchronicity: float;
    :return: float;
    """
    precalc_fn = model.pre_calculate_for_potential_value_primary if component == 'primary' else \
        model.pre_calculate_for_potential_value_secondary
    potential_fn = model.potential_value_primary if component == 'primary' else \
        model.potential_value_secondary

    precalc_args = (synchronicity, mass_ratio, component_distance, phi, theta)
    args = (mass_ratio, ) + precalc_fn(*precalc_args)
    return potential_fn(radius, *args)


def calculate_phase(time, period, t0, offset=0.5):
    """
    Calculates photometric phase from observations.

    :param time: array;
    :param period: array;
    :param t0: float;
    :param offset: float;
    :return: array;
    """
    return up.mod((time - t0 + offset * period) / period, 1.0) - offset


def faces_to_pypex_poly(t_hulls):
    """
    Convert all faces defined as numpy.array to pypex Polygon class instance.

    :param t_hulls: List[numpy.array];
    :return: List;
    """
    return [Polygon(t_hull, _validity=False) for t_hull in t_hulls]


def pypex_poly_hull_intersection(pypex_faces_gen, pypex_hull: Polygon):
    """
    Resolve intersection of polygons defined in `pypex_faces_gen` with polyogn `pypex_hull`.

    :param pypex_faces_gen: List[pypex.poly2d.polygon.Plygon];
    :param pypex_hull: pypex.poly2d.polygon.Plygon;
    :return: List[pypex.poly2d.polygon.Plygon];
    """
    return [pypex_hull.intersection(poly) for poly in pypex_faces_gen]


def pypex_poly_surface_area(pypex_polys_gen):
    """
    Compute surface areas of pypex.poly2d.polygon.Plygon's.

    :param pypex_polys_gen: List[pypex.poly2d.polygon.Plygon];
    :return: List[float];
    """
    return [poly.surface_area() if poly is not None else 0.0 for poly in pypex_polys_gen]


def hull_to_pypex_poly(hull):
    """
    Convert convex polygon defined by points in List or numpy.array to pypex.poly2d.polygon.Polygon.

    :param hull: Union[List, numpy.array];
    :return: pypex.poly2d.polygon.Plygon;
    """
    return Polygon(hull, _validity=False)


def component_to_list(component):
    """
    Converts component name string into list.

    :param component: str;  If None, `['primary', 'secondary']` will be returned otherwise
                            `primary` and `secondary` will be converted into lists [`primary`] and [`secondary`].
    :return: List[str]
    """
    if component in ["all", "both"]:
        component = ['primary', 'secondary']
    elif component in ['primary', 'secondary']:
        component = [component]
    elif is_empty(component):
        return []
    else:
        raise ValueError('Invalid name of the component. Use `primary`, `secondary`, `all` or `both`')
    return component


def renormalize_async_result(result):
    """
    Renormalize multiprocessing output to native form.
    Multiprocessing will return several dicts with same passband (due to supplied batches), but continuous
    computaion require dict in form like::

        [{'passband': [all fluxes]}]

    instead::

        [[{'passband': [fluxes in batch]}], [{'passband': [fluxes in batch]}], ...]

    :param result: List;
    :return: Dict[str; numpy.array]
    """
    # todo: come with something more sophisticated
    placeholder = {key: np.array([]) for key in result[-1]}
    for record in result:
        for passband in placeholder:
            placeholder[passband] = record[passband] if is_empty(placeholder[passband]) else np.hstack(
                (placeholder[passband], record[passband]))
    return placeholder


def move_sys_onpos(system, orbital_position, primary_potential=None, secondary_potential=None, on_copy=True):
    """
    Prepares a postion container for given orbital position.
    Supplied `system` is not affected if `on_copy` is set to True.

    Following methods are applied::

        system.set_on_position_params()
        system.flatt_it()
        system.apply_rotation()
        system.apply_darkside_filter()

    :param system: elisa.binary_system.container.OrbitalPositionContainer;
    :param orbital_position: collections.namedtuple; elisa.const.Position;
    :param primary_potential: float;
    :param secondary_potential: float;
    :param on_copy: bool;
    :return: container; elisa.binary_system.container.OrbitalPositionContainer;
    """
    if on_copy:
        system = system.copy()
    system.set_on_position_params(orbital_position, primary_potential, secondary_potential)
    system.flatt_it()
    system.apply_rotation()
    system.apply_darkside_filter()
    return system


def calculate_rotational_phase(system_container, component):
    """
    Returns rotational phase with in co-rotating frame of reference.

    :param system_container: SystemContainer;
    :param component: str; `primary` or `secondary`
    :return: float;
    """
    star = getattr(system_container, component)
    return (star.synchronicity - 1.0) * system_container.position.phase


def validate_binary_json(data):
    """
    Validate input json to create binary instance from.

    :param data: Dict; json like object
    :return: bool; return True if valid schema, othervise raise error
    :raise: ValidationError;
    """
    schema_std = SCHEMA_REGISTRY.get_schema("binary_system_std")
    schema_community = SCHEMA_REGISTRY.get_schema("binary_system_community")
    std_valid, community_valid = False, False

    try:
        validate(instance=data, schema=schema_std)
        std_valid = True
    except ValidationError:
        pass

    try:
        validate(instance=data, schema=schema_community)
        community_valid = True
    except ValidationError:
        pass

    if (not community_valid) & (not std_valid):
        raise ValidationError("BinarySystem cannot be created from supplied json schema.")

    if community_valid & std_valid:
        raise YouHaveNoIdeaError("You have no idea what is going on [M1, M2, q, a].")

    return True


def resolve_json_kind(data, _sin=False):
    """
    Resolve if json is `std` or `community`.

    std - standard physical parameters (M1, M2)
    community - astro community parameters (q, a)

    :param data: Dict; json like
    :param _sin: bool; if False, looking for `semi_major_axis` in given JSON, otherwise looking for `asini`
    :return: str; `std` or `community`
    """
    lookup = "asini" if _sin else "semi_major_axis"
    m1, m2 = data["primary"].get("mass"), data["secondary"].get("mass")
    q, a = data["system"].get("mass_ratio"), data["system"].get(lookup)

    if m1 and m2:
        return "std"
    if q and a:
        return "community"
    raise LookupError("It seems your JSON is invalid.")


def transform_json_community_to_std(data):
    """
    Transform `community` input json to `std` json.
    Compute `M1` and `M2` from `q` and `a`.

    All units of values are expected to be default.

    :param data: Dict;
    :return: Dict;
    """
    q = data["system"].pop("mass_ratio")
    a = np.float64((data["system"].pop("semi_major_axis") * units.solRad).to(units.m))
    period = np.float64((data["system"]["period"] * units.PERIOD_UNIT).to(units.s))
    m1 = ((4.0 * const.PI ** 2 * a ** 3) / (const.G * (1.0 + q) * period ** 2))
    m1 = np.float64((m1 * units.kg).to(units.solMass))
    m2 = q * m1

    data["primary"].update({"mass": m1})
    data["secondary"].update({"mass": m2})

    return data

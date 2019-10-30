from elisa import logger
from elisa.base.container import StarContainer, PositionContainer
from elisa.binary_system.surface import mesh, faces, gravity, temperature
from elisa.conf import config

config.set_up_logging()
__logger__ = logger.getLogger("binary-system-container-module")


class OrbitalPositionContainer(PositionContainer):
    def __init__(self, primary: StarContainer, secondary, position, **properties):
        self.primary = primary
        self.secondary = secondary
        self.position = position

        for key, val in properties.items():
            setattr(self, key, val)

    def has_spots(self):
        return self.primary.has_spots() or self.secondary.has_spots()

    def has_pulsations(self):
        return self.primary.has_pulsations() or self.secondary.has_pulsations()

    def build(self, components_distance, component="all", do_pulsations=False, phase=None, **kwargs):
        """
        Main method to build binary star system from parameters given on init of BinaryStar.

        called following methods::

            - build_mesh
            - build_faces
            - build_surface_areas
            - build_faces_orientation
            - build_surface_gravity
            - build_temperature_distribution

        :param phase: float; phase to build system on
        :param do_pulsations: bool; switch to incorporate pulsations
        :param component: str; `primary` or `secondary`
        :param components_distance: float; distance of components is SMA units
        :return:
        """
        self.build_mesh(components_distance, component)
        self.build_from_points(components_distance, component, do_pulsations=do_pulsations, phase=phase)

    def build_mesh(self, components_distance, component="all"):
        return mesh.build_mesh(self, components_distance, component)

    def build_faces(self, components_distance, component="all"):
        return faces.build_faces(self, components_distance, component)

    def build_surface_areas(self, component="all"):
        return faces.compute_all_surface_areas(self, component)

    def build_faces_orientation(self, components_distance, component="all"):
        return faces.build_faces_orientation(self, components_distance, component)

    def build_surface_gravity(self, components_distance, component="all"):
        return gravity.build_surface_gravity(self, components_distance, component)

    def build_temperature_distribution(self, components_distance, component="all", do_pulsations=False, phase=None):
        return temperature.build_temperature_distribution(self, components_distance, component, do_pulsations, phase)

    def build_from_points(self, components_distance, component="all", do_pulsations=False, phase=None):
        """
        Build binary system from preset surface points

        :param component: str; `primary` or `secondary`
        :param components_distance: float; distance of components is SMA units
        :param do_pulsations: bool; switch to incorporate pulsations
        :param phase: float; phase to build system on
        :return:
        """
        self.build_faces(components_distance, component)
        self.build_surface_areas(component)
        self.build_faces_orientation(components_distance, component)
        self.build_surface_gravity(components_distance, component)
        self.build_temperature_distribution(components_distance, component, do_pulsations=do_pulsations, phase=phase)

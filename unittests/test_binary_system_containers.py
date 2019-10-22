import numpy as np
from numpy.testing import assert_array_equal

from elisa.base.container import StarContainer
from elisa.binary_system.container import OrbitalPositionContainer
from elisa.const import BINARY_POSITION_PLACEHOLDER
from elisa import umpy as up
from elisa.utils import is_empty
from unittests import utils as testutils
from unittests.utils import ElisaTestCase


class BuildMeshSpotsFreeTestCase(ElisaTestCase):
    @staticmethod
    def generator_test_mesh(key, d, length):
        s = testutils.prepare_binary_system(testutils.BINARY_SYSTEM_PARAMS[key])
        s.primary.discretization_factor = d
        s.secondary.discretization_factor = d

        orbital_position_container = OrbitalPositionContainer(
            primary=StarContainer.from_properties_container(s.primary.to_properties_container()),
            secondary=StarContainer.from_properties_container(s.secondary.to_properties_container()),
            position=BINARY_POSITION_PLACEHOLDER(*(0, 1.0, 0.0, 0.0, 0.0)),
            **s.properties_serializer()
        )
        orbital_position_container.build_mesh(components_distance=1.0)

        obtained_primary = np.round(orbital_position_container.primary.points, 4)
        obtained_secondary = np.round(orbital_position_container.secondary.points, 4)
        assert_array_equal([len(obtained_primary), len(obtained_secondary)], length)

    def test_build_mesh_detached(self):
        self.generator_test_mesh(key="detached", d=up.radians(10), length=[426, 426])

    def test_build_mesh_overcontact(self):
        self.generator_test_mesh(key="over-contact", d=up.radians(10), length=[413, 401])

    def test_build_mesh_semi_detached(self):
        self.generator_test_mesh(key="semi-detached", d=up.radians(10), length=[426, 426])


class BuildSpottyMeshTestCase(ElisaTestCase):
    def generator_test_mesh(self, key, d):
        s = testutils.prepare_binary_system(testutils.BINARY_SYSTEM_PARAMS[key],
                                            spots_primary=testutils.SPOTS_META["primary"],
                                            spots_secondary=testutils.SPOTS_META["secondary"])
        s.primary.discretization_factor = d
        s.secondary.discretization_factor = d
        orbital_position_container = OrbitalPositionContainer(
            primary=StarContainer.from_properties_container(s.primary.to_properties_container()),
            secondary=StarContainer.from_properties_container(s.secondary.to_properties_container()),
            position=BINARY_POSITION_PLACEHOLDER(*(0, 1.0, 0.0, 0.0, 0.0)),
            **s.properties_serializer()
        )
        orbital_position_container.build_mesh(components_distance=1.0)

        self.assertTrue(not is_empty(orbital_position_container.primary.spots[0].points))
        self.assertTrue(not is_empty(orbital_position_container.secondary.spots[0].points))

    def test_build_mesh_detached(self):
        self.generator_test_mesh(key="detached", d=up.radians(10))

    def test_build_mesh_overcontact(self):
        self.generator_test_mesh(key="over-contact", d=up.radians(10))

    def test_build_mesh_semi_detached(self):
        self.generator_test_mesh(key="semi-detached", d=up.radians(10))

    def test_build_mesh_detached_with_overlapped_spots(self):
        s = testutils.prepare_binary_system(testutils.BINARY_SYSTEM_PARAMS['detached'],
                                            spots_primary=testutils.SPOTS_OVERLAPPED)
        s.primary.discretization_factor = up.radians(5)
        s.secondary.discretization_factor = up.radians(5)
        orbital_position_container = OrbitalPositionContainer(
            primary=StarContainer.from_properties_container(s.primary.to_properties_container()),
            secondary=StarContainer.from_properties_container(s.secondary.to_properties_container()),
            position=BINARY_POSITION_PLACEHOLDER(*(0, 1.0, 0.0, 0.0, 0.0)),
            **s.properties_serializer()
        )
        with self.assertRaises(Exception) as context:
            orbital_position_container.build_mesh(components_distance=1.0)
        self.assertTrue("Please, specify spots wisely" in str(context.exception))

    @staticmethod
    def test_build_mesh_detached_with_overlapped_like_umbra():
        s = testutils.prepare_binary_system(testutils.BINARY_SYSTEM_PARAMS['detached'],
                                            spots_primary=list(reversed(testutils.SPOTS_OVERLAPPED)))
        s.primary.discretization_factor = up.radians(5)
        s.secondary.discretization_factor = up.radians(5)
        orbital_position_container = OrbitalPositionContainer(
            primary=StarContainer.from_properties_container(s.primary.to_properties_container()),
            secondary=StarContainer.from_properties_container(s.secondary.to_properties_container()),
            position=BINARY_POSITION_PLACEHOLDER(*(0, 1.0, 0.0, 0.0, 0.0)),
            **s.properties_serializer()
        )
        orbital_position_container.build_mesh(components_distance=1.0)

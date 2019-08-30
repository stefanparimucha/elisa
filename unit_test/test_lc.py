import unittest

import numpy as np

from elisa.binary_system.geo import OrbitalSupplements
from elisa.binary_system.lc import _resolve_geometry_update
from elisa.binary_system.lc import find_apsidally_corresponding_positions, _compute_rel_d_radii
from elisa.conf import config


class MockSelf(object):
    @staticmethod
    def has_spots():
        return False

    def calculate_all_forward_radii(self, *args, **kwargs):
        return {
            "primary": np.array([0.4, 0.45, 0.48, 0.34, 0.6]),
            "secondary": np.array([0.2, 0.22, 0.19, 0.4, 0.33])
        }


class SupportMethodsTestCase(unittest.TestCase):
    def _test_find_apsidally_corresponding_positions(self, arr1, arr2, expected, tol=1e-10):
        obtained = find_apsidally_corresponding_positions(arr1[:, 0], arr1, arr2[:, 0], arr2, tol, [np.nan] * 2)
        # print(obtained)
        self.assertTrue(expected == obtained)

    def test_find_apsidally_corresponding_positions_full_match(self):
        arr1 = np.array([[1, 10], [2, 20], [3, 30], [4, 40], [5.0, 50]])
        arr2 = np.array([[1, 10], [3, 30], [2, 20], [4, 40], [5.0, 50]])
        expected = OrbitalSupplements([[1, 10], [3, 30], [2, 20], [4, 40], [5.0, 50]],
                                      [[1, 10], [3, 30], [2, 20], [4, 40], [5.0, 50]])

        self._test_find_apsidally_corresponding_positions(arr1, arr2, expected)

    def test_find_apsidally_corresponding_positions_mixed_first_longer(self):
        arr1 = np.array([[1, 10], [2, 20], [5, 50], [6, 60], [7, 70]])
        arr2 = np.array([[1, 10], [2, 20], [5.5, 50.50], [7, 70]])
        nan = [np.nan, np.nan]
        expected = OrbitalSupplements([[1.0, 10.], [2.0, 20.0], [5.5, 50.5], [7.0, 70], [5, 50], [6, 60]],
                                      [[1, 10], [2, 20], nan, [7.0, 70], nan, nan])
        self._test_find_apsidally_corresponding_positions(arr1, arr2, expected)

    def test_find_apsidally_corresponding_positions_mixed_second_longer(self):
        arr1 = np.array([[1, 10], [2, 20], [5.5, 50.50], [7, 70]])
        arr2 = np.array([[1, 10], [2, 20], [5, 50], [6, 60], [7, 70]])
        nan = [np.nan, np.nan]
        expected = OrbitalSupplements([[1., 10.], [2., 20.], [5., 50.], [6., 60.], [7., 70.], [5.5, 50.5]],
                                      [[1., 10.], [2., 20.], nan, nan, [7., 70.], nan])
        self._test_find_apsidally_corresponding_positions(arr1, arr2, expected)

    # def test_find_apsidally_corresponding_positions_mixed_under_tolerance(self):
    #     arr1 = np.array([[1, 10], [2, 20], [3, 30], [4, 40]])
    #     arr2 = np.array([[1, 10], [1.01, 10.10], [2, 20], [2.02, 20.02], [4, 40]])
    #     expected = OrbitalSupplements([1.0, 2.0, 2.0, 4.0, 3.0],
    #                                   [1.0, 2.0, 2.02, 4.0, None])
    #     self._test_find_apsidally_corresponding_positions(arr1, arr2, expected, tol=0.1)

    def test_find_apsidally_corresponding_positions_total_mixed(self):
        arr1 = np.array([[1, 10], [2, 20]])
        arr2 = np.array([[3, 30], [4, 40]])
        nan = [np.nan, np.nan]
        expected = OrbitalSupplements([[3, 30], [4, 40], [1, 10], [2, 20]], [nan, nan, nan, nan])
        self._test_find_apsidally_corresponding_positions(arr1, arr2, expected)

    def test_find_apsidally_corresponding_positions_body_not_empty(self):
        arr1 = np.array([[1, 10], [2, 20]])
        arr2 = np.array([[3, 30], [4, 40]])
        obtained = find_apsidally_corresponding_positions(arr1[:, 0], arr1, arr2[:, 0], arr2, as_empty=[np.nan] * 2)
        self.assertTrue(np.all(~np.isnan(obtained.body)))

    def test__resolve_geometry_update(self):
        val_backup = config.MAX_RELATIVE_D_R_POINT
        config.MAX_RELATIVE_D_R_POINT = 0.1
        rel_d_radii = np.array([
            [0.05, 0.04, 0.02, 0.01, 0.1, 1.1, 98, 0.00001],
            [0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.12]
        ])

        expected = np.array([True, False, False, True, False, True, True, True, True], dtype=bool)
        obtained = _resolve_geometry_update(MockSelf, rel_d_radii.shape[1] + 1, rel_d_radii)
        config.MAX_RELATIVE_D_R_POINT = val_backup

        self.assertTrue(np.all(expected == obtained))

    def test__compute_rel_d_radii(self):
        mock_supplements = OrbitalSupplements([[1., 10.]], [[1., 10.]])
        expected = np.array([[0.1111, 0.0625, 0.4118, 0.4333], [0.0909, 0.1579, 0.525, 0.2121]])
        obtained = np.round(_compute_rel_d_radii(MockSelf, mock_supplements), 4)
        self.assertTrue(np.all(expected == obtained))

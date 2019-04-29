import numpy as np

from pypex.base import shape
from pypex.poly2d.intersection import sat
from pypex.poly2d.point import Point
from pypex.poly2d.line import Line
from pypex.base.conf import ROUND_PRECISION as PRECISION


class Polygon(shape.Shape2D):
    """
    Convex Polygon
    """
    def __init__(self, hull):
        super(Polygon, self).__init__(hull=hull)
        self.sort_clockwise(inplace=True)

    def edges(self):
        """
        Provide method to iterate over edges in polygon.
        :return: numpy.array
        """
        for i in range(-1, len(self.hull)-1, 1):
            yield np.array([self.hull[i], self.hull[i+1]])

    def intersects(self, poly, in_touch=False, tol=PRECISION):
        """
        Whether two polygons intersects.

        :param tol:
        :param poly: pypex.poly2d.polygon.Polygon
        :param in_touch: bool
        :return: bool
        """
        return sat.intersects(self.hull, poly.hull, in_touch, tol)

    def intersection(self, poly, tol=PRECISION):
        """
        Find intersection polygon created by clipping of one polygon by another.

        :param poly: pypex.poly2d.polygon.Polygon
        :param tol: int; round precision of decimal points to consider numbers as same
        :return: pypex.poly2d.polygon.Polygon
        """
        # add  the corners of `self` which are inside poly
        poly1 = np.array([Point(x=corner[0], y=corner[1]) for corner in self.hull])
        poly2 = np.array([Point(x=corner[0], y=corner[1]) for corner in poly.hull])

        in_poly1 = poly2[[corner.is_inside_polygon(self) for corner in poly2]]
        in_poly2 = poly1[[corner.is_inside_polygon(poly) for corner in poly1]]
        intersection_poly = np.concatenate((in_poly1, in_poly2), axis=0).tolist()

        # find point of intersected edges
        for edge1 in self.edges():
            line1 = Line(edge1)
            for edge2 in poly.edges():
                line2 = Line(edge2)
                intersection = line1.intersects(line2, _full=True, in_touch=True, tol=tol)
                if intersection[1] and (intersection[-1] in ["INTERSECT"]):
                    intersection_poly.append(intersection[2])
        intersection_poly = Point.set(intersection_poly, tol=tol)

        return Polygon(intersection_poly) if len(intersection_poly) > 2 else None

    def surface_area(self):
        lines = np.hstack([self.hull, np.roll(self.hull, -1, axis=0)])
        area = 0.5 * abs(sum(x1 * y2 - x2 * y1 for x1, y1, x2, y2 in lines))
        return area
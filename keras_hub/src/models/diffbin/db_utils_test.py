import keras
import numpy as np

from keras_hub.src.models.diffbin.db_utils import Point
from keras_hub.src.models.diffbin.db_utils import Polygon
from keras_hub.src.models.diffbin.db_utils import binary_search_smallest_width
from keras_hub.src.models.diffbin.db_utils import fill_poly_keras
from keras_hub.src.models.diffbin.db_utils import get_coords_poly_distance
from keras_hub.src.models.diffbin.db_utils import get_coords_poly_projection
from keras_hub.src.models.diffbin.db_utils import get_line_height
from keras_hub.src.models.diffbin.db_utils import get_mask
from keras_hub.src.models.diffbin.db_utils import get_normalized_weight
from keras_hub.src.models.diffbin.db_utils import get_region_coordinate
from keras_hub.src.models.diffbin.db_utils import project_point_to_line
from keras_hub.src.models.diffbin.db_utils import project_point_to_segment
from keras_hub.src.models.diffbin.db_utils import shrink_polygan
from keras_hub.src.tests.test_case import TestCase


class TestDBUtils(TestCase):
    def test_point_operations(self):
        p1 = Point(1, 2)
        p2 = Point(3, 4)

        p_add = p1 + p2
        assert p_add.x == 4 and p_add.y == 6

        p_sub = p2 - p1
        assert p_sub.x == 2 and p_sub.y == 2

        p_neg = -p1
        assert p_neg.x == -1 and p_neg.y == -2

        cross_product = p1.cross(p2)
        assert cross_product == (1 * 4 - 2 * 3)

        p_tuple = p1.to_tuple()
        assert p_tuple == (1, 2)

    def test_shrink_polygan(self):
        polygon = [Point(0, 0), Point(2, 0), Point(2, 2), Point(0, 2)]
        offset = 0.5
        shrunk_polygon = shrink_polygan(polygon, offset)
        assert len(shrunk_polygon) == 4
        assert all(isinstance(p, Point) for p in shrunk_polygon)

        polygon_np = np.array([[0, 0], [2, 0], [2, 2], [0, 2]])
        shrunk_polygon_np = shrink_polygan(polygon_np, offset)
        assert len(shrunk_polygon_np) == 4
        assert all(isinstance(p, Point) for p in shrunk_polygon_np)

        empty_polygon = []
        assert shrink_polygan(empty_polygon, offset) == []

        small_polygon = [Point(0, 0), Point(1, 1)]
        assert shrink_polygan(small_polygon, offset) == small_polygon

    def test_polygon_area(self):
        coords = [[0, 0], [2, 0], [2, 2], [0, 2]]
        area = Polygon(coords)
        assert area == 4.0

        coords_np = np.array([[0, 0], [2, 0], [2, 2], [0, 2]])
        area_np = Polygon(coords_np)
        assert area_np == 4.0

        triangle = [[0, 0], [1, 0], [0, 1]]
        area_triangle = Polygon(triangle)
        assert area_triangle == 0.5

    def test_binary_search_smallest_width(self):
        # Example polygon, the exact shrunk amount depends on the algorithm
        # We can only test if it returns a non-negative integer.
        polygon = [[0, 0], [2, 0], [2, 2], [0, 2]]
        width = binary_search_smallest_width(polygon)
        assert isinstance(width, int)
        assert width >= 0

        small_polygon = [[0, 0], [1, 1]]
        assert binary_search_smallest_width(small_polygon) == 0

    def test_project_point_to_line(self):
        x = [1, 1]
        u = [0, 0]
        v = [2, 0]
        projection = project_point_to_line(x, u, v)
        assert np.allclose(projection, [1, 0])

        x_np = np.array([1, 1])
        u_np = np.array([0, 0])
        v_np = np.array([2, 0])
        projection_np = project_point_to_line(x_np, u_np, v_np)
        assert np.allclose(projection_np, [1, 0])

    def test_project_point_to_segment(self):
        x = [1, 1]
        u = [0, 0]
        v = [2, 0]
        projection = project_point_to_segment(x, u, v)
        assert np.allclose(projection, [1, 0])

        x_off = [3, 1]
        projection_off = project_point_to_segment(x_off, u, v)
        assert np.allclose(projection_off, [2, 0])

    def test_get_line_height(self):
        polygon = [[0, 0], [2, 0], [2, 2], [0, 2]]
        height = get_line_height(polygon)
        assert isinstance(height, int)
        assert height >= 0

    def test_fill_poly_keras(self):
        vertices = [[0, 0], [2, 0], [2, 2], [0, 2]]
        image_shape = (3, 3)
        mask = fill_poly_keras(vertices, image_shape)
        assert mask.shape == image_shape
        assert keras.ops.any(mask >= 0) and keras.ops.any(mask <= 1)

    def test_get_mask(self):
        w, h = 3, 3
        polys = [[[0, 0], [2, 0], [2, 2], [0, 2]]]
        ignores = [False]
        mask = get_mask(w, h, polys, ignores)
        assert mask.shape == (h, w)
        assert keras.ops.any(mask >= 0) and keras.ops.any(mask <= 1)

    def test_get_coords_poly_projection(self):
        coords = [[1, 1], [3, 3]]
        poly = [[0, 0], [2, 0], [2, 2], [0, 2]]
        projection = get_coords_poly_projection(coords, poly)
        assert projection.shape == (len(coords), 2)

    def test_get_coords_poly_distance(self):
        coords = [[1, 1], [3, 3]]
        poly = [[0, 0], [2, 0], [2, 2], [0, 2]]
        distances = get_coords_poly_distance(coords, poly)
        assert distances.shape == (len(coords),)
        assert keras.ops.all(distances >= 0)

    def test_get_normalized_weight(self):
        heatmap = np.array([[0.1, 0.6], [0.4, 0.8]])
        mask = np.array([[1, 1], [1, 1]])
        weight = get_normalized_weight(heatmap, mask)
        assert weight.shape == heatmap.shape
        assert np.all(weight >= 0)

        mask_partial = np.array([[1, 0], [1, 1]])
        weight_partial = get_normalized_weight(heatmap, mask_partial)
        assert np.all(weight_partial >= 0)

    def test_get_region_coordinate(self):
        w, h = 10, 10
        poly = [[[1, 1], [8, 1], [8, 3], [1, 3]]]
        heights = [1]
        shrink = 0.2
        regions = get_region_coordinate(w, h, poly, heights, shrink)
        assert isinstance(regions, list)
        if regions:
            assert isinstance(regions[0], np.ndarray)

        poly_multiple = [
            [[1, 1], [8, 1], [8, 3], [1, 3]],
            [[2, 5], [7, 5], [7, 7], [2, 7]],
        ]
        heights_multiple = [1, 0.8]
        regions_multiple = get_region_coordinate(
            w, h, poly_multiple, heights_multiple, shrink
        )
        assert isinstance(regions_multiple, list)
        assert len(regions_multiple) <= len(poly_multiple)
        for region in regions_multiple:
            assert isinstance(region, np.ndarray)

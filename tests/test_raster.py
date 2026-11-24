import math

import pytest

from pixelpath.raster import rasterize


def square(x, y, size, clockwise=True):
    points = [(x, y), (x + size, y), (x + size, y + size), (x, y + size)]
    return points if clockwise else points[::-1]


def regular_polygon(cx, cy, radius, count):
    return [(cx + radius * math.cos(2 * math.pi * i / count), cy + radius * math.sin(2 * math.pi * i / count)) for i in range(count)]


def test_filled_square_total_coverage_equals_area():
    mask = rasterize([square(5.3, 5.7, 10)], 32, 32)
    assert mask.total() == pytest.approx(100.0, rel=0.005)


def test_large_square_coverage_equals_area():
    mask = rasterize([square(10.25, 20.6, 200.5)], 256, 256)
    assert mask.total() == pytest.approx(200.5 * 200.5, rel=0.005)


def test_circle_coverage_equals_area():
    polygon = regular_polygon(32.3, 31.8, 20, 512)
    exact_polygon_area = 0.5 * 512 * 20 * 20 * math.sin(2 * math.pi / 512)
    mask = rasterize([polygon], 64, 64)
    assert mask.total() == pytest.approx(exact_polygon_area, rel=0.005)


def test_interior_pixels_are_fully_covered():
    mask = rasterize([square(2, 2, 6)], 10, 10)
    assert mask.get(4, 4) == pytest.approx(1.0)
    assert mask.get(0, 0) == 0.0
    assert mask.get(9, 9) == 0.0


def test_evenodd_hole_with_same_orientation():
    polygons = [square(0, 0, 20), square(5, 5, 10)]
    assert rasterize(polygons, 20, 20, "nonzero").get(10, 10) == pytest.approx(1.0)
    assert rasterize(polygons, 20, 20, "evenodd").get(10, 10) == pytest.approx(0.0)
    assert rasterize(polygons, 20, 20, "evenodd").get(2, 2) == pytest.approx(1.0)


def test_nonzero_hole_with_opposite_orientation():
    polygons = [square(0, 0, 20), square(5, 5, 10, clockwise=False)]
    mask = rasterize(polygons, 20, 20, "nonzero")
    assert mask.get(10, 10) == pytest.approx(0.0)
    assert mask.get(2, 2) == pytest.approx(1.0)
    assert mask.total() == pytest.approx(300.0, rel=0.005)


def test_self_intersecting_star():
    points = []
    for index in range(5):
        angle = -math.pi / 2 + index * 4 * math.pi / 5
        points.append((50 + 40 * math.cos(angle), 50 + 40 * math.sin(angle)))
    assert rasterize([points], 100, 100, "nonzero").get(50, 50) == pytest.approx(1.0)
    assert rasterize([points], 100, 100, "evenodd").get(50, 50) == pytest.approx(0.0)
    assert rasterize([points], 100, 100, "evenodd").get(50, 20) == pytest.approx(1.0)


def test_bow_tie_self_intersection():
    bow_tie = [(0, 0), (20, 20), (20, 0), (0, 20)]
    mask = rasterize([bow_tie], 20, 20, "nonzero")
    assert mask.total() == pytest.approx(200.0, rel=0.005)
    assert mask.get(10, 2) == pytest.approx(0.0)
    assert mask.get(17, 10) == pytest.approx(1.0)


def test_half_pixel_edge_gives_half_coverage():
    mask = rasterize([[(2.5, 0), (8, 0), (8, 4), (2.5, 4)]], 10, 4)
    assert mask.get(2, 1) == pytest.approx(0.5)
    assert mask.get(3, 1) == pytest.approx(1.0)


def test_horizontal_edge_coverage_is_antialiased():
    mask = rasterize([[(0, 2.25), (8, 2.25), (8, 6), (0, 6)]], 8, 8)
    assert 0.6 <= mask.get(4, 2) <= 0.9


def test_diagonal_edge_has_partial_coverage():
    mask = rasterize([[(0, 0), (32, 0), (0, 32)]], 32, 32)
    partial = [mask.get(x, y) for y in range(32) for x in range(32) if 0.0 < mask.get(x, y) < 1.0]
    assert len(partial) >= 30
    assert mask.get(15, 16) == pytest.approx(0.5, abs=0.07)


def test_at_least_sixteen_coverage_levels():
    mask = rasterize([[(0, 0), (64, 0), (64, 20)]], 64, 64)
    levels = {round(mask.get(x, y), 4) for y in range(64) for x in range(64)}
    assert len(levels) >= 16


def test_polygon_outside_canvas_is_clipped():
    mask = rasterize([square(-10, -10, 20)], 8, 8)
    assert mask.total() == pytest.approx(64.0, rel=0.005)
    assert rasterize([square(100, 100, 5)], 8, 8).total() == 0.0


def test_empty_and_degenerate_input():
    assert rasterize([], 8, 8).total() == 0.0
    assert rasterize([[(1, 1), (5, 1)]], 8, 8).total() == 0.0
    assert rasterize([[(1, 1)]], 8, 8).total() == 0.0


def test_coverage_never_exceeds_one_for_overlapping_shapes():
    mask = rasterize([square(0, 0, 10), square(0, 0, 10), square(0.5, 0.5, 5)], 10, 10, "nonzero")
    assert max(mask.get(x, y) for y in range(10) for x in range(10)) <= 1.0


def test_invalid_fill_rule():
    with pytest.raises(ValueError):
        rasterize([square(0, 0, 1)], 2, 2, "winding")

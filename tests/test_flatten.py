import math

import pytest

from pixelpath.flatten import (
    arc_endpoint_to_center,
    arc_to_cubics,
    flatten_cubic,
    flatten_path,
    flatten_quadratic,
)
from pixelpath.path import parse_path
from pixelpath.transform import Matrix


def cubic_point(p0, p1, p2, p3, t):
    u = 1 - t
    return (
        u * u * u * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t * t * t * p3[0],
        u * u * u * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t * t * t * p3[1],
    )


def distance_to_polyline(point, polyline):
    best = math.inf
    for (ax, ay), (bx, by) in zip(polyline, polyline[1:]):
        dx, dy = bx - ax, by - ay
        length_squared = dx * dx + dy * dy
        t = 0.0 if length_squared == 0 else max(0.0, min(1.0, ((point[0] - ax) * dx + (point[1] - ay) * dy) / length_squared))
        best = min(best, math.hypot(point[0] - (ax + t * dx), point[1] - (ay + t * dy)))
    return best


def test_semicircle_center_conversion():
    cx, cy, rx, ry, theta1, delta = arc_endpoint_to_center(0, 0, 1, 1, 0, 0, 1, 2, 0)
    assert (cx, cy) == pytest.approx((1.0, 0.0), abs=1e-9)
    assert (rx, ry) == pytest.approx((1.0, 1.0))
    assert math.cos(theta1) == pytest.approx(-1.0)
    assert delta == pytest.approx(math.pi)


def test_sweep_flag_controls_direction():
    *_, delta = arc_endpoint_to_center(0, 0, 1, 1, 0, 0, 0, 2, 0)
    assert delta == pytest.approx(-math.pi)


def test_large_arc_flag_selects_longer_arc():
    *_, small = arc_endpoint_to_center(0, 0, 10, 10, 0, 0, 1, 10, 0)
    *_, large = arc_endpoint_to_center(0, 0, 10, 10, 0, 1, 1, 10, 0)
    assert abs(small) < math.pi < abs(large)
    assert abs(small) + abs(large) == pytest.approx(2 * math.pi)


def test_too_small_radius_is_scaled_up():
    cx, cy, rx, ry, _, delta = arc_endpoint_to_center(0, 0, 1, 1, 0, 0, 1, 10, 0)
    assert (cx, cy) == pytest.approx((5.0, 0.0), abs=1e-9)
    assert (rx, ry) == pytest.approx((5.0, 5.0))
    assert abs(delta) == pytest.approx(math.pi)


def test_rotated_ellipse_endpoints_lie_on_ellipse():
    x1, y1, x2, y2, phi = 3.0, 4.0, 17.0, 9.0, 30.0
    cx, cy, rx, ry, theta1, delta = arc_endpoint_to_center(x1, y1, 10, 6, phi, 1, 0, x2, y2)
    cos_phi, sin_phi = math.cos(math.radians(phi)), math.sin(math.radians(phi))

    def point_at(theta):
        ex, ey = rx * math.cos(theta), ry * math.sin(theta)
        return (cx + cos_phi * ex - sin_phi * ey, cy + sin_phi * ex + cos_phi * ey)

    assert point_at(theta1) == pytest.approx((x1, y1), abs=1e-9)
    assert point_at(theta1 + delta) == pytest.approx((x2, y2), abs=1e-9)


def test_negative_radii_use_absolute_value():
    result = arc_endpoint_to_center(0, 0, -1, -1, 0, 0, 1, 2, 0)
    assert result[2:4] == pytest.approx((1.0, 1.0))


def test_zero_radius_arc_has_no_center():
    assert arc_endpoint_to_center(0, 0, 0, 5, 0, 0, 1, 10, 0) is None


def test_identical_endpoints_produce_no_cubics():
    assert arc_to_cubics(5, 5, 3, 3, 0, 0, 1, 5, 5) == []


def test_zero_radius_arc_becomes_straight_line():
    assert arc_to_cubics(0, 0, 0, 0, 0, 0, 1, 10, 0) == [((0.0, 0.0), (10.0, 0.0), (10.0, 0.0))]
    [subpath] = flatten_path(parse_path("M0 0 A0 0 0 0 1 10 0"))
    assert subpath.points == [(0.0, 0.0), (10.0, 0.0)]


def test_arc_cubics_end_exactly_on_endpoint_and_stay_on_circle():
    cubics = arc_to_cubics(0, 0, 5, 5, 0, 1, 1, 10, 0)
    assert len(cubics) >= 2
    assert cubics[-1][2] == (10.0, 0.0)
    start = (0.0, 0.0)
    for control1, control2, end in cubics:
        for step in range(11):
            x, y = cubic_point(start, control1, control2, end, step / 10)
            assert math.hypot(x - 5, y) == pytest.approx(5.0, abs=0.01)
        start = end


def test_flattened_arc_points_are_on_circle_and_end_at_endpoint():
    [subpath] = flatten_path(parse_path("M0 0 A5 5 0 0 1 10 0"), tolerance=0.01)
    assert subpath.points[0] == (0.0, 0.0)
    assert subpath.points[-1] == pytest.approx((10.0, 0.0))
    for x, y in subpath.points:
        assert math.hypot(x - 5, y) == pytest.approx(5.0, abs=0.02)
    assert all(y <= 1e-9 for _, y in subpath.points)


def test_cubic_flattening_stays_within_tolerance():
    p0, p1, p2, p3 = (0, 0), (0, 100), (100, 100), (100, 0)
    tolerance = 0.25
    points = [p0] + flatten_cubic(p0, p1, p2, p3, tolerance)
    assert points[-1] == p3
    for step in range(201):
        assert distance_to_polyline(cubic_point(p0, p1, p2, p3, step / 200), points) <= tolerance + 1e-9


def test_cubic_flattening_is_adaptive():
    coarse = flatten_cubic((0, 0), (0, 100), (100, 100), (100, 0), 1.0)
    fine = flatten_cubic((0, 0), (0, 100), (100, 100), (100, 0), 0.01)
    straight = flatten_cubic((0, 0), (1, 0), (2, 0), (3, 0), 0.25)
    assert len(fine) > len(coarse) > len(straight)
    assert straight == [(3, 0)]


def test_quadratic_flattening_stays_within_tolerance():
    p0, p1, p2 = (0, 0), (50, 100), (100, 0)
    points = [p0] + flatten_quadratic(p0, p1, p2, 0.1)
    assert points[-1] == p2
    for step in range(101):
        t = step / 100
        u = 1 - t
        point = (u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0], u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1])
        assert distance_to_polyline(point, points) <= 0.1 + 1e-9


def test_flatten_path_splits_subpaths_and_tracks_closure():
    subpaths = flatten_path(parse_path("M0 0 L10 0 L10 10 Z M20 20 L30 20"))
    assert len(subpaths) == 2
    assert subpaths[0].closed is True
    assert subpaths[0].points == [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)]
    assert subpaths[1].closed is False
    assert subpaths[1].points == [(20.0, 20.0), (30.0, 20.0)]


def test_drawing_after_close_starts_new_subpath_at_start_point():
    subpaths = flatten_path(parse_path("M0 0 L10 0 L10 10 Z L0 10"))
    assert len(subpaths) == 2
    assert subpaths[1].points == [(0.0, 0.0), (0.0, 10.0)]


def test_flatten_path_applies_transform():
    [subpath] = flatten_path(parse_path("M1 1 L2 2"), transform=Matrix.scaling(10, 20))
    assert subpath.points == [(10.0, 20.0), (20.0, 40.0)]


def test_lone_moveto_produces_single_point_subpath():
    [subpath] = flatten_path(parse_path("M5 5"))
    assert subpath.points == [(5.0, 5.0)]

import math

import pytest

from pixelpath import Canvas
from pixelpath.png import decode_png
from pixelpath.transform import Matrix


def total_alpha(canvas):
    return sum(canvas.get_pixel(x, y)[3] for y in range(canvas.height) for x in range(canvas.width)) / 255


def test_new_canvas_is_fully_transparent():
    canvas = Canvas(4, 3)
    assert (canvas.width, canvas.height) == (4, 3)
    assert all(canvas.get_pixel(x, y) == (0, 0, 0, 0) for y in range(3) for x in range(4))


def test_background_fills_canvas():
    canvas = Canvas(2, 2, background="#fff")
    assert canvas.get_pixel(1, 1) == (255, 255, 255, 255)


def test_invalid_dimensions_raise():
    with pytest.raises(ValueError):
        Canvas(0, 5)
    with pytest.raises(ValueError):
        Canvas(5, -1)


def test_fill_rect_paints_opaque_pixels_and_leaves_rest_transparent():
    canvas = Canvas(4, 4)
    canvas.fill_rect(0, 0, 2, 2, "red")
    assert canvas.get_pixel(0, 0) == (255, 0, 0, 255)
    assert canvas.get_pixel(1, 1) == (255, 0, 0, 255)
    assert canvas.get_pixel(3, 3) == (0, 0, 0, 0)


def test_opacity_scales_alpha():
    canvas = Canvas(2, 2)
    canvas.fill_rect(0, 0, 2, 2, "blue", opacity=0.5)
    red, green, blue, alpha = canvas.get_pixel(0, 0)
    assert (red, green, blue) == (0, 0, 255)
    assert abs(alpha - 128) <= 1


def test_color_alpha_and_opacity_multiply():
    canvas = Canvas(1, 1)
    canvas.fill_rect(0, 0, 1, 1, "rgba(0,255,0,0.5)", opacity=0.5)
    assert abs(canvas.get_pixel(0, 0)[3] - 64) <= 1


def test_source_over_compositing():
    canvas = Canvas(1, 1, background="red")
    canvas.fill_rect(0, 0, 1, 1, "blue", opacity=0.5)
    red, green, blue, alpha = canvas.get_pixel(0, 0)
    assert alpha == 255
    assert abs(red - 128) <= 1 and green == 0 and abs(blue - 128) <= 1


def test_compositing_two_translucent_layers_in_straight_alpha():
    canvas = Canvas(1, 1)
    canvas.fill_rect(0, 0, 1, 1, "red", opacity=0.5)
    canvas.fill_rect(0, 0, 1, 1, "blue", opacity=0.5)
    red, green, blue, alpha = canvas.get_pixel(0, 0)
    assert abs(alpha - 191) <= 1
    assert abs(red - 85) <= 1 and abs(blue - 170) <= 1


def test_antialiased_edge_is_partially_transparent():
    canvas = Canvas(4, 1)
    canvas.fill_rect(0.5, 0, 3, 1, "black")
    assert 0 < canvas.get_pixel(0, 0)[3] < 255
    assert abs(canvas.get_pixel(0, 0)[3] - 128) <= 1
    assert canvas.get_pixel(1, 0)[3] == 255


def test_fill_circle_area():
    canvas = Canvas(40, 40)
    canvas.fill_circle(20, 20, 15, "black")
    assert total_alpha(canvas) == pytest.approx(math.pi * 225, rel=0.01)
    assert canvas.get_pixel(20, 20)[3] == 255
    assert canvas.get_pixel(1, 1)[3] == 0


def test_fill_ellipse_area():
    canvas = Canvas(40, 40)
    canvas.fill_ellipse(20, 20, 15, 8, "black")
    assert total_alpha(canvas) == pytest.approx(math.pi * 15 * 8, rel=0.01)


def test_rounded_rect_corners_are_cut():
    canvas = Canvas(20, 20)
    canvas.fill_rect(0, 0, 20, 20, "black", rx=6)
    assert canvas.get_pixel(0, 0)[3] == 0
    assert canvas.get_pixel(10, 10)[3] == 255
    assert total_alpha(canvas) == pytest.approx(400 - (4 - math.pi) * 36, rel=0.01)


def test_fill_polygon():
    canvas = Canvas(10, 10)
    canvas.fill_polygon([(0, 0), (10, 0), (0, 10)], "black")
    assert total_alpha(canvas) == pytest.approx(50, rel=0.01)


def test_fill_path_with_transform_string_and_matrix():
    first = Canvas(10, 10)
    first.fill_path("M0 0 h2 v2 h-2 z", "black", transform="translate(4,4)")
    assert first.get_pixel(5, 5)[3] == 255
    assert first.get_pixel(1, 1)[3] == 0
    second = Canvas(10, 10)
    second.fill_path("M0 0 h2 v2 h-2 z", "black", transform=Matrix.scaling(3, 3))
    assert second.get_pixel(5, 5)[3] == 255


def test_fill_path_evenodd_ring():
    ring = "M0 0 H20 V20 H0 Z M5 5 H15 V15 H5 Z"
    nonzero = Canvas(20, 20)
    nonzero.fill_path(ring, "black")
    evenodd = Canvas(20, 20)
    evenodd.fill_path(ring, "black", fill_rule="evenodd")
    assert nonzero.get_pixel(10, 10)[3] == 255
    assert evenodd.get_pixel(10, 10)[3] == 0
    assert evenodd.get_pixel(2, 10)[3] == 255


def test_fill_none_draws_nothing():
    canvas = Canvas(4, 4)
    canvas.fill_rect(0, 0, 4, 4, "none")
    assert canvas.get_pixel(1, 1) == (0, 0, 0, 0)


def test_invalid_fill_rule_raises():
    with pytest.raises(ValueError):
        Canvas(4, 4).fill_path("M0 0 H4 V4 Z", "black", fill_rule="odd")


def test_stroke_line_with_round_caps():
    canvas = Canvas(20, 20)
    canvas.stroke_path("M4 10 L16 10", "black", 4)
    assert canvas.get_pixel(10, 9)[3] == 255
    assert canvas.get_pixel(10, 10)[3] == 255
    assert canvas.get_pixel(10, 13)[3] == 0
    assert canvas.get_pixel(3, 10)[3] == 255
    assert canvas.get_pixel(0, 10)[3] == 0
    assert total_alpha(canvas) == pytest.approx(12 * 4 + math.pi * 4, rel=0.02)


def test_stroke_sharp_corner_has_no_gaps():
    canvas = Canvas(30, 30)
    canvas.stroke_path("M5 5 L25 15 L5 25", "black", 3)
    assert canvas.get_pixel(24, 15)[3] == 255
    assert canvas.get_pixel(15, 15)[3] == 0


def test_closed_stroke_outline():
    canvas = Canvas(20, 20)
    canvas.stroke_path("M4 4 H16 V16 H4 Z", "black", 2)
    assert canvas.get_pixel(4, 10)[3] == 255
    assert canvas.get_pixel(10, 10)[3] == 0
    assert canvas.get_pixel(4, 4)[3] == 255


def test_stroke_width_scales_with_transform():
    canvas = Canvas(40, 40)
    canvas.stroke_path("M2 10 L18 10", "black", 2, transform="scale(2)")
    assert canvas.get_pixel(20, 18)[3] == 255
    assert canvas.get_pixel(20, 22)[3] == 0


def test_stroke_curve_is_continuous():
    canvas = Canvas(40, 40)
    canvas.stroke_path("M5 20 C5 0 35 0 35 20", "black", 2)
    assert canvas.get_pixel(20, 5)[3] > 200
    assert canvas.get_pixel(20, 20)[3] == 0


def test_zero_width_stroke_draws_nothing():
    canvas = Canvas(10, 10)
    canvas.stroke_path("M0 5 L10 5", "black", 0)
    assert total_alpha(canvas) == 0


def test_to_png_bytes_and_save(tmp_path):
    canvas = Canvas(3, 2)
    canvas.fill_rect(0, 0, 1, 1, "lime")
    data = canvas.to_png_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    width, height, pixels = decode_png(data)
    assert (width, height) == (3, 2)
    assert pixels[:4] == bytes([0, 255, 0, 255])
    assert pixels[4:8] == bytes([0, 0, 0, 0])
    target = tmp_path / "out.png"
    canvas.save(target)
    assert target.read_bytes() == data

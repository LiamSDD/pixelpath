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


CORNER = "M4 4 L16 4 L16 16"


def test_stroke_defaults_remain_round_caps_and_joins():
    default = Canvas(20, 20)
    default.stroke_path(CORNER, "black", 4)
    explicit = Canvas(20, 20)
    explicit.stroke_path(CORNER, "black", 4, linecap="round", linejoin="round")
    assert default.to_rgba_bytes() == explicit.to_rgba_bytes()


def test_stroke_butt_cap_ends_flush_with_endpoints():
    canvas = Canvas(20, 20)
    canvas.stroke_path("M4 10 L16 10", "black", 4, linecap="butt")
    assert canvas.get_pixel(4, 10)[3] == 255
    assert canvas.get_pixel(15, 10)[3] == 255
    assert canvas.get_pixel(3, 10)[3] == 0
    assert canvas.get_pixel(16, 10)[3] == 0
    assert total_alpha(canvas) == pytest.approx(12 * 4, rel=0.01)


def test_stroke_square_cap_extends_by_half_width():
    canvas = Canvas(20, 20)
    canvas.stroke_path("M4 10 L16 10", "black", 4, linecap="square")
    assert canvas.get_pixel(2, 8)[3] == 255
    assert canvas.get_pixel(17, 11)[3] == 255
    assert canvas.get_pixel(1, 10)[3] == 0
    assert canvas.get_pixel(18, 10)[3] == 0
    assert total_alpha(canvas) == pytest.approx(16 * 4, rel=0.01)


def test_stroke_square_cap_follows_direction():
    canvas = Canvas(20, 20)
    canvas.stroke_path("M10 4 L10 16", "black", 2, linecap="square")
    assert canvas.get_pixel(10, 3)[3] == 255
    assert canvas.get_pixel(9, 16)[3] == 255
    assert canvas.get_pixel(10, 2)[3] == 0
    assert canvas.get_pixel(10, 17)[3] == 0


def test_stroke_miter_join_fills_corner():
    canvas = Canvas(20, 20)
    canvas.stroke_path(CORNER, "black", 4, linecap="butt", linejoin="miter")
    assert canvas.get_pixel(17, 2)[3] == 255
    assert canvas.get_pixel(16, 3)[3] == 255
    assert canvas.get_pixel(3, 4)[3] == 0
    assert canvas.get_pixel(16, 16)[3] == 0


def test_stroke_bevel_join_cuts_corner():
    canvas = Canvas(20, 20)
    canvas.stroke_path(CORNER, "black", 4, linecap="butt", linejoin="bevel")
    assert canvas.get_pixel(17, 2)[3] == 0
    assert canvas.get_pixel(16, 3)[3] == 255
    assert canvas.get_pixel(15, 5)[3] == 255
    assert 100 < canvas.get_pixel(17, 3)[3] < 155


def test_stroke_round_join_is_between_bevel_and_miter():
    canvas = Canvas(20, 20)
    canvas.stroke_path(CORNER, "black", 4, linecap="butt", linejoin="round")
    assert 0 < canvas.get_pixel(17, 2)[3] < 255


def test_stroke_miter_limit_falls_back_to_bevel():
    canvas = Canvas(20, 20)
    canvas.stroke_path(CORNER, "black", 4, linejoin="miter", miterlimit=1.4)
    assert canvas.get_pixel(17, 2)[3] == 0
    canvas = Canvas(20, 20)
    canvas.stroke_path(CORNER, "black", 4, linejoin="miter", miterlimit=1.5)
    assert canvas.get_pixel(17, 2)[3] == 255


def test_stroke_sharp_miter_uses_default_limit_of_four():
    canvas = Canvas(60, 30)
    canvas.stroke_path("M2 5 L50 15 L2 25", "black", 2, linecap="butt", linejoin="miter")
    assert canvas.get_pixel(51, 15)[3] == 0
    assert canvas.get_pixel(49, 15)[3] == 255
    canvas = Canvas(60, 30)
    canvas.stroke_path("M2 5 L50 15 L2 25", "black", 2, linecap="butt", linejoin="miter", miterlimit=20)
    assert canvas.get_pixel(50, 15)[3] > 200
    assert canvas.get_pixel(54, 15)[3] > 0
    assert canvas.get_pixel(55, 15)[3] == 0


def test_closed_stroke_miters_every_corner_and_has_no_caps():
    canvas = Canvas(20, 20)
    canvas.stroke_path("M4 4 H16 V16 H4 Z", "black", 2, linecap="square", linejoin="miter")
    for x, y in ((3, 3), (16, 3), (16, 16), (3, 16)):
        assert canvas.get_pixel(x, y)[3] == 255
    assert canvas.get_pixel(2, 4)[3] == 0
    assert canvas.get_pixel(4, 2)[3] == 0
    assert total_alpha(canvas) == pytest.approx(14 * 14 - 10 * 10, rel=0.01)


def test_zero_length_subpath_caps():
    round_canvas = Canvas(20, 20)
    round_canvas.stroke_path("M10 10 L10 10", "black", 4, linecap="round")
    assert round_canvas.get_pixel(10, 10)[3] == 255
    assert 0 < round_canvas.get_pixel(8, 8)[3] < 255
    square_canvas = Canvas(20, 20)
    square_canvas.stroke_path("M10 10 L10 10", "black", 4, linecap="square")
    assert square_canvas.get_pixel(8, 8)[3] == 255
    assert square_canvas.get_pixel(11, 11)[3] == 255
    butt_canvas = Canvas(20, 20)
    butt_canvas.stroke_path("M10 10 L10 10", "black", 4, linecap="butt")
    assert total_alpha(butt_canvas) == 0


@pytest.mark.parametrize(
    "options",
    [{"linecap": "flat"}, {"linejoin": "arcs"}, {"miterlimit": 0.5}],
)
def test_invalid_stroke_options_raise(options):
    with pytest.raises(ValueError):
        Canvas(4, 4).stroke_path("M0 2 H4", "black", 1, **options)

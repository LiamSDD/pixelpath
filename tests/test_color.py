import pytest

from pixelpath.color import ColorError, parse_color


def test_short_hex():
    assert parse_color("#f00") == (255, 0, 0, 1.0)


def test_short_hex_with_alpha():
    assert parse_color("#f008") == (255, 0, 0, pytest.approx(0x88 / 255))


def test_long_hex():
    assert parse_color("#1a2B3c") == (0x1A, 0x2B, 0x3C, 1.0)


def test_long_hex_with_alpha():
    assert parse_color("#ff000080") == (255, 0, 0, pytest.approx(128 / 255))


def test_rgb_function():
    assert parse_color("rgb(255, 0, 10)") == (255, 0, 10, 1.0)
    assert parse_color("rgb(255 0 10)") == (255, 0, 10, 1.0)


def test_rgb_percentages():
    assert parse_color("rgb(100%, 0%, 50%)") == (255, 0, 128, 1.0)


def test_rgba_function():
    assert parse_color("rgba(0,0,255,0.5)") == (0, 0, 255, 0.5)
    assert parse_color("rgba(0 0 255 / 25%)") == (0, 0, 255, 0.25)


def test_rgb_values_are_clamped():
    assert parse_color("rgb(300, -5, 0)") == (255, 0, 0, 1.0)


def test_none_and_transparent():
    assert parse_color("none") is None
    assert parse_color("transparent") == (0, 0, 0, 0.0)


def test_current_color_defaults_to_black():
    assert parse_color("currentColor") == (0, 0, 0, 1.0)
    assert parse_color("currentcolor", current_color=(1, 2, 3, 1.0)) == (1, 2, 3, 1.0)


@pytest.mark.parametrize(
    "name, expected",
    [
        ("black", (0, 0, 0)),
        ("silver", (192, 192, 192)),
        ("gray", (128, 128, 128)),
        ("white", (255, 255, 255)),
        ("maroon", (128, 0, 0)),
        ("red", (255, 0, 0)),
        ("purple", (128, 0, 128)),
        ("fuchsia", (255, 0, 255)),
        ("green", (0, 128, 0)),
        ("lime", (0, 255, 0)),
        ("olive", (128, 128, 0)),
        ("yellow", (255, 255, 0)),
        ("navy", (0, 0, 128)),
        ("blue", (0, 0, 255)),
        ("teal", (0, 128, 128)),
        ("aqua", (0, 255, 255)),
    ],
)
def test_basic_named_colors(name, expected):
    assert parse_color(name) == expected + (1.0,)


def test_names_are_case_insensitive_and_trimmed():
    assert parse_color("  RED ") == (255, 0, 0, 1.0)


def test_tuples_pass_through():
    assert parse_color((1, 2, 3)) == (1, 2, 3, 1.0)
    assert parse_color((1, 2, 3, 0.5)) == (1, 2, 3, 0.5)


@pytest.mark.parametrize("text", ["#12", "#12345", "#ggg", "rgb(1,2)", "notacolor", "", "rgb(a,b,c)"])
def test_invalid_colors_raise(text):
    with pytest.raises(ColorError):
        parse_color(text)


def test_color_error_is_value_error():
    assert issubclass(ColorError, ValueError)

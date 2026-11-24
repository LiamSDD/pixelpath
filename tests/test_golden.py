import os
import pytest

from pixelpath import __version__, parse_path, render_svg
from pixelpath.png import decode_png

LOGO = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <rect x="4" y="4" width="56" height="56" rx="12" fill="#1e3a8a"/>
  <g fill="#ffffff">
    <circle cx="32" cy="26" r="10"/>
    <path d="M28 30 L36 30 L38 48 L26 48 Z"/>
  </g>
  <circle cx="32" cy="26" r="4" fill="#1e3a8a"/>
  <path d="M8 58 h48" stroke="#f59e0b" stroke-width="2"/>
</svg>"""

NAVY = (30, 58, 138, 255)
WHITE = (255, 255, 255, 255)
AMBER = (245, 158, 11, 255)
CLEAR = (0, 0, 0, 0)


@pytest.fixture(scope="module")
def logo():
    return render_svg(LOGO)


@pytest.mark.parametrize(
    "x, y, expected",
    [
        (0, 0, CLEAR),
        (63, 63, CLEAR),
        (5, 5, CLEAR),
        (10, 32, NAVY),
        (32, 54, NAVY),
        (32, 26, NAVY),
        (32, 19, WHITE),
        (32, 40, WHITE),
        (24, 26, WHITE),
        (20, 58, AMBER),
    ],
)
def test_logo_pixels(logo, x, y, expected):
    assert logo.get_pixel(x, y) == expected


def test_logo_edges_are_antialiased(logo):
    edge_alphas = [logo.get_pixel(x, 4)[3] for x in range(64)]
    assert any(0 < alpha < 255 for alpha in edge_alphas)
    blended = [logo.get_pixel(x, y) for y in range(14, 38) for x in range(20, 44)]
    assert any(NAVY[0] < red < 255 for red, _, _, _ in blended)


def test_logo_png_round_trip(logo):
    width, height, pixels = decode_png(logo.to_png_bytes())
    assert (width, height) == (64, 64)
    assert tuple(pixels[(32 * 64 + 10) * 4 : (32 * 64 + 10) * 4 + 4]) == NAVY
    assert pixels[3] == 0


def test_public_api():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "pyproject.toml"), encoding="utf-8") as handle:
        assert f'version = "{__version__}"' in handle.read()
    assert parse_path("M0 0")[0] == ("M", (0.0, 0.0))

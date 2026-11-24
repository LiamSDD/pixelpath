# pixelpath

**Zero-dependency SVG rasterizer for Python. Renders SVG paths and shapes to anti-aliased, transparent PNGs. No Cairo, no Pillow, no native code.**

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-3776ab.svg)](https://www.python.org/)
[![Dependencies: 0](https://img.shields.io/badge/dependencies-0-brightgreen.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Tests: 243 passing](https://img.shields.io/badge/tests-243%20passing-brightgreen.svg)](tests)

pixelpath turns icons, logos, badges and other path-based SVGs into PNG files
using nothing but the Python standard library (`zlib`, `struct`, `math` and
`xml.etree`).

## Why pixelpath

- **No system libraries.** No Cairo, librsvg, Pillow, ImageMagick or headless
  browser. Nothing to compile, nothing to `apt-get`.
- **Works anywhere Python runs.** CI runners, AWS Lambda, slim containers, locked-down
  corporate machines, Pyodide: if it runs CPython 3.9 or newer, it renders.
- **Transparent, anti-aliased output.** Real alpha channel, smooth edges, straight-alpha
  RGBA PNGs that drop cleanly into web pages, READMEs and app bundles.
- **Safe XML handling.** Documents containing `<!DOCTYPE` or `<!ENTITY` are refused
  before parsing, which shuts the door on XXE and "billion laughs" entity expansion.
- **Small and readable.** A few hundred lines per stage, each stage separately
  tested and usable on its own.

## Install

```bash
pip install git+https://github.com/LiamSDD/pixelpath
```

## Quick start

### Command line

```bash
pixelpath logo.svg -o logo.png                    # intrinsic size
pixelpath logo.svg -o logo@512.png --width 512    # height follows aspect ratio
pixelpath logo.svg -o logo@2x.png --scale 2
pixelpath logo.svg -o logo-white.png --background white
python -m pixelpath logo.svg -o logo.png          # same thing, no console script needed
```

`--width`, `--height` and `--scale` are mutually exclusive. When `-o` is omitted
the output is written next to the input with a `.png` suffix. The exit status
is `0` on success and `1` on an error, which is printed to stderr.

### Python API

```python
from pixelpath import Canvas, render_svg

render_svg("logo.svg", width=256).save("logo.png")

png_bytes = render_svg('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
                       '<circle cx="5" cy="5" r="4" fill="#4f46e5"/></svg>', scale=8).to_png_bytes()

canvas = Canvas(200, 120)
canvas.fill_rect(4, 4, 192, 112, "#4f46e5", rx=18)
canvas.fill_circle(60, 60, 34, "#eef2ff")
canvas.fill_path("M20 20 H80 V80 H20 Z M35 35 H65 V65 H35 Z", "#e11d48", fill_rule="evenodd",
                 transform="translate(100 10) scale(0.9)")
canvas.stroke_path("M46 60 l10 10 l18 -20", "#16a34a", width=7)
canvas.save("drawing.png")
```

| Function / method | Purpose |
| --- | --- |
| `render_svg(source, width=None, height=None, scale=None, background=None)` | Render SVG text, bytes or a file path into a `Canvas`. |
| `Canvas(width, height, background=None)` | Blank RGBA canvas, transparent unless a background colour is given. |
| `fill_path(d, color, opacity=1, fill_rule="nonzero", transform=None)` | Fill SVG path data (string or parsed commands). |
| `fill_rect(x, y, w, h, color, rx=0, ry=None, opacity=1, transform=None)` | Filled, optionally rounded, rectangle. |
| `fill_circle(cx, cy, r, color, ...)` / `fill_ellipse(cx, cy, rx, ry, color, ...)` | Filled circle or ellipse. |
| `fill_polygon(points, color, opacity=1, fill_rule="nonzero", transform=None)` | Filled polygon from `(x, y)` pairs. |
| `stroke_path(d, color, width, opacity=1, transform=None)` | Stroke with round joins and round caps. |
| `get_pixel(x, y)`, `to_rgba_bytes()`, `to_png_bytes()`, `save(path)` | Read pixels or export. |
| `parse_path(d)` | Parse path data into absolute `M`, `L`, `C`, `Q`, `A`, `Z` commands. |

Colours accept any string listed under [Supported SVG features](#supported-svg-features)
or an `(r, g, b)` / `(r, g, b, alpha)` tuple with channels 0-255 and alpha 0-1.
Transforms accept an SVG transform string or a `pixelpath.Matrix`.

## Showcase

Every image below was rendered by pixelpath itself from the SVGs in
[`examples/`](examples) at `--scale 2`.

| Key-lock mark | Badge | Even-odd ring |
| :---: | :---: | :---: |
| ![Key-lock mark](docs/keylock.png) | ![Badge](docs/badge.png) | ![Even-odd ring](docs/ring.png) |
| [`keylock.svg`](examples/keylock.svg): rounded rect, stroked arc shackle, keyhole | [`badge.svg`](examples/badge.svg): rounded rects, circle, arc stroke, group transform, fill-opacity | [`ring.svg`](examples/ring.svg): `fill-rule="evenodd"` concentric arcs, transformed self-intersecting star |

## Supported SVG features

| Area | Supported |
| --- | --- |
| Document | `<svg>` with `width`, `height` (`px`, `pt`, `pc`, `mm`, `cm`, `in`, `em`, `ex`), `viewBox`; `preserveAspectRatio="xMidYMid meet"` behaviour; default size 300x150 |
| Structure | Nested `<g>` (also `<a>`, `<switch>` and nested `<svg>` treated as groups) |
| References | `<use>` with `href` or `xlink:href` pointing at any element by `#id`, including elements inside `<defs>`; `x`/`y` translation, the `<use>` element's `transform`, `opacity` and presentation attributes inherited by the referenced content; `<symbol>` with `viewBox` scaled to the `<use>` `width`/`height` (default 100%) using `xMidYMid meet`; nesting limited to 32 levels and 10,000 expanded elements, circular references raise `SVGError` |
| Shapes | `path`, `rect` (with `rx`/`ry`), `circle`, `ellipse`, `polygon`, `polyline`, `line` |
| Path data | `M L H V C S Q T A Z` absolute and relative, implicit repeats, compact numbers (`1.5.5`, `-1-2`, `1e-3`), unseparated arc flags, S/T reflection |
| Transforms | `matrix`, `translate`, `scale`, `rotate` (with optional centre), `skewX`, `skewY`, lists of any length |
| Fill | `fill`, `fill-opacity`, `fill-rule` (`nonzero`, `evenodd`), inherited through groups |
| Stroke | `stroke`, `stroke-width`, `stroke-opacity` on every shape, round joins and caps |
| Opacity | `opacity` on groups and shapes, `display="none"`, `visibility="hidden"` |
| Styling | Presentation attributes and inline `style="..."` declarations |
| Colours | `#rgb`, `#rgba`, `#rrggbb`, `#rrggbbaa`, `rgb()`, `rgba()` (numbers or percentages, comma or space syntax), `none`, `transparent`, `currentColor`, the 16 basic CSS names (plus `grey`, `cyan`, `magenta`) |
| Paint fallback | `fill="url(#gradient) blue"` uses the fallback colour |
| Units | Percentages on shape geometry resolve against the `viewBox` |

### Not supported

These are skipped without raising, so documents that use them still render
everything else:

- Gradients (`linearGradient`, `radialGradient`) and patterns; a `url(...)` paint
  without a fallback colour paints nothing
- `<text>`, fonts, `<image>`, `<foreignObject>`
- Filters, masks, clip paths, markers
- `<use>` references to external files (`href="other.svg#id"`) and missing ids;
  symbol clipping to its viewport, `preserveAspectRatio` on `<symbol>`, and
  `width`/`height` on a `<use>` that references a nested `<svg>`
- Rendering `<defs>` or `<symbol>` content directly (only through `<use>`, as in SVG)
- `<style>` sheets and CSS selectors (inline `style` attributes are supported)
- `stroke-dasharray`, `stroke-linejoin` / `stroke-linecap` other than round
  (miter, bevel, butt and square are drawn as round), `stroke-miterlimit`
- `preserveAspectRatio` values other than `xMidYMid meet`
- Named colours beyond the basic set; unknown colour values are ignored, as if the
  attribute were absent

Approximations worth knowing about: group `opacity` is multiplied into each child
rather than composited as an isolated layer, and stroke width under a non-uniform
transform uses the square root of the transform's area scale.

## How it works

```
SVG text ─▶ parse ─▶ flatten ─▶ scanline coverage ─▶ composite ─▶ PNG
```

1. **Parse.** The document is screened for `<!DOCTYPE`/`<!ENTITY` (both textually
   and with an expat pre-pass that rejects any doctype or entity declaration in any
   encoding), then parsed with `xml.etree`. Path data is tokenised by a hand-written
   scanner and normalised to absolute `M`, `L`, `C`, `Q`, `A` and `Z` commands.
2. **Flatten.** Control points are transformed to device space (affine maps preserve
   Bezier curves), then curves are split into line segments. The segment count per
   curve is derived from the curve's second differences so the polyline never deviates
   more than 0.05 px from the true curve. Arcs go through the SVG implementation-notes
   endpoint-to-centre conversion and become at most quarter-turn cubic segments.
3. **Scanline coverage.** Each pixel row is sampled with 16 sub-scanlines. On every
   sub-scanline the edge crossings are sorted and walked with a winding counter, so
   `nonzero` and `evenodd` are exact for holes and self-intersections. Horizontal
   coverage within a span is computed analytically, giving smooth anti-aliasing in
   both directions with a prefix-sum accumulation per row.
4. **Composite.** Coverage multiplies the paint alpha, and the result is blended
   source-over in straight (non-premultiplied) alpha on a floating-point buffer.
   Strokes are built from quads per segment plus circles at joins and caps, filled
   in one `nonzero` pass so overlaps never double-blend.
5. **PNG.** A minimal encoder writes the signature, `IHDR`, a zlib-compressed `IDAT`
   and `IEND`, each with its CRC-32.

## Performance

Measured with [`bench.py`](bench.py) on an Apple M3 laptop with CPython 3.9.6:

| Workload | Time |
| --- | --- |
| 512x512 scene: rounded rect, three curved fills (one even-odd), a thick quadratic stroke, render + PNG encode | 0.30 s (best of 5) |
| `examples/keylock.svg` at 512 px wide | 0.21 s |
| `examples/badge.svg` at 512 px wide | 0.17 s |
| `examples/ring.svg` at 512 px wide | 0.17 s |

Cost grows with the number of covered pixels and the number of edges. pixelpath
is designed for icons, logos and diagrams, not for rendering huge or very dense
illustrations.

## Development

```bash
git clone https://github.com/LiamSDD/pixelpath
cd pixelpath
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python3 -m pytest -q      # 243 tests
python3 bench.py
```

The test suite covers path-parser edge cases, arc conversion, coverage accuracy
(a filled square's total coverage equals its area within 0.5%), fill rules, PNG
validity and CRCs, transforms, colour parsing, XXE refusal, the CLI end to end and
a golden logo render with exact pixel colours. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE) © 2026 LiamSDD

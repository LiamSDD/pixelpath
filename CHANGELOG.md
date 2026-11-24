# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.0] - 2026-11-24

### Added

- `<use>` elements (`href` and `xlink:href`) referencing any element by id,
  including content inside `<defs>`, with `x`/`y` translation, the `<use>`
  element's `transform` and inherited presentation attributes.
- `<symbol>` instancing through `<use>`, mapping the symbol `viewBox` onto the
  `<use>` `width`/`height` with `xMidYMid meet`.
- `stroke-linecap` (`butt`, `round`, `square`), `stroke-linejoin` (`miter`,
  `round`, `bevel`) and `stroke-miterlimit` in `render_svg`, inherited like other
  presentation attributes. Miter joins beyond the limit fall back to bevel.
- Keyword-only `linecap`, `linejoin` and `miterlimit` parameters on
  `Canvas.stroke_path`.
- `SECURITY.md` with the supported versions, private reporting through GitHub
  and the security scope.
- Issue templates for bug reports and feature requests, an issue template
  config pointing questions to GitHub Discussions, and a pull request template.

### Changed

- `render_svg` now uses the SVG defaults of `butt` caps and `miter` joins (miter
  limit 4) instead of drawing every stroke with round caps and joins. Documents
  that relied on the old look should set `stroke-linecap="round"` and
  `stroke-linejoin="round"`. `Canvas.stroke_path` still defaults to round caps
  and joins, so direct callers are unaffected. The showcase images were
  regenerated.

### Security

- `<use>` expansion is bounded: circular references raise `SVGError`, and nesting
  deeper than 32 levels or expanding more than 10,000 elements raises
  `UnsafeSVGError`, so crafted files cannot cause exponential blow-up.
- `render_svg` and the `pixelpath` command refuse output larger than 16384 pixels
  per side or 100 megapixels in total with an `SVGError`, and reject non-finite
  sizes with a `ValueError`, so huge declared dimensions or size options cannot
  exhaust memory.

## [0.1.0] - 2026-11-24

### Added

- SVG path-data parser covering every command (`M L H V C S Q T A Z`, absolute and
  relative), implicit repeated commands, compact numbers and unseparated arc flags.
- Adaptive Bezier flattening and SVG endpoint-to-centre arc conversion
  (with radius scale-up and zero-radius handling).
- Affine transforms and the full SVG `transform` attribute syntax.
- Anti-aliased scanline rasterizer with `nonzero` and `evenodd` fill rules.
- `Canvas` drawing API with straight-alpha source-over compositing, fills and
  round-join, round-cap strokes.
- `render_svg` for `<svg>`, `<g>`, `path`, `rect`, `circle`, `ellipse`, `polygon`,
  `polyline` and `line`, with inherited presentation attributes and inline styles.
- Refusal of documents containing `<!DOCTYPE` or `<!ENTITY` declarations.
- Pure-Python RGBA PNG encoder and a small validating decoder.
- `pixelpath` command-line tool and `python -m pixelpath`.

[Unreleased]: https://github.com/LiamSDD/pixelpath/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/LiamSDD/pixelpath/releases/tag/v0.1.0

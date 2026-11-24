# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- `<use>` elements (`href` and `xlink:href`) referencing any element by id,
  including content inside `<defs>`, with `x`/`y` translation, the `<use>`
  element's `transform` and inherited presentation attributes.
- `<symbol>` instancing through `<use>`, mapping the symbol `viewBox` onto the
  `<use>` `width`/`height` with `xMidYMid meet`.

### Security

- `<use>` expansion is bounded: circular references raise `SVGError`, and nesting
  deeper than 32 levels or expanding more than 10,000 elements raises
  `UnsafeSVGError`, so crafted files cannot cause exponential blow-up.

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

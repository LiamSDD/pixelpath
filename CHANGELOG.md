# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

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

[0.1.0]: https://github.com/LiamSDD/pixelpath/releases/tag/v0.1.0

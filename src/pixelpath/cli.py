import argparse
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__
from .color import ColorError, parse_color
from .svg import SVGError, render_svg


def _positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected a positive integer, got {text!r}") from None
    if value <= 0:
        raise argparse.ArgumentTypeError(f"expected a positive integer, got {text!r}")
    return value


def _positive_float(text: str) -> float:
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected a positive number, got {text!r}") from None
    if value <= 0:
        raise argparse.ArgumentTypeError(f"expected a positive number, got {text!r}")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pixelpath",
        description="Render an SVG file to an anti-aliased, transparent PNG using pure Python.",
    )
    parser.add_argument("input", type=Path, help="SVG file to render")
    parser.add_argument("-o", "--output", type=Path, help="PNG file to write (default: input name with .png)")
    size = parser.add_mutually_exclusive_group()
    size.add_argument("--width", type=_positive_int, help="output width in pixels; height keeps the aspect ratio")
    size.add_argument("--height", type=_positive_int, help="output height in pixels; width keeps the aspect ratio")
    size.add_argument("--scale", type=_positive_float, help="multiply the intrinsic SVG size by this factor")
    parser.add_argument("--background", metavar="COLOR", help="background colour, e.g. white or '#112233' (default: transparent)")
    parser.add_argument("--version", action="version", version=f"pixelpath {__version__}")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    arguments = build_parser().parse_args(argv)
    output = arguments.output or arguments.input.with_suffix(".png")
    try:
        if arguments.background is not None:
            parse_color(arguments.background)
        canvas = render_svg(
            arguments.input,
            width=arguments.width,
            height=arguments.height,
            scale=arguments.scale,
            background=arguments.background,
        )
        canvas.save(output)
    except (SVGError, ColorError, OSError, ValueError) as error:
        print(f"pixelpath: error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

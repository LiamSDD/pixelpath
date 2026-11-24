import math
import os
import re
import xml.etree.ElementTree as ElementTree
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from xml.parsers import expat

from .canvas import DEFAULT_MITERLIMIT, LINECAPS, LINEJOINS, Canvas
from .color import RGBA, ColorError, ColorInput, parse_color
from .path import Command, PathError, ellipse_commands, parse_path, polygon_commands, rect_commands
from .transform import Matrix, TransformError, parse_transform

SVG_NAMESPACE = "http://www.w3.org/2000/svg"
XLINK_HREF = "{http://www.w3.org/1999/xlink}href"
MAX_USE_DEPTH = 32
MAX_USE_EXPANSION = 10000
DEFAULT_WIDTH = 300.0
DEFAULT_HEIGHT = 150.0
NUMBER_PATTERN = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
LENGTH_PATTERN = re.compile(r"^\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*(px|pt|pc|mm|cm|in|em|ex|%)?\s*$", re.IGNORECASE)
UNIT_SCALES = {"": 1.0, "px": 1.0, "pt": 96 / 72, "pc": 16.0, "mm": 96 / 25.4, "cm": 96 / 2.54, "in": 96.0, "em": 16.0, "ex": 8.0}
CONTAINER_TAGS = {"svg", "g", "a", "switch"}
SHAPE_TAGS = {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon"}
INHERITED_PROPERTIES = (
    "fill",
    "fill-opacity",
    "fill-rule",
    "stroke",
    "stroke-width",
    "stroke-opacity",
    "stroke-linecap",
    "stroke-linejoin",
    "stroke-miterlimit",
    "color",
    "visibility",
)
STYLE_PROPERTIES = set(INHERITED_PROPERTIES) | {"opacity", "display"}
INITIAL_STYLE = {
    "fill": "black",
    "fill-opacity": "1",
    "fill-rule": "nonzero",
    "stroke": "none",
    "stroke-width": "1",
    "stroke-opacity": "1",
    "stroke-linecap": "butt",
    "stroke-linejoin": "miter",
    "stroke-miterlimit": "4",
    "color": "black",
    "visibility": "visible",
}
SourceInput = Union[str, bytes, bytearray, "os.PathLike[str]"]
ViewBox = Tuple[float, float, float, float]


class SVGError(ValueError):
    pass


class UnsafeSVGError(SVGError):
    pass


UNSAFE_MESSAGE = (
    "refusing to parse SVG containing a <!DOCTYPE> or <!ENTITY> declaration "
    "(protection against XXE and entity-expansion attacks)"
)


def _read_source(source: SourceInput) -> Union[str, bytes]:
    if isinstance(source, (bytes, bytearray)):
        return bytes(source)
    if isinstance(source, str) and source.lstrip().startswith("<"):
        return source
    if isinstance(source, (str, os.PathLike)):
        try:
            return Path(source).read_bytes()
        except OSError as error:
            raise SVGError(f"cannot read SVG file {os.fspath(source)!r}: {error.strerror or error}") from error
    raise TypeError(f"expected SVG text, bytes or a file path, got {type(source).__name__}")


def _refuse_declarations(*_: object) -> None:
    raise UnsafeSVGError(UNSAFE_MESSAGE)


def _ensure_safe(document: Union[str, bytes]) -> None:
    lowered = document.lower()
    markers = (b"<!doctype", b"<!entity") if isinstance(document, bytes) else ("<!doctype", "<!entity")
    if any(marker in lowered for marker in markers):
        raise UnsafeSVGError(UNSAFE_MESSAGE)
    parser = expat.ParserCreate()
    parser.StartDoctypeDeclHandler = _refuse_declarations
    parser.EntityDeclHandler = _refuse_declarations
    parser.UnparsedEntityDeclHandler = _refuse_declarations
    parser.ExternalEntityRefHandler = _refuse_declarations
    try:
        parser.Parse(document, True)
    except expat.ExpatError as error:
        raise SVGError(f"malformed SVG/XML: {error}") from error


def _parse_document(document: Union[str, bytes]) -> ElementTree.Element:
    _ensure_safe(document)
    try:
        return ElementTree.fromstring(document)
    except ElementTree.ParseError as error:
        raise SVGError(f"malformed SVG/XML: {error}") from error


def _split_tag(tag: object) -> Tuple[Optional[str], str]:
    if not isinstance(tag, str):
        return None, ""
    if tag.startswith("{"):
        namespace, _, local = tag[1:].partition("}")
        return namespace, local
    return None, tag


def _is_svg_element(element: ElementTree.Element) -> Optional[str]:
    namespace, local = _split_tag(element.tag)
    if namespace not in (None, SVG_NAMESPACE):
        return None
    return local


def _parse_length(text: Optional[str], reference: float = 0.0, default: Optional[float] = 0.0) -> Optional[float]:
    if text is None:
        return default
    match = LENGTH_PATTERN.match(text)
    if not match:
        return default
    value = float(match.group(1))
    unit = (match.group(2) or "").lower()
    if unit == "%":
        return value / 100 * reference
    return value * UNIT_SCALES[unit]


def _parse_absolute_length(text: Optional[str]) -> Optional[float]:
    if text is None or text.strip().endswith("%"):
        return None
    value = _parse_length(text, default=None)
    return value if value is not None and value > 0 else None


def _parse_view_box(text: Optional[str]) -> Optional[ViewBox]:
    if not text:
        return None
    values = [float(value) for value in NUMBER_PATTERN.findall(text)]
    if len(values) != 4 or values[2] <= 0 or values[3] <= 0:
        return None
    return (values[0], values[1], values[2], values[3])


def _parse_numbers(text: Optional[str]) -> List[float]:
    return [float(value) for value in NUMBER_PATTERN.findall(text or "")]


def _parse_opacity(text: str) -> float:
    value = _parse_length(text.strip(), reference=1.0, default=1.0)
    return max(0.0, min(1.0, value if value is not None else 1.0))


def _declarations(element: ElementTree.Element) -> Dict[str, str]:
    declared: Dict[str, str] = {}
    for name in STYLE_PROPERTIES:
        value = element.get(name)
        if value is not None:
            declared[name] = value.strip()
    for declaration in (element.get("style") or "").split(";"):
        name, separator, value = declaration.partition(":")
        name = name.strip().lower()
        if separator and name in STYLE_PROPERTIES:
            declared[name] = value.replace("!important", "").strip()
    return {name: value for name, value in declared.items() if value and value != "inherit"}


def _resolve_paint(value: str, current_color: RGBA) -> Optional[RGBA]:
    text = value.strip()
    if text.lower().startswith("url("):
        closing = text.find(")")
        fallback = text[closing + 1 :].strip() if closing >= 0 else ""
        if not fallback:
            return None
        text = fallback
    try:
        return parse_color(text, current_color=current_color)
    except ColorError:
        return None


def _parse_miterlimit(value: str) -> Optional[float]:
    try:
        limit = float(value.strip())
    except ValueError:
        return None
    return limit if limit >= 1 and math.isfinite(limit) else None


def _is_valid_property(name: str, value: str) -> bool:
    if name in ("fill", "stroke", "color"):
        return _is_valid_paint(value)
    if name == "stroke-linecap":
        return value.strip().lower() in LINECAPS
    if name == "stroke-linejoin":
        return value.strip().lower() in LINEJOINS
    if name == "stroke-miterlimit":
        return _parse_miterlimit(value) is not None
    return True


def _is_valid_paint(value: str) -> bool:
    text = value.strip()
    if text.lower().startswith("url("):
        return True
    try:
        parse_color(text)
    except ColorError:
        return False
    return True


def _index_ids(root: ElementTree.Element) -> Dict[str, ElementTree.Element]:
    index: Dict[str, ElementTree.Element] = {}
    for element in root.iter():
        identifier = element.get("id")
        if identifier and identifier not in index:
            index[identifier] = element
    return index


class _Renderer:
    def __init__(self, canvas: Canvas, view_box: ViewBox, ids: Optional[Dict[str, ElementTree.Element]] = None) -> None:
        self.canvas = canvas
        self.view_width = view_box[2]
        self.view_height = view_box[3]
        self.view_diagonal = math.sqrt((view_box[2] ** 2 + view_box[3] ** 2) / 2)
        self.ids = ids or {}
        self.references: List[ElementTree.Element] = []
        self.expanded = 0

    def render(self, element: ElementTree.Element, inherited: Dict[str, str], matrix: Matrix, opacity: float) -> None:
        if self.references:
            self.count_expansion()
        tag = _is_svg_element(element)
        if tag is None or (tag not in CONTAINER_TAGS and tag not in SHAPE_TAGS and tag != "use"):
            return
        cascaded = self.cascade(tag, element, inherited, matrix, opacity)
        if cascaded is None:
            return
        style, matrix, opacity = cascaded
        if tag in CONTAINER_TAGS:
            for child in element:
                self.render(child, style, matrix, opacity)
            return
        if tag == "use":
            self.render_use(element, style, matrix, opacity)
            return
        if style["visibility"].lower() in ("hidden", "collapse"):
            return
        self.draw_shape(tag, element, style, matrix, opacity)

    def cascade(
        self, tag: str, element: ElementTree.Element, inherited: Dict[str, str], matrix: Matrix, opacity: float
    ) -> Optional[Tuple[Dict[str, str], Matrix, float]]:
        declared = _declarations(element)
        if declared.get("display", "").lower() == "none":
            return None
        style = dict(inherited)
        for name in INHERITED_PROPERTIES:
            if name not in declared:
                continue
            value = declared[name]
            if not _is_valid_property(name, value):
                continue
            style[name] = value
        opacity *= _parse_opacity(declared.get("opacity", "1"))
        transform_text = element.get("transform")
        if transform_text:
            try:
                matrix = matrix.multiply(parse_transform(transform_text))
            except TransformError as error:
                raise SVGError(f"invalid transform on <{tag}>: {error}") from error
        if opacity <= 0:
            return None
        return style, matrix, opacity

    def count_expansion(self) -> None:
        self.expanded += 1
        if self.expanded > MAX_USE_EXPANSION:
            raise UnsafeSVGError(f"<use> expansion exceeds {MAX_USE_EXPANSION} elements")

    def render_use(self, element: ElementTree.Element, style: Dict[str, str], matrix: Matrix, opacity: float) -> None:
        reference = (element.get("href") or element.get(XLINK_HREF) or "").strip()
        if not reference.startswith("#"):
            return
        target = self.ids.get(reference[1:])
        if target is None:
            return
        if any(active is target for active in self.references):
            raise SVGError(f"circular <use> reference to {reference!r}")
        if len(self.references) >= MAX_USE_DEPTH:
            raise UnsafeSVGError(f"<use> nesting depth exceeds {MAX_USE_DEPTH}")
        width, height = self.view_width, self.view_height
        matrix = matrix.multiply(Matrix.translation(self.length(element, "x", width), self.length(element, "y", height)))
        self.references.append(target)
        try:
            if _is_svg_element(target) == "symbol":
                self.render_symbol(target, element, style, matrix, opacity)
            else:
                self.render(target, style, matrix, opacity)
        finally:
            self.references.pop()

    def render_symbol(
        self, symbol: ElementTree.Element, use: ElementTree.Element, inherited: Dict[str, str], matrix: Matrix, opacity: float
    ) -> None:
        self.count_expansion()
        cascaded = self.cascade("symbol", symbol, inherited, matrix, opacity)
        if cascaded is None:
            return
        style, matrix, opacity = cascaded
        view_box = _parse_view_box(symbol.get("viewBox"))
        if view_box is not None:
            width = self.symbol_extent(use, symbol, "width", self.view_width)
            height = self.symbol_extent(use, symbol, "height", self.view_height)
            if width <= 0 or height <= 0:
                return
            fit = min(width / view_box[2], height / view_box[3])
            offset_x = (width - view_box[2] * fit) / 2 - view_box[0] * fit
            offset_y = (height - view_box[3] * fit) / 2 - view_box[1] * fit
            matrix = matrix.multiply(Matrix(fit, 0.0, 0.0, fit, offset_x, offset_y))
        for child in symbol:
            self.render(child, style, matrix, opacity)

    def symbol_extent(self, use: ElementTree.Element, symbol: ElementTree.Element, name: str, reference: float) -> float:
        for source in (use, symbol):
            text = source.get(name)
            if text is not None and text.strip().lower() != "auto":
                value = _parse_length(text, reference, None)
                if value is not None:
                    return value
        return reference

    def length(self, element: ElementTree.Element, name: str, reference: float, default: float = 0.0) -> float:
        value = _parse_length(element.get(name), reference, default)
        return default if value is None else value

    def shape_geometry(self, tag: str, element: ElementTree.Element) -> Tuple[List[Command], List[Command]]:
        width, height, diagonal = self.view_width, self.view_height, self.view_diagonal
        if tag == "path":
            try:
                commands = parse_path(element.get("d") or "")
            except PathError as error:
                raise SVGError(f"invalid path data: {error}") from error
            return commands, commands
        if tag == "rect":
            rx_text, ry_text = element.get("rx"), element.get("ry")
            commands = rect_commands(
                self.length(element, "x", width),
                self.length(element, "y", height),
                self.length(element, "width", width),
                self.length(element, "height", height),
                _parse_length(rx_text, width) or 0.0 if rx_text is not None else 0.0,
                _parse_length(ry_text, height) if ry_text is not None else None,
            )
            return commands, commands
        if tag == "circle":
            radius = self.length(element, "r", diagonal)
            commands = ellipse_commands(self.length(element, "cx", width), self.length(element, "cy", height), radius, radius)
            return commands, commands
        if tag == "ellipse":
            rx = _parse_length(element.get("rx"), width, None)
            ry = _parse_length(element.get("ry"), height, None)
            rx = ry if rx is None else rx
            ry = rx if ry is None else ry
            commands = ellipse_commands(self.length(element, "cx", width), self.length(element, "cy", height), rx or 0.0, ry or 0.0)
            return commands, commands
        if tag == "line":
            start = (self.length(element, "x1", width), self.length(element, "y1", height))
            end = (self.length(element, "x2", width), self.length(element, "y2", height))
            return [], polygon_commands([start, end], closed=False)
        values = _parse_numbers(element.get("points"))
        points = list(zip(values[0::2], values[1::2]))
        closed = tag == "polygon"
        return polygon_commands(points, closed=True), polygon_commands(points, closed=closed)

    def draw_shape(self, tag: str, element: ElementTree.Element, style: Dict[str, str], matrix: Matrix, opacity: float) -> None:
        fill_commands, stroke_commands = self.shape_geometry(tag, element)
        current_color = _resolve_paint(style["color"], (0, 0, 0, 1.0)) or (0, 0, 0, 1.0)
        fill = _resolve_paint(style["fill"], current_color)
        if fill is not None and fill_commands:
            fill_rule = "evenodd" if style["fill-rule"].strip().lower() == "evenodd" else "nonzero"
            self.canvas.fill_path(fill_commands, fill, opacity * _parse_opacity(style["fill-opacity"]), fill_rule, matrix)
        stroke = _resolve_paint(style["stroke"], current_color)
        stroke_width = _parse_length(style["stroke-width"], self.view_diagonal, 1.0) or 0.0
        if stroke is not None and stroke_commands and stroke_width > 0:
            self.canvas.stroke_path(
                stroke_commands,
                stroke,
                stroke_width,
                opacity * _parse_opacity(style["stroke-opacity"]),
                matrix,
                linecap=style["stroke-linecap"].strip().lower(),
                linejoin=style["stroke-linejoin"].strip().lower(),
                miterlimit=_parse_miterlimit(style["stroke-miterlimit"]) or DEFAULT_MITERLIMIT,
            )


def _output_size(
    intrinsic_width: float, intrinsic_height: float, width: Optional[float], height: Optional[float], scale: Optional[float]
) -> Tuple[int, int]:
    if scale is not None and (width is not None or height is not None):
        raise ValueError("pass either scale or width/height, not both")
    if scale is not None:
        if scale <= 0:
            raise ValueError("scale must be positive")
        output_width, output_height = intrinsic_width * scale, intrinsic_height * scale
    elif width is not None and height is not None:
        output_width, output_height = width, height
    elif width is not None:
        output_width, output_height = width, width * intrinsic_height / intrinsic_width
    elif height is not None:
        output_width, output_height = height * intrinsic_width / intrinsic_height, height
    else:
        output_width, output_height = intrinsic_width, intrinsic_height
    if output_width <= 0 or output_height <= 0:
        raise ValueError("output width and height must be positive")
    return max(1, int(round(output_width))), max(1, int(round(output_height)))


def render_svg(
    source: SourceInput,
    width: Optional[float] = None,
    height: Optional[float] = None,
    scale: Optional[float] = None,
    background: ColorInput = None,
) -> Canvas:
    root = _parse_document(_read_source(source))
    if _is_svg_element(root) != "svg":
        raise SVGError(f"root element must be <svg>, found <{_split_tag(root.tag)[1]}>")
    view_box = _parse_view_box(root.get("viewBox"))
    declared_width = _parse_absolute_length(root.get("width"))
    declared_height = _parse_absolute_length(root.get("height"))
    if view_box is not None:
        aspect = view_box[3] / view_box[2]
        if declared_width is None and declared_height is None:
            declared_width, declared_height = view_box[2], view_box[3]
        elif declared_width is None:
            declared_width = declared_height / aspect
        elif declared_height is None:
            declared_height = declared_width * aspect
    intrinsic_width = declared_width or DEFAULT_WIDTH
    intrinsic_height = declared_height or DEFAULT_HEIGHT
    if view_box is None:
        view_box = (0.0, 0.0, intrinsic_width, intrinsic_height)
    output_width, output_height = _output_size(intrinsic_width, intrinsic_height, width, height, scale)
    canvas = Canvas(output_width, output_height, background=background)
    fit = min(output_width / view_box[2], output_height / view_box[3])
    offset_x = (output_width - view_box[2] * fit) / 2 - view_box[0] * fit
    offset_y = (output_height - view_box[3] * fit) / 2 - view_box[1] * fit
    viewport = Matrix(fit, 0.0, 0.0, fit, offset_x, offset_y)
    _Renderer(canvas, view_box, _index_ids(root)).render(root, dict(INITIAL_STYLE), viewport, 1.0)
    return canvas

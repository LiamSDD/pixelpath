import math
import os
from typing import Iterable, List, Optional, Sequence, Tuple, Union

from .color import RGBA, ColorInput, parse_color
from .flatten import DEFAULT_TOLERANCE, Subpath, flatten_path
from .path import Command, ellipse_commands, parse_path, polygon_commands, rect_commands
from .png import encode_png
from .raster import FILL_RULES, CoverageMask, rasterize
from .transform import Matrix, parse_transform

Point = Tuple[float, float]
PathInput = Union[str, Sequence[Command]]
TransformInput = Union[str, Matrix, None]
STROKE_JOIN_TOLERANCE = 0.05


def _signed_area(polygon: Sequence[Point]) -> float:
    area = 0.0
    previous_x, previous_y = polygon[-1]
    for x, y in polygon:
        area += previous_x * y - x * previous_y
        previous_x, previous_y = x, y
    return area / 2


def _positively_oriented(polygon: List[Point]) -> List[Point]:
    return polygon if _signed_area(polygon) >= 0 else polygon[::-1]


def _circle_polygon(cx: float, cy: float, radius: float) -> List[Point]:
    if radius <= STROKE_JOIN_TOLERANCE:
        count = 8
    else:
        count = math.ceil(math.pi / math.acos(1 - STROKE_JOIN_TOLERANCE / radius))
        count = max(8, min(256, count))
    step = 2 * math.pi / count
    return [(cx + radius * math.cos(index * step), cy + radius * math.sin(index * step)) for index in range(count)]


def _stroke_polygons(subpaths: Iterable[Subpath], half_width: float) -> List[List[Point]]:
    polygons: List[List[Point]] = []
    for subpath in subpaths:
        if len(subpath.points) == 1 and not subpath.closed:
            continue
        points: List[Point] = []
        for point in subpath.points:
            if not points or point != points[-1]:
                points.append(point)
        if subpath.closed and len(points) > 1 and points[0] == points[-1]:
            points.pop()
        if len(points) == 1:
            polygons.append(_circle_polygon(points[0][0], points[0][1], half_width))
            continue
        segment_ends = list(zip(points, points[1:]))
        if subpath.closed and len(points) > 2:
            segment_ends.append((points[-1], points[0]))
        normals = []
        for (start_x, start_y), (end_x, end_y) in segment_ends:
            length = math.hypot(end_x - start_x, end_y - start_y)
            normal_x = -(end_y - start_y) / length * half_width
            normal_y = (end_x - start_x) / length * half_width
            normals.append((normal_x, normal_y))
            polygons.append([
                (start_x - normal_x, start_y - normal_y),
                (end_x - normal_x, end_y - normal_y),
                (end_x + normal_x, end_y + normal_y),
                (start_x + normal_x, start_y + normal_y),
            ])
        joins = [(segment_ends[index][1], normals[index], normals[index + 1]) for index in range(len(segment_ends) - 1)]
        if subpath.closed and len(segment_ends) > 2:
            joins.append((segment_ends[-1][1], normals[-1], normals[0]))
        for (vertex_x, vertex_y), (first_x, first_y), (second_x, second_y) in joins:
            cosine = max(-1.0, min(1.0, (first_x * second_x + first_y * second_y) / (half_width * half_width)))
            sagitta = half_width * (1 - math.sqrt((1 + cosine) / 2))
            if sagitta > STROKE_JOIN_TOLERANCE:
                polygons.append(_circle_polygon(vertex_x, vertex_y, half_width))
                continue
            for sign in (1.0, -1.0):
                wedge = [
                    (vertex_x, vertex_y),
                    (vertex_x + sign * first_x, vertex_y + sign * first_y),
                    (vertex_x + sign * second_x, vertex_y + sign * second_y),
                ]
                if abs(_signed_area(wedge)) > 1e-12:
                    polygons.append(_positively_oriented(wedge))
        if not subpath.closed or len(points) == 2:
            polygons.append(_circle_polygon(points[0][0], points[0][1], half_width))
            polygons.append(_circle_polygon(points[-1][0], points[-1][1], half_width))
    return polygons


class Canvas:
    def __init__(self, width: int, height: int, background: ColorInput = None) -> None:
        if int(width) != width or int(height) != height or width <= 0 or height <= 0:
            raise ValueError(f"canvas dimensions must be positive integers, got {width}x{height}")
        self.width = int(width)
        self.height = int(height)
        self._data: List[float] = [0.0] * (self.width * self.height * 4)
        background_color = parse_color(background)
        if background_color is not None and background_color[3] > 0:
            red, green, blue, alpha = background_color
            self._data = [float(red), float(green), float(blue), float(alpha)] * (self.width * self.height)

    def get_pixel(self, x: int, y: int) -> Tuple[int, int, int, int]:
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError(f"pixel ({x}, {y}) is outside the {self.width}x{self.height} canvas")
        offset = (y * self.width + x) * 4
        red, green, blue, alpha = self._data[offset : offset + 4]
        alpha_byte = int(alpha * 255 + 0.5)
        if alpha_byte == 0:
            return (0, 0, 0, 0)
        return (int(red + 0.5), int(green + 0.5), int(blue + 0.5), alpha_byte)

    def fill_path(
        self,
        d: PathInput,
        color: ColorInput = "black",
        opacity: float = 1.0,
        fill_rule: str = "nonzero",
        transform: TransformInput = None,
    ) -> None:
        if fill_rule not in FILL_RULES:
            raise ValueError(f"fill_rule must be 'nonzero' or 'evenodd', got {fill_rule!r}")
        paint = self._resolve_paint(color, opacity)
        if paint is None:
            return
        subpaths = flatten_path(self._commands(d), self._matrix(transform), DEFAULT_TOLERANCE)
        polygons = [subpath.points for subpath in subpaths if len(subpath.points) >= 3]
        if polygons:
            self._composite(rasterize(polygons, self.width, self.height, fill_rule), paint)

    def fill_rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        color: ColorInput = "black",
        rx: float = 0.0,
        ry: Optional[float] = None,
        opacity: float = 1.0,
        transform: TransformInput = None,
    ) -> None:
        self.fill_path(rect_commands(x, y, width, height, rx, ry), color, opacity, "nonzero", transform)

    def fill_circle(self, cx: float, cy: float, r: float, color: ColorInput = "black", opacity: float = 1.0, transform: TransformInput = None) -> None:
        self.fill_path(ellipse_commands(cx, cy, r, r), color, opacity, "nonzero", transform)

    def fill_ellipse(
        self, cx: float, cy: float, rx: float, ry: float, color: ColorInput = "black", opacity: float = 1.0, transform: TransformInput = None
    ) -> None:
        self.fill_path(ellipse_commands(cx, cy, rx, ry), color, opacity, "nonzero", transform)

    def fill_polygon(
        self,
        points: Iterable[Sequence[float]],
        color: ColorInput = "black",
        opacity: float = 1.0,
        fill_rule: str = "nonzero",
        transform: TransformInput = None,
    ) -> None:
        self.fill_path(polygon_commands(points), color, opacity, fill_rule, transform)

    def stroke_path(
        self,
        d: PathInput,
        color: ColorInput = "black",
        width: float = 1.0,
        opacity: float = 1.0,
        transform: TransformInput = None,
    ) -> None:
        paint = self._resolve_paint(color, opacity)
        matrix = self._matrix(transform)
        half_width = float(width) * matrix.scale_factor() / 2
        if paint is None or half_width <= 0:
            return
        subpaths = flatten_path(self._commands(d), matrix, DEFAULT_TOLERANCE)
        polygons = _stroke_polygons(subpaths, half_width)
        if polygons:
            self._composite(rasterize(polygons, self.width, self.height, "nonzero"), paint)

    def to_rgba_bytes(self) -> bytes:
        data = self._data
        output = bytearray(len(data))
        alpha_bytes = bytes(int(alpha * 255 + 0.5) for alpha in data[3::4])
        output[0::4] = bytes(int(value + 0.5) for value in data[0::4])
        output[1::4] = bytes(int(value + 0.5) for value in data[1::4])
        output[2::4] = bytes(int(value + 0.5) for value in data[2::4])
        output[3::4] = alpha_bytes
        if 0 in alpha_bytes:
            for index, alpha in enumerate(alpha_bytes):
                if alpha == 0:
                    output[index * 4 : index * 4 + 3] = b"\x00\x00\x00"
        return bytes(output)

    def to_png_bytes(self) -> bytes:
        return encode_png(self.width, self.height, self.to_rgba_bytes())

    def save(self, path: Union[str, "os.PathLike[str]"]) -> None:
        with open(path, "wb") as handle:
            handle.write(self.to_png_bytes())

    @staticmethod
    def _commands(d: PathInput) -> Sequence[Command]:
        return parse_path(d) if isinstance(d, str) else d

    @staticmethod
    def _matrix(transform: TransformInput) -> Matrix:
        return parse_transform(transform) if transform is not None else Matrix.identity()

    @staticmethod
    def _resolve_paint(color: ColorInput, opacity: float) -> Optional[RGBA]:
        resolved = parse_color(color)
        if resolved is None:
            return None
        alpha = resolved[3] * max(0.0, min(1.0, float(opacity)))
        if alpha <= 0:
            return None
        return (resolved[0], resolved[1], resolved[2], alpha)

    def _composite(self, mask: CoverageMask, paint: RGBA) -> None:
        if mask.is_empty():
            return
        source_red, source_green, source_blue, source_alpha = paint
        source_red, source_green, source_blue = float(source_red), float(source_green), float(source_blue)
        data = self._data
        canvas_width = self.width
        for y, x0, row in mask.rows():
            offset = (y * canvas_width + x0) * 4
            for coverage in row:
                if coverage > 0.0:
                    alpha = source_alpha * coverage
                    destination_alpha = data[offset + 3]
                    if alpha >= 0.999999 or destination_alpha <= 0.0:
                        data[offset] = source_red
                        data[offset + 1] = source_green
                        data[offset + 2] = source_blue
                        data[offset + 3] = alpha if alpha < 0.999999 else 1.0
                    else:
                        remaining = destination_alpha * (1.0 - alpha)
                        output_alpha = alpha + remaining
                        data[offset] = (source_red * alpha + data[offset] * remaining) / output_alpha
                        data[offset + 1] = (source_green * alpha + data[offset + 1] * remaining) / output_alpha
                        data[offset + 2] = (source_blue * alpha + data[offset + 2] * remaining) / output_alpha
                        data[offset + 3] = output_alpha
                offset += 4

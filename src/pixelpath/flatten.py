import math
from typing import List, NamedTuple, Optional, Sequence, Tuple

from .path import Command
from .transform import Matrix

Point = Tuple[float, float]
CubicSegment = Tuple[Point, Point, Point]
DEFAULT_TOLERANCE = 0.05
MAX_SEGMENTS = 4096


class Subpath(NamedTuple):
    points: List[Point]
    closed: bool


def flatten_cubic(p0: Sequence[float], p1: Sequence[float], p2: Sequence[float], p3: Sequence[float], tolerance: float = DEFAULT_TOLERANCE) -> List[Point]:
    x0, y0 = p0
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    first_x, first_y = x0 - 2 * x1 + x2, y0 - 2 * y1 + y2
    second_x, second_y = x1 - 2 * x2 + x3, y1 - 2 * y2 + y3
    deviation = math.sqrt(max(first_x * first_x + first_y * first_y, second_x * second_x + second_y * second_y))
    count = min(MAX_SEGMENTS, max(1, math.ceil(math.sqrt(0.75 * deviation / tolerance))))
    points: List[Point] = []
    for step in range(1, count):
        t = step / count
        u = 1.0 - t
        weight0 = u * u * u
        weight1 = 3.0 * u * u * t
        weight2 = 3.0 * u * t * t
        weight3 = t * t * t
        points.append((
            weight0 * x0 + weight1 * x1 + weight2 * x2 + weight3 * x3,
            weight0 * y0 + weight1 * y1 + weight2 * y2 + weight3 * y3,
        ))
    points.append((x3, y3))
    return points


def flatten_quadratic(p0: Sequence[float], p1: Sequence[float], p2: Sequence[float], tolerance: float = DEFAULT_TOLERANCE) -> List[Point]:
    x0, y0 = p0
    x1, y1 = p1
    x2, y2 = p2
    deviation = math.hypot(x0 - 2 * x1 + x2, y0 - 2 * y1 + y2)
    count = min(MAX_SEGMENTS, max(1, math.ceil(math.sqrt(deviation / (4.0 * tolerance)))))
    points: List[Point] = []
    for step in range(1, count):
        t = step / count
        u = 1.0 - t
        points.append((u * u * x0 + 2 * u * t * x1 + t * t * x2, u * u * y0 + 2 * u * t * y1 + t * t * y2))
    points.append((x2, y2))
    return points


def arc_endpoint_to_center(
    x1: float, y1: float, rx: float, ry: float, phi_degrees: float, large_arc: float, sweep: float, x2: float, y2: float
) -> Optional[Tuple[float, float, float, float, float, float]]:
    rx, ry = abs(rx), abs(ry)
    if rx == 0 or ry == 0 or (x1 == x2 and y1 == y2):
        return None
    phi = math.radians(phi_degrees % 360)
    cos_phi, sin_phi = math.cos(phi), math.sin(phi)
    half_dx, half_dy = (x1 - x2) / 2, (y1 - y2) / 2
    x1_prime = cos_phi * half_dx + sin_phi * half_dy
    y1_prime = -sin_phi * half_dx + cos_phi * half_dy
    radii_check = (x1_prime * x1_prime) / (rx * rx) + (y1_prime * y1_prime) / (ry * ry)
    if radii_check > 1:
        root = math.sqrt(radii_check)
        rx *= root
        ry *= root
    rx_squared, ry_squared = rx * rx, ry * ry
    numerator = rx_squared * ry_squared - rx_squared * y1_prime * y1_prime - ry_squared * x1_prime * x1_prime
    denominator = rx_squared * y1_prime * y1_prime + ry_squared * x1_prime * x1_prime
    coefficient = math.sqrt(max(0.0, numerator / denominator))
    if bool(large_arc) == bool(sweep):
        coefficient = -coefficient
    cx_prime = coefficient * rx * y1_prime / ry
    cy_prime = -coefficient * ry * x1_prime / rx
    cx = cos_phi * cx_prime - sin_phi * cy_prime + (x1 + x2) / 2
    cy = sin_phi * cx_prime + cos_phi * cy_prime + (y1 + y2) / 2
    ux, uy = (x1_prime - cx_prime) / rx, (y1_prime - cy_prime) / ry
    vx, vy = (-x1_prime - cx_prime) / rx, (-y1_prime - cy_prime) / ry
    theta1 = math.atan2(uy, ux)
    delta = math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
    if not sweep and delta > 0:
        delta -= 2 * math.pi
    elif sweep and delta < 0:
        delta += 2 * math.pi
    return (cx, cy, rx, ry, theta1, delta)


def arc_to_cubics(
    x1: float, y1: float, rx: float, ry: float, phi_degrees: float, large_arc: float, sweep: float, x2: float, y2: float
) -> List[CubicSegment]:
    x1, y1, x2, y2 = float(x1), float(y1), float(x2), float(y2)
    if x1 == x2 and y1 == y2:
        return []
    center = arc_endpoint_to_center(x1, y1, rx, ry, phi_degrees, large_arc, sweep, x2, y2)
    if center is None:
        return [((x1, y1), (x2, y2), (x2, y2))]
    cx, cy, rx, ry, theta, delta = center
    phi = math.radians(phi_degrees % 360)
    cos_phi, sin_phi = math.cos(phi), math.sin(phi)
    count = max(1, math.ceil(abs(delta) / (math.pi / 2) - 1e-9))
    step = delta / count
    handle = 4.0 / 3.0 * math.tan(step / 4)

    def to_user(unit_x: float, unit_y: float) -> Point:
        ex, ey = rx * unit_x, ry * unit_y
        return (cx + cos_phi * ex - sin_phi * ey, cy + sin_phi * ex + cos_phi * ey)

    segments: List[CubicSegment] = []
    for index in range(count):
        start_angle = theta + index * step
        end_angle = start_angle + step
        cos_start, sin_start = math.cos(start_angle), math.sin(start_angle)
        cos_end, sin_end = math.cos(end_angle), math.sin(end_angle)
        control1 = to_user(cos_start - handle * sin_start, sin_start + handle * cos_start)
        control2 = to_user(cos_end + handle * sin_end, sin_end - handle * cos_end)
        end = (x2, y2) if index == count - 1 else to_user(cos_end, sin_end)
        segments.append((control1, control2, end))
    return segments


def flatten_path(commands: Sequence[Command], transform: Optional[Matrix] = None, tolerance: float = DEFAULT_TOLERANCE) -> List[Subpath]:
    matrix = transform if transform is not None and not transform.is_identity() else None

    def device(x: float, y: float) -> Point:
        return matrix.apply(x, y) if matrix is not None else (x, y)

    subpaths: List[Subpath] = []
    points: Optional[List[Point]] = None
    current_x = current_y = 0.0
    start_x = start_y = 0.0

    def ensure_open() -> List[Point]:
        nonlocal points
        if points is None:
            points = [device(start_x, start_y)]
        return points

    for name, arguments in commands:
        if name == "M":
            if points is not None:
                subpaths.append(Subpath(points, False))
            current_x, current_y = start_x, start_y = arguments
            points = [device(current_x, current_y)]
        elif name == "Z":
            subpaths.append(Subpath(ensure_open(), True))
            points = None
            current_x, current_y = start_x, start_y
        elif name == "L":
            ensure_open().append(device(arguments[0], arguments[1]))
            current_x, current_y = arguments
        elif name == "C":
            target = ensure_open()
            target.extend(flatten_cubic(
                target[-1], device(arguments[0], arguments[1]), device(arguments[2], arguments[3]), device(arguments[4], arguments[5]), tolerance
            ))
            current_x, current_y = arguments[4], arguments[5]
        elif name == "Q":
            target = ensure_open()
            target.extend(flatten_quadratic(target[-1], device(arguments[0], arguments[1]), device(arguments[2], arguments[3]), tolerance))
            current_x, current_y = arguments[2], arguments[3]
        elif name == "A":
            target = ensure_open()
            rx, ry, rotation, large_arc, sweep, end_x, end_y = arguments
            if arc_endpoint_to_center(current_x, current_y, rx, ry, rotation, large_arc, sweep, end_x, end_y) is None:
                if (end_x, end_y) != (current_x, current_y):
                    target.append(device(end_x, end_y))
            else:
                for control1, control2, end in arc_to_cubics(current_x, current_y, rx, ry, rotation, large_arc, sweep, end_x, end_y):
                    target.extend(flatten_cubic(target[-1], device(*control1), device(*control2), device(*end), tolerance))
            current_x, current_y = end_x, end_y
        else:
            raise ValueError(f"unknown normalised path command {name!r}")
    if points is not None:
        subpaths.append(Subpath(points, False))
    return subpaths

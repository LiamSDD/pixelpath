import math
from itertools import accumulate
from typing import Iterator, List, Sequence, Tuple

Point = Tuple[float, float]
FILL_RULES = ("nonzero", "evenodd")
DEFAULT_SAMPLES = 16


class CoverageMask:
    def __init__(self, x0: int, y0: int, width: int, height: int, values: List[float]) -> None:
        self.x0 = x0
        self.y0 = y0
        self.width = width
        self.height = height
        self.values = values

    def get(self, x: int, y: int) -> float:
        column, row = x - self.x0, y - self.y0
        if 0 <= column < self.width and 0 <= row < self.height:
            return self.values[row * self.width + column]
        return 0.0

    def total(self) -> float:
        return math.fsum(self.values)

    def rows(self) -> Iterator[Tuple[int, int, List[float]]]:
        for row in range(self.height):
            start = row * self.width
            yield self.y0 + row, self.x0, self.values[start : start + self.width]

    def is_empty(self) -> bool:
        return self.width == 0 or self.height == 0


def _empty_mask() -> CoverageMask:
    return CoverageMask(0, 0, 0, 0, [])


def rasterize(
    polygons: Sequence[Sequence[Point]],
    width: int,
    height: int,
    fill_rule: str = "nonzero",
    samples: int = DEFAULT_SAMPLES,
) -> CoverageMask:
    if fill_rule not in FILL_RULES:
        raise ValueError(f"fill_rule must be 'nonzero' or 'evenodd', got {fill_rule!r}")
    if samples < 1:
        raise ValueError("samples must be at least 1")
    minimum_x = minimum_y = math.inf
    maximum_x = maximum_y = -math.inf
    for polygon in polygons:
        if len(polygon) < 3:
            continue
        for x, y in polygon:
            if x < minimum_x:
                minimum_x = x
            if x > maximum_x:
                maximum_x = x
            if y < minimum_y:
                minimum_y = y
            if y > maximum_y:
                maximum_y = y
    if minimum_x == math.inf:
        return _empty_mask()
    left = max(0, int(math.floor(minimum_x)))
    right = min(width, int(math.ceil(maximum_x)))
    top = max(0, int(math.floor(minimum_y)))
    bottom = min(height, int(math.ceil(maximum_y)))
    if left >= right or top >= bottom:
        return _empty_mask()
    mask_width = right - left

    edges = []
    for polygon in polygons:
        count = len(polygon)
        if count < 3:
            continue
        previous_x, previous_y = polygon[-1]
        for x, y in polygon:
            if y != previous_y:
                if y > previous_y:
                    edges.append((previous_y, y, previous_x - left, (x - previous_x) / (y - previous_y), 1))
                else:
                    edges.append((y, previous_y, x - left, (previous_x - x) / (previous_y - y), -1))
            previous_x, previous_y = x, y
    edges.sort(key=lambda edge: edge[0])

    evenodd = fill_rule == "evenodd"
    weight = 1.0 / samples
    sample_offsets = [(index + 0.5) / samples for index in range(samples)]
    edge_count = len(edges)
    next_edge = 0
    active: list = []
    values: List[float] = []
    zero_row = [0.0] * mask_width
    upper_bound = float(mask_width)

    for row in range(top, bottom):
        cover = None
        delta = None
        for offset in sample_offsets:
            sample_y = row + offset
            while next_edge < edge_count and edges[next_edge][0] <= sample_y:
                active.append(edges[next_edge])
                next_edge += 1
            if not active:
                continue
            active = [edge for edge in active if edge[1] > sample_y]
            if len(active) < 2:
                continue
            crossings = sorted([(edge[2] + (sample_y - edge[0]) * edge[3], edge[4]) for edge in active])
            if cover is None:
                cover = [0.0] * (mask_width + 2)
                delta = [0.0] * (mask_width + 2)
            winding = 0
            span_start = 0.0
            for x, direction in crossings:
                was_inside = (winding & 1) if evenodd else winding
                winding += direction
                now_inside = (winding & 1) if evenodd else winding
                if now_inside and not was_inside:
                    span_start = x
                elif was_inside and not now_inside:
                    start = 0.0 if span_start < 0.0 else (upper_bound if span_start > upper_bound else span_start)
                    end = 0.0 if x < 0.0 else (upper_bound if x > upper_bound else x)
                    if end <= start:
                        continue
                    start_index = int(start)
                    end_index = int(end)
                    if start_index == end_index:
                        cover[start_index] += (end - start) * weight
                    else:
                        cover[start_index] += (start_index + 1 - start) * weight
                        delta[start_index + 1] += weight
                        delta[end_index] -= weight
                        cover[end_index] += (end - end_index) * weight
        if cover is None:
            values.extend(zero_row)
        else:
            row_values = [partial + full for partial, full in zip(cover, accumulate(delta))]
            del row_values[mask_width:]
            values.extend([1.0 if value > 1.0 else (0.0 if value < 1e-9 else value) for value in row_values])
    return CoverageMask(left, top, mask_width, bottom - top, values)

import math
import re
from typing import List, NamedTuple, Optional, Tuple, Union

NUMBER_PATTERN = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
FUNCTION_PATTERN = re.compile(r"\s*,?\s*([A-Za-z]+)\s*\(([^()]*)\)\s*")
NUMBER_LIST_PATTERN = re.compile(r"^[\s,]*(?:[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?[\s,]*)*$")
ARGUMENT_COUNTS = {
    "matrix": (6,),
    "translate": (1, 2),
    "scale": (1, 2),
    "rotate": (1, 3),
    "skewX": (1,),
    "skewY": (1,),
}


class TransformError(ValueError):
    pass


class Matrix(NamedTuple):
    a: float = 1.0
    b: float = 0.0
    c: float = 0.0
    d: float = 1.0
    e: float = 0.0
    f: float = 0.0

    @classmethod
    def identity(cls) -> "Matrix":
        return cls()

    @classmethod
    def translation(cls, tx: float, ty: float = 0.0) -> "Matrix":
        return cls(1.0, 0.0, 0.0, 1.0, float(tx), float(ty))

    @classmethod
    def scaling(cls, sx: float, sy: Optional[float] = None) -> "Matrix":
        return cls(float(sx), 0.0, 0.0, float(sx if sy is None else sy), 0.0, 0.0)

    @classmethod
    def rotation(cls, degrees: float, cx: float = 0.0, cy: float = 0.0) -> "Matrix":
        radians = math.radians(degrees)
        cosine, sine = math.cos(radians), math.sin(radians)
        rotate = cls(cosine, sine, -sine, cosine, 0.0, 0.0)
        if cx == 0 and cy == 0:
            return rotate
        return cls.translation(cx, cy).multiply(rotate).multiply(cls.translation(-cx, -cy))

    @classmethod
    def skew_x(cls, degrees: float) -> "Matrix":
        return cls(1.0, 0.0, math.tan(math.radians(degrees)), 1.0, 0.0, 0.0)

    @classmethod
    def skew_y(cls, degrees: float) -> "Matrix":
        return cls(1.0, math.tan(math.radians(degrees)), 0.0, 1.0, 0.0, 0.0)

    def multiply(self, other: "Matrix") -> "Matrix":
        a, b, c, d, e, f = self
        oa, ob, oc, od, oe, of = other
        return Matrix(
            a * oa + c * ob,
            b * oa + d * ob,
            a * oc + c * od,
            b * oc + d * od,
            a * oe + c * of + e,
            b * oe + d * of + f,
        )

    def apply(self, x: float, y: float) -> Tuple[float, float]:
        return (self.a * x + self.c * y + self.e, self.b * x + self.d * y + self.f)

    def scale_factor(self) -> float:
        return math.sqrt(abs(self.a * self.d - self.b * self.c))

    def is_identity(self) -> bool:
        return self == (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def _build(name: str, values: List[float]) -> Matrix:
    if name == "matrix":
        return Matrix(*values)
    if name == "translate":
        return Matrix.translation(values[0], values[1] if len(values) > 1 else 0.0)
    if name == "scale":
        return Matrix.scaling(values[0], values[1] if len(values) > 1 else None)
    if name == "rotate":
        return Matrix.rotation(*values)
    if name == "skewX":
        return Matrix.skew_x(values[0])
    return Matrix.skew_y(values[0])


def parse_transform(text: Union[str, Matrix, None]) -> Matrix:
    if isinstance(text, Matrix):
        return text
    result = Matrix.identity()
    if text is None:
        return result
    position = 0
    stripped = text.strip()
    while position < len(stripped):
        match = FUNCTION_PATTERN.match(stripped, position)
        if not match or match.end() == position:
            raise TransformError(f"invalid transform list {text!r}")
        name, arguments = match.group(1), match.group(2)
        if name not in ARGUMENT_COUNTS:
            raise TransformError(f"unknown transform function {name!r}")
        if not NUMBER_LIST_PATTERN.match(arguments):
            raise TransformError(f"invalid arguments for {name}: {arguments!r}")
        values = [float(value) for value in NUMBER_PATTERN.findall(arguments)]
        if len(values) not in ARGUMENT_COUNTS[name]:
            raise TransformError(f"{name} expects {' or '.join(map(str, ARGUMENT_COUNTS[name]))} arguments, got {len(values)}")
        result = result.multiply(_build(name, values))
        position = match.end()
    return result

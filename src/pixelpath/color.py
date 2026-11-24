import re
from typing import Optional, Sequence, Tuple, Union

RGBA = Tuple[int, int, int, float]
ColorInput = Union[str, Sequence[float], None]

NAMED_COLORS = {
    "black": (0, 0, 0),
    "silver": (192, 192, 192),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
    "white": (255, 255, 255),
    "maroon": (128, 0, 0),
    "red": (255, 0, 0),
    "purple": (128, 0, 128),
    "fuchsia": (255, 0, 255),
    "magenta": (255, 0, 255),
    "green": (0, 128, 0),
    "lime": (0, 255, 0),
    "olive": (128, 128, 0),
    "yellow": (255, 255, 0),
    "navy": (0, 0, 128),
    "blue": (0, 0, 255),
    "teal": (0, 128, 128),
    "aqua": (0, 255, 255),
    "cyan": (0, 255, 255),
}
BLACK: RGBA = (0, 0, 0, 1.0)
HEX_DIGITS = set("0123456789abcdef")
FUNCTION_PATTERN = re.compile(r"^(rgba?)\((.*)\)$")
COMPONENT_PATTERN = re.compile(r"^[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?%?$")


class ColorError(ValueError):
    pass


def _clamp_channel(value: float) -> int:
    return int(min(255.0, max(0.0, value)) + 0.5)


def _clamp_alpha(value: float) -> float:
    return min(1.0, max(0.0, float(value)))


def _parse_component(text: str, original: str) -> Tuple[float, bool]:
    if not COMPONENT_PATTERN.match(text):
        raise ColorError(f"invalid colour component {text!r} in {original!r}")
    if text.endswith("%"):
        return float(text[:-1]), True
    return float(text), False


def _parse_function(arguments: str, original: str) -> RGBA:
    alpha_text = None
    if "/" in arguments:
        arguments, alpha_text = arguments.split("/", 1)
    parts = [part for part in re.split(r"[\s,]+", arguments.strip()) if part]
    if alpha_text is None and len(parts) == 4:
        alpha_text = parts.pop()
    if len(parts) != 3:
        raise ColorError(f"rgb() needs three components: {original!r}")
    channels = []
    for part in parts:
        value, is_percentage = _parse_component(part, original)
        channels.append(_clamp_channel(value * 255 / 100 if is_percentage else value))
    alpha = 1.0
    if alpha_text is not None:
        value, is_percentage = _parse_component(alpha_text.strip(), original)
        alpha = _clamp_alpha(value / 100 if is_percentage else value)
    return (channels[0], channels[1], channels[2], alpha)


def _parse_hex(digits: str, original: str) -> RGBA:
    if not set(digits) <= HEX_DIGITS or len(digits) not in (3, 4, 6, 8):
        raise ColorError(f"invalid hex colour {original!r}")
    if len(digits) in (3, 4):
        digits = "".join(character * 2 for character in digits)
    red, green, blue = (int(digits[index : index + 2], 16) for index in (0, 2, 4))
    alpha = int(digits[6:8], 16) / 255 if len(digits) == 8 else 1.0
    return (red, green, blue, alpha)


def parse_color(value: ColorInput, current_color: Optional[RGBA] = None) -> Optional[RGBA]:
    if value is None:
        return None
    if not isinstance(value, str):
        components = tuple(value)
        if len(components) not in (3, 4):
            raise ColorError(f"colour tuples need 3 or 4 components, got {components!r}")
        alpha = _clamp_alpha(components[3]) if len(components) == 4 else 1.0
        return (_clamp_channel(components[0]), _clamp_channel(components[1]), _clamp_channel(components[2]), alpha)
    text = value.strip().lower()
    if text == "none":
        return None
    if text == "transparent":
        return (0, 0, 0, 0.0)
    if text == "currentcolor":
        return current_color if current_color is not None else BLACK
    if text.startswith("#"):
        return _parse_hex(text[1:], value)
    if text in NAMED_COLORS:
        return NAMED_COLORS[text] + (1.0,)
    match = FUNCTION_PATTERN.match(text)
    if match:
        return _parse_function(match.group(2), value)
    raise ColorError(f"unsupported colour {value!r}")

from typing import Iterable, List, Optional, Sequence, Tuple

Command = Tuple[str, Tuple[float, ...]]
Point = Tuple[float, float]

ARGUMENT_COUNTS = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}
WHITESPACE = " \t\n\r\f,"
DIGITS = "0123456789"


class PathError(ValueError):
    pass


class _Scanner:
    def __init__(self, text: str) -> None:
        self.text = text
        self.position = 0
        self.length = len(text)

    def skip_separators(self) -> None:
        while self.position < self.length and self.text[self.position] in WHITESPACE:
            self.position += 1

    def at_end(self) -> bool:
        self.skip_separators()
        return self.position >= self.length

    def peek(self) -> str:
        self.skip_separators()
        return self.text[self.position] if self.position < self.length else ""

    def next_starts_number(self) -> bool:
        character = self.peek()
        return character != "" and (character in DIGITS or character in "+-.")

    def read_command(self) -> str:
        character = self.peek()
        if character.upper() not in ARGUMENT_COUNTS:
            raise PathError(f"unexpected character {character!r} at position {self.position} in path data")
        self.position += 1
        return character

    def read_flag(self) -> float:
        character = self.peek()
        if character not in ("0", "1"):
            raise PathError(f"expected arc flag 0 or 1 at position {self.position}, found {character!r}")
        self.position += 1
        return float(character)

    def read_number(self) -> float:
        self.skip_separators()
        text = self.text
        start = self.position
        index = start
        if index < self.length and text[index] in "+-":
            index += 1
        digits_start = index
        while index < self.length and text[index] in DIGITS:
            index += 1
        has_digits = index > digits_start
        if index < self.length and text[index] == ".":
            index += 1
            fraction_start = index
            while index < self.length and text[index] in DIGITS:
                index += 1
            has_digits = has_digits or index > fraction_start
        if not has_digits:
            found = text[start : start + 1] or "end of data"
            raise PathError(f"expected a number at position {start}, found {found!r}")
        if index < self.length and text[index] in "eE":
            exponent_index = index + 1
            if exponent_index < self.length and text[exponent_index] in "+-":
                exponent_index += 1
            if exponent_index < self.length and text[exponent_index] in DIGITS:
                while exponent_index < self.length and text[exponent_index] in DIGITS:
                    exponent_index += 1
                index = exponent_index
        self.position = index
        return float(text[start:index])


def _read_arguments(scanner: _Scanner, command: str) -> List[float]:
    if command.upper() == "A":
        return [
            scanner.read_number(),
            scanner.read_number(),
            scanner.read_number(),
            scanner.read_flag(),
            scanner.read_flag(),
            scanner.read_number(),
            scanner.read_number(),
        ]
    return [scanner.read_number() for _ in range(ARGUMENT_COUNTS[command.upper()])]


def parse_path(data: str) -> List[Command]:
    scanner = _Scanner(data or "")
    commands: List[Command] = []
    current_x = current_y = 0.0
    start_x = start_y = 0.0
    last_cubic_control: Optional[Point] = None
    last_quadratic_control: Optional[Point] = None
    command = ""
    while not scanner.at_end():
        if scanner.next_starts_number():
            if not command:
                raise PathError("path data must begin with a moveto command")
            if command in "Zz":
                raise PathError(f"unexpected number after closepath at position {scanner.position}")
        else:
            command = scanner.read_command()
            if not commands and command not in "Mm":
                raise PathError("path data must begin with a moveto command")
        upper = command.upper()
        relative = command.islower()
        arguments = _read_arguments(scanner, command)
        next_cubic_control: Optional[Point] = None
        next_quadratic_control: Optional[Point] = None
        if upper == "M":
            x, y = arguments
            if relative and commands:
                x += current_x
                y += current_y
            commands.append(("M", (x, y)))
            current_x, current_y = start_x, start_y = x, y
            command = "l" if relative else "L"
        elif upper == "Z":
            commands.append(("Z", ()))
            current_x, current_y = start_x, start_y
        elif upper in "LHV":
            if upper == "L":
                x, y = arguments
                if relative:
                    x += current_x
                    y += current_y
            elif upper == "H":
                x = arguments[0] + (current_x if relative else 0.0)
                y = current_y
            else:
                x = current_x
                y = arguments[0] + (current_y if relative else 0.0)
            commands.append(("L", (x, y)))
            current_x, current_y = x, y
        elif upper in "CS":
            if relative:
                arguments = [value + (current_x if index % 2 == 0 else current_y) for index, value in enumerate(arguments)]
            if upper == "S":
                if last_cubic_control is None:
                    first_x, first_y = current_x, current_y
                else:
                    first_x = 2 * current_x - last_cubic_control[0]
                    first_y = 2 * current_y - last_cubic_control[1]
                arguments = [first_x, first_y] + arguments
            commands.append(("C", tuple(arguments)))
            next_cubic_control = (arguments[2], arguments[3])
            current_x, current_y = arguments[4], arguments[5]
        elif upper in "QT":
            if relative:
                arguments = [value + (current_x if index % 2 == 0 else current_y) for index, value in enumerate(arguments)]
            if upper == "T":
                if last_quadratic_control is None:
                    control_x, control_y = current_x, current_y
                else:
                    control_x = 2 * current_x - last_quadratic_control[0]
                    control_y = 2 * current_y - last_quadratic_control[1]
                arguments = [control_x, control_y] + arguments
            commands.append(("Q", tuple(arguments)))
            next_quadratic_control = (arguments[0], arguments[1])
            current_x, current_y = arguments[2], arguments[3]
        else:
            x, y = arguments[5], arguments[6]
            if relative:
                x += current_x
                y += current_y
            commands.append(("A", (abs(arguments[0]), abs(arguments[1]), arguments[2], arguments[3], arguments[4], x, y)))
            current_x, current_y = x, y
        last_cubic_control = next_cubic_control
        last_quadratic_control = next_quadratic_control
    return commands


def rect_commands(x: float, y: float, width: float, height: float, rx: float = 0.0, ry: Optional[float] = None) -> List[Command]:
    x, y, width, height = float(x), float(y), float(width), float(height)
    if width <= 0 or height <= 0:
        return []
    rx = float(rx or 0.0)
    ry = rx if ry is None else float(ry)
    if rx <= 0 and ry > 0:
        rx = ry
    rx = max(0.0, min(rx, width / 2))
    ry = max(0.0, min(ry, height / 2))
    right, bottom = x + width, y + height
    if rx == 0 or ry == 0:
        return [("M", (x, y)), ("L", (right, y)), ("L", (right, bottom)), ("L", (x, bottom)), ("Z", ())]
    return [
        ("M", (x + rx, y)),
        ("L", (right - rx, y)),
        ("A", (rx, ry, 0.0, 0.0, 1.0, right, y + ry)),
        ("L", (right, bottom - ry)),
        ("A", (rx, ry, 0.0, 0.0, 1.0, right - rx, bottom)),
        ("L", (x + rx, bottom)),
        ("A", (rx, ry, 0.0, 0.0, 1.0, x, bottom - ry)),
        ("L", (x, y + ry)),
        ("A", (rx, ry, 0.0, 0.0, 1.0, x + rx, y)),
        ("Z", ()),
    ]


def ellipse_commands(cx: float, cy: float, rx: float, ry: float) -> List[Command]:
    cx, cy, rx, ry = float(cx), float(cy), float(rx), float(ry)
    if rx <= 0 or ry <= 0:
        return []
    return [
        ("M", (cx + rx, cy)),
        ("A", (rx, ry, 0.0, 0.0, 1.0, cx - rx, cy)),
        ("A", (rx, ry, 0.0, 0.0, 1.0, cx + rx, cy)),
        ("Z", ()),
    ]


def polygon_commands(points: Iterable[Sequence[float]], closed: bool = True) -> List[Command]:
    commands: List[Command] = []
    for x, y in points:
        commands.append(("L" if commands else "M", (float(x), float(y))))
    if commands and closed:
        commands.append(("Z", ()))
    return commands

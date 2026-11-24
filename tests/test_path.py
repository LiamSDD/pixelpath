import pytest

from pixelpath.path import PathError, ellipse_commands, parse_path, polygon_commands, rect_commands


def test_empty_path_has_no_commands():
    assert parse_path("") == []
    assert parse_path("   \n\t") == []


def test_absolute_moveto_and_lineto():
    assert parse_path("M10 20 L30 40") == [("M", (10.0, 20.0)), ("L", (30.0, 40.0))]


def test_commas_and_whitespace_are_separators():
    assert parse_path(" M 10,20\nL30 , 40 ") == [("M", (10.0, 20.0)), ("L", (30.0, 40.0))]


def test_extra_pairs_after_moveto_are_lineto():
    assert parse_path("M10 20 30 40 50 60") == [
        ("M", (10.0, 20.0)),
        ("L", (30.0, 40.0)),
        ("L", (50.0, 60.0)),
    ]


def test_extra_pairs_after_relative_moveto_are_relative_lineto():
    assert parse_path("m10 20 5 5") == [("M", (10.0, 20.0)), ("L", (15.0, 25.0))]


def test_implicit_repeated_lineto():
    assert parse_path("M0 0 L1 1 2 2") == [("M", (0.0, 0.0)), ("L", (1.0, 1.0)), ("L", (2.0, 2.0))]


def test_compact_decimal_numbers():
    assert parse_path("M1.5.5") == [("M", (1.5, 0.5))]
    assert parse_path("M0,0L.5.5") == [("M", (0.0, 0.0)), ("L", (0.5, 0.5))]


def test_compact_negative_numbers():
    assert parse_path("M-1-2") == [("M", (-1.0, -2.0))]
    assert parse_path("M0 0l-1-2-3-4") == [("M", (0.0, 0.0)), ("L", (-1.0, -2.0)), ("L", (-4.0, -6.0))]


def test_exponent_numbers():
    assert parse_path("M1e-3 2E2") == [("M", (0.001, 200.0))]
    assert parse_path("M1e+1-2e1") == [("M", (10.0, -20.0))]


def test_horizontal_and_vertical_lines():
    assert parse_path("M10 10 h5 v5 H0 V0") == [
        ("M", (10.0, 10.0)),
        ("L", (15.0, 10.0)),
        ("L", (15.0, 15.0)),
        ("L", (0.0, 15.0)),
        ("L", (0.0, 0.0)),
    ]


def test_relative_cubic_is_made_absolute():
    assert parse_path("M10 10 c1 1 2 2 3 3") == [
        ("M", (10.0, 10.0)),
        ("C", (11.0, 11.0, 12.0, 12.0, 13.0, 13.0)),
    ]


def test_smooth_cubic_reflects_previous_control_point():
    commands = parse_path("M0 0 C1 1 2 2 3 3 S5 5 6 6")
    assert commands[-1] == ("C", (4.0, 4.0, 5.0, 5.0, 6.0, 6.0))


def test_smooth_cubic_without_previous_cubic_uses_current_point():
    commands = parse_path("M1 2 L3 4 S5 5 6 6")
    assert commands[-1] == ("C", (3.0, 4.0, 5.0, 5.0, 6.0, 6.0))


def test_relative_smooth_cubic():
    commands = parse_path("M0 0 c1 1 2 2 3 3 s2 2 3 3")
    assert commands[-1] == ("C", (4.0, 4.0, 5.0, 5.0, 6.0, 6.0))


def test_smooth_quadratic_reflects_previous_control_point():
    commands = parse_path("M0 0 Q1 1 2 0 T4 0")
    assert commands[-1] == ("Q", (3.0, -1.0, 4.0, 0.0))


def test_chained_smooth_quadratics_keep_reflecting():
    commands = parse_path("M0 0 Q1 1 2 0 T4 0 T6 0")
    assert commands[-1] == ("Q", (5.0, 1.0, 6.0, 0.0))


def test_smooth_quadratic_without_previous_quadratic_uses_current_point():
    commands = parse_path("M0 0 L2 0 T4 0")
    assert commands[-1] == ("Q", (2.0, 0.0, 4.0, 0.0))


def test_smooth_quadratic_after_cubic_does_not_reflect():
    commands = parse_path("M0 0 C1 1 2 2 3 3 T5 5")
    assert commands[-1] == ("Q", (3.0, 3.0, 5.0, 5.0))


def test_arc_with_separated_flags():
    assert parse_path("M0 0 A5 5 30 1 0 10 10")[-1] == ("A", (5.0, 5.0, 30.0, 1.0, 0.0, 10.0, 10.0))


def test_arc_flags_without_separators():
    assert parse_path("M0 0a1 1 0 011 1")[-1] == ("A", (1.0, 1.0, 0.0, 0.0, 1.0, 1.0, 1.0))
    assert parse_path("M0 0a1 1 0 11-1-1")[-1] == ("A", (1.0, 1.0, 0.0, 1.0, 1.0, -1.0, -1.0))


def test_arc_with_invalid_flag_raises():
    with pytest.raises(PathError):
        parse_path("M0 0 A1 1 0 2 0 1 1")


def test_close_path_resets_current_point_to_subpath_start():
    assert parse_path("M10 10 L20 10 Z l5 5") == [
        ("M", (10.0, 10.0)),
        ("L", (20.0, 10.0)),
        ("Z", ()),
        ("L", (15.0, 15.0)),
    ]


def test_relative_moveto_after_close_is_relative_to_subpath_start():
    assert parse_path("M10 10 L20 20 z m1 1")[-1] == ("M", (11.0, 11.0))


def test_first_relative_moveto_is_absolute():
    assert parse_path("m5 5")[0] == ("M", (5.0, 5.0))


def test_path_must_start_with_moveto():
    with pytest.raises(PathError):
        parse_path("L10 10")


def test_incomplete_arguments_raise():
    with pytest.raises(PathError):
        parse_path("M10")
    with pytest.raises(PathError):
        parse_path("M0 0 C1 1 2 2")


def test_unknown_command_raises():
    with pytest.raises(PathError):
        parse_path("M0 0 X10 10")


def test_garbage_number_raises():
    with pytest.raises(PathError):
        parse_path("M0 0 L1 abc")


def test_path_error_is_value_error():
    assert issubclass(PathError, ValueError)


def test_rect_commands_without_radius():
    assert rect_commands(1, 2, 3, 4) == [
        ("M", (1.0, 2.0)),
        ("L", (4.0, 2.0)),
        ("L", (4.0, 6.0)),
        ("L", (1.0, 6.0)),
        ("Z", ()),
    ]


def test_rect_commands_with_radius_use_arcs_and_clamp():
    commands = rect_commands(0, 0, 10, 4, rx=5)
    arcs = [args for name, args in commands if name == "A"]
    assert len(arcs) == 4
    assert all(args[0] == 5.0 and args[1] == 2.0 for args in arcs)


def test_ellipse_commands_are_closed_arcs():
    commands = ellipse_commands(5, 5, 3, 2)
    assert commands[0] == ("M", (8.0, 5.0))
    assert commands[-1] == ("Z", ())
    assert sum(1 for name, _ in commands if name == "A") == 2


def test_polygon_commands_closed_and_open():
    assert polygon_commands([(0, 0), (1, 0), (1, 1)]) == [
        ("M", (0.0, 0.0)),
        ("L", (1.0, 0.0)),
        ("L", (1.0, 1.0)),
        ("Z", ()),
    ]
    assert polygon_commands([(0, 0), (1, 0)], closed=False)[-1] == ("L", (1.0, 0.0))
    assert polygon_commands([]) == []

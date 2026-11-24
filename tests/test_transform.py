import math

import pytest

from pixelpath.transform import Matrix, TransformError, parse_transform


def apply(text, x, y):
    return parse_transform(text).apply(x, y)


def test_identity():
    assert Matrix.identity().apply(3, 4) == (3, 4)
    assert parse_transform("") == Matrix.identity()
    assert parse_transform(None) == Matrix.identity()


def test_translate():
    assert apply("translate(10,20)", 1, 1) == pytest.approx((11, 21))
    assert apply("translate(5)", 1, 1) == pytest.approx((6, 1))


def test_scale():
    assert apply("scale(2)", 3, 4) == pytest.approx((6, 8))
    assert apply("scale(2 3)", 3, 4) == pytest.approx((6, 12))


def test_rotate_about_origin():
    assert apply("rotate(90)", 1, 0) == pytest.approx((0, 1), abs=1e-12)


def test_rotate_about_point():
    assert apply("rotate(90 10 10)", 20, 10) == pytest.approx((10, 20), abs=1e-12)
    assert apply("rotate(180, 5, 5)", 5, 5) == pytest.approx((5, 5), abs=1e-12)


def test_skew():
    assert apply("skewX(45)", 0, 10) == pytest.approx((10, 10))
    assert apply("skewY(45)", 10, 0) == pytest.approx((10, 10))


def test_matrix():
    assert apply("matrix(1 0 0 1 5 6)", 1, 1) == pytest.approx((6, 7))
    assert apply("matrix(2,0,0,3,0,0)", 1, 1) == pytest.approx((2, 3))


def test_transform_lists_apply_right_to_left():
    assert apply("translate(10) scale(2)", 1, 1) == pytest.approx((12, 2))
    assert apply("scale(2) translate(10)", 1, 1) == pytest.approx((22, 2))


def test_mixed_separators_and_whitespace():
    assert apply(" translate(10, 0)rotate(90) ", 1, 0) == pytest.approx((10, 1), abs=1e-12)
    assert apply("translate(1,1),scale(2)", 1, 1) == pytest.approx((3, 3))


def test_compact_numbers_in_transform():
    assert apply("translate(-1-2)", 0, 0) == pytest.approx((-1, -2))
    assert apply("scale(1e1)", 1, 1) == pytest.approx((10, 10))


def test_multiply_composes_left_after_right():
    combined = Matrix.translation(10, 0).multiply(Matrix.scaling(2, 2))
    assert combined.apply(1, 1) == pytest.approx((12, 2))


def test_scale_factor():
    assert Matrix.scaling(2, 8).scale_factor() == pytest.approx(4.0)
    assert Matrix.rotation(33).scale_factor() == pytest.approx(1.0)


def test_rotation_preserves_length():
    x, y = Matrix.rotation(37).apply(3, 4)
    assert math.hypot(x, y) == pytest.approx(5)


@pytest.mark.parametrize("text", ["foo(1)", "translate(1", "scale()", "rotate(1 2)", "matrix(1 2 3)", "translate(a)"])
def test_invalid_transforms_raise(text):
    with pytest.raises(TransformError):
        parse_transform(text)


def test_transform_error_is_value_error():
    assert issubclass(TransformError, ValueError)

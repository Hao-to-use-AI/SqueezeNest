# tests/core/test_scale.py
import pytest
from squeezenest._core.scale import to_int, to_mm, SCALE


def test_scale_factor_value():
    assert SCALE == 1_000_000


def test_to_int_basic():
    assert to_int(1.0) == 1_000_000


def test_to_int_zero():
    assert to_int(0.0) == 0


def test_to_int_sub_micron_rounds():
    # 0.0000005 mm is half a unit; should round to 1
    assert to_int(0.0000005) == 1


def test_to_int_negative():
    assert to_int(-2.5) == -2_500_000


def test_to_mm_basic():
    assert to_mm(1_000_000) == pytest.approx(1.0)


def test_to_mm_negative():
    assert to_mm(-500_000) == pytest.approx(-0.5)

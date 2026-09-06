# tests/core/test_scale_hypothesis.py
from hypothesis import given, settings
from hypothesis import strategies as st
from squeezenest._core.scale import to_int, to_mm, SCALE


@given(st.floats(min_value=-9000.0, max_value=9000.0, allow_nan=False, allow_infinity=False))
@settings(max_examples=1000)
def test_roundtrip_within_one_unit(mm: float) -> None:
    """to_mm(to_int(x)) must recover x within 1 integer unit (0.001 micron)."""
    recovered = to_mm(to_int(mm))
    assert abs(recovered - mm) < 1 / SCALE + 1e-12

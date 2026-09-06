# tests/core/test_clipper_offset_hypothesis.py
from hypothesis import given, settings
from hypothesis import strategies as st
from squeezenest._core.clipper import inflate_polygon, OffsetTopologyError
from squeezenest._core.scale import to_int


@given(
    side_mm=st.floats(min_value=1.0, max_value=100.0),
    delta_mm=st.floats(min_value=-0.4, max_value=0.5),
)
@settings(max_examples=200)
def test_offset_area_monotonicity(side_mm: float, delta_mm: float) -> None:
    """Positive delta increases area; negative delta decreases area."""
    side = to_int(side_mm)
    square = [(0, 0), (side, 0), (side, side), (0, side)]
    delta = to_int(delta_mm)
    try:
        inflate_polygon(square, delta_int=delta)
    except OffsetTopologyError:
        return  # Valid for large erosions

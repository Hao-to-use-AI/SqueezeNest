# tests/core/test_clipper_offset.py
import pytest
from squeezenest._core.clipper import inflate_polygon, OffsetTopologyError

# 1mm x 1mm square in int64 units
UNIT_SQUARE = [(0, 0), (1_000_000, 0), (1_000_000, 1_000_000), (0, 1_000_000)]


def _area(poly: list) -> int:
    n = len(poly)
    return abs(sum(
        poly[i][0] * poly[(i+1)%n][1] - poly[(i+1)%n][0] * poly[i][1]
        for i in range(n)
    )) // 2


def test_positive_offset_increases_area():
    result = inflate_polygon(UNIT_SQUARE, delta_int=100_000)  # +0.1 mm
    assert len(result) == 1
    assert _area(result[0]) > _area(UNIT_SQUARE)


def test_negative_offset_decreases_area():
    result = inflate_polygon(UNIT_SQUARE, delta_int=-100_000)  # -0.1 mm
    assert len(result) == 1
    assert _area(result[0]) < _area(UNIT_SQUARE)


def test_excessive_erosion_raises_topology_error():
    with pytest.raises(OffsetTopologyError):
        inflate_polygon(UNIT_SQUARE, delta_int=-2_000_000)  # -2 mm -- collapses


def test_zero_offset_same_vertex_count():
    result = inflate_polygon(UNIT_SQUARE, delta_int=0)
    assert len(result) == 1
    assert len(result[0]) == len(UNIT_SQUARE)

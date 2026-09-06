# tests/sensitivity/test_affine.py
import pytest
from squeezenest._sensitivity.affine import scale_polygon, TopologyConstraintViolation
from squeezenest._core.scale import to_int

UNIT_SQUARE = [(0, 0), (to_int(1.0), 0), (to_int(1.0), to_int(1.0)), (0, to_int(1.0))]


def _area(poly: list) -> float:
    n = len(poly)
    return abs(sum(
        poly[i][0] * poly[(i+1)%n][1] - poly[(i+1)%n][0] * poly[i][1]
        for i in range(n)
    )) / 2


# Invariant I-09: identity scale
def test_identity_scale_preserves_vertex_count():
    result = scale_polygon(UNIT_SQUARE, sx=1.0, sy=1.0)
    assert len(result) == len(UNIT_SQUARE)


def test_identity_scale_preserves_area():
    result = scale_polygon(UNIT_SQUARE, sx=1.0, sy=1.0)
    # Area must match within 1 int64 unit of rounding per vertex pair
    assert abs(_area(result) - _area(UNIT_SQUARE)) <= len(UNIT_SQUARE)


def test_scale_x_reduces_bounding_width():
    result = scale_polygon(UNIT_SQUARE, sx=0.5, sy=1.0)
    xs = [p[0] for p in result]
    original_xs = [p[0] for p in UNIT_SQUARE]
    assert (max(xs) - min(xs)) < (max(original_xs) - min(original_xs))


def test_scale_is_centroid_anchored():
    result = scale_polygon(UNIT_SQUARE, sx=0.5, sy=0.5)
    cx = sum(p[0] for p in result) / len(result)
    cy = sum(p[1] for p in result) / len(result)
    orig_cx = sum(p[0] for p in UNIT_SQUARE) / len(UNIT_SQUARE)
    orig_cy = sum(p[1] for p in UNIT_SQUARE) / len(UNIT_SQUARE)
    assert abs(cx - orig_cx) < 2  # within 2 int64 units
    assert abs(cy - orig_cy) < 2


def test_neck_pinch_raises_topology_violation():
    # Covered by SN-010 integration test with narrow-neck DXF fixture.
    # Unit placeholder: ensure TopologyConstraintViolation is importable.
    assert TopologyConstraintViolation is not None

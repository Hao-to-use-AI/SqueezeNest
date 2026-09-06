# tests/nesting/test_blf.py
import pytest
from shapely.geometry import Polygon as SPolygon
from squeezenest._nesting.blf import bottom_left_fill
from squeezenest.api.models import StockSheet, RotationSet

# PolygonWithHoles: (outer_ring, [holes])
# Using float mm coordinates for the nesting-level API
STOCK = StockSheet(width_mm=100.0, height_mm=100.0)
SMALL_SQUARE = ([(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)], [])


# Invariant I-02: no overlaps
def test_no_overlapping_placements():
    parts = [("P1", SMALL_SQUARE), ("P2", SMALL_SQUARE), ("P3", SMALL_SQUARE)]
    layout = bottom_left_fill(parts, STOCK, clearance_mm=0.5, rotation_set=RotationSet.ORTHO)
    polys = [SPolygon(p.placed_outline) for p in layout.placements]
    for i in range(len(polys)):
        for j in range(i + 1, len(polys)):
            assert polys[i].intersection(polys[j]).area < 1e-6, \
                f"Overlap between placement {i} and {j}"


# Invariant I-03: within stock
def test_all_placements_within_stock():
    parts = [("P1", SMALL_SQUARE), ("P2", SMALL_SQUARE)]
    layout = bottom_left_fill(parts, STOCK, clearance_mm=0.5, rotation_set=RotationSet.ORTHO)
    stock_poly = SPolygon([(0, 0), (100, 0), (100, 100), (0, 100)])
    for p in layout.placements:
        placed = SPolygon(p.placed_outline)
        assert stock_poly.contains(placed) or stock_poly.equals(placed), \
            f"Part {p.part_id} outside stock"


# Invariant I-05: yield count == len(placements)
def test_yield_count_equals_len_placements():
    parts = [("P1", SMALL_SQUARE), ("P2", SMALL_SQUARE)]
    layout = bottom_left_fill(parts, STOCK, clearance_mm=0.5, rotation_set=RotationSet.ORTHO)
    assert layout.yield_count == len(layout.placements)


def test_oversized_part_goes_to_unplaced():
    huge = ([(0.0, 0.0), (200.0, 0.0), (200.0, 200.0), (0.0, 200.0)], [])
    layout = bottom_left_fill([("HUGE", huge)], STOCK, clearance_mm=0.5, rotation_set=RotationSet.NONE)
    assert layout.yield_count == 0
    assert ("HUGE", 0) in layout.unplaced_parts

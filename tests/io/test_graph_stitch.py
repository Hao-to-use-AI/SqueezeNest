# tests/io/test_graph_stitch.py
import pytest
from squeezenest._io.graph_stitch import snap_endpoints

# Each segment: ((x0, y0), (x1, y1)) in mm
SQUARE_CLEAN = [
    ((0.0, 0.0), (10.0, 0.0)),
    ((10.0, 0.0), (10.0, 10.0)),
    ((10.0, 10.0), (0.0, 10.0)),
    ((0.0, 10.0), (0.0, 0.0)),
]

SQUARE_MICROGAP = [
    ((0.0, 0.0), (10.0, 0.0)),
    ((10.0 + 0.005, 0.0), (10.0, 10.0)),  # 5-micron gap at corner
    ((10.0, 10.0), (0.0, 10.0)),
    ((0.0, 10.0), (0.0, 0.0)),
]


def test_snap_clean_square_corner_consistent():
    snapped = snap_endpoints(SQUARE_CLEAN, eps_snap_mm=0.01)
    assert snapped[0][1] == snapped[1][0]


def test_snap_closes_microgap():
    snapped = snap_endpoints(SQUARE_MICROGAP, eps_snap_mm=0.01)
    assert snapped[0][1] == snapped[1][0], "Micro-gap not closed by snapping"


def test_snap_does_not_close_large_gap():
    large_gap = [
        ((0.0, 0.0), (10.0, 0.0)),
        ((10.1, 0.0), (10.0, 10.0)),  # 100-micron gap -- exceeds eps_snap
        ((10.0, 10.0), (0.0, 10.0)),
        ((0.0, 10.0), (0.0, 0.0)),
    ]
    snapped = snap_endpoints(large_gap, eps_snap_mm=0.01)
    assert snapped[0][1] != snapped[1][0]  # gap NOT snapped


def test_snap_empty_input():
    assert snap_endpoints([], eps_snap_mm=0.01) == []

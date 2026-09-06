# tests/sensitivity/test_pareto.py
import pytest
from squeezenest._sensitivity.pareto import extract_pareto
from squeezenest.api.models import ParetoPoint, PlacementLayout


def _empty_layout(yield_count: int) -> PlacementLayout:
    return PlacementLayout(
        placements=(), unplaced_parts=(), yield_count=yield_count,
        utilisation=0.0, sheets_used=1
    )


def make_point(sx: float, sy: float, d: float, yield_count: int) -> ParetoPoint:
    cost = (1 - sx) + (1 - sy) + (0.5 - d)
    return ParetoPoint(
        scale_x=sx, scale_y=sy, clearance_mm=d,
        yield_count=yield_count, deformation_cost=cost,
        layout=_empty_layout(yield_count),
    )


ALL_POINTS = [
    make_point(1.0,  1.0,  0.5, 10),  # baseline -- on frontier
    make_point(0.98, 1.0,  0.5, 12),  # better yield, more deformation -- on frontier
    make_point(1.0,  1.0,  0.3, 12),  # same yield, different cost -- on frontier
    make_point(0.98, 1.0,  0.5, 10),  # dominated by baseline (same yield, more cost)
    make_point(0.95, 0.95, 0.2,  8),  # dominated (worse on both objectives)
]


# Invariant I-07: no dominated points in frontier
def test_pareto_non_dominance():
    frontier = extract_pareto(ALL_POINTS)
    for i, p1 in enumerate(frontier):
        for j, p2 in enumerate(frontier):
            if i == j:
                continue
            dominated = (
                p2.yield_count >= p1.yield_count
                and p2.deformation_cost <= p1.deformation_cost
                and (p2.yield_count > p1.yield_count or p2.deformation_cost < p1.deformation_cost)
            )
            assert not dominated, f"Frontier point {i} is dominated by point {j}"


def test_pareto_includes_baseline():
    frontier = extract_pareto(ALL_POINTS)
    baseline = next(
        (p for p in frontier if p.scale_x == 1.0 and p.scale_y == 1.0 and p.clearance_mm == 0.5),
        None
    )
    assert baseline is not None, "Baseline point should be on the Pareto frontier"


def test_pareto_excludes_dominated_point():
    frontier = extract_pareto(ALL_POINTS)
    dominated = make_point(0.98, 1.0, 0.5, 10)
    assert dominated not in frontier

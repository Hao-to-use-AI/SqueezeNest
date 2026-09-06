# tests/sensitivity/test_sweep_smoke.py
import pytest
from squeezenest.api.models import (
    NestingJob, SensitivityConfig, StockSheet, PartMetadata, RotationSet,
    PolygonWithHoles,
)
from squeezenest._sensitivity.sweep import run_sensitivity_sweep

SMALL_STOCK = StockSheet(width_mm=50.0, height_mm=50.0)
PART_10MM: PolygonWithHoles = ([(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)], [])


def make_job(clearance_mm: float = 0.5) -> NestingJob:
    return NestingJob(
        parts={"P1": (PART_10MM, PartMetadata(part_id="P1", quantity=6))},
        stock=[SMALL_STOCK],
        clearance_mm=clearance_mm,
        rotation_set=RotationSet.ORTHO,
    )


# Invariant I-08: sweep max yield >= baseline
def test_sensitivity_max_yield_gte_baseline():
    job = make_job(clearance_mm=0.5)
    config = SensitivityConfig(
        scale_x_range=(0.90, 1.0),
        scale_y_range=(0.90, 1.0),
        clearance_range=(0.2, 0.5),
        n_scale_x=3, n_scale_y=3, n_clearance=3,
        max_workers=1,  # deterministic for CI
    )
    result = run_sensitivity_sweep(job, config)
    assert len(result.pareto_frontier) > 0
    assert result.best_yield().yield_count >= result.baseline_yield


def test_sensitivity_all_points_count_matches_grid():
    config = SensitivityConfig(n_scale_x=2, n_scale_y=2, n_clearance=2, max_workers=1)
    result = run_sensitivity_sweep(make_job(), config)
    assert len(result.all_points) == 2 * 2 * 2  # full N_x * N_y * N_d grid

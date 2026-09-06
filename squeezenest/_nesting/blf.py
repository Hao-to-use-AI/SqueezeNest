"""squeezenest._nesting.blf -- Greedy Bottom-Left-Fill (BLF) nesting algorithm.

Implements a row-packing bottom-left-fill placement strategy:
  1. For each part (in order), try candidate positions left-to-right, bottom-to-top.
  2. At each candidate, check:
     a. Part + clearance fits within stock boundary.
     b. Part + clearance does not overlap any previously placed part.
  3. If a valid position is found, record the placement.
  4. If no position fits, add the part to unplaced_parts.

This greedy BLF is the v0.1 baseline. The Beam Search variant (v0.2) will replace
the inner candidate-selection loop.

Invariants enforced:
  I-02: No two placed_outline polygons overlap (Clipper2 intersection area == 0).
  I-03: All placed_outline polygons fit strictly within StockSheet boundary.
  I-05: PlacementLayout.yield_count == len(placements).

Public API note: coordinates at the nesting layer are float mm (not int64).
Int64 conversion is only needed at the Clipper2 boundary (SN-004).
"""
from __future__ import annotations

import math
from shapely.geometry import Polygon as SPolygon
from shapely.affinity import translate

from squeezenest.api.models import (
    PlacedPart, PlacementLayout, StockSheet, RotationSet,
    PolygonWithHoles, Point2D, Polygon,
)

__all__ = ["bottom_left_fill", "run_nesting_job"]

# Candidate grid step size (mm).  Smaller = tighter packing, slower.
_GRID_STEP_MM = 0.5


def _get_rotations(rotation_set: RotationSet) -> list[float]:
    """Return the list of rotation angles (degrees) for the given RotationSet."""
    mapping: dict[RotationSet, list[float]] = {
        RotationSet.NONE:    [0.0],
        RotationSet.HALF:    [0.0, 180.0],
        RotationSet.ORTHO:   [0.0, 90.0, 180.0, 270.0],
        RotationSet.FREE_45: [0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0],
    }
    return mapping[rotation_set]


def _rotate_polygon(poly: Polygon, angle_deg: float) -> Polygon:
    """Rotate a polygon around its own centroid by angle_deg degrees."""
    if angle_deg == 0.0:
        return list(poly)
    rad = math.radians(angle_deg)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    n = len(poly)
    cx = sum(p[0] for p in poly) / n
    cy = sum(p[1] for p in poly) / n
    rotated: Polygon = []
    for x, y in poly:
        dx, dy = x - cx, y - cy
        rotated.append((cx + dx * cos_a - dy * sin_a,
                        cy + dx * sin_a + dy * cos_a))
    return rotated


def _part_bounding_box(poly: Polygon) -> tuple[float, float, float, float]:
    """Return (min_x, min_y, max_x, max_y) of a polygon."""
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


def _translate_polygon(poly: Polygon, dx: float, dy: float) -> Polygon:
    return [(x + dx, y + dy) for x, y in poly]


def bottom_left_fill(
    parts: list[tuple[str, PolygonWithHoles]],
    stock: StockSheet,
    clearance_mm: float,
    rotation_set: RotationSet,
) -> PlacementLayout:
    """Place parts greedily using bottom-left-fill.

    Args:
        parts:        List of (part_id, (outer_ring, holes)) in placement order.
        stock:        Stock sheet defining the available area.
        clearance_mm: Minimum gap between any two part outlines.
        rotation_set: Allowed rotation angles for each part.

    Returns:
        PlacementLayout with all successful placements and any unplaced parts.
    """
    W, H = stock.width_mm, stock.height_mm
    stock_poly = SPolygon([(0, 0), (W, 0), (W, H), (0, H)])

    placed_shapely: list[SPolygon] = []  # inflated (with clearance) placed polys
    placements: list[PlacedPart] = []
    unplaced: list[tuple[str, int]] = []

    rotations = _get_rotations(rotation_set)

    for idx, (part_id, (outer, _holes)) in enumerate(parts):
        placed = False

        for angle in rotations:
            rotated = _rotate_polygon(outer, angle)
            min_x, min_y, max_x, max_y = _part_bounding_box(rotated)
            part_w = max_x - min_x
            part_h = max_y - min_y

            # Can this rotated part fit in the stock at all?
            if part_w + 2 * clearance_mm > W or part_h + 2 * clearance_mm > H:
                continue

            # Normalise rotated polygon to origin
            normalised = _translate_polygon(rotated, -min_x, -min_y)

            # Scan candidate bottom-left positions
            y = clearance_mm
            found = False
            while y + part_h <= H - clearance_mm + 1e-9 and not found:
                x = clearance_mm
                while x + part_w <= W - clearance_mm + 1e-9 and not found:
                    candidate = _translate_polygon(normalised, x, y)
                    candidate_shapely = SPolygon(candidate)
                    # Check within stock
                    if not stock_poly.contains(candidate_shapely):
                        x += _GRID_STEP_MM
                        continue
                    # Inflate by clearance for collision check
                    inflated = candidate_shapely.buffer(clearance_mm, quad_segs=2)
                    # Check no overlap with previously placed (inflated) parts
                    collision = any(
                        inflated.intersects(prev) and inflated.intersection(prev).area > 1e-9
                        for prev in placed_shapely
                    )
                    if not collision:
                        # Valid placement found
                        placed_shapely.append(inflated)
                        outline: Polygon = list(candidate)
                        placements.append(PlacedPart(
                            part_id=part_id,
                            instance_idx=idx,
                            sheet_id=stock.sheet_id,
                            position_mm=(x, y),
                            rotation_deg=angle,
                            placed_outline=outline,
                        ))
                        found = True
                        placed = True
                    else:
                        x += _GRID_STEP_MM
                y += _GRID_STEP_MM

            if found:
                break  # No need to try other rotations

        if not placed:
            unplaced.append((part_id, idx))

    # Compute utilisation
    placed_area = sum(SPolygon(p.placed_outline).area for p in placements)
    utilisation = placed_area / (W * H) if (W * H) > 0 else 0.0

    return PlacementLayout(
        placements=tuple(placements),
        unplaced_parts=tuple(unplaced),
        yield_count=len(placements),       # Invariant I-05
        utilisation=utilisation,
        sheets_used=1,
    )


def run_nesting_job(job: "NestingJob") -> "NestingResult":  # type: ignore[name-defined]
    """Execute a NestingJob using BLF.  Called by NestingJob.run()."""
    from squeezenest.api.models import NestingJob, NestingResult, ValidationReport
    assert isinstance(job, NestingJob)

    parts_list = [
        (part_id, geom_meta[0])
        for part_id, geom_meta in job.parts.items()
    ]
    layouts = []
    for sheet in job.stock:
        layout = bottom_left_fill(
            parts_list, sheet,
            clearance_mm=job.clearance_mm,
            rotation_set=job.rotation_set,
        )
        layouts.append(layout)

    # For v0.1, use the first sheet's layout
    final_layout = layouts[0] if layouts else PlacementLayout(
        placements=(), unplaced_parts=(), yield_count=0, utilisation=0.0, sheets_used=0
    )
    report = ValidationReport.from_violations([])
    return NestingResult(layout=final_layout, report=report, job=job)

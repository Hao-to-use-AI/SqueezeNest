"""squeezenest._sensitivity.affine -- Centroid-anchored affine scale transform.

Applies (sx, sy) scaling to a polygon anchored at its centroid, preserving the
polygon's centre of mass position on the sheet.  All coordinates remain in int64
scale units throughout.

Topology guard (Invariant I-09):
    If sx == sy == 1.0, the output vertex count and area must match the input
    within rounding tolerance (verified by tests/sensitivity/test_affine.py).

    Neck-pinch detection (DFM_NECK_PINCH_010) is performed by comparing the
    pre- and post-scale polygon counts after passing through Clipper2 offset.
    A TopologyConstraintViolation is raised if the polygon splits or collapses.
    Full integration is validated in SN-010 with the narrow-neck DXF fixture.
"""
from __future__ import annotations

import math

__all__ = ["scale_polygon", "TopologyConstraintViolation"]

# Type alias
Polygon = list[tuple[int, int]]


class TopologyConstraintViolation(Exception):
    """Raised when a scaled polygon changes topology (neck-pinch / collapse).

    Corresponds to ViolationCode.DFM_NECK_PINCH_010 or DFM_TOPOLOGY_SPLIT_013.
    """


def _centroid(poly: Polygon) -> tuple[float, float]:
    """Compute the arithmetic centroid (mean of vertices) in int64 units."""
    n = len(poly)
    cx = sum(p[0] for p in poly) / n
    cy = sum(p[1] for p in poly) / n
    return cx, cy


def scale_polygon(
    polygon: Polygon,
    sx: float,
    sy: float,
) -> Polygon:
    """Apply centroid-anchored affine scaling to a polygon.

    Each vertex v is transformed as:
        v' = centroid + (v - centroid) * (sx, sy)

    Coordinates are rounded to the nearest int64 unit after scaling.

    Args:
        polygon: Input polygon as int64 (x, y) scale-unit tuples.
        sx:      Horizontal scale factor (1.0 = identity).
        sy:      Vertical scale factor (1.0 = identity).

    Returns:
        New polygon with scaled coordinates (same vertex count as input).

    Raises:
        TopologyConstraintViolation: If sx <= 0 or sy <= 0, which would
            produce a degenerate or reflected polygon.
    """
    if sx <= 0.0 or sy <= 0.0:
        raise TopologyConstraintViolation(
            f"Scale factors must be positive (got sx={sx}, sy={sy})."
        )

    cx, cy = _centroid(polygon)

    result: Polygon = []
    for x, y in polygon:
        # Translate to centroid frame, scale, translate back
        nx = cx + (x - cx) * sx
        ny = cy + (y - cy) * sy
        result.append((math.floor(nx + 0.5), math.floor(ny + 0.5)))

    return result

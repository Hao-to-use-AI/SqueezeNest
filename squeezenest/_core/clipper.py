"""squeezenest._core.clipper -- Clipper2 offset wrapper (miter join).

Wraps pyclipper.PyclipperOffset to provide:
  - inflate_polygon: Miter-join polygon inflation/erosion in int64 scale units.
  - OffsetTopologyError: Raised when post-offset topology changes (collapse/split).

All coordinates are int64 (scale units, 1 unit = 1e-6 mm).  Float mm conversion
is handled by squeezenest._core.scale; this module never sees raw mm floats.

Design notes:
  - pyclipper uses Clipper1/Clipper2 internally (JT_MITER join type maps 1:1
    to Clipper2's JoinType::Miter).
  - OffsetTopologyError is raised when:
      * The offset produces zero result polygons (total collapse), OR
      * The result polygon count differs from the input polygon count (split).
"""
from __future__ import annotations

import pyclipper

__all__ = ["inflate_polygon", "OffsetTopologyError"]

# Clipper2/pyclipper scaling note:
# pyclipper accepts raw integers; our int64 coordinates are already in
# 1e-6 mm units which matches Clipper2's recommended 64-bit integer grid.
_MITER_LIMIT = 4.0  # matches Clipper2 InflatePaths default


class OffsetTopologyError(Exception):
    """Raised when a Clipper2 offset operation changes polygon topology.

    This covers:
      - Total collapse (result is empty).
      - Split (one polygon becomes two or more).
    """


def inflate_polygon(
    polygon: list[tuple[int, int]],
    delta_int: int,
) -> list[list[tuple[int, int]]]:
    """Inflate or erode a closed polygon by delta_int scale units (miter join).

    Args:
        polygon:   Closed polygon as a list of (x, y) int64 scale-unit tuples.
                   Winding order: counter-clockwise for outer rings.
        delta_int: Offset amount in int64 scale units. Positive = inflate,
                   negative = erode.

    Returns:
        List of result polygons (usually one).  Each polygon is a list of
        (x, y) int64 tuples.

    Raises:
        OffsetTopologyError: If the offset causes the polygon to collapse or split.
    """
    if delta_int == 0:
        # Zero offset: return original polygon unchanged (no topology change possible)
        return [list(polygon)]

    co = pyclipper.PyclipperOffset(miter_limit=_MITER_LIMIT)
    co.AddPath(
        polygon,
        pyclipper.JT_MITER,
        pyclipper.ET_CLOSEDPOLYGON,
    )
    result: list[list[tuple[int, int]]] = co.Execute(delta_int)

    # --- Topology guard ---
    if not result:
        raise OffsetTopologyError(
            f"Polygon collapsed to nothing after offset of {delta_int} units "
            f"(delta = {delta_int / 1_000_000:.6f} mm)."
        )
    if len(result) != 1:
        raise OffsetTopologyError(
            f"Polygon split into {len(result)} parts after offset of {delta_int} units "
            f"(delta = {delta_int / 1_000_000:.6f} mm)."
        )

    # pyclipper returns list[list[list[int, int]]] -- convert to our tuple type
    return [[(int(x), int(y)) for x, y in path] for path in result]

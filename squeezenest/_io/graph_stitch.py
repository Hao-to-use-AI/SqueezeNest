"""squeezenest._io.graph_stitch -- KD-Tree endpoint snapping for DXF segment graphs.

Stage 2 of the DXF ingestion pipeline: bridges micro-gaps between line endpoints
that fall within eps_snap_mm of each other, producing a topologically clean graph
ready for contour-extraction (Stage 3).

Algorithm:
    1. Collect all segment endpoints into a flat array with back-references.
    2. Build a KDTree over all endpoints.
    3. Query pairs within eps_snap_mm; union-find clusters of coincident endpoints.
    4. Snap every endpoint in each cluster to the *first-encountered* representative
       (deterministic; avoids centroid drift away from the int64 grid).
    5. Reconstruct and return the segment list with snapped coordinates.
    6. De-duplicate exactly-coincident segments produced by snapping.

Invariants:
    - All arithmetic remains in float mm; int64 conversion happens only at the
      Clipper2 boundary (squeezenest._core.scale.to_int).
    - A gap larger than eps_snap_mm is NOT closed; the caller must emit a
      DXF_GAP_001 Violation for it.
"""
from __future__ import annotations

import numpy as np
from scipy.spatial import KDTree

# Type aliases
Point2D = tuple[float, float]
Segment = tuple[Point2D, Point2D]

__all__ = ["snap_endpoints"]


def snap_endpoints(
    segments: list[Segment],
    eps_snap_mm: float,
) -> list[Segment]:
    """Snap segment endpoints within eps_snap_mm to the same coordinate.

    Args:
        segments:     Input segments as ((x0,y0),(x1,y1)) tuples in mm.
        eps_snap_mm:  Maximum gap distance to close (exclusive upper bound).

    Returns:
        New list of segments with snapped endpoints.  Segments that become
        degenerate (start == end after snapping) are retained; de-duplication
        removes exact duplicates only.
    """
    if not segments:
        return []

    # ------------------------------------------------------------------
    # 1. Flatten all endpoints; record (segment_idx, endpoint_idx 0|1)
    # ------------------------------------------------------------------
    n_segs = len(segments)
    # pts[i] = point for the i-th endpoint in flat order (2*seg + end)
    pts = np.empty((2 * n_segs, 2), dtype=np.float64)
    for i, (p0, p1) in enumerate(segments):
        pts[2 * i]     = p0
        pts[2 * i + 1] = p1

    # ------------------------------------------------------------------
    # 2. Build KDTree; find pairs within eps_snap_mm
    # ------------------------------------------------------------------
    tree = KDTree(pts)
    # query_ball_tree returns, for each point, indices of neighbours within r
    # Use r = eps_snap_mm (exclusive: only gaps strictly < eps snap)
    neighbour_lists = tree.query_ball_point(pts, r=eps_snap_mm)

    # ------------------------------------------------------------------
    # 3. Union-Find: cluster all endpoints within eps_snap_mm
    # ------------------------------------------------------------------
    parent = list(range(2 * n_segs))

    def _find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]  # path compression
            x = parent[x]
        return x

    def _union(a: int, b: int) -> None:
        ra, rb = _find(a), _find(b)
        if ra != rb:
            # Always merge higher index into lower so root = first-encountered
            if ra < rb:
                parent[rb] = ra
            else:
                parent[ra] = rb

    for idx, neighbours in enumerate(neighbour_lists):
        for nb in neighbours:
            _union(idx, nb)

    # ------------------------------------------------------------------
    # 4. Snap: each cluster representative = lowest-index endpoint in cluster
    # ------------------------------------------------------------------
    # Build representative -> canonical coordinate (first-encountered)
    rep_coord: dict[int, Point2D] = {}
    snapped_pts: list[Point2D] = []
    for i in range(2 * n_segs):
        rep = _find(i)
        if rep not in rep_coord:
            rep_coord[rep] = (float(pts[i][0]), float(pts[i][1]))
        snapped_pts.append(rep_coord[rep])

    # ------------------------------------------------------------------
    # 5. Reconstruct segments with snapped coordinates
    # ------------------------------------------------------------------
    result: list[Segment] = []
    seen: set[tuple[Point2D, Point2D]] = set()
    for i in range(n_segs):
        p0 = snapped_pts[2 * i]
        p1 = snapped_pts[2 * i + 1]
        seg: Segment = (p0, p1)
        # ------------------------------------------------------------------
        # 6. De-duplicate coincident segments (both orientations)
        # ------------------------------------------------------------------
        canonical = (min(p0, p1), max(p0, p1))
        if canonical not in seen:
            seen.add(canonical)
            result.append(seg)

    return result

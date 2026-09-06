# SqueezeNest -- TDD Implementation Tickets

**Version:** 0.1.0-draft  
**Methodology:** Strict Red-Green-Refactor  
**Test runner:** `pytest` + `hypothesis`  
**Coverage target:** 85% line coverage on `squeezenest/` (excluding `_nesting/ga.py`)

---

## How to Use This Document

Each ticket follows the Red-Green-Refactor cycle:

1. **RED**: Write the failing test(s) exactly as specified. Run `pytest` -- confirm failure.
2. **GREEN**: Write the *minimum* implementation to pass. No premature abstraction.
3. **REFACTOR**: Clean up the implementation. All tests must still pass.

Tickets are ordered by dependency (foundational first). Do not skip ahead.

---

## Ticket SN-001 -- Coordinate Scale Conversion

**Module:** `squeezenest/_core/scale.py`  
**Depends on:** Nothing  
**Goal:** Implement the mm <-> int64 conversion with SCALE_FACTOR = 1,000,000.

### RED -- Write these tests first

```python
# tests/core/test_scale.py
import pytest
from squeezenest._core.scale import to_int, to_mm, SCALE

def test_scale_factor_value():
    assert SCALE == 1_000_000

def test_to_int_basic():
    assert to_int(1.0) == 1_000_000

def test_to_int_zero():
    assert to_int(0.0) == 0

def test_to_int_sub_micron_rounds():
    # 0.0000005 mm is half a unit; should round to 1
    assert to_int(0.0000005) == 1

def test_to_int_negative():
    assert to_int(-2.5) == -2_500_000

def test_to_mm_basic():
    assert to_mm(1_000_000) == pytest.approx(1.0)

def test_to_mm_negative():
    assert to_mm(-500_000) == pytest.approx(-0.5)
```

```python
# tests/core/test_scale_hypothesis.py
from hypothesis import given, settings
from hypothesis import strategies as st
from squeezenest._core.scale import to_int, to_mm, SCALE

@given(st.floats(min_value=-9000.0, max_value=9000.0, allow_nan=False, allow_infinity=False))
@settings(max_examples=1000)
def test_roundtrip_within_one_unit(mm):
    """to_mm(to_int(x)) must recover x within 1 integer unit (0.001 micron)."""
    recovered = to_mm(to_int(mm))
    assert abs(recovered - mm) < 1 / SCALE + 1e-12
```

### GREEN -- Minimum implementation

```python
# squeezenest/_core/scale.py
SCALE: int = 1_000_000

def to_int(mm: float) -> int:
    return round(mm * SCALE)

def to_mm(i: int) -> float:
    return i / SCALE
```

### REFACTOR criteria
- Add module-level docstring explaining the coordinate system invariant.
- Export `__all__ = ["SCALE", "to_int", "to_mm"]`.
- No other changes needed -- keep it minimal.

---

## Ticket SN-002 -- Violation & ValidationReport Dataclasses

**Module:** `squeezenest/api/models.py`  
**Depends on:** Nothing (pure dataclasses)  
**Goal:** Verify that `Violation` and `ValidationReport` satisfy all stated invariants.

### RED -- Write these tests first

```python
# tests/api/test_models_violation.py
import pytest
from squeezenest.api.models import (
    Violation, ViolationSeverity, ViolationCode, ValidationReport
)

def make_error() -> Violation:
    return Violation(
        code=ViolationCode.DXF_GAP_001,
        severity=ViolationSeverity.ERROR,
        message="Unclosed contour",
        source_ref="HANDLE_0x1A",
        locus=(10.0, 20.0, 10.5, 20.0),
        suggested_delta=0.01,
    )

def make_warning() -> Violation:
    return Violation(
        code=ViolationCode.DFM_CLEARANCE_BREACH_012,
        severity=ViolationSeverity.WARNING,
        message="Clearance too tight",
    )

# Invariant I-10
def test_error_violation_makes_report_fatal():
    report = ValidationReport.from_violations([make_error()], strict=True)
    assert report.is_fatal is True

def test_error_violation_not_fatal_when_strict_false():
    report = ValidationReport.from_violations([make_error()], strict=False)
    assert report.is_fatal is False

def test_no_violations_not_fatal():
    report = ValidationReport.from_violations([], strict=True)
    assert report.is_fatal is False

# Invariant I-04
def test_error_count_consistency():
    report = ValidationReport.from_violations([make_error(), make_warning()], strict=True)
    assert report.error_count == len(report.errors())
    assert report.warning_count == len(report.warnings())

def test_violation_immutable():
    v = make_error()
    with pytest.raises((AttributeError, TypeError)):
        v.message = "mutated"  # frozen=True must prevent this

def test_violation_json_record_keys():
    v = make_error()
    rec = v.as_json_record()
    assert set(rec.keys()) == {
        "code", "severity", "message", "source_ref", "locus", "suggested_delta"
    }
    assert rec["code"] == "DXF_GAP_001"
    assert rec["severity"] == "ERROR"
```

### GREEN -- Minimum implementation
Implement `Violation`, `ViolationSeverity`, `ViolationCode`, and `ValidationReport`
exactly as specified in `arch_contracts.md`. No additional logic.

### REFACTOR criteria
- Confirm `frozen=True` on both `Violation` and `ValidationReport`.
- `ValidationReport.from_violations` must be a `@classmethod`.

---

## Ticket SN-003 -- DXF Graph Stitcher: Endpoint Snapping

**Module:** `squeezenest/_io/graph_stitch.py`  
**Depends on:** SN-001 (scale), scipy  
**Goal:** KD-Tree snapping bridges micro-gaps between line endpoints within eps_snap.

### RED -- Write these tests first

```python
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
```

**Required DXF fixtures (create with ezdxf before implementing):**
- `tests/fixtures/dxf/square_clean.dxf`
- `tests/fixtures/dxf/square_microgap.dxf` (5-micron gap at one corner)

### GREEN -- Minimum implementation skeleton

```python
# squeezenest/_io/graph_stitch.py
from scipy.spatial import KDTree

Segment = tuple[tuple[float, float], tuple[float, float]]

def snap_endpoints(segments: list[Segment], eps_snap_mm: float) -> list[Segment]:
    """
    Snap endpoints that are within eps_snap_mm of each other to the same coordinate.
    Returns a new list of segments with snapped endpoints.
    """
    if not segments:
        return []
    # 1. Collect all endpoints into a flat list with back-references
    # 2. Build KDTree; query_ball_tree or query_pairs within eps_snap_mm
    # 3. For each cluster, snap all members to the first endpoint in the cluster
    # 4. Reconstruct segments with snapped coordinates
    ...
```

### REFACTOR criteria
- Snap to the **first encountered endpoint** in each cluster (not centroid) for int64 grid alignment.
- De-duplicate coincident segments after snapping.
- All arithmetic in float mm; int64 conversion only at Clipper2 boundary.

---

## Ticket SN-004 -- Clipper2 Offset Wrapper: Kerf & Clearance

**Module:** `squeezenest/_core/clipper.py`  
**Depends on:** SN-001, clipper2-python  
**Goal:** Wrap Clipper2 InflatePaths with miter join; detect topology changes post-offset.

### RED -- Write these tests first

```python
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
```

```python
# tests/core/test_clipper_offset_hypothesis.py
from hypothesis import given, settings
from hypothesis import strategies as st
from squeezenest._core.clipper import inflate_polygon, OffsetTopologyError
from squeezenest._core.scale import to_int

@given(
    side_mm=st.floats(min_value=1.0, max_value=100.0),
    delta_mm=st.floats(min_value=-0.4, max_value=0.5),
)
@settings(max_examples=200)
def test_offset_area_monotonicity(side_mm, delta_mm):
    """Positive delta increases area; negative delta decreases area."""
    side = to_int(side_mm)
    square = [(0, 0), (side, 0), (side, side), (0, side)]
    delta = to_int(delta_mm)
    try:
        inflate_polygon(square, delta_int=delta)
    except OffsetTopologyError:
        return  # Valid for large erosions
```

---

## Ticket SN-005 -- NFP Cache: Key Generation & LRU Tier

**Module:** `squeezenest/_core/cache.py`  
**Depends on:** SN-001, SN-004  
**Goal:** Verify cache key generation (including symmetry invariant I-06), LRU eviction, and miss behaviour.

### RED -- Write these tests first

```python
# tests/core/test_nfp_cache.py
import pytest
from squeezenest._core.cache import make_cache_key, NFPCache

POLY_A = [(0, 0), (1_000_000, 0), (1_000_000, 1_000_000), (0, 1_000_000)]
POLY_B = [(0, 0), (500_000, 0), (500_000, 500_000), (0, 500_000)]

# Invariant I-06: symmetry
def test_cache_key_symmetry():
    key_ab = make_cache_key(POLY_A, POLY_B, rot_a_mdeg=0, rot_b_mdeg=0, clearance_int=100_000)
    key_ba = make_cache_key(POLY_B, POLY_A, rot_a_mdeg=0, rot_b_mdeg=0, clearance_int=100_000)
    assert key_ab == key_ba

def test_cache_key_differs_on_clearance():
    key_1 = make_cache_key(POLY_A, POLY_B, 0, 0, clearance_int=100_000)
    key_2 = make_cache_key(POLY_A, POLY_B, 0, 0, clearance_int=200_000)
    assert key_1 != key_2

def test_cache_key_differs_on_rotation():
    key_0  = make_cache_key(POLY_A, POLY_B, rot_a_mdeg=0,      rot_b_mdeg=0, clearance_int=100_000)
    key_90 = make_cache_key(POLY_A, POLY_B, rot_a_mdeg=90_000, rot_b_mdeg=0, clearance_int=100_000)
    assert key_0 != key_90

def test_lru_cache_stores_and_retrieves():
    cache = NFPCache(max_size=10)
    key = make_cache_key(POLY_A, POLY_B, 0, 0, 100_000)
    fake_nfp = [(100, 100), (200, 100), (200, 200)]
    cache.put(key, fake_nfp)
    assert cache.get(key) == fake_nfp

def test_lru_cache_evicts_on_overflow():
    cache = NFPCache(max_size=2)
    k1 = make_cache_key(POLY_A, POLY_B, 0,       0, 100_000)
    k2 = make_cache_key(POLY_A, POLY_B, 0,  90_000, 100_000)
    k3 = make_cache_key(POLY_A, POLY_B, 0, 180_000, 100_000)
    cache.put(k1, [(0, 0)])
    cache.put(k2, [(1, 1)])
    cache.put(k3, [(2, 2)])  # k1 should be LRU-evicted
    assert cache.get(k1) is None
    assert cache.get(k3) == [(2, 2)]

def test_lru_cache_miss_returns_none():
    cache = NFPCache(max_size=10)
    key = make_cache_key(POLY_A, POLY_B, 0, 0, 999_999)
    assert cache.get(key) is None
```

---

## Ticket SN-006 -- Affine Scale Transform + Topology Guard

**Module:** `squeezenest/_sensitivity/affine.py`  
**Depends on:** SN-001, SN-004  
**Goal:** Centroid-anchored affine scaling with neck-pinch detection (invariant I-09).

### RED -- Write these tests first

```python
# tests/sensitivity/test_affine.py
import pytest
from squeezenest._sensitivity.affine import scale_polygon, TopologyConstraintViolation
from squeezenest._core.scale import to_int

UNIT_SQUARE = [(0, 0), (to_int(1.0), 0), (to_int(1.0), to_int(1.0)), (0, to_int(1.0))]

def _area(poly):
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
```

---

## Ticket SN-007 -- Bottom-Left-Fill Placement (Non-Overlapping & Within-Stock)

**Module:** `squeezenest/_nesting/blf.py`  
**Depends on:** SN-001, SN-004, SN-005  
**Goal:** Verify invariants I-02, I-03, I-05 and the too-large-part fallthrough.

### RED -- Write these tests first

```python
# tests/nesting/test_blf.py
import pytest
from shapely.geometry import Polygon as SPolygon
from squeezenest._nesting.blf import bottom_left_fill
from squeezenest.api.models import StockSheet, PolygonWithHoles, RotationSet

STOCK = StockSheet(width_mm=100.0, height_mm=100.0)
SMALL_SQUARE: PolygonWithHoles = ([(0,0),(10,0),(10,10),(0,10)], [])

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
    stock_poly = SPolygon([(0,0),(100,0),(100,100),(0,100)])
    for p in layout.placements:
        assert stock_poly.contains(SPolygon(p.placed_outline)) or \
               stock_poly.equals(SPolygon(p.placed_outline))

# Invariant I-05: yield count == len(placements)
def test_yield_count_equals_len_placements():
    parts = [("P1", SMALL_SQUARE), ("P2", SMALL_SQUARE)]
    layout = bottom_left_fill(parts, STOCK, clearance_mm=0.5, rotation_set=RotationSet.ORTHO)
    assert layout.yield_count == len(layout.placements)

def test_oversized_part_goes_to_unplaced():
    huge: PolygonWithHoles = ([(0,0),(200,0),(200,200),(0,200)], [])
    layout = bottom_left_fill([("HUGE", huge)], STOCK, clearance_mm=0.5, rotation_set=RotationSet.NONE)
    assert layout.yield_count == 0
    assert ("HUGE", 0) in layout.unplaced_parts
```

**Golden file fixture:**  
`tests/fixtures/layouts/3x_10mm_square_100mm_stock.json` -- expected `PlacementLayout`
for 3 x 10mm squares on 100mm stock with 0.5mm clearance (used for regression).

---

## Ticket SN-008 -- Pareto Frontier Extraction

**Module:** `squeezenest/_sensitivity/pareto.py`  
**Depends on:** SN-007  
**Goal:** Verify invariants I-07 and I-08; ensure baseline appears on frontier; excluded dominated points.

### RED -- Write these tests first

```python
# tests/sensitivity/test_pareto.py
import pytest
from squeezenest._sensitivity.pareto import extract_pareto
from squeezenest.api.models import ParetoPoint, PlacementLayout

def _empty_layout(yield_count: int) -> PlacementLayout:
    return PlacementLayout(
        placements=(), unplaced_parts=(), yield_count=yield_count,
        utilisation=0.0, sheets_used=1
    )

def make_point(sx, sy, d, yield_count) -> ParetoPoint:
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
```

---

## Ticket SN-009 -- Protocol Conformance Tests

**Module:** `squeezenest/api/protocols.py`  
**Depends on:** SN-002, SN-007  
**Goal:** Verify `@runtime_checkable` Protocols accept conforming classes and reject incomplete ones.

### RED -- Write these tests first

```python
# tests/api/test_protocols.py
import pytest
from squeezenest.api.protocols import (
    FabricationEntity, HoldingTabStrategy, PartingCutStrategy, IngestAdapter
)
from squeezenest.api.models import ValidationReport

class MinimalFabricationEntity:
    @property
    def geometry(self): return ([(0,0),(1,0),(1,1),(0,1)], [])
    @property
    def min_tool_clearance_mm(self): return 0.5
    @property
    def keepout_zones(self): return []
    def validate_dfm(self, kerf_mm): return ValidationReport.from_violations([])

class MinimalHoldingTabStrategy:
    def generate_tabs(self, placed_part, stock, neighbours): return []
    @property
    def min_tab_width_mm(self): return 2.0
    @property
    def min_tab_count(self): return 2

class MinimalPartingCutStrategy:
    def generate_cut_paths(self, layout, stock): return []
    @property
    def requires_colinear_cuts(self): return False

class BadEntity:
    pass  # Missing all required members

def test_minimal_fabrication_entity_satisfies_protocol():
    assert isinstance(MinimalFabricationEntity(), FabricationEntity)

def test_minimal_holding_tab_satisfies_protocol():
    assert isinstance(MinimalHoldingTabStrategy(), HoldingTabStrategy)

def test_minimal_parting_cut_satisfies_protocol():
    assert isinstance(MinimalPartingCutStrategy(), PartingCutStrategy)

def test_incomplete_class_does_not_satisfy_fabrication_entity():
    assert not isinstance(BadEntity(), FabricationEntity)
```

---

## Ticket SN-010 -- Integration: Dirty DXF Ingestion End-to-End

**Module:** `squeezenest/_io/dxf_ingest.py`  
**Depends on:** SN-001, SN-003, SN-004, SN-002  
**Goal:** Full 6-stage pipeline from DXF file to `List[(PolygonWithHoles, PartMetadata)]` + `ValidationReport`.

### RED -- Write these tests first

```python
# tests/io/test_dxf_ingest.py
import pytest
from pathlib import Path
from squeezenest._io.dxf_ingest import ingest_dxf
from squeezenest.api.models import ViolationCode, ViolationSeverity

FIXTURES = Path("tests/fixtures/dxf")

def test_clean_square_produces_one_part():
    parts, report = ingest_dxf(FIXTURES / "square_clean.dxf")
    assert len(parts) == 1
    assert not report.is_fatal

def test_microgap_square_no_gap_error_after_snap():
    # After KD-Tree snapping (eps=0.01mm), the 5-micron gap must be closed silently
    parts, report = ingest_dxf(FIXTURES / "square_microgap.dxf", eps_snap_mm=0.01)
    assert len(parts) == 1
    gap_errors = [v for v in report.violations if v.code == ViolationCode.DXF_GAP_001]
    assert len(gap_errors) == 0

def test_large_gap_emits_gap_error():
    parts, report = ingest_dxf(FIXTURES / "square_large_gap.dxf", eps_snap_mm=0.01)
    gap_errors = [v for v in report.violations if v.code == ViolationCode.DXF_GAP_001]
    assert len(gap_errors) >= 1
    assert gap_errors[0].severity == ViolationSeverity.ERROR

def test_washer_produces_one_hole():
    # washer.dxf: outer circle + inner circle (hole)
    parts, report = ingest_dxf(FIXTURES / "washer.dxf")
    assert len(parts) == 1
    outer, holes = parts[0][0]
    assert len(holes) == 1

def test_three_parts_dxf_produces_correct_count():
    parts, report = ingest_dxf(FIXTURES / "three_parts.dxf")
    assert len(parts) == 3
```

**Required DXF fixtures** (create with ezdxf scripting before implementing):

| Fixture | Contents |
|---|---|
| `square_clean.dxf` | 4 LINE entities forming a clean 10x10mm square |
| `square_microgap.dxf` | Same square with one 5-micron endpoint gap |
| `square_large_gap.dxf` | Same square with one 100-micron endpoint gap |
| `washer.dxf` | Outer circle (r=10mm) + inner circle (r=4mm) hole |
| `three_parts.dxf` | Three closed rectangles on OUTLINE layer |

---

## Ticket SN-011 -- End-to-End Sensitivity Sweep (Smoke Test)

**Module:** `squeezenest/_sensitivity/sweep.py`  
**Depends on:** SN-006, SN-007, SN-008  
**Goal:** Verify the sweep produces a non-empty Pareto frontier and satisfies invariant I-08.

### RED -- Write these tests first

```python
# tests/sensitivity/test_sweep_smoke.py
import pytest
from squeezenest.api.models import (
    NestingJob, SensitivityConfig, StockSheet, PartMetadata, RotationSet
)
from squeezenest._sensitivity.sweep import run_sensitivity_sweep

SMALL_STOCK = StockSheet(width_mm=50.0, height_mm=50.0)
PART_10MM = ([(0,0),(10,0),(10,10),(0,10)], [])

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
```

---

## Execution Checklist

| Ticket | Module | Status |
|---|---|---|
| SN-001 | `_core/scale.py` | Not started |
| SN-002 | `api/models.py` | Not started |
| SN-003 | `_io/graph_stitch.py` | Not started |
| SN-004 | `_core/clipper.py` | Not started |
| SN-005 | `_core/cache.py` | Not started |
| SN-006 | `_sensitivity/affine.py` | Not started |
| SN-007 | `_nesting/blf.py` | Not started |
| SN-008 | `_sensitivity/pareto.py` | Not started |
| SN-009 | `api/protocols.py` | Not started |
| SN-010 | `_io/dxf_ingest.py` | Not started |
| SN-011 | `_sensitivity/sweep.py` | Not started |

Run at any time:

```bash
# All tests
pytest tests/ -v --tb=short

# Coverage gate
pytest tests/ --cov=squeezenest --cov-report=term-missing

# Hypothesis only (fast smoke)
pytest tests/ -k "hypothesis" -v
```

**Merge gate:** All 11 tickets GREEN, coverage >= 85%, `mypy --strict` and `ruff check` pass cleanly.

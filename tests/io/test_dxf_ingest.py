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

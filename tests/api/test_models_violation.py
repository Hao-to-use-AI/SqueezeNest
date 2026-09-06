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

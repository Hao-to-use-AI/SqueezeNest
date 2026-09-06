"""Coordinate scale conversion: mm <-> int64 with SCALE_FACTOR = 1,000,000.

Invariant: every real-world mm coordinate is represented as an integer number
of micro-units where 1 unit = 1e-6 mm (= 1 nm). This avoids floating-point
drift through the Clipper2 / NFP pipeline.

Round-trip guarantee: to_mm(to_int(x)) recovers x within 1 integer unit
(0.001 micron = 1e-6 mm) for all x in [-9000, 9000] mm.
"""

import math

SCALE: int = 1_000_000

__all__ = ["SCALE", "to_int", "to_mm"]


def to_int(mm: float) -> int:
    """Convert millimetres to int64 scale units (round-half-up)."""
    # Use math.floor(x + 0.5) to get deterministic round-half-up semantics,
    # avoiding Python 3 banker's rounding (round-half-to-even).
    return math.floor(mm * SCALE + 0.5)


def to_mm(i: int) -> float:
    """Convert int64 scale units back to millimetres."""
    return i / SCALE

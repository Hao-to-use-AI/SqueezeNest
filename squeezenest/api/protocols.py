"""squeezenest.api.protocols -- Runtime-checkable Protocol interfaces (SPI).

Extension authors implement these Protocols to integrate domain-specific
fabrication logic without modifying internal engine types.

Stability: Public SPI -- stable per SemVer.
Do NOT import squeezenest._* symbols in implementations.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable, Sequence
from pathlib import Path
from squeezenest.api.models import (
    PolygonWithHoles, Polygon, PlacedPart, PlacementLayout,
    StockSheet, ValidationReport, PartMetadata,
)


@runtime_checkable
class FabricationEntity(Protocol):
    """
    Protocol implemented by any domain-specific part wrapper
    (CNC routing, sheet metal, composite cutting, etc.).

    Stability: Public SPI -- stable per SemVer.
    """

    @property
    def geometry(self) -> PolygonWithHoles:
        """The part's outer boundary and interior holes (mm, floating-point)."""
        ...

    @property
    def min_tool_clearance_mm(self) -> float:
        """Minimum required clearance between this part and any neighbour."""
        ...

    @property
    def keepout_zones(self) -> list[Polygon]:
        """Additional exclusion polygons attached to this part."""
        ...

    def validate_dfm(self, kerf_mm: float) -> ValidationReport:
        """Run domain-specific DFM checks for this entity at the given kerf."""
        ...


@runtime_checkable
class HoldingTabStrategy(Protocol):
    """
    Protocol for strategies that generate structural holding tabs (bridges).

    Stability: Public SPI -- stable per SemVer.
    """

    def generate_tabs(
        self,
        placed_part: PlacedPart,
        stock: StockSheet,
        neighbours: Sequence[PlacedPart],
    ) -> list[Polygon]:
        """Compute tab geometries for a placed part."""
        ...

    @property
    def min_tab_width_mm(self) -> float:
        """Minimum tab width -- must not be less than the tool kerf width."""
        ...

    @property
    def min_tab_count(self) -> int:
        """Minimum number of tabs required per part."""
        ...


@runtime_checkable
class PartingCutStrategy(Protocol):
    """
    Protocol for strategies that generate parting / separation cut paths.

    Stability: Public SPI -- stable per SemVer.
    """

    def generate_cut_paths(
        self,
        layout: PlacementLayout,
        stock: StockSheet,
    ) -> list[list[tuple[float, float]]]:
        """Compute ordered cut paths for the complete layout."""
        ...

    @property
    def requires_colinear_cuts(self) -> bool:
        """If True, all cut paths must be straight lines spanning the full sheet."""
        ...


@runtime_checkable
class IngestAdapter(Protocol):
    """
    Protocol for custom geometry ingestion adapters.

    Stability: Public SPI -- stable per SemVer.
    """

    def can_handle(self, source_path: Path) -> bool:
        """Return True if this adapter can ingest the given file."""
        ...

    def ingest(
        self,
        source_path: Path,
        eps_snap_mm: float = 0.01,
        strict_layers: bool = False,
    ) -> tuple[list[tuple[PolygonWithHoles, PartMetadata]], ValidationReport]:
        """Parse source_path and return parts + ValidationReport."""
        ...


__all__ = [
    "FabricationEntity",
    "HoldingTabStrategy",
    "PartingCutStrategy",
    "IngestAdapter",
]

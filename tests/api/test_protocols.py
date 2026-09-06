# tests/api/test_protocols.py
import pytest
from squeezenest.api.protocols import (
    FabricationEntity, HoldingTabStrategy, PartingCutStrategy, IngestAdapter
)
from squeezenest.api.models import ValidationReport


class MinimalFabricationEntity:
    @property
    def geometry(self):
        return ([(0, 0), (1, 0), (1, 1), (0, 1)], [])

    @property
    def min_tool_clearance_mm(self):
        return 0.5

    @property
    def keepout_zones(self):
        return []

    def validate_dfm(self, kerf_mm):
        return ValidationReport.from_violations([])


class MinimalHoldingTabStrategy:
    def generate_tabs(self, placed_part, stock, neighbours):
        return []

    @property
    def min_tab_width_mm(self):
        return 2.0

    @property
    def min_tab_count(self):
        return 2


class MinimalPartingCutStrategy:
    def generate_cut_paths(self, layout, stock):
        return []

    @property
    def requires_colinear_cuts(self):
        return False


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

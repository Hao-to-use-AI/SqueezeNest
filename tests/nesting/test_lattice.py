import pytest
from shapely.geometry import Polygon as SPolygon
from squeezenest._nesting.lattice import find_best_cluster, tile_cluster, run_lattice_job
from squeezenest.api.models import StockSheet, RotationSet, NestingJob, PartMetadata, NestingStrategy
from squeezenest._nesting.blf import run_nesting_job as run_blf_job

STOCK = StockSheet(width_mm=100.0, height_mm=100.0)
# L-shape: 10x10 with a 5x5 cutout
L_SHAPE = ([(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (5.0, 5.0), (5.0, 10.0), (0.0, 10.0)], [])
SMALL_SQUARE = ([(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)], [])

def test_cluster_pair_l_shape():
    outer = L_SHAPE[0]
    rotations = [0.0, 90.0, 180.0, 270.0]
    best_b_poly, b_dx, b_dy, b_angle, c_min_x, c_min_y, c_max_x, c_max_y = find_best_cluster(outer, rotations, clearance_mm=0.0)
    
    bbox_area = (c_max_x - c_min_x) * (c_max_y - c_min_y)
    # The bounding box of two interlocking L-shapes should be <= 150
    assert bbox_area <= 150.0

def test_cluster_chooses_tightest_rotation():
    outer = L_SHAPE[0]
    # Restrict to 0 to force a bad interlock
    _, _, _, _, bad_min_x, bad_min_y, bad_max_x, bad_max_y = find_best_cluster(outer, [0.0], clearance_mm=0.0)
    bad_area = (bad_max_x - bad_min_x) * (bad_max_y - bad_min_y)
    
    # Allow 180 which should interlock perfectly
    _, _, _, _, good_min_x, good_min_y, good_max_x, good_max_y = find_best_cluster(outer, [0.0, 180.0], clearance_mm=0.0)
    good_area = (good_max_x - good_min_x) * (good_max_y - good_min_y)
    
    assert good_area < bad_area

def test_tile_axis_aligned_no_overflow():
    positions = tile_cluster(10.0, 10.0, STOCK, clearance_mm=1.0)
    for x, y in positions:
        assert 1.0 <= x <= 100.0 - 10.0 - 1.0 + 1e-9
        assert 1.0 <= y <= 100.0 - 10.0 - 1.0 + 1e-9

def test_no_overlapping_lattice_placements():
    job = NestingJob(
        parts={"P1": (SMALL_SQUARE, PartMetadata("P1", quantity=20))},
        stock=[STOCK],
        clearance_mm=1.0,
        rotation_set=RotationSet.ORTHO,
        strategy=NestingStrategy.LATTICE
    )
    result = job.run()
    polys = [SPolygon(p.placed_outline).buffer(0.5, quad_segs=2) for p in result.layout.placements]
    
    for i in range(len(polys)):
        for j in range(i + 1, len(polys)):
            assert polys[i].intersection(polys[j]).area < 1e-6

def test_yield_count_consistency_lattice():
    job = NestingJob(
        parts={"P1": (SMALL_SQUARE, PartMetadata("P1", quantity=5))},
        stock=[STOCK],
        clearance_mm=1.0,
        strategy=NestingStrategy.LATTICE
    )
    result = job.run()
    assert result.layout.yield_count == len(result.layout.placements)

def test_odd_quantity_remainder_placed_by_blf():
    job = NestingJob(
        parts={"P1": (SMALL_SQUARE, PartMetadata("P1", quantity=51))},
        stock=[STOCK],
        clearance_mm=1.0,
        strategy=NestingStrategy.LATTICE
    )
    result = job.run()
    # 51 small squares easily fit on a 100x100 stock. 50 will be paired and tiled. 1 will be BLF.
    assert result.layout.yield_count == 51
    assert len(result.layout.unplaced_parts) == 0

def test_lattice_utilisation_exceeds_blf():
    # 40 L-shapes on a 100x100 board.
    # BLF will leave gaps. Lattice should pack them better.
    job_lattice = NestingJob(
        parts={"L": (L_SHAPE, PartMetadata("L", quantity=40))},
        stock=[STOCK],
        clearance_mm=1.0,
        rotation_set=RotationSet.ORTHO,
        strategy=NestingStrategy.LATTICE
    )
    res_lat = job_lattice.run()
    
    job_blf = NestingJob(
        parts={"L": (L_SHAPE, PartMetadata("L", quantity=40))},
        stock=[STOCK],
        clearance_mm=1.0,
        rotation_set=RotationSet.ORTHO,
        strategy=NestingStrategy.BLF
    )
    res_blf = job_blf.run()
    
    assert res_lat.layout.utilisation >= res_blf.layout.utilisation

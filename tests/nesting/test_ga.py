from squeezenest.api.models import NestingJob, StockSheet, PartMetadata, RotationSet, NestingStrategy
from squeezenest._nesting.ga import run_ga_job

def test_ga_nesting_fallback():
    # Test that GA runs without crashing
    l_shape = (
        [(0.0, 0.0), (30.0, 0.0), (30.0, 15.0), (15.0, 15.0), (15.0, 30.0), (0.0, 30.0)],
        [] 
    )
    job_parts = {
        "P1": (l_shape, PartMetadata(part_id="P1", quantity=1)),
        "P2": (l_shape, PartMetadata(part_id="P2", quantity=1))
    }
    
    job = NestingJob(
        parts=job_parts,
        stock=[StockSheet(width_mm=100.0, height_mm=100.0)],
        clearance_mm=1.0,
        rotation_set=RotationSet.ORTHO,
        strategy=NestingStrategy.GA,
        beam_width=2
    )
    
    result = run_ga_job(job)
    assert result.layout.yield_count > 0

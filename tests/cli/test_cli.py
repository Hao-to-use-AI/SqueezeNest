from typer.testing import CliRunner
from squeezenest.cli import app
from pathlib import Path

runner = CliRunner()

def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "General-purpose 2D irregular nesting" in result.stdout

def test_cli_nest_missing_file():
    result = runner.invoke(app, ["nest", "non_existent.dxf", "--width", "100", "--height", "100"])
    assert result.exit_code == 1
    assert "Error: File non_existent.dxf not found." in result.output

def test_cli_nest_invalid_strategy(tmp_path, monkeypatch):
    dxf_file = tmp_path / "dummy.dxf"
    dxf_file.touch()
    
    # Mock ingest_dxf to return empty parts and a non-fatal report
    from squeezenest.api.models import ValidationReport
    monkeypatch.setattr("squeezenest._io.dxf_ingest.ingest_dxf", lambda f, eps_snap_mm: ([], ValidationReport(violations=(), error_count=0, warning_count=0, is_fatal=False)))
    
    result = runner.invoke(app, ["nest", str(dxf_file), "--width", "100", "--height", "100", "--strategy", "invalid"])
    assert result.exit_code == 1
    assert "Invalid strategy: invalid" in result.output

# In a real scenario we would mock the ingest_dxf or provide a valid minimal DXF file 
# for a full end-to-end test.

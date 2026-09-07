"""Unit tests for demo server security controls and risk mitigations (80/20 rule)."""
from __future__ import annotations

import base64
import json
import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import ezdxf

from demo.server import (
    PanelizerHandler,
    _sanitize_filename,
    _normalize_dxf_document,
    MAX_REQUEST_BODY_BYTES,
    MAX_FILES_PER_REQUEST,
    MAX_DXF_FILE_BYTES,
    MAX_DXF_ENTITIES,
    MIN_PANEL_DIM_MM,
    MAX_PANEL_DIM_MM,
    MAX_TIMEOUT_SEC,
    FIXTURES_DIR,
)


class TestDemoSecurity:
    """Test suite for 80/20 security protections on demo server."""

    def test_sanitize_filename_traversal(self) -> None:
        """Path traversal characters should be completely stripped."""
        assert _sanitize_filename("../../etc/passwd") == "passwd.dxf"
        assert _sanitize_filename("../../../secret.dxf") == "secret.dxf"
        assert _sanitize_filename("/absolute/path/to/board.dxf") == "board.dxf"
        assert _sanitize_filename(".hidden.dxf") == "hidden.dxf"
        assert _sanitize_filename("valid_board_123.dxf") == "valid_board_123.dxf"
        assert _sanitize_filename("") == "part.dxf"
        assert _sanitize_filename("board\x00malicious.dxf") == "boardmalicious.dxf"
        assert _sanitize_filename("board_name") == "board_name.dxf"

    def test_entity_count_limit_exceeded(self) -> None:
        """DXF documents exceeding entity safety limit should be rejected."""
        doc = MagicMock(spec=ezdxf.document.Drawing)
        mock_msp = MagicMock()
        mock_msp.__len__.return_value = MAX_DXF_ENTITIES + 1
        doc.modelspace.return_value = mock_msp

        with pytest.raises(ValueError, match="exceeds maximum safety limit"):
            _normalize_dxf_document(doc)

    def test_entity_count_within_limit(self) -> None:
        """Standard DXF documents within entity limit should pass normalization."""
        doc = ezdxf.new("R2010")
        msp = doc.modelspace()
        msp.add_line((0, 0), (10, 10))
        stats = _normalize_dxf_document(doc)
        assert "original_entities" in stats
        assert stats["original_entities"].get("LINE", 0) == 1

    def test_payload_too_large_rejection(self) -> None:
        """Requests larger than MAX_REQUEST_BODY_BYTES should be rejected with 413."""
        handler = MagicMock(spec=PanelizerHandler)
        handler.headers = {"Content-Length": str(MAX_REQUEST_BODY_BYTES + 1024)}
        handler._send_json = MagicMock()

        PanelizerHandler._handle_optimize(handler)
        handler._send_json.assert_called_once()
        status, data = handler._send_json.call_args[0]
        assert status == 413
        assert "Payload too large" in data["error"]

    def test_too_many_files_rejection(self) -> None:
        """Requests with more files than MAX_FILES_PER_REQUEST should be rejected with 400."""
        handler = MagicMock(spec=PanelizerHandler)
        files = [{"filename": f"f{i}.dxf", "content_base64": ""} for i in range(MAX_FILES_PER_REQUEST + 1)]
        payload = json.dumps({
            "panel_width_mm": 100,
            "panel_height_mm": 100,
            "files": files,
        }).encode("utf-8")

        handler.headers = {"Content-Length": str(len(payload))}
        handler.rfile = io.BytesIO(payload)
        handler._send_json = MagicMock()

        PanelizerHandler._handle_optimize(handler)
        handler._send_json.assert_called_once()
        status, data = handler._send_json.call_args[0]
        assert status == 400
        assert "Too many files" in data["error"]

    def test_oversized_individual_file_rejection(self) -> None:
        """An individual DXF exceeding MAX_DXF_FILE_BYTES should be rejected."""
        handler = MagicMock(spec=PanelizerHandler)
        # Create a payload claiming a file with > MAX_DXF_FILE_BYTES
        dummy_data = b"0" * (MAX_DXF_FILE_BYTES + 1024)
        b64_data = base64.b64encode(dummy_data).decode("ascii")
        payload = json.dumps({
            "panel_width_mm": 100,
            "panel_height_mm": 100,
            "files": [{"filename": "huge.dxf", "content_base64": b64_data}],
        }).encode("utf-8")

        handler.headers = {"Content-Length": str(len(payload))}
        handler.rfile = io.BytesIO(payload)
        handler._send_json = MagicMock()

        PanelizerHandler._handle_optimize(handler)
        handler._send_json.assert_called_once()
        status, data = handler._send_json.call_args[0]
        assert status == 400
        assert "exceeds" in data["error"] and "MB limit" in data["error"]

    def test_sample_dxf_path_traversal_blocked(self) -> None:
        """Attempting to access files outside FIXTURES_DIR via query must return 404."""
        handler = MagicMock(spec=PanelizerHandler)
        handler._send_json = MagicMock()

        PanelizerHandler._handle_get_sample_dxf(handler, {"name": ["../../README.md"]})
        handler._send_json.assert_called_once()
        status, data = handler._send_json.call_args[0]
        assert status == 404
        assert "not found" in data["error"].lower()

    def test_cors_origin_restriction(self) -> None:
        """CORS should only echo back localhost or 127.0.0.1 origins, not arbitrary external origins."""
        handler = MagicMock(spec=PanelizerHandler)
        handler.headers = {"Origin": "http://evil-attacker.com"}
        handler.wfile = io.BytesIO()

        PanelizerHandler._send_json(handler, 200, {"status": "ok"})
        headers_sent = [call[0] for call in handler.send_header.call_args_list]
        header_keys = [h[0] for h in headers_sent]
        header_vals = [h[1] for h in headers_sent]
        
        # Evil attacker origin should NOT be granted Access-Control-Allow-Origin
        assert "http://evil-attacker.com" not in header_vals
        assert "Access-Control-Allow-Origin" not in header_keys

        # Now test with localhost origin
        handler.reset_mock()
        handler.headers = {"Origin": "http://localhost:3000"}
        PanelizerHandler._send_json(handler, 200, {"status": "ok"})
        headers_sent = [call[0] for call in handler.send_header.call_args_list]
        assert ("Access-Control-Allow-Origin", "http://localhost:3000") in headers_sent

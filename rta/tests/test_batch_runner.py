"""
Tests for the Batch Runner module.
"""

import pytest
from batch_runner import (
    find_sdc_files, BatchResult, BatchSummary,
    batch_check, batch_report, batch_lint,
)


class TestFindSdcFiles:
    """Tests for SDC file discovery."""

    def test_find_in_nonexistent_dir(self):
        with pytest.raises(FileNotFoundError):
            find_sdc_files("/nonexistent/path")

    def test_find_in_file(self, sample_sdc_path):
        """Passing a file path raises NotADirectoryError."""
        import os
        d = os.path.dirname(sample_sdc_path)
        files = find_sdc_files(d)
        assert len(files) > 0
        assert all(f.endswith(".sdc") for f in files)


class TestBatchResult:
    """Tests for the BatchResult dataclass."""

    def test_create_ok(self):
        r = BatchResult(filepath="test.sdc", status="ok", message="All good")
        assert r.status == "ok"

    def test_create_error(self):
        r = BatchResult(filepath="test.sdc", status="error", message="Failed")
        assert r.status == "error"


class TestBatchSummary:
    """Tests for the BatchSummary dataclass."""

    def test_empty_summary(self):
        s = BatchSummary()
        assert s.total == 0

    def test_print_summary(self):
        s = BatchSummary(total=5, ok=3, errors=1, skipped=1)
        text = s.print_summary()
        assert "5" in text
        assert "3" in text
        assert "1" in text


class TestBatchCheck:
    """Tests for batch check."""

    def test_batch_check_directory(self, tmp_path):
        """Create a temp dir with one SDC file and run batch check."""
        d = tmp_path / "sdcs"
        d.mkdir()
        sdc_file = d / "test.sdc"
        sdc_file.write_text("create_clock -name clk -period 5.0 [get_ports clk]")
        summary = batch_check(str(d))
        assert summary.total >= 1
        assert summary.ok + summary.errors == summary.total

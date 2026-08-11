"""
Tests for the SDC Converter module.
"""

import json
import pytest
from converter import (
    parse_sdc, sdc_to_json, sdc_to_yaml,
    ParsedSDC, ParsedClock,
)


class TestParseSdc:
    """Tests for the SDC parser."""

    def test_parse_empty(self):
        result = parse_sdc("", "empty.sdc")
        assert isinstance(result, ParsedSDC)
        assert result.filename == "empty.sdc"
        assert result.clocks_count == 0

    def test_parse_minimal(self, minimal_sdc):
        result = parse_sdc(minimal_sdc)
        assert "2.2" in result.sdc_version
        assert result.clocks_count >= 1

    def test_parse_full(self, full_sdc):
        result = parse_sdc(full_sdc)
        assert result.clocks_count >= 3  # primary + generated + virtual
        assert len(result.false_paths) >= 1
        assert len(result.multicycle_paths) >= 1

    def test_parse_clock_details(self, full_sdc):
        result = parse_sdc(full_sdc)
        clocks = [c for c in result.clocks if not c.is_generated]
        if clocks:
            assert clocks[0].period > 0

    def test_parse_generated_clock(self, full_sdc):
        result = parse_sdc(full_sdc)
        gen_clocks = [c for c in result.clocks if c.is_generated]
        assert len(gen_clocks) >= 1

    def test_parse_input_delays(self, full_sdc):
        result = parse_sdc(full_sdc)
        assert len(result.input_delays) >= 1

    def test_parse_output_delays(self, full_sdc):
        result = parse_sdc(full_sdc)
        assert len(result.output_delays) >= 1

    def test_parse_clock_groups(self, full_sdc):
        result = parse_sdc(full_sdc)
        assert len(result.clock_groups) >= 1

    def test_parse_case_analysis(self, full_sdc):
        result = parse_sdc(full_sdc)
        assert len(result.case_analysis) >= 1

    def test_parse_timing_derate(self, full_sdc):
        result = parse_sdc(full_sdc)
        assert len(result.timing_derate) >= 2  # late + early

    def test_to_dict_serializable(self, full_sdc):
        result = parse_sdc(full_sdc)
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "clocks" in d
        assert "false_paths" in d


class TestSdcToJson:
    """Tests for JSON output."""

    def test_to_json(self, full_sdc):
        json_str = sdc_to_json(full_sdc)
        data = json.loads(json_str)
        assert "clocks" in data
        assert "clocks_count" in data

    def test_to_json_parseable(self, full_sdc):
        json_str = sdc_to_json(full_sdc)
        assert json_str.startswith("{")
        data = json.loads(json_str)
        assert data["clocks_count"] > 0


class TestSdcToYaml:
    """Tests for YAML output."""

    def test_to_yaml(self, full_sdc):
        yaml_str = sdc_to_yaml(full_sdc)
        assert isinstance(yaml_str, str)
        assert len(yaml_str) > 0
        # Should contain keys from the parsed SDC
        assert "clocks" in yaml_str or "filename" in yaml_str

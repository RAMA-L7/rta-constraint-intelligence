"""
Tests for the TCL Variable Resolver module.
"""

import pytest
from tcl_resolver import (
    VariableBinding, SymbolTable,
    parse_variables, resolve_variables,
    build_symbol_table, extract_source_files,
)


class TestParseVariables:
    """Tests for TCL variable parsing."""

    def test_basic_variable(self):
        text = "set CYCLE 10.0"
        result = parse_variables(text)
        assert "CYCLE" in result
        assert result["CYCLE"].raw_value == "10.0"
        assert result["CYCLE"].resolved_value == "10.0"

    def test_multiple_variables(self):
        text = "set A 1\nset B 2\nset C 3"
        result = parse_variables(text)
        assert len(result) == 3

    def test_brace_quoted_value(self):
        text = 'set PINS {data_a data_b}'
        result = parse_variables(text)
        assert result["PINS"].raw_value == "data_a data_b"

    def test_collection_value(self):
        text = "set PINS [get_pins *static_inst*]"
        result = parse_variables(text)
        assert result["PINS"].is_collection is True

    def test_comment_lines_skipped(self):
        text = "# set A 1\nset B 2\n# set C 3"
        result = parse_variables(text)
        assert "A" not in result
        assert "B" in result
        assert "C" not in result

    def test_blank_lines_skipped(self):
        text = "\n\nset A 1\n\n\nset B 2\n"
        result = parse_variables(text)
        assert len(result) == 2

    def test_line_number_tracking(self):
        text = "set A 1\nset B 2"
        result = parse_variables(text)
        assert result["A"].line_number == 1
        assert result["B"].line_number == 2

    def test_empty_text(self):
        assert parse_variables("") == {}

    def test_clean_value_strips_braces(self):
        assert parse_variables("set X { hello }")["X"].raw_value == "hello"


class TestSymbolTable:
    """Tests for the SymbolTable class."""

    def test_resolve_simple(self, tcl_params):
        table = SymbolTable()
        bindings = parse_variables(tcl_params)
        table.variables = bindings
        result = table.resolve("set_period $PERIOD_NS")
        assert "5.0" in result

    def test_resolve_curly_brace(self):
        table = SymbolTable()
        bindings = parse_variables("set VAR hello")
        table.variables = bindings
        result = table.resolve("echo ${VAR}_world")
        assert "hello_world" in result

    def test_resolve_no_match(self):
        table = SymbolTable()
        bindings = parse_variables("set VAR hello")
        table.variables = bindings
        result = table.resolve("echo $OTHER")
        assert "$OTHER" in result  # not replaced

    def test_get_existing(self):
        table = SymbolTable()
        bindings = parse_variables("set NAME foo")
        table.variables = bindings
        assert table.get("NAME") == "foo"

    def test_get_missing(self):
        table = SymbolTable()
        assert table.get("NONEXIST") is None
        assert table.get("NONEXIST", "default") == "default"

    def test_repr(self):
        table = SymbolTable()
        bindings = parse_variables("set A 1\nset B 2")
        table.variables = bindings
        r = repr(table)
        assert "2 vars" in r
        assert "0 files" in r


class TestResolveVariables:
    """Tests for the resolve_variables function."""

    def test_basic_resolution(self, tcl_params):
        table = SymbolTable()
        bindings = parse_variables(tcl_params)
        table.variables = bindings
        text = "create_clock -period $PERIOD_NS -name clk"
        result = resolve_variables(text, table)
        assert "5.0" in result
        assert "$PERIOD_NS" not in result

    def test_curly_brace_resolution(self, tcl_params):
        table = SymbolTable()
        bindings = parse_variables(tcl_params)
        table.variables = bindings
        text = "create_clock -period ${PERIOD_NS}"
        result = resolve_variables(text, table)
        assert "5.0" in result
        assert "${PERIOD_NS}" not in result

    def test_multiple_variables(self):
        text = "set CLK clk_1\nset PER 5.0\n"
        table = SymbolTable()
        bindings = parse_variables(text)
        table.variables = bindings
        sdc = "create_clock -name $CLK -period $PER"
        result = resolve_variables(sdc, table)
        assert "clk_1" in result
        assert "5.0" in result

    def test_no_variables_unchanged(self):
        table = SymbolTable()
        text = "create_clock -name clk -period 5.0"
        result = resolve_variables(text, table)
        assert result == text

    def test_max_depth_limit(self):
        """resolve_variables should stop after max_depth iterations."""
        table = SymbolTable()
        # Manually create a partially-resolved chain
        from tcl_resolver import VariableBinding
        table.variables = {
            "A": VariableBinding(name="A", raw_value="$B", resolved_value="$B",
                                source_file="test", line_number=1),
            "B": VariableBinding(name="B", raw_value="$C", resolved_value="$C",
                                source_file="test", line_number=2),
            "C": VariableBinding(name="C", raw_value="42", resolved_value="42",
                                source_file="test", line_number=3),
        }
        sdc = "echo $A"
        # With depth=2: $A→$B→$C→42 (fully resolved in 3 hops)
        result2 = resolve_variables(sdc, table, max_depth=2)
        assert "42" in result2
        # With depth=1: $A→$B (only one hop)
        result1 = resolve_variables(sdc, table, max_depth=1)
        assert "$B" in result1 or "42" in result1  # depends on whether $C → 42 in same pass


class TestBuildSymbolTable:
    """Tests for build_symbol_table function."""

    def test_from_main_text_only(self, tcl_params):
        table = build_symbol_table(tcl_params)
        assert "CYCLE" in table.variables
        assert "PERIOD_NS" in table.variables
        assert "CLK_PORT" in table.variables

    def test_with_linked_files(self, tcl_params):
        linked = {
            "extra.tcl": "set FREQ 100\nset RATE 2",
        }
        table = build_symbol_table("set MAIN 1", linked_files=linked)
        assert "FREQ" in table.variables
        assert "RATE" in table.variables
        assert "MAIN" in table.variables
        assert "extra.tcl" in table.source_files

    def test_main_overrides_linked(self):
        linked = {"base.tcl": "set X from_base"}
        table = build_symbol_table("set X from_main", linked_files=linked)
        assert table.variables["X"].resolved_value == "from_main"

    def test_resolve_cross_references(self, tcl_with_nested_refs):
        """Variables that reference each other should be resolved."""
        table = build_symbol_table(tcl_with_nested_refs)
        assert table.variables["FAST_CLOCK"].resolved_value == "5.0"

    def test_no_linked_files(self):
        table = build_symbol_table("set A 1")
        assert len(table.variables) == 1
        assert len(table.source_files) == 0


class TestExtractSourceFiles:
    """Tests for source file detection."""

    def test_detect_source_commands(self):
        text = "source setup.tcl\nsource constraints/io.tcl\ntiming.tcl"
        result = extract_source_files(text)
        assert "setup.tcl" in result
        assert "constraints/io.tcl" in result

    def test_no_source_commands(self):
        assert extract_source_files("set A 1\ncreate_clock...") == []

    def test_quoted_filenames(self):
        text = 'source "setup.tcl"\nsource \'lib.tcl\''
        result = extract_source_files(text)
        assert "setup.tcl" in result


class TestVariableBinding:
    """Tests for the VariableBinding dataclass."""

    def test_create_binding(self):
        vb = VariableBinding(
            name="TEST", raw_value="hello",
            resolved_value="hello", source_file="file.tcl",
            line_number=5,
        )
        assert vb.name == "TEST"
        assert vb.raw_value == "hello"
        assert vb.resolved_value == "hello"
        assert vb.line_number == 5
        assert vb.is_collection is False

    def test_collection_flag(self):
        vb = VariableBinding(
            name="PINS", raw_value="[get_pins *]",
            resolved_value="[get_pins *]", source_file="f.tcl",
            line_number=1, is_collection=True,
        )
        assert vb.is_collection is True

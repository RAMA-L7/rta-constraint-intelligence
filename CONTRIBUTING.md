# Contributing to Ṛta

Thank you for considering contributing to Ṛta! This guide will help you get started.

## 🚀 Development Setup

### Prerequisites

- Python 3.10+
- Git

### Quick Start

```bash
# Clone the repository
git clone https://github.com/RAMA-L7/rta-constraint-intelligence.git
cd rta-constraint-intelligence

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Install in development mode
pip install -e .

# Install test dependencies
pip install pytest

# Run the test suite
python -m pytest rta/tests/ -q
```

### Optional Dependencies

```bash
# For custom rules support
pip install pyyaml

# For web UI
pip install streamlit

# Install everything
pip install -e ".[all]"
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
python -m pytest rta/tests/ -q

# Run with verbose output
python -m pytest rta/tests/ -v

# Run a specific test file
python -m pytest rta/tests/test_checker.py -v

# Run a specific test
python -m pytest rta/tests/test_checker.py::TestCheckSdc::test_no_clock_creates_error -v
```

### Test Coverage

The project currently has **824 pytest tests** across 26 test files, verified
by `python rta/evidence/build_evidence.py` and recorded in
`rta/evidence/manifest/RELEASE_EVIDENCE.json`'s `test_files_detail` field
(don't hand-count — that's exactly what went stale here last time).

```bash
python rta/evidence/build_evidence.py
```


### Writing New Tests

Follow these conventions:

```python
"""tests/test_<module>.py — Tests for <module name>."""

import pytest
from <module> import <function>, <ClassName>


class TestClassName:
    """Tests for the ClassName dataclass/function."""

    def test_basic_operation(self):
        """Test normal/successful operation."""
        result = function(input)
        assert result is not None
        assert result.field == expected_value

    def test_edge_case_empty_input(self):
        """Test with empty input."""
        result = function("")
        assert result == expected

    def test_edge_case_none(self):
        """Test with None input."""
        with pytest.raises((TypeError, ValueError)):
            function(None)

    def test_error_condition(self):
        """Test that errors are raised for bad input."""
        with pytest.raises(Exception, match="expected error message"):
            function(bad_input)
```

### Test Categories

Tests should cover:
1. **Happy path** — Normal successful operation
2. **Edge cases** — Empty input, boundary values, special characters
3. **Error conditions** — Invalid input, missing files, bad format
4. **Cross-module integration** — How modules work together

## 📝 Code Style

### Python

- Follow PEP 8
- Use type hints on public functions
- Write docstrings for all public functions and classes
- Keep functions focused (single responsibility)
- Use descriptive variable names

### Example

```python
def check_sdc(text: str) -> CheckResult:
    """Validate SDC text and return a CheckResult with issues.

    Args:
        text: Raw SDC constraint text to validate.

    Returns:
        CheckResult containing errors, warnings, info items, and stats.
    """
    result = CheckResult()
    # ... implementation
    return result
```

## 🏗️ Project Structure

```
rta-constraint-intelligence/
├── Core modules (stdlib-only)
│   ├── checker.py          # SDC validation (40+ rules)
│   ├── generator.py        # SDC generation
│   ├── linter.py           # SDC formatting
│   ├── converter.py        # SDC → JSON/YAML
│   ├── batch_runner.py     # Directory processing
│   ├── constraint_diff.py  # Semantic SDC diff
│   ├── clock_relations.py  # Clock analysis
│   ├── corner_manager.py   # PVT corners
│   ├── mmc.py              # Multi-corner operations
│   ├── coverage.py         # Coverage gap analysis
│   ├── custom_rules.py     # YAML custom rules
│   ├── rules_registry.py   # Rule documentation
│   ├── reporter.py         # HTML reports
│   ├── tcl_resolver.py     # TCL variable resolution
│   └── wildcard_analyzer.py # Wildcard analysis
│
├── CLI (cli.py)            # Command-line interface
├── Legacy UI (legacy/streamlit/)  # preserved Streamlit app + ui package
├── Tests (tests/)          # 824 pytest tests
└── Documentation (docs/)   # Feature documentation
```

## 🔧 Adding a New Feature

### 1. Add the Core Logic

Create or modify a module in the root directory:

```python
# my_feature.py
"""New feature description."""

from dataclasses import dataclass


@dataclass
class MyResult:
    """Result of the new feature."""
    value: str
    score: int


def run_feature(text: str) -> MyResult:
    """Run the new feature on input text."""
    # Implementation here
    return MyResult(value="ok", score=100)
```

### 2. Add CLI Command

Edit `cli.py` to add a new subcommand:

```python
# In build_parser():
p_my = sub.add_parser("my-feature", help="Description")
p_my.add_argument("file", help="Input file")

# In main():
dispatch["my-feature"] = cmd_my_feature

# Handler function:
def cmd_my_feature(args):
    from my_feature import run_feature
    result = run_feature(Path(args.file).read_text())
    print(f"Result: {result.value}")
```

### 3. Add Tests

Create `tests/test_my_feature.py`:

```python
import pytest
from my_feature import run_feature, MyResult


class TestRunFeature:
    def test_basic(self):
        result = run_feature("input text")
        assert result.value == "ok"

    def test_empty_input(self):
        result = run_feature("")
        assert result.score == 0
```

### 4. Update Documentation

- Add to `README.md` feature table
- Update CLI reference in `README.md`
- Add sample usage in `README.md`

## 🐛 Reporting Issues

### Bug Reports

Include:
1. SDC file that causes the issue (anonymized)
2. CLI command or API call that triggers it
3. Expected behavior
4. Actual behavior
5. Python version and OS

### Feature Requests

Include:
1. Use case (why this feature is needed)
2. Expected behavior
3. Example input/output

## 📋 Pull Request Checklist

Before submitting a PR:

- [ ] Tests pass: `python -m pytest rta/tests/ -q`
- [ ] New features have tests
- [ ] No existing tests break
- [ ] Code follows project style
- [ ] Public functions have docstrings
- [ ] README is updated if applicable
- [ ] CHANGELOG is updated

## 🔄 Development Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Write tests for your changes
5. Run the test suite: `python -m pytest rta/tests/ -q`
6. Commit your changes: `git commit -m "Add my-feature"`
7. Push to your fork: `git push origin feature/my-feature`
8. Open a Pull Request

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.
---
name: run-tests
description: Run the SDC Tools test suite. Trigger: /run-tests [options]
---

# /run-tests

Run pytest on the SDC Tools project.

## Usage

```
/run-tests              # full suite
/run-tests -v           # verbose
/run-tests test_cli.py  # specific test file
/run-tests -k "check"   # filter by keyword
```

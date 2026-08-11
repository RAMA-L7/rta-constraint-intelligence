---
name: check-sdc
description: Validate an SDC file using the SDC Tools checker. Trigger: /check-sdc <file>
---

# /check-sdc

Run the SDC checker on a file and explain the findings.

## Usage

```
/check-sdc <file.sdc>
```

## What it does

1. Runs `python cli.py check <file>` 
2. Categorizes errors, warnings, and info items
3. Explains each finding in plain language

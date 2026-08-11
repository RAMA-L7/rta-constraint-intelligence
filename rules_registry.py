"""Ṛta migration shim — implementation moved to rta.engine.rules.rules_registry."""
import runpy as _runpy
import sys as _sys
from rta.engine.rules import rules_registry as _impl
_sys.modules[__name__] = _impl
if __name__ == "__main__":
    _runpy.run_path(_impl.__file__, run_name="__main__")

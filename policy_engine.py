"""Ṛta migration shim — implementation moved to rta.engine.policy.policy_engine."""
import runpy as _runpy
import sys as _sys
from rta.engine.policy import policy_engine as _impl
_sys.modules[__name__] = _impl
if __name__ == "__main__":
    _runpy.run_path(_impl.__file__, run_name="__main__")

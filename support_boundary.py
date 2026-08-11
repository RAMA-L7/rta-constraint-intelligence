"""Ṛta migration shim — implementation moved to rta.engine.trust.support_boundary."""
import runpy as _runpy
import sys as _sys
from rta.engine.trust import support_boundary as _impl
_sys.modules[__name__] = _impl
if __name__ == "__main__":
    _runpy.run_path(_impl.__file__, run_name="__main__")

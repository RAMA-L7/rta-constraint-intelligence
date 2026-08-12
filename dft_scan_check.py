"""Ṛta migration shim — implementation moved to rta.engine.analysis.dft_scan_check."""
import runpy as _runpy
import sys as _sys
from rta.engine.analysis import dft_scan_check as _impl
_sys.modules[__name__] = _impl
if __name__ == "__main__":
    _runpy.run_path(_impl.__file__, run_name="__main__")

"""Ṛta migration shim — implementation moved to rta.engine.preprocess.sdc_preprocess."""
import runpy as _runpy
import sys as _sys
from rta.engine.preprocess import sdc_preprocess as _impl
_sys.modules[__name__] = _impl
if __name__ == "__main__":
    _runpy.run_path(_impl.__file__, run_name="__main__")

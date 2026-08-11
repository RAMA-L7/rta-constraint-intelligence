"""Ṛta migration shim — implementation moved to rta.tools.batch.batch_runner."""
import runpy as _runpy
import sys as _sys
from rta.tools.batch import batch_runner as _impl
_sys.modules[__name__] = _impl
if __name__ == "__main__":
    _runpy.run_path(_impl.__file__, run_name="__main__")

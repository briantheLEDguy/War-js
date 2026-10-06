"""Compatibility entry point: bind shared city levels; never copy siege scenery."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('sync-shared-cities.py')), run_name='__main__')

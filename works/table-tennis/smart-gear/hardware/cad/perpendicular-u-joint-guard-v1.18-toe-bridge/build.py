"""Reuse the verified native-SCAD/Manifold finishing pipeline for v1.18."""
from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('guard_edge_finish',HERE.parent/'perpendicular-u-joint-guard-v1.17-load-path/build.py')
shared=importlib.util.module_from_spec(spec);spec.loader.exec_module(shared)
shared.HERE=HERE
shared.VERSION='1.18'
shared.OUT=HERE.parent/'exports/perpendicular-u-joint-v1.18-toe-bridge'
shared.OUT.mkdir(parents=True,exist_ok=True)
shared.SCAD=HERE/'toe_bridge_guard.scad'
load=shared.load
OUT=shared.OUT
CAD=shared.CAD
if __name__=='__main__':shared.main()

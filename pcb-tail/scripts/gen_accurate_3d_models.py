#!/usr/bin/env python3
"""Generate KiCad 3D models via OpenSCAD → STL → STEP (+ optional WRL).

STEP is required for KiCad 3D viewer / STEP export; WRL alone is rejected
with "Cannot load any VRML model for this export".

  python3 pcb-tail/scripts/gen_accurate_3d_models.py
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import os
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path


# ===== 分区：常量/配置 =====
HERE = Path(__file__).resolve().parent
OUT_DIR = HERE.parent / "lib" / "3dmodels"
OPENSCAD = "openscad"

# (scad stem, output basename without extension)
JOBS = (
    ("_sw_spst_45_tht", "SW_SPST_4.5x4.5_THT"),
    ("_led_ws2812_2020", "LED_WS2812B-2020_PLCC4_2.0x2.0mm"),
    ("_usb_c_vert_short", "USB_C_Receptacle_16P_Vertical_SMT_Short"),
)

# Prefer a Python that already has OCP (build123d env); fall back to current.
_OCP_PYTHON_CANDIDATES = (
    Path("/private/tmp/sp3d/bin/python3"),
    Path(sys.executable),
)


# ===== 分区：私有成员 =====
def _read_stl_triangles(path: Path) -> list[tuple[tuple[float, float, float], ...]]:
    data = path.read_bytes()
    if data[:5].lower() == b"solid" and b"\x00" not in data[:80]:
        return _read_ascii_stl(data.decode("utf-8", errors="replace"))
    return _read_binary_stl(data)


def _read_ascii_stl(text: str) -> list[tuple[tuple[float, float, float], ...]]:
    tris: list[tuple[tuple[float, float, float], ...]] = []
    verts: list[tuple[float, float, float]] = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[0] == "vertex":
            verts.append((float(parts[1]), float(parts[2]), float(parts[3])))
            if len(verts) == 3:
                tris.append(tuple(verts))
                verts = []
    return tris


def _read_binary_stl(data: bytes) -> list[tuple[tuple[float, float, float], ...]]:
    if len(data) < 84:
        raise ValueError("STL too small")
    n = struct.unpack_from("<I", data, 80)[0]
    tris: list[tuple[tuple[float, float, float], ...]] = []
    off = 84
    for _ in range(n):
        vals = struct.unpack_from("<12fH", data, off)
        v0 = (vals[3], vals[4], vals[5])
        v1 = (vals[6], vals[7], vals[8])
        v2 = (vals[9], vals[10], vals[11])
        tris.append((v0, v1, v2))
        off += 50
    return tris


def _stl_to_wrl(stl: Path, wrl: Path) -> None:
    """Optional VRML (inches) with footprint scale 1.0 — official KiCad style."""
    tris = _read_stl_triangles(stl)
    if not tris:
        raise RuntimeError(f"no triangles in {stl}")
    coords: list[tuple[float, float, float]] = []
    index: dict[tuple[float, float, float], int] = {}
    faces: list[list[int]] = []
    inch = 1.0 / 25.4

    def vid(p: tuple[float, float, float]) -> int:
        key = (round(p[0] * inch, 6), round(p[1] * inch, 6), round(p[2] * inch, 6))
        if key not in index:
            index[key] = len(coords)
            coords.append(key)
        return index[key]

    for a, b, c in tris:
        faces.append([vid(a), vid(b), vid(c)])

    coord_s = ", ".join(f"{x} {y} {z}" for x, y, z in coords)
    face_s = " ".join(f"{i0},{i1},{i2},-1" for i0, i1, i2 in faces)
    wrl.write_text(
        "#VRML V2.0 utf8\n"
        "# OpenSCAD → STL → WRL (inches); KiCad scale xyz 1\n"
        "Shape {\n"
        "  appearance Appearance {\n"
        "    material Material { diffuseColor 0.55 0.55 0.58 }\n"
        "  }\n"
        "  geometry IndexedFaceSet {\n"
        "    creaseAngle 0.5\n"
        "    coord Coordinate { point [ " + coord_s + " ] }\n"
        "    coordIndex [ " + face_s + " ]\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )


def _render_scad(scad: Path, stl: Path) -> None:
    cmd = [OPENSCAD, "-o", str(stl), "--export-format=binstl", str(scad)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not stl.exists():
        raise RuntimeError(
            f"openscad failed ({r.returncode}): {scad}\n"
            f"stdout: {r.stdout}\nstderr: {r.stderr}"
        )


def _ocp_python() -> Path:
    for cand in _OCP_PYTHON_CANDIDATES:
        if not cand.is_file():
            continue
        r = subprocess.run(
            [str(cand), "-c", "from OCP.StlAPI import StlAPI_Reader"],
            capture_output=True,
            text=True,
        )
        if r.returncode == 0:
            return cand
    raise RuntimeError(
        "Need a Python with OCP (OpenCASCADE) to write STEP. "
        "Install build123d/cadquery-ocp, or set SMARTPADDLE_OCP_PYTHON."
    )


def _stl_to_step(stl: Path, step: Path) -> None:
    env_py = os.environ.get("SMARTPADDLE_OCP_PYTHON")
    py = Path(env_py) if env_py else _ocp_python()
    helper = r"""
from pathlib import Path
import sys
from OCP.StlAPI import StlAPI_Reader
from OCP.TopoDS import TopoDS_Shape
from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
from OCP.Interface import Interface_Static
from OCP.IFSelect import IFSelect_RetDone

stl, step = Path(sys.argv[1]), Path(sys.argv[2])
shape = TopoDS_Shape()
if not StlAPI_Reader().Read(shape, str(stl)) or shape.IsNull():
    raise SystemExit(f"STL read failed: {stl}")
Interface_Static.SetCVal_s("write.step.schema", "AP214IS")
writer = STEPControl_Writer()
if writer.Transfer(shape, STEPControl_AsIs) != IFSelect_RetDone:
    raise SystemExit("STEP transfer failed")
if writer.Write(str(step)) != IFSelect_RetDone or not step.is_file():
    raise SystemExit(f"STEP write failed: {step}")
print(f"wrote {step} ({step.stat().st_size} bytes)")
"""
    r = subprocess.run(
        [str(py), "-c", helper, str(stl), str(step)],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0 or not step.is_file():
        raise RuntimeError(
            f"STL→STEP failed\nstdout: {r.stdout}\nstderr: {r.stderr}"
        )
    print(f"  {r.stdout.strip()}")


# ===== 分区：公开 API =====
def main() -> None:
    if not shutil.which(OPENSCAD):
        raise SystemExit("openscad not on PATH")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="tail3d_") as tmp:
        tmp_path = Path(tmp)
        for stem, base in JOBS:
            scad = OUT_DIR / f"{stem}.scad"
            if not scad.is_file():
                raise FileNotFoundError(scad)
            stl = tmp_path / f"{stem}.stl"
            step = OUT_DIR / f"{base}.step"
            wrl = OUT_DIR / f"{base}.wrl"
            print(f"openscad {scad.name} → {base}.step")
            _render_scad(scad, stl)
            _stl_to_step(stl, step)
            _stl_to_wrl(stl, wrl)
            print(f"  wrote {wrl.name} ({wrl.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

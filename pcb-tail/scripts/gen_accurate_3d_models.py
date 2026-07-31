#!/usr/bin/env python3
"""Generate KiCad WRL 3D models via OpenSCAD (no build123d).

Pipeline: .scad → openscad STL → IndexedFaceSet .wrl (mm).
Footprints use scale 0.03937 (mm → KiCad WRL inch convention).

  python3 pcb-tail/scripts/gen_accurate_3d_models.py
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import struct
import subprocess
import tempfile
from pathlib import Path


# ===== 分区：常量/配置 =====
HERE = Path(__file__).resolve().parent
OUT_DIR = HERE.parent / "lib" / "3dmodels"
OPENSCAD = "openscad"

# (scad stem, output wrl name)
JOBS = (
    ("_sw_spst_45_tht", "SW_SPST_4.5x4.5_THT.wrl"),
    ("_led_ws2812_2020", "LED_WS2812B-2020_PLCC4_2.0x2.0mm.wrl"),
    ("_usb_c_vert_short", "USB_C_Receptacle_16P_Vertical_SMT_Short.wrl"),
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
        # normal(3f) + 3*vertex(3f) + attr(2)
        vals = struct.unpack_from("<12fH", data, off)
        v0 = (vals[3], vals[4], vals[5])
        v1 = (vals[6], vals[7], vals[8])
        v2 = (vals[9], vals[10], vals[11])
        tris.append((v0, v1, v2))
        off += 50
    return tris


def _stl_to_wrl(stl: Path, wrl: Path) -> None:
    tris = _read_stl_triangles(stl)
    if not tris:
        raise RuntimeError(f"no triangles in {stl}")
    # dedupe coords for compact IndexedFaceSet
    coords: list[tuple[float, float, float]] = []
    index: dict[tuple[float, float, float], int] = {}
    faces: list[list[int]] = []

    def vid(p: tuple[float, float, float]) -> int:
        key = (round(p[0], 5), round(p[1], 5), round(p[2], 5))
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
        "# OpenSCAD → STL → WRL (mm); KiCad scale xyz 0.03937\n"
        "Shape {\n"
        "  appearance Appearance {\n"
        "    material Material { diffuseColor 0.55 0.55 0.58 }\n"
        "  }\n"
        "  geometry IndexedFaceSet {\n"
        "    solid TRUE\n"
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


# ===== 分区：公开 API =====
def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="tail3d_") as tmp:
        tmp_path = Path(tmp)
        for stem, wrl_name in JOBS:
            scad = OUT_DIR / f"{stem}.scad"
            if not scad.is_file():
                raise FileNotFoundError(scad)
            stl = tmp_path / f"{stem}.stl"
            wrl = OUT_DIR / wrl_name
            print(f"openscad {scad.name} → {wrl_name}")
            _render_scad(scad, stl)
            _stl_to_wrl(stl, wrl)
            print(f"  wrote {wrl} ({wrl.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

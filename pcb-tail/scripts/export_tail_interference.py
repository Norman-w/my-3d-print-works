#!/usr/bin/env python3
"""Export handle interference facts from pcb-tail KiCad board.

Writes enclosure/stl/interference/tail_interference.json (+ optional .scad):
  - Edge.Cuts polygon (KiCad XY = handle XZ)
  - J1 / SW1 / D1 / LED1 poses + cut envelopes for shell boolean
  - new F-side TPS2553 support-part envelopes and shell headroom
  - an explicit tolerance gate for the guided B3U plunger

  python3 pcb-tail/scripts/export_tail_interference.py
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import json
import sys
from pathlib import Path


# ===== 分区：常量/配置 =====
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PCB = ROOT / "pcb-tail" / "layouts" / "default" / "default.kicad_pcb"
FACTS = ROOT / "pcb-tail" / "outline-facts.json"
OUT = ROOT / "enclosure" / "stl" / "interference" / "tail_interference.json"
OUT_SCAD = ROOT / "enclosure" / "stl" / "interference" / "tail_board_cuts.scad"

# 开孔相对器件的间隙（mm）
USB_CLEAR = 0.35
BTN_HOLE_OVER = 0.40          # Ø1.6 推杆配 Ø2.0 导向孔（径向间隙 0.2）
LED_HOLE_OVER = 0.40
BOARD_AXIAL_CLEAR = 0.15      # 板厚向每侧

FRONT_POWER_HEIGHT_MM = {
    "U4": 1.45, "U5": 1.45,       # TPS2553 DBV package maximum
    "C8": 0.95, "C9": 0.95, "C10": 0.95,
    "R8": 0.65, "R9": 0.65,
    "D2": 1.00,
}

# Exact current KiCad 3D assembly versus the Step6 tail shell identified these
# twelve local wall/ring-groove intersections.  Heights are conservative
# package envelopes rounded up from the archived/stock 3D models.  Courtyards
# supply the in-plane envelope, so the resulting pockets follow any later
# footprint move instead of baking today's absolute coordinates into the shell.
SHELL_KEEPOUT_HEIGHT_MM = {
    "C6": 1.70,
    "J2": 4.80,
    "J3": 4.80,
    "D2": 1.20,
    "C9": 0.90,
    "U2": 1.70,
    "U4": 1.70,
    "U5": 1.70,
    "R9": 0.60,
    "R5": 0.60,
    "L1": 2.20,
    "C7": 1.35,
}
SHELL_KEEPOUT_AXIAL_CLEAR = 0.20
SHELL_KEEPOUT_BOARD_OVERLAP = 0.15


# ===== 分区：私有成员 =====
def _kicad_python() -> str:
    mac = Path(
        "/Applications/KiCad/KiCad.app/Contents/Frameworks/"
        "Python.framework/Versions/Current/bin/python3"
    )
    if mac.is_file():
        return str(mac)
    # Linux KiCad packages install pcbnew for the system interpreter, while
    # Step6 itself normally runs from scripts/.venv-stl.
    linux = Path("/usr/bin/python3")
    dist_packages = Path("/usr/lib/python3/dist-packages")
    if linux.is_file() and any(dist_packages.glob("pcbnew*")):
        return str(linux)
    return sys.executable


def _extract() -> dict:
    import wx

    _app = wx.App(False)
    import pcbnew

    board = pcbnew.LoadBoard(str(PCB))
    facts = json.loads(FACTS.read_text(encoding="utf-8"))
    butt_y = float(facts["butt_y"])
    pcb_y = float(facts["pcb_y"])
    board_t = float(facts["board_thickness"])

    edge: list[list[float]] = []
    for dr in board.GetDrawings():
        if board.GetLayerName(dr.GetLayer()) != "Edge.Cuts":
            continue
        outline = dr.GetPolyShape().Outline(0)
        for i in range(outline.PointCount()):
            p = outline.CPoint(i)
            edge.append([p.x / 1e6, p.y / 1e6])
        break
    if len(edge) < 8:
        raise RuntimeError("Edge.Cuts polygon missing")

    def fp_pose(ref: str) -> dict:
        fp = board.FindFootprintByReference(ref)
        if fp is None:
            raise RuntimeError(f"missing footprint {ref}")
        p = fp.GetPosition()
        return {
            "ref": ref,
            "x": p.x / 1e6,
            "y": p.y / 1e6,
            "rot_deg": fp.GetOrientationDegrees(),
            "layer": board.GetLayerName(fp.GetLayer()),
        }

    def courtyard_box(ref: str) -> list[float]:
        fp = board.FindFootprintByReference(ref)
        layer_name = "F.Courtyard" if fp.GetLayer() == pcbnew.F_Cu else "B.Courtyard"
        boxes = []
        for item in fp.GraphicalItems():
            if board.GetLayerName(item.GetLayer()) != layer_name:
                continue
            box = item.GetBoundingBox()
            boxes.append(
                [
                    box.GetX() / 1e6,
                    box.GetY() / 1e6,
                    (box.GetX() + box.GetWidth()) / 1e6,
                    (box.GetY() + box.GetHeight()) / 1e6,
                ]
            )
        if not boxes:
            raise RuntimeError(f"missing courtyard for {ref}")
        return [
            min(box[0] for box in boxes), min(box[1] for box in boxes),
            max(box[2] for box in boxes), max(box[3] for box in boxes),
        ]

    j1 = fp_pose("J1")
    sw1 = fp_pose("SW1")
    d1 = fp_pose("D1")
    led1 = fp_pose("LED1")

    # 器件包络（J1 来自主数据表；SW1 来自 Omron B3U 数据表 A162-E1）
    usb = {
        **j1,
        "shell_w": 8.94,
        "shell_d": 3.26,
        "height": 5.80,
        "clear": USB_CLEAR,
    }
    button = {
        **sw1,
        "part": "Omron B3U-1000P",
        "body_w": 3.00,
        "body_d": 2.50,
        "body_h": 1.20,
        "operation_h": 1.60,
        "act_d": 1.50,
        "pretravel": 0.15,
        "pretravel_min": 0.05,
        "pretravel_max": 0.35,
        "hole_d": 1.60 + BTN_HOLE_OVER,
        "access_mode": "pinhole_with_optional_retained_plunger",
        "pinhole_ready": True,
        "pocket_w": 3.00 + 0.60,
        "pocket_d": 2.50 + 0.60,
        "wall_t": float(facts["wall_t"]),
        "plunger_shaft_d": 1.60,
        "plunger_flange_d": 3.00,
        "plunger_flange_h": 0.50,
        "plunger_flange_pocket_d": 3.40,
        "plunger_flange_pocket_depth": 0.80,
        "plunger_flange_pocket_wall_overlap": 0.10,
        "plunger_outer_projection": 0.30,
        "plunger_rest_gap": 0.05,
        # Current fixed geometry can actuate the nominal switch but cannot
        # cover the full Omron pretravel tolerance without an unspecified
        # overtravel risk.  Keep it prototype-only until a printed coupon is
        # measured; manufacturing gates consume this flag.
        "plunger_max_travel": 0.30,
        "activation_travel_nominal": 0.20,
        "activation_travel_worst_case": 0.40,
        "plunger_optional": True,
        "retention": "inside-loaded flange; retained between shell wall and installed SW1",
        "tolerance_closed": False,
        "plunger_validation_note": "optional plunger stop/travel requires a measured tail-section coupon",
    }
    led_rgb = {
        **d1,
        "body": 2.0,
        "height": 1.08,
        "hole_d": 2.0 + LED_HOLE_OVER,
    }
    led_status = {
        **led1,
        "body_w": 1.6,
        "body_d": 0.8,
        "height": 0.8,
        "hole_d": 1.6 + LED_HOLE_OVER,
    }

    # F.Cu faces the butt cap.  The shell inner wall is wall_t inward from the
    # butt plane, so this is the nominal axial cavity available above F-side
    # packages before any local pocket is needed.
    front_cavity_depth = pcb_y - (butt_y + float(facts["wall_t"]))
    front_power_parts = []
    for ref, height in FRONT_POWER_HEIGHT_MM.items():
        pose = fp_pose(ref)
        if pose["layer"] != "F.Cu":
            raise RuntimeError(f"{ref} unexpectedly left F.Cu")
        clearance = front_cavity_depth - height
        if clearance < 1.0:
            raise RuntimeError(f"{ref} has only {clearance:.2f} mm nominal shell headroom")
        front_power_parts.append(
            {
                **pose,
                "courtyard_xy": courtyard_box(ref),
                "height_max": height,
                "nominal_shell_headroom": clearance,
            }
        )

    component_keepouts = []
    for ref, height in SHELL_KEEPOUT_HEIGHT_MM.items():
        pose = fp_pose(ref)
        x0, z0, x1, z1 = courtyard_box(ref)
        if pose["layer"] == "F.Cu":
            y0 = pcb_y - height - SHELL_KEEPOUT_AXIAL_CLEAR
            y1 = pcb_y + SHELL_KEEPOUT_BOARD_OVERLAP
        elif pose["layer"] == "B.Cu":
            y0 = pcb_y + board_t - SHELL_KEEPOUT_BOARD_OVERLAP
            y1 = pcb_y + board_t + height + SHELL_KEEPOUT_AXIAL_CLEAR
        else:
            raise RuntimeError(f"{ref} unexpectedly left a copper side")
        component_keepouts.append(
            {
                **pose,
                "courtyard_xy": [x0, z0, x1, z1],
                "height_max": height,
                "axial_clear": SHELL_KEEPOUT_AXIAL_CLEAR,
                "handle_box_xyz": [x0, y0, z0, x1, y1, z1],
            }
        )

    return {
        "source_pcb": str(PCB.relative_to(ROOT)),
        "butt_y": butt_y,
        "pcb_y": pcb_y,
        "board_thickness": board_t,
        "board_axial_clear": BOARD_AXIAL_CLEAR,
        "ring_groove_radial": float(facts["ring_groove_radial"]),
        "orientation": facts["orientation"],
        "edge_cuts_xy": edge,
        "usb": usb,
        "button": button,
        "led_rgb": led_rgb,
        "led_status": led_status,
        "front_component_cavity_depth": front_cavity_depth,
        "front_power_parts": front_power_parts,
        "component_keepouts": component_keepouts,
        "transform": {
            "comment": "handle(x,y,z) = (kicad_x, pcb_y - kicad_z, kicad_y)",
            "kicad_z_toward_butt": True,
        },
    }


def _write_scad(data: dict) -> None:
    """OpenSCAD 可 include 的开孔参数（由 KiCad 位姿生成）。"""
    usb, btn = data["usb"], data["button"]
    d1, led1 = data["led_rgb"], data["led_status"]
    edge = data["edge_cuts_xy"]
    pts = ",\n".join(f"    [{x:.5f}, {y:.5f}]" for x, y in edge)
    keepouts = ",\n".join(
        "    [" + ", ".join(f"{value:.5f}" for value in item["handle_box_xyz"]) + "]"
        for item in data["component_keepouts"]
    )
    text = f"""// AUTO-GENERATED by pcb-tail/scripts/export_tail_interference.py — do not edit
// KiCad XY → handle XZ；F.Cu @ pcb_y；+Z_kicad 朝拍尾 (−Y)

tail_if_pcb_y = {data['pcb_y']:.6f};
tail_if_butt_y = {data['butt_y']:.6f};
tail_if_board_t = {data['board_thickness']:.3f};
tail_if_axial = {data['board_axial_clear']:.3f};

tail_if_usb_x = {usb['x']:.5f};
tail_if_usb_z = {usb['y']:.5f};
tail_if_usb_w = {usb['shell_w'] + 2 * usb['clear']:.3f};
tail_if_usb_d = {usb['shell_d'] + 2 * usb['clear']:.3f};
tail_if_usb_rot = {usb['rot_deg']:.3f};

tail_if_btn_x = {btn['x']:.5f};
tail_if_btn_z = {btn['y']:.5f};
tail_if_btn_rot = {btn['rot_deg']:.3f};
tail_if_btn_hole_d = {btn['hole_d']:.3f};
tail_if_btn_pocket_w = {btn['pocket_w']:.3f};
tail_if_btn_pocket_d = {btn['pocket_d']:.3f};
tail_if_btn_body_h = {btn['body_h']:.3f};
tail_if_btn_operation_h = {btn['operation_h']:.3f};
tail_if_btn_pretravel = {btn['pretravel']:.3f};
tail_if_btn_pretravel_min = {btn['pretravel_min']:.3f};
tail_if_btn_pretravel_max = {btn['pretravel_max']:.3f};
tail_if_btn_wall_t = {btn['wall_t']:.3f};
tail_if_btn_plunger_d = {btn['plunger_shaft_d']:.3f};
tail_if_btn_flange_d = {btn['plunger_flange_d']:.3f};
tail_if_btn_flange_h = {btn['plunger_flange_h']:.3f};
tail_if_btn_flange_pocket_d = {btn['plunger_flange_pocket_d']:.3f};
tail_if_btn_flange_pocket_depth = {btn['plunger_flange_pocket_depth']:.3f};
tail_if_btn_flange_pocket_wall_overlap = {btn['plunger_flange_pocket_wall_overlap']:.3f};
tail_if_btn_outer_projection = {btn['plunger_outer_projection']:.3f};
tail_if_btn_rest_gap = {btn['plunger_rest_gap']:.3f};
tail_if_btn_max_travel = {btn['plunger_max_travel']:.3f};
tail_if_btn_access_mode = "{btn['access_mode']}";
tail_if_btn_pinhole_ready = true;
tail_if_btn_plunger_optional = true;
tail_if_btn_tolerance_closed = false;

// F-side TPS2553 support parts fit the common board cavity without new holes.
// Nominal cavity depth = {data['front_component_cavity_depth']:.3f} mm;
// minimum audited package headroom = {min(p['nominal_shell_headroom'] for p in data['front_power_parts']):.3f} mm.

tail_if_d1_x = {d1['x']:.5f};
tail_if_d1_z = {d1['y']:.5f};
tail_if_d1_hole_d = {d1['hole_d']:.3f};

tail_if_led1_x = {led1['x']:.5f};
tail_if_led1_z = {led1['y']:.5f};
tail_if_led1_hole_d = {led1['hole_d']:.3f};

tail_if_edge_pts = [
{pts}
];

// [x0, y0, z0, x1, y1, z1] local pockets derived from the current KiCad
// component courtyards and conservative 3D package heights.
tail_if_component_keepouts = [
{keepouts}
];

module tail_if_stadium_2d(w, d) {{
    r = min(d / 2, w / 2);
    hull() for (sx = [-1, 1])
        translate([sx * (w / 2 - r), 0]) circle(r = r, $fn = 28);
}}

module tail_board_interference_cuts() {{
    y0 = tail_if_pcb_y - tail_if_axial;
    y1 = tail_if_pcb_y + tail_if_board_t + tail_if_axial;
    // 满截面板槽：Edge.Cuts 沿 Y 拉伸（板比平滑内腔大 → 卡进环槽）
    // rotate+90 使挤出朝 −Y，故从 y1 起挤到 y0
    translate([0, y1, 0])
        rotate([90, 0, 0])
            linear_extrude(height = y1 - y0)
                polygon(tail_if_edge_pts);

    // 靠板边器件的局部避让；只切实际相交的 12 个包络，不扩大公共内腔。
    for (k = tail_if_component_keepouts)
        translate([(k[0] + k[3]) / 2, (k[1] + k[4]) / 2, (k[2] + k[5]) / 2])
            cube([k[3] - k[0], k[4] - k[1], k[5] - k[2]], center = true);

    // Type-C 穿出拍尾（跑道长轴跟 J1 rot；0°=口宽沿 handle X）
    translate([tail_if_usb_x, tail_if_pcb_y + 0.8, tail_if_usb_z])
        rotate([90, 0, 0])
            linear_extrude(height = (tail_if_pcb_y + 0.8) - (tail_if_butt_y - 3))
                rotate(tail_if_usb_rot)
                    tail_if_stadium_2d(tail_if_usb_w, tail_if_usb_d);

    // B3U 导向活动推杆孔 + 随 footprint 旋转的开关体凹坑
    translate([tail_if_btn_x, tail_if_butt_y - 3, tail_if_btn_z])
        rotate([-90, 0, 0])
            cylinder(d = tail_if_btn_hole_d, h = (tail_if_pcb_y + 1) - (tail_if_butt_y - 3), $fn = 28);
    translate([
        tail_if_btn_x,
        tail_if_butt_y + tail_if_btn_wall_t - tail_if_btn_flange_pocket_wall_overlap,
        tail_if_btn_z
    ])
        rotate([-90, 0, 0])
            cylinder(
                d = tail_if_btn_flange_pocket_d,
                h = tail_if_btn_flange_pocket_depth + tail_if_btn_flange_pocket_wall_overlap,
                $fn = 32
            );
    translate([tail_if_btn_x, tail_if_pcb_y - tail_if_btn_body_h / 2, tail_if_btn_z])
        rotate([0, tail_if_btn_rot, 0])
            cube([tail_if_btn_pocket_w, tail_if_btn_body_h + 0.35, tail_if_btn_pocket_d], center = true);

    // LED 透光孔
    translate([tail_if_d1_x, tail_if_butt_y - 2.5, tail_if_d1_z])
        rotate([-90, 0, 0])
            cylinder(d = tail_if_d1_hole_d, h = (tail_if_pcb_y + 0.5) - (tail_if_butt_y - 2.5), $fn = 24);
    translate([tail_if_led1_x, tail_if_butt_y - 2.5, tail_if_led1_z])
        rotate([-90, 0, 0])
            cylinder(d = tail_if_led1_hole_d, h = (tail_if_pcb_y + 0.5) - (tail_if_butt_y - 2.5), $fn = 24);
}}

// 可选独立打印、从壳内装入；内侧法兰防止装配后向壳外脱出。
// 静止端面与 B3U 执行头留 0.05 mm 名义间隙，外露 0.30 mm。
// 壳体本身的 Ø2.0 mm 针孔是基准操作方式；推杆仅为便利附件。
// 推杆覆盖 0.15 mm 名义预行程，但未覆盖 0.35 mm 最坏值，批量采用前仍须试片。
module tail_if_button_plunger() {{
    y_outer = tail_if_butt_y - tail_if_btn_outer_projection;
    y_tip = tail_if_pcb_y - tail_if_btn_operation_h - tail_if_btn_rest_gap;
    union() {{
        translate([tail_if_btn_x, y_outer, tail_if_btn_z])
            rotate([-90, 0, 0])
                cylinder(d = tail_if_btn_plunger_d, h = y_tip - y_outer, $fn = 32);
        translate([tail_if_btn_x, tail_if_butt_y + tail_if_btn_wall_t + 0.05, tail_if_btn_z])
            rotate([-90, 0, 0])
                cylinder(d = tail_if_btn_flange_d, h = tail_if_btn_flange_h, $fn = 32);
    }}
}}
"""
    OUT_SCAD.write_text(text, encoding="utf-8")


# ===== 分区：公开 API =====
def main() -> int:
    data = _extract()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    _write_scad(data)
    print(f"wrote {OUT}  edge_pts={len(data['edge_cuts_xy'])}")
    print(f"wrote {OUT_SCAD}")
    print(
        f"  usb@({data['usb']['x']:.2f},{data['usb']['y']:.2f})  "
        f"sw@({data['button']['x']:.2f},{data['button']['y']:.2f})  "
        f"d1@({data['led_rgb']['x']:.2f},{data['led_rgb']['y']:.2f})"
    )
    return 0


if __name__ == "__main__":
    # Run extract under KiCad Python if needed
    try:
        import pcbnew  # noqa: F401
    except ImportError:
        import subprocess

        raise SystemExit(
            subprocess.call([_kicad_python(), str(Path(__file__).resolve()), *sys.argv[1:]])
        )
    raise SystemExit(main())

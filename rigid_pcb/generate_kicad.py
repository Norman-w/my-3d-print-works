"""Generate SmartPaddle rigid PCB study.

This layout is a rigid-board alternative to the full FPC:
- a drone-frame-like central carrier in the OpenSCAD sweet zone,
- embedded cutouts for the ESP32-C6 and IM948 modules,
- castellated half-hole landing pads around those cutouts,
- PZT front-end parts placed near each PZT along the radial direction,
- handle wire pads for battery, USB, LED, and the single user button.
"""

import math
import subprocess
import sys
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
YAML_PATH = PROJECT_ROOT / "shared" / "board_params.yaml"
OUTPUT_DIR = Path(__file__).resolve().parent / "layouts" / "default"
OUTPUT_FILE = OUTPUT_DIR / "default.kicad_pcb"

TRACE_SIG = 0.22
TRACE_PWR = 0.35
TRACE_MAIN_PWR = 0.7
VIA_DRILL = 0.3
VIA_PAD = 0.65


def main():
    import pcbnew

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    board = pcbnew.BOARD()
    ds = board.GetDesignSettings()
    ds.SetBoardThickness(int(0.8e6))
    ds.m_CopperLayerCount = 2

    params = yaml.safe_load(YAML_PATH.read_text())

    nets = {}

    def N(name):
        if name in ("", "NC", None):
            return None
        if name not in nets:
            item = pcbnew.NETINFO_ITEM(board, name)
            board.Add(item)
            nets[name] = item
        return nets[name]

    gnd = N("GND")
    vbat_in = N("VBAT_IN")
    vbat = N("VBAT")
    vcc = N("VCC")
    en = N("EN")
    for name in [
        "USB_D+", "USB_D-", "UART_TX", "UART_RX",
        "LED_DATA", "LED_DIN", "USER_BTN", "BTN_SW", "PWR_LATCH",
        "BOOT", "P_GATE", "IMU_KEY", "IMU_GPIO",
        "PZT_TR_SIGNAL", "PZT_TL_SIGNAL", "PZT_BR_SIGNAL", "PZT_BL_SIGNAL",
    ]:
        N(name)

    def mk(mm):
        return int(round(mm * 1e6))

    def pt(x, y):
        return pcbnew.VECTOR2I(mk(x), mk(y))

    def track(net, a, b, width=TRACE_SIG, layer=pcbnew.F_Cu):
        t = pcbnew.PCB_TRACK(board)
        t.SetLayer(layer)
        t.SetNet(net)
        t.SetStart(pt(*a))
        t.SetEnd(pt(*b))
        t.SetWidth(mk(width))
        board.Add(t)

    def route(net, points, width=TRACE_SIG, layer=pcbnew.F_Cu):
        for a, b in zip(points, points[1:]):
            track(net, a, b, width, layer)

    def connect(net, points, width=TRACE_SIG, layer=pcbnew.F_Cu):
        """Manual route helper.

        Keep this separate from route() so the first rigid-PCB study can choose
        between placement-only and explicitly routed output without deleting the
        intended connection list.
        """
        route(net, points, width, layer)

    def via(net, x, y):
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pt(x, y))
        v.SetNet(net)
        v.SetWidth(mk(VIA_PAD))
        v.SetDrill(mk(VIA_DRILL))
        board.Add(v)

    def shape_line(layer, a, b, width=0.1):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetLayer(layer)
        s.SetStart(pt(*a))
        s.SetEnd(pt(*b))
        s.SetWidth(mk(width))
        board.Add(s)

    def poly_edge(points):
        for a, b in zip(points, points[1:] + points[:1]):
            shape_line(pcbnew.Edge_Cuts, a, b, 0.1)

    def rect_edge(cx, cy, w, h):
        poly_edge(rect_points(cx, cy, w, h))

    def rect_graphic(layer, cx, cy, w, h, width=0.1):
        pts = rect_points(cx, cy, w, h)
        for a, b in zip(pts, pts[1:] + pts[:1]):
            shape_line(layer, a, b, width)

    def circle(layer, cx, cy, r, width=0.1):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_CIRCLE)
        s.SetLayer(layer)
        s.SetCenter(pt(cx, cy))
        s.SetEnd(pt(cx + r, cy))
        s.SetWidth(mk(width))
        board.Add(s)

    def hide_texts(fp):
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)

    def make_fp(ref, value, x, y, rot=0):
        fp = pcbnew.FOOTPRINT(board)
        fp.SetReference(ref)
        fp.SetValue(value)
        hide_texts(fp)
        fp.SetLayer(pcbnew.F_Cu)
        fp.SetPosition(pt(x, y))
        fp.SetOrientationDegrees(rot)
        return fp

    def add_pad(fp, num, rel, size, net, shape=pcbnew.PAD_SHAPE_RECT, layers=None):
        p = pcbnew.PAD(fp)
        p.SetNumber(str(num))
        p.SetShape(shape)
        p.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        p.SetFPRelativePosition(pt(*rel))
        p.SetSize(pcbnew.VECTOR2I(mk(size[0]), mk(size[1])))
        p.SetOrientationDegrees(fp.GetOrientationDegrees())
        if net is not None:
            p.SetNet(net)
        ls = pcbnew.LSET()
        for ly in layers or [pcbnew.F_Cu, pcbnew.F_Paste, pcbnew.F_Mask]:
            ls.addLayer(ly)
        p.SetLayerSet(ls)
        fp.Add(p)
        return p

    def add_through_hole(fp, num, rel, drill, size, net=None):
        p = pcbnew.PAD(fp)
        p.SetNumber(str(num))
        p.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
        p.SetAttribute(pcbnew.PAD_ATTRIB_NPTH if net is None else pcbnew.PAD_ATTRIB_PTH)
        p.SetFPRelativePosition(pt(*rel))
        p.SetSize(pcbnew.VECTOR2I(mk(size), mk(size)))
        p.SetDrillSize(pcbnew.VECTOR2I(mk(drill), mk(drill)))
        if net is not None:
            p.SetNet(net)
        ls = pcbnew.LSET()
        pad_layers = [pcbnew.F_Mask, pcbnew.B_Mask]
        if net is None:
            pad_layers.append(pcbnew.Edge_Cuts)
        else:
            pad_layers = [pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.F_Mask, pcbnew.B_Mask]
        for ly in pad_layers:
            ls.addLayer(ly)
        p.SetLayerSet(ls)
        fp.Add(p)
        return p

    def add_castellated(fp, num, pos, net, drill=0.50, size=1.00):
        return add_through_hole(fp, num, pos, drill, size, net)

    def pad_xy(p):
        pos = p.GetPosition()
        return (pos.x / 1e6, pos.y / 1e6)

    pins = {}

    def rec(ref, num, p):
        pins[(ref, num)] = pad_xy(p)

    def two_pad(ref, value, x, y, n1, n2, rot=0, pitch=1.6, size=(1.0, 0.7)):
        fp = make_fp(ref, value, x, y, rot)
        p1 = add_pad(fp, 1, (0, -pitch / 2), size, n1)
        p2 = add_pad(fp, 2, (0, pitch / 2), size, n2)
        board.Add(fp)
        rec(ref, 1, p1)
        rec(ref, 2, p2)
        return fp

    def sot23(ref, value, x, y, mapping, rot=0):
        fp = make_fp(ref, value, x, y, rot)
        loc = {1: (-0.95, -0.65), 2: (0.95, -0.65), 3: (0, 0.95)}
        for num, rel in loc.items():
            rec(ref, num, add_pad(fp, num, rel, (0.75, 0.55), mapping.get(num)))
        board.Add(fp)
        return fp

    def sot23_5(ref, value, x, y, mapping, rot=0):
        fp = make_fp(ref, value, x, y, rot)
        loc = {
            1: (-0.95, -0.65), 2: (0, -0.65), 3: (0.95, -0.65),
            4: (0.95, 0.65), 5: (-0.95, 0.65),
        }
        for num, rel in loc.items():
            rec(ref, num, add_pad(fp, num, rel, (0.65, 0.5), mapping.get(num)))
        board.Add(fp)
        return fp

    def wire_pad(ref, label, x, y, net):
        fp = make_fp(ref, label, x, y)
        p = add_pad(fp, 1, (0, 0), (3.6, 2.2), net)
        board.Add(fp)
        rec(ref, 1, p)
        return fp

    def convex_hull(points):
        pts = sorted(set((round(x, 6), round(y, 6)) for x, y in points))
        if len(pts) <= 1:
            return pts

        def cross(o, a, b):
            return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

        lower = []
        for p in pts:
            while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
                lower.pop()
            lower.append(p)
        upper = []
        for p in reversed(pts):
            while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
                upper.pop()
            upper.append(p)
        return lower[:-1] + upper[:-1]

    def rect_points(cx, cy, w, h):
        return [
            (cx - w / 2, cy - h / 2),
            (cx + w / 2, cy - h / 2),
            (cx + w / 2, cy + h / 2),
            (cx - w / 2, cy + h / 2),
        ]

    def arm_polygon(a, b, width):
        ax, ay = a
        bx, by = b
        dx, dy = bx - ax, by - ay
        mag = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / mag * width / 2, dx / mag * width / 2
        return [(ax + nx, ay + ny), (bx + nx, by + ny), (bx - nx, by - ny), (ax - nx, ay - ny)]

    def area(poly):
        return abs(sum(
            poly[i][0] * poly[(i + 1) % len(poly)][1] -
            poly[(i + 1) % len(poly)][0] * poly[i][1]
            for i in range(len(poly))
        ) / 2)

    # Drone-frame-like rigid PCB outline:
    # central electronics island + four radial arms + four PZT front-end islands.
    # KiCad needs one non-self-intersecting outer boundary, so we collect the
    # important outer vertices and emit one clockwise skeleton polygon.
    center_rect = rect_points(0, 5, 54, 62)
    outline_pts = [
        (-27, -26), (27, -26),
    ]
    outline_area = 54 * 62

    # M2 clearance holes from the OpenSCAD sweet-zone line.
    for i, y in enumerate([-18, 33], 1):
        fp = make_fp(f"MH{i}", "M2_NPTH", 0, y)
        add_through_hole(fp, "", (0, 0), 2.2, 3.0, None)
        board.Add(fp)

    def j1_pin(pin):
        pitch = 1.27
        if pin <= 14:
            i = pin - 1
            return ((i - 6.5) * pitch, 13 + 8.75)
        i = pin - 15
        return (-((i - 6.5) * pitch), 13 - 8.75)

    # ESP32-C6-WROOM-1 embedded carrier cutout. The board edge passes through
    # each plated hole center, yielding complementary half-hole pads after fab.
    j1_cutout = (3.0, 13.0, 27.0, 17.5)
    j1 = make_fp("J1", "ESP32-C6-WROOM-1_CUTOUT", 0, 0)
    j1_nets = {
        1: gnd, 2: vcc, 3: en,
        4: N("PZT_TR_SIGNAL"), 5: N("PZT_TL_SIGNAL"),
        6: N("PZT_BR_SIGNAL"), 7: N("PZT_BL_SIGNAL"),
        8: N("LED_DATA"), 9: N("BOOT"), 10: N("USER_BTN"),
        11: N("PWR_LATCH"), 13: N("USB_D+"), 16: N("USB_D-"),
        24: N("UART_TX"), 25: N("UART_RX"), 28: gnd,
    }
    for pin in range(1, 29):
        p = add_castellated(j1, pin, j1_pin(pin), j1_nets.get(pin))
        rec("J1", pin, p)
    board.Add(j1)
    rect_graphic(pcbnew.Eco1_User, *j1_cutout, 0.12)

    # IM948 embedded carrier cutout.
    imu_x, imu_y = 0, -6.0
    imu_w, imu_h = 18.5, 13.0
    imu_pitch = 2.0
    imu_row = imu_h / 2
    imu_fp = make_fp("U1", "IM948_CUTOUT", imu_x, imu_y)
    imu_bottom = ["GND", "VBUS", "VBAT", "NC", "NC", "NC", "NC", "GND"]
    imu_top = ["NC", "NC", "IMU_GPIO", "IMU_KEY", "UART_TX", "UART_RX", "VBAT", "GND"]
    for i, nn in enumerate(imu_bottom):
        x = (i - 3.5) * imu_pitch
        p = add_castellated(imu_fp, i + 1, (x, -imu_row), N(nn), drill=0.75, size=1.30)
        rec("U1", i + 1, p)
    for i, nn in enumerate(imu_top):
        x = (i - 3.5) * imu_pitch
        p = add_castellated(imu_fp, i + 9, (x, imu_row), N(nn), drill=0.75, size=1.30)
        rec("U1", i + 9, p)
    board.Add(imu_fp)
    rect_graphic(pcbnew.Eco1_User, imu_x, imu_y, imu_w, imu_h, 0.12)

    # Handle wire pads.
    wire_pad("TP_BAT", "BAT+", -17, 54, vbat_in)
    wire_pad("TP_GND", "GND", -8.5, 54, gnd)
    wire_pad("TP_LEDV", "LED+", 0, 54, vbat)
    wire_pad("TP_LEDD", "LED_DIN", 8.5, 54, N("LED_DIN"))
    wire_pad("TP_BTN", "BTN", 17, 54, N("BTN_SW"))
    wire_pad("TP_DP", "D+", 8.5, 48, N("USB_D+"))
    wire_pad("TP_DN", "D-", 17, 48, N("USB_D-"))

    # Power and control parts.
    sot23("Q_PWR", "AO3401", -17, 26, {1: N("P_GATE"), 2: vbat_in, 3: vbat}, 90)
    sot23("Q_LATCH", "2N7002", -17, 18, {1: N("PWR_LATCH"), 2: gnd, 3: N("P_GATE")}, 90)
    two_pad("R_GATE", "100k", -22, 28, N("P_GATE"), vbat_in)
    two_pad("D_BTN", "1N4148", -12, 28, N("P_GATE"), N("BTN_SW"))
    two_pad("R_BTN", "100k", -14, 20, N("BTN_SW"), N("USER_BTN"), 90)
    two_pad("R_LATCH_PD", "100k", -22, 15, N("PWR_LATCH"), gnd)

    sot23_5("U3", "AP2112K-3.3", -17, 7, {1: vbat, 2: gnd, 3: vbat, 5: vcc}, 90)
    two_pad("C_IN", "10uF", -22, 6, vbat, gnd)
    two_pad("C_OUT", "10uF", -12, 6, vcc, gnd)
    two_pad("C_LED", "100nF", 14, 30, vbat, gnd)
    two_pad("R_LED", "330R", 12, 25, N("LED_DATA"), N("LED_DIN"), 90)
    two_pad("R_EN", "10k", -6, 25, en, vcc)

    wire_pad("TP_BOOT", "BOOT", 22, 22, N("BOOT"))
    wire_pad("TP_EN", "EN", 22, 17, en)
    wire_pad("TP_IMUK", "IMU_KEY", -14, -18, N("IMU_KEY"))
    wire_pad("TP_IMUG", "IMU_GPIO", -19, -18, N("IMU_GPIO"))

    # PZT front-end islands and pads.
    pzt_info = {}
    for pzt in params["components"]["piezo"]:
        pid = pzt["id"]
        x, y0 = pzt["position"]
        y = -y0
        sn = N(f"{pid}_SIGNAL")
        dx, dy = -x, 5 - y
        mag = math.hypot(dx, dy) or 1
        ux, uy = dx / mag, dy / mag
        nx, ny = -uy, ux
        sig = (x + ux * 8, y + uy * 8)
        g = (x + ux * 8 + nx * 6.5, y + uy * 8 + ny * 6.5)
        wire_pad(pid, pid, sig[0], sig[1], sn)
        wire_pad(f"{pid}_G", "PZT_G", g[0], g[1], gnd)
        pzt_info[pid] = {"p": (x, y), "sig": sig, "gnd": g, "u": (ux, uy), "n": (nx, ny)}

        rpos = (x + ux * 14 + nx * 2.2, y + uy * 14 + ny * 2.2)
        dpos = (x + ux * 17 - nx * 2.2, y + uy * 17 - ny * 2.2)
        island_cx = (sig[0] + g[0] + rpos[0] + dpos[0]) / 4
        island_cy = (sig[1] + g[1] + rpos[1] + dpos[1]) / 4
        island = convex_hull(
            rect_points(sig[0], sig[1], 6.5, 5.0) +
            rect_points(g[0], g[1], 6.5, 5.0) +
            rect_points(rpos[0], rpos[1], 5.5, 4.0) +
            rect_points(dpos[0], dpos[1], 6.0, 4.5)
        )
        arm_start = (23 if island_cx > 0 else -23, 22 if island_cy > 0 else -22)
        arm = arm_polygon(arm_start, (island_cx, island_cy), 11.0)
        outline_area += area(arm) + area(island)
        pzt_info[pid]["island"] = island
        pzt_info[pid]["center"] = (island_cx, island_cy)
        rot = math.degrees(math.atan2(uy, ux)) + 90
        two_pad(f"R_{pid}", "1M", rpos[0], rpos[1], sn, gnd, rot)
        dfp = sot23(f"D_{pid}", "BAT54S", dpos[0], dpos[1], {1: sn, 2: gnd, 3: vcc}, rot)

    # One continuous concave outline: central island with four broad arms.
    # This is intentionally shaped like a drone frame instead of a solid panel.
    skeleton = [
        (-50, -58), (-22, -54), (22, -54), (50, -58),
        (45, -34), (32, -29), (28, -22), (28, 32),
        (36, 34), (52, 34), (48, 58), (22, 58),
        (22, 40), (-22, 40), (-22, 58), (-48, 58),
        (-52, 34), (-36, 34), (-28, 32), (-28, -22),
        (-32, -29), (-45, -34),
    ]
    outline_area = area(skeleton)
    poly_edge(skeleton)
    rect_edge(*j1_cutout)
    rect_edge(imu_x, imu_y, imu_w, imu_h)

    approx_area = outline_area - j1_cutout[2] * j1_cutout[3] - imu_w * imu_h
    approx_mass_g = approx_area / 100 * 0.08 * 1.85
    print(f"Rigid skeleton outline area ~= {outline_area:.1f} mm^2, FR4 0.8mm ~= {approx_mass_g:.1f} g")

    # Main signal routes. Keep the first rigid-PCB output placement-oriented;
    # earlier straight-line routing created many artificial shorts. The intended
    # connections are preserved below for the next routed iteration.
    ROUTE_STUDY = False
    if ROUTE_STUDY:
        connect(vbat_in, [pins[("TP_BAT", 1)], (-17, 48), pins[("Q_PWR", 2)]], TRACE_MAIN_PWR)
        connect(vbat, [pins[("Q_PWR", 3)], pins[("U3", 1)]], TRACE_PWR)
        connect(vbat, [pins[("Q_PWR", 3)], (0, 37), pins[("TP_LEDV", 1)]], TRACE_MAIN_PWR)
        connect(vcc, [pins[("U3", 5)], pins[("J1", 2)]], TRACE_PWR)
        connect(vcc, [pins[("U3", 5)], pins[("C_OUT", 1)]], TRACE_PWR)
        connect(vbat, [pins[("U3", 1)], pins[("C_IN", 1)]], TRACE_PWR)
        connect(en, [pins[("J1", 3)], pins[("R_EN", 1)], pins[("TP_EN", 1)]], TRACE_SIG)
        connect(vcc, [pins[("R_EN", 2)], pins[("J1", 2)]], TRACE_PWR)

        connect(N("P_GATE"), [pins[("Q_PWR", 1)], pins[("R_GATE", 1)], pins[("D_BTN", 1)], pins[("Q_LATCH", 3)]])
        connect(vbat_in, [pins[("R_GATE", 2)], pins[("Q_PWR", 2)]], TRACE_PWR)
        connect(N("BTN_SW"), [pins[("TP_BTN", 1)], pins[("D_BTN", 2)], pins[("R_BTN", 1)]])
        connect(N("USER_BTN"), [pins[("R_BTN", 2)], pins[("J1", 10)]])
        connect(N("PWR_LATCH"), [pins[("J1", 11)], pins[("Q_LATCH", 1)], pins[("R_LATCH_PD", 1)]])

        connect(N("LED_DATA"), [pins[("J1", 8)], pins[("R_LED", 1)]])
        connect(N("LED_DIN"), [pins[("R_LED", 2)], pins[("TP_LEDD", 1)]])
        connect(vbat, [pins[("TP_LEDV", 1)], pins[("C_LED", 1)]], TRACE_PWR)
        connect(N("BOOT"), [pins[("J1", 9)], pins[("TP_BOOT", 1)]])

        connect(N("USB_D+"), [pins[("TP_DP", 1)], pins[("J1", 13)]])
        connect(N("USB_D-"), [pins[("TP_DN", 1)], pins[("J1", 16)]])
        connect(N("UART_TX"), [pins[("J1", 24)], pins[("U1", 13)]])
        connect(N("UART_RX"), [pins[("J1", 25)], pins[("U1", 14)]])
        connect(vbat, [pins[("U1", 3)], pins[("U1", 15)], pins[("U3", 1)]], TRACE_PWR)
        connect(N("IMU_KEY"), [pins[("U1", 12)], pins[("TP_IMUK", 1)]])
        connect(N("IMU_GPIO"), [pins[("U1", 11)], pins[("TP_IMUG", 1)]])

    pzt_pins = {"PZT_TR": 4, "PZT_TL": 5, "PZT_BR": 6, "PZT_BL": 7}
    lanes = {"PZT_TR": (30, -5), "PZT_TL": (-30, -5), "PZT_BR": (32, 34), "PZT_BL": (-32, 34)}
    for pid, pin in pzt_pins.items():
        sn = N(f"{pid}_SIGNAL")
        p = pins[(pid, 1)]
        r1 = pins[(f"R_{pid}", 1)]
        d1 = pins[(f"D_{pid}", 1)]
        if ROUTE_STUDY:
            connect(sn, [p, r1, d1])
        lane_x, lane_y = lanes[pid]
        if ROUTE_STUDY:
            connect(sn, [d1, (lane_x, d1[1]), (lane_x, lane_y), pins[("J1", pin)]], TRACE_SIG, pcbnew.B_Cu)
            via(sn, lane_x, d1[1])
            via(sn, lane_x, lane_y)

    # 3.3V clamp rail to each BAT54S.
    for pid in pzt_pins:
        if ROUTE_STUDY:
            connect(vcc, [pins[("U3", 5)], (0, 40), (pins[(f"D_{pid}", 3)][0], 40), pins[(f"D_{pid}", 3)]],
                    TRACE_PWR, pcbnew.B_Cu)
            via(vcc, pins[(f"D_{pid}", 3)][0], 40)

    # GND stitching: use B.Cu zone and local vias.
    for key, pos in list(pins.items()):
        if key[0].endswith("_G") or key in [
            ("Q_LATCH", 2), ("R_LATCH_PD", 2), ("U3", 2),
            ("C_IN", 2), ("C_OUT", 2), ("C_LED", 2),
        ]:
            via(gnd, *pos)

    # GND zone.
    zone = pcbnew.ZONE(board)
    zone.SetNet(gnd)
    zone.SetLayer(pcbnew.B_Cu)
    zone.SetIsRuleArea(False)
    zone.SetAssignedPriority(0)
    outline = zone.Outline()
    outline.NewOutline()
    for x, y in skeleton:
        outline.Append(mk(x), mk(y))
    zone.SetFillMode(pcbnew.ZONE_FILL_MODE_POLYGONS)
    zone.SetHatchStyle(0)
    zone.SetMinThickness(mk(0.2))
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    board.Add(zone)

    pcbnew.SaveBoard(str(OUTPUT_FILE), board)
    fill = PROJECT_ROOT / "fpc" / "fill_zones.py"
    subprocess.run([sys.executable, str(fill), str(OUTPUT_FILE)], check=False)
    print(f"Wrote {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

"""SmartPaddle FPC v9.0 — Y 轴自动翻转 + net 保存修复
═══════════════════════════════════════════════════
A. Y 轴不翻转: SCAD +Y=拍头 ↔ KiCad +Y=屏上, 原坐标直接使用
B. J1: ESP32-C6 14+14=28邮票孔, 18×25.5mm
C. IMU: IM948 8+8=16邮票孔, UART
D. 终端焊盘: 4×3mm, D+/D- → IO19/IO18
E. IMU Y=+6 (拍头甜区) / MCU Y=-20 (拍柄方向) 间隙4mm
F. KiCad 9.0.6 Save bug 后处理修复
"""

import yaml, sys, subprocess, math, re, uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
YAML_PATH    = PROJECT_ROOT / "shared" / "board_params.yaml"
OUTPUT_DIR   = Path(__file__).resolve().parent / "layouts" / "default"
OUTPUT_FILE  = OUTPUT_DIR / "default.kicad_pcb"

TRACE_SIG = 0.2; TRACE_PWR = 0.3
VIA_DRILL = 0.3; VIA_PAD   = 0.6


def main():
    import pcbnew; b = pcbnew.BOARD()
    ds = b.GetDesignSettings(); ds.SetBoardThickness(int(0.2e6))
    ds.m_CopperLayerCount = 2

    with open(YAML_PATH) as f: params = yaml.safe_load(f)

    # ═══════════════════════════════════════════════
    # 坐标系约定: OpenSCAD 与 KiCad 一致
    #   SCAD:   +Y = 拍头 (拍尖 Y=+78.5)   /   -Y = 拍柄 (Y=-78.5)
    #   KiCad:  +Y = 屏幕上方
    # 因此 SCAD 原坐标直接使用: 拍头在屏上方 ✓
    # ═══════════════════════════════════════════════

    nets = {}
    def N(n):
        if n not in nets:
            nets[n] = pcbnew.NETINFO_ITEM(b, n); b.Add(nets[n])
        return nets[n]
    gnd = N("GND"); vcc = N("VCC")
    N("USB_D+"); N("USB_D-"); N("UART_RX"); N("UART_TX")
    N("PZT_TR_SIGNAL"); N("PZT_TL_SIGNAL"); N("PZT_BR_SIGNAL"); N("PZT_BL_SIGNAL")

    def mk(x): return int(x * 1e6)

    # ═══════════════════════════════════════════════
    # 板外形数据
    # ═══════════════════════════════════════════════
    bp = params["board"]; raw = bp["bezier_blade_poly"]
    wt = bp["wall_thickness"]; inset = wt + 0.5
    opts = []
    for x,y in raw:
        ax = abs(x); nx = (ax-inset) if ax>inset+0.5 else 0
        opts.append((nx if x>=0 else -nx, y))

    # ── FP 构建器 ──
    def pad(fp, nr, pos, sz, net, shape=pcbnew.PAD_SHAPE_CIRCLE):
        p = pcbnew.PAD(fp); p.SetNumber(str(nr)); p.SetShape(shape)
        p.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        p.SetPosition(pcbnew.VECTOR2I(mk(pos[0]), mk(pos[1])))
        p.SetSize(pcbnew.VECTOR2I(mk(sz[0]), mk(sz[1])))
        p.SetNet(net); ls = pcbnew.LSET()
        for ly in [pcbnew.F_Cu,pcbnew.F_Paste,pcbnew.F_Mask]: ls.addLayer(ly)
        p.SetLayerSet(ls); fp.Add(p)

    track_records = []  # (net_name, x1, y1, x2, y2, width)

    def track(net,x1,y1,x2,y2,w=TRACE_SIG):
        t=pcbnew.PCB_TRACK(b); t.SetLayer(pcbnew.F_Cu); t.SetNet(net)
        t.SetStart(pcbnew.VECTOR2I(mk(x1),mk(y1)))
        t.SetEnd(pcbnew.VECTOR2I(mk(x2),mk(y2)))
        t.SetWidth(mk(w)); b.Add(t)
        nn = net.GetNetname() if hasattr(net,'GetNetname') else str(net)
        track_records.append((nn, x1, y1, x2, y2, w))

    def via(net,x,y):
        v=pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(mk(x),mk(y)))
        v.SetNet(net); v.SetWidth(mk(VIA_PAD)); v.SetDrill(mk(VIA_DRILL)); b.Add(v)

    def gfx_rect(layer,x1,y1,x2,y2,w=0.05):
        g=pcbnew.PCB_SHAPE(b); g.SetShape(pcbnew.SHAPE_T_RECT)
        g.SetStart(pcbnew.VECTOR2I(mk(x1),mk(y1)))
        g.SetEnd(pcbnew.VECTOR2I(mk(x2),mk(y2)))
        g.SetLayer(layer); g.SetWidth(int(w*1e6)); b.Add(g)

    def gfx_circle(layer,cx,cy,r,w=0.05):
        g=pcbnew.PCB_SHAPE(b); g.SetShape(pcbnew.SHAPE_T_CIRCLE)
        g.SetCenter(pcbnew.VECTOR2I(mk(cx),mk(cy)))
        g.SetEnd(pcbnew.VECTOR2I(mk(cx+r),mk(cy)))
        g.SetLayer(layer); g.SetWidth(int(w*1e6)); b.Add(g)

    def silk_text(x,y,txt,sz=1.0,th=0.12,rot=0):
        tx=pcbnew.PCB_TEXT(b); tx.SetText(txt)
        tx.SetPosition(pcbnew.VECTOR2I(mk(x),mk(y)))
        tx.SetLayer(pcbnew.F_SilkS)
        tx.SetTextSize(pcbnew.VECTOR2I(mk(sz),mk(sz)))
        tx.SetTextThickness(mk(th))
        if rot: tx.SetTextAngle(pcbnew.EDA_ANGLE(rot, pcbnew.DEGREES_T))
        b.Add(tx)

    def make_fp(ref, val, gx, gy):
        f=pcbnew.FOOTPRINT(b); f.SetReference(ref); f.SetValue(val)
        f.SetLayer(pcbnew.F_Cu)
        f.SetPosition(pcbnew.VECTOR2I(mk(gx), mk(gy)))
        return f

    def fab_rect(fp, gx, gy, lx, ly, w, h):
        g=pcbnew.PCB_SHAPE(fp); g.SetShape(pcbnew.SHAPE_T_RECT)
        g.SetStart(pcbnew.VECTOR2I(mk(lx-w/2), mk(ly-h/2)))
        g.SetEnd(pcbnew.VECTOR2I(mk(lx+w/2), mk(ly+h/2)))
        g.SetLayer(pcbnew.F_Fab); g.SetWidth(int(0.1e6)); fp.Add(g)

    def crtyd_rect(fp, gx, gy, lx, ly, w, h, margin=0.5):
        g=pcbnew.PCB_SHAPE(fp); g.SetShape(pcbnew.SHAPE_T_RECT)
        g.SetStart(pcbnew.VECTOR2I(mk(lx-w/2-margin), mk(ly-h/2-margin)))
        g.SetEnd(pcbnew.VECTOR2I(mk(lx+w/2+margin), mk(ly+h/2+margin)))
        g.SetLayer(pcbnew.F_CrtYd); g.SetWidth(int(0.05e6)); fp.Add(g)

    def fab_circle(fp, gx, gy, lx, ly, r):
        c=pcbnew.PCB_SHAPE(fp); c.SetShape(pcbnew.SHAPE_T_CIRCLE)
        c.SetCenter(pcbnew.VECTOR2I(mk(lx), mk(ly)))
        c.SetEnd(pcbnew.VECTOR2I(mk(lx+r), mk(ly)))
        c.SetLayer(pcbnew.F_Fab); c.SetWidth(int(0.1e6)); fp.Add(c)

    pp = {}
    def Rec(ref,pn,gx,gy): pp[(ref,pn)]=(gx,gy)

    # ═══════════════════════════════════════════════
    # PZT 焊盘 + 耳槽角度
    # ═══════════════════════════════════════════════
    mc_mod  = params["components"]["main_module"]
    mc_c    = mc_mod["center"]
    cx, cy  = mc_c[0], mc_c[1]          # 槽中心 (cx,cy) = (0,-5)，用于耳角等
    mc_y    = -20                       # MCU Y=-20 (拍柄方向: 顶-7.25,底-32.75)
    ear     = {}

    for pzt in params["components"]["piezo"]:
        pid = pzt["id"]; px,py = pzt["position"]; dia = pzt["cavity_diameter"]
        sn = N(f"{pid}_SIGNAL")
        ang = math.degrees(math.atan2(cy-py, cx-px))
        ear[pid] = ang

        fp = make_fp(pid, "PZT-5A", px, py)
        pad(fp, 1, (0,0), (8,8), sn)
        pad(fp, 2, (9.5,0), (3,3), gnd)
        fab_circle(fp, px, py, 0, 0, dia/2)
        crtyd_rect(fp, px, py, 0, 0, dia+1, dia+1)
        b.Add(fp); Rec(pid, 1, px, py); Rec(pid, 2, px+9.5, py)
        gfx_circle(pcbnew.F_SilkS, px, py, dia/2, 0.12)
        silk_text(px, py-12, pid, 1.2, 0.15)

    # ═══════════════════════════════════════════════
    # 信号调理 — 耳槽方向
    # ═══════════════════════════════════════════════
    pzt_list = params["components"]["piezo"]
    for sc in params["components"]["signal_conditioning"]:
        pid = sc["piezo"]; sn = N(f"{pid}_SIGNAL"); ang = ear[pid]
        pzx = [p["position"][0] for p in pzt_list if p["id"]==pid][0]
        pzy = [p["position"][1] for p in pzt_list if p["id"]==pid][0]

        piezo_d = 20.5; ear_l = 8.0
        off_r = piezo_d/2 + ear_l/2 - 2
        rad = math.radians(ang)
        rx = pzx + off_r * math.cos(rad)
        ry = pzy + off_r * math.sin(rad)

        rf = make_fp(f"R_{pid}", "1M", rx, ry)
        rf.SetOrientationDegrees(ang + 90)
        pad(rf, 1, (0, 0.8), (1.0, 0.7), sn, pcbnew.PAD_SHAPE_RECT)
        pad(rf, 2, (0, -0.8), (1.0, 0.7), gnd, pcbnew.PAD_SHAPE_RECT)
        fab_rect(rf, rx, ry, 0, 0, 1.6, 0.8); crtyd_rect(rf, rx, ry, 0, 0, 1.6, 0.8)
        b.Add(rf)
        ca=math.cos(rad+math.pi/2); sa=math.sin(rad+math.pi/2)
        Rec(f"R_{pid}",1,rx+0.8*ca,ry+0.8*sa); Rec(f"R_{pid}",2,rx-0.8*ca,ry-0.8*sa)

        doff = off_r + 2.5
        dx = pzx + doff*math.cos(rad); dy = pzy + doff*math.sin(rad)
        df = make_fp(f"D_{pid}", "BAT54S", dx, dy)
        df.SetOrientationDegrees(ang + 90)
        pad(df, 1, (0, 1.0), (0.7, 0.6), sn, pcbnew.PAD_SHAPE_RECT)
        pad(df, 2, (0, -1.0), (0.7, 0.6), gnd, pcbnew.PAD_SHAPE_RECT)
        pad(df, 3, (1.0, 0), (0.7, 0.6), vcc, pcbnew.PAD_SHAPE_RECT)
        fab_rect(df, dx, dy, 0, 0, 1.7, 1.25); crtyd_rect(df, dx, dy, 0, 0, 1.7, 1.25)
        b.Add(df)
        Rec(f"D_{pid}",1,dx+1.0*ca,dy+1.0*sa); Rec(f"D_{pid}",2,dx-1.0*ca,dy-1.0*sa)
        Rec(f"D_{pid}",3,dx,dy)

    # ═══════════════════════════════════════════════
    # IM948 IMU — 16 邮票孔, UART 通信
    # ═══════════════════════════════════════════════
    imu_x, imu_y = 0, 6                # 拍头方向 (IMU 底-3.25,顶15.25, 槽顶16, 距MCU顶4mm)
    iw, ih = 13.0, 18.5                # IM948: 宽13 × 高18.5mm
    imu_pitch = 1.27; imu_n = 8        # 每侧8脚
    imu_hw = iw / 2; imu_hh = ih / 2
    imu_span = (imu_n - 1) * imu_pitch / 2  # 4.445mm

    imu_fp = make_fp("U1", "IM948", imu_x, imu_y)
    # 左侧引脚 (X=-6.5): 1-VSS,2-VBUS(NC),3-VBAT,4-VDDIO(NC),5-NC,6-NC,7-ADIN(NC),8-VSS
    for i in range(imu_n):
        yo = (i - (imu_n - 1) / 2) * imu_pitch
        ln = [gnd, vcc, vcc, vcc, vcc, vcc, vcc, gnd][i]   # 简化: 只连 VSS→GND, VBAT→VCC
        pad(imu_fp, i + 1, (-imu_hw, yo), (1.5, 0.8), ln, pcbnew.PAD_SHAPE_RECT)
        Rec("U1", i + 1, imu_x - imu_hw, imu_y + yo)
    # 右侧引脚 (X=+6.5): 9-LED_B(NC),10-LED_R(NC),11-GPIO(NC),12-KEY(NC),13-RXD,14-TXD,15-VBAT,16-VSS
    for i in range(imu_n):
        yo = (i - (imu_n - 1) / 2) * imu_pitch
        rnet = [vcc, vcc, vcc, vcc, N("UART_TX"), N("UART_RX"), vcc, gnd][i]
        pad(imu_fp, i + imu_n + 1, (imu_hw, yo), (1.5, 0.8), rnet, pcbnew.PAD_SHAPE_RECT)
        Rec("U1", i + imu_n + 1, imu_x + imu_hw, imu_y + yo)
    fab_rect(imu_fp, imu_x, imu_y, 0, 0, iw, ih)
    crtyd_rect(imu_fp, imu_x, imu_y, 0, 0, iw, ih)
    b.Add(imu_fp)
    gfx_rect(pcbnew.F_SilkS, imu_x - imu_hw - 1, imu_y - imu_hh - 1,
             imu_x + imu_hw + 1, imu_y + imu_hh + 1, 0.12)
    silk_text(imu_x, imu_y - imu_hh - 2, "IM948 IMU", 1.0, 0.12)
    silk_text(imu_x - 5, imu_y + imu_span + 1.5, "RXD\u2190Pin13", 0.6, 0.1)
    silk_text(imu_x + 2, imu_y + imu_span + 1.5, "TXD\u2192Pin14", 0.6, 0.1)

    # ═══════════════════════════════════════════════
    # MCU J1 — ESP32-C6-WROOM-1-N8 14+14=28邮票孔
    # ═══════════════════════════════════════════════
    fw = mc_mod["footprint_width"]; fh = mc_mod["footprint_height"]
    pitch = 1.27; n_per_edge = 14; half_w = fw / 2
    half_span = (n_per_edge - 1) * pitch / 2  # 8.255mm
    cf = make_fp("J1", "ESP32-C6", cx, mc_y)

    # 左侧引脚 1-14 (X = -half_w = -9mm)
    l_net = [
        "GND",            # 1: GND
        "VCC",            # 2: 3V3 供电
        "GND",            # 3: EN → GND (内部上拉, 不悬空)
        "GND",            # 4: IO0 → GND
        "PZT_TR_SIGNAL",  # 5: IO1/ADC1_CH0
        "PZT_TL_SIGNAL",  # 6: IO2/ADC1_CH1
        "PZT_BR_SIGNAL",  # 7: IO3/ADC1_CH2
        "PZT_BL_SIGNAL",  # 8: IO4/ADC1_CH3
        "GND",            # 9: IO5
        "GND",            # 10: IO6
        "GND",            # 11: IO7
        "GND",            # 12: IO8
        "GND",            # 13: IO9
        "GND",            # 14: IO10
    ]
    # 右侧引脚 15-28 (X = +half_w = +9mm)
    r_net = [
        "GND",            # 15: IO11
        "GND",            # 16: IO12
        "GND",            # 17: IO13
        "GND",            # 18: IO14
        "GND",            # 19: IO15
        "USB_D-",         # 20: IO18/USB_D- → 引出焊盘
        "USB_D+",         # 21: IO19/USB_D+ → 引出焊盘
        "GND",            # 22: IO20
        "GND",            # 23: IO21
        "GND",            # 24: IO22
        "GND",            # 25: IO23
        "GND",            # 26: NC
        "UART_RX",        # 27: IO17/U0RXD ← IMU TXD(14)
        "UART_TX",        # 28: IO16/U0TXD → IMU RXD(13)
    ]
    for i in range(n_per_edge):
        yo = (i - (n_per_edge - 1) / 2) * pitch
        pad(cf, i + 1, (-half_w, yo), (1.5, 0.8),
            N(l_net[i]), pcbnew.PAD_SHAPE_RECT)
        pad(cf, i + n_per_edge + 1, (half_w, yo), (1.5, 0.8),
            N(r_net[i]), pcbnew.PAD_SHAPE_RECT)
        Rec("J1", i + 1, cx - half_w, mc_y + yo)
        Rec("J1", i + n_per_edge + 1, cx + half_w, mc_y + yo)
    # EPAD 29 — 中心接地焊盘
    pad(cf, 29, (0, 0), (12, 16), gnd, pcbnew.PAD_SHAPE_RECT)
    Rec("J1", 29, cx, mc_y)

    fab_rect(cf, cx, mc_y, 0, 0, fw, fh)
    crtyd_rect(cf, cx, mc_y, 0, 0, fw, fh)
    b.Add(cf)
    gfx_rect(pcbnew.F_SilkS, cx - half_w - 1, mc_y - fh / 2 - 1,
             cx + half_w + 1, mc_y + fh / 2 + 1, 0.12)
    silk_text(cx, mc_y + fh / 2 + 2, "ESP32-C6", 1.0, 0.12)

    # ═══════════════════════════════════════════════
    # 拍柄末端引出焊盘 (修正 B:4×3mm + C:文字90°)
    # ═══════════════════════════════════════════════
    all_y = [y for _,y in opts]
    bot_y = min(all_y) + 2    # 拍柄端在 Y 最小处
    term = [("VCC",-5.5),("GND",-2),("D+",2),("D-",5.5)]
    term_w, term_h = 4.0, 3.0
    for label,xo in term:
        nn = "VCC" if label=="VCC" else "GND" if label=="GND" else f"USB_{label}"
        tf = make_fp(f"TP_{label}", label, xo, bot_y)
        pad(tf, 1, (0,0), (term_w, term_h), N(nn), pcbnew.PAD_SHAPE_RECT)
        fab_rect(tf, xo, bot_y, 0, 0, term_w, term_h)
        crtyd_rect(tf, xo, bot_y, 0, 0, term_w, term_h)
        b.Add(tf); Rec(f"TP_{label}", 1, xo, bot_y)
        silk_text(xo+3.5, bot_y, label, 0.9, 0.12, rot=90)
    silk_text(0, bot_y+6, "\u2192 \u62CD\u67C4\u65B9\u5411", 0.9, 0.12)

    # ═══════════════════════════════════════════════
    # 标注层
    # ═══════════════════════════════════════════════
    for cov in params["coverlay_openings"]:
        if cov["zone"] == "PZT_electrodes":
            for pzt in params["components"]["piezo"]:
                gfx_circle(pcbnew.User_1, pzt["position"][0], pzt["position"][1],
                           pzt["cavity_diameter"]/2, 0.05)
        elif cov["zone"] == "connector_fingers":
            gfx_rect(pcbnew.User_1, cx-fw/2, mc_y-fh/2, cx+fw/2, mc_y+fh/2, 0.05)

    for stiff in params["stiffeners"]:
        zone = stiff["zone"]
        if zone == "PZT_pads_all":
            for pzt in params["components"]["piezo"]:
                px,py = pzt["position"]
                gfx_rect(pcbnew.User_3, px-12.5, py-12.5, px+12.5, py+12.5, 0.05)
        elif zone == "signal_conditioning":
            for sc in params["components"]["signal_conditioning"]:
                pid = sc["piezo"]; ang = ear[pid]; rad = math.radians(ang)
                pzx = [p["position"][0] for p in pzt_list if p["id"]==pid][0]
                pzy = [p["position"][1] for p in pzt_list if p["id"]==pid][0]
                off = 20.5/2 + 8.0/2 - 2 + 1.25
                csx = pzx + off*math.cos(rad); csy = pzy + off*math.sin(rad)
                gfx_rect(pcbnew.User_3, csx-6, csy-4, csx+6, csy+4, 0.05)
        elif zone == "main_module_connector":
            gfx_rect(pcbnew.User_3, cx-25, mc_y-25, cx+25, mc_y+25, 0.05)

    for koz in params.get("keep_out_zones", []):
        cr = koz.get("clearance_radius", 3.5)
        for hx,hy in koz.get("positions", []):
            gfx_circle(pcbnew.User_4, hx, hy, cr, 0.05)

    for koz in params.get("keep_out_zones", []):
        tp = koz.get("type","")
        label = "\u9500\u5B54" if "pin" in tp else "\u87BA\u4E1D" if "screw" in tp else ""
        if label:
            for hx,hy in koz.get("positions", []):
                silk_text(hx, hy-3.5, label, 0.7, 0.1)

    # ═══════════════════════════════════════════════
    # 走线
    # ═══════════════════════════════════════════════
    NECK_Y1 = -71.7; NECK_Y2 = -78.5   # 拍头→拍柄 肩膀区域
    SPINE_L = -22; SPINE_R = 22

    def route_signal(pid, spine_x, pin):
        sn = N(f"{pid}_SIGNAL")
        d1 = pp[(f"D_{pid}",1)]; jp = pp[("J1",pin)]
        neck_x = max(-8, min(8, spine_x))
        mid_y = min(d1[1], NECK_Y1) - 5    # 中转线在 MCU 之上
        pts = [(d1[0],d1[1]),(d1[0],mid_y),(spine_x,mid_y),
               (spine_x,NECK_Y2+2),(neck_x,NECK_Y2+2),(jp[0],NECK_Y2+2),(jp[0],jp[1])]
        for i in range(len(pts)-1):
            track(sn, pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1])

    def route_vcc(pid, spine_x, pin):
        j1v = pp[("J1",pin)]; d3 = pp[(f"D_{pid}",3)]
        neck_x = max(-8, min(8, spine_x))
        pts = [(j1v[0],j1v[1]),(j1v[0],NECK_Y2+2),(neck_x,NECK_Y2+2),
               (spine_x,NECK_Y2+2),(spine_x,NECK_Y1),(spine_x,d3[1]),(d3[0],d3[1])]
        for i in range(len(pts)-1):
            track(vcc, pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1], TRACE_PWR)

    # PZT 信号 → J1 ADC 引脚: IO1(5), IO2(6), IO3(7), IO4(8)
    route_signal("PZT_TR", SPINE_R, 5); route_vcc("PZT_TR", SPINE_R+4, 2)
    route_signal("PZT_BR", SPINE_R, 7); route_vcc("PZT_BR", SPINE_R+4, 2)
    route_signal("PZT_TL", SPINE_L, 6); route_vcc("PZT_TL", SPINE_L-4, 2)
    route_signal("PZT_BL", SPINE_L, 8); route_vcc("PZT_BL", SPINE_L-4, 2)

    # UART: IMU(13:RXD←), IMU(14:TXD→) ↔ J1(27:IO17/RX), J1(28:IO16/TX)
    u1_rxd = pp[("U1", 13)]; u1_txd = pp[("U1", 14)]
    j1_tx  = pp[("J1", 28)]  # IO16 → IMU RXD  (右侧pin28)
    j1_rx  = pp[("J1", 27)]  # IO17 ← IMU TXD  (右侧pin27)
    # 汇流点: IMU 底与 MCU 顶之间 (拍头方向)
    jy = mc_y + fh/2 + 2        # MCU 顶=-7.25, jy=-5.25
    # TX: IMU pin13(6.5,10.45) → 下到 jy → 横走到 pin28
    track(N("UART_TX"), u1_rxd[0], u1_rxd[1], u1_rxd[0], jy)
    track(N("UART_TX"), u1_rxd[0], jy, j1_tx[0], jy)
    track(N("UART_TX"), j1_tx[0], jy, j1_tx[0], j1_tx[1])
    # RX: IMU pin14(6.5,7.91) → 下到 jy-0.5 → 横走到 pin27
    track(N("UART_RX"), u1_txd[0], u1_txd[1], u1_txd[0], jy-0.5)
    track(N("UART_RX"), u1_txd[0], jy-0.5, j1_rx[0], jy-0.5)
    track(N("UART_RX"), j1_rx[0], jy-0.5, j1_rx[0], j1_rx[1])

    for sc in params["components"]["signal_conditioning"]:
        pid = sc["piezo"]; sn = N(f"{pid}_SIGNAL")
        p1=pp[(pid,1)]; r1=pp[(f"R_{pid}",1)]; d1=pp[(f"D_{pid}",1)]
        track(sn, p1[0],p1[1], r1[0],r1[1]); track(sn, r1[0],r1[1], d1[0],d1[1])

    for label,xo in term:
        tp = pp[(f"TP_{label}",1)]
        nn = "VCC" if label=="VCC" else "GND" if label=="GND" else f"USB_{label}"
        w = TRACE_PWR if label in ("VCC","GND") else TRACE_SIG
        # 先拉到拍颈区域
        track(N(nn), tp[0], tp[1], tp[0], bot_y-3, w)
    # D+/D- 从拍颈上拉到 J1 右列上端
    for label, j1_pin in [("D+", 21), ("D-", 20)]:
        tp = pp[(f"TP_{label}",1)]; jp = pp[("J1", j1_pin)]
        track(N(f"USB_{label}"), tp[0], bot_y-3, jp[0], bot_y-3, TRACE_SIG)
        track(N(f"USB_{label}"), jp[0], bot_y-3, jp[0], jp[1], TRACE_SIG)

    for pid in ["PZT_TR","PZT_TL","PZT_BR","PZT_BL"]:
        for ref,pn in [(pid,2),(f"R_{pid}",2),(f"D_{pid}",2)]:
            if (ref,pn) in pp: via(gnd, pp[(ref,pn)][0], pp[(ref,pn)][1])
    via(gnd, cx-4, mc_y+9); via(gnd, cx+4, mc_y+9)

    # ═══════════════════════════════════════════════
    # B.Cu 地平面
    # ═══════════════════════════════════════════════
    z = pcbnew.ZONE(b); z.SetNet(gnd); z.SetLayer(pcbnew.B_Cu)
    z.SetIsRuleArea(False); z.SetAssignedPriority(0)
    zo = z.Outline(); zo.NewOutline()
    for x,y in [opts[i] for i in range(0, len(opts), 3)]:
        zo.Append(mk(x), mk(y))
    z.SetFillMode(pcbnew.ZONE_FILL_MODE_POLYGONS); z.SetHatchStyle(0)
    z.SetMinThickness(mk(0.2)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    z.SetThermalReliefGap(mk(0.3)); z.SetThermalReliefSpokeWidth(mk(0.4))
    b.Add(z)

    # ═══ Edge.Cuts 外框 (step=2 + 拍尾全精度) ═══
    outline_raw = [(round(p[0], 2), round(p[1], 2)) for p in opts]
    if outline_raw[0] == outline_raw[-1]:
        outline_raw.pop()  # 去尾闭合重复 → 89唯一点
    n_raw = len(outline_raw)
    ymin = min(p[1] for p in outline_raw)
    # step=2 基础采样
    keep_idx = set(range(0, n_raw, 2))
    # 补拍尾全精度 (Y 最低点 X 最低+5mm)
    for i, (x, y) in enumerate(outline_raw):
        if y < ymin + 5:
            keep_idx.add(i)
    keep_idx = sorted(keep_idx)
    outline_pts = [outline_raw[i] for i in keep_idx]
    if outline_pts[0] != outline_pts[-1]:
        outline_pts.append(outline_pts[0])  # 闭环

    edge_count = 0
    for i in range(len(outline_pts) - 1):
        x1, y1 = outline_pts[i]
        x2, y2 = outline_pts[i + 1]
        ln = pcbnew.PCB_SHAPE(b)
        ln.SetShape(pcbnew.SHAPE_T_SEGMENT)
        ln.SetStart(pcbnew.VECTOR2I(int(x1 * 1e6), int(y1 * 1e6)))
        ln.SetEnd(pcbnew.VECTOR2I(int(x2 * 1e6), int(y2 * 1e6)))
        ln.SetWidth(int(0.1e6))
        ln.SetLayer(pcbnew.Edge_Cuts)
        b.Add(ln)
        edge_count += 1

    # ── 保存 ──
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    b.Save(str(OUTPUT_FILE))

    # ═══════════════════════════════════════════════
    # KiCad 9.0.6 b.Save() bug workaround:
    # tracks net 引用在保存时全部错写为 GND (net 1)
    # 后处理: 从 track_records 根据坐标匹配恢复正确 net 编号
    # ═══════════════════════════════════════════════
    def fix_track_nets(filepath, records):
        with open(filepath) as f:
            lines = f.readlines()

        # Build net_name → net_number from net declarations
        net_map = {}
        for line in lines:
            m = re.match(r'\s*\(net (\d+) "([^"]+)"\)', line)
            if m:
                net_map[m.group(2)] = int(m.group(1))

        # Build (start,end) → [net_number, ...] list from track_records
        from collections import defaultdict
        rec_map = defaultdict(list)
        for name, x1, y1, x2, y2, w in records:
            key = (f'{x1:.4f}', f'{y1:.4f}', f'{x2:.4f}', f'{y2:.4f}')
            rec_map[key].append(net_map.get(name, 1))

        # Consume entries as we match segments (same-order assumption)
        rec_consumed = {k: 0 for k in rec_map}

        # Parse each segment block and fix net
        out_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.strip().startswith('(segment'):
                # Collect segment block lines
                block = [line]
                i += 1
                while i < len(lines):
                    block.append(lines[i])
                    if lines[i].strip() == ')':
                        i += 1
                        break
                    i += 1
                # Extract start/end from block
                sx = sy = ex = ey = None
                for bl in block:
                    ms = re.match(r'\s*\(start\s+([-\d.]+)\s+([-\d.]+)\)', bl)
                    if ms: sx, sy = float(ms.group(1)), float(ms.group(2))
                    me = re.match(r'\s*\(end\s+([-\d.]+)\s+([-\d.]+)\)', bl)
                    if me: ex, ey = float(me.group(1)), float(me.group(2))
                if sx is not None and ex is not None:
                    key = (f'{sx:.4f}', f'{sy:.4f}', f'{ex:.4f}', f'{ey:.4f}')
                    candidates = rec_map.get(key, [])
                    idx = rec_consumed.get(key, 0)
                    if idx < len(candidates):
                        correct = candidates[idx]
                        rec_consumed[key] = idx + 1
                        new_block = []
                        for bl in block:
                            bl = re.sub(r'\(net \d+\)', f'(net {correct})', bl)
                            new_block.append(bl)
                        block = new_block
                out_lines.extend(block)
            else:
                out_lines.append(line)
                i += 1

        with open(filepath, 'w') as f:
            f.write(''.join(out_lines))

    fix_track_nets(str(OUTPUT_FILE), track_records)

    # ── 统计 ──
    from collections import Counter
    net_counts = Counter(name for name, *_ in track_records)

    fps = sum(1 for _ in b.Footprints())
    trs = len(track_records)
    vis = sum(1 for t in b.Tracks() if t.Type()==pcbnew.PCB_VIA_T)
    print(f"\n{'='*55}")
    print(f"KiCad PCB v9.0: {OUTPUT_FILE}")
    print(f"   Footprints: {fps}  |  Nets: {len(nets)}")
    print(f"   Tracks: {trs} (信号已修复)  |  Vias: {vis}")
    print(f"   Per net: {dict(net_counts)}")
    print(f"   Edge.Cuts: {edge_count} 段 (拍头+拍尾全精度)")
    print(f"{'='*55}")

    if "--preview" in sys.argv:
        subprocess.run(["open","-a","/Applications/KiCad/PCB Editor.app",
                        str(OUTPUT_FILE)], check=False)


if __name__ == "__main__":
    main()

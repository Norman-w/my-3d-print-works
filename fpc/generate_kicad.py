"""SmartPaddle FPC v9.3 — Y 翻转 + IMU/MCU 摆 X 长 + 实物 1:1
═══════════════════════════════════════════════════
A. Y 翻转: SCAD +Y=拍头 → KiCad 数据 -Y=屏上 (KiCad 9 内部 Y+ 永远=屏下)
B. J1: ESP32-C6-N8 14+14=28邮票孔, 摆放 fab 25.5×18 (X 长)
C. IMU: IM948 8+8=16邮票孔, 摆放 fab 18.5×13 (X 长)
D. 终端焊盘: 4×3mm
E. IMU Y=-6 (拍头甜区, 屏上) / MCU Y=+17 (拍柄端, 屏下) 间隙 7.5mm, X 都居中
F. KiCad 9.0.6 Save bug 后处理修复
G. RF keepout 18.5×3 / 25.5×3 (摆放方向)
H. NC pin 不 pad 出来, 避免空 net (块 1.5 修复 2026-06-09)
I. 28 pin 完整 net 表 (块 2 修复 2026-06-10): EN 上拉 VCC, PZT→IO4-7, USB→IO13/18, UART→IO16/17
J. 摆放修正 (块 3 修复 2026-06-10): IMU 拍头端, MCU 拍柄端, X 都用长边
K. Y 翻转 (v9.3 修复 2026-06-10): opts/PZT/耳角/keepout/stiffener 全部 -(y)
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
        if n in ("NC", "", None):
            return None
        if n not in nets:
            nets[n] = pcbnew.NETINFO_ITEM(b, n); b.Add(nets[n])
        return nets[n]
    gnd = N("GND"); vcc = N("VCC")
    vcc_3v3 = N("VCC_3V3")
    vbus = N("VBUS")
    en = N("EN")
    N("USB_D+"); N("USB_D-"); N("UART_RX"); N("UART_TX")
    N("PZT_TR_SIGNAL"); N("PZT_TL_SIGNAL"); N("PZT_BR_SIGNAL"); N("PZT_BL_SIGNAL")
    pzt_adin = N("PZT_ADIN")

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

    # ═══════════════════════════════════════════════
    # Y 翻转 (KiCad 9 内部 Y+=屏幕下方, SCAD Y+=拍头; 必须翻转以让拍头出现在屏幕顶部)
    # 在 opts 构建后立即翻转, 后面所有 footprint/track/gr_text 都用 (x, -y) 数据
    # ═══════════════════════════════════════════════
    def flipy(pt): return (pt[0], -pt[1]) if isinstance(pt, tuple) else pt
    opts = [(x, -y) for (x, y) in opts]
    # PZT 中心 (x, y) → (x, -y)
    for p in params["components"]["piezo"]:
        p["position"] = (p["position"][0], -p["position"][1])
    for sc in params["components"].get("signal_conditioning", []):
        sc["r_position"] = (sc["r_position"][0], -sc["r_position"][1])
        sc["d_position"] = (sc["d_position"][0], -sc["d_position"][1])
    # 拍柄末端 X 不动, Y 由 bot_y 自动随之翻转
    # main_module center (cx, cy) 中的 cy
    mc_c_orig = params["components"]["main_module"]["center"]
    params["components"]["main_module"]["center"] = (mc_c_orig[0], -mc_c_orig[1])
    # keep_out_zones positions
    for koz in params.get("keep_out_zones", []):
        if "positions" in koz:
            koz["positions"] = [(x, -y) for (x, y) in koz["positions"]]
    # stiffeners
    for st in params.get("stiffeners", []):
        if "position" in st:
            x, y = st["position"]
            st["position"] = (x, -y)

    # ── FP 构建器 ──
    def pad(fp, nr, pos, sz, net, shape=pcbnew.PAD_SHAPE_CIRCLE):
        p = pcbnew.PAD(fp); p.SetNumber(str(nr)); p.SetShape(shape)
        p.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        p.SetPosition(pcbnew.VECTOR2I(mk(pos[0]), mk(pos[1])))
        p.SetSize(pcbnew.VECTOR2I(mk(sz[0]), mk(sz[1])))
        if net is not None:
            p.SetNet(net)
        ls = pcbnew.LSET()
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
    mc_y    = 17                        # MCU 拍柄端: SCAD Y=-17 → KiCad Y=+17 (屏下 = 拍柄)
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
    # 实物顶视图 (D=18.5 Y 长, E=13 X 短) + 摆放方向 X 长 (旋转 90°)
    # 官方数据表 2026-06-09:
    #   D=18.5  实物长边  | E=13.0  实物短边
    #   e=2.0   邮票孔中心到短边距离
    #   b=1.27  邮票孔 P 间距  | a=1.0  邮票孔直径  | t1=1.0  铜环
    # 摆放后: fab 框 18.5 × 13 (X 长 Y 短), 邮票孔沿 X 排
    #   邮票孔中心 Y 坐标 = ±(E/2 - e) = ±4.5
    #   邮票孔中心 X 范围 = ±((N-1)/2 × b) = ±4.445 (N=8/边, pitch=1.27)
    #   RF 净空: 顶部 18.5×3mm (旋转后 X 方向是长边) (User_4)
    #   实物 Pin 1 在左下 → 摆放后 Pin 1 在左上 (旋转 90° CCW)
    # ═══════════════════════════════════════════════
    imu_x, imu_y = 0, -6              # IMU 拍头端: SCAD Y=+6 → KiCad Y=-6 (屏上 = 拍头)
    iw, ih = 18.5, 13.0                # IM948 摆放后 fab: X=长边18.5, Y=短边13
    imu_pitch = 1.27; imu_n = 8        # 每侧 8 脚, P 间距
    imu_hw = ih / 2 - 2.0              # 邮票孔中心 Y = ±(6.5-2.0) = ±4.5
    imu_hh = iw / 2                    # fab 框 X 半长 = 9.25
    imu_span = (imu_n - 1) * imu_pitch / 2  # 4.445mm (邮票孔 X 跨距)
    imu_pad_sz = 1.0                   # 邮票孔直径 a=1.0 (PTH 圆形)

    imu_fp = make_fp("U1", "IM948", imu_x, imu_y)
    # Pin 1-8 沿下侧长边 (Y = -imu_hw = -4.5), 沿 X 等距 1.27
    # 实物左下 → 摆放后左上 (旋转 CCW 90° 后 X=-span/2 是 Pin 1, X=+span/2 是 Pin 8)
    # 实物 → 摆放映射: 实物 l_net[i] 对应摆放后 Pin 1-8 (X 从 -span 到 +span)
    # 实物引脚 1=VSS(左下) → 摆放后 Pin 1 在 X=-span 端 (左下→左上)
    #  1=VSS, 2=VBUS, 3=VBAT, 4=VDDIO, 5=NC, 6=NC, 7=ADIN, 8=VSS
    l_net = [
        "GND",        # 1  VSS
        "VBUS",       # 2  USB 5V 充电输入
        "VCC",        # 3  锂电池 3.7V
        "VCC_3V3",    # 4  GPIO 电压域 (≤3.4V!)
        "NC",         # 5
        "NC",         # 6
        "PZT_ADIN",   # 7  ADIN: 4 路 PZT 经 CD4051 选通后单 ADC 输入
        "GND",        # 8  VSS
    ]
    for i in range(imu_n):
        if l_net[i] == "NC":
            continue                            # NC 不创建 pad (避免出现在 net 表)
        xo = (i - (imu_n - 1) / 2) * imu_pitch
        pad(imu_fp, i + 1, (xo, -imu_hw), (imu_pad_sz, imu_pad_sz),
            N(l_net[i]), pcbnew.PAD_SHAPE_CIRCLE)
        Rec("U1", i + 1, imu_x + xo, imu_y - imu_hw)

    # Pin 9-16 沿上侧长边 (Y = +imu_hw = +4.5), 沿 X 等距 1.27
    # 实物右下 → 摆放后右上
    #  9=LED-B, 10=LED-R, 11=GPIO, 12=KEY, 13=RXD, 14=TXD, 15=VBAT, 16=VSS
    r_net = [
        "NC",         # 9  LED-B    (留空)
        "NC",         # 10 LED-R    (留空)
        "NC",         # 11 GPIO     (留空)
        "NC",         # 12 KEY      (留空)
        "UART_TX",    # 13 RXD ← ESP32 TX (IO16)
        "UART_RX",    # 14 TXD → ESP32 RX (IO17)
        "VCC",        # 15 VBAT
        "GND",        # 16 VSS
    ]
    for i in range(imu_n):
        if r_net[i] == "NC":
            continue
        xo = (i - (imu_n - 1) / 2) * imu_pitch
        pad(imu_fp, i + imu_n + 1, (xo, imu_hw), (imu_pad_sz, imu_pad_sz),
            N(r_net[i]), pcbnew.PAD_SHAPE_CIRCLE)
        Rec("U1", i + imu_n + 1, imu_x + xo, imu_y + imu_hw)

    fab_rect(imu_fp, imu_x, imu_y, 0, 0, iw, ih)
    crtyd_rect(imu_fp, imu_x, imu_y, 0, 0, iw, ih)
    b.Add(imu_fp)
    gfx_rect(pcbnew.F_SilkS, imu_x - iw/2 - 0.5, imu_y - ih/2 - 0.5,
             imu_x + iw/2 + 0.5, imu_y + ih/2 + 0.5, 0.12)
    silk_text(imu_x, imu_y - ih/2 - 1.5, "IM948 IMU", 1.0, 0.12)
    silk_text(imu_x - imu_span, imu_y - imu_hw - 0.8, "1", 0.6, 0.1)
    silk_text(imu_x + imu_span, imu_y - imu_hw - 0.8, "8", 0.6, 0.1)
    silk_text(imu_x - imu_span, imu_y + imu_hw + 1.2, "9", 0.6, 0.1)
    silk_text(imu_x + imu_span, imu_y + imu_hw + 1.2, "16", 0.6, 0.1)

    # RF 净空区: 模块顶部 18.5×3mm 无铜 (官方要求, 摆放后顶部是 X 方向长边)
    rf_x1, rf_y1 = imu_x - iw/2, imu_y + ih/2
    rf_x2, rf_y2 = imu_x + iw/2, imu_y + ih/2 + 3.0
    gfx_rect(pcbnew.User_4, rf_x1, rf_y1, rf_x2, rf_y2, 0.05)
    silk_text(imu_x, rf_y1 + 1.5, "RF KEEPOUT 18.5\u00D73", 0.7, 0.1)

    # ═══════════════════════════════════════════════
    # MCU J1 — ESP32-C6-WROOM-1-N8 14+14=28邮票孔 (块 2 修复 2026-06-10)
    # 实物顶视图 (W=18 Y=25.5 实物, 摆放后 fab 25.5×18 X 长)
    #   邮票孔中心 Y = ±(9-0.85) = ±8.15
    #   邮票孔中心 X 范围 = ±((14-1)/2 × 1.27) = ±8.255
    #   Pin 1=GND 在左下 → 摆放后 Pin 1 在 X=-span/2 端 (旋转 CCW 90° 后 14 颗从下到上变成从左到右)
    #   实物 → 摆放映射: 实物左列(Pin 1-14, 从下到上) → 摆放后下排(X 从 -span 到 +span)
    #   实物右列(Pin 15-28, 从下到上) → 摆放后上排
    # 引脚功能来自 ESP32-C6-N8 官方资料 (用户 2026-06-10 提供):
    # ═══════════════════════════════════════════════
    fw, fh = 25.5, 18.0               # 摆放后 fab: X=长边25.5, Y=短边18
    pitch = 1.27; n_per_edge = 14
    half_w = fh / 2 - 0.85           # 邮票孔中心 Y = ±(9-0.85) = ±8.15
    half_span = (n_per_edge - 1) * pitch / 2  # 8.255mm
    cf = make_fp("J1", "ESP32-C6-N8", cx, mc_y)

    # 左侧引脚 1-14 沿下边 (Y = -half_w = -8.15), 沿 X 等距 1.27
    # 实物左列从下到上 1=GND, 2=3V3, 3=EN, 4=IO4, 5=IO5, 6=IO6, 7=IO7, 8=IO0,
    #                  9=IO1, 10=IO8, 11=IO10, 12=IO11, 13=IO12, 14=IO13
    l_net = [
        "GND",            # 1  GND     接地
        "VCC",            # 2  3V3     供电
        "EN",             # 3  EN      复位使能 (高电平使能, 需上拉到 3V3)
        "PZT_TR_SIGNAL",  # 4  IO4/ADC1_CH4  ← PZT TR
        "PZT_TL_SIGNAL",  # 5  IO5/ADC1_CH5  ← PZT TL
        "PZT_BR_SIGNAL",  # 6  IO6/ADC1_CH6  ← PZT BR
        "PZT_BL_SIGNAL",  # 7  IO7/ADC1_CH7  ← PZT BL
        "NC",             # 8  IO0     (不接, 避免启动模式干扰)
        "NC",             # 9  IO1
        "NC",             # 10 IO8
        "NC",             # 11 IO10
        "NC",             # 12 IO11
        "NC",             # 13 IO12
        "USB_D+",         # 14 IO13/USB_D+  → 终端焊盘
    ]
    # 右侧引脚 15-28 沿上边 (Y = +half_w = +8.15), 沿 X 等距 1.27
    # 实物右列从下到上 15=IO9, 16=IO18, 17=IO19, 18=IO20, 19=IO21, 20=IO22, 21=IO23,
    #                  22=NC, 23=IO15, 24=RXD0(IO17), 25=TXD0(IO16), 26=IO3, 27=IO2, 28=GND
    r_net = [
        "NC",             # 15 IO9
        "USB_D-",         # 16 IO18/USB_D-  → 终端焊盘
        "NC",             # 17 IO19
        "NC",             # 18 IO20
        "NC",             # 19 IO21
        "NC",             # 20 IO22
        "NC",             # 21 IO23
        "NC",             # 22 NC (实物悬空, 不能接地)
        "NC",             # 23 IO15
        "UART_RX",        # 24 RXD0/IO17  ← IMU TXD (14)
        "UART_TX",        # 25 TXD0/IO16  → IMU RXD (13)
        "NC",             # 26 IO3
        "NC",             # 27 IO2
        "GND",            # 28 GND
    ]
    for i in range(n_per_edge):
        if l_net[i] == "NC":
            continue                            # NC 不创建 pad
        xo = (i - (n_per_edge - 1) / 2) * pitch
        pad(cf, i + 1, (xo, -half_w), (1.5, 0.8),
            N(l_net[i]), pcbnew.PAD_SHAPE_RECT)
        Rec("J1", i + 1, cx + xo, mc_y - half_w)
    for i in range(n_per_edge):
        if r_net[i] == "NC":
            continue
        xo = (i - (n_per_edge - 1) / 2) * pitch
        pad(cf, i + n_per_edge + 1, (xo, half_w), (1.5, 0.8),
            N(r_net[i]), pcbnew.PAD_SHAPE_RECT)
        Rec("J1", i + n_per_edge + 1, cx + xo, mc_y + half_w)
    # EPAD 29 — 中心接地焊盘
    pad(cf, 29, (0, 0), (12, 16), gnd, pcbnew.PAD_SHAPE_RECT)
    Rec("J1", 29, cx, mc_y)

    fab_rect(cf, cx, mc_y, 0, 0, fw, fh)
    crtyd_rect(cf, cx, mc_y, 0, 0, fw, fh)
    b.Add(cf)
    gfx_rect(pcbnew.F_SilkS, cx - fw/2 - 1, mc_y - half_w - 1,
             cx + fw/2 + 1, mc_y + half_w + 1, 0.12)
    silk_text(cx, mc_y + half_w + 2, "ESP32-C6-N8", 1.0, 0.12)
    silk_text(cx - half_span, mc_y - half_w - 1.5, "1", 0.6, 0.1)
    silk_text(cx + half_span, mc_y - half_w - 1.5, "14", 0.6, 0.1)
    silk_text(cx - half_span, mc_y + half_w + 1.5, "15", 0.6, 0.1)
    silk_text(cx + half_span, mc_y + half_w + 1.5, "28", 0.6, 0.1)

    # RF 净空区: 模块顶部 25.5×3mm 无铜 (官方要求, 摆放后顶部 X 长)
    rf_x1, rf_y1 = cx - fw/2, mc_y + fh/2
    rf_x2, rf_y2 = cx + fw/2, mc_y + fh/2 + 3.0
    gfx_rect(pcbnew.User_5, rf_x1, rf_y1, rf_x2, rf_y2, 0.05)
    silk_text(cx, rf_y1 + 1.5, "RF KEEPOUT 25.5\u00D73", 0.7, 0.1)

    # ═══════════════════════════════════════════════
    # 拍柄末端引出焊盘 (修正 B:4×3mm + C:文字90°)
    # ═══════════════════════════════════════════════
    all_y = [y for _,y in opts]
    bot_y = max(all_y) - 2    # 拍柄端: Y 翻转后拍柄在屏下方 = max(Y)
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
    # 走线 (v9.2 — 适配 IMU/MCU 摆 X 长后所有 pin 沿 X 分布)
    # ═══════════════════════════════════════════════
    NECK_Y1 = -71.7; NECK_Y2 = -78.5   # 拍头→拍柄 肩膀区域
    SPINE_L = -22; SPINE_R = 22

    # ESP32 pin 坐标 (摆放后 fab 25.5×18, center (0, mc_y=-17), half_w=8.15, half_span=8.255)
    # 实物 → 摆放映射: 实物左列从下到上(Pin 1-14) → 摆放后下排 X 从 -8.255 到 +8.255
    #                实物右列从下到上(Pin 15-28) → 摆放后上排 X 从 -8.255 到 +8.255
    def j1_pin_xy(pin_num):
        """返回 ESP32 pin 实际世界坐标"""
        pitch = 1.27; half_span_v = 8.255; half_w_v = 8.15
        if pin_num <= 14:
            i = pin_num - 1
            x = (i - 6.5) * pitch
            y = -half_w_v
        else:
            i = pin_num - 15
            x = (i - 6.5) * pitch
            y = +half_w_v
        return (cx + x, mc_y + y)

    # PZT 信号 → J1 ADC 引脚: IO4(4), IO5(5), IO6(6), IO7(7)
    # PZT 在拍面 Y=±52, J1 pin 在 Y=-25.15 (下排), 需走长距离
    def route_signal_v92(pid, spine_x, pin_num):
        sn = N(f"{pid}_SIGNAL")
        d1 = pp[(f"D_{pid}",1)]
        jp = j1_pin_xy(pin_num)
        neck_x = max(-8, min(8, spine_x))
        # 路径: D1(拍面) → 沿 X 走到 spine_x → 上到拍颈 → 横穿到 J1 pin X → 下到 J1 pin Y
        mid_y = min(d1[1], NECK_Y1) - 5
        # 简化路径: D1 → spine_x → 拍颈 Y → J1 X → J1 Y (走两次长距离)
        # 但 ESP32 pin 在 Y=-25.15 (下排), 拍颈 -78.5, 拍面 +52
        # 走法: D1(±52) → 沿 X 到 spine_x → 沿 Y 到 mid_y (拍颈) → 沿 X 到 neck_x → 沿 Y 到 -25.15
        pts = [(d1[0],d1[1]),(d1[0],mid_y),(spine_x,mid_y),
               (spine_x,-25),(neck_x,-25),(jp[0],-25),(jp[0],jp[1])]
        for i in range(len(pts)-1):
            track(sn, pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1])

    route_signal_v92("PZT_TR", SPINE_R, 4)
    route_signal_v92("PZT_BR", SPINE_R, 6)
    route_signal_v92("PZT_TL", SPINE_L, 5)
    route_signal_v92("PZT_BL", SPINE_L, 7)

    # VCC → J1 Pin2 (3V3) — 从拍柄终端 VCC 拉到 J1(2)
    j1_vcc = j1_pin_xy(2)
    for label, jx in [("VCC", cx - 4), ("GND", cx + 4)]:
        tp = pp[(f"TP_{label}",1)]
        track(N(label), tp[0], bot_y-3, jx, bot_y-3, TRACE_PWR)
        track(N(label), jx, bot_y-3, jx, j1_vcc[1], TRACE_PWR)
        track(N(label), jx, j1_vcc[1], j1_vcc[0], j1_vcc[1], TRACE_PWR)

    # UART: IMU(13:RXD←), IMU(14:TXD→) ↔ J1(24:RXD0/IO17), J1(25:TXD0/IO16)
    # IMU pin 13/14 在 Y=+10.5 (上排), J1 pin 24/25 在 Y=-8.85 (上排)
    # 汇流点: IMU 与 J1 中间, Y=-0.5 (IMU 底) 到 -8.85 (J1 顶), 中间 Y≈-5
    u1_rxd = pp[("U1", 13)]  # IMU RXD 中心 (0.635, 10.5)
    u1_txd = pp[("U1", 14)]  # IMU TXD 中心 (1.905, 10.5)
    j1_tx  = j1_pin_xy(25)   # IO16 中心 (+4.445, -8.85)
    j1_rx  = j1_pin_xy(24)   # IO17 中心 (+3.175, -8.85)
    jy = -4  # IMU 底 -0.5, J1 顶 -8.85, 中转 Y
    # TX: IMU pin13 (0.635, 10.5) → 下到 jy=-4 → 横走到 J1 TX X=4.445 → 下到 J1 TX Y=-8.85
    track(N("UART_TX"), u1_rxd[0], u1_rxd[1], u1_rxd[0], jy)
    track(N("UART_TX"), u1_rxd[0], jy, j1_tx[0], jy)
    track(N("UART_TX"), j1_tx[0], jy, j1_tx[0], j1_tx[1])
    # RX: IMU pin14 (1.905, 10.5) → 下到 jy-0.5=-4.5 → 横走到 J1 RX X=3.175 → 下到 J1 RX Y=-8.85
    track(N("UART_RX"), u1_txd[0], u1_txd[1], u1_txd[0], jy-0.5)
    track(N("UART_RX"), u1_txd[0], jy-0.5, j1_rx[0], jy-0.5)
    track(N("UART_RX"), j1_rx[0], jy-0.5, j1_rx[0], j1_rx[1])

    for sc in params["components"]["signal_conditioning"]:
        pid = sc["piezo"]; sn = N(f"{pid}_SIGNAL")
        p1=pp[(pid,1)]; r1=pp[(f"R_{pid}",1)]; d1=pp[(f"D_{pid}",1)]
        track(sn, p1[0],p1[1], r1[0],r1[1]); track(sn, r1[0],r1[1], d1[0],d1[1])

    # EN 上拉到 VCC (短接到 J1 Pin 2 的 VCC net, J1 Pin 3=EN 离 Pin 2 很近)
    j1_en = j1_pin_xy(3)    # X=-5.715, Y=-25.15
    j1_3v3 = j1_pin_xy(2)   # X=-6.985, Y=-25.15
    track(en, j1_en[0], j1_en[1], j1_3v3[0], j1_3v3[1], TRACE_PWR)

    # D+/D- 从拍颈上拉到 J1 [实物 2026-06-10]:
    #   D+ → J1(14)=IO13/USB_D+ (下排 X=+8.255, Y=-25.15)
    #   D- → J1(16)=IO18/USB_D- (上排 X=-6.985, Y=-8.85)
    for label, pin_num in [("D+", 14), ("D-", 16)]:
        tp = pp[(f"TP_{label}",1)]
        jp = j1_pin_xy(pin_num)
        track(N(f"USB_{label}"), tp[0], bot_y-3, jp[0], bot_y-3, TRACE_SIG)
        track(N(f"USB_{label}"), jp[0], bot_y-3, jp[0], jp[1], TRACE_SIG)

    for pid in ["PZT_TR","PZT_TL","PZT_BR","PZT_BL"]:
        for ref,pn in [(pid,2),(f"R_{pid}",2),(f"D_{pid}",2)]:
            if (ref,pn) in pp: via(gnd, pp[(ref,pn)][0], pp[(ref,pn)][1])
    # MCU 接地 via: J1 中心 EPAD + 两端
    via(gnd, cx, mc_y)
    via(gnd, cx-8, mc_y-8); via(gnd, cx+8, mc_y+8)

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

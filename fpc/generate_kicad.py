"""SmartPaddle FPC v9.12 — OpenSCAD 槽位驱动的 KiCad 9 FPC 生成脚本
═══════════════════════════════════════════════════════════════
v9.12 (2026-06-11): 模块位置由 OpenSCAD 甜区槽 center/size 计算
  - U1/J1 都约束在 42×42 PCB 槽内, 避开中线 M2 螺丝
  - IMU 在拍头侧, MCU 在拍柄侧, 均沿 X 方向放长边

v9.11 (2026-06-11): 用 FootprintLoad() 加载 Espressif 官方封装替换自定义 ESP32 段
  - J1: FootprintLoad('fpc/footprints/Espressif.pretty', 'ESP32-C6-WROOM-1')
  - 旋转 90° 让 fab 长边沿 X (FPC 长边方向)
  - 28 邮票孔 + 9 EPAD 阵列
  - 旋转后 pad 沿 X 方向 (Pin 1-14 在 Y=+8.75, Pin 15-28 在 Y=-8.75)
  - 整体 fab 范围 26.72×19.72mm (含 antenna 突出)

之前 v9.0-v9.10 历史 (保留注释):
  A. Y 翻转: SCAD +Y=拍头 → KiCad 数据 -Y=屏上 (KiCad 9 内部 Y+ 永远=屏下)
  B. J1: 自定义 14+14=28 邮票孔, 摆放 fab 25.5×18 (X 长) — v9.11 改用官方
  C. U1: 13×18.5 16-pin 模块旋转为 X 长摆放 (18.5×13), 信号/RF避让朝 X-
  D. 终端焊盘: 4×3mm
  E. U1/J1 位置来自 main_module.center/size, 不再硬编码
  F. KiCad 9.0.6 Save bug 后处理修复
  G. RF keepout 18.5×3 / 25.5×3 (摆放方向)
  H. NC pin 物理有 pad 不连 net
  I. 28 pin 完整 net 表: EN 上拉 VCC, PZT→IO4-7, USB→IO13/18, UART→IO16/17
  J. 摆放修正: IMU 拍头端, MCU 拍柄端, X 都用长边
  K. Y 翻转: opts/PZT/耳角/keepout/stiffener 全部 -(y)
  L. KiCad 9 正确 pcbnew API (v9.7):
     - SetPosition/GetPosition → 绝对 (全局) 坐标
     - SetFPRelativePosition/GetFPRelativePosition → fp 内部相对坐标
  M. main_module_connector stiffener 改 ESP32 fab 框大小
  N. 中线 2 NPTH M2 螺丝孔
  O. 中线 2 keepout 大圆移除
  P. 丝印重排 (v9.8)
  Q. IMU net 表重写 (v9.8): Pin 7=RXD, Pin 8=TXD (实物 IM948 UART)
  R. UART 走线: U1 pin 13/14 (RXD/TXD) -> J1 pin 25/24 (TXD/RXD)
"""

import yaml, sys, subprocess, math, re, uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
YAML_PATH    = PROJECT_ROOT / "shared" / "board_params.yaml"
OUTPUT_DIR   = Path(__file__).resolve().parent / "layouts" / "default"
OUTPUT_FILE  = OUTPUT_DIR / "default.kicad_pcb"

TRACE_SIG = 0.2; TRACE_PWR = 0.3
VIA_DRILL = 0.3; VIA_PAD   = 0.6
EMIT_SILK = False
EMIT_COURTYARD = False


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
        # KiCad 9.0.6 pcbnew 正确 API:
        #   - SetPosition / GetPosition → 绝对 (全局) 坐标
        #   - SetFPRelativePosition / GetFPRelativePosition → fp 内部相对坐标
        # 用 SetFPRelativePosition 设 fp 内部 pos, 加载时 KiCad 正确计算全局
        p = pcbnew.PAD(fp); p.SetNumber(str(nr)); p.SetShape(shape)
        p.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        p.SetFPRelativePosition(pcbnew.VECTOR2I(mk(pos[0]), mk(pos[1])))
        p.SetSize(pcbnew.VECTOR2I(mk(sz[0]), mk(sz[1])))
        if shape == pcbnew.PAD_SHAPE_RECT:
            p.SetOrientationDegrees(fp.GetOrientationDegrees())
        if net is not None:
            p.SetNet(net)
        ls = pcbnew.LSET()
        for ly in [pcbnew.F_Cu,pcbnew.F_Paste,pcbnew.F_Mask]: ls.addLayer(ly)
        p.SetLayerSet(ls); fp.Add(p)
        return p

    track_records = []  # (net_name, x1, y1, x2, y2, width)

    def track(net,x1,y1,x2,y2,w=TRACE_SIG,layer=pcbnew.F_Cu):
        t=pcbnew.PCB_TRACK(b); t.SetLayer(layer); t.SetNet(net)
        t.SetStart(pcbnew.VECTOR2I(mk(x1),mk(y1)))
        t.SetEnd(pcbnew.VECTOR2I(mk(x2),mk(y2)))
        t.SetWidth(mk(w)); b.Add(t)
        nn = net.GetNetname() if hasattr(net,'GetNetname') else str(net)
        track_records.append((nn, x1, y1, x2, y2, w))

    def route(net, pts, w=TRACE_SIG, layer=pcbnew.F_Cu):
        for i in range(len(pts) - 1):
            track(net, pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1], w, layer)

    def via(net,x,y):
        v=pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(mk(x),mk(y)))
        v.SetNet(net); v.SetWidth(mk(VIA_PAD)); v.SetDrill(mk(VIA_DRILL)); b.Add(v)

    def pad_xy(p):
        pos = p.GetPosition()
        return (pos.x / 1e6, pos.y / 1e6)

    def gfx_rect(layer,x1,y1,x2,y2,w=0.05):
        if layer == pcbnew.F_SilkS and not EMIT_SILK:
            return
        g=pcbnew.PCB_SHAPE(b); g.SetShape(pcbnew.SHAPE_T_RECT)
        g.SetStart(pcbnew.VECTOR2I(mk(x1),mk(y1)))
        g.SetEnd(pcbnew.VECTOR2I(mk(x2),mk(y2)))
        g.SetLayer(layer); g.SetWidth(int(w*1e6)); b.Add(g)

    def gfx_circle(layer,cx,cy,r,w=0.05):
        if layer == pcbnew.F_SilkS and not EMIT_SILK:
            return
        g=pcbnew.PCB_SHAPE(b); g.SetShape(pcbnew.SHAPE_T_CIRCLE)
        g.SetCenter(pcbnew.VECTOR2I(mk(cx),mk(cy)))
        g.SetEnd(pcbnew.VECTOR2I(mk(cx+r),mk(cy)))
        g.SetLayer(layer); g.SetWidth(int(w*1e6)); b.Add(g)

    def silk_text(x,y,txt,sz=1.0,th=0.12,rot=0):
        if not EMIT_SILK:
            return
        tx=pcbnew.PCB_TEXT(b); tx.SetText(txt)
        tx.SetPosition(pcbnew.VECTOR2I(mk(x),mk(y)))
        tx.SetLayer(pcbnew.F_SilkS)
        tx.SetTextSize(pcbnew.VECTOR2I(mk(sz),mk(sz)))
        tx.SetTextThickness(mk(th))
        if rot: tx.SetTextAngle(pcbnew.EDA_ANGLE(rot, pcbnew.DEGREES_T))
        b.Add(tx)

    def hide_fp_texts(fp):
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)

    def make_fp(ref, val, gx, gy):
        f=pcbnew.FOOTPRINT(b); f.SetReference(ref); f.SetValue(val)
        hide_fp_texts(f)
        f.SetLayer(pcbnew.F_Cu)
        f.SetPosition(pcbnew.VECTOR2I(mk(gx), mk(gy)))
        return f

    def fab_rect(fp, gx, gy, lx, ly, w, h):
        # KiCad 9 PCB_SHAPE.SetStart 全局坐标: KiCad 自动转 fp 内部, 加载时正确
        g=pcbnew.PCB_SHAPE(fp); g.SetShape(pcbnew.SHAPE_T_RECT)
        g.SetStart(pcbnew.VECTOR2I(mk(gx + lx - w/2), mk(gy + ly - h/2)))
        g.SetEnd(pcbnew.VECTOR2I(mk(gx + lx + w/2), mk(gy + ly + h/2)))
        g.SetLayer(pcbnew.F_Fab); g.SetWidth(int(0.1e6)); fp.Add(g)

    def crtyd_rect(fp, gx, gy, lx, ly, w, h, margin=0.5):
        if not EMIT_COURTYARD:
            return
        g=pcbnew.PCB_SHAPE(fp); g.SetShape(pcbnew.SHAPE_T_RECT)
        g.SetStart(pcbnew.VECTOR2I(mk(gx + lx - w/2 - margin), mk(gy + ly - h/2 - margin)))
        g.SetEnd(pcbnew.VECTOR2I(mk(gx + lx + w/2 + margin), mk(gy + ly + h/2 + margin)))
        g.SetLayer(pcbnew.F_CrtYd); g.SetWidth(int(0.05e6)); fp.Add(g)

    def fab_circle(fp, gx, gy, lx, ly, r):
        c=pcbnew.PCB_SHAPE(fp); c.SetShape(pcbnew.SHAPE_T_CIRCLE)
        c.SetCenter(pcbnew.VECTOR2I(mk(gx + lx), mk(gy + ly)))
        c.SetEnd(pcbnew.VECTOR2I(mk(gx + lx + r), mk(gy + ly)))
        c.SetLayer(pcbnew.F_Fab); c.SetWidth(int(0.1e6)); fp.Add(c)

    pp = {}
    def Rec(ref,pn,gx,gy): pp[(ref,pn)]=(gx,gy)

    # ═══════════════════════════════════════════════
    # PZT 焊盘 + 耳槽角度
    # ═══════════════════════════════════════════════
    mc_mod  = params["components"]["main_module"]
    mc_c    = mc_mod["center"]
    cx, cy  = mc_c[0], mc_c[1]          # 槽中心, 已随上面的 KiCad 视觉坐标处理
    cavity_w, cavity_h = mc_mod["size"]
    cavity_top_y = cy - cavity_h / 2
    cavity_bottom_y = cy + cavity_h / 2
    ear     = {}

    for pzt in params["components"]["piezo"]:
        pid = pzt["id"]; px,py = pzt["position"]; dia = pzt["cavity_diameter"]
        sn = N(f"{pid}_SIGNAL")
        ang = math.degrees(math.atan2(cy-py, cx-px))
        ear[pid] = ang

        fp = make_fp(pid, "PZT-5A", px, py)
        pad(fp, 1, (0,0), (8,8), sn)
        # v9.9 修复 (用户 2026-06-10 提供 PZT 实物图):
        #   实物 PZT-5A 负极是 "翻边电极" (外圈 2-3mm 环带, 不是小方块)
        #   用户要求: 4 个 PZT 负极都朝耳区方向 (朝 MCU/中心)
        #   中心在 (cx, cy) = (0, -5), PZT 在四角, 方向向量 = (cx-px, cy-py)
        dx, dy = cx - px, cy - py
        mag = math.hypot(dx, dy)
        # GND pad 中心放 PZT 外圈 (距离 = dia/2 - 1.5, 留 1.5mm 边距进中心 signal pad)
        gnd_off = dia/2 - 1.5
        gx_local = dx / mag * gnd_off
        gy_local = dy / mag * gnd_off
        # 用 3.5×2.5 椭圆 pad 模拟翻边 (环带 2-3mm 宽)
        pad(fp, 2, (gx_local, gy_local), (3.5, 2.5), gnd, pcbnew.PAD_SHAPE_RECT)
        fab_circle(fp, px, py, 0, 0, dia/2)
        crtyd_rect(fp, px, py, 0, 0, dia+1, dia+1)
        b.Add(fp); Rec(pid, 1, px, py); Rec(pid, 2, px + gx_local, py + gy_local)
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
        rf_p1 = pad(rf, 1, (0, 0.8), (1.0, 0.7), sn, pcbnew.PAD_SHAPE_RECT)
        rf_p2 = pad(rf, 2, (0, -0.8), (1.0, 0.7), gnd, pcbnew.PAD_SHAPE_RECT)
        fab_rect(rf, rx, ry, 0, 0, 1.6, 0.8); crtyd_rect(rf, rx, ry, 0, 0, 1.6, 0.8)
        b.Add(rf)
        ca=math.cos(rad+math.pi/2); sa=math.sin(rad+math.pi/2)
        Rec(f"R_{pid}", 1, *pad_xy(rf_p1))
        Rec(f"R_{pid}", 2, *pad_xy(rf_p2))

        doff = off_r + 2.5
        dx = pzx + doff*math.cos(rad); dy = pzy + doff*math.sin(rad)
        df = make_fp(f"D_{pid}", "BAT54S", dx, dy)
        df.SetOrientationDegrees(ang + 90)
        df_p1 = pad(df, 1, (0, 1.0), (0.7, 0.6), sn, pcbnew.PAD_SHAPE_RECT)
        df_p2 = pad(df, 2, (0, -1.0), (0.7, 0.6), gnd, pcbnew.PAD_SHAPE_RECT)
        df_p3 = pad(df, 3, (1.0, 0), (0.7, 0.6), vcc, pcbnew.PAD_SHAPE_RECT)
        fab_rect(df, dx, dy, 0, 0, 1.7, 1.25); crtyd_rect(df, dx, dy, 0, 0, 1.7, 1.25)
        b.Add(df)
        Rec(f"D_{pid}", 1, *pad_xy(df_p1))
        Rec(f"D_{pid}", 2, *pad_xy(df_p2))
        Rec(f"D_{pid}", 3, *pad_xy(df_p3))

    # ═══════════════════════════════════════════════
    # U1 — 13×18.5mm 16-pin 模块, UART 通信
    # 实际装配约束:
    #   IMU 靠拍头端, MCU 靠拍柄端; 两者都让长边沿 X 方向。
    #   IMU 信号/RF 避让区朝 X- 方向, MCU 信号/RF 避让区朝 X+ 方向。
    # 用户资料:
    #   原模块 D=18.5 长边, E=13.0 短边; 旋转后 fab = 18.5×13。
    #   2.0mm pitch, 推荐落盘 1.65×1.27mm; 旋转后焊盘尺寸取 1.27×1.65mm。
    #   实物邮票孔贴模块边缘, F.Fab/F.SilkS 外框即模块完整外边界。
    #   Pin 13/14 为 UART RXD/TXD, Pin 15/16 为 VBAT/VSS。
    # ═══════════════════════════════════════════════
    iw, ih = 18.5, 13.0                # 旋转后: X=长边18.5, Y=短边13
    esp_body_h = 18.0                  # ESP32 实物安装外框旋转后 Y 向高度
    module_gap = 3.0
    stack_h = ih + module_gap + esp_body_h
    stack_top_y = cy - stack_h / 2
    imu_x, imu_y = cx, stack_top_y + ih / 2
    mc_y = stack_top_y + ih + module_gap + esp_body_h / 2
    imu_pitch = 2.0; imu_n = 8         # 每侧 8 脚, 2.0mm pitch
    imu_pad_sz = (1.27, 1.65)          # 旋转后: X 为 pitch 方向, Y 为伸出方向
    imu_row_y = ih / 2                 # 邮票孔中心贴模块实物边线
    imu_span = (imu_n - 1) * imu_pitch / 2  # 7.0mm (X 方向 pin 跨距)

    imu_fp = make_fp("U1", "IM948", imu_x, imu_y)
    # Pin 1-8: 原左侧旋转到下侧, X 从左到右
    #  1=VSS, 2=VBUS, 3=VBAT, 4=VDDIO, 5=NC, 6=NC, 7=ADIN, 8=VSS
    l_net = [
        "GND",        # 1  VSS
        "VBUS",       # 2  USB 5V 充电输入
        "VCC",        # 3  锂电池 3.7V (VBAT)
        "VCC_3V3",    # 4  GPIO 电压域 (VDDIO, ≤3.4V!)
        "NC",         # 5
        "NC",         # 6
        "NC",         # 7  ADIN 当前未接
        "GND",        # 8  VSS
    ]
    for i in range(imu_n):
        net = N(l_net[i]) if l_net[i] != "NC" else None
        xo = (i - (imu_n - 1) / 2) * imu_pitch
        pad(imu_fp, i + 1, (xo, -imu_row_y), imu_pad_sz,
            net, pcbnew.PAD_SHAPE_RECT)
        Rec("U1", i + 1, imu_x + xo, imu_y - imu_row_y)

    # Pin 9-16: 原右侧旋转到上侧, X 从左到右为 Pin 9→16
    #  9=LED-B, 10=LED-R, 11=GPIO, 12=KEY, 13=RXD, 14=TXD, 15=VBAT, 16=VSS
    r_net = [
        "NC",         # 9  LED-B    (留空)
        "NC",         # 10 LED-R    (留空)
        "NC",         # 11 GPIO     (留空)
        "NC",         # 12 KEY      (留空)
        "UART_TX",    # 13 RXD ← ESP32 TX (IO16)
        "UART_RX",    # 14 TXD → ESP32 RX (IO17)
        "VCC",        # 15 VBAT
        "GND",        # 16 VSS      (双 GND 增强)
    ]
    for i in range(imu_n):
        net = N(r_net[i]) if r_net[i] != "NC" else None
        xo = (i - (imu_n - 1) / 2) * imu_pitch
        pad(imu_fp, i + imu_n + 1, (xo, imu_row_y), imu_pad_sz,
            net, pcbnew.PAD_SHAPE_RECT)
        Rec("U1", i + imu_n + 1, imu_x + xo, imu_y + imu_row_y)

    fab_rect(imu_fp, imu_x, imu_y, 0, 0, iw, ih)
    crtyd_rect(imu_fp, imu_x, imu_y, 0, 0, iw, ih)
    b.Add(imu_fp)
    for gnd_pin in [1, 8, 16]:
        via(gnd, *pp[("U1", gnd_pin)])
    gfx_rect(pcbnew.F_SilkS, imu_x - iw/2, imu_y - ih/2,
             imu_x + iw/2, imu_y + ih/2, 0.12)
    silk_text(imu_x, imu_y + ih/2 + 3.5, "IM948 IMU", 1.0, 0.12)
    silk_text(imu_x - imu_span, imu_y - imu_row_y - 1.4, "1", 0.6, 0.1)
    silk_text(imu_x + imu_span, imu_y - imu_row_y - 1.4, "8", 0.6, 0.1)
    silk_text(imu_x - imu_span, imu_y + imu_row_y + 1.4, "9", 0.6, 0.1)
    silk_text(imu_x + imu_span, imu_y + imu_row_y + 1.4, "16", 0.6, 0.1)

    # IMU 信号/RF 避让区: 朝 X- 方向, 13×3mm
    rf_x1, rf_y1 = imu_x - iw/2 - 3.0, imu_y - ih/2
    rf_x2, rf_y2 = imu_x - iw/2, imu_y + ih/2
    gfx_rect(pcbnew.User_4, rf_x1, rf_y1, rf_x2, rf_y2, 0.05)
    silk_text(rf_x1 - 1.0, imu_y, "IMU RF X-", 0.7, 0.1, 90)

    # ═══════════════════════════════════════════════
    # MCU J1 — v9.11 改用 Espressif 官方 ESP32-C6-WROOM-1 封装
    #   FootprintLoad() 加载官方 .kicad_mod
    #   旋转 90° 让 fab 长边沿 X (FPC 长边方向)
    #   28 邮票孔 + 9 EPAD 阵列
    #   旋转后:
    #     - Pad 1-14 沿 Y=+8.75 (下排), X 从 -8.26 到 +8.25
    #     - Pad 15-28 沿 Y=-8.75 (上排), X 从 -4.45 到 -8.26
    #     - fab 范围 26.72×19.72 (含 antenna 突出)
    #   mc_y 由 OpenSCAD 甜区槽中心/尺寸计算, 不能硬编码到螺丝区。
    # ═══════════════════════════════════════════════
    J1_LIB_PATH = str(PROJECT_ROOT / "fpc" / "footprints" / "Espressif.pretty")
    cf = pcbnew.FootprintLoad(J1_LIB_PATH, "ESP32-C6-WROOM-1")
    cf.SetReference("J1")
    cf.SetValue("ESP32-C6-WROOM-1")
    hide_fp_texts(cf)
    cf.SetPosition(pcbnew.VECTOR2I(mk(cx), mk(mc_y)))
    cf.SetOrientationDegrees(90)  # fab 长边 → X 方向
    # 官方封装自带的 antenna keepout 在旋转后的 footprint 内会覆盖左侧绕线通道。
    # 本板按实物装配单独在 X+ 方向画 RF 避让框, 因此移除官方局部 keepout zone。
    for z in list(cf.Zones()):
        if z.GetZoneName() == "antenna keepout":
            cf.Remove(z)
    # 官方封装把天线区域边界和局部外框画在 F.SilkS, 容易被误读为安装外框。
    # 保留官方信息到 Eco2.User, 板级重新画唯一的实物外框与 X+ 避让框。
    for gi in cf.GraphicalItems():
        if gi.GetLayer() == pcbnew.F_SilkS:
            gi.SetLayer(pcbnew.Eco2_User)

    # 旋转 90° 后 pad 全局坐标 (从刚才的实测确认):
    #   Pad 1-14: Y = +8.75, X 从 -8.26 到 +8.25 (沿 +X 递增)
    #   Pad 15-28: Y = -8.75, X 从 -8.26 到 +8.25 (沿 +X 递减, 180° 旋转 pad)
    # 引脚功能来自 ESP32-C6-WROOM-1 datasheet (用户 2026-06-11 提供官方资料):
    #   Pin 1=GND, 2=3V3, 3=EN, 4=IO4, 5=IO5, 6=IO6, 7=IO7, 8=IO8, 9=IO9, 10=IO10,
    #   11=IO11, 12=IO12, 13=IO13, 14=IO14 (下排 X=-8.26 → +8.25)
    #   Pin 15=IO15, 16=IO16, 17=IO17, 18=IO18, 19=IO19, 20=IO20, 21=IO21, 22=IO22,
    #   23=IO23, 24=IO24, 25=IO25, 26=IO26, 27=IO27, 28=GND (上排 X=+8.25 → -8.26)
    # 注意: ESP32-C6-WROOM-1 实物 pin 1 实际是 GND, 但 datasheet pin 序是:
    #   datasheet 是按芯片本体 pin, WROOM-1 模块把 chip pin 重新编号
    # 用户指定的 pin 功能映射 (2026-06-10):
    #   下排 (Pad 1-14, X=-8.26 → +8.25):
    #     1=GND, 2=3V3, 3=EN, 4=IO4/PZT_TR, 5=IO5/PZT_TL, 6=IO6/PZT_BR, 7=IO7/PZT_BL,
    #     8=IO8, 9=IO9, 10=IO10, 11=IO11, 12=IO12, 13=IO13/USB_D+, 14=IO14
    #   上排 (Pad 15-28, X=+8.25 → -8.26):
    #     15=IO15, 16=IO16/USB_D-, 17=IO17, 18=IO18, 19=IO19, 20=IO20, 21=IO21,
    #     22=IO22, 23=IO23, 24=IO24/UART_TX, 25=IO25/UART_RX, 26=IO26, 27=IO27, 28=GND
    j1_nets = {
        1: "GND", 2: "VCC", 3: "EN",
        4: "PZT_TR_SIGNAL", 5: "PZT_TL_SIGNAL",
        6: "PZT_BR_SIGNAL", 7: "PZT_BL_SIGNAL",
        8: "NC", 9: "NC", 10: "NC", 11: "NC", 12: "NC",
        13: "USB_D+", 14: "NC",
        15: "NC", 16: "USB_D-", 17: "NC", 18: "NC", 19: "NC", 20: "NC",
        21: "NC", 22: "NC", 23: "NC",
        24: "UART_TX",  # IO24 → IMU RXD (U1 pin 13)
        25: "UART_RX",  # IO25 ← IMU TXD (U1 pin 14)
        26: "NC", 27: "NC", 28: "GND",
    }
    # EPAD (Pad "29", 9 个) → GND (散热)
    for p in list(cf.Pads()):
        pnum = p.GetNumber()
        if pnum == "29":
            p.SetNet(gnd)
        else:
            pin_int = int(pnum)
            net_name = j1_nets.get(pin_int, "NC")
            if net_name != "NC":
                p.SetNet(N(net_name))
            # NC pin 不连 net, 留 None (有 pad 物理存在)

    b.Add(cf)
    # 记录 pin 坐标供走线用 (旋转 90° 后的全局坐标)
    half_w_v = 8.75          # 旋转后 pad 距 X 轴距离
    half_span_v = 8.255       # X 方向 pin 跨距 (1.27×13/2)
    pitch_v = 1.27
    # Pad 1-14: X 从 -8.26 → +8.25 (沿 +X 方向, X 递增)
    # Pad 15-28: 180° 旋转, X 从 +8.25 → -8.26 (沿 -X 方向)
    for i in range(14):
        xo = (i - 6.5) * pitch_v  # X 从 -8.255 到 +8.255
        Rec("J1", i + 1, cx + xo, mc_y + half_w_v)
    for i in range(14):
        xo = -((i - 6.5) * pitch_v)  # X 反向 (Pin 15 在 +X 端)
        Rec("J1", i + 15, cx + xo, mc_y - half_w_v)

    # 官方封装 EPAD 是 3×3 独立 GND pad, 需要显式连成一组并下接 B.Cu GND。
    epad_pts = sorted([pad_xy(p) for p in cf.Pads() if p.GetNumber() == "29"],
                      key=lambda pt: (round(pt[1], 3), round(pt[0], 3)))
    epad_rows = {}
    epad_cols = {}
    for ex, ey in epad_pts:
        epad_rows.setdefault(round(ey, 3), []).append((ex, ey))
        epad_cols.setdefault(round(ex, 3), []).append((ex, ey))
    for row in epad_rows.values():
        row.sort()
        for a, c in zip(row, row[1:]):
            track(gnd, a[0], a[1], c[0], c[1], TRACE_PWR)
    for col in epad_cols.values():
        col.sort(key=lambda pt: pt[1])
        for a, c in zip(col, col[1:]):
            track(gnd, a[0], a[1], c[0], c[1], TRACE_PWR)
    if epad_pts:
        via(gnd, *epad_pts[len(epad_pts) // 2])
    via(gnd, *pp[("J1", 28)])

    # ESP32 实物安装外框: 官方本地外框 x=-9..9, y=-15.75..9.75;
    # 旋转 90° 后成为 X=-9.75..15.75, Y=-9..9。
    esp_x1, esp_y1 = cx - 9.75, mc_y - 9.0
    esp_x2, esp_y2 = cx + 15.75, mc_y + 9.0
    gfx_rect(pcbnew.F_SilkS, esp_x1, esp_y1, esp_x2, esp_y2, 0.12)
    silk_text(cx, mc_y + half_w_v + 4.0, "ESP32-C6-WROOM-1", 1.0, 0.12)

    # MCU 信号/RF 避让区: 朝 X- 方向 (antenna 朝 IMU, 拍头端), 19.7×3mm
    # 实物 antenna 朝 X+ (ESP32 长边内) - 不对, antenna 在 fab 内 -Y 端 (官方 silk "Antenna Area" at 0 -12.75)
    # 旋转 90° CCW: 原 -Y → +X, 即 antenna 沿 +X 方向
    # antenna keepout 放 X+ 方向 (远离 IMU)
    rf_x1, rf_y1 = esp_x2, esp_y1
    rf_x2, rf_y2 = esp_x2 + 3.0, esp_y2
    gfx_rect(pcbnew.User_5, rf_x1, rf_y1, rf_x2, rf_y2, 0.05)
    silk_text(rf_x2 + 1.0, mc_y, "ESP32 RF X+", 0.7, 0.1, 90)

    # 更新 ESP32 fab 范围用于 stiffener (用官方 fab 范围)
    fw, fh = 26.72, 19.72

    # ═══════════════════════════════════════════════
    # 拍柄末端引出焊盘 (修正 B:4×3mm + C:文字90°)
    # ═══════════════════════════════════════════════
    all_y = [y for _,y in opts]
    bot_y = max(all_y) - 4    # 拍柄端: Y 翻转后拍柄在屏下方 = max(Y), 留足板边间距
    # v9.10 修复: 4 个终端 pad 间距 4.5mm (pad 宽 4mm, 必须 >= pad 宽避免重叠)
    term = [("VCC",-6.75),("GND",-2.25),("D+",2.25),("D-",6.75)]
    term_w, term_h = 4.0, 3.0
    for label,xo in term:
        nn = "VCC" if label=="VCC" else "GND" if label=="GND" else f"USB_{label}"
        tf = make_fp(f"TP_{label}", label, xo, bot_y)
        pad(tf, 1, (0,0), (term_w, term_h), N(nn), pcbnew.PAD_SHAPE_RECT)
        fab_rect(tf, xo, bot_y, 0, 0, term_w, term_h)
        crtyd_rect(tf, xo, bot_y, 0, 0, term_w, term_h)
        b.Add(tf); Rec(f"TP_{label}", 1, xo, bot_y)
        silk_text(xo, bot_y + 3.0, label, 0.9, 0.12)
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
            # ESP32-C6 摆 X 长后 fab 框 25.5×18, stiffener 加 1mm 余量
            gfx_rect(pcbnew.User_3, cx-fw/2-1, mc_y-fh/2-1, cx+fw/2+1, mc_y+fh/2+1, 0.05)

    for koz in params.get("keep_out_zones", []):
        cr = koz.get("clearance_radius", 3.5)
        for hx,hy in koz.get("positions", []):
            # 中线 2 颗螺丝已经有 NPTH 实物, 不再画大 keepout 圆 (避免中央视觉混乱)
            if hx == 0 and hy in [18, -33]:
                continue
            gfx_circle(pcbnew.User_4, hx, hy, cr, 0.05)

    for koz in params.get("keep_out_zones", []):
        tp = koz.get("type","")
        label = "\u9500\u5B54" if "pin" in tp else "\u87BA\u4E1D" if "screw" in tp else ""
        if label:
            for hx,hy in koz.get("positions", []):
                silk_text(hx, hy-3.5, label, 0.7, 0.1)

    # ═══ 中线 NPTH 螺丝孔 — FPC 必须避让 2 颗中线螺丝 (Y 翻后 Y=+33/-18) ═══
    # Y 翻后: (0, 18)→(0, -18) [拍头端, 紧贴 IMU fab 框 Y=0.5 下侧]
    #         (0, -33)→(0, +33) [拍柄端, 紧贴 ESP32 fab 框 Y=26 上侧]
    # 螺丝 clearance Ø2.2, pad 直径 3.0 (留 0.4mm 边距)
    for hy in [-18, 33]:
        mh = pcbnew.FOOTPRINT(b)                 # 容器 fp
        mh.SetReference("")
        mh.SetValue(f"M2_NPTH")
        mh.SetPosition(pcbnew.VECTOR2I(0, mk(hy)))
        thru = pcbnew.PAD(mh)
        thru.SetNumber("")                       # 无 pin 编号
        thru.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
        thru.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)  # 非电镀通孔
        # KiCad 9 正确 API: SetFPRelativePosition 设 fp 内部 (0, 0)
        thru.SetFPRelativePosition(pcbnew.VECTOR2I(0, 0))
        thru.SetSize(pcbnew.VECTOR2I(mk(3.0), mk(3.0)))
        thru.SetDrillSize(pcbnew.VECTOR2I(mk(2.2), mk(2.2)))
        ls = pcbnew.LSET()
        for ly in [pcbnew.Edge_Cuts, pcbnew.F_Cu, pcbnew.B_Cu]:
            ls.addLayer(ly)
        thru.SetLayerSet(ls)
        mh.Add(thru)
        b.Add(mh)
        silk_text(0, hy + 3.5, "M2", 0.7, 0.1)   # silk 标记

    # ESP32 EN 上拉电阻位。不能把 EN 直接短到 VCC, 否则 DRC 会正确报短路。
    r_en_x, r_en_y = cx - 5.72, mc_y + half_w_v + 2.4
    r_en = make_fp("R_EN", "10k", r_en_x, r_en_y)
    r_en_p1 = pad(r_en, 1, (0, -0.8), (1.0, 0.7), en, pcbnew.PAD_SHAPE_RECT)
    r_en_p2 = pad(r_en, 2, (0, 0.8), (1.0, 0.7), vcc, pcbnew.PAD_SHAPE_RECT)
    fab_rect(r_en, r_en_x, r_en_y, 0, 0, 1.6, 0.8)
    crtyd_rect(r_en, r_en_x, r_en_y, 0, 0, 1.6, 0.8)
    b.Add(r_en)
    Rec("R_EN", 1, *pad_xy(r_en_p1))
    Rec("R_EN", 2, *pad_xy(r_en_p2))

    # ═══════════════════════════════════════════════
    # 走线 (v9.2 — 适配 IMU/MCU 摆 X 长后所有 pin 沿 X 分布)
    # ═══════════════════════════════════════════════
    NECK_Y1 = -71.7; NECK_Y2 = -78.5   # 拍头→拍柄 肩膀区域
    SPINE_L = -22; SPINE_R = 22

    # ESP32 pin 坐标 (官方封装, 旋转 90° CCW 后 fab 26.72×19.72)
    # 实测 pcbnew 输出 (权威):
    #   Pad 1-14 全局: Y = mc_y + 8.75, X 从 -8.26 (Pin 1) → +8.25 (Pin 14)
    #   Pad 15-28 全局: Y = mc_y - 8.75, X 从 +8.25 (Pin 15) → -8.26 (Pin 28)
    # pcbnew 内 fp SetOrientationDegrees(90) 的旋转矩阵对应 (x, y) → (y, -x)
    # 而非常见的 CCW (-y, x):
    #   Pad 1 局部 (-8.75, -8.26) → 全局偏移 (-8.26, +8.75)
    #   Pad 14 局部 (-8.75, +8.25) → 全局 (+8.25, +8.75) ✓
    #   Pad 15 局部 (+8.75, -8.26) → 全局 (-8.26, -8.75) ✓ [Pad 自身旋转 180°, fp 90°: 总 270°]
    #   Pad 28 局部 (+8.75, +8.25) → 全局 (+8.25, -8.75) ✓
    # 简化为实测的全局公式:
    #   Pin 1-14:  X = -(i-6.5)*1.27,  Y = +8.75    [i = pin-1]
    #   Pin 15-28: X = +(i-6.5)*1.27,  Y = -8.75    [i = pin-15]
    #   Pin 1 (i=0):  X = -(-6.5)*1.27 = -8.255 ✓ (-8.26 接近)
    #   Pin 14 (i=13): X = -(13-6.5)*1.27 = +8.255 ✓
    #   Pin 15 (i=0):  X = +(-6.5)*1.27 = -8.255? 但实测 Pin 15 在 X=+8.25!
    # 重新核对 (实测):
    #   Pad 1: X=-8.26 (i=0), Pad 14: X=+8.25 (i=13) → X = (i-6.5)*1.27 + 修正
    #     (i=0)→X=-8.26: (0-6.5)*1.27 = -8.255 ✓
    #     (i=13)→X=+8.25: (13-6.5)*1.27 = +8.255 ✓
    #   Pad 15: X=+8.25 (i=0), Pad 28: X=-8.26 (i=13)
    #     Pin 15 (i=0) → X=+8.25: 但 (0-6.5)*1.27 = -8.255 (负), 不匹配!
    # 正确公式 (Pad 15 是 Pin 14 的镜像, 反 X):
    #   Pin 15-28: X = -(i-6.5)*1.27 (反方向)
    #     (i=0) → X = -(-6.5)*1.27 = +8.255 ✓ (Pad 15 = +8.25)
    #     (i=13) → X = -(6.5)*1.27 = -8.255 ✓ (Pad 28 = -8.26)
    def j1_pin_xy(pin_num):
        """返回 ESP32 pin 全局坐标 (官方封装旋转 90° 后, pcbnew 实测)"""
        pitch = 1.27
        if pin_num <= 14:
            i = pin_num - 1
            x = (i - 6.5) * pitch    # -8.26 → +8.25
            y = +8.75                # 下排 (Y = mc_y + 8.75)
        else:
            i = pin_num - 15
            x = -((i - 6.5) * pitch) # +8.25 → -8.26 (反方向)
            y = -8.75                # 上排 (Y = mc_y - 8.75)
        return (cx + x, mc_y + y)

    # PZT 信号 → J1 ADC 引脚: IO4(4), IO5(5), IO6(6), IO7(7)
    # 长距离段走 B.Cu 左右走廊, 从 D1 与 J1 pin 附近用 via 出入,
    # 避免在 F.Cu 中线穿过 IMU、M2 和 ESP32 EPAD。
    def route_signal_v92(pid, side_x, pin_num, lane_y):
        sn = N(f"{pid}_SIGNAL")
        d1 = pp[(f"D_{pid}",1)]
        jp = j1_pin_xy(pin_num)
        entry = (side_x, d1[1])
        exitp = (jp[0], lane_y)
        track(sn, d1[0], d1[1], entry[0], entry[1])
        via(sn, *entry)
        route(sn, [entry, (side_x, lane_y), exitp], layer=pcbnew.B_Cu)
        via(sn, *exitp)
        track(sn, exitp[0], exitp[1], jp[0], jp[1])

    route_signal_v92("PZT_TR", SPINE_R, 4, 26.0)
    route_signal_v92("PZT_TL", SPINE_L, 5, 27.4)
    route_signal_v92("PZT_BR", SPINE_R, 6, 28.8)
    route_signal_v92("PZT_BL", SPINE_L, 7, 30.2)

    # VCC/GND 从拍柄终端拉到 J1 供电脚。
    # GND 用 B.Cu 绕过 VCC 竖线和 ESP32 官方 antenna keepout。
    power_targets = {
        "VCC": j1_pin_xy(2),
        "GND": j1_pin_xy(1),
    }
    vcc_tp = pp[("TP_VCC", 1)]
    gnd_tp = pp[("TP_GND", 1)]
    vcc_target = power_targets["VCC"]
    gnd_target = power_targets["GND"]
    route(vcc, [vcc_tp, (vcc_target[0], vcc_tp[1]), vcc_target], TRACE_PWR)
    gnd_entry = (gnd_tp[0], gnd_tp[1] - 2.0)
    gnd_exit = (gnd_target[0], gnd_target[1] + 2.0)
    track(gnd, gnd_tp[0], gnd_tp[1], gnd_entry[0], gnd_entry[1], TRACE_PWR)
    via(gnd, *gnd_entry)
    gnd_spine = (-8.25, gnd_entry[1])
    route(gnd, [gnd_entry, gnd_spine], TRACE_PWR, pcbnew.B_Cu)
    via(gnd, *gnd_spine)
    route(gnd, [gnd_spine, (-8.25, gnd_exit[1]), gnd_exit, gnd_target], TRACE_PWR)

    # UART: U1(13:RXD, 14:TXD) ↔ J1(24:TXD/IO24, 25:RXD/IO25)
    # U1 信号侧朝 X-, J1 信号侧朝 X+; 走线先引到模块间汇流 Y=0。
    u1_rxd = pp[("U1", 13)]  # U1 RXD 中心, 接 J1 TXD
    u1_txd = pp[("U1", 14)]  # U1 TXD 中心, 接 J1 RXD
    j1_tx  = j1_pin_xy(24)  # IO24 TXD 中心 (Pin 24, 全局 (-3.18, 4.60))
    j1_rx  = j1_pin_xy(25)  # IO25 RXD 中心 (Pin 25, 全局 (-4.45, 4.60))
    # TX (J1→U1): U1 RXD pin 13 → J1 TX pin 24, 在两模块之间短接。
    route(N("UART_TX"), [u1_rxd, (u1_rxd[0], 2.35), (j1_tx[0], 2.35), j1_tx])
    # RX (U1→J1): 另一根走 B.Cu 避免和 TX/模块边界交叉。
    rx_entry = (u1_txd[0], 2.9)
    rx_exit = (j1_rx[0], 3.35)
    track(N("UART_RX"), u1_txd[0], u1_txd[1], rx_entry[0], rx_entry[1])
    via(N("UART_RX"), *rx_entry)
    route(N("UART_RX"), [rx_entry, (8.8, rx_entry[1]), (8.8, rx_exit[1]), rx_exit],
          layer=pcbnew.B_Cu)
    via(N("UART_RX"), *rx_exit)
    track(N("UART_RX"), rx_exit[0], rx_exit[1], j1_rx[0], j1_rx[1])

    for sc in params["components"]["signal_conditioning"]:
        pid = sc["piezo"]; sn = N(f"{pid}_SIGNAL")
        p1=pp[(pid,1)]
        r1=pp[(f"R_{pid}",1)]; r2=pp[(f"R_{pid}",2)]
        d1=pp[(f"D_{pid}",1)]; d2=pp[(f"D_{pid}",2)]
        # PZT GND 翻边焊盘位于 PZT 中心与调理器件之间; 信号线必须切向绕开。
        vx, vy = r1[0] - p1[0], r1[1] - p1[1]
        mag = math.hypot(vx, vy) or 1.0
        px, py = -vy / mag, vx / mag
        # 左右两侧用相反切向, 让走线绕到各自 PZT 外侧。
        # 底部 PZT 的局部几何相反, 切向符号需要翻转, 否则会擦过 GND 翻边焊盘。
        side = 1 if p1[0] >= 0 else -1
        if p1[1] > 0:
            side *= -1
        off = 6.0 * side
        dog1 = (p1[0] + px * off, p1[1] + py * off)
        if p1[1] > 0:
            # 底部两片的 R_GND pad 位于进线侧, 先进入 D1 signal 再回接 R1。
            dvx, dvy = d1[0] - d2[0], d1[1] - d2[1]
            dmag = math.hypot(dvx, dvy) or 1.0
            d_approach = (d1[0] + dvx / dmag * 1.4, d1[1] + dvy / dmag * 1.4)
            dog2 = (d_approach[0] + px * off * 0.35, d_approach[1] + py * off * 0.35)
            route(sn, [p1, dog1, dog2, d_approach, d1, r1])
        else:
            dog2 = (r1[0] + px * off * 0.65, r1[1] + py * off * 0.65)
            avx, avy = r1[0] - r2[0], r1[1] - r2[1]
            amag = math.hypot(avx, avy) or 1.0
            approach = (r1[0] + avx / amag * 1.3, r1[1] + avy / amag * 1.3)
            route(sn, [p1, dog1, dog2, approach, r1, d1])

    # EN 通过 R_EN 上拉到 VCC。
    j1_en = j1_pin_xy(3)    # X=-5.715, Y=-25.15
    j1_3v3 = j1_pin_xy(2)   # X=-6.985, Y=-25.15
    r_en_1 = pp[("R_EN", 1)]
    r_en_2 = pp[("R_EN", 2)]
    route(en, [j1_en, (j1_en[0], r_en_1[1]), r_en_1], TRACE_PWR)
    route(vcc, [r_en_2, (j1_3v3[0], r_en_2[1]), j1_3v3], TRACE_PWR)

    # IMU supply pins: route on F.Cu around the left side of the ESP32 body,
    # keeping the antenna keepout clear.
    u1_vbat_a = pp[("U1", 3)]
    u1_vbat_b = pp[("U1", 15)]
    u1_vbat_escape = (u1_vbat_a[0], -15.0)
    route(vcc, [j1_3v3, (j1_3v3[0], 19.0), (-18.0, 19.0),
                (-18.0, -15.0), u1_vbat_escape, u1_vbat_a], TRACE_PWR)
    route(vcc, [u1_vbat_escape, (-18.0, -15.0), (-18.0, -3.0),
                (u1_vbat_b[0], -3.0), u1_vbat_b], TRACE_PWR)

    # BAT54S clamp rails: feed from TP_VCC on B.Cu using left/right outer corridors.
    # X=±30 stays outside the PZT signal pads and outside the B.Cu PZT signal spines.
    tp_vcc = pp[("TP_VCC", 1)]
    via(vcc, *tp_vcc)
    left_top_bus_x, left_bottom_bus_x, right_bus_x = -26.0, -30.0, 28.0
    left_top_y = pp[("D_PZT_TL", 3)][1]
    left_bottom_y = pp[("D_PZT_BL", 3)][1]
    right_top_y = pp[("D_PZT_TR", 3)][1]
    route(vcc, [tp_vcc, (left_top_bus_x, tp_vcc[1]), (left_top_bus_x, left_top_y)],
          TRACE_PWR, pcbnew.B_Cu)
    route(vcc, [tp_vcc, (left_bottom_bus_x, tp_vcc[1]), (left_bottom_bus_x, left_bottom_y)],
          TRACE_PWR, pcbnew.B_Cu)
    route(vcc, [tp_vcc, (right_bus_x, tp_vcc[1]), (right_bus_x, right_top_y)],
          TRACE_PWR, pcbnew.B_Cu)
    for pid in ["PZT_TL", "PZT_BL", "PZT_TR", "PZT_BR"]:
        p = pp[(f"D_{pid}", 3)]
        if pid == "PZT_TL":
            x = left_top_bus_x
        elif pid == "PZT_BL":
            x = left_bottom_bus_x
        else:
            x = right_bus_x
        via(vcc, *p)
        route(vcc, [(x, p[1]), p], TRACE_PWR, pcbnew.B_Cu)

    # D+/D- 从拍颈上拉到 J1 [实物 2026-06-10]:
    #   D+ → J1(13)=IO13/USB_D+ (下排)
    #   D- → J1(16)=IO18/USB_D- (上排 X=-6.985, Y=-8.85)
    usb_dp_tp = pp[("TP_D+", 1)]
    usb_dn_tp = pp[("TP_D-", 1)]
    usb_dp_jp = j1_pin_xy(13)
    usb_dn_jp = j1_pin_xy(16)
    usb_bottom_y = bot_y - 4.2
    dp_lane_y = usb_dp_jp[1] + 1.8
    route(N("USB_D+"), [usb_dp_tp, (usb_dp_tp[0], dp_lane_y),
                        (usb_dp_jp[0], dp_lane_y), usb_dp_jp])

    dn_entry = (12.0, usb_dn_tp[1])
    dn_exit = (12.0, usb_dn_jp[1] + 1.8)
    route(N("USB_D-"), [usb_dn_tp, dn_entry, dn_exit, (usb_dn_jp[0], dn_exit[1]), usb_dn_jp])

    for pid in ["PZT_TR","PZT_TL","PZT_BR","PZT_BL"]:
        for ref,pn in [(pid,2),(f"R_{pid}",2),(f"D_{pid}",2)]:
            if (ref,pn) in pp: via(gnd, pp[(ref,pn)][0], pp[(ref,pn)][1])
    # J1 是模块落盘, 不放中心 EPAD/近端接地 via, 避免压到 castellated pads。

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
    # 保留拍头尖端左右相邻点, 避免闭合线段在尖端附近形成自交。
    keep_idx.update({0, 1, n_raw - 1})
    # 补拍尾全精度 (Y 最低点 X 最低+5mm)
    for i, (x, y) in enumerate(outline_raw):
        if y < ymin + 5:
            keep_idx.add(i)
    keep_idx = sorted(keep_idx)
    outline_pts = [outline_raw[i] for i in keep_idx]
    outline_pts = [
        p for p in outline_pts
        if not (abs(p[0]) < 0.01 and ymin < p[1] < ymin + 1.0)
    ]
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

    fill_script = Path(__file__).resolve().parent / "fill_zones.py"
    subprocess.run([sys.executable, str(fill_script), str(OUTPUT_FILE)], check=False)

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

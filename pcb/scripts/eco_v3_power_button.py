#!/usr/bin/env python3
"""V3 power/button ECO on a PCB *copy* — does not run atopile placement.

Usage:
  /Applications/KiCad/.../python3 pcb/scripts/eco_v3_power_button.py \\
      --board pcb/layouts/default/default.kicad_pcb.eco-wip
"""

from __future__ import annotations

# ===== 分区：导入/依赖 =====
import argparse
import json
import sys
from pathlib import Path

# ===== 分区：常量/配置 =====
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BOARD = ROOT / "pcb" / "layouts" / "default" / "default.kicad_pcb.eco-wip"
CORRIDOR_SNAPSHOT = ROOT / "pcb" / "layouts" / "default" / "corridor_snapshot.json"

# 宽栈道机械位：4.5×4.5 THT（与尾键同规格）；旧 TP_MCU_* 脚本位保留勿覆盖
BRINGUP_POS = {
    "debug_sw.sw_boot": (4.870, 49.706, 90.0),
    "debug_sw.sw_en": (4.870, 57.995, 90.0),
    "debug_sw.sw_pwr": (4.870, 66.294, 90.0),
    "bringup.tp_mcu_boot": (-3.130, 49.706, 0.0),
    "bringup.tp_mcu_en": (-3.130, 56.720, 0.0),
    "bringup.gnd_pad": (-3.130, 43.000, 0.0),
    "bringup.vbat_pad": (-3.130, 63.500, 0.0),
    "bringup.vcc_pad": (19.050, -13.335, 0.0),
}

READABLE_REFS = {
    "debug_sw.sw_boot": ("SW_BOOT", "4.5x4.5"),
    "debug_sw.sw_en": ("SW_EN", "4.5x4.5"),
    "bringup.gnd_pad": ("TP_GND", "GND"),
    "bringup.vcc_pad": ("TP_3V3", "3V3"),
    "bringup.vbat_pad": ("TP_VBAT", "VBAT_SW"),
    "bringup.tp_mcu_boot": ("TP_MCU_BOOT", "BOOT"),
    "bringup.tp_mcu_en": ("TP_MCU_EN", "EN"),
    "power.d_btn_start": ("D_BTN_START", "1N4148W"),
    "power.d_ldo_bat": ("D_LDO_BAT", "SS14"),
    "power.d_ldo_usb": ("D_LDO_USB", "SS14"),
    "power.r_button_series": ("PW_R_BTN_SER_1K", "1k"),
}


# ===== 分区：私有成员 =====
def _mm(pcbnew, x: float, y: float):
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))


def _addr(fp) -> str | None:
    try:
        if hasattr(fp, "HasProperty") and fp.HasProperty("atopile_address"):
            return fp.GetProperty("atopile_address")
        if hasattr(fp, "HasFieldByName") and fp.HasFieldByName("atopile_address"):
            return fp.GetFieldByName("atopile_address").GetText()
        # KiCad 9 fallback
        for prop in ("atopile_address",):
            try:
                return fp.GetProperty(prop)
            except Exception:
                pass
    except Exception:
        return None
    return None


def _fp_by_addr(board) -> dict:
    out = {}
    for fp in list(board.GetFootprints()):
        try:
            a = _addr(fp)
        except Exception:
            continue
        if a:
            out[a] = fp
    return out


def _fp_by_ref(board, ref: str):
    for fp in board.GetFootprints():
        if fp.GetReference() == ref:
            return fp
    return None


def _ensure_net(board, pcbnew, name: str):
    net = board.FindNet(name)
    if net is None:
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
    return net


def _set_pad_net(board, pcbnew, fp, pad_num: str, net_name: str | None) -> None:
    for pad in fp.Pads():
        if pad.GetNumber() != pad_num:
            continue
        if net_name is None or net_name == "":
            pad.SetNetCode(0)
        else:
            pad.SetNet(_ensure_net(board, pcbnew, net_name))
        return
    raise KeyError(f"pad {pad_num} not on {fp.GetReference()}")


def _delete_tracks_touching_nets(board, net_names: set[str], only_no_net: bool = False) -> int:
    """Delete copper tracks/vias. If only_no_net, delete tracks with empty net name."""
    dead = []
    for t in list(board.GetTracks()):
        name = t.GetNetname() or ""
        if only_no_net:
            if name == "":
                dead.append(t)
            continue
        if name in net_names:
            dead.append(t)
    for t in dead:
        board.Delete(t)
    return len(dead)


def _delete_tracks_between_pads(board, pcbnew, a_fp, a_pad, b_fp, b_pad) -> int:
    """Remove any track segment whose endpoints are near both pads (approx bbox)."""
    pa = next(p for p in a_fp.Pads() if p.GetNumber() == a_pad)
    pb = next(p for p in b_fp.Pads() if p.GetNumber() == b_pad)
    ax, ay = pcbnew.ToMM(pa.GetPosition().x), pcbnew.ToMM(pa.GetPosition().y)
    bx, by = pcbnew.ToMM(pb.GetPosition().x), pcbnew.ToMM(pb.GetPosition().y)
    tol = 0.8
    dead = []
    for t in list(board.GetTracks()):
        if t.GetClass() != "PCB_TRACK":
            continue
        sx, sy = pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y)
        ex, ey = pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y)

        def near(x, y, tx, ty):
            return abs(x - tx) <= tol and abs(y - ty) <= tol

        if (near(sx, sy, ax, ay) and near(ex, ey, bx, by)) or (
            near(sx, sy, bx, by) and near(ex, ey, ax, ay)
        ):
            dead.append(t)
    for t in dead:
        board.Delete(t)
    return len(dead)


def _add_track(board, pcbnew, net_name: str, x1, y1, x2, y2, width=0.25, layer=None) -> None:
    if layer is None:
        layer = pcbnew.F_Cu
    track = pcbnew.PCB_TRACK(board)
    track.SetStart(_mm(pcbnew, x1, y1))
    track.SetEnd(_mm(pcbnew, x2, y2))
    track.SetWidth(pcbnew.FromMM(width))
    track.SetLayer(layer)
    track.SetNet(_ensure_net(board, pcbnew, net_name))
    board.Add(track)


def _pad_xy(pcbnew, fp, pad_num: str) -> tuple[float, float]:
    for pad in fp.Pads():
        if pad.GetNumber() == pad_num:
            return pcbnew.ToMM(pad.GetPosition().x), pcbnew.ToMM(pad.GetPosition().y)
    raise KeyError(pad_num)


def _restore_bringup(board, pcbnew) -> None:
    by = _fp_by_addr(board)
    for addr, (x, y, rot) in BRINGUP_POS.items():
        fp = by.get(addr)
        if fp is None:
            print(f"WARN missing footprint for {addr}")
            continue
        fp.SetPosition(_mm(pcbnew, x, y))
        fp.SetOrientation(pcbnew.EDA_ANGLE(rot, pcbnew.DEGREES_T))
        alias = READABLE_REFS.get(addr)
        if alias:
            fp.SetReference(alias[0])
            fp.SetValue(alias[1])
    # Also rename any leftover power aliases
    for addr, (ref, val) in READABLE_REFS.items():
        fp = by.get(addr)
        if fp:
            fp.SetReference(ref)
            fp.SetValue(val)


def _write_corridor_snapshot() -> None:
    rows = [
        {"addr": addr, "x": x, "y": y, "rot": rot}
        for addr, (x, y, rot) in BRINGUP_POS.items()
    ]
    CORRIDOR_SNAPSHOT.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {CORRIDOR_SNAPSHOT}")


def _fix_imu_vddio(board, pcbnew) -> int:
    removed = 0
    imu = None
    for fp in board.GetFootprints():
        if "IM948" in fp.GetFPIDAsString() or _addr(fp) == "imu":
            imu = fp
            break
    if imu is None:
        print("WARN: IMU footprint not found")
        return 0
    # float pad 4
    _set_pad_net(board, pcbnew, imu, "4", None)
    # delete tracks/vias that were on VDDIO or still attached near pad4
    px, py = _pad_xy(pcbnew, imu, "4")
    dead = []
    for t in list(board.GetTracks()):
        name = t.GetNetname() or ""
        if name in ("VDDIO", "vddio"):
            dead.append(t)
            continue
        # tracks on vcc/3v3 that end near pad4
        if name in ("vcc", "VCC", "3V3", "VCC_3V3"):
            pts = []
            if t.GetClass() == "PCB_VIA":
                pts.append((pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y)))
            else:
                pts.append((pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y)))
                pts.append((pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y)))
            if any(abs(x - px) < 1.2 and abs(y - py) < 1.2 for x, y in pts):
                dead.append(t)
    for t in dead:
        board.Delete(t)
        removed += 1
    print(f"IMU VDDIO floated; removed {removed} nearby power copper items")
    return removed


def _fix_button_path(board, pcbnew) -> None:
    by = _fp_by_addr(board)
    # Prefer address lookup; fall back to refs
    d_btn = by.get("power.d_btn_start") or _fp_by_ref(board, "D_BTN_START") or _fp_by_ref(board, "D1")
    r_ser = by.get("power.r_button_series") or _fp_by_ref(board, "PW_R_BTN_SER_1K")
    mcu = by.get("mcu")
    if mcu is None:
        for fp in board.GetFootprints():
            if "SGFK_ESP32" in fp.GetFPIDAsString():
                mcu = fp
                break
    if not d_btn or not r_ser or not mcu:
        raise RuntimeError(f"missing parts d_btn={d_btn} r_ser={r_ser} mcu={mcu}")

    if d_btn.GetReference() in ("D1", "REF**", ""):
        d_btn.SetReference("D_BTN_START")
    d_btn.SetValue("1N4148W")

    # Nets: diode SOD-323 KiCad: pad1=cathode, pad2=anode
    # anode=P_GATE, cathode=btn_sw
    _set_pad_net(board, pcbnew, d_btn, "2", "p_gate")
    _set_pad_net(board, pcbnew, d_btn, "1", "btn_sw")
    # series R: btn_sw <-> user_btn (MCU pad16)
    _set_pad_net(board, pcbnew, r_ser, "1", "btn_sw")
    _set_pad_net(board, pcbnew, r_ser, "2", "user_btn")
    _set_pad_net(board, pcbnew, mcu, "16", "user_btn")
    _set_pad_net(board, pcbnew, mcu, "11", "pwr_latch")

    # Delete old copper that shorted wrong topology
    n1 = _delete_tracks_between_pads(board, pcbnew, r_ser, "2", mcu, "16")
    # Also delete any track that connects user_btn pad area incorrectly — rebuild
    n2 = 0
    for net in ("user_btn", "btn_sw", "p_gate"):
        # Only remove segments that are clearly between r_ser and mcu or r_ser and p_gate legacy
        pass
    # Broader: remove tracks on user_btn then re-add R→MCU
    user_tracks = [t for t in board.GetTracks() if (t.GetNetname() or "") == "user_btn"]
    for t in user_tracks:
        board.Delete(t)
        n2 += 1
    # Remove p_gate tracks that end on R series pads (legacy R was on p_gate)
    rx1, ry1 = _pad_xy(pcbnew, r_ser, "1")
    rx2, ry2 = _pad_xy(pcbnew, r_ser, "2")
    dead = []
    for t in list(board.GetTracks()):
        if (t.GetNetname() or "") != "p_gate" or t.GetClass() != "PCB_TRACK":
            continue
        pts = [
            (pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y)),
            (pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y)),
        ]
        if any(abs(x - rx1) < 0.9 and abs(y - ry1) < 0.9 for x, y in pts) or any(
            abs(x - rx2) < 0.9 and abs(y - ry2) < 0.9 for x, y in pts
        ):
            dead.append(t)
    for t in dead:
        board.Delete(t)
    print(f"removed button copper: between={n1} user_btn={n2} p_gate_at_R={len(dead)}")

    # Rebuild: btn_sw already to diode; ensure R↔MCU
    mx, my = _pad_xy(pcbnew, mcu, "16")
    _add_track(board, pcbnew, "user_btn", rx2, ry2, mx, my, width=0.25)
    # Diode pads to R / gate if needed (connectivity may already exist via zones)
    dx_c, dy_c = _pad_xy(pcbnew, d_btn, "1")  # cathode btn_sw
    dx_a, dy_a = _pad_xy(pcbnew, d_btn, "2")  # anode p_gate
    _add_track(board, pcbnew, "btn_sw", dx_c, dy_c, rx1, ry1, width=0.25)
    # p_gate to diode anode — short stub if not already connected by zone
    q_load = by.get("power.q_power") or _fp_by_ref(board, "PW_Q_LOAD")
    if q_load:
        gx, gy = _pad_xy(pcbnew, q_load, "1")  # gate
        _add_track(board, pcbnew, "p_gate", dx_a, dy_a, gx, gy, width=0.25)
    print("rewired: P_GATE→D_BTN_START→btn_sw→R→MCU16; MCU11=PWR_LATCH")


def _fix_ss14(board, pcbnew) -> None:
    by = _fp_by_addr(board)
    for addr, ref in (("power.d_ldo_bat", "D_LDO_BAT"), ("power.d_ldo_usb", "D_LDO_USB")):
        fp = by.get(addr) or _fp_by_ref(board, ref)
        if not fp:
            print(f"WARN missing {ref}")
            continue
        fp.SetReference(ref)
        fp.SetValue("SS14")
        # Ensure SOD-123 footprint id
        fpid = fp.GetFPIDAsString()
        if "SOD-123" not in fpid:
            print(f"WARN {ref} footprint is {fpid}, expected SOD-123 — replace manually if needed")
        # Clear copper under pads (no-net + old vias near pads)
        for pad in fp.Pads():
            px, py = pcbnew.ToMM(pad.GetPosition().x), pcbnew.ToMM(pad.GetPosition().y)
            dead = []
            for t in list(board.GetTracks()):
                pts = []
                if t.GetClass() == "PCB_VIA":
                    pts.append((pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y)))
                elif t.GetClass() == "PCB_TRACK":
                    pts += [
                        (pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y)),
                        (pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y)),
                    ]
                if any(abs(x - px) < 0.6 and abs(y - py) < 0.6 for x, y in pts):
                    # keep if same net as pad and looks intentional? User asked remove vias under new pads
                    if t.GetClass() == "PCB_VIA" or (t.GetNetname() or "") == "":
                        dead.append(t)
            for t in dead:
                board.Delete(t)
        # Re-stub anode/cathode to their nets from pad centers to nearest same-net copper is hard;
        # pad nets already set by ato — add short tracks to LDO/cap if known.
    # Reconnect LDO diodes: pad1=cathode→ldo_vin(cathode), pad2=anode→VBAT_SW / USB_VBUS
    bat = by.get("power.d_ldo_bat") or _fp_by_ref(board, "D_LDO_BAT")
    usb = by.get("power.d_ldo_usb") or _fp_by_ref(board, "D_LDO_USB")
    ldo = by.get("power.ldo") or _fp_by_ref(board, "PW_LDO_3V3")
    cin = by.get("power.c_in") or _fp_by_ref(board, "PW_C_IN_10U")
    # Normalize shared OR net name to ldo_vin if currently "cathode"
    or_net = "ldo_vin"
    for fp in (bat, usb, ldo, cin):
        if not fp:
            continue
        for pad in fp.Pads():
            if (pad.GetNetname() or "") == "cathode":
                pad.SetNet(_ensure_net(board, pcbnew, or_net))
    if bat and ldo:
        bx, by_ = _pad_xy(pcbnew, bat, "1")
        lx, ly = _pad_xy(pcbnew, ldo, "1")
        _add_track(board, pcbnew, or_net, bx, by_, lx, ly, width=0.4)
    if usb and ldo:
        ux, uy = _pad_xy(pcbnew, usb, "1")
        lx, ly = _pad_xy(pcbnew, ldo, "1")
        _add_track(board, pcbnew, or_net, ux, uy, lx, ly, width=0.4)
    if bat:
        # anode to VBAT_SW
        _set_pad_net(board, pcbnew, bat, "2", "VBAT_SW")
        _set_pad_net(board, pcbnew, bat, "1", or_net)
    if usb:
        _set_pad_net(board, pcbnew, usb, "2", "USB_VBUS")
        _set_pad_net(board, pcbnew, usb, "1", or_net)
    print("SS14 nets normalized to ldo_vin; stubs re-added")


def _clear_no_net(board) -> int:
    n = 0
    for t in list(board.GetTracks()):
        if (t.GetNetname() or "") == "":
            board.Delete(t)
            n += 1
    print(f"removed {n} <no net> copper items")
    return n


def _refill_zones(board, pcbnew) -> None:
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    print(f"refilled {len(list(board.Zones()))} zones")


def _assert_no_refstar(board) -> None:
    bad = [fp.GetReference() for fp in board.GetFootprints() if fp.GetReference() in ("REF**", "")]
    if bad:
        raise RuntimeError(f"still have blank/REF** refs: {bad[:10]}")


# ===== 分区：公开 API =====
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    parser.add_argument("--skip-zones", action="store_true")
    args = parser.parse_args()
    board_path = args.board.resolve()
    if not board_path.is_file():
        print(f"missing board: {board_path}", file=sys.stderr)
        return 2

    import pcbnew

    board = pcbnew.LoadBoard(str(board_path))
    if board is None:
        print(f"LoadBoard failed: {board_path}", file=sys.stderr)
        return 2
    _write_corridor_snapshot()
    _restore_bringup(board, pcbnew)
    _fix_imu_vddio(board, pcbnew)
    _fix_button_path(board, pcbnew)
    _fix_ss14(board, pcbnew)
    _clear_no_net(board)
    if not args.skip_zones:
        _refill_zones(board, pcbnew)
    _assert_no_refstar(board)
    board.Save(str(board_path))
    print(f"ECO saved: {board_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

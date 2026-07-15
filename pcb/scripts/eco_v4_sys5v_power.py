#!/usr/bin/env python3
"""V4 power ECO: remove SS14 OR, rename SYS_5V_*, float IMU VBAT/VDDIO.

Does NOT auto-route — leaves airwires for manual routing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BOARD = ROOT / "pcb" / "layouts" / "default" / "default.kicad_pcb"

# old_name -> new_name (do NOT map USB_VBUS globally — control finger handled per-pad)
NET_RENAME = {
    "vbat_in": "SYS_5V_IN",
    "VBAT_IN": "SYS_5V_IN",
    "VBAT_SW": "SYS_5V_SW",
    "vbat_sw": "SYS_5V_SW",
    "ldo_vin": "SYS_5V_SW",
    "cathode": "SYS_5V_SW",
    "vbus": "SYS_5V_SW",
    "vbat_sense": "bat_sense",
}

DELETE_REFS = {"D_LDO_BAT", "D_LDO_USB"}


def _ensure_net(board, pcbnew, name: str):
    net = board.FindNet(name)
    if net is None:
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
    return net


def _set_pad(board, pcbnew, fp, num: str, net_name: str | None) -> None:
    for pad in fp.Pads():
        if pad.GetNumber() != num:
            continue
        if not net_name:
            pad.SetNetCode(0)
        else:
            pad.SetNet(_ensure_net(board, pcbnew, net_name))
        return


def _rename_nets(board, pcbnew) -> int:
    n = 0
    # pads
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            old = pad.GetNetname() or ""
            if old in NET_RENAME:
                # skip IMU VBUS pad — handled specially (vbus→SYS_5V_SW ok actually)
                pad.SetNet(_ensure_net(board, pcbnew, NET_RENAME[old]))
                n += 1
    # tracks/vias
    for t in board.GetTracks():
        old = t.GetNetname() or ""
        if old in NET_RENAME:
            t.SetNet(_ensure_net(board, pcbnew, NET_RENAME[old]))
            n += 1
    # zones
    for z in board.Zones():
        old = z.GetNetname() or ""
        if old in NET_RENAME:
            z.SetNet(_ensure_net(board, pcbnew, NET_RENAME[old]))
            n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    args = ap.parse_args()
    board_path = args.board.resolve()
    import pcbnew

    board = pcbnew.LoadBoard(str(board_path))
    if board is None:
        print("LoadBoard failed", board_path)
        return 2

    # 1) delete SS14 diodes + their copper on ldo_vin-ish nets near them
    deleted_fp = 0
    for fp in list(board.GetFootprints()):
        if fp.GetReference() in DELETE_REFS:
            # delete tracks touching pads
            for pad in fp.Pads():
                px = pcbnew.ToMM(pad.GetPosition().x)
                py = pcbnew.ToMM(pad.GetPosition().y)
                for t in list(board.GetTracks()):
                    pts = []
                    if t.GetClass() == "PCB_VIA":
                        pts.append(
                            (pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y))
                        )
                    else:
                        pts += [
                            (pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y)),
                            (pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y)),
                        ]
                    if any(abs(x - px) < 0.8 and abs(y - py) < 0.8 for x, y in pts):
                        board.Delete(t)
            board.Delete(fp)
            deleted_fp += 1
            print("deleted", fp.GetReference() if False else "SS14 footprint")
    print(f"removed {deleted_fp} SS14 footprints")

    # 2) rename nets globally
    nren = _rename_nets(board, pcbnew)
    print(f"renamed {nren} pad/track/zone net refs")

    # 3) fix specific pads after rename
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        fpid = fp.GetFPIDAsString()
        if "IM948" in fpid or ref == "IMU_IM948":
            # pad2 VBUS → SYS_5V_SW; 3/4/15 float
            _set_pad(board, pcbnew, fp, "2", "SYS_5V_SW")
            _set_pad(board, pcbnew, fp, "3", None)
            _set_pad(board, pcbnew, fp, "4", None)
            _set_pad(board, pcbnew, fp, "15", None)
            print("IMU: VBUS=SYS_5V_SW; VBAT/VDDIO float")
        if ref == "PW_Q_LOAD":
            _set_pad(board, pcbnew, fp, "2", "SYS_5V_IN")  # source
            _set_pad(board, pcbnew, fp, "3", "SYS_5V_SW")  # drain
        if ref == "PW_LDO_3V3":
            _set_pad(board, pcbnew, fp, "1", "SYS_5V_SW")  # vin
            _set_pad(board, pcbnew, fp, "3", "SYS_5V_SW")  # en
        if ref == "PW_C_IN_10U":
            _set_pad(board, pcbnew, fp, "1", "SYS_5V_SW")
        if ref == "PW_R_GATE_100K":
            # p2 should be SYS_5V_IN
            for pad in fp.Pads():
                if pad.GetNumber() == "2":
                    pad.SetNet(_ensure_net(board, pcbnew, "SYS_5V_IN"))
        if ref == "TAIL_PWR":
            _set_pad(board, pcbnew, fp, "F", "SYS_5V_IN")
            _set_pad(board, pcbnew, fp, "B", "gnd")
        if ref == "TAIL_LED":
            _set_pad(board, pcbnew, fp, "F", "SYS_5V_SW")
        if ref == "TAIL_CTL":
            _set_pad(board, pcbnew, fp, "B", "bat_cell_p")
        if ref == "BAT_R_TOP_1M":
            _set_pad(board, pcbnew, fp, "1", "bat_cell_p")
            _set_pad(board, pcbnew, fp, "2", "bat_sense")
        if ref == "BAT_R_BOT_1M":
            _set_pad(board, pcbnew, fp, "1", "bat_sense")
        if ref == "BAT_C_ADC_100N":
            for pad in fp.Pads():
                if (pad.GetNetname() or "") in ("vbat_sense", "bat_sense", "VBAT_SW", "SYS_5V_SW"):
                    # keep sense side on bat_sense, gnd side gnd — set both carefully
                    pass
            # pad1 often sense, pad2 gnd — force
            pads = list(fp.Pads())
            if len(pads) >= 2:
                # whichever was on sense network
                for pad in pads:
                    n = pad.GetNetname() or ""
                    if n in ("gnd", "GND"):
                        continue
                    pad.SetNet(_ensure_net(board, pcbnew, "bat_sense"))
        if ref in ("TP_VBAT",) or (
            fp.HasFieldByName("atopile_address")
            and fp.GetFieldByName("atopile_address").GetText()
            in ("bringup.vbat_pad", "bringup.sys5_pad")
        ):
            fp.SetReference("TP_SYS_5V_SW")
            fp.SetValue("SYS_5V_SW")
            _set_pad(board, pcbnew, fp, "1", "SYS_5V_SW")
        # LED supply cap
        if ref == "LED_C_SUP_100N":
            for pad in fp.Pads():
                n = pad.GetNetname() or ""
                if n not in ("gnd", "GND", ""):
                    pad.SetNet(_ensure_net(board, pcbnew, "SYS_5V_SW"))

    # 4) remove obsolete USB_VBUS copper (was diode-OR / charge finger power)
    usb_dead = 0
    for t in list(board.GetTracks()):
        if (t.GetNetname() or "") in ("USB_VBUS", "vbus"):
            board.Delete(t)
            usb_dead += 1
    print(f"removed {usb_dead} obsolete USB_VBUS/vbus copper items")

    # 4b) clear <no net>
    nn = 0
    for t in list(board.GetTracks()):
        if not (t.GetNetname() or ""):
            board.Delete(t)
            nn += 1
    print(f"cleared {nn} no-net copper items")

    # 5) refill zones
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())

    board.Save(str(board_path))
    print(f"V4 power ECO saved (no auto-routes): {board_path}")
    print("HAND ROUTE: SYS_5V_IN→PMOS→SYS_5V_SW→LDO/C_IN; IMU VBUS; LED+; clear old VBAT copper")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

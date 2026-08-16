#!/usr/bin/env python3
"""Safely synchronize the tail-board power redesign from Atopile staging.

Atopile 0.12.5 is allowed to rewrite ``layouts/staging`` only.  In particular,
it can mirror the internal geometry of existing B.Cu footprints while still
reporting a successful build.  This script transfers logical pad nets by
``atopile_address`` + pad number, keeps every non-approved footprint pose,
performs the explicitly-approved footprint geometry upgrades, applies the
documented connector-relief poses, and parks new parts outside the
board for later manual placement/routing.

Run with KiCad's Python, for example on macOS:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 \
      pcb-tail/scripts/sync_power_architecture.py
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

try:
    import pcbnew
except ImportError as exc:  # pragma: no cover - depends on the KiCad runtime
    raise SystemExit(
        "pcbnew is unavailable; run this script with KiCad 9's bundled Python"
    ) from exc


# ===== 分区：常量/配置 =====
REPO = Path(__file__).resolve().parents[2]
DEFAULT_TARGET = REPO / "pcb-tail/layouts/default/default.kicad_pcb"
DEFAULT_STAGING = REPO / "pcb-tail/layouts/staging/default.atopile.kicad_pcb"
TAIL_FP_LIB = REPO / "pcb-tail/lib/footprints.pretty"
J4_SYNC_DESCRIPTION = (
    "JST ACH 1.2mm 2P SMT top-entry; project footprint/docs preview revision 1"
)
MOLEX_53261_DRAWING_URL = (
    "https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/"
    "en-us/salesdrawingpdf/532/53261/532610271_sd.pdf"
)
MOLEX_53261_FOOTPRINT = (
    "Molex_PicoBlade_53261-0471_1x04-1MP_P1.25mm_Horizontal"
)


@dataclass(frozen=True)
class Part:
    reference: str
    value: str
    datasheet: str = ""


# Stable references are part of the handoff contract.  Explicit values also
# compensate for Atopile 0.12.5 ignoring this legacy project's ``value =``
# assignments while still returning build success.
PARTS: dict[str, Part] = {
    "c_ahct": Part("C1", "100nF"),
    "c_led": Part("C2", "100nF"),
    "c_bat": Part("C3", "10uF 10V X5R/X7R"),
    "c_vin": Part("C4", "10uF 10V X5R/X7R"),
    "c_vin_damp": Part("C5", "10uF 10V X5R/X7R"),
    "c_vout": Part("C6", "22uF 10V X5R/X7R"),
    "c_vout2": Part("C7", "10uF 10V X5R/X7R"),
    "c_system_limit_in": Part("C8", "100nF 10V X7R"),
    "c_system_limit_out": Part("C9", "100nF 10V X7R"),
    "c_vbus_limit": Part("C10", "100nF 10V X7R"),
    "led_rgb": Part("D1", "WS2812B-2020"),
    "d_key_isolate": Part("D2", "1N4148W"),
    "usb": Part(
        "J1",
        "USB-C-16P-VERTICAL-H5.8-SHORT",
        "${KIPRJMOD}/../../../docs/usb-c-vertical-16p-short/"
        "Type-C-16PIN-vertical-H5.8-short-datasheet.pdf",
    ),
    "j_pwr": Part("J2", "Molex 53261-0471", MOLEX_53261_DRAWING_URL),
    "j_sig": Part("J3", "Molex 53261-0471", MOLEX_53261_DRAWING_URL),
    "j_bat": Part(
        "J4",
        "BM02B-ACHSS-GAN-ETF",
        "${KIPRJMOD}/../../../docs/battery-connector-jst-ach-2p/"
        "JST-ACH-official.pdf",
    ),
    "l_boost": Part("L1", "XFL4020-222MEC 2.2uH"),
    "led_stat": Part("LED1", "LTST-C190KGKT"),
    "r_cc1": Part("R1", "5.1k 1%"),
    "r_cc2": Part("R2", "5.1k 1%"),
    "r_led": Part("R3", "330R"),
    "r_key": Part("R4", "10k"),
    "r_led1": Part("R5", "200R"),
    "r_led23": Part("R6", "1k"),
    "r_vin_damp": Part("R7", "2R"),
    "r_system_ilim": Part("R8", "43.2k 1%"),
    "r_vbus_ilim": Part("R9", "59k 1%"),
    "sw_user": Part(
        "SW1",
        "B3U-1000P",
        "${KIPRJMOD}/../../../docs/tail-user-switch-b3u-1000p/"
        "Omron-B3U-A162-E1-07-official.pdf",
    ),
    "u_ahct": Part("U1", "SN74AHCT1G125DBVR"),
    "u_esd": Part("U2", "USBLC6-2SC6"),
    "u_pmic": Part(
        "U3",
        "IP5305T",
        "${KIPRJMOD}/../../../docs/power-architecture-rework/sources/"
        "IP5305T-V1.4.pdf",
    ),
    "u_system_limit": Part(
        "U4",
        "TPS2553DBVR",
        "${KIPRJMOD}/../../../docs/power-architecture-rework/sources/"
        "TPS2553-RevF.pdf",
    ),
    "u_vbus_limit": Part(
        "U5",
        "TPS2553DBVR",
        "${KIPRJMOD}/../../../docs/power-architecture-rework/sources/"
        "TPS2553-RevF.pdf",
    ),
}

ORIGINAL_ADDRESSES = frozenset(
    {
        "c_ahct",
        "c_led",
        "c_bat",
        "c_vin",
        "c_vin_damp",
        "c_vout",
        "c_vout2",
        "led_rgb",
        "usb",
        "j_pwr",
        "j_sig",
        "j_bat",
        "l_boost",
        "led_stat",
        "r_cc1",
        "r_cc2",
        "r_led",
        "r_key",
        "r_led1",
        "r_led23",
        "r_vin_damp",
        "sw_user",
        "u_ahct",
        "u_esd",
        "u_pmic",
    }
)

# First-add positions are deliberately outside the board outline (right edge is
# about X=14.87 mm).  They are a parking tray, not a layout decision.
PARK_MM: dict[str, tuple[float, float]] = {
    "u_system_limit": (21.0, -3.0),
    "c_system_limit_in": (25.0, -4.0),
    "c_system_limit_out": (25.0, -2.0),
    "r_system_ilim": (28.0, -3.0),
    "u_vbus_limit": (21.0, 4.0),
    "c_vbus_limit": (25.0, 3.0),
    "r_vbus_ilim": (28.0, 4.0),
    "d_key_isolate": (21.0, 10.0),
}

# Mechanical relief approved after checking the complete 53261 + 51021 mated
# envelopes, not merely the PCB-header courtyards.  C2 changes side; the
# low-current LED2/LED3 resistor and the battery connector move into nearby
# free space.  C3/U3/L1 deliberately stay fixed so the IP5305T BAT/SW
# high-current loop is not enlarged.
APPROVED_POSES_MM: dict[str, tuple[float, float, float, str]] = {
    "c_led": (2.000000, 1.000000, 0.0, "F.Cu"),
    "j_pwr": (-11.300000, -0.600000, -90.0, "B.Cu"),
    "j_sig": (6.300000, -5.800000, 180.0, "B.Cu"),
    "j_bat": (-2.794000, -7.000000, 90.0, "B.Cu"),
    "r_led23": (-10.500000, 6.200000, 0.0, "B.Cu"),
}

# These pads must remain truly NC.  Atopile may assign synthetic one-pad nets
# after a repeated build, which is semantically different from an NC contact.
FORCED_NC = {
    ("usb", "A8"),
    ("usb", "B8"),
    ("u_system_limit", "4"),
    ("u_vbus_limit", "4"),
}


# ===== 分区：私有成员 =====
class SyncError(RuntimeError):
    pass


def _field(fp: "pcbnew.FOOTPRINT", name: str) -> str:
    return fp.GetFieldByName(name).GetText() if fp.HasFieldByName(name) else ""


def _by_address(board: "pcbnew.BOARD") -> dict[str, "pcbnew.FOOTPRINT"]:
    result: dict[str, "pcbnew.FOOTPRINT"] = {}
    for fp in board.GetFootprints():
        address = _field(fp, "atopile_address")
        if not address:
            raise SyncError(f"{fp.GetReference()} has no atopile_address")
        if address in result:
            raise SyncError(f"duplicate atopile_address: {address}")
        result[address] = fp
    return result


def _pose(fp: "pcbnew.FOOTPRINT") -> tuple[int, int, float, int]:
    pos = fp.GetPosition()
    return (pos.x, pos.y, fp.GetOrientationDegrees(), fp.GetLayer())


def _pad_net_map(fp: "pcbnew.FOOTPRINT") -> dict[str, str | None]:
    nets: dict[str, set[str | None]] = {}
    for pad in fp.Pads():
        nets.setdefault(pad.GetNumber(), set()).add(pad.GetNetname() or None)
    collapsed: dict[str, str | None] = {}
    for number, names in nets.items():
        if len(names) != 1:
            raise SyncError(
                f"{_field(fp, 'atopile_address')}.{number} has conflicting nets: {names}"
            )
        collapsed[number] = next(iter(names))
    return collapsed


def _ensure_net(board: "pcbnew.BOARD", name: str) -> "pcbnew.NETINFO_ITEM":
    net = board.FindNet(name)
    if net is None:
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
    return net


def _find_stock_capacitor_library() -> Path:
    candidates = []
    if path := os.environ.get("KICAD9_FOOTPRINT_DIR"):
        candidates.append(Path(path) / "Capacitor_SMD.pretty")
    candidates.extend(
        [
            Path(
                "/Applications/KiCad/KiCad.app/Contents/SharedSupport/"
                "footprints/Capacitor_SMD.pretty"
            ),
            Path("/usr/share/kicad/footprints/Capacitor_SMD.pretty"),
        ]
    )
    for candidate in candidates:
        if (candidate / "C_1206_3216Metric.kicad_mod").is_file():
            return candidate
    raise SyncError("KiCad 9 Capacitor_SMD.pretty library was not found")


def _find_stock_molex_library() -> Path:
    candidates = []
    if path := os.environ.get("KICAD9_FOOTPRINT_DIR"):
        candidates.append(Path(path) / "Connector_Molex.pretty")
    candidates.extend(
        [
            Path(
                "/Applications/KiCad/KiCad.app/Contents/SharedSupport/"
                "footprints/Connector_Molex.pretty"
            ),
            Path("/usr/share/kicad/footprints/Connector_Molex.pretty"),
        ]
    )
    for candidate in candidates:
        if (candidate / f"{MOLEX_53261_FOOTPRINT}.kicad_mod").is_file():
            return candidate
    raise SyncError("KiCad 9 Connector_Molex.pretty library was not found")


def _copy_fields(source: "pcbnew.FOOTPRINT") -> dict[str, str]:
    return {item.GetName(): item.GetText() for item in source.GetFields()}


def _replace_from_library(
    board: "pcbnew.BOARD",
    old: "pcbnew.FOOTPRINT",
    library: Path,
    item_name: str,
    library_nickname: str,
) -> "pcbnew.FOOTPRINT":
    position = old.GetPosition()
    orientation = old.GetOrientationDegrees()
    layer = old.GetLayer()
    fields = _copy_fields(old)

    replacement = pcbnew.FootprintLoad(str(library), item_name)
    if replacement is None:
        raise SyncError(f"could not load footprint {library_nickname}:{item_name}")

    # KiCad 9.0.6's generic Remove() leaves other SWIG footprint handles in a
    # corrupted state.  RemoveNative() keeps the board container iterable so
    # multiple audited replacements can be performed in one synchronization.
    board.RemoveNative(old)
    board.Add(replacement)
    replacement.SetPosition(position)
    if layer == pcbnew.B_Cu:
        replacement.Flip(position, pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
    elif layer != pcbnew.F_Cu:
        raise SyncError(f"unsupported footprint layer {layer} for {fields['Reference']}")
    replacement.SetOrientationDegrees(orientation)
    replacement.SetFPID(pcbnew.LIB_ID(library_nickname, item_name))
    replacement.SetFields(fields)
    return replacement


def _u3_geometry_is_current(fp: "pcbnew.FOOTPRINT") -> bool:
    pads = list(fp.Pads())
    epads = [pad for pad in pads if pad.GetNumber() == "9"]
    if len(epads) != 1 or epads[0].GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
        return False
    side = [pad for pad in pads if pad.GetNumber() == "1"]
    if len(side) != 1:
        return False
    size = side[0].GetSize()
    return (
        fp.GetFPIDAsString() == "SmartPaddleTail:IP5305T_HSOP-8-1EP"
        and size.x == pcbnew.FromMM(1.6)
        and size.y == pcbnew.FromMM(0.6)
    )


def _c6_geometry_is_current(fp: "pcbnew.FOOTPRINT") -> bool:
    pads = {pad.GetNumber(): pad for pad in fp.Pads()}
    if set(pads) != {"1", "2"}:
        return False
    # Compare footprint-relative nominal geometry through absolute pad spacing;
    # orientation may be changed later by the user without invalidating it.
    p1 = pads["1"].GetPosition()
    p2 = pads["2"].GetPosition()
    dx = p1.x - p2.x
    dy = p1.y - p2.y
    spacing_squared = dx * dx + dy * dy
    size = pads["1"].GetSize()
    return (
        fp.GetFPIDAsString() == "Capacitor_SMD:C_1206_3216Metric"
        and spacing_squared == pcbnew.FromMM(2.95) ** 2
        and sorted((size.x, size.y))
        == sorted((pcbnew.FromMM(1.15), pcbnew.FromMM(1.8)))
    )


def _picoblade_53261_geometry_is_current(fp: "pcbnew.FOOTPRINT") -> bool:
    pads: dict[str, list["pcbnew.PAD"]] = {}
    for pad in fp.Pads():
        pads.setdefault(pad.GetNumber(), []).append(pad)
    if set(pads) != {"1", "2", "3", "4", "MP"}:
        return False
    if any(len(pads[number]) != 1 for number in ("1", "2", "3", "4")):
        return False
    if len(pads["MP"]) != 2:
        return False
    signal_size = pads["1"][0].GetSize()
    mount_size = pads["MP"][0].GetSize()
    return (
        fp.GetFPIDAsString()
        == f"Connector_Molex:{MOLEX_53261_FOOTPRINT}"
        and sorted((signal_size.x, signal_size.y))
        == sorted((pcbnew.FromMM(0.8), pcbnew.FromMM(1.6)))
        and sorted((mount_size.x, mount_size.y))
        == sorted((pcbnew.FromMM(2.1), pcbnew.FromMM(3.0)))
    )


def _set_pose_mm(
    board: "pcbnew.BOARD",
    fp: "pcbnew.FOOTPRINT",
    pose: tuple[float, float, float, str],
) -> None:
    x, y, orientation, layer_name = pose
    target_layer = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu}[layer_name]
    if fp.GetLayer() != target_layer:
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
    fp.SetPosition(pcbnew.VECTOR2I_MM(x, y))
    fp.SetOrientationDegrees(orientation)


def _set_part_fields(fp: "pcbnew.FOOTPRINT", address: str) -> None:
    part = PARTS[address]
    fp.SetReference(part.reference)
    fp.SetValue(part.value)
    if fp.HasFieldByName("Datasheet"):
        fp.GetFieldByName("Datasheet").SetText(part.datasheet)
    if address == "j_bat" and fp.HasFieldByName("Description"):
        fp.GetFieldByName("Description").SetText(J4_SYNC_DESCRIPTION)
        fp.Reference().SetVisible(False)
    if address in {"j_pwr", "j_sig"}:
        fp.Reference().SetVisible(False)
    if fp.HasFieldByName("atopile_address"):
        address_field = fp.GetFieldByName("atopile_address")
        address_field.SetLayer(pcbnew.User_9)
        address_field.SetVisible(False)
    if address == "j_bat":
        fp.SetFPID(
            pcbnew.LIB_ID(
                "SmartPaddleTail",
                "JST_ACH_BM02B-ACHSS-GAN-ETF_1x02-1MP_P1.20mm_Vertical",
            )
        )


def _validate_staging(
    stage: "pcbnew.BOARD", stage_parts: dict[str, "pcbnew.FOOTPRINT"]
) -> dict[str, dict[str, str | None]]:
    if set(stage_parts) != set(PARTS):
        raise SyncError(
            "staging address set differs from the 33-part contract: "
            f"missing={sorted(set(PARTS) - set(stage_parts))}, "
            f"extra={sorted(set(stage_parts) - set(PARTS))}"
        )
    if list(stage.GetTracks()) or stage.GetAreaCount():
        raise SyncError("staging board must not contain routing, vias, or zones")

    # Atopile 0.12.5 can keep stale embedded drawing primitives/descriptions
    # while changing a footprint library identifier.  Require the intended
    # logical FPID here, but deliberately import and audit the physical 53261
    # geometry from KiCad's stock library in the target board below.
    expected_connector_fpid = f"Connector_Molex:{MOLEX_53261_FOOTPRINT}"
    for address in ("j_pwr", "j_sig"):
        if stage_parts[address].GetFPIDAsString() != expected_connector_fpid:
            raise SyncError(
                f"staging {address} footprint is "
                f"{stage_parts[address].GetFPIDAsString()!r}, expected "
                f"{expected_connector_fpid!r}"
            )

    maps = {address: _pad_net_map(fp) for address, fp in stage_parts.items()}
    required = {
        ("u_system_limit", "5"): "system_ilim",
        ("r_system_ilim", "1"): "system_ilim",
        ("u_vbus_limit", "5"): "vbus_ilim",
        ("r_vbus_ilim", "1"): "vbus_ilim",
        ("u_pmic", "1"): "vbus_limited",
        ("u_pmic", "8"): "vout_5v_raw",
        ("j_pwr", "1"): "vout_5v",
    }
    for (address, pad), expected in required.items():
        if maps[address].get(pad) != expected:
            raise SyncError(
                f"staging build is incomplete: {address}.{pad}="
                f"{maps[address].get(pad)!r}, expected {expected!r}; "
                "run `ato build --build default` again and re-audit"
            )
    return maps


# ===== 分区：公开 API =====
def synchronize(target_path: Path, staging_path: Path) -> None:
    if not target_path.is_file() or not staging_path.is_file():
        raise SyncError("target or staging PCB is missing")

    # KiCad 9's SWIG layer can segfault when a board loaded from beside its
    # live .kicad_pro is saved under another name.  Work on a detached byte-for-
    # byte copy and replace the target only after independent reload checks.
    input_handle = tempfile.NamedTemporaryFile(
        prefix="smartpaddle-tail-input-", suffix=".kicad_pcb", delete=False
    )
    detached_input = Path(input_handle.name)
    input_handle.close()
    shutil.copy2(target_path, detached_input)
    target = pcbnew.LoadBoard(str(detached_input))
    stage = pcbnew.LoadBoard(str(staging_path))
    target_parts = _by_address(target)
    stage_parts = _by_address(stage)
    logical_nets = _validate_staging(stage, stage_parts)

    if not ORIGINAL_ADDRESSES.issubset(target_parts):
        raise SyncError(
            f"target is missing original footprints: "
            f"{sorted(ORIGINAL_ADDRESSES - set(target_parts))}"
        )
    if list(target.GetTracks()) or target.GetAreaCount():
        raise SyncError(
            "target must remain route-free during this phase; remove tracks/vias/zones first"
        )

    original_poses = {address: _pose(target_parts[address]) for address in ORIGINAL_ADDRESSES}

    u3 = target_parts["u_pmic"]
    if not _u3_geometry_is_current(u3):
        target_parts["u_pmic"] = _replace_from_library(
            target,
            u3,
            TAIL_FP_LIB,
            "IP5305T_HSOP-8-1EP",
            "SmartPaddleTail",
        )

    c6 = target_parts["c_vout"]
    if not _c6_geometry_is_current(c6):
        target_parts["c_vout"] = _replace_from_library(
            target,
            c6,
            _find_stock_capacitor_library(),
            "C_1206_3216Metric",
            "Capacitor_SMD",
        )

    molex_library = _find_stock_molex_library()
    for address in ("j_pwr", "j_sig"):
        # Removing one footprint invalidates other SWIG object handles from the
        # same board; refresh the address map before inspecting each connector.
        target_parts = _by_address(target)
        connector = target_parts[address]
        if not _picoblade_53261_geometry_is_current(connector):
            target_parts[address] = _replace_from_library(
                target,
                connector,
                molex_library,
                MOLEX_53261_FOOTPRINT,
                "Connector_Molex",
            )

    target_parts = _by_address(target)

    j4 = target_parts["j_bat"]
    if _field(j4, "Description") != J4_SYNC_DESCRIPTION:
        target_parts["j_bat"] = _replace_from_library(
            target,
            j4,
            TAIL_FP_LIB,
            "JST_ACH_BM02B-ACHSS-GAN-ETF_1x02-1MP_P1.20mm_Vertical",
            "SmartPaddleTail",
        )

    target_parts = _by_address(target)

    for address in sorted(set(PARTS) - set(target_parts)):
        if address not in PARK_MM:
            raise SyncError(f"no first-add parking coordinate for {address}")
        clone = stage_parts[address].Duplicate()
        target.Add(clone)
        clone.SetPosition(pcbnew.VECTOR2I_MM(*PARK_MM[address]))
        clone.SetOrientationDegrees(0)
        target_parts[address] = clone

    target_parts = _by_address(target)

    for address, pose in APPROVED_POSES_MM.items():
        _set_pose_mm(target, target_parts[address], pose)

    if set(target_parts) != set(PARTS):
        raise SyncError(
            f"target address set mismatch after add: "
            f"missing={sorted(set(PARTS) - set(target_parts))}, "
            f"extra={sorted(set(target_parts) - set(PARTS))}"
        )

    for address, fp in target_parts.items():
        _set_part_fields(fp, address)
        stage_map = logical_nets[address]
        target_pad_numbers = {pad.GetNumber() for pad in fp.Pads()}
        if target_pad_numbers != set(stage_map):
            raise SyncError(
                f"pad-number mismatch for {address}: target={sorted(target_pad_numbers)}, "
                f"staging={sorted(stage_map)}"
            )
        for pad in fp.Pads():
            number = pad.GetNumber()
            net_name = None if (address, number) in FORCED_NC else stage_map[number]
            if net_name:
                pad.SetNet(_ensure_net(target, net_name))
            else:
                pad.SetNetCode(0)

    target.SanitizeNetcodes()

    for address, before in original_poses.items():
        if address in APPROVED_POSES_MM:
            continue
        after = _pose(target_parts[address])
        if after != before:
            raise SyncError(f"existing footprint pose changed: {address}: {before} -> {after}")
    for address, pose in APPROVED_POSES_MM.items():
        x, y, orientation, layer_name = pose
        expected = (
            pcbnew.FromMM(x),
            pcbnew.FromMM(y),
            orientation,
            {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu}[layer_name],
        )
        actual = _pose(target_parts[address])
        if actual != expected:
            raise SyncError(f"approved footprint pose mismatch: {address}: {actual} != {expected}")

    references = [fp.GetReference() for fp in target.GetFootprints()]
    if len(references) != len(set(references)):
        raise SyncError("duplicate references after synchronization")
    if len(references) != 33:
        raise SyncError(f"expected 33 footprints, found {len(references)}")
    if list(target.GetTracks()) or target.GetAreaCount():
        raise SyncError("synchronization unexpectedly created routing or zones")

    handle = tempfile.NamedTemporaryFile(
        prefix="smartpaddle-tail-sync-", suffix=".kicad_pcb", delete=False
    )
    temporary = Path(handle.name)
    handle.close()
    temporary.unlink()
    pcbnew.SaveBoard(str(temporary), target)
    reloaded = pcbnew.LoadBoard(str(temporary))
    if len(list(reloaded.GetFootprints())) != 33 or list(reloaded.GetTracks()):
        temporary.unlink(missing_ok=True)
        raise SyncError("saved-board verification failed")
    for suffix in (".kicad_pro", ".kicad_prl"):
        temporary.with_suffix(suffix).unlink(missing_ok=True)
    swap = target_path.with_name(
        f".{target_path.stem}.{uuid.uuid4().hex}.sync.swap.kicad_pcb"
    )
    shutil.copy2(temporary, swap)
    temporary.unlink()
    os.replace(swap, target_path)
    detached_input.unlink(missing_ok=True)
    for suffix in (".kicad_pro", ".kicad_prl"):
        detached_input.with_suffix(suffix).unlink(missing_ok=True)

    print("Tail power-architecture synchronization PASS")
    print(f"  target: {target_path}")
    print("  all non-approved existing footprint poses preserved")
    print("  U3/C6 geometry and J2/J3 Molex 53261 right-angle footprints applied")
    print("  C2/J2/J3/J4/R6 use the approved complete-connector relief poses")
    print("  C3/U3/L1 remain fixed to preserve the IP5305T high-current loop")
    print("  8 added parts retained at their existing poses (parked only on first add)")
    print("  33 footprints; 0 tracks/vias; 0 zones")
    print("  J1 A8/B8 and TPS2553 /FAULT pads are true NC")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--staging", type=Path, default=DEFAULT_STAGING)
    args = parser.parse_args()
    try:
        synchronize(args.target.resolve(), args.staging.resolve())
    except SyncError as exc:
        print(f"SYNC FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

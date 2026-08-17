#!/usr/bin/env python3
"""Safely merge one routed functional island into the tail-board workbench.

This tool is intentionally narrow:

* the destination must identify itself as the non-fabrication functional-island
  workbench and contain the exact eight expected PCB_GROUP objects;
* the route source must contain exactly the footprints assigned to the selected
  island and may use only that island's explicitly allowed internal nets;
* footprints, drawings, Edge.Cuts, zones, and pre-existing copper are immutable;
* copied tracks/vias are attached to the selected PCB_GROUP; and
* saving is atomic and targets a new file unless ``--in-place`` is explicit.

It must be run with KiCad's bundled Python/pcbnew module.  It never reads from
or writes to the production ``layouts/default`` board.
"""

from __future__ import annotations

import argparse
import gc
import os
import uuid
from pathlib import Path
from typing import Iterable

try:
    import pcbnew
except ImportError as exc:  # pragma: no cover - KiCad runtime only
    raise SystemExit("run with KiCad 9's bundled Python") from exc

from build_functional_group_workbench import ISLANDS


REPO = Path(__file__).resolve().parents[2]
DEFAULT_WORKBENCH = (
    REPO / "pcb-tail/layouts/functional-groups/functional-groups.kicad_pcb"
)


# Cross-island nets are deliberately excluded.  A shared net such as GND is
# legal here only for copper connecting pads that exist in the source island's
# reduced board; exact source-footprint inventory is checked before copying.
ALLOWED_INTERNAL_NETS: dict[str, frozenset[str]] = {
    "G1_USB_C_CC_ESD": frozenset(
        {"GND", "cc1", "cc2", "usb_dp_conn", "usb_dn_conn", "vbus"}
    ),
    "G2_USB_INPUT_LIMIT": frozenset({"GND", "vbus", "vbus_ilim"}),
    "G3_IP5305_POWER_CORE": frozenset(
        {
            "GND",
            "bat_p",
            "pmic_led23",
            "sw_node",
            "vbus_limited",
            "vin_damp_mid",
            "vout_5v_raw",
        }
    ),
    "G4_SYSTEM_5V_LIMIT": frozenset(
        {"GND", "system_ilim", "vout_5v", "vout_5v_raw"}
    ),
    "G5_PMIC_KEY_STATUS": frozenset(
        {"GND", "user_btn", "pmic_key_isolated", "led_stat_a"}
    ),
    "G6_RGB_BUFFER_PIXEL": frozenset(
        {"GND", "led_ahct_y", "led_din", "v5_sw_return"}
    ),
    # J2 and J4 deliberately form the battery-through interface inside G7.
    "G7_POWER_BAT_INTERFACES": frozenset({"GND", "bat_p"}),
    # The single J3 footprint has no honest internal net.
    "G8_SIGNAL_INTERFACE": frozenset(),
}

ALIASES = {name.split("_", 1)[0]: name for name in ISLANDS}


class MergeError(RuntimeError):
    pass


def _uuid(item: object) -> str:
    return item.m_Uuid.AsString()


def _xy(vector: "pcbnew.VECTOR2I") -> tuple[int, int]:
    return (int(vector.x), int(vector.y))


def _footprint_fingerprint(board: "pcbnew.BOARD") -> tuple[tuple[object, ...], ...]:
    return tuple(
        sorted(
            (
                fp.GetReference(),
                _uuid(fp),
                *_xy(fp.GetPosition()),
                round(float(fp.GetOrientationDegrees()), 9),
                int(fp.GetLayer()),
                fp.GetFPIDAsString(),
            )
            for fp in board.GetFootprints()
        )
    )


def _shape_fingerprint(item: object) -> tuple[object, ...]:
    """Fingerprint immutable board drawings, including exact Edge.Cuts."""
    result: list[object] = [item.GetClass(), _uuid(item), int(item.GetLayer())]
    for accessor in (
        "GetShape",
        "GetStart",
        "GetEnd",
        "GetCenter",
        "GetArcMid",
        "GetBezierC1",
        "GetBezierC2",
        "GetWidth",
        "GetText",
        "GetPosition",
    ):
        if not hasattr(item, accessor):
            continue
        try:
            value = getattr(item, accessor)()
        except (AttributeError, TypeError, RuntimeError):
            continue
        if hasattr(value, "x") and hasattr(value, "y"):
            value = _xy(value)
        elif hasattr(value, "AsDegrees"):
            value = round(float(value.AsDegrees()), 9)
        elif not isinstance(value, (str, int, float, bool, tuple)):
            value = str(value)
        result.extend((accessor, value))
    return tuple(result)


def _drawing_fingerprint(board: "pcbnew.BOARD") -> tuple[tuple[object, ...], ...]:
    return tuple(sorted(_shape_fingerprint(item) for item in board.GetDrawings()))


def _zone_fingerprint(board: "pcbnew.BOARD") -> tuple[tuple[object, ...], ...]:
    # Workbench is expected to have no zones.  UUID/net/layers still make this
    # safe if a later workbench revision deliberately adds documentation zones.
    zones: list[tuple[object, ...]] = []
    for index in range(board.GetAreaCount()):
        zone = board.GetArea(index)
        layers = tuple(sorted(int(layer) for layer in zone.GetLayerSet().Seq()))
        zones.append((_uuid(zone), zone.GetNetname(), layers))
    return tuple(sorted(zones))


def _route_fingerprint(item: object) -> tuple[object, ...]:
    common: list[object] = [item.GetClass(), _uuid(item), item.GetNetname()]
    if isinstance(item, pcbnew.PCB_VIA):
        common.extend(
            (
                int(item.GetFrontWidth()),
                *_xy(item.GetPosition()),
                int(item.GetDrill()),
                int(item.GetViaType()),
                int(item.TopLayer()),
                int(item.BottomLayer()),
            )
        )
    elif isinstance(item, pcbnew.PCB_TRACK):
        common.extend(
            (
                int(item.GetWidth()),
                *_xy(item.GetStart()),
                *_xy(item.GetEnd()),
                int(item.GetLayer()),
            )
        )
    else:  # pragma: no cover - caller rejects unsupported classes first
        common.append(str(item))
    return tuple(common)


def _copper_fingerprint(items: Iterable[object]) -> tuple[tuple[object, ...], ...]:
    return tuple(sorted(_route_fingerprint(item) for item in items))


def _group_map(board: "pcbnew.BOARD") -> dict[str, object]:
    groups = {group.GetName(): group for group in board.Groups()}
    if set(groups) != set(ISLANDS):
        raise MergeError(
            "destination PCB_GROUP inventory mismatch: "
            f"expected={sorted(ISLANDS)}, actual={sorted(groups)}"
        )
    seen_refs: list[str] = []
    for name, group in groups.items():
        actual_refs = sorted(
            item.GetReference()
            for item in group.GetItems()
            if isinstance(item, pcbnew.FOOTPRINT)
        )
        expected_refs = sorted(ISLANDS[name].refs)
        if actual_refs != expected_refs:
            raise MergeError(
                f"destination footprint membership mismatch in {name}: "
                f"expected={expected_refs}, actual={actual_refs}"
            )
        seen_refs.extend(actual_refs)
    if len(seen_refs) != 33 or len(set(seen_refs)) != 33:
        raise MergeError("destination group membership must cover 33 refs exactly once")
    return groups


def _resolve_group(value: str) -> str:
    value = value.upper()
    if value in ALIASES:
        return ALIASES[value]
    for name in ISLANDS:
        if value == name.upper():
            return name
    raise MergeError(f"unknown group {value!r}; choose G1 through G8")


def _assert_safe_workbench_path(path: Path, role: str) -> None:
    resolved = path.resolve()
    default_dir = (REPO / "pcb-tail/layouts/default").resolve()
    if default_dir == resolved.parent or default_dir in resolved.parents:
        raise MergeError(f"refusing {role} under production layouts/default: {resolved}")


def _validate_workbench(board: "pcbnew.BOARD", path: Path) -> dict[str, object]:
    _assert_safe_workbench_path(path, "workbench")
    title = board.GetTitleBlock().GetTitle().lower()
    if "functional-island workbench" not in title or "not for fab" not in title:
        raise MergeError("destination does not identify itself as the NOT FOR FAB workbench")
    if len(list(board.GetFootprints())) != 33:
        raise MergeError("destination must contain exactly 33 footprints")
    return _group_map(board)


def _extract_source(
    source: "pcbnew.BOARD",
    group_name: str,
) -> tuple[dict[str, tuple[object, ...]], list[dict[str, object]]]:
    expected_refs = set(ISLANDS[group_name].refs)
    source_refs = {fp.GetReference(): fp for fp in source.GetFootprints()}
    if set(source_refs) != expected_refs:
        raise MergeError(
            f"source footprint inventory for {group_name} is not exact: "
            f"expected={sorted(expected_refs)}, actual={sorted(source_refs)}"
        )
    source_poses = {
        ref: (
            *_xy(src.GetPosition()),
            round(float(src.GetOrientationDegrees()), 9),
            int(src.GetLayer()),
        )
        for ref, src in source_refs.items()
    }

    source_tracks = list(source.GetTracks())
    if source.GetAreaCount() != 0:
        raise MergeError("source zones are unsupported; merge explicit tracks/vias only")
    if not source_tracks:
        raise MergeError(f"source has no routes for {group_name}")
    allowed = ALLOWED_INTERNAL_NETS[group_name]
    used = {item.GetNetname() for item in source_tracks}
    if "" in used or used != allowed:
        raise MergeError(
            f"source route-net inventory is incomplete or cross-island for {group_name}: "
            f"missing={sorted(allowed - used)}, extra={sorted(used - allowed)}"
        )
    for item in source_tracks:
        if not isinstance(item, (pcbnew.PCB_TRACK, pcbnew.PCB_VIA)):
            raise MergeError(f"unsupported routed object: {item.GetClass()}")
        if item.GetClass() not in {"PCB_TRACK", "PCB_VIA"}:
            raise MergeError(f"unsupported routed object class: {item.GetClass()}")
    route_specs: list[dict[str, object]] = []
    for item in source_tracks:
        if isinstance(item, pcbnew.PCB_VIA):
            route_specs.append(
                {
                    "kind": "via",
                    "net": item.GetNetname(),
                    "position": _xy(item.GetPosition()),
                    "width": int(item.GetFrontWidth()),
                    "drill": int(item.GetDrill()),
                    "via_type": int(item.GetViaType()),
                    "top_layer": int(item.TopLayer()),
                    "bottom_layer": int(item.BottomLayer()),
                }
            )
        else:
            route_specs.append(
                {
                    "kind": "track",
                    "net": item.GetNetname(),
                    "start": _xy(item.GetStart()),
                    "end": _xy(item.GetEnd()),
                    "width": int(item.GetWidth()),
                    "layer": int(item.GetLayer()),
                }
            )
    return source_poses, route_specs


def _validate_source_alignment(
    destination: "pcbnew.BOARD",
    source_poses: dict[str, tuple[object, ...]],
) -> None:
    destination_refs = {fp.GetReference(): fp for fp in destination.GetFootprints()}
    for ref, src_pose in sorted(source_poses.items()):
        dst = destination_refs[ref]
        dst_pose = (
            *_xy(dst.GetPosition()),
            round(float(dst.GetOrientationDegrees()), 9),
            int(dst.GetLayer()),
        )
        if src_pose != dst_pose:
            raise MergeError(
                f"source route geometry is stale for {ref}: source={src_pose}, "
                f"workbench={dst_pose}"
            )


def _clone_route(
    destination: "pcbnew.BOARD",
    spec: dict[str, object],
) -> object:
    try:
        destination_net = destination.GetNetsByName()[str(spec["net"])]
    except IndexError as exc:
        raise MergeError(f"destination lacks net {spec['net']!r}") from exc

    if spec["kind"] == "via":
        clone = pcbnew.PCB_VIA(destination)
        clone.SetPosition(pcbnew.VECTOR2I(*spec["position"]))
        clone.SetWidth(int(spec["width"]))
        clone.SetDrill(int(spec["drill"]))
        clone.SetViaType(int(spec["via_type"]))
        clone.SetLayerPair(int(spec["top_layer"]), int(spec["bottom_layer"]))
    elif spec["kind"] == "track":
        clone = pcbnew.PCB_TRACK(destination)
        clone.SetStart(pcbnew.VECTOR2I(*spec["start"]))
        clone.SetEnd(pcbnew.VECTOR2I(*spec["end"]))
        clone.SetWidth(int(spec["width"]))
        clone.SetLayer(int(spec["layer"]))
    else:  # pragma: no cover - validated before cloning
        raise MergeError(f"unsupported routed object kind: {spec['kind']}")
    clone.SetNet(destination_net)
    return clone


def _atomic_save(path: Path, board: "pcbnew.BOARD", force: bool) -> None:
    if path.exists() and not force:
        raise MergeError(f"output already exists (use --force): {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    temporary = path.with_name(f".{path.stem}.route-merge-{token}.tmp.kicad_pcb")
    sidecars = [temporary.with_suffix(".kicad_pro"), temporary.with_suffix(".kicad_prl")]
    try:
        pcbnew.SaveBoard(str(temporary), board)
        if not temporary.is_file():
            raise MergeError("KiCad did not create the temporary output")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
        for sidecar in sidecars:
            sidecar.unlink(missing_ok=True)


def merge(
    workbench_path: Path,
    route_path: Path,
    group_name: str,
    output_path: Path,
    *,
    force: bool = False,
    in_place: bool = False,
) -> None:
    workbench_path = workbench_path.resolve()
    route_path = route_path.resolve()
    output_path = output_path.resolve()
    _assert_safe_workbench_path(output_path, "output")
    if output_path == workbench_path and not in_place:
        raise MergeError("refusing to overwrite workbench without --in-place")
    if output_path != workbench_path and in_place:
        raise MergeError("--in-place requires output path to equal workbench path")
    if route_path == workbench_path or route_path == output_path:
        raise MergeError("route source must be a distinct file")

    # KiCad 9's macOS pcbnew bindings can crash in SaveBoard when another
    # BOARD instance remains live.  Extract the reduced route board into plain
    # Python values, release it, and only then load the destination board.
    source = pcbnew.LoadBoard(str(route_path))
    if source is None:
        raise MergeError("unable to load route board")
    source_poses, route_specs = _extract_source(source, group_name)
    del source
    gc.collect()

    destination = pcbnew.LoadBoard(str(workbench_path))
    if destination is None:
        raise MergeError("unable to load workbench")
    groups = _validate_workbench(destination, workbench_path)
    _validate_source_alignment(destination, source_poses)
    group = groups[group_name]

    existing_group_routes = [
        item
        for item in group.GetItems()
        if isinstance(item, (pcbnew.PCB_TRACK, pcbnew.PCB_VIA))
    ]
    if existing_group_routes:
        raise MergeError(
            f"{group_name} already owns {len(existing_group_routes)} routed objects; "
            "start from a clean workbench or add replacement support deliberately"
        )

    before_footprints = _footprint_fingerprint(destination)
    before_drawings = _drawing_fingerprint(destination)
    before_zones = _zone_fingerprint(destination)
    before_copper = _copper_fingerprint(destination.GetTracks())
    before_copper_count = len(list(destination.GetTracks()))

    added: list[object] = []
    for route_spec in route_specs:
        clone = _clone_route(destination, route_spec)
        destination.Add(clone)
        group.AddItem(clone)
        added.append(clone)

    if _footprint_fingerprint(destination) != before_footprints:
        raise MergeError("internal error: footprint inventory/pose changed during merge")
    if _drawing_fingerprint(destination) != before_drawings:
        raise MergeError("internal error: drawings or Edge.Cuts changed during merge")
    if _zone_fingerprint(destination) != before_zones:
        raise MergeError("internal error: zones changed during merge")
    if not set(before_copper) <= set(_copper_fingerprint(destination.GetTracks())):
        raise MergeError("internal error: pre-existing copper changed during merge")
    if len(list(destination.GetTracks())) != before_copper_count + len(route_specs):
        raise MergeError("internal error: copied copper count mismatch")

    _atomic_save(output_path, destination, force=force or in_place)

    # Release the saved BOARD before reloading it for the same pcbnew reason.
    del added, group, groups, destination
    gc.collect()
    verify = pcbnew.LoadBoard(str(output_path))
    if verify is None:
        raise MergeError("unable to reload merged output")
    verify_groups = _validate_workbench(verify, output_path)
    if _footprint_fingerprint(verify) != before_footprints:
        raise MergeError("saved output changed footprint inventory/pose")
    if _drawing_fingerprint(verify) != before_drawings:
        raise MergeError("saved output changed drawings or Edge.Cuts")
    if _zone_fingerprint(verify) != before_zones:
        raise MergeError("saved output changed zones")
    if not set(before_copper) <= set(_copper_fingerprint(verify.GetTracks())):
        raise MergeError("saved output changed pre-existing copper")
    if len(list(verify.GetTracks())) != before_copper_count + len(route_specs):
        raise MergeError("saved output copper count mismatch")
    verify_group_routes = [
        item
        for item in verify_groups[group_name].GetItems()
        if isinstance(item, (pcbnew.PCB_TRACK, pcbnew.PCB_VIA))
    ]
    if len(verify_group_routes) != len(route_specs):
        raise MergeError(
            "saved PCB_GROUP membership mismatch: "
            f"expected {len(route_specs)}, got {len(verify_group_routes)}"
        )

    counts: dict[str, int] = {}
    for spec in route_specs:
        name = str(spec["net"])
        counts[name] = counts.get(name, 0) + 1
    print(f"ROUTE MERGE PASS: {group_name}")
    print(f"  source: {route_path}")
    print(f"  output: {output_path}")
    print(f"  copied: {len(route_specs)} tracks/vias; nets={counts}")
    print("  invariant: 33 footprints, poses, drawings/Edge.Cuts, zones, old copper")
    print(f"  PCB_GROUP membership: {len(verify_group_routes)} routed objects")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("group", help="G1..G8 or the full PCB_GROUP name")
    parser.add_argument("route_board", type=Path, help="validated group-only routed PCB")
    parser.add_argument("--workbench", type=Path, default=DEFAULT_WORKBENCH)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--force", action="store_true", help="replace an existing non-input output file"
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="explicitly allow output == workbench (still rejects layouts/default)",
    )
    args = parser.parse_args()
    group_name = _resolve_group(args.group)
    merge(
        args.workbench,
        args.route_board,
        group_name,
        args.output,
        force=args.force,
        in_place=args.in_place,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MergeError as exc:
        print(f"ROUTE MERGE FAIL: {exc}")
        raise SystemExit(1)

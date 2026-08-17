#!/usr/bin/env python3
"""Read-only electrical audit for the tail functional-island workbench.

The workbench intentionally keeps the production Edge.Cuts while parking all
functional islands outside that outline.  Consequently this audit never treats
outside-board copper as an error.  Instead it verifies the invariants that make
the exploded workbench useful and safe to merge later:

* all 33 footprints belong to exactly one of the eight expected PCB_GROUPs;
* every track/via belongs to exactly one matching group and no zones exist;
* a group uses only nets that are internal to its own footprint inventory;
* every internal net connects every pad of that net inside the group; and
* no via annulus overlaps any pad copper on any shared copper layer.

Run this script with KiCad's bundled Python/pcbnew module.  It only reads the
board and never calls SaveBoard.  With no ``--group`` it is a full gate.  The
optional group selector is deliberately labelled PARTIAL and exists only for
incremental routing diagnostics; it is not a fabrication/release gate.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Iterable

try:
    import pcbnew
except ImportError as exc:  # pragma: no cover - KiCad runtime only
    raise SystemExit("run with KiCad 9's bundled Python") from exc

from build_functional_group_workbench import ISLANDS
from merge_functional_group_routes import ALLOWED_INTERNAL_NETS


REPO = Path(__file__).resolve().parents[2]
DEFAULT_BOARD = (
    REPO / "pcb-tail/layouts/functional-groups/functional-groups.kicad_pcb"
)
ALIASES = {name.split("_", 1)[0]: name for name in ISLANDS}


class AuditError(RuntimeError):
    pass


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def _uuid(item: object) -> str:
    return item.m_Uuid.AsString()


def _is_route(item: object) -> bool:
    return isinstance(item, (pcbnew.PCB_TRACK, pcbnew.PCB_VIA))


def _resolve_group(value: str) -> str:
    upper = value.upper()
    if upper in ALIASES:
        return ALIASES[upper]
    for name in ISLANDS:
        if upper == name.upper():
            return name
    raise AuditError(f"unknown group {value!r}; choose G1 through G8")


def _assert_read_only_workbench_path(path: Path) -> None:
    resolved = path.resolve()
    production = (REPO / "pcb-tail/layouts/default").resolve()
    _expect(
        production != resolved.parent and production not in resolved.parents,
        f"refusing to audit production layouts/default as a workbench: {resolved}",
    )


def _group_inventory(
    board: "pcbnew.BOARD",
) -> tuple[dict[str, object], dict[str, str], dict[str, list[object]]]:
    """Validate group/ref/route ownership and return normalized inventories."""

    expected_refs = {ref for island in ISLANDS.values() for ref in island.refs}
    actual_refs = [fp.GetReference() for fp in board.GetFootprints()]
    _expect(len(actual_refs) == 33, f"expected 33 footprints, found {len(actual_refs)}")
    _expect(
        len(set(actual_refs)) == len(actual_refs),
        "footprint references are not unique",
    )
    _expect(
        set(actual_refs) == expected_refs,
        "footprint inventory mismatch: "
        f"missing={sorted(expected_refs - set(actual_refs))}, "
        f"extra={sorted(set(actual_refs) - expected_refs)}",
    )

    groups = {group.GetName(): group for group in board.Groups()}
    _expect(
        set(groups) == set(ISLANDS),
        "PCB_GROUP inventory mismatch: "
        f"expected={sorted(ISLANDS)}, actual={sorted(groups)}",
    )

    ref_owners: dict[str, list[str]] = defaultdict(list)
    route_owners: dict[str, list[str]] = defaultdict(list)
    group_routes: dict[str, list[object]] = {}
    board_route_by_uuid = {_uuid(item): item for item in board.GetTracks()}

    for name, group in groups.items():
        refs: list[str] = []
        routes: list[object] = []
        for item in group.GetItems():
            if isinstance(item, pcbnew.FOOTPRINT):
                ref = item.GetReference()
                refs.append(ref)
                ref_owners[ref].append(name)
            elif _is_route(item):
                _expect(
                    item.GetClass() in {"PCB_TRACK", "PCB_VIA"},
                    f"{name} contains unsupported routed object {item.GetClass()}",
                )
                route_id = _uuid(item)
                _expect(
                    route_id in board_route_by_uuid,
                    f"{name} contains stale routed object {route_id}",
                )
                routes.append(item)
                route_owners[route_id].append(name)

        expected = sorted(ISLANDS[name].refs)
        _expect(
            sorted(refs) == expected,
            f"{name} footprint membership mismatch: "
            f"expected={expected}, actual={sorted(refs)}",
        )
        group_routes[name] = routes

    bad_ref_owners = {
        ref: owners for ref, owners in ref_owners.items() if len(owners) != 1
    }
    _expect(
        not bad_ref_owners and set(ref_owners) == expected_refs,
        "footprints must be covered by exactly one PCB_GROUP: "
        f"owners={bad_ref_owners}, unowned={sorted(expected_refs - set(ref_owners))}",
    )

    unowned_routes = sorted(set(board_route_by_uuid) - set(route_owners))
    multiply_owned_routes = {
        route_id: owners
        for route_id, owners in route_owners.items()
        if len(owners) != 1
    }
    _expect(
        not unowned_routes and not multiply_owned_routes,
        "every track/via must belong to exactly one PCB_GROUP: "
        f"unowned={unowned_routes}, multiply_owned={multiply_owned_routes}",
    )

    route_owner = {route_id: owners[0] for route_id, owners in route_owners.items()}
    return groups, route_owner, group_routes


def _group_pads(
    board: "pcbnew.BOARD", group_name: str
) -> dict[str, list[object]]:
    refs = set(ISLANDS[group_name].refs)
    pads: dict[str, list[object]] = defaultdict(list)
    for footprint in board.GetFootprints():
        if footprint.GetReference() not in refs:
            continue
        for pad in footprint.Pads():
            net = pad.GetNetname()
            if net:
                pads[net].append(pad)
    return dict(pads)


def _validate_internal_net_definition(
    board: "pcbnew.BOARD", group_name: str
) -> dict[str, list[object]]:
    """Ensure the allow-list exactly equals nets with >=2 pads in the island."""

    all_pads = _group_pads(board, group_name)
    derived = {net for net, pads in all_pads.items() if len(pads) >= 2}
    allowed = set(ALLOWED_INTERNAL_NETS[group_name])
    _expect(
        derived == allowed,
        f"{group_name} internal-net contract drift: "
        f"derived={sorted(derived)}, allowlist={sorted(allowed)}",
    )
    return {net: all_pads[net] for net in sorted(allowed)}


def _connected_component(
    connectivity: object,
    start: object,
    net_name: str,
) -> tuple[dict[str, object], dict[str, object]]:
    """Traverse KiCad's exact copper-connectivity graph from one pad."""

    queue = deque([start])
    seen: set[str] = set()
    pads: dict[str, object] = {}
    routes: dict[str, object] = {}

    while queue:
        item = queue.popleft()
        item_id = _uuid(item)
        if item_id in seen:
            continue
        seen.add(item_id)
        _expect(
            item.GetNetname() == net_name,
            f"KiCad connectivity crossed from {net_name} to {item.GetNetname()}",
        )
        if isinstance(item, pcbnew.PAD):
            pads[item_id] = item
        elif _is_route(item):
            routes[item_id] = item
        else:
            raise AuditError(
                f"unsupported connected object {item.GetClass()} on {net_name}"
            )

        for neighbor in connectivity.GetConnectedTracks(item):
            if _uuid(neighbor) not in seen:
                queue.append(neighbor)
        for neighbor in connectivity.GetConnectedPads(item):
            if _uuid(neighbor) not in seen:
                queue.append(neighbor)

    return pads, routes


def _pad_label(pad: object) -> str:
    return f"{pad.GetParentFootprint().GetReference()}.{pad.GetNumber()}"


def _validate_group_routes(
    board: "pcbnew.BOARD",
    connectivity: object,
    group_name: str,
    group_routes: list[object],
    route_owner: dict[str, str],
) -> None:
    internal_pads = _validate_internal_net_definition(board, group_name)
    allowed = set(ALLOWED_INTERNAL_NETS[group_name])
    used = {item.GetNetname() for item in group_routes}

    _expect(
        "" not in used and used <= allowed,
        f"{group_name} has cross-island/unnamed copper: "
        f"allowed={sorted(allowed)}, used={sorted(used)}",
    )
    if not allowed:
        _expect(
            not group_routes,
            f"{group_name} has no honest internal net and must contain 0 copper",
        )
        return

    _expect(
        used == allowed,
        f"{group_name} routing incomplete: "
        f"missing={sorted(allowed - used)}, extra={sorted(used - allowed)}",
    )

    group_refs = set(ISLANDS[group_name].refs)
    group_route_ids_by_net: dict[str, set[str]] = defaultdict(set)
    for item in group_routes:
        group_route_ids_by_net[item.GetNetname()].add(_uuid(item))

    for net_name, expected_pads in internal_pads.items():
        reachable_pads, reachable_routes = _connected_component(
            connectivity, expected_pads[0], net_name
        )
        missing_pads = [
            _pad_label(pad)
            for pad in expected_pads
            if _uuid(pad) not in reachable_pads
        ]
        foreign_pads = sorted(
            _pad_label(pad)
            for pad in reachable_pads.values()
            if pad.GetParentFootprint().GetReference() not in group_refs
        )
        _expect(
            not missing_pads and not foreign_pads,
            f"{group_name}/{net_name} topology incomplete or escaped island: "
            f"missing_pads={missing_pads}, foreign_pads={foreign_pads}",
        )

        expected_route_ids = group_route_ids_by_net[net_name]
        reachable_route_ids = set(reachable_routes)
        orphan_routes = sorted(expected_route_ids - reachable_route_ids)
        foreign_routes = sorted(
            route_id
            for route_id in reachable_route_ids
            if route_owner.get(route_id) != group_name
        )
        _expect(
            not orphan_routes and not foreign_routes,
            f"{group_name}/{net_name} contains orphan/foreign copper: "
            f"orphan={orphan_routes}, foreign={foreign_routes}",
        )


def _shared_copper_layers(
    board: "pcbnew.BOARD", via: object, pad: object
) -> Iterable[int]:
    for layer in board.GetEnabledLayers().CuStack():
        if via.IsOnLayer(layer) and pad.IsOnLayer(layer):
            yield int(layer)


def _validate_no_via_in_pad(
    board: "pcbnew.BOARD", route_owner: dict[str, str]
) -> int:
    """Use KiCad's real effective copper shapes, not bounding boxes."""

    pads = [pad for fp in board.GetFootprints() for pad in fp.Pads()]
    vias = [item for item in board.GetTracks() if isinstance(item, pcbnew.PCB_VIA)]
    collisions: list[str] = []
    for via in vias:
        for pad in pads:
            for layer in _shared_copper_layers(board, via, pad):
                via_shape = via.GetEffectiveShape(layer)
                pad_shape = pad.GetEffectiveShape(layer)
                _expect(
                    via_shape is not None and pad_shape is not None,
                    "KiCad did not provide an effective copper shape for collision audit",
                )
                if via_shape.Collide(pad_shape, 0):
                    pos = via.GetPosition()
                    collisions.append(
                        f"{route_owner[_uuid(via)]}/{via.GetNetname()} via "
                        f"({pcbnew.ToMM(pos.x):.4f},{pcbnew.ToMM(pos.y):.4f}) "
                        f"overlaps {_pad_label(pad)}/{pad.GetNetname()} "
                        f"on {pcbnew.LayerName(layer)}"
                    )
    _expect(
        not collisions,
        "strict no-via-in-pad violation(s), tested with KiCad effective copper "
        "shape collision:\n  " + "\n  ".join(collisions),
    )
    return len(vias)


def _route_summary(group_routes: list[object]) -> str:
    tracks = sum(not isinstance(item, pcbnew.PCB_VIA) for item in group_routes)
    vias = sum(isinstance(item, pcbnew.PCB_VIA) for item in group_routes)
    by_net: dict[str, Counter[str]] = defaultdict(Counter)
    for item in group_routes:
        kind = "via" if isinstance(item, pcbnew.PCB_VIA) else "track"
        by_net[item.GetNetname()][kind] += 1
    nets = ", ".join(
        f"{net}[t={counts['track']},v={counts['via']}]"
        for net, counts in sorted(by_net.items())
    )
    return f"tracks={tracks}, vias={vias}, nets={nets or '-'}"


def _group_envelope(
    board: "pcbnew.BOARD", group_name: str, group_routes: list[object]
) -> str:
    """Report the routed island's courtyard+copper axis-aligned envelope."""

    refs = set(ISLANDS[group_name].refs)
    boxes: list[tuple[float, float, float, float]] = []
    for footprint in board.GetFootprints():
        if footprint.GetReference() not in refs:
            continue
        courtyard = (
            pcbnew.F_CrtYd if footprint.GetLayer() == pcbnew.F_Cu else pcbnew.B_CrtYd
        )
        courtyard_boxes = [
            item.GetBoundingBox()
            for item in footprint.GraphicalItems()
            if item.GetLayer() == courtyard
        ]
        _expect(
            courtyard_boxes,
            f"{group_name}/{footprint.GetReference()} has no courtyard geometry",
        )
        for box in courtyard_boxes:
            boxes.append(
                (
                    pcbnew.ToMM(box.GetLeft()),
                    pcbnew.ToMM(box.GetTop()),
                    pcbnew.ToMM(box.GetRight()),
                    pcbnew.ToMM(box.GetBottom()),
                )
            )

    for item in group_routes:
        if isinstance(item, pcbnew.PCB_VIA):
            position = item.GetPosition()
            radius = pcbnew.ToMM(item.GetFrontWidth()) / 2.0
            x, y = pcbnew.ToMM(position.x), pcbnew.ToMM(position.y)
            boxes.append((x - radius, y - radius, x + radius, y + radius))
        else:
            start, end = item.GetStart(), item.GetEnd()
            radius = pcbnew.ToMM(item.GetWidth()) / 2.0
            x0, x1 = sorted((pcbnew.ToMM(start.x), pcbnew.ToMM(end.x)))
            y0, y1 = sorted((pcbnew.ToMM(start.y), pcbnew.ToMM(end.y)))
            boxes.append((x0 - radius, y0 - radius, x1 + radius, y1 + radius))

    _expect(boxes, f"{group_name} has no footprint/copper envelope")
    left = min(box[0] for box in boxes)
    top = min(box[1] for box in boxes)
    right = max(box[2] for box in boxes)
    bottom = max(box[3] for box in boxes)
    width, height = right - left, bottom - top
    return (
        f"envelope={width:.3f}x{height:.3f}mm, "
        f"area={width * height:.3f}mm^2"
    )


def audit(board_path: Path, selected_group: str | None = None) -> None:
    board_path = board_path.resolve()
    _assert_read_only_workbench_path(board_path)
    _expect(board_path.is_file(), f"board not found: {board_path}")
    board = pcbnew.LoadBoard(str(board_path))
    _expect(board is not None, f"unable to load board: {board_path}")

    title = board.GetTitleBlock().GetTitle().lower()
    _expect(
        "functional-island workbench" in title and "not for fab" in title,
        "board title does not identify the NOT FOR FAB functional-island workbench",
    )
    _expect(board.GetAreaCount() == 0, "functional workbench must contain 0 zones")

    _groups, route_owner, group_routes = _group_inventory(board)
    for group_name, routes in group_routes.items():
        allowed = set(ALLOWED_INTERNAL_NETS[group_name])
        bad = sorted({item.GetNetname() for item in routes} - allowed)
        _expect(
            not bad,
            f"{group_name} uses non-internal routed nets: {bad}",
        )

    via_count = _validate_no_via_in_pad(board, route_owner)
    board.BuildConnectivity()
    connectivity = board.GetConnectivity()
    groups_to_check = [selected_group] if selected_group else list(ISLANDS)
    for group_name in groups_to_check:
        _validate_group_routes(
            board,
            connectivity,
            group_name,
            group_routes[group_name],
            route_owner,
        )

    mode = f"PARTIAL {selected_group}" if selected_group else "FULL"
    print(f"FUNCTIONAL-GROUP WORKBENCH {mode} AUDIT PASS")
    print(f"  board: {board_path}")
    print("  inventory: 33 footprints / 8 mutually exclusive PCB_GROUPs / 0 zones")
    print(f"  strict via-in-pad: PASS ({via_count} vias, exact KiCad copper shapes)")
    for group_name in groups_to_check:
        print(
            f"  {group_name}: {_route_summary(group_routes[group_name])}; "
            f"{_group_envelope(board, group_name, group_routes[group_name])}"
        )
    if selected_group:
        print("  NOTE: PARTIAL mode is for routing diagnostics, not release/fabrication")
    else:
        print("  topology: every internal net connects every in-group pad")
        print("  Edge.Cuts/outside-board island placement: intentionally not audited")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    parser.add_argument(
        "--group",
        help="diagnostic-only partial check for G1..G8; omit for the full gate",
    )
    args = parser.parse_args()
    selected = _resolve_group(args.group) if args.group else None
    audit(args.board, selected)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuditError as exc:
        print(f"FUNCTIONAL-GROUP WORKBENCH AUDIT FAIL: {exc}")
        raise SystemExit(1)

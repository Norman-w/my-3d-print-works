#!/usr/bin/env python3
"""Executable one-cycle trigger contract for the unreleased electric feeder.

This is a controller reference model, not MCU firmware.  The present CAD has
no trusted full-stroke, true mechanical zero, or stopped-motor input, so the
model must not be treated as a working electrical assembly.
"""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
from hashlib import sha256
import itertools
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/electronic-trigger-candidate/point-shot-fsm.json"
INTEGRATION = ROOT / "output/electric-trigger-integration/review.json"
OPTICAL = ROOT / "output/optical-home-candidate/transition-budget.json"
DRIVE = ROOT / "output/electric-drive-feasibility/report.json"

LOCKED = "LOCKED"
READY = "READY"
OUTBOUND = "OUTBOUND"
RETURN = "RETURN"
STOPPING = "STOPPING"
WAIT_RELEASE = "WAIT_RELEASE"
FAULT = "FAULT"
ACTIVE = {OUTBOUND, RETURN}


def sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class Input:
    trigger_pressed: bool = False
    near_home_blocked: bool = False
    full_stroke_event: bool = False
    verified_mechanical_zero: bool = False
    motor_idle: bool = True
    fresh_stop_event: bool = False
    power_good: bool = True
    cycle_watchdog_expired: bool = False


@dataclass(frozen=True)
class Machine:
    state: str = LOCKED
    departed_near_home: bool = False


@dataclass(frozen=True)
class Result:
    machine: Machine
    motor_enable: bool
    start_event: bool
    completed_cycle_event: bool
    reason: str


def step(machine: Machine, sample: Input) -> Result:
    """One debounced input sample; commands are derived after the transition."""
    if machine.state == FAULT:
        return Result(machine, False, False, False, "latched fault")
    if not sample.power_good:
        next_machine = Machine(FAULT)
        reason = "power lost"
    elif sample.verified_mechanical_zero and not sample.near_home_blocked:
        next_machine = Machine(FAULT)
        reason = "zero proof contradicts near-home sensor"
    elif sample.fresh_stop_event and (
            machine.state != STOPPING or not sample.motor_idle):
        next_machine = Machine(FAULT)
        reason = "stale or contradictory stop event"
    elif machine.state in ACTIVE | {STOPPING} and sample.cycle_watchdog_expired:
        next_machine = Machine(FAULT)
        reason = "cycle watchdog expired"
    elif machine.state == LOCKED:
        if (not sample.trigger_pressed and sample.near_home_blocked
                and sample.verified_mechanical_zero and sample.motor_idle
                and not sample.full_stroke_event):
            next_machine, reason = Machine(READY), "released and verified at zero"
        else:
            next_machine, reason = machine, "not yet safe to arm"
    elif machine.state == READY:
        if (not sample.near_home_blocked or not sample.verified_mechanical_zero
                or not sample.motor_idle or sample.full_stroke_event):
            next_machine, reason = Machine(FAULT), "ready precondition lost"
        elif sample.trigger_pressed:
            next_machine, reason = Machine(OUTBOUND), "fresh trigger starts one cycle"
        else:
            next_machine, reason = machine, "armed; waiting for press"
    elif machine.state == OUTBOUND:
        departed = machine.departed_near_home or not sample.near_home_blocked
        if sample.full_stroke_event and not departed:
            next_machine, reason = Machine(FAULT), "full stroke without departure"
        elif sample.full_stroke_event:
            next_machine, reason = Machine(RETURN, True), "full stroke confirmed"
        else:
            next_machine = Machine(OUTBOUND, departed)
            reason = "departed near home" if departed else "awaiting departure"
    elif machine.state == RETURN:
        if sample.full_stroke_event:
            next_machine, reason = Machine(FAULT), "unexpected second full stroke"
        elif sample.verified_mechanical_zero and sample.near_home_blocked:
            next_machine, reason = Machine(STOPPING, True), "true zero; remove drive"
        else:
            next_machine, reason = machine, "near-home alone cannot complete cycle"
    elif machine.state == STOPPING:
        if (not sample.near_home_blocked or not sample.verified_mechanical_zero
                or sample.full_stroke_event):
            next_machine, reason = Machine(FAULT), "zero lost during stopping"
        elif sample.motor_idle and sample.fresh_stop_event:
            next_machine = Machine(READY if not sample.trigger_pressed else WAIT_RELEASE)
            reason = "stopped at zero; release required before next press"
        else:
            next_machine, reason = machine, "waiting for stopped motor"
    elif machine.state == WAIT_RELEASE:
        if (not sample.near_home_blocked or not sample.verified_mechanical_zero
                or not sample.motor_idle or sample.full_stroke_event):
            next_machine, reason = Machine(FAULT), "zero lost while held"
        elif not sample.trigger_pressed:
            next_machine, reason = Machine(READY), "released after complete cycle"
        else:
            next_machine, reason = machine, "held trigger cannot repeat"
    else:
        raise RuntimeError(f"Unknown state: {machine.state}")
    return Result(
        next_machine,
        next_machine.state in ACTIVE,
        machine.state == READY and next_machine.state == OUTBOUND,
        machine.state == STOPPING and next_machine.state in {READY, WAIT_RELEASE},
        reason,
    )


def trace(samples: list[Input]) -> dict:
    machine = Machine()
    rows = []
    for index, sample in enumerate(samples):
        before = machine
        result = step(machine, sample)
        machine = result.machine
        rows.append({"tick": index, "before": before.state,
                     "inputs": asdict(sample), "after": machine.state,
                     "motor_enable": result.motor_enable,
                     "start_event": result.start_event,
                     "completed_cycle_event": result.completed_cycle_event,
                     "reason": result.reason})
    return {"rows": rows,
            "motor_start_count": sum(row["start_event"] for row in rows),
            "completed_cycle_count": sum(row["completed_cycle_event"] for row in rows),
            "final_state": machine.state}


def exhaustive_invariants() -> dict:
    # The two missing proof inputs are deliberately varied independently of
    # the optical boolean; contradictory assertions must fault, not rearm.
    choices = [Input(trigger_pressed=t, near_home_blocked=o,
                     full_stroke_event=f, verified_mechanical_zero=z,
                     motor_idle=i, fresh_stop_event=s)
               for t, o, f, z, i, s in
               itertools.product((False, True), repeat=6)]
    queue = deque([(Machine(), 0, False, False)])
    seen = set(queue)
    transitions = 0
    while queue:
        machine, starts, held_after_start, cycle_completed = queue.popleft()
        for sample in choices:
            result = step(machine, sample)
            transitions += 1
            if result.start_event:
                assert machine.state == READY
                assert sample.trigger_pressed
                assert not held_after_start
                assert cycle_completed or starts == 0
            if machine.state == FAULT:
                assert result.machine.state == FAULT and not result.motor_enable
            if machine.state == RETURN and sample.near_home_blocked \
                    and not sample.verified_mechanical_zero:
                assert result.machine.state != STOPPING
            if result.completed_cycle_event:
                assert sample.motor_idle and sample.fresh_stop_event
                assert sample.verified_mechanical_zero
            if result.motor_enable:
                assert result.machine.state in ACTIVE
            # Monitor the same uninterrupted physical hold. A release sample
            # resets the monitor even if it occurs during an active cycle.
            new_held = (held_after_start and sample.trigger_pressed) \
                or result.start_event
            if not sample.trigger_pressed:
                new_held = False
            new_starts = min(starts + int(result.start_event), 2)
            new_completed = cycle_completed or result.completed_cycle_event
            node = (result.machine, new_starts, new_held, new_completed)
            if node not in seen:
                seen.add(node)
                queue.append(node)
    return {"distinct_abstract_states": len(seen),
            "checked_transitions": transitions,
            "invariants": [
                "start only from READY with a pressed trigger and prior arming",
                "held trigger cannot cause a second start",
                "optical reblock without verified mechanical zero cannot stop or rearm",
                "cycle completion requires motor idle and verified zero",
                "a fresh post-disable stop event is required for completion",
                "FAULT is latched with motor command off",
            ]}


def main() -> int:
    integration = json.loads(INTEGRATION.read_text())
    optical = json.loads(OPTICAL.read_text())
    drive = json.loads(DRIVE.read_text())
    if integration["status"] != "SELECTED_TRIGGER_GEOMETRY_PASS_UNRELEASED" \
            or optical["status"] != "GEOMETRIC_NEAR_HOME_ONLY_ZERO_UNPROVEN" \
            or optical["one_shot_rearm_from_optical_blocked_alone_permitted"] \
            or drive["status"] != "NECESSARY_LOAD_BOUND_ONLY_MOTOR_NOT_APPROVED":
        raise RuntimeError("Current geometry or motor evidence no longer matches contract")
    home = Input(near_home_blocked=True, verified_mechanical_zero=True)
    held_home = Input(trigger_pressed=True, near_home_blocked=True,
                      verified_mechanical_zero=True)
    moving = Input(trigger_pressed=True, near_home_blocked=False, motor_idle=False)
    full = Input(trigger_pressed=True, near_home_blocked=False,
                 full_stroke_event=True, motor_idle=False)
    unsafe_partial = Input(trigger_pressed=True, near_home_blocked=True,
                           verified_mechanical_zero=False, motor_idle=False)
    returned = Input(trigger_pressed=True, near_home_blocked=True,
                     verified_mechanical_zero=True, motor_idle=False)
    stopped_event_held = Input(trigger_pressed=True, near_home_blocked=True,
                               verified_mechanical_zero=True, motor_idle=True,
                               fresh_stop_event=True)
    stopped_held = Input(trigger_pressed=True, near_home_blocked=True,
                         verified_mechanical_zero=True, motor_idle=True)
    normal = trace([home, held_home, moving, full, unsafe_partial, returned,
                    stopped_event_held, stopped_held, home])
    two_presses = trace([home, held_home, moving, full, unsafe_partial, returned,
                         stopped_event_held, stopped_held, home, held_home])
    held = trace([home, held_home, moving, full, unsafe_partial, returned,
                  stopped_event_held, stopped_held, stopped_held])
    stuck = trace([home, held_home, moving, full, unsafe_partial,
                   Input(trigger_pressed=False, near_home_blocked=True,
                         motor_idle=False, cycle_watchdog_expired=True), home])
    stop_not_confirmed = trace([home, held_home, moving, full, returned,
                                Input(trigger_pressed=False, near_home_blocked=True,
                                      verified_mechanical_zero=True, motor_idle=False,
                                      cycle_watchdog_expired=True)])
    coast_past_zero = trace([home, held_home, moving, full, returned,
                             Input(trigger_pressed=True, near_home_blocked=False,
                                   verified_mechanical_zero=False,
                                   motor_idle=False), home])
    stuck_idle_high = trace([
        home, held_home,
        Input(trigger_pressed=True, near_home_blocked=False, motor_idle=True),
        Input(trigger_pressed=True, near_home_blocked=False,
              full_stroke_event=True, motor_idle=True),
        Input(trigger_pressed=True, near_home_blocked=True,
              verified_mechanical_zero=True, motor_idle=True),
        stopped_held,
    ])
    stale_stop_event = trace([home, held_home,
                              Input(trigger_pressed=True, near_home_blocked=False,
                                    motor_idle=False, fresh_stop_event=True)])
    boot_held = trace([held_home, held_home, home, held_home])
    assert normal["motor_start_count"] == 1 \
        and normal["completed_cycle_count"] == 1 \
        and normal["final_state"] == READY
    assert two_presses["motor_start_count"] == 2 \
        and two_presses["completed_cycle_count"] == 1
    assert held["motor_start_count"] == 1 and held["final_state"] == WAIT_RELEASE
    assert stuck["motor_start_count"] == 1 and stuck["final_state"] == FAULT
    assert stop_not_confirmed["final_state"] == FAULT
    assert coast_past_zero["motor_start_count"] == 1 \
        and coast_past_zero["completed_cycle_count"] == 0 \
        and coast_past_zero["rows"][4]["after"] == STOPPING \
        and not coast_past_zero["rows"][4]["motor_enable"] \
        and coast_past_zero["final_state"] == FAULT
    assert boot_held["motor_start_count"] == 1 \
        and boot_held["rows"][0]["after"] == LOCKED
    assert stuck_idle_high["rows"][4]["after"] == STOPPING \
        and stuck_idle_high["completed_cycle_count"] == 0 \
        and stuck_idle_high["final_state"] == STOPPING
    assert stale_stop_event["final_state"] == FAULT
    assert normal["rows"][4]["after"] == RETURN \
        and normal["rows"][4]["motor_enable"]
    report = {
        "status": "REFERENCE_CONTROLLER_CONTRACT_ONLY_MISSING_REAL_INPUTS",
        "source_sha256": {
            "analysis/electric_point_shot_fsm.py": sha(Path(__file__)),
            str(INTEGRATION.relative_to(ROOT)): sha(INTEGRATION),
            str(OPTICAL.relative_to(ROOT)): sha(OPTICAL),
            str(DRIVE.relative_to(ROOT)): sha(DRIVE),
        },
        "state_names": [LOCKED, READY, OUTBOUND, RETURN,
                        STOPPING, WAIT_RELEASE, FAULT],
        "normal_cycle": normal,
        "two_presses_with_release": two_presses,
        "held_trigger_cycle": held,
        "partial_return_timeout": stuck,
        "stop_not_confirmed_timeout": stop_not_confirmed,
        "coast_past_zero_after_drive_cut": coast_past_zero,
        "stuck_high_idle_without_fresh_stop_event": stuck_idle_high,
        "stale_stop_event_while_running": stale_stop_event,
        "boot_with_trigger_held": boot_held,
        "exhaustive_boolean_input_review": exhaustive_invariants(),
        "electrical_output_scope": "At most one motor-start command per uninterrupted trigger hold, conditional on trusted full-stroke, mechanical-zero, and cycle-bound fresh-stop proofs; ball count is not proved",
        "current_hardware_inputs_missing": [
            "trusted full-stroke event or validated internal motor phase",
            "mechanical-zero proof independent of the current near-home optical boolean",
            "stopped-motor feedback or validated post-stop settling behavior",
            "a cycle-bound fresh stop event from the hardware adapter",
            "measured cycle duration for a watchdog setting",
        ],
        "optical_blocked_aliased_as_verified_zero": False,
        "mcu_firmware_implemented": False,
        "power_stage_selected": False,
        "motor_mounted": False,
        "ball_exit_count_verified": False,
        "manufacturing_release": False,
        "physical_acceptance": False,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("electric one-shot contract: "
          f"{report['exhaustive_boolean_input_review']['checked_transitions']} "
          "abstract transitions; hardware proof inputs open")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

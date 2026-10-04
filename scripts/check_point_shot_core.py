#!/usr/bin/env python3
"""Compare every Boolean input transition with the reviewed Python contract.

This checks portable controller logic only. It does not test sensor wiring,
motor braking, real-time sampling, physical end points, or ball count.
"""

from __future__ import annotations

from hashlib import sha256
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
import electric_point_shot_fsm as reference  # noqa: E402

STATES = (
    reference.LOCKED, reference.READY, reference.OUTBOUND,
    reference.RETURN, reference.STOPPING, reference.WAIT_RELEASE,
    reference.FAULT,
)
OUT = ROOT / "output/electronic-trigger-candidate/point-shot-core-review.json"
SOURCES = (
    ROOT / "firmware/point_shot_core.h",
    ROOT / "firmware/point_shot_core.cpp",
    ROOT / "firmware/point_shot_core_cli.cpp",
    ROOT / "analysis/electric_point_shot_fsm.py",
    Path(__file__),
)


def fingerprint(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def all_cases() -> list[tuple[reference.Machine, reference.Input]]:
    cases = []
    for state, departed in itertools.product(STATES, (False, True)):
        for bits in itertools.product((False, True), repeat=8):
            cases.append((reference.Machine(state, departed),
                          reference.Input(*bits)))
    return cases


def encode(machine: reference.Machine, sample: reference.Input) -> str:
    values = (STATES.index(machine.state), machine.departed_near_home,
              sample.trigger_pressed, sample.near_home_blocked,
              sample.full_stroke_event, sample.verified_mechanical_zero,
              sample.motor_idle, sample.fresh_stop_event, sample.power_good,
              sample.cycle_watchdog_expired)
    return " ".join(str(int(value)) for value in values)


def main() -> int:
    cases = all_cases()
    compiler = ["c++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                "-pedantic", "-O2"]
    with tempfile.TemporaryDirectory(prefix="point-shot-core-") as tmp:
        binary = Path(tmp) / "core-cli"
        subprocess.run(compiler + [str(ROOT / "firmware/point_shot_core.cpp"),
                                   str(ROOT / "firmware/point_shot_core_cli.cpp"),
                                   "-o", str(binary)], check=True)
        payload = "\n".join(encode(machine, sample) for machine, sample in cases)
        # An invalid stored state must fail closed even if inputs appear safe.
        payload += "\n255 0 0 1 0 1 1 0 1 0\n"
        completed = subprocess.run([str(binary)], input=payload, text=True,
                                   capture_output=True, check=True)
    lines = completed.stdout.splitlines()
    if len(lines) != len(cases) + 1:
        raise RuntimeError("Host controller did not return one result per case")
    mismatches = []
    for index, ((machine, sample), line) in enumerate(zip(cases, lines)):
        expected = reference.step(machine, sample)
        expected_fields = (
            STATES.index(expected.machine.state),
            int(expected.machine.departed_near_home),
            int(expected.motor_enable), int(expected.start_event),
            int(expected.completed_cycle_event),
        )
        actual_fields = tuple(int(field) for field in line.split())
        if actual_fields != expected_fields:
            mismatches.append({"case": index, "prior_state": machine.state,
                               "departed": machine.departed_near_home,
                               "input": reference.asdict(sample),
                               "expected": expected_fields,
                               "actual": actual_fields})
    invalid_state_fields = tuple(int(field) for field in lines[-1].split())
    if invalid_state_fields != (6, 0, 0, 0, 0):
        mismatches.append({"case": "invalid-state-fail-closed",
                           "actual": invalid_state_fields})
    invariants = reference.exhaustive_invariants()
    assert invariants["checked_transitions"] >= 900
    report = {
        "status": "PORTABLE_CORE_MATCHES_REFERENCE_UNRELEASED" if not mismatches
                  else "PORTABLE_CORE_MISMATCH",
        "exhaustive_reference_transition_count": invariants["checked_transitions"],
        "cross_language_boolean_transition_count": len(cases),
        "invalid_state_fails_closed": invalid_state_fields == (6, 0, 0, 0, 0),
        "mismatches": mismatches,
        "source_sha256": {str(path.relative_to(ROOT)): fingerprint(path)
                          for path in SOURCES},
        "hardware_adapter_implemented": False,
        "motor_driver_selected": False,
        "real_sensor_inputs_verified": False,
        "watchdog_time_measured": False,
        "motor_stop_repeatability_measured": False,
        "manufacturing_release": False,
        "physical_acceptance": False,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"{report['status']}: {len(cases)} host transitions, "
          f"{len(mismatches)} mismatches")
    return 0 if not mismatches else 1


if __name__ == "__main__":
    raise SystemExit(main())

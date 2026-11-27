#!/usr/bin/env python3
"""Screen real low-voltage driver ratings against archived BY141 seller claims.

This is a component selection gate, not a power-stage design. The seller's
shared gallery is not a measured specification for the exact chosen SKU.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from electric_drive_feasibility import seller_gallery_claims


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/electric-drive-feasibility/driver-screen.json"

# Primary manufacturer documents. Values are operating ratings, not a
# promise of usable current on an arbitrary breakout/PCB or duty cycle.
DRIVERS = {
    "TI DRV8850": {
        "source": "https://www.ti.com/lit/ds/symlink/drv8850.pdf",
        "supply_v": [2.0, 5.5], "peak_a": 8.0, "continuous_a": 5.0,
        "current_feedback_a": [0.5, 5.0],
        "current_feedback_test_supply_v": 4.2,
        "notes": "5 A continuous assumes adequate PCB heat sinking. Low-side slow-decay braking is available through half-bridge controls, but VPROPI does not sense low-side braking current. OCP automatically retries and is not a shot-completion signal.",
    },
    "TI DRV8833 paralleled": {
        "source": "https://www.ti.com/product/DRV8833",
        "supply_v": [2.7, 10.8], "peak_a": 4.0,
        "continuous_a": 3.0,
        "notes": "Parallel outputs require the specified package and correct parallel wiring; still below the seller's upper stall claim.",
    },
    "TI DRV8873": {
        "source": "https://www.ti.com/product/DRV8873",
        "supply_v": [4.5, 38.0], "peak_a": 10.0,
        "notes": "Minimum operating supply exceeds the motor's nominal 3.7 V.",
    },
    "Infineon BTS7960": {
        "source": "https://www.infineon.com/assets/row/public/documents/10/57/infineon-bts7960-ds-en.pdf",
        "supply_v": [5.5, 27.5],
        "notes": "Minimum operating supply exceeds the motor's nominal 3.7 V; the chip is a half-bridge, not a complete H-bridge.",
    },
}


def sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> int:
    gallery = seller_gallery_claims()
    motor_v = gallery["image_06_claims"]["voltage_range_v"]
    nominal_v = gallery["image_02_claims"]["nominal_voltage_v"]
    stall_upper = gallery["image_06_claims"]["stall_current_a"][1]
    rated_upper = gallery["image_06_claims"]["rated_current_upper_a"]
    assert motor_v == [2.5, 4.5] and nominal_v == 3.7
    assert stall_upper == 7.5 and rated_upper == 0.36
    comparisons = {}
    for name, spec in DRIVERS.items():
        supply_min, supply_max = spec["supply_v"]
        covers_nominal = supply_min <= nominal_v <= supply_max
        peak = spec.get("peak_a")
        peak_headroom = None if peak is None else round(peak - stall_upper, 3)
        feedback = spec.get("current_feedback_a")
        comparisons[name] = {
            **spec,
            "motor_nominal_supply_covered": covers_nominal,
            "seller_upper_stall_claim_to_driver_peak_headroom_a": peak_headroom,
            "seller_rated_upper_inside_feedback_spec": None if feedback is None
            else feedback[0] <= rated_upper <= feedback[1],
            "seller_stall_upper_inside_feedback_spec": None if feedback is None
            else feedback[0] <= stall_upper <= feedback[1],
            "final_driver_approved": False,
        }
    assert comparisons["TI DRV8850"]["seller_upper_stall_claim_to_driver_peak_headroom_a"] == .5
    assert not comparisons["TI DRV8850"]["seller_rated_upper_inside_feedback_spec"]
    assert not comparisons["TI DRV8850"]["seller_stall_upper_inside_feedback_spec"]
    assert comparisons["TI DRV8833 paralleled"]["seller_upper_stall_claim_to_driver_peak_headroom_a"] < 0
    assert not comparisons["TI DRV8873"]["motor_nominal_supply_covered"]
    assert not comparisons["Infineon BTS7960"]["motor_nominal_supply_covered"]
    report = {
        "status": "LOW_VOLTAGE_DRIVER_SCREEN_NO_FINAL_SELECTION",
        "motor_evidence_scope": gallery["scope"],
        "motor_nominal_voltage_v": nominal_v,
        "seller_shared_image_motor_voltage_range_v": motor_v,
        "seller_shared_image_stall_current_range_a":
            gallery["image_06_claims"]["stall_current_a"],
        "seller_shared_image_rated_current_upper_a": rated_upper,
        "comparisons": comparisons,
        "bench_candidate": "TI DRV8850",
        "bench_candidate_only_reason": [
            "Only 0.5 A numerical headroom from the unverified 7.5 A stall claim to the 8 A specified peak; peak duration and PCB thermal behavior remain unknown.",
            "Its specified 0.5-5 A current-feedback window covers neither the seller's <0.36 A rated-current statement nor 7.5 A stall upper claim.",
            "OCP/thermal events can auto-retry; they cannot certify a completed motor cycle or parked feeder.",
            "Stopping after power removal and motor load/current are unmeasured for the exact SKU.",
        ],
        "required_before_final_driver_selection": [
            "Measured current peaks and duration at startup, forward load, return load and braking at the intended supply range.",
            "Measured stop/coast/brake behavior and repeatable true-zero parking with the actual mechanical load.",
            "Measured continuous duty and driver PCB temperature, plus a power source that holds the motor within its real allowed voltage range.",
        ],
        "seller_gallery_sha256": gallery["product_evidence_sha256"],
        "source_images": gallery["source_images"],
        "source_sha256": {"analysis/by141_driver_screen.py": sha(Path(__file__))},
        "driver_selected": False,
        "power_stage_schematic_complete": False,
        "manufacturing_release": False,
        "physical_acceptance": False,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("BY141 driver screen: DRV8850 bench candidate only; "
          "no final power stage selected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

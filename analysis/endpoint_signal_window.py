#!/usr/bin/env python3
"""Screen the endpoint-switch pulse width without treating seller speed as measured.

The switch is adjusted to trip shortly before the mechanical stop. This script
compares two *illustrative* feeder motion profiles; it cannot size a debounce
filter or approve a motor/driver without a measured displacement-time trace.
"""

from __future__ import annotations

from hashlib import sha256
import json
from math import acos, pi
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "output/electric-home-switch-screen/review.json"
FULL = ROOT / "output/electric-full-stroke-switch-screen/review.json"
SIDE = ROOT / "output/electric-end-switch-side-cap/review.json"
OUT = ROOT / "output/electric-end-switch-side-cap/signal-window.json"


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def sinusoidal_time_from_endpoint_ms(distance_mm: float, stroke_mm: float,
                                     cycles_per_second: float) -> float:
    # u(t) = stroke/2 * (1 - cos(2*pi*f*t)); t=0 is an endpoint.
    return 1000 * acos(1 - 2 * distance_mm / stroke_mm) / (2 * pi * cycles_per_second)


def main() -> None:
    home = json.loads(HOME.read_text())
    full = json.loads(FULL.read_text())
    side = json.loads(SIDE.read_text())
    assert home["status"] == "HOME_SWITCH_PACKAGING_SCREEN_ONLY"
    assert full["status"] == "FULL_STROKE_SWITCH_PACKAGING_SCREEN_ONLY"
    assert side["status"] == "SIDE_BOLTED_ENDPOINT_CAP_GEOMETRY_PASS_UNRELEASED"
    assert side["home_switch_review_sha256"] == digest(HOME)
    assert side["full_switch_review_sha256"] == digest(FULL)
    assert side["promoted_to_selected_parts"] is False
    assert side["physical_acceptance"] is False
    home_press = home["catalogue_only_calibration_window"]["intended_press_past_actual_OP_at_home_mm"]
    full_press = full["catalogue_only_calibration_window"]["intended_press_past_actual_OP_at_full_mm"]
    assert home_press == full_press == [0.1, 0.2]
    md_max = home["catalogue"]["movement_differential_max_mm"]
    assert md_max == 0.12
    assert home["catalogue"]["overtravel_min_mm"] == 0.25
    assert full["candidate_geometry"]["full_stroke_travel_mm"] == 20
    stroke_mm = 20.0
    hypothetical_cycles_per_second = 2.0
    traverse_ms = 1000 / (2 * hypothetical_cycles_per_second)
    uniform_speed_mm_s = stroke_mm / (traverse_ms / 1000)
    cases = []
    for press_mm in home_press:
        for md_mm in (0.0, md_max):
            release_distance_mm = press_mm + md_mm
            arrival_ms = 1000 * press_mm / uniform_speed_mm_s
            departure_ms = 1000 * release_distance_mm / uniform_speed_mm_s
            harmonic_arrival_ms = sinusoidal_time_from_endpoint_ms(
                press_mm, stroke_mm, hypothetical_cycles_per_second)
            harmonic_departure_ms = sinusoidal_time_from_endpoint_ms(
                release_distance_mm, stroke_mm, hypothetical_cycles_per_second)
            cases.append({
                "press_past_actual_OP_at_stop_mm": press_mm,
                "assumed_movement_differential_mm": md_mm,
                "switch_actuates_before_stop_mm": press_mm,
                "switch_releases_after_departing_stop_mm": release_distance_mm,
                "constant_speed_illustration": {
                    "arrival_to_stop_ms": round(arrival_ms, 3),
                    "stop_to_release_ms": round(departure_ms, 3),
                    "total_pressed_window_ms": round(arrival_ms + departure_ms, 3),
                },
                "sinusoidal_illustration": {
                    "arrival_to_stop_ms": round(harmonic_arrival_ms, 3),
                    "stop_to_release_ms": round(harmonic_departure_ms, 3),
                    "total_pressed_window_ms": round(harmonic_arrival_ms + harmonic_departure_ms, 3),
                },
            })
    assert [row["constant_speed_illustration"]["total_pressed_window_ms"]
            for row in cases] == [2.5, 4.0, 5.0, 6.5]
    result = {
        "status": "ILLUSTRATIVE_ENDPOINT_PULSE_SCREEN_REAL_TIMING_UNKNOWN",
        "source_sha256": {
            "analysis/endpoint_signal_window.py": digest(Path(__file__).resolve()),
            str(HOME.relative_to(ROOT)): digest(HOME),
            str(FULL.relative_to(ROOT)): digest(FULL),
            str(SIDE.relative_to(ROOT)): digest(SIDE),
        },
        "catalogue": {
            "part": home["catalogue"]["part_candidate"],
            "url": home["catalogue"]["url"],
            "movement_differential_max_mm": md_max,
            "overtravel_min_mm": home["catalogue"]["overtravel_min_mm"],
        },
        "geometry": {
            "feeder_stroke_mm": stroke_mm,
            "calibrate_each_physical_switch_past_its_own_OP_at_stop_mm": home_press,
            "upper_and_lower_end_switches_share_this_screen": True,
        },
        "illustration_only": {
            "hypothetical_complete_cycles_per_second": hypothetical_cycles_per_second,
            "hypothetical_half_cycle_traverse_ms": traverse_ms,
            "constant_speed_mm_per_second": uniform_speed_mm_s,
            "sinusoidal_displacement": "u(t)=10*(1-cos(4*pi*t)) mm",
            "seller_cycle_rate_or_selected_motor_profile_verified": False,
            "cases": cases,
        },
        "five_ms_stable_debounce_safe_from_this_evidence": False,
        "home_switch_closed_alone_proves_hard_stop": False,
        "full_switch_closed_alone_proves_full_travel": False,
        "endpoint_event_capture_and_noise_rejection_finalized": False,
        "measured_waveforms_required": [
            "Both raw switch signals against independently measured carriage position",
            "Minimum active interval through start, steady run, low battery and loaded ball path",
            "Contact bounce and electrical noise at motor start/stop",
            "Drive-off to true motor standstill and any motion after the zero event",
        ],
        "manufacturing_release": False,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(f"Wrote {OUT.relative_to(ROOT)}: idealized constant-speed window "
          f"{cases[0]['constant_speed_illustration']['total_pressed_window_ms']}–"
          f"{cases[-1]['constant_speed_illustration']['total_pressed_window_ms']} ms")


if __name__ == "__main__":
    main()

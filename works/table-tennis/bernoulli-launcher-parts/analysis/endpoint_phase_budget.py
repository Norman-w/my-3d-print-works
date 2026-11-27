#!/usr/bin/env python3
"""Size the two-way motor/rocker endpoint travel budget from measured positions.

Motor positions must share one fixed mounting datum and include all positions
reachable after the intended stop command. This is a kinematic bound, not a
strength, spring, or motor approval.
"""

from __future__ import annotations

import argparse
import json
import math


def finite_nonnegative(value: float) -> bool:
    return math.isfinite(value) and value >= 0


def budget(
    home_min: float,
    home_max: float,
    full_min: float,
    full_max: float,
    output_travel: float,
    ratio: float,
    home_cushion: float,
    full_cushion: float,
    output_travel_tolerance: float = 0,
) -> dict:
    values = (home_min, home_max, full_min, full_max, output_travel,
              ratio, home_cushion, full_cushion, output_travel_tolerance)
    if not all(math.isfinite(v) for v in values):
        raise ValueError("All positions and dimensions must be finite")
    if not home_min <= home_max < full_min <= full_max:
        raise ValueError("Expected home_min <= home_max < full_min <= full_max")
    if output_travel <= output_travel_tolerance or ratio <= 0 or not all(
        finite_nonnegative(v) for v in (
            home_cushion, full_cushion, output_travel_tolerance)
    ):
        raise ValueError("Travel must exceed its tolerance; ratio > 0; cushions >= 0")

    # Motor x increases from the home end to the full end. At a hard stop the
    # output stays still while a captured, compliant motor-side joint takes up
    # the residual input motion. The geometric hard-stop phase is h at home
    # and h + F/r at full. Both must be reached in every endpoint cycle.
    output_min = output_travel - output_travel_tolerance
    output_max = output_travel + output_travel_tolerance
    input_between_stops_min = output_min / ratio
    input_between_stops_max = output_max / ratio
    robust_span = full_min - home_max
    phase_low = home_max + home_cushion
    phase_high = full_min - input_between_stops_max - full_cushion
    usable_span = robust_span - home_cushion - full_cushion
    result = {
        "status": "FEASIBLE_KINEMATIC_BUDGET_ONLY" if phase_low <= phase_high
                  else "INFEASIBLE_ENDPOINT_BUDGET",
        "input_positions_mm": {
            "home": [home_min, home_max], "full": [full_min, full_max]
        },
        "output_travel_mm": output_travel,
        "output_travel_interval_mm": [output_min, output_max],
        "output_to_input_ratio": ratio,
        "input_distance_between_output_stops_interval_mm": [
            input_between_stops_min, input_between_stops_max
        ],
        "robust_input_span_mm": robust_span,
        "minimum_input_overtravel_mm": {
            "home": home_cushion, "full": full_cushion
        },
        "phase_window_mm": [phase_low, phase_high],
        "phase_window_width_mm": phase_high - phase_low,
        "minimum_ratio_for_requested_cushions": (
            output_max / usable_span if usable_span > 0 else None
        ),
        "missing_input_travel_mm": max(0.0, phase_low - phase_high),
        "scope": (
            "Endpoint positions must be measured on the selected motor and "
            "include stopping overrun. A feasible interval only sizes a "
            "two-way compliant joint; it does not establish its spring force, "
            "strength, case mounting or one-ball operation."
        ),
    }
    if phase_low <= phase_high:
        # Balance the two worst-case end capacities, then clamp to the window
        # that guarantees the requested minimum cushion at both ends.
        balanced_phase = (home_min + full_max - input_between_stops_min) / 2
        phase = max(phase_low, min(phase_high, balanced_phase))
        result["suggested_adjustment_mm"] = {
            "motor_position_at_output_home_stop": phase,
            "motor_position_at_output_full_stop_interval": [
                phase + input_between_stops_min,
                phase + input_between_stops_max,
            ],
            "relative_to_same_mounting_datum": True,
        }
        result["required_captured_joint_motion_mm"] = {
            "toward_home_max": phase - home_min,
            "toward_full_max": full_max - phase - input_between_stops_min,
        }
        result["guaranteed_minimum_joint_motion_mm"] = {
            "toward_home": phase - home_max,
            "toward_full": full_min - phase - input_between_stops_max,
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("home-min", "home-max", "full-min", "full-max",
                 "ratio"):
        parser.add_argument(f"--{name}", required=True, type=float)
    parser.add_argument("--output-travel", type=float, default=20)
    parser.add_argument("--output-travel-tolerance", type=float, default=0)
    parser.add_argument("--home-cushion", type=float, default=0)
    parser.add_argument("--full-cushion", type=float, default=0)
    args = parser.parse_args()
    try:
        result = budget(args.home_min, args.home_max, args.full_min,
                        args.full_max, args.output_travel, args.ratio,
                        args.home_cushion, args.full_cushion,
                        args.output_travel_tolerance)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "FEASIBLE_KINEMATIC_BUDGET_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())

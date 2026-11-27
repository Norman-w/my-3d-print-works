#!/usr/bin/env python3
"""Independent v4/v5 reducer equations, SCAD sample parity and C3 join audit.

Geometry only: radial curves/derivatives are not a fluid or strength simulation.
"""
import json
import math
import numpy as np

from build_fan76_smooth_v2 import dump, sha
from fan76_smooth_release import smooth_release


def clamp(t):
    return max(0., min(1., t))


def smooth(t):
    t = clamp(t)
    return t**3*(10-15*t+6*t*t)


def old_progress(t, a=.35):
    if t < a:
        u = t/a
        return a*(u**3-u**4/2)/(1-a)
    if t > 1-a:
        return 1-old_progress(1-t, a)
    return (t-a/2)/(1-a)


def ramp_integral(u, b):
    """T and its first three derivatives, independent of SCAD evaluation."""
    if u < b:
        v = u/b
        return (b*b*(v**4/4-v**5/10)/(1-b),
                b*(v**3-v**4/2)/(1-b), (3*v*v-2*v**3)/(1-b),
                (6*v-6*v*v)/(b*(1-b)))
    if u > 1-b:
        t, d1, d2, d3 = ramp_integral(1-u, b)
        return u-.5+t, 1-d1, d2, -d3
    return (u*u/2-b*u/2+3*b*b/20)/(1-b), (u-b/2)/(1-b), 1/(1-b), 0.


def progress(t, a, b):
    if t <= 0:
        return (0., 0., 0., 0.)
    if t >= 1:
        return (1., 0., 0., 0.)
    if t < a:
        v, d1, d2, d3 = ramp_integral(t/a, b)
        return a*v/(1-a), d1/(1-a), d2/(a*(1-a)), d3/(a*a*(1-a))
    if t > 1-a:
        v, d1, d2, d3 = progress(1-t, a, b)
        return 1-v, d1, -d2, d3
    return (t-a/2)/(1-a), 1/(1-a), 0., 0.


def profile(z, p, revision):
    # SCAD echo rounds to six significant digits. Use exact polygon equation.
    r0 = p["socket_id"]/2/math.cos(math.pi/p["fn"])
    end = p["female_minor"]/2
    t = clamp((z-p["blend_z0"])/p["blend_length"])
    if revision == 4:
        s = old_progress(t, p["curve_ramp_fraction"])
        fade, rise = smooth((z-26)/60), smooth((z-98)/32)
    else:
        a = 34/p["blend_length"]
        b = p["curve_curvature_ramp_fraction"]
        s = progress(t, a, b)[0]
        fade = progress(clamp((z-p["blend_z0"])/p["wall_fade_length"]), .3, b)[0]
        rise = progress(clamp((z-p["wall_rise_z0"])/p["wall_rise_length"]), .3, b)[0]
    inner = r0+(end-r0)*s
    thin = p["thin_wall_radial_nominal"]
    wall = thin+(p["body_od"]/2-r0-thin)*(1-fade)+(p["thread_shell_od"]/2-end-thin)*rise
    return inner, inner+wall


def main():
    cases = []
    for revision in [4, 5]:
        release = smooth_release(revision)
        p = json.loads((release.out / "verification/parameters.json").read_text())
        samples = np.asarray(json.loads((release.out / "verification/profile-samples.json").read_text()))
        rows = samples[(samples[:, 0] >= p["blend_z0"]) & (samples[:, 0] <= p["blend_z1"])]
        error = np.max(np.abs(np.array([profile(float(z), p, revision) for z in rows[:, 0]])-rows[:, 1:]))
        z = np.linspace(p["blend_z0"], p["blend_z1"], 12401)
        radii = np.array([profile(float(v), p, revision) for v in z])
        slope = np.gradient(radii, z, axis=0)
        second = np.gradient(slope, z, axis=0)
        cases.append({"revision": revision, "scad_samples_max_error_mm": float(error),
                      "inner_max_angle_deg": float(np.degrees(np.arctan(np.max(np.abs(slope[:, 0]))))),
                      "outer_max_angle_deg": float(np.degrees(np.arctan(np.max(np.abs(slope[:, 1]))))),
                      "inner_max_abs_radius_second_derivative_per_mm": float(np.max(np.abs(second[:, 0]))),
                      "outer_max_abs_radius_second_derivative_per_mm": float(np.max(np.abs(second[:, 1]))),
                      "source_samples_sha256": sha(release.out / "verification/profile-samples.json")})
    p = json.loads((smooth_release(5).out / "verification/parameters.json").read_text())
    joins = []
    for a in [34/p["blend_length"], .3]:
        b = p["curve_curvature_ramp_fraction"]
        knots = [0, a*b, a*(1-b), a, 1-a, 1-a*(1-b), 1-a*b, 1]
        for t in knots:
            delta = np.abs(np.array(progress(t-1e-10, a, b))-progress(t+1e-10, a, b))
            joins.append({"a": a, "t": t, "value_d1_d2_d3_join_differences": delta.tolist()})
    checks = {"source_samples_match_independent_equations": all(c["scad_samples_max_error_mm"] < .0001 for c in cases),
              "C3_joins": all(max(j["value_d1_d2_d3_join_differences"]) < .001 for j in joins),
              "inner_angle_reduced": cases[1]["inner_max_angle_deg"] < cases[0]["inner_max_angle_deg"],
              "outer_angle_reduced": cases[1]["outer_max_angle_deg"] < cases[0]["outer_max_angle_deg"],
              "inner_slope_change_reduced": cases[1]["inner_max_abs_radius_second_derivative_per_mm"] < cases[0]["inner_max_abs_radius_second_derivative_per_mm"],
              "outer_slope_change_reduced": cases[1]["outer_max_abs_radius_second_derivative_per_mm"] < cases[0]["outer_max_abs_radius_second_derivative_per_mm"]}
    report = {"pass": all(checks.values()), "checks": checks, "cases": cases, "joins": joins,
              "limitation": "Independent equations checked against evaluated SCAD samples; no CFD, strength or manufacturing acceptance."}
    dump(smooth_release(5).out / "verification/curve-smoothness.json", report)
    print(json.dumps({k: v for k, v in report.items() if k != "joins"}, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

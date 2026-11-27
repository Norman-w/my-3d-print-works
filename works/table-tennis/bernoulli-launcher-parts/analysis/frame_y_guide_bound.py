#!/usr/bin/env python3
"""Conditional rail-pose comparison for the added public-frame Y adjustment.

This is a consequence of stated finite contact domains, not a whole-feeder
error certificate or a claim about measured printing accuracy.
"""
from fractions import Fraction as F
from pathlib import Path
import hashlib
import json
import math
import re

ROOT = Path(__file__).resolve().parents[1]
GRID = 10**12


def upper(v):
    return F(-((-v.numerator*GRID)//v.denominator), GRID)


def lower(v):
    return F((v.numerator*GRID)//v.denominator, GRID)


def sqrt_lower(v):
    return F(math.isqrt(v.numerator*GRID*GRID//v.denominator), GRID)


def sqrt_upper(v):
    q = sqrt_lower(v)
    return q if q*q == v else q+F(1, GRID)


def bound(gx, gy, ly):
    gx, gy, ly = map(lambda v: F(str(v)), (gx, gy, ly))
    lx = lower(4/(4+gx))
    lz = lower(4*lx/(4+gy))
    uzx = upper(gx/F('36.7'))
    uxz, uzy = sqrt_upper(1-lx*lx), F(1)
    for _ in range(25):
        d = 4+gy-4*lx
        uxy, uyz = upper(d/116), upper(d/ly)
        uyx = upper((uyz*uzx+uxy)/lz)
        uzy = min(uzy, upper(uxz*uyx+uyz))
        uxz = min(uxz, upper(uyx*uzy+uzx))
        lx = max(lx, sqrt_lower(1-uyx*uyx-uzx*uzx))
        lz = max(lz, sqrt_lower(1-uzx*uzx-uzy*uzy))
    ly_diag = sqrt_lower(1-uyx*uyx-uyz*uyz)
    return {'X_parallel_gap_mm': float(gx), 'Y_parallel_gap_mm': float(gy),
            'Y_station_separation_mm': float(ly),
            'matrix_abs_upper': {k: float(v) for k, v in
                dict(Rxy=uxy, Ryz=uyz, Ryx=uyx, Rzx=uzx, Rzy=uzy, Rxz=uxz).items()},
            'matrix_diagonal_lower': list(map(float, [lx, ly_diag, lz])),
            'axis_angle_upper_deg': math.degrees(math.acos(float((lx+ly_diag+lz-1)/2)))+1e-9}


def main():
    path = ROOT/'cad/feeder-frame-y-guide.scad'
    text = path.read_text()
    band = re.search(r'yg_bands\s*=\s*(\[\[.*?\]\]);', text)
    bands = json.loads(band.group(1))
    clearance = F(re.search(r'yg_pocket_clear\s*=\s*([\d.]+);', text).group(1))
    # Keep each fixed-Z station .01 mm inside both finite band footprints
    # for every allowed gib axial translation, rather than using the end face.
    z0 = F(str(bands[0][0]))+clearance+F('.01')
    z1 = F(str(bands[1][1]))-clearance-F('.01')
    assert z0 < F(str(bands[0][1]))-clearance
    assert z1 > F(str(bands[1][0]))+clearance
    rows = [bound(.1, .4, 40)]
    for gx, gy in [(.1, .1), (.05, .1), (.1, .05), (.05, .05)]:
        rows.append(bound(gx, gy, float(z1-z0)))
    a = math.radians(.5)
    old_height = 4/math.cos(a)+40*math.tan(a)
    new_height = 4/math.cos(a)+float(z1-z0)*math.tan(a)
    assert old_height < 4.4 and new_height > 4.1
    files = [path, ROOT/'cad/feeder-supports.scad', ROOT/'cad/feeder-cam-guide-revision.scad', Path(__file__)]
    result = {'status': 'CONDITIONAL_RAIL_POSE_COMPARISON_ONLY',
        'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        'common_Y_contact_station_Z_mm': [float(z0), float(z1)],
        'station_selection_scope': 'Parallel-gib pose with the stated axial translation; a pitched gib must independently retain both contact domains.',
        'necessary_inequalities': [
            '116*abs(Rxy)+4*Rxx+Ly*abs(Ryz) <= (4+gy)*Rzz',
            '4+36.7*abs(Rzx) <= (4+gx)*Rxx'],
        'conditions': [
            'Rigid orthogonal rail pose, Rxx>0, Rzz>0; both rails remain normally engaged.',
            'The transformed rail corners used at the two fixed Z stations lie inside the real upper and lower Y pads, including their finite X widths.',
            'Station selection directly covers parallel gibs only. The separate CAD differential-pitch clearance check is not a proof of contact-domain coverage here.',
            'The original X-guide station intersections at world Y22 remain inside the finite rail side faces and the real X contact bands.',
            'The actual rail is finite: the contact-domain and endpoint-phase checks must be maintained. This calculation does not replace them.',
            'gy is the maximum effective gap across all four Y bands after adjustment, including differential jack settings; gx has the analogous meaning.',
            'Displayed .1/.05 gaps are comparison inputs, not measured or guaranteed PETG capability.'],
        'rows': rows,
        'roll_control': {'angle_deg': .5, 'old_required_Y_height_mm': old_height,
                         'old_available_mm': 4.4, 'new_required_Y_height_mm': new_height,
                         'new_available_if_adjusted_gap_is_point1_mm': 4.1},
        'rounding': 'Rational operations rounded outward on a 1e-12 grid; displayed degree bound includes 1e-9 degree padding.',
        'whole_feeder_1mm_budget_proven': False, 'physical_acceptance': False}
    out = ROOT/'output/frame-y-guide-bound/report.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    for row in rows:
        print(row['X_parallel_gap_mm'], row['Y_parallel_gap_mm'], row['axis_angle_upper_deg'])


if __name__ == '__main__':
    main()

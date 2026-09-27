#!/usr/bin/env python3
"""Continuous plane consequences with finite patch re-entry, parallel host branch only."""
from pathlib import Path
from fractions import Fraction as Q
import hashlib
import json
import math
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'analysis'))
from frame_y_guide_bound import upper as up, lower as down, sqrt_lower as sl, sqrt_upper as su


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def q(v): return Q(str(v))
def conv(d):
    if isinstance(d, Q): return float(d)
    if isinstance(d, dict): return {k: conv(v) for k, v in d.items()}
    if isinstance(d, (list, tuple)): return [conv(v) for v in d]
    return d


def bound(gx, gy):
    gx, gy = q(gx), q(gy)
    lx, ly, a = q('36.7'), q('36.58'), q(56)
    # n_x=R*e_x, n_y=R*e_y; every n·(p-T) is a LOCAL coordinate.
    zx, xy, zy = up(gx/lx), up(gy/(2*a)), up(gy/ly)
    xx, yy = down(4/(4+gx)), down(4/(4+gy))
    for _ in range(30):
        zz = sl(1-zx*zx-zy*zy)
        yz = up(zx*xy+zy)  # cofactor Ryz=Rzx*Rxy-Rxx*Rzy
        yx = up((yz*zx+xy)/zz)
        xz = up(yx*zy+zx)
        xx = max(xx, sl(1-yx*yx-zx*zx))
        yy = max(yy, sl(1-xy*xy-zy*zy))
        zx = min(zx, up(((4+gx)-4)/lx))
        xy = min(xy, up(gy/(2*a)))
        zy = min(zy, up(gy/ly))
    # wX<=gx,wY<=gy are exact outer widths of inverse-translation constraints.
    wx, wy = gx, gy
    # Y-pad ray intersections: pX=+-56, pY in[20,24+gy], pZ=-33.29 or3.29.
    # The X-guide plane at pY22,pZ-15 eliminates T dot n_x.
    reentry_x = up(110*(1-xx)+(2+gy)*yx+q('18.29')*zx+wx)
    # X-guide rays: pY22, pX in[54,58+gx], pZ=-33.35 or3.35.
    # Averaging the four Y-pad stations eliminates their X and centred Z terms.
    reentry_y = up((58+gx)*xy+2*(1-yy)+q('18.35')*zy+wy)
    # Fixed stop at+5/-35, moving stop faces local+5/-55.
    phase = up(59*zx+25*zy+55*(1-zz))
    txp = up(54*(1-xx)+22*yx+15*zx+wx)
    typ = up(20*(1-yy)+15*zy+wy)
    tzp_lo = -up((phase+zx*txp+zy*typ)/zz)
    tzp_hi = up((20+phase+zx*txp+zy*typ)/zz)
    # Local rail Z at all ray intersections; common envelope of both ray sets.
    zlo = -up((58+gx)*xz+(24+gy)*yz+q('33.35')+tzp_hi)
    zhi = up((58+gx)*xz+(24+gy)*yz+q('3.35')-tzp_lo)
    xreserve = down(2-reentry_x)
    yreserve = down(2-reentry_y)
    zreserve = min(down(zlo+q('64.5')), down(16-zhi))
    # The two pure fixed-body planes have true teeth covering these points.
    tooth_x_reserve = q('1.6')   #56 within[54.2+dx,57.8+dx], dx in[-.2,.2]
    tooth_z_reserve = q('.01')  # stations .01 inside all dz-shifted teeth
    # Body-stop corner strips remain outside the channel. This uses full
    # rigid transforms T=R*T', with Tz represented above, not Tx=Ty=0.
    tx = up(txp+xy*typ+xz*max(-tzp_lo,tzp_hi))
    ty = up(yx*txp+typ+yz*max(-tzp_lo,tzp_hi))
    stop_x_error = up(59*(1-xx)+25*xy+55*xz+tx)
    stop_y_error = up(59*yx+25*(1-yy)+55*yz+ty)
    # Corresponding corners x53/59 vs nominal open channel[53.8,58.2];
    # y19/25 vs outside fixed solid envelope[17.5,35.5].
    stop_strip_reserve = down(q('.8')-stop_x_error)
    stop_outer_y_reserve = down(q('1.5')-stop_y_error)
    # End windows in the current CG wrapper reach X>=57.8, Y20.8..24.2.
    # Both Y19/25 stop corners stay outside these internal cutouts too.
    stop_window_y_reserve = down(q('.8')-stop_y_error)
    assert min(xreserve,yreserve,zreserve,stop_strip_reserve,stop_outer_y_reserve,
               stop_window_y_reserve)>0
    return {
        'parallel_effective_gaps_mm': [gx, gy],
        'matrix_abs_upper': dict(Rxy=xy,Rxz=xz,Ryx=yx,Ryz=yz,Rzx=zx,Rzy=zy),
        'matrix_diagonal_lower': [xx,yy,zz],
        'axis_angle_upper_deg_diagnostic': math.degrees(math.acos(float((xx+yy+zz-1)/2)))+1e-9,
        'finite_Y_ray_rail_X_deviation_upper_mm': reentry_x,
        'finite_X_ray_rail_Y_deviation_upper_mm': reentry_y,
        'moving_rail_XY_reentry_reserve_mm': [xreserve,yreserve],
        'moving_rail_local_Z_outer_mm': [zlo,zhi],
        'moving_rail_Z_reserve_mm': zreserve,
        'fixed_Y_tooth_XZ_station_reserve_mm': [tooth_x_reserve,tooth_z_reserve],
        'stop_phase_abs_upper_mm': phase,
        'inverse_translation_abs_upper_XY_mm': [txp,typ],
        'inverse_translation_Z_outer_mm': [tzp_lo,tzp_hi],
        'stop_corner_XY_error_upper_mm': [stop_x_error,stop_y_error],
        'stop_corner_fixed_strip_reserve_XY_mm': [stop_strip_reserve,stop_outer_y_reserve],
        'stop_corner_internal_window_Y_reserve_mm': stop_window_y_reserve,
        'finite_patch_reentry_passed_on_declared_branch': True,
    }


def main():
    files = ['cad/parameters.scad','cad/cam-study.scad','cad/feeder-supports.scad',
             'cad/feeder-frame-y-guide.scad','cad/feeder-cam-guide-revision.scad',
             'analysis/frame_y_guide_bound.py',str(Path(__file__).relative_to(ROOT))]
    before = {name: sha(ROOT/name) for name in files}
    # Lock the CAD identities to the just-reviewed full current-source report.
    current = json.loads((ROOT/'output/current-joint-tolerance/report.json').read_text())
    for name in files[:-1]:
        assert current['source_hashes'][name] == before[name], name
    for name,digest in current['source_hashes'].items():
        assert sha(ROOT/name)==digest,name
        before[name]=digest
    yg = (ROOT/'cad/feeder-frame-y-guide.scad').read_text()
    cg = (ROOT/'cad/feeder-cam-guide-revision.scad').read_text()
    assert 'yg_tooth_x=[54.2,57.8]' in yg
    assert 'yg_bands=[[-33.5,-27.5],[-2.5,3.5]]' in yg
    assert 'yg_pocket_clear=.2' in yg and 'yg_datum_x=[53.5,58.5]' in yg
    assert 'cg_contact_y0=21' in cg and 'cg_end_recess=.4' in cg
    rows = [bound(.1,.1),bound(.05,.05)]
    result = {
        'status':'FINITE_RAIL_CONTACT_REENTRY_PROVED_FOR_PARALLEL_REGISTERED_HOST_BRANCH_ONLY',
        'source_sha256':before,
        'joint_report_sha256':sha(ROOT/'output/current-joint-tolerance/report.json'),
        'coordinates':'R maps rail-local to world; T is its origin. Two supports share a registered parallel datum in this comparison, not assumed in the real full assembly.',
        'old_corner_coverage_check': {
            'rail_local_outer_X': [54,58], 'upper_tooth_X':[54.2,57.8],
            'outer_X_corners_covered_even_at_identity': False,
            'meaning':'The earlier116-span corner antecedent is not satisfied by these upper teeth at identity. Its conditional result was not a current whole-assembly certificate.',
        },
        'new_world_stations': {'Y_planes_X':[-56,56],'Y_planes_Z':[-33.29,3.29],
                              'X_planes_Y':22,'X_planes_Z':[-33.35,3.35]},
        'necessary_plane_inequalities':[
            '4 + 36.7 abs(Rzx) <= (4+gx) Rxx',
            '4 + 112 abs(Rxy) + 36.58 abs(Rzy) <= (4+gy) Ryy'],
        'proof_chain':[
            'Y normal n_y=R e_y. At fixed world X,Z the two rail Y faces differ by4/Ryy; their ray centres range by(112|Rxy|+36.58|Rzy|)/Ryy.',
            'X normal n_x=R e_x. Fixed Y22 and two Z stations give thickness4/Rxx and centre variation36.7|Rzx|/Rxx.',
            'Orthogonality and cofactors bound all six off-diagonal entries with outward rational arithmetic; no sampled angle extrema.',
            'X-guide translation interval eliminates n_x dot T from the Y-ray local X; Y-plane mean eliminates n_y dot T from X-ray local Y.',
            'The hard stop corner strips give the displayed origin phase bound; their world XY inclusion is checked by the same resulting interval.',
            'Inverse translation and the phase bound put all rays back in actual rail X,Y,Z extents with positive reserves. Actual fixed teeth cover chosen stations including their±.2 pure translations.',
            'First-exit argument on the collision-free connected component containing the nominal assembled rail: until an exit from the finite station/stop domains the plane consequences hold; their strictly positive re-entry reserves contradict such a first exit. Starting disconnected or escaped poses are excluded, not proved impossible.',
            'No claim is made about differential gib pitch, independently registered supports, form/load errors or actual adjusted gap.'
        ],
        'conditions':[
            'Both support datums are aligned in this common comparison frame, with no independent body/support registration error.',
            'Gibs are parallel (pitch0), with their declared pure X/Z float; effective gaps gx/gy are upper bounds on the four actual bands.',
            'Collision-free continuous component containing the nominal assembled rail between its real guide and stop faces, Rxx,Ryy,Rzz positive; disconnected/escaped poses are not covered.',
            'Rigid nominal geometry with no missing/warped band material. Real gap, form and loaded behaviour remain unmeasured.'
        ],
        'rows':rows,
        'whole_D02_domain_certified':False,'manufacturing_release':False,'physical_acceptance':False,
        'source_stable': all(sha(ROOT/n)==h for n,h in before.items()),
    }
    assert result['source_stable']
    (OUT/'report.json').write_text(json.dumps(conv(result),ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(conv({'status':result['status'],'rows':rows}),ensure_ascii=False,indent=2))


if __name__=='__main__': main()

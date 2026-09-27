#!/usr/bin/env python3
"""Whole-stroke CONDITIONAL bounds, not an as-built/current-play certificate.

No optimization or sampled poses. Actual source provides the slot graph, V
contact span, shoulder/window locations and dimensions. Missing pose/shape/load
limits remain explicit required inputs, never silently set to zero.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import re
from fractions import Fraction
from pin_v_seat_error import load as load_v

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/final-gate-error-bound'


def literal(path, key):
    rows = re.findall(r'^\s*' + re.escape(key) + r'\s*=\s*([-+\d.]+)\s*;', path.read_text(), re.M)
    assert len(rows) == 1, key
    return float(rows[0])


def parameters():
    p, hashes = load_v()
    paths = {name: ROOT / 'cad' / name for name in
             ['parameters.scad', 'feeder-supports.scad', 'cam-study.scad', 'feeder-body.scad']}
    p['slot_half_gap'] = literal(paths['parameters.scad'], 'radial_print_clearance')
    p['fixed_front_y'] = literal(paths['feeder-supports.scad'], 'support_radial_y1')
    p['slot_radius'] = p['cam_pin_d']/2 + p['slot_half_gap']
    p['slope'] = (p['finger_open_center_r']-p['finger_closed_center_r']) / (
        p['cam_stroke']*(1-p['gate_overlap_fraction'])/2)
    p['v_mid_y'] = (p['ps_seat_y0']+p['ps_seat_y1'])/2
    p['v_half_span'] = (p['ps_seat_y1']-p['ps_seat_y0'])/2
    support = re.sub(r'\s+', '', paths['feeder-supports.scad'].read_text())
    assert 'z-cam_slot_d/2' in support and '+cam_slot_d/2+support_eps,20,cam_slot_d' in support
    cam = re.sub(r'\s+', '', paths['cam-study.scad'].read_text())
    assert 'modulecam_slot(side,rear)' in cam and 'hull(){' in cam
    assert '*cam_clamp(t/cam_closing_end,0,1)' in cam
    assert '*cam_clamp((t-cam_opening_start)/cam_closing_end,0,1)' in cam
    p['graph_domain_note'] = 'Each gate graph has slopes between 0 and +/-m; constant continuation outside end caps is an outer envelope.'
    return p, hashes


def frame_contact_review():
    """Necessary bounds on the normally engaged rigid-rail branch.

    Exact rational operations with outward 1e-12 rounding. This is NOT the
    missing whole-assembly/contact proof: phase, carrier and pin are separate.
    The finite rail re-entry test is explicit; no infinitely long rail is used.
    """
    S=10**12
    def F(x):return Fraction(str(x))
    def up(x):return Fraction(-((-x.numerator*S)//x.denominator),S)
    def down(x):return Fraction((x.numerator*S)//x.denominator,S)
    def sqrt_down(x):return Fraction(math.isqrt((x.numerator*S*S)//x.denominator),S)
    def sqrt_up(x):
        q=sqrt_down(x)
        return q if q*q==x else q+Fraction(1,S)
    source=ROOT/'cad/feeder-supports.scad'
    values={k:literal(source,k) for k in ['support_rail_x0','support_rail_x1',
        'support_rail_y0','support_rail_y1','support_guide_z0','support_guide_z1',
        'support_axial_clearance']}
    cg=ROOT/'cad/feeder-cam-guide-revision.scad'
    recess=literal(cg,'cg_end_recess');float_z=literal(cg,'cg_pocket_gap')
    assert values=={'support_rail_x0':54.,'support_rail_x1':58.,
        'support_rail_y0':20.,'support_rail_y1':24.,'support_guide_z0':-35.,
        'support_guide_z1':5.,'support_axial_clearance':.2}
    assert recess==.4 and float_z==.2
    rows=[]
    for gap in [.10,.05,.02]:
        g=F(gap);Lxx=down(4/(4+g));Lzz=down(4*Lxx/F(4.4))
        Uzx=up(g/F(36.7));Uxz=sqrt_up(1-Lxx*Lxx);Uzy=F(1)
        for _ in range(20):
            d=F(4.4)-4*Lxx
            Uxy=up(d/116);Uyz=up(d/40)
            Uyx=up((Uyz*Uzx+Uxy)/Lzz)
            Uzy=min(Uzy,up(Uxz*Uyx+Uyz))
            Uxz=min(Uxz,up(Uyx*Uzy+Uzx))
            Lxx=max(Lxx,sqrt_down(1-Uyx*Uyx-Uzx*Uzx))
            Lzz=max(Lzz,sqrt_down(1-Uzx*Uzx-Uzy*Uzy))
        Lyy=sqrt_down(1-Uyx*Uyx-Uyz*Uyz)
        # These finite intersections are back-substituted at all corners of
        # x[-58,58], y[20,24], Z[-35,5], origin translation u[0,20].
        phase=up(59*Uzx+25*Uzy+55*(1-Lzz))
        zlo=-up((55+58*Uzx+24*Uzy+phase)/Lzz)
        zhi=up((5+58*Uzx+24*Uzy+phase)/Lzz)
        bdev=max(1-Lxx,up(1/Lzz)-1)
        fy=up(F(.2)+16*bdev)
        fx=up(g+F(102.25)*(up(1/Lxx)-1)+(14+fy)*Uyx/Lxx)
        fz=up(F(48.25)*Uzx+13*Uzy+F(50.75)*(1-Lzz))
        rows.append({'parallel_X_gap_mm':gap,
          'rounding':'Outward rational 1e-12 grid; no random pose or optimizer.',
          'rotation_matrix_abs_upper':{k:float(v) for k,v in dict(Rxy=Uxy,Ryz=Uyz,
              Ryx=Uyx,Rzx=Uzx,Rzy=Uzy,Rxz=Uxz).items()},
          'rotation_matrix_diagonal_lower':{k:float(v)for k,v in dict(Rxx=Lxx,Ryy=Lyy,Rzz=Lzz).items()},
          'rotation_angle_upper_deg':math.degrees(math.acos(float((Lxx+Lyy+Lzz-1)/2))),
          'finite_rail_local_z_interval_mm':[float(zlo),float(zhi)],
          'finite_rail_material_z_interval_mm':[-64.5,16],
          'finite_rail_end_reserve_mm':min(float(zlo)+64.5,16-float(zhi)),
          'cam_field_upper_WITH_CONTACT_DOMAIN_CONDITIONS_mm':{'X':float(fx),'Y':float(fy),
              'Z_relative_to_actual_origin_u':float(fz)},
          'X_field_domain_world_z_mm':[-33.35,3.35],
          'X_field_domain_note':'Only material/contact points between these stations. Points outside require affine extrapolation; this number is not automatically the whole-slot field used by evaluate().',
          'separate_endpoint_stop_phase_allowance_mm':float(phase),
          'phase_warning':'The Z field uses actual origin u. A mechanical rest-stop datum adds a separate phase term; it is not automatically zero.',
          'scope':'Necessary-plane consequence for the normal fully engaged branch only. Does not certify carrier/pin constraints, manufacturing, loads or a whole-mechanism upper bound.'})
    return {'actual_fixed_Y_gap_mm':.4,'actual_moving_rail_length_mm':80.5,
       'fixed_Y_guide_length_mm':40,'X_contact_stations_world_z_mm':[-33.35,3.35],
       'X_gib_axial_float_mm':[-.2,.2],'X_gib_end_recess_mm':.4,
       'necessary_inequalities':[
        '116*abs(Rxy)+4*Rxx+40*abs(Ryz) <= 4.4*Rzz',
        '4+36.7*abs(Rzx) <= (4+g)*Rxx'],
       'conditions':['R maps local to world, det(R)=1, Rxx>0 and Rzz>0.',
        'Both real rails remain inside both closed Y guides and the two actual X contact bands; this is the normal assembled branch, not an arbitrary disconnected pose.',
        'For the first inequality, every fixed-Z corner maps back into the finite moving rail; the report gives that back-substitution interval.',
        'For the second inequality, plane intersections at world Y=22 and both listed Z stations lie inside the actual side-face rectangles, not infinite slabs.',
        'Contact-domain membership and frame phase still need to be carried into a full assembly interval proof; the matrix bound alone is not that proof.'],
       'rail_only_roll_example':{
         'angle_deg':.5,
         'fixed_Z_section_required_Y_height_mm':4/math.cos(math.radians(.5))+40*math.tan(math.radians(.5)),
         'available_Y_height_mm':4.4,
         'cam_near_plane_Z_shift_at_local_z_minus15_mm':-14*math.sin(math.radians(.5)),
         'explanation':'Rigid rotation about X through (Y22,Z-15) retains X guide planes exactly and fits both Y rail channels. This is a rail-subassembly pose, not a verified whole-mechanism witness.'},
       'rows':rows}


def validate(c):
    for k, v in c.items():
        if isinstance(v, (float, int)):
            assert math.isfinite(v) and v >= 0, k
    assert c['radius_error'] < 2
    assert max(c['carrier_rotation_deg'], c['pin_world_inclination_deg'],
               c['pin_relative_inclination_deg'], c['v_normal_angle_deg']) < 10


def evaluate(p, c):
    validate(c)
    m = p['slope']; r = p['cam_pin_d']/2; rho = c['radius_error']
    theta = math.atan(m); half = theta/2
    carrier = math.radians(c['carrier_rotation_deg'])
    pin = math.radians(c['pin_world_inclination_deg'])
    rel = math.radians(c['pin_relative_inclination_deg'])
    alpha = math.radians(c['v_normal_angle_deg'])
    # A tilted circular-cylinder section contains a disk of radius r_min.
    # Rotating the entire Lipschitz graph by its half-angle gives slopes +/-K.
    # Applying the disk extreme point bound in that frame and rotating back
    # covers the rounded joins and end caps as well as the straight segments.
    slot_r = p['slot_radius'] + c['slot_outward_shape_error']
    r_min = r-rho
    slot = (slot_r-r_min*math.cos(half))*math.sqrt(1+m*m)
    straight_only = (slot_r-r_min)*math.sqrt(1+m*m)
    # Contact may occur at DIFFERENT Y stations on the two finite V faces.
    # Bound their mid-plane line offsets, including a tilted cylinder's support
    # radius, then perturb the actual 2x2 normal matrix in operator norm.
    e = c['v_face_normal_error']
    finite_contact = p['v_half_span']*math.tan(rel)
    tilted_radius = (r+rho)*(1/math.cos(rel)-1)
    b = e+rho+finite_contact+tilted_radius
    eps = 2*math.sqrt(2)*math.sin(alpha/2)
    seat = (math.sqrt(2)*b + eps*math.sqrt(2)*r)/(1-eps)
    # All pose bounds cover the WHOLE actual slot solid, not qX at the frame
    # origin. Take a FIXED WORLD-Y plane through the plate's nominal middle.
    # An oblique cam face is not a fixed-Y cylinder section: silently using a
    # full disk there would be invalid. The two actual outer faces must straddle
    # this plane over the pin footprint, guaranteed by fy < thickness/2 plus
    # the explicit fully-engaged material/contact-domain requirement.
    fx = c['frame_x_play']+c['frame_x_manufacturing']
    fy = c['frame_y_play']+c['frame_y_manufacturing']
    fz = c['frame_z_play']+c['frame_z_manufacturing']
    cy = c['carrier_y_play']+c['carrier_y_manufacturing']
    a = p['cam_follower_offset']; y = p['v_mid_y']
    # |Ryx| <= sin(angle), Ryy >= cos(angle); the V-center error has norm <=seat.
    seat_y_lower = -cy-a*math.sin(carrier)+y*math.cos(carrier)-seat
    sample_y = p['cam_plate_y']+p['cam_plate_thickness']/2
    assert fy<p['cam_plate_thickness']/2, 'Fixed world-Y section is not inside the plate.'
    pin_lever = max(0, sample_y-seat_y_lower)
    fixed_lever = max(0, p['fixed_front_y']-seat_y_lower)
    fixed_gap = (p['slot_half_gap']+rho+c['fixed_window_center_error']
                 +c['fixed_window_outward_shape_error'])
    pin_z_section = fixed_gap+max(0, sample_y-p['fixed_front_y'])*math.tan(pin)
    rotation_x = a*(1-math.cos(carrier))+y*math.sin(carrier)
    transfer_x = rotation_x+seat+pin_lever*math.tan(pin)
    # A varying frame/material-point error is an outer rectangle about the
    # nominal slot, NOT a single uniform X translation. In the half-angle
    # proof its Fx coefficient is sqrt(1+m^2), and its Fz coefficient is m.
    # Using coefficient 1 for Fx here would understate this conditional bound.
    frame_x = math.sqrt(1+m*m)*fx
    x = slot+frame_x+m*(pin_z_section+fz)+transfer_x+c['loaded_tip_x_deflection']
    z = (fixed_gap+math.hypot(a,y)*math.sin(carrier)+seat
         +fixed_lever*math.tan(pin)+c['loaded_tip_z_deflection'])
    return {'x_upper_mm': x, 'z_upper_mm': z, 'both_within_1mm_if_all_conditions_hold': max(x,z)<=1,
        'terms_x_mm': {'whole_stroke_slot': slot, 'cam_x_pose_field_with_strip_factor': frame_x,
            'fixed_window_to_section_pin_z_times_slope': m*pin_z_section,
            'cam_z_pose_field_times_slope': m*fz, 'carrier_rotation': rotation_x,
            'finite_V_midplane_center': seat, 'pin_axis_extension': pin_lever*math.tan(pin),
            'loaded_tip_deflection': c['loaded_tip_x_deflection']},
        'terms_z_mm': {'fixed_window': fixed_gap,
            'carrier_rotation': math.hypot(a,y)*math.sin(carrier),
            'finite_V_midplane_center': seat, 'pin_axis_extension': fixed_lever*math.tan(pin),
            'loaded_tip_deflection': c['loaded_tip_z_deflection']},
        'diagnostics': {'straight_slot_only_bound_NOT_whole_stroke': straight_only,
            'slot_turn_extra': slot-straight_only, 'finite_V_contact_offset_per_face': finite_contact,
            'tilted_pin_radius_increase': tilted_radius, 'V_normal_matrix_perturbation': eps,
            'seat_y_lower': seat_y_lower, 'pin_extension_max': pin_lever,
            'fixed_world_y_sample': sample_y, 'remaining_x': 1-x, 'remaining_z': 1-z},
        'bound_kind': 'Analytic sufficient bound conditional on listed pose/contact/manufacturing/load envelopes; NOT measured or CAD-certified play.'}


def max_v_error(p,c):
    lo,hi=0.,.5
    if max(evaluate(p,{**c,'v_face_normal_error':0})[k] for k in ['x_upper_mm','z_upper_mm'])>1:
        return None
    for _ in range(64):
        mid=(lo+hi)/2
        r=evaluate(p,{**c,'v_face_normal_error':mid})
        if max(r['x_upper_mm'],r['z_upper_mm'])<=1:lo=mid
        else:hi=mid
    return lo


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--inputs',type=Path)
    args=parser.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    p,hashes=parameters()
    broad={'frame_x_play':.10,'frame_z_play':.20,'frame_y_play':.20,
        'frame_x_manufacturing':.01,'frame_z_manufacturing':.01,'frame_y_manufacturing':.02,
        'carrier_y_play':.10,'carrier_y_manufacturing':.05,'carrier_rotation_deg':1.,
        'pin_world_inclination_deg':.5,'pin_relative_inclination_deg':.1,
        'v_face_normal_error':.10,'v_normal_angle_deg':.1,'radius_error':.005,
        'slot_outward_shape_error':.02,'fixed_window_center_error':.02,
        'fixed_window_outward_shape_error':.02,'loaded_tip_x_deflection':.02,
        'loaded_tip_z_deflection':.02}
    target={**broad,'frame_x_play':.05,'frame_z_play':.11,
            'carrier_rotation_deg':.75,'pin_world_inclination_deg':.25}
    if args.inputs:
        supplied=json.loads(args.inputs.read_text())
        assert set(supplied)==set(target),'Every input must be supplied explicitly; no hidden defaults.'
        cases={'external_input':supplied}
    else:
        cases={'looser_review_allocation_NOT_actual_play':broad,
               'tighter_review_allocation_NOT_proven_achievable':target}
    rows=[]
    for name,c in cases.items():
        result=evaluate(p,c)
        nominal={k:(0. if k in ['frame_x_manufacturing','frame_z_manufacturing','frame_y_manufacturing',
          'carrier_y_manufacturing','v_face_normal_error','v_normal_angle_deg','radius_error',
          'slot_outward_shape_error','fixed_window_center_error','fixed_window_outward_shape_error',
          'loaded_tip_x_deflection','loaded_tip_z_deflection'] else v) for k,v in c.items()}
        table=[{'V_face_design_error_mm':e,**evaluate(p,{**c,'v_face_normal_error':e})}
               for e in [0,.05,.10,.15,.20]]
        rows.append({'name':name,'input_envelopes':c,'result':result,'face_error_table':table,
            'zero_manufacturing_reference_same_pose_requirements':evaluate(p,nominal),
            'maximum_V_face_error_if_all_other_requirements_hold_mm':max_v_error(p,c)})
    checks=[]
    # Identity checks of the all-stroke slot bound, including a zero-turn case.
    assert abs((p['slot_radius']-p['cam_pin_d']/2)-p['slot_half_gap'])<1e-12
    for m in [0,.1,p['slope'],1]:
        theta=math.atan(m);K=math.tan(theta/2)
        direct=(p['slot_radius']-p['cam_pin_d']/2*math.cos(theta/2))*math.sqrt(1+m*m)
        rotated=(p['slot_radius']*math.sqrt(1+K*K)-p['cam_pin_d']/2)*(math.cos(theta/2)+m*math.sin(theta/2))
        checks.append(abs(direct-rotated));assert checks[-1]<1e-12
        h=theta/2;gain=math.cos(h)+m*math.sin(h)
        assert abs((math.cos(h)+K*math.sin(h))*gain-math.sqrt(1+m*m))<1e-12
        assert abs((math.sin(h)+K*math.cos(h))*gain-m)<1e-12
    stable=all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in hashes.items())
    report={'status':'WHOLE_STROKE_CONDITIONAL_BOUND_WITH_EXPLICIT_OPEN_INPUTS',
      'source_sha256':hashes,'sources_stable':stable,
      'analysis_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      'parameter_snapshot':p,'cases':rows,'identity_check_max_residual':max(checks),
      'actual_frame_contact_review':frame_contact_review(),
      'current_CAD_unqualified_upper_bound_mm':None,'current_assembly_budget_passed':False,
      'actual_measured_inputs':False,'physical_acceptance':False,
      'conditions':['Four followers, both mirrors, every u in [0,20]; arbitrary pose variation only within the declared envelopes.',
        'Frame component bounds apply to every material point throughout both slot contact domains, including phase error; NOT qX at the origin.',
        'Fixed world Y=10.5 intersects the full pin footprint inside the cam thickness; both outer faces straddle it. This is not an oblique cam-face disk approximation.',
        'Pin shoulder remains cylindrical across the fixed +Y window face and world-Y sample plane; pin must remain inside the existing fixed window X interval.',
        'Both V faces remain loaded at cylindrical contacts inside Y1.75..4.5; shoulder axial seating persists; no block hard-stop force bypass.',
        'Finite-V normal/position errors are referenced to its nominal apex; relative pin inclination and face-normal angle bounds must be verified.',
        'Carrier rigid rotation is the full axis-angle norm; pin world inclination is relative to fixed Y. These bounds are requirements, not inferred from nominal slit widths.',
        'Deflection, frictional seating loss, screw loosening and wear must fit the separate load allowance or invalidate the bound.'],
      'open_geometry_proof':['Actual frame contact inequalities and finite rail back-substitution are provided; their contact-domain/phase conditions and the V-ear carrier domains are not a completed whole-assembly interval proof.',
        'Current fixed axial-guide Y play permits roll; X gib adjustment alone cannot enforce all cam-Z/pin-inclination targets.',
        'No catalog shoulder radius tolerance or physical PETG face/angle/preload data was invented.'],
      'interpretation':'A bound greater than 1 is failure to certify that input box, NOT proof of a feasible >1 counterexample. A smaller conditional bound is not an as-built pass.'}
    (OUT/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    for row in rows:print(row['name'],row['result']['x_upper_mm'],row['result']['z_upper_mm'],
                         'maxE',row['maximum_V_face_error_if_all_other_requirements_hold_mm'])
    print('source stable',stable,'CURRENT_ASSEMBLY_PASS=false')
    return 0 if stable else 1


if __name__=='__main__':raise SystemExit(main())

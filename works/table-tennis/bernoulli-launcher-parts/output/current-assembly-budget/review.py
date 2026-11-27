#!/usr/bin/env python3
"""Current-source, conditional feeder budget. No CAD edits or native reruns.

Run with the bundled FreeCAD Python or ordinary Python 3. All results stay in
this directory. Existing analysis mains/reports are never executed/overwritten.
"""
from pathlib import Path
import hashlib, json, math, re, sys
from datetime import datetime, timezone

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT/'analysis'))
from gate_geometry import read_parameters
from frame_y_guide_bound import bound as frame_bound
from final_gate_error_bound import parameters as transfer_parameters, evaluate
from pin_v_seat_error import load as load_v

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def literal(path,key):
    hits=re.findall(r'^\s*'+re.escape(key)+r'\s*=\s*([-+\d.]+)\s*;', (ROOT/path).read_text(), re.M)
    assert len(hits)==1,(path,key)
    return float(hits[0])
def ref(path,needle):
    lines=(ROOT/path).read_text().splitlines()
    hits=[i+1 for i,s in enumerate(lines) if needle in s]
    assert hits,(path,needle)
    return {'path':path,'line':hits[0],'matching_text':lines[hits[0]-1]}
def bisect(f,lo,hi,n=80):
    assert f(lo)*f(hi)<=0
    for _ in range(n):
        mid=(lo+hi)/2
        if f(lo)*f(mid)<=0:hi=mid
        else:lo=mid
    return (lo+hi)/2

p,_=read_parameters(ROOT/'cad/parameters.scad')
v,vhash=load_v()
st=ROOT/'cad/feeder-supports.scad'
param_sources={k:ref('cad/parameters.scad',k+' =') for k in [
    'ball_min_d','ball_max_d','guide_id','guide_od','guide_start_z','guide_length',
    'guide_clearance_budget','gate_position_budget','finger_tip_radius',
    'finger_closed_center_r','finger_open_center_r','gate_spacing','cam_stroke',
    'gate_overlap_fraction','radial_print_clearance']}
c,o,L=p['finger_closed_center_r'],p['finger_open_center_r'],p['gate_spacing']
Rlo,Rhi=p['ball_min_d']/2,p['ball_max_d']/2
A=p['guide_id']/2+p['guide_clearance_budget']
tip=p['finger_tip_radius'];h=tip+p['radial_print_clearance']
u_close=p['cam_stroke']*(1-p['gate_overlap_fraction'])/2
u_open=p['cam_stroke']-u_close
m=(o-c)/u_close
ecc=lambda r:math.sqrt(A*A-h*h)-math.sqrt(r*r-h*h)
E=ecc(Rlo);pitch=math.sqrt((2*Rlo)**2-(2*E)**2)

# Contract checking: current half-shell wrapping preserves the cylindrical
# guide and uses the same four round radial holes, not the old animation alone.
checks={
 'body_round_holes':'cylinder(h=120,r=finger_tip_radius+radial_print_clearance);' in (ROOT/'cad/feeder-body.scad').read_text(),
 'body_main_bore':'body_tube(guide_start_z,guide_length,guide_od,guide_id);' in (ROOT/'cad/feeder-body.scad').read_text(),
 'adopted_y_guides':'yg_caps();yg_gibs();' in (ROOT/'cad/launcher-final-assembly.scad').read_text(),
 'adopted_v_carriers':'ps_carriers(t);ps_blocks(t);' in (ROOT/'cad/launcher-final-assembly.scad').read_text(),
 'new_direct_law':'fixed-guide-direct-pull-v2' in (ROOT/'cad/cable-trigger-input.scad').read_text(),
 'positive_output_stops':'support_guide_z0-cam_stroke-support_stop_thickness' in st.read_text(),
}
assert all(checks.values())

def gate(bx,bz,by=0.,tip_min=tip):
    # tip_min is used for guaranteed blocking/depth; full nominal radius for
    # collision/clearance. By is a separate finger-centre transverse envelope.
    hmin2=(Rlo+tip_min)**2-(c+bx)**2-(E+by)**2
    hmin=math.sqrt(max(0,hmin2))
    hmax=max(math.sqrt((r+tip)**2-(c-bx-ecc(r))**2) for r in [Rlo,Rhi])
    lower=2*hmax+2*bz
    upper=hmin+pitch-hmax-2*bz
    block=math.sqrt(max(0,(Rlo+tip_min)**2-(E+by)**2))-bx
    release=u_open+(Rlo+tip+E+bx-c)/m
    rear_block=(o-block)/m
    front_block=u_open+(block-c)/m
    return dict(Bx=bx,Bz=bz,By=by,tip_min_mm=tip_min,
       Hmin_mm=hmin,Hmax_mm=hmax,minimum_ball_pitch_mm=pitch,
       allowed_nominal_gate_spacing_mm=[lower,upper],
       lower_spacing_margin_mm=L-lower,upper_spacing_margin_mm=upper-L,
       max_Bz_for_this_Bx_By_mm=min(L-2*hmax,hmin+pitch-hmax-L)/2,
       closed_radial_margin_mm=block-c,
       fully_open_radial_margin_mm=o-bx-Rlo-tip-E,
       release_requires_u_strictly_greater_mm=release,
       rest_rear_fully_open_requires_u_strictly_less_mm=p['cam_stroke']-release,
       both_guaranteed_blocking_u_interval_mm=[rear_block,front_block],
       both_guaranteed_blocking_width_mm=front_block-rear_block,
       sufficient_static_spacing_pass=hmin2>0 and lower<L<upper and block>c)

rows=[gate(b,1) for b in [0,.25,.5,.75,1,1.1,1.2]]
base=gate(1,1)
maxbx=bisect(lambda b:min(gate(b,1)['lower_spacing_margin_mm'],gate(b,1)['upper_spacing_margin_mm']),1,1.2)
by_max=bisect(lambda by:gate(1,1,by)['upper_spacing_margin_mm'],0,2)

# Read actual already-exported tip facets; this diagnoses ideal-sphere vs CAD
# polygon modelling. Numeric padding below is mesh-reading allowance, not FDM.
exp_rel='output/cable-scene-export/20260927T091627124663Z/report.json'
exp=json.loads((ROOT/exp_rel).read_text())
finger=next(r for r in exp['parts'] if r['id']=='feeder/finger-right-front')
fp=ROOT/'output/cable-scene-export/20260927T091627124663Z/feeder__finger-right-front.stl'
assert sha(fp)==finger['sha256']
verts=[tuple(map(float,x))for x in re.findall(r'^\s*vertex\s+(\S+)\s+(\S+)\s+(\S+)',fp.read_text(),re.M)]
dist=[]
for i in range(0,len(verts),3):
    tri=[(a[0]-c,a[1],a[2])for a in verts[i:i+3]]
    if all(abs(sum(q*q for q in a)-tip*tip)<1e-4 and a[0]<=1e-6 for a in tri):
        a,b,d=tri;u=[b[j]-a[j]for j in range(3)];w=[d[j]-a[j]for j in range(3)]
        n=[u[1]*w[2]-u[2]*w[1],u[2]*w[0]-u[0]*w[2],u[0]*w[1]-u[1]*w[0]]
        nn=math.sqrt(sum(z*z for z in n))
        if nn:dist.append(abs(sum(n[j]*a[j]for j in range(3)))/nn)
assert dist and min(dist)>2.4845
faceted=gate(1,1,.1,2.4845)

# Current actual settings (nominal parallel pose only); no process accuracy is
# inferred from them. Both admissible positive/negative compensation are shown.
assert 'cg_front_retracted=support_rail_x1+cg_travel;' in (ROOT/'cad/feeder-cam-guide-revision.scad').read_text()
gx=literal('cad/feeder-cam-guide-revision.scad','cg_travel')-literal('cad/feeder-cam-guide-revision.scad','cg_setting')
gy=literal('cad/feeder-frame-y-guide.scad','yg_face')-24
cygap=4.5-(literal('cad/feeder-guide-revision.scad','revision_front_retracted')+literal('cad/feeder-guide-revision.scad','revision_setting'))-9
assert abs(gx-.1)<1e-10 and abs(gy-.1)<1e-10 and abs(cygap-.1)<1e-10
frows=[]
for xgap,ygap in [(.1,.1),(.05,.1),(.1,.05),(.05,.05)]:
    r=frame_bound(xgap,ygap,36.58)
    a=r['matrix_abs_upper'];zz=r['matrix_diagonal_lower'][2]
    r['rest_stop_phase_abs_upper_if_contact_conditions_hold_mm']=59*a['Rzx']+25*a['Rzy']+5*(1-zz)
    r['full_stop_phase_abs_upper_if_contact_conditions_hold_mm']=59*a['Rzx']+25*a['Rzy']+55*(1-zz)
    r['stop_span_abs_error_upper_if_poses_independent_mm']=r['rest_stop_phase_abs_upper_if_contact_conditions_hold_mm']+r['full_stop_phase_abs_upper_if_contact_conditions_hold_mm']
    frows.append(r)

# The inherited transfer evaluator is source checked and algebraically useful,
# but none of its pose fields becomes measured by calling it. Expose the actual
# affordable error inequalities rather than retuning an arbitrary box to pass.
tp,_=transfer_parameters()
zero={k:0. for k in ['frame_x_play','frame_z_play','frame_y_play','frame_x_manufacturing',
 'frame_z_manufacturing','frame_y_manufacturing','carrier_y_play','carrier_y_manufacturing',
 'carrier_rotation_deg','pin_world_inclination_deg','pin_relative_inclination_deg',
 'v_face_normal_error','v_normal_angle_deg','radius_error','slot_outward_shape_error',
 'fixed_window_center_error','fixed_window_outward_shape_error','loaded_tip_x_deflection','loaded_tip_z_deflection']}
reference=evaluate(tp,zero)
slot_all=reference['terms_x_mm']['whole_stroke_slot']
base_intrinsic=slot_all+m*.25
available=1-base_intrinsic
straight=.25*math.sqrt(1+m*m)
rho_example=.005
v_e_max=(.3-(1+math.sqrt(2))*rho_example)/math.sqrt(2)

# Exact new direct-pull formula from the source constants; degree conversion is
# explicit. δ changes absolute length only after reseating and resetting zero.
def law(theta,delta=0):
    t=math.radians(theta);bx=60*math.sin(t);by=60*math.cos(t)
    d=math.hypot(bx+24,by);phi=max(0,math.atan2(bx+24,by)-math.acos(60/d))
    return 5-delta+60*phi+math.sqrt(d*d-60*60)
def takeup(theta):return law(theta)-law(0)
def angle(u):return bisect(lambda a:takeup(a)-u,0,30)
def sx(u):
    a=math.radians(angle(u));return -4*math.cos(a)-26*math.sin(a)-5.5
def hull(points):
    points=sorted(set(points))
    def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    low=[];high=[]
    for p0 in points:
        while len(low)>1 and cross(low[-2],low[-1],p0)<=0:low.pop()
        low.append(p0)
    for p0 in reversed(points):
        while len(high)>1 and cross(high[-2],high[-1],p0)<=0:high.pop()
        high.append(p0)
    return low[:-1]+high[:-1]
def clipped_y(poly,y,keep_above):
    out=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        ain=(a[1]>=y) if keep_above else (a[1]<=y)
        bin=(b[1]>=y) if keep_above else (b[1]<=y)
        if ain:out.append(a)
        if ain!=bin:
            t=(y-a[1])/(b[1]-a[1]);out.append((a[0]+t*(b[0]-a[0]),y))
    return out
def stop_contact_min_x(u):
    # Exact source 72-gon negative-Y webs at Z2. At that Z the D3 screw-end
    # polygon includes every Y in [-25.5,-22.5]. Other source lever regions
    # (hub, positive-Y arm and rest lug) cannot enter this band for 0..22.1.
    angle_rad=math.radians(angle(u));co,si=math.cos(angle_rad),math.sin(angle_rad)
    values=[]
    for ends,r in [([(0,0),(-4,-26)],5.5),([(-4,-26),(1,-42)],5)]:
        local=hull([(x+r*math.cos(2*math.pi*i/72),y+r*math.sin(2*math.pi*i/72)) for x,y in ends for i in range(72)])
        poly=[(x*co+y*si,-x*si+y*co)for x,y in local]
        poly=clipped_y(clipped_y(poly,-25.5,True),-22.5,False)
        if poly:values.extend(p0[0]for p0 in poly)
    return min(values)
stoprows=[]
for u in [16,18,19.2,20,22]:
    a=math.radians(angle(u));y=4*math.sin(a)-26*math.cos(a)
    # The circular web's minimum-X tangent falls inside the D3 stop's end disk.
    # Polygonal web is inscribed; its radial discrepancy delays contact slightly.
    stoprows.append(dict(setting_equivalent_u_mm=u,angle_deg=math.degrees(a),tip_x_mm=sx(u),
        lever_circle_center_y_mm=y,stop_end_disk_y_margin_mm=1.5-abs(y+24),
        circular_nominal_first_contact_u_mm=u,
        polygon_web_first_contact_u_mm=bisect(lambda q:stop_contact_min_x(q)-sx(u),0,22.1),
        working_output_overtravel_if_lossless_mm=max(0,u-20)))
assert all(r['stop_end_disk_y_margin_mm']>0 for r in stoprows)
# At u>=16, x_min derivative wrt u is negative. Conservative smallest magnitude
# uses sin(theta_max), cos(theta_max), A<=60; continuous on this interval.
amax=math.radians(angle(22))
dxdu_lower=(26*math.cos(amax)-4*math.sin(amax))/60
poly_deficit=5.5*(1-math.cos(math.pi/72))
poly_u_delay=poly_deficit/dxdu_lower
assert dxdu_lower>0
window=20-base['release_requires_u_strictly_greater_mm']
balanced=(20+base['release_requires_u_strictly_greater_mm'])/2

sources=set(vhash)|set(exp['source_sha256'])|set(param['path']for param in param_sources.values())
sources|={'analysis/assembly_budget.py','analysis/feeder_tolerance.py','analysis/guide_revision_tolerance.py',
 'analysis/gate_budget_feasibility.py','analysis/gate_geometry.py','analysis/guide_openings.py',
 'analysis/final_gate_error_bound.py','analysis/frame_y_guide_bound.py','analysis/pin_v_seat_error.py',
 'docs/gate-envelope.md','docs/frame-y-guide-bound.md','docs/final-gate-error-bound.md'}
ident={s:sha(ROOT/s)for s in sorted(sources)}
assert all(sha(ROOT/k)==x for k,x in exp['source_sha256'].items())

legacy=[
 {'analysis':'analysis/assembly_budget.py','reuse':'Base slot slope/clearance arithmetic only.', 'invalid_current':'Unadjusted guide .2 and old D4.5 carrier hole .25 installation offset; current V-seat and X/Y gibs omitted.'},
 {'analysis':'analysis/feeder_tolerance.py','reuse':'Optimization method supplies feasible witnesses only for the geometry model actually encoded.', 'invalid_current':'Old circular pin seat/fixed guides; old CSG subset. A source hash of unchanged base files does not make its model current; no optimizer maximum is an upper bound.'},
 {'analysis':'analysis/guide_revision_tolerance.py','reuse':'Historical witness against carrier-Y revision only.', 'invalid_current':'No adopted V-ear cutout/common X and Y guide chain; surrogate full-height front band is not current exact contact domain.'},
 {'analysis':'analysis/gate_budget_feasibility.py','reuse':'Static necessary-window method when its ideal ball/guide/tip and equal B assumptions are explicitly retained.', 'invalid_current':'B=1.1 historical alternate c/L does not describe current c21/L28.5; the two witness families do not certify the whole mechanism.'},
 {'analysis':'analysis/gate_geometry.py','reuse':'Continuous static sufficient formulas and parked two-ball conditions; current straight-guide round-hole topology is preserved.', 'invalid_current':'B, diameter/radius envelopes are design hypotheses. Add transverse finger drift and faceted-tip allowance; moving/late balls and flexible bypass are outside the theorem.'},
 {'analysis':'analysis/final_gate_error_bound.py','reuse':'evaluate() whole-slot/V/pin transfer with explicitly supplied envelopes.', 'invalid_current':'frame_contact_review() still says fixed .4 Y gap; default box is an allocation, not current play. New frame-y bound replaces only that subchain.'},
 {'analysis':'analysis/frame_y_guide_bound.py','reuse':'Current parallel-gib necessary matrix inequalities and rational outward bound.', 'invalid_current':'Does not establish finite contact-domain coverage of all tilted gibs or carrier/V preload, and is not by itself whole-tip ±1 proof.'}]

report={
 'status':'CURRENT_SOURCE_CONDITIONAL_BUDGET_WITH_FUNCTIONAL_STOP_WINDOW',
 'generated_utc':datetime.now(timezone.utc).isoformat(),'analysis_sha256':sha(Path(__file__)),
 'source_sha256':ident,'sources_stable':all(sha(ROOT/k)==s for k,s in ident.items()),
 'current_export_identity':{'report':exp_rel,'sha256':sha(ROOT/exp_rel),'all_32_source_hashes_current':True},
 'scope':'Analytical review; no CAD edits, whole-CAD reruns, slicer runs or physical measurements.',
 'actual_measured_print_accuracy':False,'actual_measured_ball_range':False,
 'whole_feeder_tolerance_certified':False,'physical_acceptance':False,
 'parameter_snapshot':{k:p[k] for k in param_sources},'parameter_sources':param_sources,'source_contract_checks':checks,
 'input_classification':{'user_nominal':'PC pipe ID48/OD50 and hose ID50/OD55; not gauged dimensions.',
   'design_envelope':'ball D40..41, guide radius +/-0.25 and tip position +/-1 are CAD hypotheses; 40+ does not specify an upper measured diameter.',
   'nominal_clearance':'radial_print_clearance=.25 is model space, not symmetric manufacturing accuracy.',
   'adjusted_clearance':'displayed .1 gaps depend on assembled settings, surface form, contact and load.'},
 'legacy_applicability':legacy,
 'gate_budget':{'E_max_mm':E,'A_max_mm':A,'hole_r_mm':h,'static_conditions':[
     'Two rigid spheres already parked at the downstream gate; all centres in the side-hole-expanded disk.',
     'Four tips maintain the positively captured cam profile; no deflection/slip can bypass a stalled rear gate.',
     'Cylinder interior is the common guide domain; seam displacement/gap and radial-hole variation must fit the declared guide and tip envelopes.',
     'Bx bounds each finger radial centre error, Bz each gate axial error, By each finger transverse drift; manufacturing, mounting, play, phase and load cannot each spend B independently.'],
   'equations':{'eccentricity':'E(R)=sqrt(A^2-h^2)-sqrt(R^2-h^2)',
    'Hmin':'sqrt((Rmin+tmin)^2-(c+Bx)^2-(Emax+By)^2)',
    'Hmax':'max_R=sizes endpoints sqrt((R+tmax)^2-(c-Bx-E(R))^2)',
    'Pmin':'sqrt((2Rmin)^2-(2Emax)^2)',
    'spacing':'2*Hmax+2*Bz < L < Hmin+Pmin-Hmax-2*Bz',
    'closed':'sqrt((c+Bx)^2+(Emax+By)^2) < Rmin+tmin',
    'open':'o-Bx > Rmin+tmax+Emax'},
   'rows_ideal_sphere_By0':rows,'baseline_Bx_Bz_1':base,
   'maximum_Bx_when_Bz1_By0_ideal_tip_mm':maxbx,
   'maximum_By_when_Bx_Bz1_ideal_tip_mm':by_max,
   'current_tip_mesh_diagnostic':{'file':str(fp.relative_to(ROOT)),'sha256':sha(fp),'exposed_spherical_facets':len(dist),
      'minimum_facet_plane_distance_mm':min(dist),'selected_conservative_reference_radius_mm':2.4845,
      'scope':'Current nominal mesh diagnostic. 0.000109 mm padding is numerical/model allowance, not print tolerance; not a full manufactured shape guarantee.'},
   'faceted_reference_with_By_point1':faceted},
 'guides_and_pin':{'nominal_parallel_clearances_mm':{
     'common_X_translation_interval':[0,gx],'common_Y_translation_interval':[0,gy],
     'each_carrier_Y_translation_interval':[-cygap,0],
     'carrier_Z_rectangular_channel_total':.4,'fixed_D4_pin_window_Z_half':.25,
     'cam_slot_D4_pin_circular_half':.25,'cam_slot_32gon_inscribed_radial_fit':2.25*math.cos(math.pi/32)-2,
     'pin_shoulder_beyond_far_cam_face':.75,'X_gib_end_recess_minus_axial_float':.2},
   'adjustment_domains':{
     'common_X_face_mm':[58,59],'common_Y_face_work_mm':[23.8,25],
     'common_Y_face_hard_mm':[23.7,25.2],'carrier_Y_gap_work_mm':[0,1],
     'V_block_work_dx_mm':[-.5,.3],'V_block_hard_dx_mm':[-.6,.4]},
   'warning':'Zero/negative effective guide gap is binding/preload, not extra accuracy; settings require actual face contact and free 20 mm motion.',
   'actual_finite_domains':{'X_stations_Z_mm':[-33.35,3.35],'Y_stations_Z_mm':[-33.29,3.29],
      'Y_station_scope':'Parallel gibs, dz within +/-0.2; both actual finite X/Z tooth domains still required.',
      'remaining_carrier_front_band_abs_Z_mm':[3.0,4.0],
      'removed_carrier_front_patch_local_X_mm':[22.8,27.5]},
   'necessary_frame_inequalities':['4+36.7*abs(Rzx) <= (4+gx)*Rxx',
      '116*abs(Rxy)+4*Rxx+36.58*abs(Ryz) <= (4+gy)*Rzz'],
   'conditional_frame_rows':frows,
   'V_error_equations':['dx=(d1+d2)/sqrt(2)+sqrt(2)*dr','dz=(d2-d1)/sqrt(2)',
      'required_block_dx=(d1+d2)/sqrt(2)+(1+sqrt(2))*dr',
      'sqrt(2)*E+(1+sqrt(2))*rho <= .3 (symmetric error box fits asymmetric working range)',
      'P-Fx > abs(Fz) is necessary for both V faces to remain loaded in the 2D force model'],
   'V_symmetric_face_error_max_if_radius_error_zero_mm':.3/math.sqrt(2),
   'V_face_error_example_if_radius_error_point005_NOT_measured_mm':v_e_max,
   'remaining_required_envelopes':'Face form/angle, shoulder radius/inclination, positive retained V preload, carrier rotation, whole cam displacement field and loaded flex must enter transfer; adjustable travel alone proves none.'},
 'host_registration':{
   'side_support_mount':'Two M3 shanks nominal D3 in support/body D3.4 clearance features, at Z[-45,16]. X seat is a real datum; screw axes alone do not set exact Y/Z registration.',
   'bolt_clearance_only_relative_hole_center_allowance_mm':.4,
   'bolt_clearance_scope':'Sum of two .2 radial clearances, not a feasible assembly displacement witness: captured nuts, body finger bores and other contacts can further constrain it.',
   'seam_locators':'D3 pin in negative D3.1 and positive D3.2 round/slot-width locations; nominal relative transverse centre allowance .05+.1=.15 at each locator, before manufacturing.',
   'seam_pins_nominal_transverse_allowance_mm':.15,
   'budget_rule':'Mount registration and split-guide steps/gaps consume the SAME Bx/Bz/By and A/h envelopes. They must not be appended as extra independent allowances after the gate calculation passes.',
   'sources':[ref('cad/feeder-body.scad','module body_side_cuts'),ref('cad/feeder-supports.scad','support_mount_z ='),ref('cad/feeder-seam-candidate.scad','seam_fixed_hole_d =')]},
 'all_stroke_transfer':{'slot_half_gap_straight_only_mm':straight,'slot_whole_graph_bound_mm':slot_all,
   'fixed_window_slope_term_mm':m*.25,'intrinsic_zero_pose_reference_Bx_mm':base_intrinsic,
   'remaining_Bx_budget_to1_before_other_terms_mm':available,
   'equation_x':'Bx >= S + sqrt(1+m^2)*Fx + m*(.25+rho+window_error+3.25*tan(beta_world)+Fz) + carrier_rotation_x + V_midplane_error + pin_extension*tan(beta_world) + loaded_tip_x',
   'equation_z':'Bz >= .25+rho+window_error + hypot(20,3.125)*sin(alpha_carrier) + V_midplane_error + fixed_pin_extension*tan(beta_world) + loaded_tip_z',
   'Fz_definition':'Whole cam field including installation/stop phase when referenced to a hard-stop zero; not only translation u.',
   'scope':'Conditional sufficient bound reused with current source assertions, not a certified as-built input box. Both finite V contacts and sample-plane engagement must hold.'},
 'stroke_and_stops':{'cam_phases_mm':{'rear_close':[0,8],'both_commanded_closed':[8,12],'front_open':[12,20]},
   'fixed_output_stop_planes_Z_mm':[-35,5],'moving_rest_stop_lower_Z_mm':5,
   'moving_full_stop_upper_Z_at_u0_mm':-55,'nominal_output_range_mm':[0,20],
   'input_stop_rows':stoprows,'input_stop_circular_vs_polygon':{
      'scope':'First contact of the specified local lever-web/stop pair only. It does not prove absence of earlier collisions with other assemblies. The existing system report covers its own sampled 0..20 domain; numerical roots slightly above20 and near22 are local diagnostic continuations, not permitted assembled travel.',
      'web_72gon_max_radial_deficit_mm':poly_deficit,'abs_dx_du_continuous_lower_bound':dxdu_lower,
      'additional_contact_delay_u_upper_mm':poly_u_delay,
      'continuous_first_contact_argument':'Before the circular target angle the origin-to-knuckle web lies to the right of its decreasing circular minimum-X bound. Until atan(5/16) the lower web extends toward +X, and above that angle its clipped-band left reach is less than 5.21 mm from the knuckle versus at least 5.4947 for the larger knuckle. At target angles 16..22 the supporting 72-gon vertex Y offset is <=5.5*sin(2.5deg)=.2399, below the minimum screw-end band margin .26775 (and remains below it through the .01380-u delay). Thus the contact root is the first contact in this local stop geometry, not just a sampled overlap.',
      'meaning':'Circular formula is nominal; inscribed web can delay actual first contact by up to this small design discretization amount. Target screw end disk still covers the supporting vertex.'},
   'functional_window_Bx1_mm':[base['release_requires_u_strictly_greater_mm'],20],
   'functional_window_width_mm':window,
   'strict_stop_inequalities':['U > u_release + ell_max', 'U < H_min + ell_min',
      'Feasible iff ell_max-ell_min < H_min-u_release; inequalities are strict for positive clearance.'],
   'ell_definition':'Net input takeup minus output displacement at full pull, including bounded slack/stretch/zero-reference errors; separate any uncertainty in H_min.',
   'symmetric_error_center_if_H20_mm':balanced,'symmetric_error_halfwidth_if_H20_mm':window/2,
   'example_U19point2_NOT_setup_instruction':{'release_side_budget_mm':19.2-base['release_requires_u_strictly_greater_mm'],
      'hard_stop_side_budget_mm':.8,'meaning':'Illustrates allocation only; actual loss/phase bounds must fit before selecting a setting.'},
   'zero_setup':'Output rests on its real zero stop; input rests on its rest lug; seat ferrules, retension output core, lock M6 and then set pull stop inside the functional interval. Positive core preload must not hold output off zero.',
   'M6_delta':'Assembly +/-2 moves absolute core reference by +/-2; re-zero after reseating. It exceeds the 1.5786 functional end-window if left uncompensated.',
   'end_slot_fit_condition':'At each rounded track end, a sufficient ideal-axis nominal fit is combined pin-centre endpoint error norm < 0.239165 mm (32-gon inscribed slot radius minus circular D4 pin radius). Manufacturing/tilt consume it; it is not 0.25 plus another independent allowance.',
   'separating_web_mm':L-p['cam_stroke']-4.5,
   'optional_endpoint_runout_candidate':'If full 20 mm stop synchronization cannot satisfy endpoint phase budget, extend only constant-radius parked slot ends axially by e; nominal slot web becomes 4-2e. e=.5 would leave 3 mm. This is an unadopted minimum-geometry option, not validated CAD.'},
 'conclusions':{
    'new_proven_hard_intersection':None,
    'specific_closed_items':['Old report applicability separated from current geometry.',
       'Static functional endpoint requires >18.421388, not necessarily exact20, for the stated Bx1 envelope.',
       'Variable lost motion has a nonempty fixed-stop solution exactly when its spread fits the functional end-window after hard-stop uncertainty.',
       'Actual nominal guide gaps, V compensation allowance and conditional stop phase are explicit rather than called print accuracy.'],
    'specific_open_items':['No current complete enclosure proves actual four-follower Bx/Bz/By including finite guide domains and loading.',
       'Simultaneous nominal U20 and output20 leaves zero positive allowance for stop/zero/loss variation; choose inside the derived window after bounding them.',
       'Current rounded cam ends have only .239 mm sufficient circular-pin fit allowance; phase/shape errors must fit or endpoint runout requires a separate local design review.'],
    'do_not_infer':['A failed sufficient budget is not a feasible physical collision.',
       'No sampled native collision report is a full tolerance proof.',
       'Static parked-pair passing and continuous hold inequality do not prove dynamic single-ball feeding, return speed or ball ejection.']},
 'related_return_budget':'output/current-return-budget/report.json'}
assert report['sources_stable']
assert base['sufficient_static_spacing_pass'] and faceted['sufficient_static_spacing_pass']
assert abs(window-1.578612318588092)<1e-10
(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':report['status'],'source_count':len(ident),'sources_stable':report['sources_stable'],
 'functional_window_mm':report['stroke_and_stops']['functional_window_Bx1_mm'],
 'max_Bx_at_Bz1':maxbx,'faceted_By_point1_margins':[faceted['lower_spacing_margin_mm'],faceted['upper_spacing_margin_mm']],
 'stop_polygon_delay_bound_mm':poly_u_delay,'current_complete_tolerance_proven':False},ensure_ascii=False,indent=2))

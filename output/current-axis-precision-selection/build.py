#!/usr/bin/env python3
"""Reproduce bounded catalogue/interval review; no CAD, network or procurement."""
from pathlib import Path
from decimal import Decimal as D
import hashlib, json, math

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def dec(x): return D(str(x))
def grid(value,lo,hi,step):
    return dec(lo)<=dec(value)<=dec(hi) and (dec(value)-dec(lo))%dec(step)==0
def rnd(x): return round(float(x),12)

def main():
    evidence=OUT/'evidence'
    files=sorted(p for p in evidence.iterdir() if p.is_file())+[Path(__file__).resolve()]
    hashes={str(p.relative_to(ROOT)):sha(p) for p in files}
    native=json.loads((evidence/'shoulder-native-report.json').read_text())
    rejected=json.loads((evidence/'rejected-l27-report.json').read_text())
    checks=[]
    def check(name,value):
        checks.append({'check':name,'passed':bool(value)})
        assert value,name
    check('catalogue_L_grid',grid(24.5,10,60,.1))
    check('catalogue_F_grid',grid(12,6,18,.5))
    check('catalogue_M_choice',6 in [5,6,8])
    check('catalogue_L_plus_F',dec(24.5)+dec(12)<=70)
    check('L27_actual_collision_retained',rejected['reachable_collision_witness']['mesh']['signed_volume_mm3']>0)
    L=[D('24.45'),D('24.55')]; body=D('-12'); seat=D('11.5')
    span=seat-body
    # lo cannot exceed body exterior; hi cannot precede recessed head seat.
    lo=[seat-L[1],body]; hi=[seat,body+L[1]]
    F=[D('11.5'),D('12.5')]; t=[D('1.4'),D('1.8')]; nh=[D('5.7'),D('6')]
    envelopes={'shaft':[lo[0],hi[1]],'head':[hi[0],hi[1]+D('6.2')],
       'thread':[lo[0]-F[1],lo[1]],'washer':[lo[0]-t[1],lo[1]],
       'nut':[lo[0]-t[1]-nh[1],lo[1]-t[0]]}
    expected={'shaft':[-13.05,12.55],'head':[11.5,18.75],'thread':[-25.55,-12],
       'washer':[-14.85,-12],'nut':[-20.85,-13.4]}
    for k,v in envelopes.items():check('continuous_interval_'+k,[rnd(x) for x in v]==expected[k])
    check('native_head_limit_matches',native['calculated']['head_max_z_mm']==rnd(envelopes['head'][1]))
    check('AABB_Y_matches_local_Z',native['axis_cad_aabb_mm'][0][1]==rnd(D('-82')+envelopes['thread'][0]) and native['axis_cad_aabb_mm'][1][1]==rnd(D('-82')+envelopes['head'][1]))
    check('broad_phase_count',len(native['feeder_noninput_broad_phase'])==58)
    for original,copied in [('output/current-axis-shoulder-candidate/candidate.scad','reviewed-shoulder-candidate.scad'),('output/current-axis-shoulder-candidate/review.py','reviewed-shoulder-review.py')]:
        check('native_source_identity_'+copied,native['source_sha256'][original]==sha(evidence/copied))
    check('outer_polygon_compensation_present','k=1/cos(180/72);' in (evidence/'reviewed-shoulder-candidate.scad').read_text())
    native_report=Path(native['cases'][0]['command'][-2]).parent/'report.json'
    check('copied_native_report_identity',sha(native_report)==sha(evidence/'shoulder-native-report.json'))
    # Standard washer interval gives this full annulus only if coaxial, flat,
    # and the supplier-unbounded root relief is completely outside the face.
    nominal_flat_width=(D('7.986')-D('6.62'))/2
    report={
      'status':'CATALOGUE_SHOULDER_CANDIDATE_IDENTIFIED_END_SEATING_OPEN',
      'date_utc':'2026-09-27','source_sha256':hashes,
      'preferred':{
        'catalogue_derived_configuration':'GDSMSB8-24.5-F12-M6',
        'configured_sku_verified':False,'ordered':False,
        'official_url':'https://jp.misumi-ec.com/vona2/detail/110300249570/',
        'published_template':'GDSMSB8-[10-60/0.1]-F[6-18/0.5]-M[5,6,8]',
        'material':'SUS304 equivalent','strength_class':'A2-50',
        'shaft_diameter_mm':[7.986,7.995],'shoulder_length_mm':[24.45,24.55],
        'head_nominal':{'diameter_mm':13,'height_mm':6,'socket_AF_mm':5},
        'thread':'M6 x 1','F_nominal_mm':12,
        'drawing':{'url':'https://content.misumi-ec.com/image/upload/t_msmwm_wyg/v1/p/jp/product/wysiwyg/110300249570/110300249570_001_20230913143356.gif',
          'local_file':str((evidence/'gdmsb-current-drawing.gif').relative_to(ROOT)),
          'visually_inspected':True,'bearing_surface_Ra_um':1.6,
          'shoulder_length_tolerance_mm':.05,'thread_end_groove_depicted_when_M_less_than_D':True,
          'under_head_detail_axial_mark_max_mm':2.5,'under_head_detail_T_for_D8_mm':8.7,
          'under_head_detail_other_mark_max_mm':1,
          'root_radius_limit_mm':None,'groove_depth_width_limits_mm':None,
          'head_height_diameter_tolerances_mm':None,'full_usable_thread_length_mm':None},
        'limits':['Catalogue-domain validity is not checkout, stock, delivery or inspection evidence.',
          'Thread-end groove depiction does not prove a DIN 125 washer can seat flat.',
          'Known Ra1.6 is not qualification of the future POM bearing pair.']},
      'end_hardware':{
        'nut':{'code':'HNN-M6-A2','official_url':'https://www.accu.co.uk/hexagon-nylon-locking-nuts/7948-HNN-M6-A2',
          'thread':'M6 x 1','material':'A2-70 stainless, nylon insert','height_mm':[5.7,6],
          'across_flats_mm':[9.78,10],'minimum_hex_metal_height_mm':4,
          'current_stock_or_orderability_verified':False},
        'flat_washer_dimension_reference':{'code':'HPW-M6-A2','official_url':'https://www.accu.co.uk/metric-flat-washers/72494-HPW-M6-A2',
          'material':'A2 stainless','OD_mm':[11.6,12],'ID_mm':[6.4,6.62],'thickness_mm':[1.4,1.8],
          'current_stock_or_orderability_verified':False,
          'availability_note':'Parsed page contains several mutually exclusive status templates; no reliable live status inferred.',
          'shoulder_seating_verified':False,'coaxial_flat_face_annulus_width_without_root_relief_mm':rnd(nominal_flat_width)},
        'machined_relief_washer_fallback':{
          'off_the_shelf':False,'adopted':False,
          'requirements':['M6 thread and maximum root profile must clear the bore/chamfer at every axial section.',
            'Root relief diameter at the bearing face plus twice total eccentricity must be less than shoulder minimum diameter 7.986 mm.',
            'Choose relief diameter/depth only from a bounded supplier root envelope; no root radius has been guessed.',
            'Retain a checked flat shoulder-contact annulus and enough outer bearing area to capture the nominal 8.3 mm body hole.',
            'Thickness, hardness, flatness, bending and allowed clamp load require explicit requirements before release.',
            'A new relief washer outside OD<=12 and thickness1.4..1.8 requires updating the existing envelope review.']},
        'engagement_requirement':'Use bounded full-thread start/end and nylon-zone position; F minus washer/nut heights only gives physical tip projection, not usable engagement.',
        'load_loop':'M6 nut -> metal washer -> shoulder end -> integral threaded nose -> nut; integral head captures the opposite plastic face. PETG must not carry the tightening clamp loop.',
        'replaces':'M4 through-bolt, M4 nut and old M4-axis end washers; solid shoulder has no through bore.'},
      'conditional_geometry_review':{
        'reviewed_native_report':str(native_report.relative_to(ROOT)),
        'reviewed_candidate_sha256':hashes[str((evidence/'reviewed-shoulder-candidate.scad').relative_to(ROOT))],
        'independently_reran_CGAL':False,'capture_span_mm':rnd(span),
        'float_mm':[rnd(x-span) for x in L],
        'continuous_local_Z_envelopes_mm':{k:[rnd(x) for x in v] for k,v in envelopes.items()},
        'head_nominal_H6_max_Z_mm':18.55,'head_window_H6_2_max_Z_mm':18.75,
        'nominal_host_starts_Z_mm':19,'head_window_axial_gap_mm':.25,
        'cover_recess_mm':{'diameter':13.8,'seat_Z':11.5,'remaining_wall':3.5},
        'under_head_relief_support_limit':{
          'drawing_interpretation':'Conditional on the marked 2.5 max axial head-root region being measured from the under-head bearing face, as depicted in its enlarged detail.',
          'lowest_head_face_Z_mm':11.5,'possible_relief_start_Z_mm':9,
          'cover_inner_face_Z_mm':8,'wall_length_outside_that_region_mm':1,
          'statement':'The full-diameter cylinder in the collision model must not be treated as proof that the full 3.5 mm cover wall bears on uninterrupted g6 shaft. This is not a support-load or actual-contact certification; the detailed head-root profile, including T=8.7, still needs compatible clearance.'},
        'design_windows_not_supplier_proven':{'head_D_max_mm':13.2,'head_H_max_mm':6.2,'F_mm':[11.5,12.5]},
        'physical_tip_projection_mm':[rnd(F[0]-t[1]-nh[1]),rnd(F[1]-t[0]-nh[0])],
        'polygon_revision':{'facets':72,'previous_head_R6_6_inscribed_radial_deficit_mm':6.6*(1-math.cos(math.pi/72)),
          'resolved':True,'external_scale_factor':1/math.cos(math.pi/72),
          'statement':'Reviewed revision circumscribes external circular envelopes, keeps internal cuts inscribed and enlarges the broad-phase radial bound. The previous polygon underbound is resolved for the stated coaxial envelope; tilt is still excluded.'},
        'not_closed':['Root/washer flat seating and under-head corner seating',
          'Head and F supplier tolerances meeting the stated design windows',
          'Real bore registration, tilt, printed cover thickness and deflection',
          'POM bush bore tolerance, running clearance, surface pairing, thrust capture',
          'Torque, washer bending, nylon engagement/reuse, anti-rotation and service tool access']},
      'excluded':[
        {'candidate':'L27 through-tube/M4 fastener arrangement','evidence':'output/current-axis-through-candidate/locking/runs/20260927T130027855890Z/report.json',
          'envelope_collision_mm3':rejected['cases'][3]['mesh']['signed_volume_mm3'],
          'reachable_nominal_collision_mm3':rejected['reachable_collision_witness']['mesh']['signed_volume_mm3'],
          'reason':'Actual host collision; L27 shoulder/head cannot be carried forward unchanged.'},
        {'candidate':'SPJ8 / SSPJ8 precision hollow shaft','official_url':'https://jp.misumi-ec.com/vona2/detail/110302635960/',
          'OD_g6_mm':[7.986,7.995],'catalogue_bore_nominal_mm':3,
          'reason':'Catalogue bore is below required >=4.1; not a compatible M4 through-shaft. Enlarging bore is a new machining process, not catalogue identity.'}],
      'bounded_next_action':'Retain the L24.5 shoulder route; obtain or specify bounded root/under-head geometry and matching metal washer. Do not buy solely by nominal M6 washer size. No second ready-made hollow-shaft route has been established.',
      'checks':checks,'production_CAD_modified':False,'purchased':False,'contacted_supplier':False,
      'manufacturing_release':False,'physical_acceptance':False}
    assert all(sha(ROOT/k)==v for k,v in hashes.items())
    (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'checks':len(checks),'status':report['status'],'report_sha256':sha(OUT/'report.json')},indent=2))

if __name__=='__main__':main()

#!/usr/bin/env python3
"""Source/contract audit only; consumes prior tests without rerunning them."""
from pathlib import Path
import hashlib,json,math
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
candidate=HERE.parent/'candidate.scad';route=HERE.parent/'housing-route/equal-length-route.scad'
native_plus2=HERE.parent/'housing-route/numeric/plus2.echo'
root_numeric=HERE.parent/'housing-route/numeric/report.json'
tools_report=HERE/'tool-review-upper-sector/report.json';failed=HERE/'tool-review/report.json'
before={str(p):sha(p) for p in [candidate,route,root_numeric,native_plus2,tools_report,failed,ROOT/'cad/cable-housing-route.scad',ROOT/'cad/cable-service-contract.scad',ROOT/'cad/cable-service-review.scad',HERE/'tool-probes.scad',Path(__file__)]}
assert sha(candidate)=='f76a83eeb95644bd3c856922b31da749cc47c083d688d271116f946493994588'
assert sha(route)=='9d16bec62f032885f987e97506c62ae279fff389abc59246d7193fdb78d8a729'
r=json.loads(root_numeric.read_text());t=json.loads(tools_report.read_text())
assert t['all_checks_passed']
s=math.sqrt(.5);P=[75+s*123,-80,5-s*3];B=[P[0]+100*s,115,P[2]-100*s];C=[-58,35.5,400]
bc=[C[i]-B[i] for i in range(3)];bc_len=math.sqrt(sum(v*v for v in bc));c=[v/bc_len for v in bc]
cd=(c[0]-c[2])*s;cy=c[1];proof=[]
for a in (2,12):
    h=math.hypot(195,a);th1=math.acos(-a/h);th2max=math.acos((a*cd+195*cy)/h)
    trim1=75*math.tan(th1/2);trim2=75*math.tan(th2max/2)
    # Original final segment length is a root-report input; third arc is fixed.
    trim3=289-r['rows'][0]['straight_lengths'][3]
    proof.append({'shift_abs_bound_mm':a,'theta2_derivative_sign_numerator_upper':195*cd+a*abs(cy),
      'length_derivative_wrt_shift_lower_bound':1-a/195-75*math.tan(th1/2)**2/195,
      'straight_lower_bounds_mm':[100-2-a-trim1,195-trim1-trim2,bc_len-trim2-trim3,289-trim3]})
assert abs(proof[0]['length_derivative_wrt_shift_lower_bound']-r['continuous_existence']['length_derivative_wrt_shift_lower_bound'])<1e-12
assert all(x['length_derivative_wrt_shift_lower_bound']>0 and x['theta2_derivative_sign_numerator_upper']<0 and min(x['straight_lower_bounds_mm'])>0 for x in proof)
result={'status':'BOUNDED_ROUTE_FORMULA_AND_BENCH_TOOL_GEOMETRY_REVIEW_PASS',
 'source_hashes_before':before,'source_hashes_after':{p:sha(Path(p)) for p in before},
 'route_audit':{'formula_review':'L=polyline length - sum(2 R tan(theta_i/2)-R theta_i); L(delta,s)=L(0,s)+delta. The parent derivative and positive lower-bound derivation are correct on |s|<=2. The same bound also stays positive over the native initial bisection bracket |s|<=12.',
   'independent_derivative_coefficients':{'c_dot_input_direction':cd,'c_y':cy},'independent_inequality_checks':proof,
   'port_binding':'cv Pdelta=P0-delta*cr_input_direction equals v2 local head inlet [-63+delta,60,2], since direction is -basis_x and origin/basis are preserved.',
   'third_arc_binding':'cv_vertices fixes indices 2,3,4; cv_arc(3) directly returns cr_arc(3); cv_require asserts radius equality. Geometry of the retained output bend is unchanged.',
   'root_numeric_report':str(root_numeric),'root_numeric_report_sha256':sha(root_numeric),
   'root_samples_consumed_not_rerun':r['sample_count'],'root_length_mm':r['outside_port_route_length'],
   'root_shift_at_minus2_mm':r['rows'][0]['shift'],'root_shift_at_plus2_mm':r['rows'][-1]['shift'],
   'root_min_sampled_straight_mm':min(min(x['straight_lengths']) for x in r['rows']),
   'no_claims':['Automatic physical shape retention of the free first two bends','Continuous all-delta collision clearance from three-delta or 81-delta samples','Final housing cut length without actual seating correction','Cable force/friction/bend lifetime/installation ergonomics']},
 'tool_audit':{'accepted_report':str(tools_report),'accepted_report_sha256':sha(tools_report),
   'rejected_report':str(failed),'rejected_report_sha256':sha(failed),
   'rejected_swing':'-60..+60 deg: real lower-rib intersection 65.3239956919 mm^3',
   'accepted_swing_deg':[0,60],'loose_nut_gap_mm':[0,.2],
   'minimum_nominal_thread_end_margin_during_loosen_mm':1.0,
   'minimum_nominal_tool_nut_axial_overlap_mm':2.9,
   'simultaneous_tools':{'proof':'Exact axial interval separation. All torque/entry arc inflation is planar YZ; none enlarges X.',
      'sw8_all_motion_x_mm':[-63,-56],'sw10_left_all_motion_x_mm':[-49.7,-46.7],'sw10_right_all_motion_x_mm':[-35.3,-32.3],
      'minimum_axial_gap_left_mm':6.3,'minimum_axial_gap_right_mm':20.7},
   'raw_contact_classification':'Loose-nut raw mesh has only x=-46.6 / -35.4 planar washer bearing contacts. No contact skins removed. Loose-nut versus printed parts alone is empty.',
   'sequence':['Disconnect power/air; no balls; feeder at rest. Release output core and fully clear the terminal cross-bore. Disconnect/park housing, remove required retainer/mount fasteners, place input module on bench, remove main cover and park ferrule away from adjuster.',
     'Counterhold SW8 head at fixed angular orientation; this wrench follows delta axially. Use only one SW10 wrench at a time.',
     'Increase delta: retreat left nut from its washer by at most .2 mm; move SW10 to right nut and turn it toward its washer, advancing adjuster +X by no more than the available loose gap. Repeat. Decrease delta: exchange left/right and X directions.',
     'Perform both turn directions within upper 0..60 deg by reversing stroke and reindexing entry as needed. Never take the downward -60 deg path. Limit each axial step by the loose gap and actual pitch, without assuming an unverified turn count.',
     'Lock both nuts at their washer faces within measured delta +/-2. Reseat housing/ferrule, install within the equal-length family space, reset core slack/preload/output clamp and stroke stop, then refit cover and module.'],
   'scope':'Geometric budgets for candidate tools. No purchased tool certification, torque or preload approval, thread-runout approval, FDM tolerance or physical dexterity proof.'}}
result['sources_unchanged']=result['source_hashes_before']==result['source_hashes_after']
(HERE/'route-and-tool-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':result['status'],'sources_unchanged':result['sources_unchanged'],'proof':proof,'simultaneous':result['tool_audit']['simultaneous_tools']},indent=2))

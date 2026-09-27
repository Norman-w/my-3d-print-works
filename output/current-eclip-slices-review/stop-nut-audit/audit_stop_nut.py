from pathlib import Path
import sys,json,hashlib,math
import numpy as np
from shapely.geometry import LineString,Point,box,Polygon
from shapely.ops import nearest_points
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'analysis'))
import cable_input_slice_review as p
import cable_eclip_body_clearances as b
F=ROOT/'output/current-eclip-slices/20260927T155752390241Z/cable-input-body'
a=json.loads((F/'artifact-review.json').read_text());I=np.linalg.inv(np.array(a['input_local_to_command']))
s={'kind':'xhex','x':[-35,-32.6],'cy':-24,'cz':2,'r':5.5/math.sqrt(3)}
results=[]
for r in p.extrusion_paths((F/'plate_1.gcode').open()):
 if r.feature in b.NONMODEL or r.feature.startswith('Support'):continue
 q=p.affine(r.points,I);lo,hi=sorted([float(q[0,2]),float(q[0,2]+(I[:3,:3]@np.array([0,0,-r.height]))[2])]);roi=b.projection(s,lo,hi)
 if roi.is_empty:continue
 line=LineString(q[:,:2]);d=line.distance(roi);g=d-r.width/2
 if g>=.01:continue
 qp,rp=nearest_points(line,roi)
 results.append(dict(line=r.line,feature=r.feature,print_z=r.layer,height=r.height,width=r.width,z=[lo,hi],points=q.tolist(),distance=d,gap_raw=g,gap_with_errors=g-b.ERROR,path_nearest=list(qp.coords)[0],roi_nearest=list(rp.coords)[0],roi_bounds=roi.bounds))
results.sort(key=lambda x:x['gap_raw'])
(Path(__file__).parent/'raw-hits.json').write_text(json.dumps(results,indent=2)+'\n')
for r in results[:12]:print(json.dumps(r))
# Same rigid nut, inserted continuously from local -X. This is not a smaller nut.
# The swept union is a hex prism from first leading station minus nut thickness
# to its final front face. Nut's bore is conservatively filled throughout.
shift=0.019
specs=[dict(s,x=[-90,-32.6],label='full_original_insertion'),dict(s,x=[-90,-32.6-shift],label='same_nut_insertion_0p019_before_nominal_bearing')]
sweep=[]
for spec in specs:
 hit=[];mingap=math.inf;minrec=None;examined=0
 for r in p.extrusion_paths((F/'plate_1.gcode').open()):
  if r.feature in b.NONMODEL or r.feature.startswith('Support'):continue
  q=p.affine(r.points,I);lo,hi=sorted([float(q[0,2]),float(q[0,2]+(I[:3,:3]@np.array([0,0,-r.height]))[2])]);roi=b.projection(spec,lo,hi)
  if roi.is_empty:continue
  line=LineString(q[:,:2]);d=line.distance(roi)
  if d>3:continue
  examined+=1;gap=d-r.width/2-b.ERROR
  if gap<mingap:mingap=gap;minrec=r.line
  if gap<0:
   qp,rp=nearest_points(line,roi);hit.append(dict(line=r.line,gap=gap,path_nearest=list(qp.coords)[0],roi_nearest=list(rp.coords)[0]))
 sweep.append(dict(label=spec['label'],x=spec['x'],nut_AF_mm=5.5,nut_length_mm=2.4,examined=examined,min_gap_mm=mingap,min_line=minrec,hits=hit))
print(json.dumps([{k:v for k,v in q.items()if k!='hits'}|{'hits':len(q['hits'])}for q in sweep],indent=2))
(Path(__file__).parent/'swept-insertion.json').write_text(json.dumps(sweep,indent=2)+'\n')
# Freeze a machine-readable conclusion, keeping the original root flag intact.
OUT=Path(__file__).parent
flags=[q for q in results if q['gap_with_errors']<0]
assert len(flags)==202 and all(abs(q['roi_nearest'][0]+32.6)<1e-7 for q in flags)
assert len(sweep[0]['hits'])==202 and len(sweep[1]['hits'])==0
worst=flags[0];assert worst['line']==349521 and worst['feature']=='Overhang wall'
# A point strictly inside the nominal bead slab AND solid part of the nut.
witness=np.array([-32.6074,-24,3.75]);line=LineString(np.array(worst['points'])[:,:2]);dist=line.distance(Point(witness[:2]));ahex=np.arange(6)*math.pi/3+math.pi/6
hex_yz=Polygon(np.column_stack([-24+s['r']*np.sin(ahex),2-s['r']*np.cos(ahex)]))
assert -35<witness[0]<-32.6 and hex_yz.contains(Point(witness[1:]))
assert math.hypot(witness[1]+24,witness[2]-2)>3.1/2
assert worst['z'][0]<witness[2]<worst['z'][1] and dist<worst['width']/2
source_files=[ROOT/'cad/cable-trigger-input.scad',ROOT/'analysis/cable_eclip_body_clearances.py',ROOT/'analysis/cable_input_slice_review.py',ROOT/'analysis/cable_slice_contract.py',F/'artifact-review.json',F/'body-clearance-review.json',F/'plate_1.gcode',F/'invocation.json',F/'slice-review.3mf',Path(__file__).resolve()]
report={
 'status':'AXIAL_BEARING_CONTACT_CLASSIFIED_NOT_RADIAL_FIT_FAILURE',
 'scope':'Independent bounded read-only check of current declared bead slabs against nominal captured M3 stop nut. No CAD/profile/slice modification.',
 'nominal_geometry':{'nut_AF_mm':5.5,'nut_length_mm':2.4,'nut_x_mm':[-35,-32.6],'axis_local_yz':[-24,2],
 'nut_actual_cad_rotation':'rotate([0,90,0]) rotate([0,0,30]) six-sided cylinder',
 'cavity_AF_mm':5.8,'cavity_x_mm':[-38.3,-32.6],'designed_bearing_plane_x_mm':-32.6,
 'nominal_radial_face_clearance_mm':.15,'nominal_rear_axial_room_mm':3.3,
 'source_lines_cavity':[293,296],'source_lines_hardware':[399,408]},
 'original_result_preserved':{'flag_count':202,'min_clearance_lower_mm':-0.01813070640983921,'file':str(F/'body-clearance-review.json')},
 'classification':{'all_flag_nearest_points_on_bearing_plane':True,'radial_side_nearest_flag_count':0,
 'raw_nominal_halfwidth_negative_count':sum(q['gap_raw']<0 for q in flags),
 'worst_nonexceptional_raw_penetration_mm':-min(q['gap_raw']for q in flags[1:]),
 'original_error_budget_mm':b.ERROR,'worst':worst,
 'positive_volume_witness_local':witness.tolist(),'witness_nominal_bead_radial_margin_mm':worst['width']/2-dist,
 'witness_nut_bore_clearance_mm':math.hypot(witness[1]+24,witness[2]-2)-1.55,
 'meaning':'The nominal constant-height declared bead envelope really crosses the ideal bearing plane; this is not zero-thickness contact and not a wrong hex orientation. Its location is the intended axial contact datum, not the hex radial walls.'},
 'continuous_same_nut_insertion':[{k:v for k,v in q.items()if k!='hits'}|{'hit_count':len(q['hits'])}for q in sweep],
 'pose_interpretation':{'unchanged_nut_size':True,'early_position_local_x':[-35.019,-32.619],
 'axial_change_mm':-.019,'cavity_rear_room_at_early_position_mm':3.281,
 'inserted_union':'Exact union of the same convex hex prism translating +localX from X[-90,-87.6] to the reported final pose; no rotation.',
 'continuity':'Entire swept prism is clear at the early pose. The original pose has positive nominal bead intersection, so first contact lies between them; this bounds axial seat location under the declared slab model.',
 'not_a_tolerance_claim':'0.019 mm is a bound needed for this nominal envelope, not FDM process accuracy or guaranteed actual fit. Physical seating proceeds to actual contact and the adjustable stop must then be calibrated.'},
 'decision':{'enlarge_hex_required_by_this_flag':False,'new_CAD_or_reslice_required_by_this_flag':False,
 'reason':'No radial-fit or insertion-path obstruction was found under the unchanged conservative bead model; zero-clearance bearing contact cannot use the same strict clearance rule as a transit passage.',
 'if_exact_nominal_seat_is_required':'That accuracy is not established. Do not silently translate the official hardware or declare a precision datum. Treat actual bearing position/finish and stop calibration as physical limits rather than arbitrarily enlarging SW5.8.'},
 'limits':['Checks nominal metal envelope and emitted bead slabs, with original arc/buffer error budget retained.',
 'The 0.45 width straight segment has a strict interior overlap witness even without the extra error budget; bead geometry is a declaration envelope, not measured deposited polymer.',
 'Existing support must be removed before insertion. This review excludes tools, other hardware, supplier dimensional tolerances, deformed/sagged beads, seating force and bearing strength.',
 'Clear swept volume proves an available nominal approach to first contact; it does not certify exact full-face seating, process capability, assembly strength, or the complete mechanism.'],
 'source_sha256':{str(q.relative_to(ROOT)):hashlib.sha256(q.read_bytes()).hexdigest()for q in source_files},
 'manufacturing_release':False,'physical_acceptance':False}
(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')

# Bind the original report, data and explanatory classification for root aggregation.
report['source_sha256'][str(Path(__file__).resolve().relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
report['evidence_sha256']=dict(report['source_sha256'])
for name in ['README.md','raw-hits.json','swept-insertion.json']:
 q=OUT/name
 report['evidence_sha256'][str(q.relative_to(ROOT))]=hashlib.sha256(q.read_bytes()).hexdigest()
(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')

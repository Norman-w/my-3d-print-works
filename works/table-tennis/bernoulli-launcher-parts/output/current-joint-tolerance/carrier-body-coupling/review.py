#!/usr/bin/env python3
"""Continuous finite carrier/body coupling on an explicit normal branch.
No CAD changes, optimizer, pose grid, slicing or manufacturing certification.
"""
from pathlib import Path
from fractions import Fraction as F
import hashlib,json,math,re,sys
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'analysis'))
import frame_y_guide_bound as rounding
up=rounding.upper;down=rounding.lower;sl=rounding.sqrt_lower;su=rounding.sqrt_upper

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def fl(x):
 if isinstance(x,F):return float(x)
 if isinstance(x,dict):return{k:fl(v)for k,v in x.items()}
 if isinstance(x,(list,tuple)):return[fl(v)for v in x]
 return x
def atan_i(x,n=100):
 a=sum((-1)**k*x**(2*k+1)/F(2*k+1)for k in range(n));b=a+(-1)**n*x**(2*n+1)/F(2*n+1)
 return min(a,b),max(a,b)
a,b=atan_i(F(1,5));c,d=atan_i(F(1,239));PIhi=16*b-4*c
def coslo(x):return down(1-x*x/2+x**4/24-x**6/720)
C3=coslo(PIhi/60);S3=su(1-C3*C3)

def source_lit(file,key):
 t=(ROOT/'cad'/file).read_text();m=re.findall(r'^\s*'+re.escape(key)+r'\s*=\s*([-+\d.]+)\s*;',t,re.M);assert len(m)==1,(file,key);return F(m[0])
assert source_lit('cam-study.scad','cam_carrier_width')==9
assert source_lit('cam-study.scad','cam_carrier_axial')==8
assert source_lit('cam-study.scad','cam_carrier_inner_offset')==13
assert source_lit('cam-study.scad','cam_carrier_length')==15
for key,value in [('support_mount_x','35.5'),('support_radial_x1','58'),('support_radial_y0','-10'),('support_radial_y1','7.25'),('support_radial_half_z','7.5')]:
 assert source_lit('feeder-supports.scad',key)==F(value)
assert source_lit('feeder-supports.scad','support_radial_clearance')==F('.2')
assert source_lit('parameters.scad','radial_print_clearance')==F('.25')
assert source_lit('feeder-guide-revision.scad','revision_setting')==F('.9')
assert source_lit('feeder-guide-revision.scad','revision_front_retracted')==F('-5.5')
assert source_lit('feeder-guide-revision.scad','revision_datum_y')==F('4.5')
assert source_lit('feeder-guide-revision.scad','revision_datum_z0')==F('2.5')
assert source_lit('feeder-pin-seat-revision.scad','ps_lip_half_z')+source_lit('feeder-pin-seat-revision.scad','ps_clear')==3
assert source_lit('parameters.scad','finger_tip_radius')==F('2.5')
# K_i is centred for algebra at carrier-local a=(21.5,0,0), not at the tip.
# Both station16 and27 exist in the same15mm carrier; tip radialX is20..27.
L=F(11);halfL=L/2;H=F(4);Y=F('4.5');ZW=F('3.5');gL=F('.4');gT=F('.1');gZ=F('.4');centreDelta=F('.05')
ly=lz=C3
iterations=[]
for n in range(30):
 uyx=up(((gL+gT)/2+centreDelta+2*Y*(1-ly))/L)
 uyz=up((gT+2*Y*(1-ly))/(2*ZW))
 uzx=up((gZ/2+H*(1-lz))/halfL)
 uzy=up((uyz+uyx*uzx)/(1-uyx*uyx))
 uxz=up(uzx+uyx*uzy);uxy=up(uyx+uyz*uzx)
 lx=sl(1-uyx*uyx-uzx*uzx)
 ly=max(ly,sl(1-uyx*uyx-uyz*uyz));lz=max(lz,sl(1-uzx*uzx-uzy*uzy))
 iterations.append([lx,ly,lz,uyx,uyz,uzx,uzy,uxy,uxz])
# Interior-to-bootstrap proof uses trace to avoid an acos/degree roundoff gate.
angle_gate=lx+ly+lz>1+2*C3
cy=up(min(F('4.7')-Y*ly+halfL*uyx,F('.05')+F('4.55')-Y*ly+halfL*uyx));cz=up(F('4.2')-4*lz)
assert angle_gate and cy<1 and cz<1
axis_sin=su(uyx*uyx+uzx*uzx);axis_tan=up(axis_sin/lx)
# Finite contact-domain proof on the BROADER angle3deg, cY/cZ<=1 branch.
finite={
 'leading_Y_witness_world_X':[down(20+16*C3-8*S3),up(27+16+8*S3)],
 'trailing_Y_witness_world_X':[down(20+27*C3-8*S3),up(27+27+8*S3)],
 'leading_Z_witness_world_X':[down(20+16*C3-4*S3),up(27+16+4*S3)],
 'trailing_Z_witness_world_X':[down(20+27*C3-4*S3),up(27+27+4*S3)],
 'Z_witness_abs_Y_coarse_upper':up(1+F('9.5')*S3),
 'Z_witness_abs_Z_coarse_range':[down(4*C3-1-halfL*S3),up(4+1+halfL*S3)],
 'Y_witness_abs_Z_after_Z_constraint':[down(F('7.5')*C3-F('4.2')-Y*S3),up(F('4.2')-F('.5')*C3+Y*S3)],
 'Y_witness_abs_Y_coarse_upper':up(1+Y+9*S3)}
assert finite['leading_Y_witness_world_X'][0]>F('35.5') and finite['leading_Y_witness_world_X'][1]<F('43.6')
assert finite['trailing_Y_witness_world_X'][0]>F('44.3') and finite['trailing_Y_witness_world_X'][1]<F('57.3')
assert finite['Z_witness_abs_Y_coarse_upper']<F('4.5')
assert finite['Z_witness_abs_Z_coarse_range'][0]>F('2.25') and finite['Z_witness_abs_Z_coarse_range'][1]<F('7.5')
assert finite['Y_witness_abs_Z_after_Z_constraint'][0]>F('2.5') and finite['Y_witness_abs_Z_after_Z_constraint'][1]<F('4.1')
assert finite['Y_witness_abs_Y_coarse_upper']<F('7.25')
# The carrier rear hex has corner radius5.8/sqrt3 < witness absZ3.5.
assert source_lit('parameters.scad','nut_af')/sl(F(3))<ZW
rodR=F('2.5');holeR=F('2.75');rodRmin=down(rodR*coslo(PIhi/32));bodyGap=up(holeR-rodRmin)
body_stations=[F('31.6'),F('33.4')]
# Infinite-cylinder intersection is valid only if full oblique sections stay in
# the real localX[0,14] cylinder. Bound both ellipse-end axial deviations.
local_lo=down(body_stations[0]-27-rodR*axis_tan)
local_hi=up((body_stations[1]-20)/lx+rodR*axis_tan)
assert local_lo>0 and local_hi<14
D=body_stations[0]-20
B=up(bodyGap+D*axis_tan);Bround=up(F('.25')+D*axis_tan)
assert B<1
residual=down(1-B)
num={'matrix_diagonal_lower':{'Rxx':lx,'Ryy':ly,'Rzz':lz},'matrix_abs_upper':{'Ryx':uyx,'Ryz':uyz,'Rzx':uzx,'Rzy':uzy,'Rxy':uxy,'Rxz':uxz},'axis_angle_deg_upper_display_only':math.degrees(math.acos(float((lx+ly+lz-1)/2)))+1e-9,'rod_axis_to_support_X_tan_upper':axis_tan,'rod_axis_to_support_X_angle_deg_display_only':math.degrees(math.atan(float(axis_tan)))+1e-9,'carrier_reference_abs_Y_upper_mm':cy,'carrier_reference_abs_Z_upper_mm':cz,'strictly_inside_bootstrap_angle_and_offsets':True,'rod_full_cross_section_local_X_interval_mm':[local_lo,local_hi],'rod_guaranteed_inscribed_radius_lower_mm':rodRmin,'body_bore_radial_axis_room_upper_mm':bodyGap,'tip_transverse_YZ_norm_upper_mm_CURRENT_nominal_mesh':B,'tip_transverse_YZ_norm_upper_mm_ideal_round_rod_reference':Bround,'remaining_transverse_budget_to1_mm':residual,'axial_radial_lower_endpoint_extra_error_gain':axis_tan}
needles=[('cad/cam-study.scad','cylinder(h=cam_carrier_inner_offset+1'),('cad/cam-study.scad','cube([cam_carrier_length,cam_carrier_width,cam_carrier_axial])'),('cad/feeder-body.scad','side==1?31.5:-body_side_mount_x'),('cad/feeder-body.scad','side==1?33.5:-60'),('cad/feeder-body.scad','side==1?23.5:-33.5'),('cad/feeder-guide-revision.scad','revision_x0-revision_pocket_clearance,-14'),('cad/feeder-guide-revision.scad','revision_datum_lead'),('cad/feeder-pin-seat-revision.scad','ps_lip_half_z+ps_clear'),('cad/feeder-supports.scad','cam_carrier_width+2*support_radial_clearance')]
evidence=[]
for name,needle in needles:
 lines=(ROOT/name).read_text().splitlines();found=[{'path':name,'line':i+1,'text':x}for i,x in enumerate(lines)if needle in x];assert found,(name,needle);evidence.extend(found)
for name,needle in [('cad/launcher-final-assembly.scad','hc_support_clearance(1)yg_right_support()'),('cad/launcher-final-assembly.scad','ic_host_half(false);ic_host_half(true)'),('cad/feeder-return-spring.scad','translate([rs_x-nut_af/2,11.4-rs_eps,-11])'),('cad/feeder-frame-y-guide.scad','for(z=support_cap_screw_z)yg_ycyl'),('cad/feeder-hardware-clearance.scad','hc_x_cylinder(47.05,-14,z,45,7+2*hc_head_clearance)'),('cad/feeder-integrated-candidate.scad','sh_host_cuts(positive)'),('cad/cam-study.scad','r=finger_tip_radius,$fn=32)')]:
 lines=(ROOT/name).read_text().splitlines();hits=[{'path':name,'line':i+1,'text':x}for i,x in enumerate(lines)if needle in x];assert hits,(name,needle);evidence.extend(hits)
files={ROOT/x['path'] for x in evidence}|{ROOT/'cad/parameters.scad',ROOT/'analysis/frame_y_guide_bound.py',ROOT/'output/current-joint-tolerance/report.json',Path(__file__)}
scene_seen=set()
def include_graph(path):
 path=path.resolve()
 if path in scene_seen:return
 scene_seen.add(path);files.add(path)
 for name in re.findall(r'\b(?:include|use)\s*<([^>]+)>',path.read_text()):include_graph(path.parent/name)
include_graph(ROOT/'cad/cable-scene-export.scad')
hashes={str(p.relative_to(ROOT)):sha(p)for p in sorted(files)}
report={'status':'NEW_CONTINUOUS_FINITE_CARRIER_BODY_TRANSVERSE_BOUND_ON_EXPLICIT_NORMAL_SUBDOMAIN','task_id':'D02-carrier-body-coupling','new_result':num,'source_hashes':hashes,'source_evidence':evidence,'finite_back_substitution':finite,
 'domain':{'one_rigid_carrier':'The same K_i transforms both rod and actual carrier patches. Additional V/P_i/window/cam constraints can only shrink this set; no independent pin pose was used to gain a favourable result.','reference_origin_local':[21.5,0,0],'carrier_tip_body_X_mm':[20,27],'radial_X_scope':'Supplied finite subdomain, NOT inferred or certified by this proof. Covers nominal21..26 with1mm X allowance; cannot itself certify Bx<=1.','body_and_support_registration':'Mount faces remain seated with common X normal, so support/body relative rotation is aboutX and preserves rod-axis transverse norm; translations and roll are otherwise NOT set to zero.','normal_connected_branch':'Starts threaded through real outer body bearing and with carrier relative rotation<3deg, |cY|<1, |cZ|<1; continuous nonpenetration while radialX remains20..27. Proven bounds are strictly inside those angle/offset limits, so no first exit through them is possible. Arbitrary disconnected poses are not covered.','gib_setting':'Current parallel carrier gib source setting0.9: trailing gap[-4.6,4.5]. Old leading channel[-4.7,4.7]. Manufacturing/tilted-gib changes require new effective planes and finite coverage.','rigidity':'Current nominal straight rod rigidly joined to carrier; loaded deflection/form errors remain external parameters.'},
 'witnesses':{'Z_faces_local':{'x':[16,27],'y':[0],'z':[-4,4]},'Y_faces_local':{'x':[16,27],'y':[-4.5,4.5],'z':[-3.5,3.5]},'body_axis_sections_world_X':[31.6,33.4],'real_body_bearing_material_X':[31.5,33.5],'rod_local_axis_extent':[0,14]},
 'finite_material_audit':{'coordinate_note':'Right-side support-local coordinates, each gate translated toZ0. Support/body share X coordinate on the seated-normal branch. Left side uses the mirrored canonical coordinates.','leading_Y_planes':{'X':[35.5,43.6],'Y':[-4.7,4.7],'outer_material_Y':[-10,7.25]},'trailing_Y_planes':{'front_X':[44.3,57.3],'front_Y':4.5,'front_abs_Z':[2.5,4.1],'rear_X':[43.8,57.8],'rear_Y':-4.6,'rear_abs_Z':[2.1,4.1],'outer_material_Y':[-10.15,7.25]},'Z_planes':{'Z':[-4.2,4.2],'body_outer_Z':[-7.5,7.5],'witness_Y_is_outside_front_and_rear_cuts':True},'wrapper_cut_exclusions':['hc_support service cutters have Y<=-10.25; all witness-Y envelopes lie above that.','rs nut relief is atX-72, while mirrored witness absoluteX is35.56..54.42.','yg reopened cap screw axes are at|X|62.75; cg guide case cutters are outside the radial guide witness region.','sh/seam host cuts are atX near16/0, not the finite outer rod bearingX31.5..33.5. All current wrappers were read and their source hashes are included.'],'carrier_cut_exclusions':'Y-face witnesses absZ3.5 exceed the V/block ear cuts absZ3 and the original hex circumradius5.8/sqrt3; top/bottomZ4 witnesses likewise remain material.'},
 'continuous_derivation':['Let R map carrier to support axes, c be the transformed carrier-local point(21.5,0,0), and all diagonals be positive on the stated branch.','Z witnesses remain in real host material ranges: nonpenetration gives |cz|+5.5|Rzx|+4Rzz<=4.2. This first bounds Y-witness Z into the actual front/rear bands.','Set W=4.5Ryy+3.5|Ryz|. Leading station gives |cy-5.5Ryx|+W<=4.7; trailing station gives |cy+5.5Ryx+.05|+W<=4.55.','Consequently 9Ryy+7|Ryz|<=9.1 and |11Ryx+.05|+9Ryy+7|Ryz|<=9.25. Preserve these correlated inequalities; the printed matrix box is only an outer consequence.','Orthogonality gives |Rzy|<=(|Ryz|+|Ryx||Rzx|)/(1-|Ryx|²), |Rxz|<=|Rzx|+|Ryx||Rzy|, and diagonal square-root lower bounds. Outward rational iteration encloses every feasible matrix in the subdomain.','Support/body rotation aboutX preserves |axis_YZ| and axis_X. Same K_i therefore has body transverse slope <=tau=sqrt(Ryx²+Rzx²)/Rxx.','At each actual body section X31.6/33.4, the rod contains a disk of radius2.5cos(pi/32). Within the threaded normal branch the axis centre is in the hole outer disk eroded by this disk: ||a||,||b||<=2.75-rmin; b-a=1.8w, ||w||<=tau.','Tip centre is a-(31.6-tipX)w. Thus ||tip_YZ-body_bore_axis_YZ||<=bodyGap+(31.6-20)*tau, continuously for every eligible pose and every stroke position. No separate support-registration extremum or fixed-pin-window error is added to this direct point bound.'],
 'parameterized_remaining_allowance':{'inequality':'delta_body_hole_outward + delta_rod_inward + transverse_nonrigid_tip_error + tau*extra_radial_lower_endpoint_error <= remaining_transverse_budget_to1_mm','scope':'Only if stated effective carrier guide planes, finite contact patches, straight-cylinder engagement and common-X mounting normals remain valid. Carrier guide form changes also alter tau and cannot be hidden only in the final residual.','actual_parameter_values':None,'real_manufacturing_acceptance':False},
 'what_did_not_close':['This does not certify radialBx, shaft/form accuracy, retained V contact, common cam/slot endpoint phase or the physical ball-release process.','The bound is relative to the matching body-half bore axis. The two half/liner/ball-axis joint registration must still be handled by the root common-domain proof; do not add seam extrema and call them attainable.','No statement that matrix-box component maxima occur in the same actual configuration; only universal inequalities support the continuous bound.'],
 'comparison':'Earlier mount-only norm0.802717 was registration before local pin/window terms. The new bound is directly on the tip point after BOTH carrier and body constraints, so adding old registration or .25 fixed-window play would double-count the already constrained same point.','numerical_method':'Fraction arithmetic, outward1e-12 grid; pi enclosed by alternating Machin arctan; cosine lower bound by alternating Taylor. Degree values are displays only, first-exit certificate is diagonal trace inequality.','iterations':iterations,'all_sources_stable':all(sha(ROOT/p)==h for p,h in hashes.items()),'full_D02_closed':False,'manufacturing_release':False,'physical_acceptance':False}
(OUT/'report.json').write_text(json.dumps(fl(report),ensure_ascii=False,indent=2)+'\n')
print(json.dumps(fl(num),ensure_ascii=False));print('finite',json.dumps(fl(finite)));print('sources',report['all_sources_stable'])

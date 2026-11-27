from pathlib import Path
import hashlib,json,math
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
src=ROOT/'cad/cable-trigger-input.scad'
s=src.read_text().replace('ci_','cil_')
s='// Independent direct-pull / fixed fairlead diagnosis. NOT RELEASED.\ninclude <'+str(ROOT/'cad/parameters.scad')+'>\n'+s
s=s.replace('cil_part="assembly";','cil_part="none";')
s=s.replace('cil_theta_max=cil_stroke/cil_R*180/PI;','cil_theta_max=cil_angle(cil_stroke);')
s=s.replace('function cil_angle(u)=u/cil_R*180/PI;',r'''
// Fixed core centreline bend: R60, tangent to the existing axial bore.
// The .2 mm axial gap keeps the new guide clear of the metal end face.
cil_fairlead_C=[-28.8,0,2];
cil_fairlead_R=60;
cil_terminal=[0,60,2];
cil_cap_bolts=[[2,54],[2,66]];
function cil_B(a)=[60*sin(a),60*cos(a),2];
function cil_phi(a)=let(p=cil_B(a),x=p[0]+28.8,y=p[1],d=sqrt(x*x+y*y)) max(0,atan2(x,y)-acos(60/d));
function cil_T(a)=let(p=cil_phi(a))[-28.8+60*sin(p),60*cos(p),2];
function cil_path_length(a)=let(p=cil_B(a),x=p[0]+28.8,y=p[1]) .2+60*cil_phi(a)*PI/180+sqrt(x*x+y*y-3600);
function cil_takeup(a)=cil_path_length(a)-29;
function cil_angle(u,lo=0,hi=30,n=0)=n>=48?(lo+hi)/2:let(m=(lo+hi)/2)cil_takeup(m)<u?cil_angle(u,m,hi,n+1):cil_angle(u,lo,m,n+1);
function cil_effective_arm(u)=60*cos(cil_angle(u)-cil_phi(cil_angle(u)));
function cil_delta_max()=cil_angle(22)-cil_phi(cil_angle(22));
''')
# No unknown tip/seat is altered. Adopt the separately reviewed lower seat roots.
s=s.replace('cil_box(-45,-37,49,71,-8,12);','cil_box(-45,-37,49,71,-12,12);')
s=s.replace('cil_box(-42,-29,-34,-18,-8,12);','cil_box(-42,-29,-34,-18,-12,12);')
s=s.replace(' // Actual end stops: lug lives',r'''
 // Fixed R59.25 guide surface + .75 wire radius gives R60 centreline.
 // All additions grow from Z=-12. The back rib joins the existing M6 root.
 cil_box(-45,-20,49,55,-12,-4);
 cil_guide_solid();
 // Actual end stops: lug lives''')
start=s.index('module cil_local_lever_blank()')
end=s.index('module cil_local_cover_blank(',start)
s=s[:start]+r'''
module cil_direct_fan(z0=.9,z1=3.2){
 // Exact angular bound of terminal -> tangent line in rotating coordinates.
 // The .01 extra radial offset encloses polygonal/numeric error; no mesh welding.
 translate([0,60,z0])linear_extrude(height=z1-z0)offset(r=1.11,$fn=72)
 polygon(concat([[0,0]],[for(a=[180:.25:180+cil_delta_max()]) [65*cos(a),65*sin(a)]],
 [[65*cos(180+cil_delta_max()),65*sin(180+cil_delta_max())]]));
}
module cil_local_lever_blank(){union(){
 // Axis, finger silhouette and return-stop lug are preserved literally.
 cil_zcyl(0,0,-3.5,11,24);
 cil_web([0,0],[-4,-26],5.5,-3.5,7.5);
 cil_web([-4,-26],[1,-42],5,-3.5,7.5);
 cil_sector(10,22,177,183,-3.5,7.5);
 // The former spool spokes/rim are replaced by a 14 mm planar pull arm.
 cil_web([0,0],[0,54],7,-3.5,3.1);
 cil_web([0,54],[0,66],7,-3.5,3.1);
}}
module cil_local_lever_zero(){difference(){
 cil_local_lever_blank();
 cil_zcyl(0,0,-4,12,12.2);
 translate(cil_terminal)sphere(d=5.6);
 cil_zcyl(0,60,2,3,5.6); // upward load entry before cap installation
 cil_direct_fan();
 for(p=cil_cap_bolts){
  cil_zcyl(p[0],p[1],-4,9,3.4);
  cil_zhex(p[0],p[1],-3.6,3.0,5.8); // M3 nut roof at -.6; nut -.3? see hardware
 }
}}
module cil_local_terminal_cap(sweep=0){difference(){
 cil_web([0,54],[0,66],7,3.1,7.5+sweep);
 translate(cil_terminal)sphere(d=5.6);
 for(p=cil_cap_bolts){
  cil_zcyl(p[0],p[1],3,5+sweep,3.4);
  cil_zcyl(p[0],p[1],4.5+sweep,3.1,6.2);
 }
}}
module cil_local_lever(u=cil_u){rotate([0,0,-cil_angle(u)])cil_local_lever_zero();}
module cil_terminal_cap(u=cil_u){cil_to_cad()rotate([0,0,-cil_angle(u)])cil_local_terminal_cap();}
module cil_local_terminal_fasteners(){for(p=cil_cap_bolts){
 // Candidate standard M3x8 socket-head: D5.5 H3, SW2.5; M3 nut SW5.5 H2.4.
 cil_zbolt(p[0],p[1],4.5,8,3,5.5,3,2.5);
 difference(){cil_zhex(p[0],p[1],-3,2.4,5.5);cil_zcyl(p[0],p[1],-3.1,2.6,3.1);}
}}

'''+s[end:]
start=s.index('module cil_local_moving_hardware(')
end=s.index('// Explicit tool budget',start)
s=s[:start]+r'''
module cil_local_moving_hardware(u=cil_u){rotate([0,0,-cil_angle(u)]){
 cil_zring(0,0,-3.5,11,12,8.2);
 translate(cil_terminal)sphere(d=5);
 cil_local_terminal_fasteners();
}}
module cil_seg(a,b,d=1.5){hull(){translate(a)sphere(d=d,$fn=24);translate(b)sphere(d=d,$fn=24);}}
module cil_local_cable(u=cil_u){
 a=cil_angle(u);p=cil_phi(a);q=cil_T(a);b=cil_B(a);
 cil_xcyl(60,2,cil_ferrule_mouth_display,-28.8-cil_ferrule_mouth_display,1.5);
 if(p>.00001)translate(cil_fairlead_C)rotate([0,0,90-p])rotate_extrude(angle=p,$fn=7200)
  translate([60,0,0])circle(d=1.5,$fn=24);
 cil_seg(q,b,1.5);
}

'''+s[end:]
s=s.replace('module cil_moving(u=cil_u){cil_lever(u);cil_moving_hardware(u);}',
            'module cil_moving(u=cil_u){cil_lever(u);cil_terminal_cap(u);cil_moving_hardware(u);}')
s=s.replace('color([.12,.65,.85])cil_lever();','color([.12,.65,.85]){cil_lever();cil_terminal_cap();}')
# Do not expose inherited old wrap motion/terminal contracts as current APIs.
s=s.replace('function cil_spec()=[','function cil_legacy_wrap_spec_DO_NOT_USE()=[')
s=s.replace('module cil_contract(){echo(cil_contract=cil_spec());}','module cil_contract(){cil_direct_contract();}')
s=s.replace('module cil_probe(kind=cil_probe_kind,u=cil_u){','module cil_legacy_wrap_probe_DO_NOT_USE(kind=cil_probe_kind,u=cil_u){')
# Override inherited old spec and selectors with explicit diagnosis contract.
index=s.index('if(cil_part=="assembly")cil_assembly();')
s=s[:index]+r'''
module cil_guide_solid(){
 // Only this functional face uses .1 degree segmentation, not global $fn.
 translate([-28.8,0,-12])linear_extrude(height=19.5)polygon(concat(
  [for(i=[0:80])[59.25*cos(82+i*.1),59.25*sin(82+i*.1)]],
  [for(i=[80:-1:0])[53*cos(82+i*.1),53*sin(82+i*.1)]]));
}
module cil_direct_contract(){echo(cil_direct_contract=[
 ["status","DIAGNOSTIC_NOT_RELEASED"],["basis","feeder CAD"],["origin",cil_origin],
 ["preserved","axis stack, finger silhouette, mounting, M6 bore/seat, main cover"],
 ["changed","upper pull arm; terminal at local [0,60,2]; two-screw moving cap; fixed R60 fairlead"],
 ["fairlead_center",cil_fairlead_C],["fairlead_core_R",60],["fairlead_surface_R",59.25],
 ["u_samples",[for(u=[0,10,20,22])[u,cil_angle(u),cil_phi(cil_angle(u)),cil_path_length(cil_angle(u)),cil_effective_arm(u),36*sin(cil_angle(u))]]],
 ["cap_bolts",cil_cap_bolts],["cap_split_z",3.1],["cap_screw","2x M3x8 socket head; D5.5 H3"],
 ["cap_nut","2x M3 SW5.5 H2.4; z[-3,-.6]"],
 ["unknown","actual cable bend endurance, friction/preload, terminal shape tolerance, printed guide wear and layer surfaces"]]);}
if(cil_part=="assembly")cil_assembly();
else if(cil_part=="body")cil_body();
else if(cil_part=="lever")cil_lever();
else if(cil_part=="terminal-cap")cil_terminal_cap();
else if(cil_part=="cover")cil_cover();
else if(cil_part=="fixed-hardware")cil_fixed_hardware();
else if(cil_part=="moving-hardware")cil_moving_hardware();
else if(cil_part=="cable")cil_cable();
else if(cil_part=="contract")cil_direct_contract();
else if(cil_part!="none")assert(false,str("Unknown cil_part: ",cil_part));
'''
(OUT/'candidate.scad').write_text(s)
(OUT/'source-identity.json').write_text(json.dumps({'original':str(src),'original_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'candidate_sha256':hashlib.sha256(s.encode()).hexdigest(),'original_modified':False,'status':'DIAGNOSTIC_UNVALIDATED'},indent=2)+'\n')
print(OUT/'candidate.scad')

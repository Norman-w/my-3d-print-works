from pathlib import Path
import difflib,hashlib,json
R=Path(__file__).resolve().parents[4];O=Path(__file__).resolve().parent
p=R/'cad/cable-trigger-input.scad';s=p.read_text()
def replace(a,b):
 global s
 assert s.count(a)==1,(a[:100],s.count(a));s=s.replace(a,b)
replace('// Fixed-guide direct-pull input. Adopted from frozen v2 geometry; manufacturing open.','// Fixed-guide direct-pull input with HCDG8-30 pin / supplied NETW7 retention.\n// Engineering design adopted; installed E-clip form, load and physical acceptance open.')
replace('ci_origin=[75,-82,5];','ci_origin=[75,-85,5]; // Global host mounting holes and load faces remain unchanged.')
replace('ci_axis_sleeve_z=[-5.5,9.5];','''// Axis design source. Purchased geometry below is nominal display, not factory CAD.
ci_axis_pin_part="HCDG8-30";
ci_axis_clip_part="NETW7"; // supplied member of the pin kit, not an extra purchase
ci_axis_pin_q=.7; // display pose only; instantaneous allowed coaxial float is 0..1.54
ci_axis_pin_L=30.05; // under-head to NEAR groove wall
ci_axis_pin_N=3;
ci_axis_pin_groove_M=.95;
ci_axis_pin_groove_d=7.045;
ci_axis_pin_D=7.9905;
ci_axis_pin_head_D=12;
ci_axis_pin_head_T=2;
ci_axis_bore_D=8.3;
ci_axis_root_relief_D=9.2;
ci_axis_root_relief_z=[11.3,14.3];
ci_axis_tail_washer_part="HRDW-M8-A2";
ci_axis_tail_washer_od_id_t=[15,8.5,1.6];
ci_axis_tail_washer_z=[-15.2,-13.6];
ci_axis_thrust_part="SWSPS16-10-.25";
ci_axis_thrust_od_id_t=[16,10,.25];
ci_axis_thrust_z=[-3.75,7.5];
ci_bush_af=12;
ci_bush_socket_af=12.4;
ci_bush_id=8.2;
ci_bush_length=11;
ci_bush_edge=.05;
ci_bush_bore_edge=.1;''')
replace('["units","mm"],["status","direct-pull-adopted-manufacturing-open"],','["units","mm"],["status","eclip-axis-and-direct-pull-adopted-physical-acceptance-open"],')
replace(''' ["cover_axis_z",ci_axis_cover_z],["metal_sleeve_z",ci_axis_sleeve_z],
 ["metal_sleeve_od_id_length",[8,4.3,15]],["replaceable_bush_od_id_length",[12,8.2,11]],
 ["thrust_washer_od_id_t",[16,8.4,.25]],["total_axial_float",.5],''',''' ["cover_axis_z",ci_axis_cover_z],
 ["axis_design","HCDG8-30-grooved-pin-with-supplied-NETW7"],
 ["axis_pin_part",ci_axis_pin_part],["axis_clip_part",ci_axis_clip_part],
 ["axis_bom_columns",["id","part","quantity","accounting","nominal"]],["axis_bom",ci_axis_bom()],
 ["axis_pin_nominal",[["L_near_groove",ci_axis_pin_L],["N_tail",ci_axis_pin_N],
  ["groove_width",ci_axis_pin_groove_M],["groove_root_d",ci_axis_pin_groove_d],
  ["shaft_d",ci_axis_pin_D],["head_d",ci_axis_pin_head_D],["head_t",ci_axis_pin_head_T]]],
 ["axis_pin_catalog_bounds",[["L_near_groove",[30,30.1]],["shaft_g6_d",[7.986,7.995]],
  ["groove_width",[.9,1]],["groove_root_d",[7,7.09]],["head_t",[1.9,2.1]]]],
 ["axis_pin_display_q",ci_axis_pin_q],["axis_pin_q_domain_nominal_H26",[0,1.54]],
 ["axis_pin_capture_float_limit_nominal_H26",[.4,1.54]],
 ["axis_capture_span_bounds",[26.4,27.54]],["axis_plastic_outer_span_nominal",26],
 ["axis_actual_span_acceptance_requirement",[25.7,26.3]],
 ["axis_pin_capture_float_limit_at_required_actual_span",[.1,1.84]],
 ["axis_bore_d",ci_axis_bore_D],["axis_root_relief_d_z",[ci_axis_root_relief_D,ci_axis_root_relief_z]],
 ["axis_engineering_bounds_not_supplier_guarantees",[["head_d_max",16],["tail_N_max",6],
  ["root_d_max",9],["root_length_max",2.5],["washer_od_nominal",15],
  ["installed_clip_radius_max",10],["clip_axial_overhang_beyond_groove_max",1]]],
 ["axis_space_scope","coaxial nominal H26; q0..1.54 only; actual H acceptance does not enlarge verified envelope"],
 ["axis_clip_space_local_z",[-18.1,-13.46]],["axis_clip_space_role","reference requirement, NOT actual installed E-ring solid"],
 ["axis_clip_actual_installed_envelope_verified",false],
 ["axis_clip_insertion_removal_tool_verified",false],
 ["axis_tail_washer_part",ci_axis_tail_washer_part],
 ["axis_tail_washer_od_id_t",ci_axis_tail_washer_od_id_t],["axis_tail_washer_z",ci_axis_tail_washer_z],
 ["axis_tail_washer_bounds",[["ID",[8.4,8.62]],["thickness",[1.4,1.8]],["OD_nominal",15]]],
 ["bush_shape","hexagonal external; cylindrical bore; machined unfilled POM-C"],
 ["bush_af_id_length",[ci_bush_af,ci_bush_id,ci_bush_length]],
 ["bush_acceptance_requirements",[["AF",[11.97,12]],["ID",[8.2,8.25]],["L",[10.97,11]],
  ["bore_cylindricity_max",.02],["bore_to_hex_position_diameter_max",.05],
  ["end_parallelism_max",.02],["end_perpendicularity_to_bore_max",.03],
  ["outer_edge_break_max",ci_bush_edge],["bore_edge_break_max",ci_bush_bore_edge]]],
 ["bush_supplier_grade_confirmed",false],["bush_socket_af",ci_bush_socket_af],
 ["bush_socket_actual_acceptance_af",[12.2,12.6]],
 ["thrust_washer_part",ci_axis_thrust_part],["thrust_washer_od_id_t",ci_axis_thrust_od_id_t],
 ["thrust_washer_z",ci_axis_thrust_z],["thrust_washer_bounds",[["OD",[15.5,16]],["ID",[10,10.5]],["thickness",[.225,.275]]]],
 ["rotor_nominal_axial_float",.5],["rotor_float_semantics","12 mm inner cheek span minus 11 mm bush/lever and two .25 mm internal washers; independent of whole-pin capture float"],
 ["axis_adoption","engineering geometry and parts contract adopted; manufacturing and physical acceptance false"],
 ["axis_physical_acceptance",false],["manufacturing_release",false],''')
replace('["part_selectors",["assembly","body","lever","terminal-cap","cover","fixed-hardware","moving-hardware","adjuster","ferrule","cable","probe","contract"]]', '["part_selectors",["assembly","body","lever","terminal-cap","cover","fixed-hardware","moving-hardware","axis-pin","tail-washers","bush","thrust-washers","axis-space","eclip-space","adjuster","ferrule","cable","probe","contract"]]')
replace('module ci_contract(){echo(ci_contract=ci_spec());}', '''// Physical member count includes the supplied clip once; purchase roots do not.
function ci_axis_bom()=[
 ["axis-pin-kit",ci_axis_pin_part,1,"purchase-root-kit",[["supplied_clip",ci_axis_clip_part],["L_near_groove",ci_axis_pin_L]]],
 ["axis-supplied-clip",ci_axis_clip_part,1,"nonadditive-member-of-axis-pin-kit",[["actual_installed_geometry_verified",false]]],
 ["axis-tail-washer",ci_axis_tail_washer_part,2,"separate-purchase",[["OD_ID_t",ci_axis_tail_washer_od_id_t]]],
 ["axis-bush","machined-unfilled-POM-C",1,"machined-part-not-PETG-print",[["AF_ID_L",[ci_bush_af,ci_bush_id,ci_bush_length]]]],
 ["axis-thrust-washer",ci_axis_thrust_part,2,"separate-purchase",[["OD_ID_t",ci_axis_thrust_od_id_t]]]
];
module ci_contract(){echo(ci_contract=ci_spec());}''')
replace(''' ci_zcyl(0,0,-13,28,4.5);
 ci_zcyl(0,0,-5.5,1.6,8.3); // steel spacer end seat, NOT the rotating bearing''',''' ci_zcyl(0,0,-13,28,ci_axis_bore_D); // free through pin; no old distance-tube seat''')
# Hex socket contains the old round hole exactly, matching ar_lever_zero.
replace(' ci_zcyl(0,0,-4,12,12.2);',' translate([0,0,-4])linear_extrude(height=12)ci_bush_hex_2d(ci_bush_socket_af);')
replace(''' ci_zcyl(0,0,7,8+sweep,4.5);
 ci_zcyl(0,0,7.9,1.6,8.3);''',''' ci_zcyl(0,0,7,8+sweep,ci_axis_bore_D);
 // For +Z continuous cover removal, the wider recess remains only at the
 // leading outer end; lower shifted small-bore material fills its old location.
 ci_zcyl(0,0,ci_axis_root_relief_z[0]+sweep,
   ci_axis_root_relief_z[1]-ci_axis_root_relief_z[0],ci_axis_root_relief_D);''')
replace(' // Original nuts/host washers remain in parent. THESE replace old screws.',' // Original four host nuts remain in parent. Replace old screws AND their washers once.')
replace('''module ci_local_fixed_hardware(delta=ci_delta){
 // Precision steel distance tube supports both cheeks and carries clamp load.
 ci_zring(0,0,-5.5,15,8,4.3);
 for(z=[-3.75,7.5])ci_zring(0,0,z,.25,16,8.4);
 ci_zbolt(0,0,14.8,35,4,7,4,3);
 ci_zring(0,0,14,.8,9,4.3);
 ci_zring(0,0,-12.8,.8,9,4.3);
 difference(){ci_zhex(0,0,-16,3.2,7);ci_zcyl(0,0,-16.1,3.4,4.1);}
''','''// Other fixed hardware excludes all central axis parts and global mount bolts.
module ci_local_other_fixed_hardware(delta=ci_delta){
''')
replace('''module ci_local_moving_hardware(u=ci_u){rotate([0,0,-ci_angle(u)]){
 ci_zring(0,0,-3.5,11,12,8.2);
 translate(ci_terminal)sphere(d=5);
 ci_local_terminal_fasteners();
}}''','''module ci_bush_hex_2d(af=ci_bush_af){rotate(30)circle(d=af/cos(30),$fn=6);}
module ci_local_bush_zero(){z=2-ci_bush_length/2;difference(){
 union(){
  translate([0,0,z])linear_extrude(height=ci_bush_edge,scale=ci_bush_af/(ci_bush_af-2*ci_bush_edge))ci_bush_hex_2d(ci_bush_af-2*ci_bush_edge);
  translate([0,0,z+ci_bush_edge])linear_extrude(height=ci_bush_length-2*ci_bush_edge)ci_bush_hex_2d();
  translate([0,0,z+ci_bush_length-ci_bush_edge])linear_extrude(height=ci_bush_edge,scale=(ci_bush_af-2*ci_bush_edge)/ci_bush_af)ci_bush_hex_2d();
 }
 ci_zcyl(0,0,z-.01,ci_bush_length+.02,ci_bush_id);
 translate([0,0,z])cylinder(h=ci_bush_bore_edge,d1=ci_bush_id+2*ci_bush_bore_edge,d2=ci_bush_id);
 translate([0,0,z+ci_bush_length-ci_bush_bore_edge])cylinder(h=ci_bush_bore_edge,d1=ci_bush_id,d2=ci_bush_id+2*ci_bush_bore_edge);
}}
module ci_local_axis_ring(z,h,od,id){difference(){
 ci_zcyl(0,0,z,h,od);ci_zcyl(0,0,z-.01,h+.02,id);
}}
// Catalogue nominal pin only, not supplier exact shape or a clearance proof.
module ci_local_axis_pin(q=ci_axis_pin_q){
 zhead=14+q;
 difference(){union(){
  ci_zcyl(0,0,zhead-ci_axis_pin_L-ci_axis_pin_N,ci_axis_pin_L+ci_axis_pin_N,ci_axis_pin_D);
  ci_zcyl(0,0,zhead,ci_axis_pin_head_T,ci_axis_pin_head_D);
 }
 ci_local_axis_ring(zhead-ci_axis_pin_L-ci_axis_pin_groove_M,ci_axis_pin_groove_M,ci_axis_pin_head_D+1,ci_axis_pin_groove_d);
 // These under-head relief dimensions are reference dimensions, not tolerances.
 ci_local_axis_ring(zhead-1.5,1.5,ci_axis_pin_head_D+1,7.75);
}}
module ci_local_tail_washers(){for(z=ci_axis_tail_washer_z)
 ci_local_axis_ring(z,ci_axis_tail_washer_od_id_t[2],ci_axis_tail_washer_od_id_t[0],ci_axis_tail_washer_od_id_t[1]);}
module ci_local_thrust_washers(){for(z=ci_axis_thrust_z)
 ci_local_axis_ring(z,ci_axis_thrust_od_id_t[2],ci_axis_thrust_od_id_t[0],ci_axis_thrust_od_id_t[1]);}
module ci_local_fixed_axis_hardware(){ci_local_axis_pin();ci_local_tail_washers();ci_local_thrust_washers();}
module ci_local_fixed_hardware(delta=ci_delta){ci_local_fixed_axis_hardware();ci_local_other_fixed_hardware(delta);}
module ci_local_bush(u=ci_u){rotate([0,0,-ci_angle(u)])ci_local_bush_zero();}
module ci_local_other_moving_hardware(u=ci_u){rotate([0,0,-ci_angle(u)]){
 translate(ci_terminal)sphere(d=5);ci_local_terminal_fasteners();
}}
module ci_local_moving_hardware(u=ci_u){ci_local_bush(u);ci_local_other_moving_hardware(u);}
// Engineering acceptance SPACE only. Never union these volumes into real hardware.
module ci_local_eclip_space(){ci_zcyl(0,0,-18.1,4.64,20/cos(180/72));}
module ci_local_axis_space(){k=1/cos(180/72);
 ci_zcyl(0,0,-22.1,37.64,8*k);ci_zcyl(0,0,11.5,4.04,9*k);
 ci_zcyl(0,0,14,3.64,16*k);ci_local_axis_ring(-17.1,5.1,15*k,8.4);
}''')
replace('module ci_body(){ci_to_cad()ci_local_body();}','''module ci_axis_pin(){ci_to_cad()ci_local_axis_pin();}
module ci_tail_washers(){ci_to_cad()ci_local_tail_washers();}
module ci_thrust_washers(){ci_to_cad()ci_local_thrust_washers();}
module ci_bush(u=ci_u){ci_to_cad()ci_local_bush(u);}
module ci_axis_space(){ci_to_cad()ci_local_axis_space();}
module ci_eclip_space(){ci_to_cad()ci_local_eclip_space();}
module ci_body(){ci_to_cad()ci_local_body();}''')
# Remove stale duplicate diagnostic contract; public authoritative source is ci_spec.
a=s.index('module ci_direct_contract(){');b=s.index('\nif(ci_part=="assembly")',a)
s=s[:a]+'''// Compatibility echo entry with the SAME current contract, not old axis claims.
module ci_direct_contract(){echo(ci_direct_contract=ci_spec());}
'''+s[b:]
replace('else if(ci_part=="cable")ci_cable();','''else if(ci_part=="axis-pin")ci_axis_pin();
else if(ci_part=="tail-washers")ci_tail_washers();
else if(ci_part=="bush")ci_bush();
else if(ci_part=="thrust-washers")ci_thrust_washers();
else if(ci_part=="axis-space")ci_axis_space();
else if(ci_part=="eclip-space")ci_eclip_space();
else if(ci_part=="cable")ci_cable();''')
p.write_text(s)
p=R/'cad/cable-housing-route.scad';s=p.read_text();assert s.count('cr_side_run=195;')==1;s=s.replace('cr_side_run=195;','cr_side_run=198; // input origin -Y3; keep second/third virtual corners and output fixed.')
s=s.replace('cr_side_run==195','cr_side_run==198');s=s.replace(' ["route_law","fixed-third-arc-equal-length-v1"],',' ["route_law","fixed-third-arc-equal-length-v1"],\n    ["nominal_input_run",cr_input_run],["nominal_side_run",cr_side_run],["nominal_apex_z",cr_apex_z],')
s=s.replace('module cr_require_valid(){','module cr_require_valid(){\n    assert(cr_get(ci_spec(),"origin")==[75,-85,5],"Reviewed input-offset route requires its adopted origin");')
p.write_text(s)
p=R/'cad/cable-scene-export.scad';s=p.read_text();needle='    else if(part=="input-wire")ci_cable(cse_input_u(t));';assert s.count(needle)==1;s=s.replace(needle,'''    // Independent reference budget; NEVER an actual E-clip mesh or printable part.
    else if(part=="input-eclip-space")ci_eclip_space();
    else if(part=="input-axis-space")ci_axis_space();
    else if(part=="input-axis-pin")ci_axis_pin();
    else if(part=="input-tail-washers")ci_tail_washers();
    else if(part=="input-thrust-washers")ci_thrust_washers();
    else if(part=="input-bush")ci_bush(cse_input_u(t));
'''+needle);p.write_text(s)
paths=['cad/cable-trigger-input.scad','cad/cable-housing-route.scad','cad/cable-scene-export.scad']
diff=''.join(''.join(difflib.unified_diff((O/'frozen-baseline'/n).read_text().splitlines(True),(R/n).read_text().splitlines(True),fromfile='before/'+n,tofile='after/'+n))for n in paths)
(O/'adoption.patch').write_text(diff)
print(json.dumps({n:hashlib.sha256((R/n).read_bytes()).hexdigest()for n in paths},indent=2))

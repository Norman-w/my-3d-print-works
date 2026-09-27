// Read-only service envelopes for the frozen ci/co candidates. Units mm.
// All public geometry is in feeder CAD coordinates. No printable part added.
use <cable-trigger-input.scad>
use <cable-output-interface.scad>
cs_part="contract";
cs_t=0;
cs_stop_setting=20;
$fn=72;
function cs_get(s,k)=s[search([k],s)[0]][1];
function cs_input_holes()=cs_get(ci_spec(),"mount_holes_cad");
function cs_underhead()=cs_get(ci_spec(),"mount_bolt_underhead_y");
function cs_tip()=cs_get(ci_spec(),"mount_bolt_tip_y");
function cs_head_face()=cs_underhead()-4;
function cs_contract_data()=[
 ["units","mm"],["basis","feeder CAD"],
 ["tool_status","clearance budgets; purchased drive/tool geometry not certified"],
 ["input_mount_tool_direction",[0,1,0]],["input_mount_head_face_y",cs_head_face()],
 ["input_mount_tool_budget",["3mm hex, round shaft OD4, shaft length80"]],
 ["input_mount_bolt_remove_direction",[0,-1,0]],["input_mount_bolt_remove_distance",60],
 ["input_module_key_release_direction",[0,-1,0]],["input_module_key_release_distance",6],
 ["input_module_remove_prerequisites","output core released and pulled clear; housing disconnected/parked; mount bolts and intermediate retainers removed"],
 ["input_cover_remove_direction",[0,1,0]],["input_cover_remove_distance",25],
 ["input_cover_remove_prerequisites","whole input module off host on bench; axis/cover screws and corresponding hardware removed"],
 ["input_stop_tool_local_direction",[1,0,0]],
 ["input_stop_locknut_tool_budget",["SW5.5, thickness3, headOD12, straight entry30; not purchased tool",[-28.9,-25.9]]],["input_stop_tool_setting_range",[16,22]],
 ["output_service_pose",0],["output_cap_remove_direction",[0,1,0]],["output_cap_remove_distance",35],
 ["output_cap_bolt_remove_distance",16],
 ["output_washer_remove_direction",[0,1,0]],["output_washer_remove_distance",35],
 ["output_nipple_remove_direction",[0,1,0]],["output_nipple_remove_distance",35],
 ["output_nipple_remove_prerequisites","cap and washer off; M4 clamp loose; steel core tail pulled completely out of the closed transverse bore"],
 ["output_clamp_drive","unmarked slot dimensions; generic OD3.4 driver is a budget only"],
 ["housing_test_scope","fixed installed housing allowed for tools, bolts, output cap/washer; not a constraint for disconnected module or bench cover motion"],
 ["disclaimer","nominal service paths do not certify screw protrusion, actual tools, flexible cable deformation or loaded handling"]
];
module cs_contract(){echo("CS_CONTRACT",cs_contract_data());}

// Four independently accessible straight shafts; no hull between four holes.
// Hex tips fit the modeled sockets, not a declaration of actual driver supply.
module cs_input_mount_tools(reach=80){
 for(p=cs_input_holes()){
  ci_ycyl(p[0],p[2],cs_head_face()-reach,reach,4);
  ci_yhex(p[0],p[2],cs_head_face(),1.9,2.9);
 }
}
// Continuous translation union of each original bolt's shaft and head.
// Full 60 mm withdraws its tip past Y=-94 rear plate; washers removed with it.
module cs_input_mount_bolt_sweep(travel=60,with_washers=true){
 assert(travel>=0);
 for(p=cs_input_holes()){
  ci_ycyl(p[0],p[2],cs_underhead()-travel,cs_tip()-cs_underhead()+travel,4);
  ci_ycyl(p[0],p[2],cs_head_face()-travel,4+travel,7);
  if(with_washers)difference(){
   ci_ycyl(p[0],p[2],cs_underhead()-travel,.8+travel,9);
   ci_ycyl(p[0],p[2],cs_underhead()-travel-.02,.84+travel,4.3);
  }
 }
}
// Reuses the frozen local stop geometry. Enter from local -X / CAD(+X,-Z).
// This checks the hex-driver path only, NOT access to the external locknut.
module cs_input_stop_tools(setting=cs_stop_setting,entry_local_x=-100){
 assert(setting>=16&&setting<=22);
 sx=ci_stop_tip(setting);
 ci_to_cad(){
  ci_xcyl(-24,2,entry_local_x,sx-33-entry_local_x,4);
  translate([sx-33,-24,2])rotate([0,90,0])rotate([0,0,30])
   cylinder(h=1.5,d=2.5/cos(30),$fn=6);
 }
}
// External M3 locknut, nominal SW5.5. Open end faces local +Y and enters
// from local -Y. sweep is a CONTINUOUS translation, not sampled positions.
// Tool envelope includes an explicit handle, but its real supply is unresolved.
module cs_input_stop_locknut_tool(sweep=30){ci_to_cad(){
 x=-28.9;
 difference(){
  hull(){ci_xcyl(-24,2,x,3,12);ci_xcyl(-24-sweep,2,x,3,12);}
  ci_box(x-.1,x+3.1,-27.3,100,-.85,4.85);
 }
 ci_box(x,x+3,-69-sweep,-29,-.5,4.5);
}}
module cs_input_adjuster_tools(){ci_to_cad()for(i=[0,1])ci_local_adjuster_tool(i,25);}
// Exact rigid pose only. Caller must not hold a connected housing fixed.
// ci_local_fixed_hardware deliberately excludes the four removed mount bolts.
module cs_input_module_pose(retreat=0,u=0){translate([0,-retreat,0]){
 ci_body();ci_cover();ci_lever(u);ci_terminal_cap(u);
 ci_to_cad()ci_local_fixed_hardware();ci_moving_hardware(u);
}}
// Bench-local continuous cover sweep. Actual cover screws/axis bolt removed.
// Coordinates kept at the original datum for comparison to local module ONLY.
module cs_input_bench_cover_sweep(travel=25){ci_to_cad()ci_local_cover(travel);}

// co_tools() is composite; use these subsets to avoid mixing disassembly stages.
module cs_output_cap_tools(t=cs_t,reach=40){co_move(t)
 for(x=[-62.5,-51])co_ycyl(x,26,46.75,reach,4);
}
module cs_output_clamp_tool(t=cs_t,reach=50){co_move(t)co_ycyl(-58,15,39.05,reach,3.4);}
module cs_output_adjuster_lower_tool(){difference(){
 co_lower_wrench_outer();co_zhex(-58,35.5,77.98,7.04,10.2);
}}
module cs_output_cap_bolt_sweep(t=cs_t,travel=16){co_move(t)
 for(x=[-62.5,-51]){
  co_ycyl(x,26,27.7,16+travel,3);
  co_ycyl(x,26,43.7,3+travel,5.5);
  difference(){co_ycyl(x,26,43.2,.5+travel,7);co_ycyl(x,26,43.18,.54+travel,3.2);}
 }
}
// Native cap travel is exact straight swept geometry, including notch/bore.
module cs_output_cap_sweep(t=cs_t,travel=35){co_lug_cap(t,travel);}
// Solid conservative outer envelopes, rather than filling any nearby scene.
// all_float=true includes nominal seat radial float and max washer thickness.
module cs_output_washer_sweep(t=cs_t,travel=35,all_float=true){co_move(t)
 if(all_float)co_ycyl(-58,14.7,39,.9+travel,9.8);
 else co_ycyl(-58,15,39.1,.8+travel,9);
}
module cs_output_nipple_sweep(t=cs_t,travel=35){co_nipple_envelope(t,travel);}
// Unbounded protrusion is NOT silently included in the nipple's D5 body.
// Choose end_y beyond the measured scene bound to test an outward corridor.
module cs_output_screw_exit(end_y=1000,t=cs_t){co_screw_exit_ray(t,end_y);}

if(cs_part=="contract")cs_contract();
else if(cs_part=="input-mount-tools")cs_input_mount_tools();
else if(cs_part=="input-mount-bolts")cs_input_mount_bolt_sweep();
else if(cs_part=="input-stop-tools")cs_input_stop_tools();
else if(cs_part=="input-stop-locknut-tool")cs_input_stop_locknut_tool();
else if(cs_part=="input-adjuster-tools")cs_input_adjuster_tools();
else if(cs_part=="input-module")cs_input_module_pose(6);
else if(cs_part=="input-bench-cover")cs_input_bench_cover_sweep();
else if(cs_part=="output-cap-tools")cs_output_cap_tools();
else if(cs_part=="output-clamp-tool")cs_output_clamp_tool();
else if(cs_part=="output-cap-bolts")cs_output_cap_bolt_sweep();
else if(cs_part=="output-cap")cs_output_cap_sweep();
else if(cs_part=="output-washer")cs_output_washer_sweep();
else if(cs_part=="output-nipple")cs_output_nipple_sweep();
else if(cs_part=="output-screw-exit")cs_output_screw_exit();
else assert(false,str("Unknown cable service selector: ",cs_part));

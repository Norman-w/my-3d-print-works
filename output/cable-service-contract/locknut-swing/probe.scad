// Independent continuous angular bound, source components remain frozen.
use <../../../cad/cable-trigger-input.scad>
use <../../../cad/cable-service-contract.scad>
u=0;
mode="collision";
step=.5;
fn_round=144;
angle_lo=-15;
angle_hi=15;
max_radius=sqrt(45*45+2.5*2.5);
// Each actual angle is <=step/2 from a sample. Two points at equal radius
// differ by <=2Rsin(step/4); dilate only YZ, since rotation preserves X.
delta=2*max_radius*sin(step/4);
source_guard=.001; // conservative reconstruction guard, independently tested below
offset_radius=(delta+source_guard)/cos(180/fn_round); // circumscribed offset arc facets
$fn=72;
module tool_2d(){
 difference(){circle(d=12);translate([-2.85,-3.3])square([5.7,100]);}
 translate([-2.5,-45])square([5,40]);
}
module tool_at(a=0,inflated=false,radius=offset_radius){ci_to_cad()
 translate([-28.9-(inflated?.001:0),-24,2])rotate([0,90,0])linear_extrude(height=3+(inflated?.002:0))
 rotate(a)if(inflated)offset(r=radius,$fn=fn_round)tool_2d();else tool_2d();
}
module continuous_tool(){ci_to_cad()
 // .001 axial expansion makes containment stricter and avoids coplanar sheets.
 translate([-28.901,-24,2])rotate([0,90,0])linear_extrude(height=3.002)
 union()for(a=[angle_lo:step:angle_hi])rotate(a)
 offset(r=offset_radius,$fn=fn_round)tool_2d();
}
module target_nut(){ci_to_cad()difference(){
 translate([-29,-24,2])rotate([0,90,0])rotate([0,0,30])cylinder(h=2.4,d=5.5/cos(30),$fn=6);
 ci_xcyl(-24,2,-29.1,2.6,3.1);
}}
module obstacles(){
 ci_body();ci_cover();ci_lever(u);ci_moving_hardware(u);
 difference(){ci_fixed_hardware();target_nut();}
}
if(mode=="collision")intersection(){continuous_tool();obstacles();}
else if(mode=="positive-control")intersection(){continuous_tool();union(){obstacles();ci_to_cad()translate([-27.5,-65,2])sphere(d=5,$fn=24);}}
else if(mode=="source-parity")union(){
 difference(){tool_at();cs_input_stop_locknut_tool(0);}
 difference(){cs_input_stop_locknut_tool(0);tool_at();}
}
else if(mode=="source-containment")difference(){cs_input_stop_locknut_tool(0);tool_at(0,true,source_guard/cos(180/fn_round));}
else if(mode=="target-engagement")intersection(){continuous_tool();target_nut();}
else if(mode=="envelope")continuous_tool();
else if(mode=="scene"){
 color([.2,.4,.55])ci_body();color([.2,.7,.8,.3])ci_cover();color([.2,.65,.8])ci_lever(u);
 color([.7,.7,.72]){ci_fixed_hardware();ci_moving_hardware(u);}
 color([.95,.65,.1,.55])continuous_tool();
}
else if(mode=="contract")echo(step=step,angle_range=[angle_lo,angle_hi],max_radius=max_radius,delta=delta,offset_radius=offset_radius,tool_x=[-28.9,-25.9]);
else assert(false,"Unknown swing probe mode");

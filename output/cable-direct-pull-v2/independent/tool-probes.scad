// Bench-service budgets only; not a purchased-tool specification.
include </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/cable-direct-pull-v2/candidate.scad>
it_kind="sw8-motion";
it_fault=false;
it_loose_gap=.2;
it_tool_t=3;
it_handle_end=70; // radial handle extent from head axis; not overall tool length.
it_torque_deg=60;
it_torque_start=0; // UPWARD service sector only; -60..60 had a real rib collision.
it_step_deg=2;
// Max handle point radius sqrt(70^2+3^2); this outward planar offset exceeds
// the exact 2-degree chord sagitta, and covers continuous rotation per segment.
it_chord_cover=.011;
assert(it_chord_cover*cos(180/24)>=sqrt(70*70+3*3)*(1-cos(it_step_deg/2)));

module it_common_obstacles(){
 cdp_local_body();
 cdp_local_lever(0);cdp_local_terminal_cap();
 cdp_local_moving_hardware(0);
 // Cover and its fasteners are conceptually removed. Retaining those distant
 // fasteners here is conservative; neither is used to make an access claim.
 difference(){cdp_local_fixed_hardware(0);
  cdp_local_adjuster(0);cdp_local_ferrule(0);
  for(x=cdp_adjuster_nut_x)cdp_xnut(x,10,cdp_adjuster_nut_t,6.1);
 }
 if(it_fault)cdp_box(-62,-57,59,61,8,9);
}
// A fully rotating AF10 nut inside its circumscribed envelope and a continuous
// max .2 mm retreat. No housing/head is claimed to be in this nut's volume.
module it_loose_nut_envelope(i){
 x=cdp_adjuster_nut_x[i];sgn=i==0?-1:1;
 cdp_xcyl(60,2,x+min(0,sgn*it_loose_gap),cdp_adjuster_nut_t+it_loose_gap,
          10/cos(30)/cos(180/72));
}
module it_sw8_outer_motion(){
 // Head plane x[-61,-58]+delta for delta[-2,2]. Fixed angular orientation:
 // SW8 counterholds while the nuts produce the axial change.
 hull(){cdp_xcyl(60,2,-63,7,18);cdp_xcyl(85,2,-63,7,18);}
 cdp_box(-63,-56,69,155,-1,5);
}
module it_sw8_entry(delta){
 x=-61+delta;
 difference(){
  hull(){cdp_xcyl(60,2,x,3,18);cdp_xcyl(85,2,x,3,18);}
  cdp_box(x-.1,x+3.1,-100,66,-2.2,6.2); // nominal SW8 + .4 total opening.
 }
 cdp_box(x,x+3,69,155,-1,5);
}
function it_rot(p,a)=[p[0]*cos(a)-p[1]*sin(a),p[0]*sin(a)+p[1]*cos(a)];
module it_handle_profile(){
 // profile coordinates are [-localZ_relative, localY_relative] for rotateY90.
 for(a=[it_torque_start:it_step_deg:it_torque_deg-it_step_deg])offset(r=it_chord_cover,$fn=24)hull(){
  for(ang=[a,a+it_step_deg])polygon([for(p=[[9,-3],[70,-3],[70,3],[9,3]])
   let(q=it_rot(p,ang))[-q[1],q[0]]]);
 }
}
module it_head_entry_profile(){
 // All head centres move out radially by up to 25 mm at any working angle.
 // Circumscribed offset also covers the angular arc chord and nominal OD20.
 for(a=[it_torque_start:it_step_deg:it_torque_deg-it_step_deg])offset(r=10.011/cos(180/72),$fn=72)hull(){
  for(ang=[a,a+it_step_deg],r=[0,25])translate([-r*sin(ang),r*cos(ang)])circle(r=.0001,$fn=12);
 }
}
module it_sw10_upper_entry_outer(i){
 x=cdp_adjuster_tool_x[i];
 translate([x,60,2])rotate([0,90,0])linear_extrude(height=3)it_head_entry_profile();
 // A retreating handle reaches radius 95. Its 2-degree chord error is .0145,
 // covered by .015 mm (including the round-offset polygon support factor).
 translate([x,60,2])rotate([0,90,0])linear_extrude(height=3)
 for(a=[it_torque_start:it_step_deg:it_torque_deg-it_step_deg])offset(r=.015,$fn=72)hull(){
  for(ang=[a,a+it_step_deg])polygon([for(p=[[9,-3],[95,-3],[95,3],[9,3]])
   let(q=it_rot(p,ang))[-q[1],q[0]]]);
 }
}
module it_sw10_torque_outer(i){
 x=cdp_adjuster_tool_x[i];
 // A complete OD20 disk conservatively contains the rotating fork head;
 // its intentional nut/shaft area is excluded from the obstacle set.
 cdp_xcyl(60,2,x,3,20/cos(180/72));
 translate([x,60,2])rotate([0,90,0])linear_extrude(height=3)it_handle_profile();
}
module it_other_nut(i){it_loose_nut_envelope(1-i);}
module it_target_fits(){
 // Nominal opening fit only. Real jaw widths and fitting AF remain unverified.
 for(d=[-2,0,2])intersection(){it_sw8_entry(d);cdp_local_adjuster(d);}
 for(i=[0,1],gap=[0,it_loose_gap])intersection(){
  cdp_local_adjuster_tool(i,25);
  cdp_xnut(cdp_adjuster_nut_x[i]+(i==0?-gap:gap),10,3.2,6.1);
 }
}
if(it_kind=="sw8-motion")intersection(){it_sw8_outer_motion();union(){
 it_common_obstacles();for(i=[0,1])it_loose_nut_envelope(i);
}}
else if(it_kind=="sw10-entry")intersection(){
 union(){for(i=[0,1])cdp_local_adjuster_tool(i,25);}
 union(){it_common_obstacles();for(d=[-2,0,2])cdp_local_adjuster(d);
  // Before straight insertion, reindex the wrench to the actual nut flats.
  for(i=[0,1])cdp_xhex(60,2,cdp_adjuster_nut_x[i]-(i==0?it_loose_gap:0),3.2+it_loose_gap,10);
 }
}
else if(it_kind=="sw10-torque")for(i=[0,1])intersection(){it_sw10_torque_outer(i);union(){
 it_common_obstacles();it_other_nut(i);
 // The circular shaft is inside the fork opening; the remote hex head is a
 // separate obstacle and has no axial overlap with either wrench plane.
 for(d=[-2,2])translate([d,0,0])cdp_xhex(60,2,-63,10,8);
}}
else if(it_kind=="sw10-upper-entry")for(i=[0,1])intersection(){it_sw10_upper_entry_outer(i);union(){
 it_common_obstacles();it_other_nut(i);
 for(d=[-2,2])translate([d,0,0])cdp_xhex(60,2,-63,10,8);
}}
else if(it_kind=="loose-nut")intersection(){union(){for(i=[0,1])it_loose_nut_envelope(i);}it_common_obstacles();}
else if(it_kind=="loose-nut-printed")intersection(){union(){for(i=[0,1])it_loose_nut_envelope(i);}
 union(){cdp_local_body();cdp_local_lever(0);cdp_local_terminal_cap();}}
else if(it_kind=="target-fit")it_target_fits();
else if(it_kind=="sw8-budget")it_sw8_outer_motion();
else if(it_kind=="sw10-budget")for(i=[0,1])it_sw10_torque_outer(i);
else assert(false,"Unknown independent tool probe");

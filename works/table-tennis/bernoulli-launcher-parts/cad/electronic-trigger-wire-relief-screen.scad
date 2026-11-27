// Wire-strain-relief screen for the selected signal trigger beam.
// Two 3 mm through-holes on the fixed backplate admit a nominal 2.5 mm tie.
// The translucent lead route is a clearance envelope, not purchased wire or
// an installed loom. et_beam() now contains the two selected tie holes.
use <electronic-trigger-candidate.scad>
use <electric-feeder-trigger-assembly.scad>
use <electric-feeder-assembly.scad>
use <feeder-optical-home.scad>

wr_part = "probe"; // probe, beam, context
wr_probe = "lead-beam";
wr_angle = 0;
wr_feed_t = 0;
wr_hole_x = [42.5,48.5];
wr_hole_z = -13.5;
wr_hole_d = 3;
wr_tie_nominal_width = 2.5;
wr_lead_d = 2;
wr_bundle_d = 4;
// T18R catalogue head is 4.45 x 4.8 x 3.7 mm. Check a larger keep-out
// so an equivalent 2.5-mm tie can be selected without crowding moving parts.
wr_tie_head_clearance_x = 5.5;
wr_tie_head_clearance_z = 5.8;
wr_tie_head_clearance_y = 4.7;

assert(wr_hole_x[0]-wr_hole_d/2-39 >= 2);
assert(wr_hole_x[1]-wr_hole_x[0]-wr_hole_d >= 3);
assert(-18-(wr_hole_z-wr_hole_d/2) <= -3);
assert(wr_tie_nominal_width<wr_hole_d);

module wr_box(x0,x1,y0,y1,z0,z1){
    translate([x0,y0,z0])cube([x1-x0,y1-y0,z1-z0]);
}
module wr_ball(p,d){translate(p)sphere(d=d,$fn=24);}
module wr_segment(a,b,d){hull(){wr_ball(a,d);wr_ball(b,d);}}
module wr_holes(){et_wire_tie_holes();}
module wr_beam(){et_beam();}
module wr_leads(){
    // All three D3-tab positions are kept as a conservative space envelope.
    // COM/NO assignment, solder sleeves, real bend radius and cable routing
    // after this fixed relief point are not represented by these cylinders.
    for(z=[-5.58,-.5,4.58])
        wr_segment([40.5,-52,z],[38,-52,z],wr_lead_d);
    wr_segment([38,-52,4.58],[38,-52,-13.5],wr_bundle_d);
    wr_segment([38,-52,-13.5],[45.5,-52,-13.5],wr_bundle_d);
}
module wr_tie_envelope(){
    // 2.5 mm strip proxy. The legs pass through the 3 mm backplate holes;
    // front/back spans conservatively bound a small bundle without claiming
    // a particular tie-head footprint or installation access.
    for(x=wr_hole_x)et_y_cyl(x,wr_hole_z,-60.2,12,wr_tie_nominal_width);
    wr_box(wr_hole_x[0],wr_hole_x[1],-60.2,-59.2,
           wr_hole_z-wr_tie_nominal_width/2,
           wr_hole_z+wr_tie_nominal_width/2);
    wr_box(wr_hole_x[0],wr_hole_x[1],-49.2,-48.2,
           wr_hole_z-wr_tie_nominal_width/2,
           wr_hole_z+wr_tie_nominal_width/2);
    // Put the locking head on the outside front of the left hole. This
    // enlarged box includes the catalogue head and a modest assembly margin.
    wr_box(wr_hole_x[0]-wr_tie_head_clearance_x/2,
           wr_hole_x[0]+wr_tie_head_clearance_x/2,
           -48.2,-48.2+wr_tie_head_clearance_y,
           wr_hole_z-wr_tie_head_clearance_z/2,
           wr_hole_z+wr_tie_head_clearance_z/2);
}
module wr_other_fixed(){ed_fixed_without_beam();oh_left_cap();}
module wr_other_moving(){ed_moving_printed(wr_feed_t);et_lever(wr_angle);}
module wr_probe_geometry(){
    if(wr_probe=="lead-beam")intersection(){wr_leads();wr_beam();}
    else if(wr_probe=="lead-switch-body")intersection(){wr_leads();et_switch_body();}
    else if(wr_probe=="lead-other-fixed")intersection(){wr_leads();wr_other_fixed();}
    else if(wr_probe=="lead-other-moving")intersection(){wr_leads();wr_other_moving();}
    else if(wr_probe=="tie-beam")intersection(){wr_tie_envelope();wr_beam();}
    else if(wr_probe=="tie-switch-body")intersection(){wr_tie_envelope();et_switch_body();}
    else if(wr_probe=="tie-other-fixed")intersection(){wr_tie_envelope();wr_other_fixed();}
    else if(wr_probe=="tie-other-moving")intersection(){wr_tie_envelope();wr_other_moving();}
    else if(wr_probe=="hole-switch-body")intersection(){wr_holes();et_switch_body();}
    else if(wr_probe=="hole-pivot")intersection(){wr_holes();et_pivot_reference();}
    else if(wr_probe=="hole-original-positive-control")intersection(){wr_holes();et_beam_without_wire_relief();}
    else if(wr_probe=="original-minus-beam-positive-control")difference(){et_beam_without_wire_relief();wr_beam();}
    else if(wr_probe=="beam-minus-original")difference(){wr_beam();et_beam_without_wire_relief();}
    else assert(false,"Unknown wire-relief probe");
}

if(wr_part=="probe")wr_probe_geometry();
else if(wr_part=="beam")wr_beam();
else if(wr_part=="context"){
    color([.18,.45,.68])intersection(){
        wr_beam();wr_box(34,84,-64,-41,-45,12);
    }
    color([.96,.40,.11])et_lever(wr_angle);
    color([.1,.1,.12])et_switch_reference();
    color([.78,.25,.14,.65])wr_leads();
    color([.95,.82,.25,.55])wr_tie_envelope();
    et_pivot_reference();
}
else assert(false,"Unknown wire-relief part");

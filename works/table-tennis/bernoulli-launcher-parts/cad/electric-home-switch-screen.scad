// Packaging screen only: an independent mechanical-zero switch at the right
// upper carriage stop. Units are mm. Nothing here is a selected printed part.
// The existing fixed guide top and moving shoulder remain the load-bearing
// stop; this proposed tab only touches the D2F plunger beside that stop.
use <electric-feeder-trigger-assembly.scad>
use <electric-feeder-assembly.scad>
use <electronic-trigger-candidate.scad>
use <feeder-optical-home.scad>
use <feeder-return-spring.scad>
use <outlet-retention.scad>
use <inlet-retention-final.scad>

hs_part = "probe"; // probe, context, switch, tab
hs_probe = "switch-fixed";
hs_t = 0; // 0..1 maps to 0..20 mm; zero is against the fixed upper stop

// Omron D2F-01F-D3 catalogue outline: case 12.8 x 5.8 x about 5.0,
// operating plunger height 5.5 +/- 0.3 above the case datum. The three D3
// solder tabs are deliberately over-bounded by a continuous underside slab.
hs_case_x = 58.5;
hs_case_y = 42;
hs_case_z = 0.45;
hs_case_l = 12.8;
hs_case_w = 5.8;
hs_case_h = 5;
hs_plunger_dx = 1.2;
hs_plunger_x = hs_case_x + hs_plunger_dx;
hs_plunger_y = hs_case_y + hs_case_w/2;
hs_tab_z0 = 5.8;
hs_tab_z1 = 9;
hs_tab_x0 = 54;
hs_tab_y0 = 23.5;
hs_tab_end_margin = 1.6;

assert(hs_t >= 0 && hs_t <= 1);

module hs_box(x0,x1,y0,y1,z0,z1) {
    translate([x0,y0,z0]) cube([x1-x0,y1-y0,z1-z0]);
}
module hs_case() {
    hs_box(hs_case_x,hs_case_x+hs_case_l,hs_case_y,hs_case_y+hs_case_w,
           hs_case_z,hs_case_z+hs_case_h);
}
module hs_solder_clearance() {
    // Conservative terminal/wire-start space, not an Omron terminal drawing.
    hs_box(hs_case_x,hs_case_x+hs_case_l,
           hs_case_y+hs_case_w/2-.5,hs_case_y+hs_case_w/2+.5,
           hs_case_z-3.5,hs_case_z);
}
module hs_non_actuating_envelope() {
    // Full free plunger bound also has to clear the existing selected parts.
    hs_case(); hs_solder_clearance(); hs_plunger_free_bound();
}
module hs_plunger_free_bound() {
    // Maximum catalogue OP + maximum pretravel = 5.8 + 0.5 = 6.3.
    translate([hs_plunger_x,hs_plunger_y,hs_case_z+hs_case_h-.02])
        cylinder(h=1.32,d=2.2,$fn=48);
}
module hs_nominal_operating_marker() {
    translate([hs_plunger_x,hs_plunger_y,hs_tab_z0])
        cylinder(h=.15,d=2.2,$fn=48);
}
module hs_tab(t=hs_t) {
    // Root intersects the existing upper shoulder X=53..59,Y=19..25,Z=5..9.
    // The 0.8 mm vertical gap over the fixed guide is nominal only.
    translate([0,0,20*t])
        hs_box(hs_tab_x0,hs_plunger_x+hs_tab_end_margin,
               hs_tab_y0,hs_plunger_y+hs_tab_end_margin,
               hs_tab_z0,hs_tab_z1);
}
module hs_selected_hardware(t=hs_t) {
    ed_fixed_hardware(); ed_moving_hardware(t);
    oh_sensor_reference(); et_switch_reference(); et_pivot_reference();
    et_spring_reference(0); rs_spring(t); or_pipe(); ir_hose_reference();
}
module hs_probe_geometry() {
    if(hs_probe=="switch-fixed")
        intersection(){hs_non_actuating_envelope();it_fixed_printed();}
    else if(hs_probe=="switch-moving")
        intersection(){hs_non_actuating_envelope();it_moving_printed(hs_t,0);}
    else if(hs_probe=="switch-hardware")
        intersection(){hs_non_actuating_envelope();hs_selected_hardware(hs_t);}
    else if(hs_probe=="tab-fixed")
        intersection(){hs_tab(hs_t);it_fixed_printed();}
    else if(hs_probe=="tab-hardware")
        intersection(){hs_tab(hs_t);hs_selected_hardware(hs_t);}
    else if(hs_probe=="zero-contact")
        intersection(){hs_tab(hs_t);hs_nominal_operating_marker();}
    else if(hs_probe=="one-mm-free-clearance")
        intersection(){hs_tab(hs_t);hs_plunger_free_bound();}
    else if(hs_probe=="tab-root-control")
        intersection(){hs_tab(hs_t);it_moving_printed(hs_t,0);}
    else assert(false,"Unknown home-switch probe");
}

if(hs_part=="probe") hs_probe_geometry();
else if(hs_part=="switch") hs_non_actuating_envelope();
else if(hs_part=="tab") hs_tab();
else if(hs_part=="context") {
    color([.70,.74,.77,.55]) it_assembly(hs_t,0);
    color([.13,.13,.14]) hs_case();
    color([.72,.72,.74]) hs_solder_clearance();
    color([.85,.18,.12]) hs_plunger_free_bound();
    color([.98,.75,.12]) hs_tab(hs_t);
}
else assert(false,"Unknown home-switch screen part");

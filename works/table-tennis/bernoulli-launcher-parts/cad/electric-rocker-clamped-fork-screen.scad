// Split-clamp Y=65 fork screen for the 6 mm catalog pivot pin.
// The M2 hardware is only a conservative placement envelope. Clamp force,
// printed compliance, fatigue and pin slip have not been measured.
use <electric-rocker-pivot-mount-screen.scad>
use <electric-rocker-pivot-joint-screen.scad>
use <electric-rocker-bridge-screen.scad>
use <electric-rocker-pin-retention-screen.scad>
use <electric-end-switch-side-cap.scad>
use <electric-feeder-trigger-assembly.scad>
use <electric-home-switch-screen.scad>

cf_part = "probe";
cf_probe = "bracket-moving";
cf_t = 0;
pm_pivot_y = 65;
rb_plane_y = 65;
cf_x = 85-sqrt(75*75-15*15);
cf_pivot_z = 25;
cf_ears = [[58,61],[69,73]];
cf_slit_width = 1.2;
cf_slit_z0 = 28;
cf_slit_z1 = 42.1;
cf_bolt_z = 36.5;
cf_bolt_clearance_d = 2.25;
cf_head_envelope_d = 4.5;
cf_nut_envelope_d = 5;
cf_nut_trap_af = 4.3; // M2 steel hex nut: 4 mm AF plus nominal pocket allowance
cf_nut_trap_x0 = 21.8;
cf_nut_trap_x1 = 24.1;
cf_beam_extra_bottom = -18;

assert(cf_t>=0 && cf_t<=1);
assert(cf_ears[0][0]==pm_pivot_y-7 && cf_ears[1][1]==pm_pivot_y+8);
assert(cf_bolt_z-cf_bolt_clearance_d/2-(cf_pivot_z+6.4/2)>2.5);

module cf_pad_pair(y0,y1){
    // Left screw head bears here; the +X boss captures a steel hex nut.
    pm_box(1.5,7,y0,y1,31,40);
    pm_box(16,21.5,y0,y1,29,40);
    if(y0<60)
        pm_box(18,24,56,63,33,42);
    else
        pm_box(18,24,67,76,33,42);
}
module cf_nut_trap(y){
    // Hex socket opens to +X for insertion before the motor is fitted.
    translate([cf_nut_trap_x0,y,cf_bolt_z])rotate([0,90,0])
        cylinder(h=cf_nut_trap_x1-cf_nut_trap_x0,
                 d=cf_nut_trap_af/cos(30),$fn=6);
}
module cf_bracket(){difference(){
    union(){
        pm_bracket();
        // Deepen the original 3 x 7 mm low beam without entering its M3 bores.
        pm_box(7,10,40,pm_pivot_y+8,cf_beam_extra_bottom,-14);
        for(pair=cf_ears)cf_pad_pair(pair[0],pair[1]);
    }
    for(pair=cf_ears){
        pm_box(cf_x-cf_slit_width/2,cf_x+cf_slit_width/2,
               pair[0]-.1,pair[1]+.1,cf_slit_z0,cf_slit_z1);
        pm_xcyl(1,24.1,(pair[0]+pair[1])/2,cf_bolt_z,
                 cf_bolt_clearance_d);
        cf_nut_trap((pair[0]+pair[1])/2);
    }
}}
module cf_fasteners(){
    for(pair=cf_ears){
        y=(pair[0]+pair[1])/2;
        color([.60,.62,.66]){
            pm_xcyl(1.5,26.5,y,cf_bolt_z,2);
            pm_xcyl(-.5,1.5,y,cf_bolt_z,cf_head_envelope_d);
            // Nominal M2 hex nut: 4 mm across flats, 1.6 mm thick.
            translate([cf_nut_trap_x0,y,cf_bolt_z])rotate([0,90,0])
                cylinder(h=1.6,d=4/cos(30),$fn=6);
        }
    }
}
module cf_driver_access(){
    for(pair=cf_ears)
        pm_xcyl(-25,-.5,(pair[0]+pair[1])/2,cf_bolt_z,4.5);
}
module cf_nut_access(){
    for(pair=cf_ears)
        pm_xcyl(24,80,(pair[0]+pair[1])/2,cf_bolt_z,cf_nut_envelope_d);
}
module cf_moving(){it_moving_printed(cf_t,0);ss_tabs(cf_t);}
module cf_fixed(){ss_other_fixed();ss_cap();}
module cf_rocker(){pj_rocker();}
module cf_bushing(){pj_bushing();}
module cf_shaft(){pr_ycyl(58,76.1,6);}
module cf_probe_geometry(){
    if(cf_probe=="bracket-moving")intersection(){cf_bracket();cf_moving();}
    else if(cf_probe=="bracket-moving-clearance-1mm")intersection(){
        minkowski(){cf_bracket();sphere(r=1,$fn=24);}cf_moving();
    }
    else if(cf_probe=="bracket-fixed")intersection(){cf_bracket();cf_fixed();}
    else if(cf_probe=="bracket-hardware")intersection(){
        cf_bracket();
        difference(){hs_selected_hardware(cf_t);pm_existing_anchor_heads();}
    }
    else if(cf_probe=="bracket-rocker")intersection(){cf_bracket();cf_rocker();}
    else if(cf_probe=="bracket-rocker-clearance-0p5")intersection(){
        minkowski(){cf_bracket();sphere(r=.5,$fn=24);}cf_rocker();
    }
    else if(cf_probe=="bracket-bushing")intersection(){cf_bracket();cf_bushing();}
    else if(cf_probe=="bracket-shaft")intersection(){cf_bracket();cf_shaft();}
    else if(cf_probe=="rocker-bushing")intersection(){cf_rocker();cf_bushing();}
    else if(cf_probe=="rocker-shaft")intersection(){cf_rocker();cf_shaft();}
    else if(cf_probe=="bushing-shaft")intersection(){cf_bushing();cf_shaft();}
    else if(cf_probe=="bracket-bridge")intersection(){cf_bracket();rb_output_bridge();}
    else if(cf_probe=="bracket-motor")intersection(){cf_bracket();rb_motor_proxy();}
    else if(cf_probe=="bracket-switch")intersection(){cf_bracket();ss_switches();}
    else if(cf_probe=="fasteners-moving")intersection(){cf_fasteners();cf_moving();}
    else if(cf_probe=="fasteners-fixed")intersection(){cf_fasteners();cf_fixed();}
    else if(cf_probe=="fasteners-bracket")intersection(){cf_fasteners();cf_bracket();}
    else if(cf_probe=="fasteners-rocker")intersection(){cf_fasteners();cf_rocker();}
    else if(cf_probe=="fasteners-bushing")intersection(){cf_fasteners();cf_bushing();}
    else if(cf_probe=="fasteners-bridge")intersection(){cf_fasteners();rb_output_bridge();}
    else if(cf_probe=="fasteners-motor")intersection(){cf_fasteners();rb_motor_proxy();}
    else if(cf_probe=="fasteners-pin-ends")intersection(){
        cf_fasteners();
        union(){pr_front_head_envelope();pr_rear_ring_tip_envelope();}
    }
    else if(cf_probe=="driver-moving")intersection(){cf_driver_access();cf_moving();}
    else if(cf_probe=="driver-fixed")intersection(){cf_driver_access();cf_fixed();}
    else if(cf_probe=="driver-rocker")intersection(){cf_driver_access();cf_rocker();}
    else if(cf_probe=="driver-bridge")intersection(){cf_driver_access();rb_output_bridge();}
    else if(cf_probe=="driver-motor")intersection(){cf_driver_access();rb_motor_proxy();}
    else if(cf_probe=="nut-moving")intersection(){cf_nut_access();cf_moving();}
    else if(cf_probe=="nut-fixed")intersection(){cf_nut_access();cf_fixed();}
    else if(cf_probe=="nut-rocker")intersection(){cf_nut_access();cf_rocker();}
    else if(cf_probe=="nut-bridge")intersection(){cf_nut_access();rb_output_bridge();}
    else if(cf_probe=="nut-motor")intersection(){cf_nut_access();rb_motor_proxy();}
    else if(cf_probe=="positive-control")intersection(){cf_bracket();cf_bracket();}
    else if(cf_probe=="raw-rocker-shaft-positive-control")intersection(){
        rb_rocker();cf_shaft();
    }
    else assert(false,"Unknown split-clamp fork probe");
}
if(cf_part=="probe")cf_probe_geometry();
else if(cf_part=="bracket")cf_bracket();
else if(cf_part=="rocker-phase")cf_rocker();
else if(cf_part=="context"){
    color([.68,.72,.76,.18])cf_fixed();
    color([.96,.53,.17,.45])cf_moving();
    color([.95,.20,.16,.12])rb_motor_proxy();
    color([.16,.52,.82])cf_bracket();
    color([.19,.72,.39])cf_rocker();
    color([.92,.80,.28])cf_bushing();
    color([.9,.7,.2])rb_output_bridge_visual();
    color([.61,.63,.68]){cf_fasteners();cf_shaft();pr_front_head_envelope();
                             pr_rear_ring_tip_envelope();}
}
else if(cf_part=="detail"){
    color([.16,.52,.82])cf_bracket();
    color([.19,.72,.39])cf_rocker();
    color([.92,.80,.28])cf_bushing();
    color([.61,.63,.68]){cf_fasteners();cf_shaft();pr_front_head_envelope();
                             pr_rear_ring_tip_envelope();}
}
else assert(false,"Unknown split-clamp fork part");

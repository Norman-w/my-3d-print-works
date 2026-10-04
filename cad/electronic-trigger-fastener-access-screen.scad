// M2 switch fastening and calibration access on the selected signal trigger.
// Nominal catalogue/standard envelopes only; no purchased hardware implied.
use <electronic-trigger-candidate.scad>
use <electric-feeder-assembly.scad>

fa_part = "probe"; // probe, context
fa_probe = "shaft-mount";
fa_shift = 0;      // selected switch must calibrate within +/-1 mm
fa_angle = 0;      // 0 released, -8 pulled
fa_feed = 0;       // 0..1, 20 mm feeder travel

fa_hole_x = 43.988+1.5+fa_shift;
fa_hole_z = [-6.9+3.15,-6.9+3.15+6.5];
fa_shank_start_y = -59.9; // under head; first 0.9 mm passes the washer
fa_shank_length = 14;
fa_plate_rear_y = -59;
fa_washer_od = 7; // wide-series M2 washer, e.g. ISO 7093 / DIN 9021
fa_washer_id = 2.2;
fa_switch_front_y = -49.2;
fa_nut_thickness = 1.6; // M2 full-nut envelope; verify purchased hardware
fa_head_top_y = -61.9; // ISO 4762 M2 socket head is 2 mm tall
fa_driver_start_y = -90;
fa_nut_tool_end_y = -25;

assert(fa_shift>=-1.4 && fa_shift<=1.4);
assert(fa_angle>=-8 && fa_angle<=0);
assert(fa_feed>=0 && fa_feed<=1);

module fa_ycyl(x,z,y0,y1,d,fn=48) {
    translate([x,y0,z])rotate([-90,0,0])
        cylinder(h=y1-y0,d=d,$fn=fn);
}
module fa_yhex(x,z,y0,y1,af) {
    translate([x,y0,z])rotate([-90,0,0])rotate([0,0,30])
        cylinder(h=y1-y0,d=af/cos(30),$fn=6);
}
module fa_shanks() {
    for(z=fa_hole_z)
        fa_ycyl(fa_hole_x,z,fa_shank_start_y,
                 fa_shank_start_y+fa_shank_length,2);
}
module fa_heads() {
    for(z=fa_hole_z) {
        fa_ycyl(fa_hole_x,z,fa_head_top_y,fa_shank_start_y,3.8);
    }
}
module fa_washers() {
    // Wide M2 washer annulus, with real 0.9-mm axial thickness.
    for(z=fa_hole_z)
        difference() {
            fa_ycyl(fa_hole_x,z,fa_shank_start_y,fa_plate_rear_y,
                    fa_washer_od);
            fa_ycyl(fa_hole_x,z,fa_shank_start_y-.01,fa_plate_rear_y+.01,
                    fa_washer_id);
        }
}
module fa_head_stacks() {fa_heads();fa_washers();}
module fa_nuts() {
    for(z=fa_hole_z)
        fa_yhex(fa_hole_x,z,fa_switch_front_y,
                fa_switch_front_y+fa_nut_thickness,4);
}
module fa_driver_access() {
    for(z=fa_hole_z)
        fa_ycyl(fa_hole_x,z,fa_driver_start_y,fa_head_top_y,4);
}
module fa_nut_tool_access() {
    // A 6-mm circular envelope screens a small nut driver above each M2 nut.
    for(z=fa_hole_z)
        fa_ycyl(fa_hole_x,z,fa_switch_front_y+fa_nut_thickness,
                fa_nut_tool_end_y,6);
}
module fa_switch_bored() {
    // The earlier display proxy had a solid case; only the maker's two M2
    // through-holes are subtracted here to test shaft routing.
    difference() {
        et_switch_body();
        for(z=fa_hole_z)
            fa_ycyl(fa_hole_x,z,-55.1,-49.1,2.2);
    }
}
module fa_existing_fixed() { ed_fixed_printed(); }
module fa_existing_moving() { ed_moving_printed(fa_feed); }
module fa_other_fixed() { difference(){fa_existing_fixed();et_beam();} }

module fa_probe_geometry() {
    if(fa_probe=="shaft-mount")intersection(){fa_shanks();et_mount();}
    else if(fa_probe=="shaft-switch")intersection(){fa_shanks();fa_switch_bored();}
    else if(fa_probe=="shaft-lever")intersection(){fa_shanks();et_lever(fa_angle);}
    else if(fa_probe=="head-beam")intersection(){fa_head_stacks();et_beam();}
    else if(fa_probe=="head-lever")intersection(){fa_head_stacks();et_lever(fa_angle);}
    else if(fa_probe=="head-other-fixed")intersection(){fa_head_stacks();fa_other_fixed();}
    else if(fa_probe=="head-moving")intersection(){fa_head_stacks();fa_existing_moving();}
    else if(fa_probe=="nut-beam")intersection(){fa_nuts();et_beam();}
    else if(fa_probe=="nut-lever")intersection(){fa_nuts();et_lever(fa_angle);}
    else if(fa_probe=="nut-other-fixed")intersection(){fa_nuts();fa_other_fixed();}
    else if(fa_probe=="nut-moving")intersection(){fa_nuts();fa_existing_moving();}
    else if(fa_probe=="nut-terminals")intersection(){fa_nuts();et_switch_terminals();}
    else if(fa_probe=="driver-beam")intersection(){fa_driver_access();et_beam();}
    else if(fa_probe=="driver-lever")intersection(){fa_driver_access();et_lever(fa_angle);}
    else if(fa_probe=="driver-other-fixed")intersection(){fa_driver_access();fa_other_fixed();}
    else if(fa_probe=="driver-moving")intersection(){fa_driver_access();fa_existing_moving();}
    else if(fa_probe=="nut-tool-beam")intersection(){fa_nut_tool_access();et_beam();}
    else if(fa_probe=="nut-tool-lever")intersection(){fa_nut_tool_access();et_lever(fa_angle);}
    else if(fa_probe=="nut-tool-other-fixed")intersection(){fa_nut_tool_access();fa_other_fixed();}
    else if(fa_probe=="nut-tool-moving")intersection(){fa_nut_tool_access();fa_existing_moving();}
    else if(fa_probe=="nut-tool-terminals")intersection(){fa_nut_tool_access();et_switch_terminals();}
    else if(fa_probe=="head-self-control")intersection(){fa_heads();fa_heads();}
    else if(fa_probe=="washer-self-control")intersection(){fa_washers();fa_washers();}
    else assert(false,"Unknown switch fastener probe");
}

if(fa_part=="probe")fa_probe_geometry();
else if(fa_part=="context") {
    color([.15,.45,.69,.35])et_beam();
    color([.96,.42,.10,.80])et_lever(fa_angle);
    color([.12,.13,.15])fa_switch_bored();
    color([.70,.72,.75]){fa_shanks();fa_head_stacks();fa_nuts();}
    color([.15,.86,.92,.25])fa_driver_access();
    color([.82,.30,.90,.25])fa_nut_tool_access();
}
else assert(false,"Unknown switch fastener screen part");

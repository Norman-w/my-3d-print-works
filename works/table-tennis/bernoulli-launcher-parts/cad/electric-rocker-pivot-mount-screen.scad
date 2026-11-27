// Fixed rocker-pivot mount candidate, millimetres. SCREEN ONLY.
// X1C/PETG concept: a removable, +X-side bracket shares the two existing
// +Y seam-screw stations at Z=16 and -10. It does not cut the air chamber or
// bridge the X=0 split. The original two M3 screws must be replaced by longer
// screws; their clamp load, PETG creep and the actual motor force are OPEN.
// The Y-axis pivot is held between two cheeks. A metal shaft and bushings,
// their retention, and the rocker pivot bore are NOT yet designed.
use <electric-rocker-bridge-screen.scad>
use <electric-end-switch-side-cap.scad>
use <electric-feeder-trigger-assembly.scad>
use <feeder-complete-hardware.scad>
use <electric-home-switch-screen.scad>

pm_part = "probe"; // probe, bracket, context
pm_probe = "bracket-fixed";
pm_t = 0;
pm_pivot_x = 85-sqrt(75*75-15*15);
pm_pivot_y = 62;
pm_pivot_z = 25;
pm_anchor_x0 = 7;
pm_anchor_x1 = 14;
pm_anchor_y = 40;
pm_anchor_z = [-10,16];
pm_cheek_y = [[pm_pivot_y-7,pm_pivot_y-4],
              [pm_pivot_y+4,pm_pivot_y+8]];
pm_pivot_bore_d = 6.4; // space candidate, not a shaft/bushing selection
pm_screw_clearance_d = 3.5;
pm_head_counterbore_d = 6.2;
pm_head_under_x = 10.8;
pm_replacement_screw_underhead_length = 20;
pm_clearance = 1;

assert(pm_t>=0 && pm_t<=1);
assert(pm_anchor_x0==7 && pm_anchor_y==40);
assert((pm_pivot_y==62 || pm_pivot_y==65) && pm_pivot_z==25);
assert(pm_cheek_y[0][1]<pm_pivot_y-2.5 &&
       pm_cheek_y[1][0]>pm_pivot_y+2.5);

module pm_box(x0,x1,y0,y1,z0,z1){
    translate([x0,y0,z0])cube([x1-x0,y1-y0,z1-z0]);
}
module pm_xcyl(x0,x1,y,z,d){
    translate([x0,y,z])rotate([0,90,0])
        cylinder(h=x1-x0,d=d,$fn=64);
}
module pm_ycyl(y0,y1,x,z,d){
    translate([x,y0,z])rotate([-90,0,0])
        cylinder(h=y1-y0,d=d,$fn=64);
}

module pm_anchor_web(){
    // The Y=40 shell bosses have outer X face at +7. Both bolt pads remain
    // on that one half, with a 26 mm Z spread to resist pivot overturning.
    hull()for(z=pm_anchor_z)
        pm_xcyl(pm_anchor_x0,pm_anchor_x1,pm_anchor_y,z,10);
}
module pm_cantilever(){
    // The first straight diagonal collided with the moving frame at Y48..54
    // during the first quarter-stroke. Carry load on a low beam instead, then
    // rise only beyond the frame's current +Y envelope.
    pm_box(7,10,40,pm_pivot_y+8,-14,-7);
    for(pair=pm_cheek_y)
        pm_box(7,10,pair[0],pair[1],-14,17);
}
module pm_cheek(y0,y1){
    // A broad circular seat around the bore plus a low gusset to the beam.
    hull(){
        pm_ycyl(y0,y1,pm_pivot_x,pm_pivot_z,18);
        pm_box(7,13,y0,y1,11,17);
    }
}
module pm_bracket_blank(){
    union(){
        pm_anchor_web();
        pm_cantilever();
        for(pair=pm_cheek_y)pm_cheek(pair[0],pair[1]);
    }
}
module pm_bracket(){difference(){
    pm_bracket_blank();
    for(z=pm_anchor_z){
        pm_xcyl(pm_anchor_x0-.1,pm_anchor_x1+.1,
                 pm_anchor_y,z,pm_screw_clearance_d);
        pm_xcyl(pm_head_under_x,pm_anchor_x1+.1,
                 pm_anchor_y,z,pm_head_counterbore_d);
    }
    for(pair=pm_cheek_y)
        pm_ycyl(pair[0]-.1,pair[1]+.1,pm_pivot_x,pm_pivot_z,
                 pm_pivot_bore_d);
}}
module pm_existing_anchor_heads(){
    // The two original +Y seam heads are replaced, not stacked underneath.
    for(z=pm_anchor_z){
        pm_xcyl(3.8,6.8,pm_anchor_y,z,5.5);
    }
}
module pm_replacement_screws(){
    for(z=pm_anchor_z){
        pm_xcyl(pm_head_under_x-pm_replacement_screw_underhead_length,
                 pm_head_under_x,pm_anchor_y,z,3);
        pm_xcyl(pm_head_under_x,pm_head_under_x+3,
                 pm_anchor_y,z,5.5);
    }
}
module pm_screw_tools(){
    for(z=pm_anchor_z)
        pm_xcyl(pm_anchor_x1,90,pm_anchor_y,z,4);
}
module pm_pivot_tool(){
    pm_ycyl(pm_pivot_y+8,pm_pivot_y+38,pm_pivot_x,pm_pivot_z,8);
}
module pm_rocker(){translate([0,pm_pivot_y-62,0])rb_rocker();}
module pm_other_fixed(){
    ss_other_fixed();ss_cap();
}
module pm_moving(){
    it_moving_printed(pm_t,0);ss_tabs(pm_t);
}
module pm_probe_geometry(){
    if(pm_probe=="bracket-fixed")intersection(){pm_bracket();pm_other_fixed();}
    else if(pm_probe=="bracket-moving")intersection(){pm_bracket();pm_moving();}
    else if(pm_probe=="bracket-moving-clearance-1mm")intersection(){
        minkowski(){pm_bracket();sphere(r=1,$fn=48);}pm_moving();
    }
    else if(pm_probe=="bracket-rocker")intersection(){pm_bracket();pm_rocker();}
    else if(pm_probe=="bracket-rocker-clearance-1mm")intersection(){
        minkowski(){pm_bracket();sphere(r=1,$fn=48);}pm_rocker();
    }
    else if(pm_probe=="bracket-bridge")intersection(){pm_bracket();rb_output_bridge();}
    else if(pm_probe=="bracket-switch")intersection(){pm_bracket();ss_switches();}
    else if(pm_probe=="bracket-motor")intersection(){pm_bracket();rb_motor_proxy();}
    else if(pm_probe=="bracket-hardware")intersection(){
        pm_bracket();difference(){hs_selected_hardware(pm_t);pm_existing_anchor_heads();}
    }
    else if(pm_probe=="anchor-contact-upper" ||
            pm_probe=="anchor-contact-lower")intersection(){
        pm_bracket_blank();
        // A 0.1 mm projection into the shell face demonstrates each pad's
        // load path; assembled bracket is face-contact at X=7 only.
        intersection(){
            translate([.1,0,0])pm_other_fixed();
            pm_box(6.9,7.2,34,46,
                   pm_probe=="anchor-contact-upper"?10:-16,
                   pm_probe=="anchor-contact-upper"?22:-4);
        }
    }
    else if(pm_probe=="screw-tool-with-cap")intersection(){pm_screw_tools();ss_cap();}
    else if(pm_probe=="screw-tool-cap-off")intersection(){
        pm_screw_tools();ss_other_fixed();
    }
    else if(pm_probe=="pivot-tool")intersection(){
        pm_pivot_tool();union(){pm_other_fixed();pm_moving();rb_motor_proxy();}
    }
    else if(pm_probe=="replacement-screw-bracket")intersection(){
        pm_replacement_screws();pm_bracket();
    }
    else if(pm_probe=="positive-control")intersection(){pm_bracket();pm_bracket();}
    else assert(false,"Unknown pivot mount probe");
}
if(pm_part=="probe")pm_probe_geometry();
else if(pm_part=="bracket")pm_bracket();
else if(pm_part=="rocker-phase")pm_rocker();
else if(pm_part=="context"){
    color([.72,.75,.78,.32])pm_other_fixed();
    color([.91,.52,.15,.55])pm_moving();
    color([.15,.53,.78])pm_bracket();
    color([.22,.72,.42])pm_rocker();
    color([.99,.72,.19,.55])rb_output_bridge_visual();
    color([.95,.20,.16,.12])rb_motor_proxy();
}
else assert(false,"Unknown pivot mount part");

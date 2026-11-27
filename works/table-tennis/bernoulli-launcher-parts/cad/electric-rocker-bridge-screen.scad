// Packaging screen for the two-way rocker output path, millimetres.
// X1C/PETG is the intended future FDM process, but this volume is NOT a
// printable part. It is a minimum occupied crosshead/bridge envelope with
// a closed horizontal pin slot, linked to the moving upper tab.
// Motor and switch dimensions remain catalogue/seller proxies. The pivot
// bracket, pin retention, motor-side clevis and load-bearing root are open.
use <electric-end-switch-side-cap.scad>
use <electric-feeder-trigger-assembly.scad>
use <electric-home-switch-screen.scad>

rb_part = "probe"; // probe, context
rb_probe = "bridge-fixed";
rb_t = 0;
rb_input_r = 75; // 45, 60 or 75 mm screen; output/input = 2/3
rb_plane_y = 62;
rb_motor_x = 85;
rb_motor_y = 70;
rb_motor_d = 29;
rb_pivot_z = 25; // lifted 2 mm; keeps slot wall and opens cap clearance
rb_pin_d = 7;
rb_pin_clearance = .4;
rb_slot_end_wall = 3;
rb_slot_top_wall = 3;
rb_bridge_y_root = 35.5;
rb_rocker_thickness_y = 5;
rb_pivot_bearing_span_y = 12;
rb_clearance_r = 2;
rb_bridge_outer_y = rb_plane_y-3.5; // 1 mm from the rocker plate's inner face
rb_angle_half = asin(15/rb_input_r);
rb_output_r = rb_input_r*2/3;
rb_pivot_x = rb_motor_x-sqrt(rb_input_r*rb_input_r-15*15);
rb_pin_x_end = rb_pivot_x+rb_output_r*cos(rb_angle_half);
rb_pin_x_middle = rb_pivot_x+rb_output_r;
rb_slot_x0 = rb_pin_x_end-rb_pin_d/2-rb_pin_clearance-rb_slot_end_wall;
rb_slot_x1 = rb_pin_x_middle+rb_pin_d/2+rb_pin_clearance+rb_slot_end_wall;
rb_bridge_half_z = rb_pin_d/2+rb_pin_clearance+rb_slot_top_wall;
rb_output_z = rb_pivot_z-10+20*rb_t;
// Use actual input displacement as phase. Linear angle interpolation would
// introduce ~0.07 mm false vertical mismatch at quarter stroke.
rb_angle = asin((30*rb_t-15)/rb_input_r);

assert(rb_t>=0 && rb_t<=1);
assert(rb_input_r>15 && rb_output_r==rb_input_r*2/3);
assert(rb_bridge_y_root<rb_bridge_outer_y);
assert(rb_bridge_outer_y<=rb_plane_y-rb_rocker_thickness_y/2-1);

module rb_box(x0,x1,y0,y1,z0,z1){
    translate([x0,y0,z0])cube([x1-x0,y1-y0,z1-z0]);
}
module rb_ycyl(x,z,d,h){
    translate([x,0,z])rotate([90,0,0])cylinder(d=d,h=h,center=true,$fn=72);
}
module rb_rocker(){
    translate([rb_pivot_x,rb_plane_y,rb_pivot_z])
        rotate([0,-rb_angle,0]){
            hull(){rb_ycyl(0,0,10,rb_rocker_thickness_y);
                   rb_ycyl(rb_input_r,0,rb_pin_d,rb_rocker_thickness_y);}
            // Separate pin projects inward from the rocker plate through
            // the crosshead slot. Its real retaining hardware is unresolved.
            translate([0,-5,0])rb_ycyl(rb_output_r,0,rb_pin_d,14);
        }
}
module rb_pivot_reference(){
    translate([rb_pivot_x,rb_plane_y,rb_pivot_z])
        rotate([90,0,0])cylinder(d=12,h=rb_pivot_bearing_span_y,center=true,$fn=72);
}
module rb_output_bridge(){
    // Deliberately test the entire minimum solid exterior. The closed slot
    // opening is not subtracted: collision screening then errs on the side
    // of rejecting a layout. This envelope itself is not an STL for use.
    union(){
        rb_box(rb_slot_x0,rb_slot_x1,
               rb_bridge_y_root,rb_bridge_outer_y,
               rb_output_z-rb_bridge_half_z,
               rb_output_z+rb_bridge_half_z);
        if(rb_pivot_z>=25)
            // A narrow root web descends toward the integral moving tab,
            // clear of the x>=66.4 switch saddle. It is a volume envelope,
            // not yet a strength-certified carriage union.
            rb_box(54,64,rb_bridge_y_root,41,
                   rb_output_z-rb_bridge_half_z-1,
                   rb_output_z-rb_bridge_half_z+.1);
    }
}
module rb_output_bridge_visual(){difference(){
    rb_output_bridge();
    hull()for(x=[rb_pin_x_end,rb_pin_x_middle])
        translate([x,rb_bridge_y_root-.1,rb_output_z])
            rotate([-90,0,0])cylinder(
                h=rb_bridge_outer_y-rb_bridge_y_root+.2,
                d=rb_pin_d+2*rb_pin_clearance,$fn=72);
}}
module rb_motor_proxy(){
    translate([rb_motor_x,rb_motor_y,-91+(rb_pivot_z-23)])
        cylinder(h=129,d=rb_motor_d,$fn=96);
}
module rb_fixed(){ss_other_fixed();ss_cap();}
module rb_hardware(){hs_selected_hardware(rb_t);ss_switch_fasteners();}
module rb_probe_geometry(){
    if(rb_probe=="bridge-fixed")intersection(){rb_output_bridge();rb_fixed();}
    else if(rb_probe=="bridge-fixed-clearance-2mm")intersection(){
        minkowski(){rb_output_bridge();sphere(r=rb_clearance_r,$fn=64);}rb_fixed();
    }
    else if(rb_probe=="bridge-switch-clearance-2mm")intersection(){
        minkowski(){rb_output_bridge();sphere(r=rb_clearance_r,$fn=64);}ss_switches();
    }
    else if(rb_probe=="bridge-hardware-clearance-2mm")intersection(){
        minkowski(){rb_output_bridge();sphere(r=rb_clearance_r,$fn=64);}rb_hardware();
    }
    else if(rb_probe=="bridge-motor-clearance-5mm")intersection(){
        minkowski(){rb_output_bridge();sphere(r=5,$fn=64);}rb_motor_proxy();
    }
    else if(rb_probe=="bridge-hardware")intersection(){rb_output_bridge();rb_hardware();}
    else if(rb_probe=="bridge-switch")intersection(){rb_output_bridge();ss_switches();}
    else if(rb_probe=="bridge-motor")intersection(){rb_output_bridge();rb_motor_proxy();}
    else if(rb_probe=="motor-proxy-fixed")intersection(){rb_motor_proxy();rb_fixed();}
    else if(rb_probe=="motor-proxy-moving")intersection(){rb_motor_proxy();it_moving_printed(rb_t,0);ss_tabs(rb_t);}
    else if(rb_probe=="motor-proxy-hardware")intersection(){rb_motor_proxy();rb_hardware();}
    else if(rb_probe=="rocker-fixed")intersection(){union(){rb_rocker();rb_pivot_reference();}rb_fixed();}
    else if(rb_probe=="rocker-fixed-clearance-2mm")intersection(){
        minkowski(){union(){rb_rocker();rb_pivot_reference();}sphere(r=2,$fn=48);}rb_fixed();
    }
    else if(rb_probe=="rocker-moving")intersection(){union(){rb_rocker();rb_pivot_reference();}it_moving_printed(rb_t,0);ss_tabs(rb_t);}
    else if(rb_probe=="rocker-moving-clearance-2mm")intersection(){
        minkowski(){union(){rb_rocker();rb_pivot_reference();}sphere(r=2,$fn=48);}
        union(){it_moving_printed(rb_t,0);ss_tabs(rb_t);}
    }
    else if(rb_probe=="rocker-hardware")intersection(){union(){rb_rocker();rb_pivot_reference();}rb_hardware();}
    else if(rb_probe=="rocker-hardware-clearance-2mm")intersection(){
        minkowski(){union(){rb_rocker();rb_pivot_reference();}sphere(r=2,$fn=48);}rb_hardware();
    }
    else if(rb_probe=="rocker-switch")intersection(){union(){rb_rocker();rb_pivot_reference();}ss_switches();}
    else if(rb_probe=="rocker-switch-clearance-2mm")intersection(){
        minkowski(){union(){rb_rocker();rb_pivot_reference();}sphere(r=2,$fn=48);}ss_switches();
    }
    else if(rb_probe=="rocker-bridge-visual")intersection(){rb_rocker();rb_output_bridge_visual();}
    else if(rb_probe=="bridge-tab-root")intersection(){rb_output_bridge();ss_home_tab(rb_t);}
    else if(rb_probe=="visual-bridge-tab-root")intersection(){rb_output_bridge_visual();ss_home_tab(rb_t);}
    else if(rb_probe=="positive-control")intersection(){rb_output_bridge();rb_output_bridge();}
    else assert(false,"Unknown rocker-bridge screen probe");
}
if(rb_part=="probe")rb_probe_geometry();
else if(rb_part=="context"){
    color([.68,.73,.78,.38])ss_other_fixed();
    color([.94,.55,.17,.65]){it_moving_printed(rb_t,0);ss_tabs(rb_t);}
    color([.15,.55,.80])ss_cap();
    color([.10,.12,.14])ss_switches();
    color([.16,.68,.45])rb_rocker();
    color([.98,.70,.18,.90])rb_output_bridge_visual();
    color([.95,.2,.16,.18])rb_motor_proxy();
}
else assert(false,"Unknown rocker-bridge screen part");

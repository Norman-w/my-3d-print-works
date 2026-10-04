// One-piece feeder output crosshead candidate. Millimetres; X1C/0.4/PETG.
// It adds a closed pin slot to the existing moving frame, with a broad root
// into the frame's upper transverse bridge instead of loading the thin switch
// tab. No shell split or fixed air-seal surface changes. Pin retention,
// bearing pressure, layer strength and motor endpoint compliance remain open.
use <electric-end-switch-side-cap.scad>
use <electric-rocker-bridge-screen.scad>
use <electric-rocker-clamped-fork-screen.scad>
use <electric-feeder-assembly.scad>
use <electric-feeder-trigger-assembly.scad>
use <electric-home-switch-screen.scad>

oc_part = "probe"; // probe, carriage, crosshead, context
oc_probe = "crosshead-fixed";
oc_t = 0;
rb_t = oc_t;
rb_plane_y = 65;
rb_motor_y = 63;
rb_pivot_z = 25;
pm_pivot_y = 65;
cf_t = oc_t;

oc_input_r = 75;
oc_output_r = 50;
oc_pivot_x = 85-sqrt(oc_input_r*oc_input_r-15*15);
oc_pin_d = 7;
oc_pin_radial_clearance = .4;
oc_slot_r = oc_pin_d/2+oc_pin_radial_clearance;
oc_wall = 3;
oc_pin_x_end = oc_pivot_x+oc_output_r*sqrt(1-(15/oc_input_r)*(15/oc_input_r));
oc_pin_x_mid = oc_pivot_x+oc_output_r;
oc_outer_x0 = oc_pin_x_end-oc_slot_r-oc_wall;
oc_outer_x1 = oc_pin_x_mid+oc_slot_r+oc_wall;
oc_outer_y0 = 50;
oc_outer_y1 = rb_plane_y-3.5; // 1 mm from the rocker plate inner face
oc_root_x0 = 48;
oc_root_x1 = oc_pin_x_end-oc_slot_r-.1;
oc_root_y0 = 48;
oc_root_y1 = 55;
oc_center_z = rb_pivot_z-10+20*oc_t;
oc_half_z = oc_slot_r+oc_wall;

assert(oc_t>=0 && oc_t<=1);
assert(oc_output_r*3==oc_input_r*2);
assert(oc_root_x0<52 && oc_root_y0<=48 && oc_root_y1>=54);
assert(oc_root_x1>oc_outer_x0 && oc_root_x1<oc_pin_x_end-oc_slot_r);
assert(oc_outer_y1-oc_outer_y0>=2*oc_wall);

module oc_box(x0,x1,y0,y1,z0,z1){
    translate([x0,y0,z0])cube([x1-x0,y1-y0,z1-z0]);
}
module oc_slot_void(){
    hull()for(x=[oc_pin_x_end,oc_pin_x_mid])
        translate([x,oc_outer_y0-.1,oc_center_z])rotate([-90,0,0])
            cylinder(h=oc_outer_y1-oc_outer_y0+.2,r=oc_slot_r,$fn=72);
}
module oc_root(){
    // Broad face overlap with the original carriage top bridge:
    // x=48..52, y=48..54, z=10..16 at t=0.
    oc_box(oc_root_x0,oc_root_x1,oc_root_y0,oc_root_y1,
           oc_center_z-oc_half_z,oc_center_z+oc_half_z);
}
module oc_crosshead(){
    difference(){
        union(){
            oc_box(oc_outer_x0,oc_outer_x1,oc_outer_y0,oc_outer_y1,
                   oc_center_z-oc_half_z,oc_center_z+oc_half_z);
            oc_root();
        }
        oc_slot_void();
    }
}
module oc_carriage(){ss_carriage(oc_t);oc_crosshead();}
module oc_fixed(){ss_other_fixed();ss_cap();}
module oc_hardware(){hs_selected_hardware(oc_t);ss_switch_fasteners();}
module oc_probe_geometry(){
    if(oc_probe=="crosshead-fixed")intersection(){oc_crosshead();oc_fixed();}
    else if(oc_probe=="crosshead-hardware")intersection(){oc_crosshead();oc_hardware();}
    else if(oc_probe=="crosshead-switch")intersection(){oc_crosshead();ss_switches();}
    else if(oc_probe=="crosshead-motor")intersection(){oc_crosshead();ss_motor_envelope();}
    else if(oc_probe=="crosshead-bracket")intersection(){oc_crosshead();cf_bracket();}
    else if(oc_probe=="crosshead-fasteners")intersection(){oc_crosshead();cf_fasteners();}
    else if(oc_probe=="crosshead-rocker")intersection(){oc_crosshead();rb_rocker();}
    else if(oc_probe=="crosshead-other-moving")intersection(){
        oc_crosshead();difference(){it_moving_printed(oc_t,0);ss_carriage(oc_t);}
    }
    else if(oc_probe=="crosshead-fixed-clearance-0p5")intersection(){
        minkowski(){oc_crosshead();sphere(r=.5,$fn=24);}oc_fixed();
    }
    else if(oc_probe=="root-carriage-control")intersection(){oc_root();ed_carriage(oc_t);}
    else if(oc_probe=="slot-pin-control")intersection(){oc_slot_void();rb_rocker();}
    else if(oc_probe=="crosshead-self-control")intersection(){oc_crosshead();oc_crosshead();}
    else assert(false,"Unknown output-crosshead probe");
}
if(oc_part=="probe")oc_probe_geometry();
else if(oc_part=="carriage")oc_carriage();
else if(oc_part=="crosshead")oc_crosshead();
else if(oc_part=="context"){
    color([.70,.73,.77,.27])oc_fixed();
    color([.95,.54,.17,.72])oc_carriage();
    color([.17,.69,.43])rb_rocker();
    color([.11,.50,.82,.75])cf_bracket();
    color([.12,.12,.13])ss_switches();
    color([.95,.20,.15,.13])ss_motor_envelope();
}
else assert(false,"Unknown output-crosshead part");

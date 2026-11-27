// Compare two Y planes for a genuinely retained 6 mm rocker pivot.
// The bushing dimensions are from igus GFM-0608-06. The pin head, front
// washer/cotter and PETG press-fit geometry remain envelopes, not selected
// purchasable hardware or a released rocker.
use <electric-rocker-pivot-mount-screen.scad>
use <electric-rocker-bridge-screen.scad>
use <electric-end-switch-side-cap.scad>
use <electric-feeder-trigger-assembly.scad>

pj_part = "probe"; // probe, rocker, bracket, context, retainer-detail
pj_probe = "front-retainer-moving";
pj_t = 0;
pm_pivot_y = 62; // CLI compares 62 and 65; shared with bracket module
rb_plane_y = pm_pivot_y; // CLI must also set rb_plane_y for imported rocker
pj_x = 85-sqrt(75*75-15*15);
pj_y = pm_pivot_y;
pj_z = 25;
pj_rocker_thickness = 5;
pj_rocker_hub_d = 16;
pj_bushing_body_d = 8;
pj_bushing_bore_d = 6;
pj_bushing_body_length = 6;
pj_bushing_flange_d = 12;
pj_bushing_flange_thickness = 1;
pj_bracket_front_outer_y = pj_y-7;
pj_bracket_front_inner_y = pj_y-4;
pj_bracket_rear_inner_y = pj_y+4;
pj_bracket_rear_outer_y = pj_y+8;
pj_rear_head_d = 12;
pj_rear_head_thickness = 2;
pj_front_retainer_d = 16; // deliberately oversized washer+cotter envelope
pj_front_retainer_axial = 3; // not a selected hardware stack

assert(pj_y==62 || pj_y==65);
assert(pj_bracket_rear_inner_y-pj_bracket_front_inner_y==8);
assert(pj_bushing_body_length+pj_bushing_flange_thickness==7);
assert(pj_rocker_thickness==5);

module pj_ycyl(y0,y1,x,z,d,fn=72){
    translate([x,y0,z])rotate([-90,0,0])
        cylinder(h=y1-y0,d=d,$fn=fn);
}
module pj_rocker_blank(){
    union(){
        rb_rocker();
        pj_ycyl(pj_y-2.5,pj_y+2.5,pj_x,pj_z,pj_rocker_hub_d);
    }
}
module pj_rocker(){difference(){
    pj_rocker_blank();
    // Nominal H7 housing bore for GFM-0608-06. An X1C print does not produce
    // this tolerance by itself; reaming/retention remains unresolved.
    pj_ycyl(pj_y-2.6,pj_y+2.6,pj_x,pj_z,pj_bushing_body_d);
}}
module pj_bushing(){difference(){
    union(){
        pj_ycyl(pj_y-3.5,pj_y+2.5,pj_x,pj_z,pj_bushing_body_d);
        pj_ycyl(pj_y+2.5,pj_y+3.5,pj_x,pj_z,pj_bushing_flange_d);
    }
    pj_ycyl(pj_y-3.6,pj_y+3.6,pj_x,pj_z,pj_bushing_bore_d);
}}
module pj_shaft(){
    pj_ycyl(pj_bracket_front_outer_y-2,pj_bracket_rear_outer_y,
            pj_x,pj_z,6);
}
module pj_rear_head(){
    pj_ycyl(pj_bracket_rear_outer_y,
            pj_bracket_rear_outer_y+pj_rear_head_thickness,
            pj_x,pj_z,pj_rear_head_d);
}
module pj_front_retainer(){
    pj_ycyl(pj_bracket_front_outer_y-pj_front_retainer_axial,
            pj_bracket_front_outer_y,pj_x,pj_z,pj_front_retainer_d);
}
module pj_hardware(){pj_shaft();pj_rear_head();pj_front_retainer();}
module pj_moving(){it_moving_printed(pj_t,0);ss_tabs(pj_t);}
module pj_fixed(){ss_other_fixed();ss_cap();}

module pj_probe_geometry(){
    if(pj_probe=="front-retainer-moving")intersection(){
        pj_front_retainer();pj_moving();
    }
    else if(pj_probe=="front-retainer-moving-clearance-1mm")intersection(){
        minkowski(){pj_front_retainer();sphere(r=1,$fn=48);}pj_moving();
    }
    else if(pj_probe=="front-retainer-fixed")intersection(){
        pj_front_retainer();pj_fixed();
    }
    else if(pj_probe=="rear-head-moving")intersection(){pj_rear_head();pj_moving();}
    else if(pj_probe=="rear-head-fixed")intersection(){pj_rear_head();pj_fixed();}
    else if(pj_probe=="rocker-moving")intersection(){pj_rocker();pj_moving();}
    else if(pj_probe=="rocker-fixed")intersection(){pj_rocker();pj_fixed();}
    else if(pj_probe=="bushing-rocker")intersection(){pj_bushing();pj_rocker();}
    else if(pj_probe=="bushing-bracket")intersection(){pj_bushing();pm_bracket();}
    else if(pj_probe=="pin-bushing")intersection(){pj_shaft();pj_bushing();}
    else if(pj_probe=="pin-bracket")intersection(){pj_shaft();pm_bracket();}
    else if(pj_probe=="bracket-moving")intersection(){pm_bracket();pj_moving();}
    else if(pj_probe=="bracket-fixed")intersection(){pm_bracket();pj_fixed();}
    else if(pj_probe=="bridge-fixed-clearance-2mm")intersection(){
        minkowski(){rb_output_bridge();sphere(r=2,$fn=48);}pj_fixed();
    }
    else if(pj_probe=="bridge-motor-clearance-4mm")intersection(){
        minkowski(){rb_output_bridge();sphere(r=4,$fn=64);}rb_motor_proxy();
    }
    else if(pj_probe=="bridge-motor-clearance-5mm")intersection(){
        minkowski(){rb_output_bridge();sphere(r=5,$fn=64);}rb_motor_proxy();
    }
    else if(pj_probe=="front-retainer-positive-control")intersection(){
        pj_front_retainer();pj_front_retainer();
    }
    else assert(false,"Unknown pivot joint probe");
}
if(pj_part=="probe")pj_probe_geometry();
else if(pj_part=="rocker")pj_rocker();
else if(pj_part=="rocker-phase")pj_rocker();
else if(pj_part=="bracket")pm_bracket();
else if(pj_part=="context"){
    color([.68,.72,.76,.23])pj_fixed();
    color([.95,.54,.17,.50])pj_moving();
    color([.15,.53,.82])pm_bracket();
    color([.15,.70,.36])pj_rocker();
    color([.92,.80,.28])pj_bushing();
    color([.66,.68,.70])pj_hardware();
    color([.96,.05,.04])intersection(){pj_front_retainer();pj_moving();}
    color([.98,.72,.18,.55])rb_output_bridge_visual();
    color([.95,.20,.17,.14])rb_motor_proxy();
}
else if(pj_part=="retainer-detail"){
    color([.15,.53,.82,.28])pm_bracket();
    color([.15,.70,.36,.28])pj_rocker();
    color([.95,.54,.17,.55])pj_moving();
    color([.68,.70,.72])pj_front_retainer();
    color([.96,.05,.04])intersection(){pj_front_retainer();pj_moving();}
}
else assert(false,"Unknown pivot joint part");

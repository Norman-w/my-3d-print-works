// Catalogue pin orientation screen at the outer Y=65 rocker pivot.
// MISUMI HCDG6-16 is inserted from the moving-frame side: head at Y<58,
// supplied NETW5 E-clip at Y>73. The two grey volumes overbound the nominal
// head / ring / pin tip; they are not exact purchased hardware solids.
use <electric-rocker-pivot-mount-screen.scad>
use <electric-rocker-bridge-screen.scad>
use <electric-end-switch-side-cap.scad>
use <electric-feeder-trigger-assembly.scad>

pr_part = "probe";
pr_probe = "front-head-moving";
pr_t = 0;
pm_pivot_y = 65;
rb_plane_y = 65;
// Imported modules are also set with -D pm_pivot_y, rb_plane_y and rb_t by
// the review runner. A local pr_t assignment alone does not move them.
pr_x = 85-sqrt(75*75-15*15);
pr_z = 25;
pr_front_outer_y = pm_pivot_y-7;
pr_rear_outer_y = pm_pivot_y+8;
pr_front_head_envelope_d = 16;
pr_front_head_envelope_axial = 3;
pr_rear_ring_tip_envelope_d = 16;
pr_rear_ring_tip_envelope_axial = 4;

assert(pr_t>=0 && pr_t<=1);
assert(pr_front_outer_y==58 && pr_rear_outer_y==73);

module pr_ycyl(y0,y1,d){
    translate([pr_x,y0,pr_z])rotate([-90,0,0])
        cylinder(h=y1-y0,d=d,$fn=72);
}
module pr_front_head_envelope(){
    pr_ycyl(pr_front_outer_y-pr_front_head_envelope_axial,
            pr_front_outer_y,pr_front_head_envelope_d);
}
module pr_rear_ring_tip_envelope(){
    pr_ycyl(pr_rear_outer_y,
            pr_rear_outer_y+pr_rear_ring_tip_envelope_axial,
            pr_rear_ring_tip_envelope_d);
}
module pr_moving(){it_moving_printed(pr_t,0);ss_tabs(pr_t);}
module pr_fixed(){ss_other_fixed();ss_cap();}
module pr_probe_geometry(){
    if(pr_probe=="front-head-moving")
        intersection(){pr_front_head_envelope();pr_moving();}
    else if(pr_probe=="front-head-moving-clearance-1mm")
        intersection(){
            minkowski(){pr_front_head_envelope();sphere(r=1,$fn=48);}
            pr_moving();
        }
    else if(pr_probe=="front-head-fixed")
        intersection(){pr_front_head_envelope();pr_fixed();}
    else if(pr_probe=="rear-ring-moving")
        intersection(){pr_rear_ring_tip_envelope();pr_moving();}
    else if(pr_probe=="rear-ring-moving-clearance-1mm")
        intersection(){
            minkowski(){pr_rear_ring_tip_envelope();sphere(r=1,$fn=48);}
            pr_moving();
        }
    else if(pr_probe=="rear-ring-fixed")
        intersection(){pr_rear_ring_tip_envelope();pr_fixed();}
    else if(pr_probe=="mount-tool-moving")
        intersection(){pm_screw_tools();pr_moving();}
    else if(pr_probe=="mount-tool-bridge")
        intersection(){pm_screw_tools();rb_output_bridge();}
    else if(pr_probe=="mount-tool-preassembled-pivot")
        intersection(){
            pm_screw_tools();
            union(){rb_rocker();pr_front_head_envelope();
                    pr_rear_ring_tip_envelope();}
        }
    else if(pr_probe=="front-head-positive-control")
        intersection(){pr_front_head_envelope();pr_front_head_envelope();}
    else if(pr_probe=="rear-ring-positive-control")
        intersection(){pr_rear_ring_tip_envelope();pr_rear_ring_tip_envelope();}
    else assert(false,"Unknown rocker pin retention probe");
}
if(pr_part=="probe")pr_probe_geometry();
else if(pr_part=="context"){
    color([.68,.73,.76,.20])pr_fixed();
    color([.94,.52,.16,.45])pr_moving();
    color([.12,.52,.82])pm_bracket();
    color([.16,.70,.38])rb_rocker();
    color([.62,.65,.69]){
        pr_ycyl(pr_front_outer_y,pr_rear_outer_y+3.1,6);
        pr_front_head_envelope();pr_rear_ring_tip_envelope();
    }
}
else assert(false,"Unknown rocker pin retention part");

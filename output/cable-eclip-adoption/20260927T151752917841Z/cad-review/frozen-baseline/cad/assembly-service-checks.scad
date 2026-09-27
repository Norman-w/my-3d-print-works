// Actual translational nut-insertion envelopes; no friction/force simulation.
feeder_support_library_mode = true;
include <feeder-supports.scad>
use <spin-head.scad>
service_case = "feeder_nut";

module left_nut_sweep() {
    // A convex solid hexagon encloses the actual hollow nut. Its hull between
    // the endpoints encloses the entire straight insertion, not just samples.
    hull() for(z=[support_guide_z0-5,max(support_cap_screw_z)])
        support_y_hex(-support_cap_screw_x,z,18.1,2.4,5.5);
}
module spin_preload_nut_sweep() {
    hull() for(y=[25,0]) cyl_x(55.75,y,43,3.2,7/cos(30),6);
}

if(service_case=="feeder_nut" || service_case=="feeder_nut_old_rib")
    intersection() {
        left_nut_sweep();
        union() {
            mirror([1,0,0]) feeder_side_support_local();
            feeder_spring_fixed_interface();
            if(service_case=="feeder_nut_old_rib")
                translate([-67,11.4,-23]) cube([4,12.8,14]);
        }
    }
else if(service_case=="spin_nut_first" || service_case=="spin_nut_wrong_order")
    intersection() {
        spin_preload_nut_sweep();
        union() {
            cover();
            if(service_case=="spin_nut_wrong_order")
                cyl_x(47,11,43,12,3);
        }
    }
else assert(false,"Unknown service case");

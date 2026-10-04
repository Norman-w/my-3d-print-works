// Nominal free-space probes on the current electric feeder. This deliberately
// contains NO motor, mount or linkage; an empty intersection is only room for
// a future interface, not evidence that any real motor fits or carries load.
use <electric-feeder-assembly.scad>

dr_region = "right-drive-plane";
dr_target = "moving";
dr_t = 0;

assert(dr_t >= 0 && dr_t <= 1);

module dr_box(x0,x1,y0,y1,z0,z1) {
    translate([x0,y0,z0]) cube([x1-x0,y1-y0,z1-z0]);
}
module dr_region_solid() {
    if(dr_region == "right-drive-plane")
        dr_box(20,120,58,70,-80,60);
    else if(dr_region == "right-riser")
        dr_box(72,82,30,70,-35,45);
    else if(dr_region == "pivot-crossbar")
        dr_box(18,78,60,66,20,26);
    else if(dr_region == "anchor-patch")
        dr_box(60,67,24,30,-32,3);
    else assert(false,"Unknown drive-route region");
}
module dr_target_solid() {
    if(dr_target == "fixed") ed_fixed_printed();
    else if(dr_target == "moving") ed_moving_printed(dr_t);
    else if(dr_target == "hardware") {
        ed_fixed_hardware(); ed_moving_hardware(dr_t);
    }
    else assert(false,"Unknown drive-route target");
}

intersection() { dr_region_solid(); dr_target_solid(); }

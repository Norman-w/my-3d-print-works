// Integrated geometry candidate. Not a print or functional release.
feeder_support_library_mode = true;
include <feeder-supports.scad>
use <feeder-body.scad>

assembly_part = "review"; // review, section, body_interference, removal_probe
assembly_stroke = 0;
assembly_removal = 0;
assembly_body_fault = 0; // positive-control radial intrusion only

module integrated_body() {
    translate([assembly_body_fault,0,0]) feeder_body_full();
}
module integrated_hardware() {
    feeder_cap_hardware();
    feeder_mount_hardware();
}
module integrated_review(section=false) {
    color([0.66,0.70,0.73]) {
        if(section) feeder_body_half(true);
        else integrated_body();
    }
    color([0.75,0.76,0.79]) feeder_support_fixed();
    color([0.10,0.46,0.80]) feeder_carriage(assembly_stroke);
    for(side=[-1,1],rear=[false,true]) {
        color(rear?[0.15,0.65,0.42]:[0.95,0.4,0.1])
            cam_finger(side,rear,assembly_stroke);
        color([0.28,0.30,0.34]) {
            cam_pin(side,rear,assembly_stroke);
            cam_follower_nut(side,rear,assembly_stroke);
        }
    }
    color([0.28,0.30,0.34]) integrated_hardware();
}

if(assembly_part=="review") integrated_review();
else if(assembly_part=="section") integrated_review(true);
else if(assembly_part=="body_interference") intersection() {
    integrated_body();
    union() {
        feeder_support_fixed();
        feeder_support_moving(assembly_stroke);
        integrated_hardware();
    }
}
else if(assembly_part=="removal_probe") intersection() {
    integrated_body();
    union() {
        feeder_carriage(assembly_stroke,60*assembly_removal);
        for(side=[-1,1],rear=[false,true])
            translate([side*35*assembly_removal,0,0])
                cam_finger(side,rear,assembly_stroke);
    }
}
else assert(false,"Unknown integrated assembly part");

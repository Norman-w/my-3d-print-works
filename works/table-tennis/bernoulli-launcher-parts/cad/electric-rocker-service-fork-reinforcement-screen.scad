// Unreleased strength/layout screen. The existing 3 x 11 mm low beam is
// widened to 7 x 11 mm through X=14 while retaining the original two shell
// screw channels. This is not a printable or load-rated replacement yet.
use <electric-rocker-service-fork-screen.scad>
use <electric-output-crosshead-screen.scad>
use <electric-end-switch-side-cap.scad>

rf_part = "probe"; // probe, base, moving-control, context
rf_probe = "added-moving";

module rf_box(x0,x1,y0,y1,z0,z1){
    translate([x0,y0,z0]) cube([x1-x0,y1-y0,z1-z0]);
}
module rf_extension(){
    // The service fork already fills X=7..10; only X=10..14 is added.
    // Keep the lower shell screw's existing through hole and counterbore.
    difference(){
        rf_box(10,14,40,61,-18,-7);
        sf_anchor_holes();
    }
}
module rf_base(){union(){sf_base();rf_extension();}}
module rf_added_only(){difference(){rf_base();sf_base();}}

module rf_probe_geometry(){
    if(rf_probe=="added-moving")intersection(){rf_added_only();oc_carriage();}
    else if(rf_probe=="added-fixed")intersection(){rf_added_only();sf_fixed();}
    else if(rf_probe=="added-hardware")intersection(){
        rf_added_only();sf_other_hardware();
    }
    else if(rf_probe=="added-motor")intersection(){
        rf_added_only();ss_motor_envelope();
    }
    else if(rf_probe=="added-rear")intersection(){rf_added_only();sf_rear();}
    else if(rf_probe=="anchor-channel")intersection(){
        rf_added_only();sf_anchor_holes();
    }
    else if(rf_probe=="added-positive-control")intersection(){
        rf_added_only();rf_added_only();
    }
    else assert(false,"Unknown reinforcement probe");
}

if(rf_part=="probe")rf_probe_geometry();
else if(rf_part=="base")rf_base();
else if(rf_part=="moving-control")oc_carriage();
else if(rf_part=="context"){
    color([.17,.52,.79,.35])sf_base();
    color([.12,.78,.32])rf_added_only();
    color([.82,.57,.23,.40])oc_carriage();
}
else assert(false,"Unknown reinforcement part");

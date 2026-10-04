// Current electric-feeder layout, mm. +Z is the 20 mm feeder motion.
// The Bowden input/output/route, their replacement beam and their frame are
// NOT assembled here. The original manual finger loop is removed as well.
// This is a feeder + optical-home mechanical baseline;
// no BY141-3 motor mount or two-way coupling is released without its dimensions.
include <parameters.scad>
use <launcher-final-assembly.scad>
use <feeder-integrated-candidate.scad>
use <feeder-cam-guide-revision.scad>
use <feeder-guide-revision.scad>
use <feeder-supports.scad>
use <feeder-support-harness.scad>
use <feeder-hardware-clearance.scad>
use <outlet-retention.scad>
use <feeder-complete-hardware.scad>
use <feeder-pin-seat-revision.scad>
use <feeder-frame-y-guide.scad>
use <feeder-return-spring.scad>
use <inlet-retention-final.scad>
use <feeder-optical-home.scad>

ed_part = "assembly"; // assembly, baseline, optical-left-cap, optical-moving-spacer, probe
ed_legacy_part = "frame";
ed_side = 1;
ed_rear = false;
ed_t = 0;
ed_probe = "sensor-other-fixed";
assert(ed_t >= 0 && ed_t <= 1);

// The non-Bowden carriage carries a manual finger loop beyond X=58. Its
// positive-X hard-stop shoulder intentionally extends to X=59 at Z=5..9;
// remove the finger projection only above Z=10 in carriage-local coordinates.
// The motor linkage is still open.
module ed_carriage(t=ed_t){
    difference(){
        feeder_carriage(t);
        translate([58,-100,10+cam_stroke*t]) cube([100,200,90]);
    }
}

// Partition the ORIGINAL 38-instance feeder. Replace exactly two instances:
// left Y cap and moving spring spacer. No old printed item is hidden by a
// coincident mesh or silently retained in an assembly union.
module ed_fixed_without_beam(){
    ic_host_half(false); ic_host_half(true);
    hc_support_clearance(1) yg_right_support();
    hc_support_clearance(-1) yg_left_support();
    yg_at(1) yg_cap_local();
    yg_gibs(); hc_keepers();
    cg_cover(); cg_gib(); revision_gibs();
    or_capture(); or_pipe_clamp(); or_liner();
    rs_spacer(true,0); ir_printed();
}
module ed_fixed_other_printed(){ ed_fixed_without_beam(); sh_beam(); }
module ed_fixed_printed(){ ed_fixed_other_printed(); oh_left_cap(); }
module ed_moving_other_printed(t=ed_t){
    ed_carriage(t); ps_carriers(t); ps_blocks(t);
}
module ed_moving_printed(t=ed_t){
    ed_moving_other_printed(t); oh_moving_spacer(t);
}
module ed_fixed_hardware(){la_fixed_hardware(); oh_sensor_fasteners();}
module ed_moving_hardware(t=ed_t){la_moving_hardware(t);}

module ed_assembly(t=ed_t){
    color([.60,.70,.77]) ed_fixed_other_printed();
    color([.17,.46,.67]) oh_left_cap();
    color([.92,.55,.16]) ed_moving_other_printed(t);
    color([.96,.41,.10]) oh_moving_spacer(t);
    color([.12,.13,.15]) oh_sensor_reference();
    color([.67,.69,.72]) {ed_fixed_hardware(); ed_moving_hardware(t);}
    color([.22,.67,.40]) rs_spring(t);
    color([.45,.76,.84,.20]) {or_pipe(); ir_hose_reference();}
}

module ed_probe_geometry(){
    if(ed_probe=="sensor-other-fixed") intersection(){
        oh_sensor_reference(); ed_fixed_other_printed();
    }
    else if(ed_probe=="sensor-other-moving") intersection(){
        oh_sensor_reference(); ed_moving_printed(ed_t);
    }
    else if(ed_probe=="sensor-original-hardware") intersection(){
        oh_sensor_reference(); union(){la_fixed_hardware(); ed_moving_hardware(ed_t);}
    }
    else if(ed_probe=="flag-other-fixed") intersection(){
        oh_moving_spacer(ed_t); ed_fixed_other_printed();
    }
    else if(ed_probe=="flag-other-moving") intersection(){
        oh_flag_extension(ed_t); ed_moving_other_printed(ed_t);
    }
    else if(ed_probe=="flag-hardware") intersection(){
        oh_flag_extension(ed_t); union(){la_fixed_hardware(); ed_moving_hardware(ed_t);}
    }
    else if(ed_probe=="beam-blocked") intersection(){
        oh_moving_spacer(ed_t); oh_optical_window();
    }
    else if(ed_probe=="right-stop-shoulder") intersection(){
        ed_carriage(ed_t);
        translate([58.2,21,6+cam_stroke*ed_t]) cube([.6,2,2]);
    }
    else if(ed_probe=="left-stop-shoulder") intersection(){
        ed_carriage(ed_t);
        translate([-58.8,21,6+cam_stroke*ed_t]) cube([.6,2,2]);
    }
    else if(ed_probe=="former-trigger-projection") intersection(){
        ed_carriage(ed_t);
        translate([60,20.5,11+cam_stroke*ed_t]) cube([4,3,4]);
    }
    else if(ed_probe=="positive-control") intersection(){
        oh_moving_spacer(ed_t); oh_moving_spacer(ed_t);
    }
    else assert(false,"Unknown electric feeder probe");
}

if(ed_part=="assembly") ed_assembly();
else if(ed_part=="fixed-printed") ed_fixed_printed();
else if(ed_part=="moving-printed") ed_moving_printed();
else if(ed_part=="baseline"){
    if(ed_legacy_part=="frame") ed_carriage(ed_t);
    else la_item(ed_legacy_part,ed_side,ed_rear,ed_t);
}
else if(ed_part=="optical-left-cap") oh_left_cap();
else if(ed_part=="optical-moving-spacer") oh_moving_spacer();
else if(ed_part=="sensor-reference") oh_sensor_reference();
else if(ed_part=="sensor-hardware") oh_sensor_fasteners();
else if(ed_part=="probe") ed_probe_geometry();
else assert(false,"Unknown electric feeder part");

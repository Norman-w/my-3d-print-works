// Review instances of ONE integrated feeder; no alternate shell overlays.
// Assembly coordinates in mm. Printing orientations are separate evidence.
include <parameters.scad>
use <feeder-integrated-candidate.scad>
use <feeder-cam-guide-revision.scad>
use <feeder-guide-revision.scad>
use <feeder-supports.scad>
use <cam-study.scad>
use <feeder-seam-candidate.scad>
use <feeder-support-harness.scad>
use <outlet-retention.scad>
use <feeder-complete-hardware.scad>

rp_part="frame";
rp_side=1;
rp_rear=false;
rp_t=0;

module rp_hardware(){
    cg_old_hardware();cg_new_hardware();fh_added_hardware();seam_pins();
    sh_bolts();sh_nuts();or_hardware();
    for(side=[-1,1],rear=[false,true]){
        cam_pin(side,rear,rp_t);cam_follower_nut(side,rear,rp_t);
    }
}
module rp_item(part=rp_part,side=rp_side,rear=rp_rear,t=rp_t){
    if(part=="positive-half")ic_host_half(true);
    else if(part=="negative-half")ic_host_half(false);
    else if(part=="beam-grip")sh_beam();
    else if(part=="capture")or_capture_half(side>0);
    else if(part=="pipe-clamp")or_pipe_clamp_half(side>0);
    else if(part=="liner")or_liner();
    else if(part=="right-support")cg_right_support();
    else if(part=="left-support")union(){
        mirror([1,0,0])revision_side_support_local();feeder_spring_fixed_interface();
    }
    else if(part=="y-cap")scale([side,1,1])feeder_guide_cap_local();
    else if(part=="y-gib")scale([side,1,1])
        translate([0,0,rear?-gate_spacing:0])revision_gib_local();
    else if(part=="y-keeper")scale([side,1,1])
        translate([0,0,rear?-gate_spacing:0])revision_keeper_local();
    else if(part=="x-gib")cg_gib();
    else if(part=="x-cover")cg_cover();
    else if(part=="frame")feeder_carriage(t);
    else if(part=="finger")cam_finger(side,rear,t);
    else if(part=="hardware")rp_hardware();
    else if(part=="pc-reference")or_pipe();
    else if(part=="all-reference"){ic_fixed();cg_moving(t);}
    else assert(false,"Unknown feeder review instance");
}
rp_item();

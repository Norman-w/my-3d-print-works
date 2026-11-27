// One review host combines the current seam, X/Y guides, harness and outlet.
// No duplicate half-shell variants. mm, +Z feed. Actual Y fitting is not modelled.
include <parameters.scad>
use <feeder-seam-candidate.scad>
use <feeder-cam-guide-revision.scad>
use <feeder-guide-revision.scad>
use <feeder-supports.scad>
use <feeder-support-harness.scad>
use <outlet-retention.scad>
use <feeder-complete-hardware.scad>

ic_part="assembly";
ic_probe="motion";
ic_t=0;
ic_fault=0;

module ic_host_half(positive=true){difference(){
    union(){seam_candidate_half(positive);sh_host_additions(positive);or_host_additions(positive);}
    sh_host_cuts(positive);
    // Preserve the original negative-half reservoir after flange/ear additions.
    if(!positive) seam_reservoir_cuts();
}}
module ic_host(){ic_host_half(false);ic_host_half(true);seam_pins();}
module ic_support(){sh_beam();sh_bolts();sh_nuts();}
module ic_outlet(){or_capture();or_pipe_clamp();or_liner();or_hardware();or_pipe();}
module ic_old_fixed(){cg_fixed();cg_gib();revision_gibs();cg_old_hardware();cg_new_hardware();}
module ic_fixed(){ic_host();ic_old_fixed();ic_support();ic_outlet();fh_added_hardware();}
module ic_new_solids(){sh_ears();ic_support();for(p=[false,true])or_host_additions(p);ic_outlet();}
module ic_show(){
    color([.66,.75,.80]){ic_host_half(false);ic_host_half(true);}
    color([.52,.58,.63]){cg_fixed();cg_gib();revision_gibs();}
    color([.91,.58,.17])cg_moving(ic_t);
    color([.13,.36,.51])sh_beam();
    color([.16,.51,.61]){or_capture();or_pipe_clamp();}
    color([.89,.59,.22])or_liner();
    color([.30,.67,.78,.25])or_pipe();
    color([.27,.29,.31]){cg_old_hardware();cg_new_hardware();fh_added_hardware();seam_pins();sh_bolts();sh_nuts();or_hardware();}
}
module ic_probe_geometry(){
    if(ic_probe=="motion")intersection(){ic_fixed();cg_moving(ic_t);}
    else if(ic_probe=="frame-sweep")intersection(){ic_new_solids();import("../output/feeder-integrated-candidate/frame-sweep.stl");}
    else if(ic_probe=="new-vs-fixed")intersection(){ic_new_solids();ic_old_fixed();}
    else if(ic_probe=="new-vs-old-hardware")intersection(){ic_new_solids();fh_added_hardware();}
    else if(ic_probe=="harness-vs-outlet")intersection(){ic_support();ic_outlet();}
    else if(ic_probe=="extra-hardware-fit")intersection(){fh_added_hardware();union(){ic_host();ic_old_fixed();ic_support();ic_outlet();cg_moving(ic_t);}}
    else if(ic_probe=="seam-tools-before-frame")intersection(){fh_seam_tools();union(){ic_host();ic_outlet();ic_old_fixed();}}
    else if(ic_probe=="seam-tools-harness-obstruction")intersection(){fh_seam_tools();ic_support();}
    else if(ic_probe=="seam-nut-feed")intersection(){fh_seam_nut_feeds();union(){ic_host();ic_support();ic_outlet();}}
    else if(ic_probe=="mount-nut-feed")intersection(){fh_mount_nut_feeds();ic_host();}
    else if(ic_probe=="finger-path")intersection(){sh_finger_sweep();ic_new_solids();}
    else if(ic_probe=="old-tools-vs-new")intersection(){sh_existing_tools();ic_new_solids();}
    else if(ic_probe=="new-tools-vs-other")union(){
        intersection(){sh_tools();ic_outlet();}
        intersection(){or_tools();union(){sh_ears();ic_old_fixed();fh_added_hardware();cg_moving(ic_t);}}
    }
    else if(ic_probe=="outlet-tools-harness-obstruction")intersection(){or_tools();ic_support();}
    else if(ic_probe=="band-workspace")intersection(){or_band_envelope();union(){ic_support();ic_old_fixed();fh_added_hardware();cg_moving(ic_t);}}
    else if(ic_probe=="frame-lift")intersection(){ic_new_solids();hull()for(dy=[0,65])feeder_carriage(0,dy);}
    else if(ic_probe=="body-half-remove")intersection(){union(){ic_support();ic_outlet();}translate([25,0,0])ic_host_half(true);}
    else if(ic_probe=="body-root")intersection(){union(){for(p=[false,true]){sh_host_additions(p);or_host_additions(p);}}union(){seam_candidate_half(false);seam_candidate_half(true);}}
    else if(ic_probe=="body-corridor")intersection(){union(){sh_ears();for(p=[false,true])or_host_additions(p);}
        translate([0,0,-127])cylinder(h=197,d=41.5,$fn=96);}
    else if(ic_probe=="fault-control")intersection(){translate([0,ic_fault,0])sh_beam();ic_host();}
    else assert(false,"Unknown integrated probe");
}
if(ic_part=="assembly")ic_show();
else if(ic_part=="positive-half")ic_host_half(true);
else if(ic_part=="negative-half")ic_host_half(false);
else if(ic_part=="frame-start")feeder_carriage(0);
else if(ic_part=="probe")ic_probe_geometry();

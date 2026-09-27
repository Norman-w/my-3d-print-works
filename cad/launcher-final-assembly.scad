// Integrated feeder with the V-located followers and real spring endpoints.
// mm; +Z follows the ball feed. Spin head mounts separately on the original
// discharge PC tube, beyond the original Y fitting, not on this feed axis.
include <parameters.scad>
use <feeder-integrated-candidate.scad>
use <feeder-cam-guide-revision.scad>
use <feeder-guide-revision.scad>
use <feeder-supports.scad>
use <feeder-seam-candidate.scad>
use <feeder-support-harness.scad>
use <outlet-retention.scad>
use <feeder-complete-hardware.scad>
use <feeder-pin-seat-revision.scad>
use <feeder-return-spring.scad>
use <feeder-review-parts.scad>
use <feeder-frame-y-guide.scad>
use <feeder-hardware-clearance.scad>
use <inlet-retention-final.scad>

la_part="assembly";
la_probe="motion";
la_t=0;
la_side=1;
la_rear=false;
la_fault=0;

module la_fixed_printed(){
    ic_host_half(false);ic_host_half(true);
    hc_support_clearance(1)yg_right_support();
    hc_support_clearance(-1)yg_left_support();
    yg_caps();yg_gibs();
    hc_keepers();
    cg_cover();cg_gib();revision_gibs();
    sh_beam();or_capture();or_pipe_clamp();or_liner();
    rs_spacer(true,0);
    ir_printed();
}
module la_fixed_hardware(){
    cg_old_hardware(false);cg_new_hardware();fh_added_hardware();seam_pins();
    sh_bolts();sh_nuts();or_hardware();rs_endpoint_hardware(true,0);
    yg_hardware();ir_hardware();
}
module la_moving_printed(t=la_t){
    feeder_carriage(t);ps_carriers(t);ps_blocks(t);rs_spacer(false,t);
}
module la_moving_hardware(t=la_t){
    ps_original_pins(t);ps_added_hardware(t);rs_endpoint_hardware(false,t);
}
module la_fixed(){la_fixed_printed();la_fixed_hardware();or_pipe();ir_hose_reference();}
module la_moving(t=la_t){la_moving_printed(t);la_moving_hardware(t);}
module la_hardware(t=la_t){la_fixed_hardware();la_moving_hardware(t);}
module la_show(){
    color([.67,.75,.80]){ic_host_half(false);ic_host_half(true);}
    color([.48,.59,.65])difference(){la_fixed_printed();union(){
        ic_host_half(false);ic_host_half(true);sh_beam();
        or_capture();or_pipe_clamp();or_liner();ir_printed();
    }}
    color([.90,.56,.13])la_moving_printed();
    color([.12,.34,.47])sh_beam();
    color([.13,.48,.56]){or_capture();or_pipe_clamp();}
    color([.88,.67,.26])or_liner();
    color([.12,.4,.56]){ir_rear();ir_backplate();}
    color([.92,.60,.18])ir_front();
    color([.7,.25,.45,.35]){ir_pad_reference();ir_pad_reference(true);}
    color([.26,.28,.31])la_hardware();
    color([.13,.62,.40])rs_spring(la_t);
    color([.45,.75,.84,.24])or_pipe();
    color([.45,.75,.84,.20])ir_hose_reference();
}
module la_item(part=la_part,side=la_side,rear=la_rear,t=la_t){
    if(part=="right-support")hc_support_clearance(1)yg_right_support();
    else if(part=="left-support")hc_support_clearance(-1)yg_left_support();
    else if(part=="y-cap")yg_at(side)yg_cap_local();
    else if(part=="frame-y-gib")yg_at(side)yg_gib_local();
    else if(part=="y-keeper")scale([side,1,1])translate([0,0,rear?-gate_spacing:0])hc_keeper_local(rear);
    else if(part=="inlet-rear")ir_rear();
    else if(part=="inlet-front")ir_front();
    else if(part=="inlet-backplate")ir_backplate();
    else if(part=="hose-reference")ir_hose_reference();
    else if(part=="liner-reference"){ir_pad_reference();ir_pad_reference(true);}
    else if(part=="finger")ps_at(side,rear,t)ps_carrier_local();
    else if(part=="pin-block")ps_at(side,rear,t)ps_block_local();
    else if(part=="fixed-spacer")rs_spacer(true,0);
    else if(part=="moving-spacer")rs_spacer(false,t);
    else if(part=="hardware")la_hardware(t);
    else if(part=="spring-reference")rs_spring(t);
    else if(part=="assembly")la_show();
    else rp_item(part,side,rear,t);
}
module la_probe_geometry(){
    if(la_probe=="motion")intersection(){la_fixed();la_moving();}
    else if(la_probe=="frame-vs-followers")intersection(){feeder_carriage(la_t);ps_followers(la_t);}
    else if(la_probe=="spring-neighbors")intersection(){rs_spring(la_t,true);union(){la_fixed();la_moving();}}
    else if(la_probe=="spring-sweep")intersection(){rs_spring_continuous_sweep();la_fixed();}
    else if(la_probe=="spring-relative-sweep")intersection(){rs_spring_continuous_sweep(true);union(){
        feeder_carriage(0);rs_spacer(false,0);rs_endpoint_hardware(false,0);
    }}
    else if(la_probe=="spring-hardware")intersection(){rs_spring(la_t);union(){la_hardware();rs_spacers(la_t);}}
    else if(la_probe=="pin-tools")intersection(){ps_tools(la_t);union(){la_fixed();la_moving();}}
    else if(la_probe=="spring-tools")intersection(){rs_tools(la_t);union(){la_fixed();la_moving();}}
    else if(la_probe=="spring-fastener-fit")intersection(){rs_fasteners(la_t);union(){la_fixed_printed();la_moving_printed();}}
    else if(la_probe=="v-hardware-fit")intersection(){ps_carriers(la_t);union(){ps_blocks(la_t);ps_added_hardware(la_t);ps_original_pins(la_t);}}
    else if(la_probe=="all-fixed-hardware-fit")intersection(){la_fixed_hardware();la_fixed_printed();}
    else if(la_probe=="fault-control")intersection(){translate([la_fault,0,0])ps_carriers(la_t);la_fixed_printed();}
    else assert(false,"Unknown final assembly probe");
}
if(la_part=="probe")la_probe_geometry();else la_item();

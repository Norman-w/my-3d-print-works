// Review-only harness; not a dependency of the pure Y-guide library.
yg_library_mode=true;
include <feeder-frame-y-guide.scad>
use <feeder-integrated-candidate.scad>
use <feeder-support-harness.scad>
use <outlet-retention.scad>
use <feeder-complete-hardware.scad>
use <feeder-pin-seat-revision.scad>
yg_review_part="assembly";

// Explicit old33 composition, taken from launcher-final a8b81b6f before
// integration. The harness has NO dependency on launcher-final-assembly.
module yg_old_printed_without_caps(){
    ic_host_half(false);ic_host_half(true);cg_right_support();rs_left_support();
    for(s=[-1,1],g=[0,-gate_spacing])scale([s,1,1])translate([0,0,g])revision_keeper_local();
    cg_cover();cg_gib();revision_gibs();sh_beam();or_capture();or_pipe_clamp();or_liner();rs_spacer(true,0);
}
module yg_old_hardware_without_caps(){
    cg_old_hardware(false);cg_new_hardware();fh_added_hardware();seam_pins();
    sh_bolts();sh_nuts();or_hardware();rs_endpoint_hardware(true,0);
}
module yg_base_moving_printed(t=yg_t){feeder_carriage(t);ps_carriers(t);ps_blocks(t);rs_spacer(false,t);}
module yg_base_moving_hardware(t=yg_t){ps_original_pins(t);ps_added_hardware(t);rs_endpoint_hardware(false,t);}
module yg_base_moving(t=yg_t){yg_base_moving_printed(t);yg_base_moving_hardware(t);}
module yg_fixed_printed(){yg_old_printed_without_caps();yg_added_datums();yg_caps();yg_gibs();}
module yg_neighbors(t=yg_t){yg_old_printed_without_caps();yg_old_hardware_without_caps();
    yg_base_moving(t);rs_spring(t);}
module yg_new_only(){yg_caps();yg_gibs();yg_hardware();}

module yg_show(){
    color([.53,.65,.71,.4])yg_old_printed_without_caps();
    color([.2,.5,.65]){yg_added_datums();yg_caps();}
    color([.95,.6,.15]){yg_gibs();yg_base_moving_printed(yg_t);}
    color([.25,.26,.29]){yg_hardware();yg_old_hardware_without_caps();yg_base_moving_hardware(yg_t);}
}
module yg_probe_geometry(){
    if(yg_probe=="motion")union(){
        intersection(){yg_new_only();yg_neighbors();}
        intersection(){yg_added_datums();union(){yg_old_hardware_without_caps();yg_base_moving();}}
    }
    else if(yg_probe=="rail-sweep")intersection(){yg_rail_sweep();union(){yg_added_datums();yg_caps();yg_gibs();}}
    else if(yg_probe=="gib-fit")intersection(){yg_gibs();union(){yg_old_printed_without_caps();yg_added_datums();yg_caps();}}
    else if(yg_probe=="hardware")intersection(){yg_hardware();union(){yg_fixed_printed();yg_old_hardware_without_caps();yg_base_moving();}}
    else if(yg_probe=="hardware-pairs")for(z=yg_jack_z)intersection(){
        yg_station_hardware_local(z);yg_cap_hardware_local(skip="jack",skip_z=z);}
    else if(yg_probe=="legacy-lock-height-control")intersection(){
        translate([0,yg_cap_top-yg_lock_top,0])yg_local_tools(yg_jack_z[0]);
        yg_station_hardware_local(support_cap_screw_z[0],false);}
    else if(yg_probe=="cap-remove-sweep")intersection(){yg_at()yg_cap_remove_sweep();
        union(){yg_old_printed_without_caps();yg_old_hardware_without_caps();yg_base_moving();yg_gibs();}}
    else if(yg_probe=="tools")for(s=[-1,1])for(z=yg_jack_z)intersection(){
        yg_at(s)yg_local_tools(z);
        union(){yg_fixed_printed();yg_old_hardware_without_caps();yg_base_moving();
            yg_at(s)yg_cap_hardware_local(skip="jack",skip_z=z);
            yg_at(-s)yg_cap_hardware_local();}}
    else if(yg_probe=="mount-tools")for(s=[-1,1])for(z=support_cap_screw_z)intersection(){
        yg_at(s)yg_local_tools(z,false);
        union(){yg_fixed_printed();yg_old_hardware_without_caps();yg_base_moving();
            yg_at(s)yg_cap_hardware_local(skip="mount",skip_z=z);yg_at(-s)yg_cap_hardware_local();}}
    else if(yg_probe=="new-nut-feed")intersection(){yg_new_nut_feed();yg_cap_local();}
    else if(yg_probe=="wrong-nut-sequence")intersection(){yg_new_nut_feed();yg_gib_local();}
    else if(yg_probe=="cap-remove")intersection(){
        yg_at()translate([0,yg_remove,0])yg_cap_local();
        union(){yg_old_printed_without_caps();yg_old_hardware_without_caps();yg_base_moving();yg_gibs();}}
    else if(yg_probe=="gib-remove-sweep")intersection(){yg_at()yg_gib_remove_sweep();
        union(){yg_old_printed_without_caps();yg_old_hardware_without_caps();yg_base_moving();}}
    else if(yg_probe=="gib-remove")intersection(){
        yg_at()translate([0,yg_remove,0])yg_gib_local();
        union(){yg_old_printed_without_caps();yg_old_hardware_without_caps();yg_base_moving();}}
    else if(yg_probe=="wrong-gib-sequence")intersection(){
        translate([0,2,0])yg_gib_local();yg_cap_local();}
    else if(yg_probe=="datum-root")intersection(){yg_lower_datum_local();cg_right_support();}
    else if(yg_probe=="fixed-stop-face")intersection(){
        cg_datum();yg_box(53,54,21,24,yg_t==0?4.99:-35,yg_t==0?5:-34.99);}
    else assert(false,"Unknown Y-guide probe");
}

if(yg_review_part=="assembly")yg_show();
else if(yg_review_part=="section")intersection(){yg_show();yg_box(50,81,-20,80,-31.5,-29.5);}
else if(yg_review_part=="probe")yg_probe_geometry();
else assert(false,"Unknown Y guide review part");

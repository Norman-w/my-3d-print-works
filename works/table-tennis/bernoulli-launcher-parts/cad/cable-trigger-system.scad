// Review-only integration of the cable actuator with the CURRENT feeder.
// Units mm, original feeder CAD basis. ct_t is normalized [0,1].
// Printed parts are exported individually; this assembly is never a print job.
include <parameters.scad>
use <launcher-final-assembly.scad>
use <feeder-supports.scad>
use <feeder-support-harness.scad>
use <feeder-return-spring.scad>
use <cable-trigger-input.scad>
use <cable-output-interface.scad>
use <cable-housing-route.scad>
use <outlet-retention.scad>
use <inlet-retention-final.scad>

ct_part="assembly";
ct_probe="input-host";
ct_t=0;
ct_cover=true; // visibility only; every probe always includes the real cover
ct_housing=true;
assert(ct_t>=0 && ct_t<=1);

module ct_original_fixed_hardware(){
    // The longer actuator mounting screws replace the original four screws.
    // Keep the original captive nuts. Do not draw two bolts in each hole.
    // Boolean removal of a bolt would also cut the overlapping thread envelope
    // from its nut. Restore each original nut unchanged after the subtraction.
    difference(){la_fixed_hardware();union(){sh_bolts();sh_nuts();}}
    sh_nuts();
}
module ct_fixed_printed(){
    la_fixed_printed();ci_body();ci_cover();co_fixed_bridge();
}
module ct_original_other_moving(t=ct_t){
    // Only the frame is replaced. All followers, pin blocks and spring
    // spacer retain their original source geometry and placement.
    difference(){la_moving_printed(t);feeder_carriage(t);}
}
module ct_moving_printed(t=ct_t){
    ct_original_other_moving(t);co_frame(t);co_lug_cap(t);ci_lever(cam_stroke*t);ci_terminal_cap(cam_stroke*t);
}
module ct_show(t=ct_t){
    color([.50,.64,.70,.38])la_fixed_printed();
    color([.20,.43,.54]){ci_body();co_fixed_bridge();}
    if(ct_cover)color([.35,.60,.68,.35])ci_cover();
    color([.92,.65,.22]){co_frame(t);co_lug_cap(t);ci_lever(cam_stroke*t);ci_terminal_cap(cam_stroke*t);}
    color([.45,.67,.74])ct_original_other_moving(t);
    color([.69,.71,.72]){ct_original_fixed_hardware();la_moving_hardware(t);ci_hardware(cam_stroke*t);co_hardware(t);}
    color([.30,.75,.47])rs_spring(t);
    color([.45,.75,.84,.24]){or_pipe();ir_hose_reference();}
    if(ct_housing){color([.14,.17,.20,.85])cr_housing();color([.7,.72,.76])cr_wire();}
}
module ct_probe_geometry(){
    if(ct_probe=="input-host")intersection(){
        union(){ci_body();ci_cover();ci_lever(cam_stroke*ct_t);ci_terminal_cap(cam_stroke*ct_t);}
        union(){la_fixed_printed();la_moving_printed(ct_t);ct_original_fixed_hardware();la_moving_hardware(ct_t);}
    }
    // This exact partition has the same union as input-host; only the
    // pose-independent mating contacts need the slower regularized backend.
    else if(ct_probe=="input-host-static")intersection(){
        union(){ci_body();ci_cover();}
        union(){la_fixed_printed();ct_original_fixed_hardware();}
    }
    else if(ct_probe=="input-host-dynamic")union(){
        intersection(){union(){ci_lever(cam_stroke*ct_t);ci_terminal_cap(cam_stroke*ct_t);}
            union(){la_fixed_printed();ct_original_fixed_hardware();la_moving_printed(ct_t);la_moving_hardware(ct_t);}}
        intersection(){union(){ci_body();ci_cover();}
            union(){la_moving_printed(ct_t);la_moving_hardware(ct_t);}}
    }
    else if(ct_probe=="input-output")intersection(){
        union(){ci_body();ci_cover();ci_lever(cam_stroke*ct_t);ci_terminal_cap(cam_stroke*ct_t);}
        union(){co_fixed_bridge();co_frame(ct_t);co_lug_cap(ct_t);co_hardware(ct_t);}
    }
    else if(ct_probe=="input-hardware-host")intersection(){
        ci_hardware(cam_stroke*ct_t);
        union(){la_fixed_printed();difference(){ct_original_fixed_hardware();sh_nuts();}
            la_moving_printed(ct_t);la_moving_hardware(ct_t);co_fixed_bridge();co_frame(ct_t);co_lug_cap(ct_t);co_hardware(ct_t);}
    }
    // Four intentional M4 thread pairs: bolt major diameter 4, nut minor 3.4.
    // Their engagement is checked separately rather than called a collision.
    else if(ct_probe=="input-mount-thread-engagement")intersection(){ci_mount_hardware_cad();sh_nuts();}
    else if(ct_probe=="output-hardware-host")intersection(){
        co_hardware(ct_t);union(){la_fixed();la_moving(ct_t);}
    }
    else if(ct_probe=="frame-fixed")intersection(){co_frame(ct_t);la_fixed();}
    else if(ct_probe=="baseline-frame-fixed")intersection(){feeder_carriage(ct_t);la_fixed();}
    else if(ct_probe=="output-bridge-moving")intersection(){
        co_fixed_bridge();union(){co_frame(ct_t);co_lug_cap(ct_t);la_moving_hardware(ct_t);rs_spring(ct_t,true);}
    }
    else if(ct_probe=="input-motion")intersection(){
        union(){ci_body();ci_cover();}
        union(){ci_lever(cam_stroke*ct_t);ci_terminal_cap(cam_stroke*ct_t);}
    }
    else if(ct_probe=="spring-added")intersection(){
        rs_spring(ct_t,true);
        union(){ci_body();ci_cover();ci_lever(cam_stroke*ct_t);ci_terminal_cap(cam_stroke*ct_t);co_fixed_bridge();co_frame(ct_t);co_lug_cap(ct_t);}
    }
    else if(ct_probe=="spring-continuous-fixed")intersection(){
        rs_spring_continuous_sweep();union(){ci_body();ci_cover();co_fixed_bridge();}
    }
    else if(ct_probe=="spring-continuous-relative")intersection(){
        rs_spring_continuous_sweep(true);union(){co_frame(0);co_lug_cap(0);}
    }
    // This is an outward clearance ray, not an assumed grub-screw length.
    // End Y1000 is beyond the separately exported complete local assembly.
    else if(ct_probe=="output-screw-exit" || ct_probe=="output-screw-exit-control")intersection(){
        co_screw_exit_ray(ct_t,1000);
        union(){ct_fixed_printed();ct_moving_printed(ct_t);
            ct_original_fixed_hardware();la_moving_hardware(ct_t);
            ci_hardware(cam_stroke*ct_t);co_hardware(ct_t);
            rs_spring(ct_t,true);cr_housing();or_pipe();ir_hose_reference();
            if(ct_probe=="output-screw-exit-control")
                translate([-58,150,14.7+cam_stroke*ct_t])sphere(d=10,$fn=24);
        }
    }
    else if(ct_probe=="input-core-free")intersection(){
        union(){difference(){ci_body();ci_to_cad()ci_guide_solid();}
            ci_cover();ci_lever(cam_stroke*ct_t);ci_terminal_cap(cam_stroke*ct_t);}
        ci_cable(cam_stroke*ct_t);
    }
    // Positive control: each checker must detect a real solid overlap.
    else if(ct_probe=="solid-overlap-control")intersection(){ci_body();ci_body();}
    else assert(false,"Unknown cable system probe");
}
if(ct_part=="assembly")ct_show();
else if(ct_part=="probe")ct_probe_geometry();
else if(ct_part=="input-body")ci_body();
else if(ct_part=="input-cover")ci_cover();
else if(ct_part=="input-lever")ci_lever(cam_stroke*ct_t);
else if(ct_part=="input-terminal-cap")ci_terminal_cap(cam_stroke*ct_t);
else if(ct_part=="output-beam")co_beam();
else if(ct_part=="output-frame")co_frame(ct_t);
else if(ct_part=="output-cap")co_lug_cap(ct_t);
else if(ct_part=="contract")echo("CT_CONTRACT",[
    ["input",ci_spec()],["output",co_contract_data()],
    ["spring_length_rest",rs_L(0)],["spring_length_pulled",rs_L(1)]]);
else assert(false,"Unknown cable system item");

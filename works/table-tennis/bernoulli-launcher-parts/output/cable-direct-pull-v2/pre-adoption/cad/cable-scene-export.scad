// Instance export adapter only. Authoritative mechanical sources remain unchanged.
// Existing solids are called or partitioned; no replacement primitive geometry.
include <parameters.scad>
use <launcher-final-assembly.scad>
use <cable-trigger-system.scad>
use <cable-trigger-input.scad>
use <cable-output-interface.scad>
use <cable-housing-route.scad>
use <cable-route-retention.scad>
use <feeder-return-spring.scad>
use <feeder-pin-seat-revision.scad>
use <cam-study.scad>
use <spin-head.scad>
use <spin-complete-hardware.scad>

cse_part="contract";
cse_legacy="positive-half";
cse_side=1;
cse_rear=false;
cse_t=0;
cse_float=0;
cse_preload=0;
assert(cse_t>=0&&cse_t<=1);

module cse_follower_hardware(side=1,rear=false,t=0){
    // Exact per-instance partition of ps_added_hardware + ps_original_pins.
    ps_at(side,rear,t){ps_nut_local();ps_jack_local();}
    cam_pin(side,rear,t);
    translate([0,.1,0])cam_follower_nut(side,rear,t);
}
module cse_route_wire(){
    // Original cr_wire overlaps ci_cable's fixed tangent inside the adjuster.
    // Remove only already represented solids; union with ci/co wires is unchanged.
    // That overlap is on the fixed tangent and does not vary with trigger stroke.
    difference(){cr_wire();union(){ci_cable(0);co_wire(0);}}
}
module cse_spin_printed(part="body",f=0,p=0){
    if(part=="body")body();
    else if(part=="carriage")translate([f,0,0])carriage();
    else if(part=="pad")translate([f,0,0])pad();
    else if(part=="pad-keeper")translate([f,0,0])pad_keeper();
    else if(part=="opposite-guide")opposite_guide();
    else if(part=="cover")cover();
    else if(part=="spring-cage")spring_cage();
    else if(part=="spring-seat")translate([-p,0,0])spring_seat();
    else if(part=="pull-cap")translate([f,0,0])pull_cap();
    else if(part=="hold-fork")hold_fork();
    else assert(false,"Unknown spin printed instance");
}
module cse_item(part=cse_part,t=cse_t){
    if(part=="legacy")la_item(cse_legacy,cse_side,cse_rear,t);
    else if(part=="beam")co_beam();
    else if(part=="frame")co_frame(t);
    else if(part=="input-body")ci_body();
    else if(part=="input-lever")ci_lever(20*t);
    else if(part=="input-cover")ci_cover();
    else if(part=="output-cap")co_lug_cap(t);
    else if(part=="route-base")crr_base();
    else if(part=="route-cap")crr_cap();
    else if(part=="route-lower")crr_lower();
    else if(part=="original-fixed-hardware")ct_original_fixed_hardware();
    else if(part=="follower-hardware")cse_follower_hardware(cse_side,cse_rear,t);
    else if(part=="spring-moving-hardware")rs_endpoint_hardware(false,t);
    else if(part=="input-fixed-hardware")ci_fixed_hardware();
    else if(part=="input-moving-hardware")ci_moving_hardware(20*t);
    else if(part=="input-wire")ci_cable(20*t);
    else if(part=="output-fixed-hardware"){co_adjuster_hardware();co_ferrule_reference();}
    else if(part=="output-moving-hardware")co_terminal_hardware(t);
    else if(part=="output-wire")co_wire(t);
    else if(part=="route-hardware")crr_hardware();
    else if(part=="route-housing")cr_housing();
    else if(part=="route-wire")cse_route_wire();
    else if(part=="spring-reference")rs_spring(t);
    else if(part=="spin-printed")cse_spin_printed(cse_legacy,cse_float,cse_preload);
    else if(part=="spin-hardware")sch_hardware(cse_legacy,cse_float,cse_preload,false);
    else if(part=="spin-latch-removable-hardware")difference(){sch_latch_hardware(true);sch_latch_hardware(false);}
    else if(part=="spin-spring")sch_spring(cse_float,cse_preload);
    else if(part=="contract")echo("CABLE_SCENE_CONTRACT",[
        ["ci",ci_spec()],["co",co_contract_data()],["cr",cr_contract()],
        ["retention",crr_contract()],
        ["spring_pin_span_including_pin_d_at_t0",rs_L(0)],
        ["spring_pin_span_including_pin_d_at_t1",rs_L(1)],
        ["gate_radii_t0",[cam_gate_r(false,0),cam_gate_r(true,0)]],
        ["gate_radii_t1",[cam_gate_r(false,1),cam_gate_r(true,1)]],
        ["gate_z",[cam_gate_z(false),cam_gate_z(true)]]]);
    else assert(false,str("Unknown cable scene adapter part: ",part));
}
cse_item();

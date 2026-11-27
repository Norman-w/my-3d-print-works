// Independent Bowden output candidate. mm, X1C/.4/PETG; t=0..1.
// Wrappers replace frame / beam; original CAD and frozen 33-part viewer stay intact.
// See docs/cable-output-interface.md for the interface contract and open evidence.
include <parameters.scad>
use <feeder-supports.scad>
use <feeder-support-harness.scad>
use <feeder-return-spring.scad>
use <feeder-pin-seat-revision.scad>
use <review-launcher-baseline33.scad>

co_part="assembly";
co_t=0;
co_kind="motion";
co_fault=0;
co_eps=.02;
co_x=-58;
co_y=35.5;
co_z=15;
co_stop_z=85;
co_plate_t=8;
co_nipple_d=5;
co_nipple_l=7;
co_nipple_clear=.3;
co_wire_d=1.5;
co_wire_slot=2.2;
co_wire_tail=8; // modeled maximum below nipple centre; supplier tail minimum unresolved
co_cap_y=39.2;
co_cap_t=4;
co_cap_screws=[-62.5,-51];
co_cap_screw_z=26;
co_adjuster_thread_l=24;
co_adjuster_total_l=34;
co_adjuster_start_z=77;
co_adjuster_inlet_d=7;
co_adjuster_inlet_straight=8.5;
co_adjuster_head_af=8;
co_ferrule_d=5.5;
co_ferrule_l=11;
co_ferrule_bore_d=5;
co_ferrule_bore_l=9;
co_ferrule_wire_d=2.5;
// Nominal M4 DIN125-A metal washer. Limits BELOW are from Brighton-Best's
// 2026 PDS, not attributed to norelem 07300. Actual purchase remains open.
co_ret_id=4.3;
co_ret_id_max=4.48;
co_ret_od=9;
co_ret_od_min=8.64;
co_ret_t=.8;
co_ret_t_min=.7;
co_ret_t_max=.9;
co_ret_seat_d=9.8;
co_ret_seat_z=co_z-co_nipple_clear;
co_ret_back_y=38.9;
co_ret_front_y=39.9;
co_ret_exit_d=6;
co_lug_bottom=7;
co_m6_washer_t=1.6; // norelem 07300-106, nominal ISO7089 M6
co_m6_nut_t=3.2; // norelem 07212-106 M6/SW10, DIN439 thin nut
co_hardware_fn=72;
$fn=72;

function co_A(t=0)=[co_x,co_y,co_z+cam_stroke*t];
function co_B()=[co_x,co_y,co_stop_z];
function co_adjuster_tip()=[co_x,co_y,co_adjuster_start_z];
function co_housing_entry()=[co_x,co_y,co_adjuster_start_z+co_adjuster_total_l];
// Bounds from section-view order, NOT a manufactured cone angle/length.
function co_adjuster_transition_z_bounds()=[
    co_adjuster_start_z+co_adjuster_thread_l,
    co_housing_entry()[2]-co_adjuster_inlet_straight];
function co_ferrule_reference_tip()=[co_x,co_y,
    co_housing_entry()[2]-co_adjuster_inlet_straight];
function co_contract_data()=[
    ["units","mm"],["t_domain",[0,1]],["stroke",cam_stroke],
    ["moving_wire_axis_t0",co_A(0)],["moving_wire_axis_t1",co_A(1)],
    ["fixed_mount_datum",co_B()],["adjuster_wire_tip",co_adjuster_tip()],
    ["housing_route_entry",co_housing_entry()],
    ["housing_entry_status","verified outer inlet face; ferrule bearing position unresolved"],
    ["adjuster_inlet",[co_adjuster_inlet_d,co_adjuster_inlet_straight]],
    ["adjuster_transition_z_bounds",co_adjuster_transition_z_bounds()],
    ["adjuster_transition_status","cone angle/length unmarked; step is maximum-material reference only"],
    ["ferrule_reference_tip",co_ferrule_reference_tip()],
    ["ferrule_reference_status","straight-bore boundary pose, NOT actual bearing seat"],
    ["ferrule",[co_ferrule_d,co_ferrule_l,co_ferrule_bore_d,co_ferrule_bore_l,co_ferrule_wire_d]],
    ["nipple_material","nickel-plated brass"],
    ["nipple_screw_drive","slotted; exact slot dimensions and protrusion unresolved"],
    ["retaining_washer",[co_ret_id,co_ret_od,co_ret_t]],
    ["retaining_washer_limit_source","Brighton-Best 2026 DIN125-A PDS; supplier not ordered"],
    ["retaining_washer_limits",[[co_ret_id,co_ret_id_max],[co_ret_od_min,co_ret_od],[co_ret_t_min,co_ret_t_max]]],
    ["retaining_washer_seat",[co_ret_seat_d,co_ret_seat_z,co_ret_back_y,co_ret_front_y]],
    ["retaining_washer_full_cover_lip_min_nominal",(co_ret_od_min-co_ret_exit_d)/2-(co_ret_seat_d-co_ret_od_min)/2],
    ["nipple_axial_float_nominal_limits",[co_ret_front_y-31.8-co_nipple_l-co_ret_t_max,co_ret_front_y-31.8-co_nipple_l-co_ret_t_min]],
    ["screw_exit","open +Y Ø6, no fixed external screw length assumed"],
    ["cap_assembly_gate","metal washer provides positive capture; M4 slot/torque and actual purchased tolerances still unverified"],
    ["m6_washer_spec",["norelem 07300-106",6.4,12,co_m6_washer_t]],
    ["m6_nut_spec",["norelem 07212-106",6,10,co_m6_nut_t]],
    ["m6_stack_z",[80.2,83.4,85,93,94.6,97.8]],
    ["m6_thread_exposure_each",3.2],
    ["fixed_bridge_includes_old_beam",false],["co_beam_includes_old_beam",true],
    ["co_frame_replaces_old_frame",true],["cap_install_direction",[0,-1,0]],
    ["wire_force_direction",[0,0,1]],["wire_d",co_wire_d],
    ["wire_tail_below_center",co_wire_tail],
    ["wire_tail_outside_nipple",co_wire_tail-co_nipple_d/2],
    ["wire_tail_status","nominal installation maximum; supplier minimum/holding force not certified; trim last"],
    ["core_withdrawal_from_nipple_nominal",co_wire_tail+co_nipple_d/2],
    ["nipple",[co_nipple_d,co_nipple_l,1.8,3.5]],
    ["purchase_status","candidates only, not confirmed owned"]];
module co_contract(){echo("CO_CONTRACT",co_contract_data());}

module co_box(x0,x1,y0,y1,z0,z1){translate([x0,y0,z0])cube([x1-x0,y1-y0,z1-z0]);}
module co_ycyl(x,z,y,h,d){translate([x,y,z])rotate([-90,0,0])cylinder(h=h,d=d);}
module co_zcyl(x,y,z,h,d){translate([x,y,z])cylinder(h=h,d=d);}
module co_yhex(x,z,y,h,af){translate([x,y,z])rotate([-90,0,0])rotate([0,0,30])cylinder(h=h,d=af/cos(30),$fn=6);}
module co_zhex(x,y,z,h,af){translate([x,y,z])rotate([0,0,30])cylinder(h=h,d=af/cos(30),$fn=6);}
module co_move(t){assert(t>=0&&t<=1,"co t must be normalized 0..1");translate([0,0,cam_stroke*t])children();}

// Loaded nipple is biased to the +Z wall of its clearance pocket. The small
// nominal take-up is not a declaration of an as-printed tolerance.
module co_lug_blank(){
    co_box(-65.5,-49,28,co_cap_y,co_lug_bottom,32);
    // Positive volume into the ORIGINAL left upper side bridge, not edge contact.
    co_box(-65.5,-47,28,33,10,16);
}
module co_retaining_seat_cut(){
    co_ycyl(co_x,co_ret_seat_z,co_ret_back_y,
        co_ret_front_y-co_ret_back_y,co_ret_seat_d);
}
module co_lug_cuts(){
    co_ycyl(co_x,co_z-co_nipple_clear,31.8,co_cap_y-31.8+co_eps,
        co_nipple_d+2*co_nipple_clear);
    co_retaining_seat_cut();
    // Side-open wire channel lets the clamped nipple and wire insert together.
    co_box(co_x-co_wire_slot/2,co_x+co_wire_slot/2,
        co_y-co_wire_slot/2,co_cap_y+co_eps,co_lug_bottom-co_eps,40);
    for(x=co_cap_screws){
        co_ycyl(x,co_cap_screw_z,27.6,20,3.4);
        // Nuts enter from the free -Y face; roof takes clamp reaction in +Y.
        co_yhex(x,co_cap_screw_z,27.8,3,5.8);
    }
}
module co_frame(t=0){co_move(t)difference(){
    union(){feeder_carriage(0);co_lug_blank();}
    co_lug_cuts();
}}
module co_lug_cap(t=0,travel=0){co_move(t)difference(){
    co_box(-65.5,-48,co_cap_y,co_cap_y+co_cap_t+travel,co_lug_bottom,32);
    // The original frame bridge extends to Y54. Preserve it; notch the cap.
    co_box(-52.2,-47.8,co_cap_y-co_eps,co_cap_y+co_cap_t+travel+co_eps,9.8,16.2);
    for(x=co_cap_screws)co_ycyl(x,co_cap_screw_z,co_cap_y-co_eps,co_cap_t+travel+2*co_eps,3.4);
    co_retaining_seat_cut();
    // Metal washer captures Ø5 nipple; cap supports the washer's outer annulus.
    // Through opening has no blind face for an unknown protruding M4 screw.
    co_ycyl(co_x,co_ret_seat_z,co_cap_y-co_eps,co_cap_t+travel+2*co_eps,co_ret_exit_d);
}}

module co_lower_wrench_outer(){
    co_zcyl(co_x,co_y,78,7,18);
    co_box(co_x,-18,co_y-6,co_y+6,78,85);
}
module co_bridge_blank(){
    co_box(-65,12,-58,-46,18,26);
    co_box(-65,-51,-58,-46,18,93);
    co_box(-70,-46,-52,45,co_stop_z,co_stop_z+co_plate_t);
    // Two real triangular webs in the YZ plane, each joined at its foot.
    for(x=[-65,-55])translate([x,0,0])rotate([0,90,0])
        linear_extrude(height=4)polygon([[-24,-52],[-89,-52],[-89,39]]);
}
module co_fixed_bridge(){difference(){
    co_bridge_blank();
    co_zcyl(co_x,co_y,co_stop_z-co_eps,co_plate_t+2*co_eps,6.6);
    co_lower_wrench_outer();
}}
module co_beam(){union(){sh_beam();co_fixed_bridge();}}

module co_nipple(t=0,travel=0){co_move(t)difference(){
    co_ycyl(co_x,co_z,32,co_nipple_l+travel,co_nipple_d);
    // Factory thread is represented by an open bore, not an invented thread.
    co_ycyl(co_x,co_z,co_y,co_nipple_l+travel,4.1);
    co_zcyl(co_x,co_y,co_z-4,8,1.8);
}}
module co_nipple_envelope(t=0,travel=0){co_move(t)co_ycyl(co_x,co_z,32,co_nipple_l+travel,co_nipple_d);}
module co_terminal_hardware(t=0){co_move(t){
    co_nipple(0);
    co_retaining_washer();
    // Only the known internal M4 envelope is shown, NOT a flush-end claim.
    // Factory slotted screw length/protrusion and slot width are unmarked.
    co_ycyl(co_x,co_z,co_y+co_wire_d/2,39-(co_y+co_wire_d/2),4);
    for(x=co_cap_screws){
        // M3x16 + .5 washer + standard full M3 nut; +Y screw access.
        co_ycyl(x,co_cap_screw_z,27.7,16,3);
        co_ycyl(x,co_cap_screw_z,43.7,3,5.5);
        difference(){co_ycyl(x,co_cap_screw_z,43.2,.5,7);co_ycyl(x,co_cap_screw_z,43.18,.54,3.2);}
        difference(){co_yhex(x,co_cap_screw_z,28.2,2.4,5.5);co_ycyl(x,co_cap_screw_z,28.18,2.44,3.2);}
    }
}}
module co_retaining_washer(t=0,dx=0,dz=.3,od=co_ret_od,id=co_ret_id,th=co_ret_t,front=co_ret_front_y){co_move(t)
    difference(){
        co_ycyl(co_x+dx,co_ret_seat_z+dz,front-th,th,od);
        co_ycyl(co_x+dx,co_ret_seat_z+dz,front-th-co_eps,th+2*co_eps,id);
    }
}
module co_zwasher(z){difference(){co_zcyl(co_x,co_y,z,co_m6_washer_t,12);co_zcyl(co_x,co_y,z-co_eps,co_m6_washer_t+2*co_eps,6.4);}}
module co_znut(z){difference(){co_zhex(co_x,co_y,z,co_m6_nut_t,10);co_zcyl(co_x,co_y,z-co_eps,co_m6_nut_t+2*co_eps,6.1);}}
module co_adjuster_hardware(){
    difference(){union(){
        co_zcyl(co_x,co_y,co_adjuster_start_z,co_adjuster_thread_l,6);
        co_zhex(co_x,co_y,co_adjuster_start_z+co_adjuster_thread_l,
            co_adjuster_total_l-co_adjuster_thread_l,co_adjuster_head_af);
    }
        co_zcyl(co_x,co_y,co_adjuster_start_z-co_eps,co_adjuster_total_l+2*co_eps,3);
        co_zcyl(co_x,co_y,co_housing_entry()[2]-co_adjuster_inlet_straight,
            co_adjuster_inlet_straight+co_eps,co_adjuster_inlet_d);
        // Unmarked transition omitted: the internal step is a conservative
        // maximum-material envelope, NOT an assertion of a flat bearing seat.
    }
    co_zwasher(co_stop_z-co_m6_washer_t);
    co_zwasher(co_stop_z+co_plate_t);
    co_znut(co_stop_z-co_m6_washer_t-co_m6_nut_t);
    co_znut(co_stop_z+co_plate_t+co_m6_washer_t);
}
module co_ferrule_reference(){
    // Shallow boundary pose. Actual nose seats farther into the unmarked cone.
    // Nose chamfer/internal cone are unmarked and deliberately not invented.
    z=co_ferrule_reference_tip()[2];
    difference(){
        co_zcyl(co_x,co_y,z,co_ferrule_l,co_ferrule_d);
        co_zcyl(co_x,co_y,z-co_eps,co_ferrule_l+2*co_eps,co_ferrule_wire_d);
        co_zcyl(co_x,co_y,z+co_ferrule_l-co_ferrule_bore_l,
            co_ferrule_bore_l+co_eps,co_ferrule_bore_d);
    }
}
module co_wire(t=0){
    assert(co_wire_tail>=0,"Cable tail length cannot be negative");
    a=co_A(t);co_zcyl(a[0]+co_fault,a[1],a[2]-co_wire_tail,
        co_housing_entry()[2]-(a[2]-co_wire_tail),co_wire_d);
}
module co_hardware(t=0){co_terminal_hardware(t);co_adjuster_hardware();co_ferrule_reference();co_wire(t);}
module co_tools(t=0){
    co_move(t){
        for(x=co_cap_screws)co_ycyl(x,co_cap_screw_z,46.75,40,4);
        co_ycyl(co_x,co_z,39.05,50,3.4);
    }
    difference(){co_lower_wrench_outer();co_zhex(co_x,co_y,77.98,7.04,10.2);}
}
// A clearance ray, NOT a guessed screw envelope. Caller supplies an endpoint
// beyond the measured +Y bound of the complete assembly being checked.
module co_screw_exit_ray(t=0,end_y=200){co_move(t)
    co_ycyl(co_x,co_ret_seat_z,co_ret_front_y+co_eps,
        end_y-co_ret_front_y-co_eps,5.6);
}
module co_washer_insertion(t=0){co_move(t)
    co_ycyl(co_x,co_z,co_ret_front_y-co_ret_t,35,co_ret_od);
}
module co_existing_moving(t=0){ps_carriers(t);ps_blocks(t);rs_spacer(false,t);la_moving_hardware(t);}
module co_all_fixed(){la_fixed();co_fixed_bridge();}
module co_all_moving(t=0){co_frame(t);co_lug_cap(t);co_terminal_hardware(t);co_existing_moving(t);}
module co_new_lug(t=0){co_move(t)difference(){co_lug_blank();co_lug_cuts();}}
module co_probe(kind="motion",t=0){
    if(kind=="motion")intersection(){co_all_fixed();co_all_moving(t);}
    else if(kind=="fixed-fit")intersection(){co_fixed_bridge();difference(){la_fixed();sh_beam();}}
    else if(kind=="hardware-fit")intersection(){co_hardware(t);union(){co_beam();co_frame(t);co_lug_cap(t);}}
    else if(kind=="spring")intersection(){rs_spring(t,true);union(){co_fixed_bridge();co_frame(t);co_lug_cap(t);co_terminal_hardware(t);}}
    else if(kind=="tools")intersection(){co_tools(t);union(){co_all_fixed();co_frame(t);co_lug_cap(t);co_existing_moving(t);}}
    else if(kind=="cap-insertion")intersection(){co_lug_cap(t,35);union(){co_all_fixed();co_frame(t);co_existing_moving(t);}}
    else if(kind=="nipple-insertion")intersection(){co_nipple_envelope(t,35);union(){co_all_fixed();co_frame(t);co_existing_moving(t);}}
    else if(kind=="continuous")intersection(){co_all_fixed();hull()for(q=[0,1]){co_new_lug(q);co_lug_cap(q);co_terminal_hardware(q);}}
    else if(kind=="spring-continuous")union(){
        intersection(){rs_spring_continuous_sweep();co_fixed_bridge();}
        intersection(){rs_spring_continuous_sweep(true);union(){co_new_lug(0);co_lug_cap(0);co_terminal_hardware(0);}}
    }
    else if(kind=="frame-extract-bridge")intersection(){co_fixed_bridge();
        hull()for(dy=[0,60])translate([0,dy,0]){co_frame(t);co_lug_cap(t);co_terminal_hardware(t);}}
    else if(kind=="wire-channel")intersection(){co_wire(t);union(){co_frame(t);co_lug_cap(t);co_fixed_bridge();}}
    else if(kind=="washer-insertion")intersection(){co_washer_insertion(t);union(){co_all_fixed();co_frame(t);co_existing_moving(t);}}
    else if(kind=="screw-exit")intersection(){co_screw_exit_ray(t);union(){co_all_fixed();co_frame(t);co_lug_cap(t);co_existing_moving(t);}}
    else if(kind=="washer-float")intersection(){
        union()for(a=[0:30:330])let(r=(co_ret_seat_d-co_ret_od_min)/2)
            co_retaining_washer(t,r*cos(a),r*sin(a),co_ret_od_min,co_ret_id_max,co_ret_t_min);
        union(){co_frame(t);co_lug_cap(t);}
    }
    else if(kind=="lug-root")intersection(){feeder_carriage(0);co_lug_blank();}
    else if(kind=="bridge-root")intersection(){sh_beam();co_fixed_bridge();}
    else assert(false,"Unknown co_probe kind");
}
module co_show(t=co_t){
    color([.65,.73,.78,.25])la_fixed();
    color([.15,.43,.58])co_fixed_bridge();
    color([.9,.6,.18])co_frame(t);
    color([.94,.74,.35])co_lug_cap(t);
    color([.25,.28,.3]){co_existing_moving(t);co_hardware(t);}
    color([.1,.65,.42])rs_spring(t);
}

if(co_part=="frame")co_frame(co_t);
else if(co_part=="lug-cap")co_lug_cap(co_t);
else if(co_part=="fixed-bridge")co_fixed_bridge();
else if(co_part=="beam")co_beam();
else if(co_part=="hardware")co_hardware(co_t);
else if(co_part=="probe")co_probe(co_kind,co_t);
else if(co_part=="contract")co_contract();
else co_show();

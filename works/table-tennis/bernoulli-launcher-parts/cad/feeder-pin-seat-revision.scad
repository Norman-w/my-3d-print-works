// Independent four-follower pin-location candidate, mm. X1C/.4/PETG.
// No frozen source is edited. A print/CSG result is not a preload/tolerance release.
cg_library_mode=true;
include <feeder-cam-guide-revision.scad>
use <feeder-integrated-candidate.scad>

ps_part="assembly"; // assembly,local,section,carrier,block,probe,dimensions
ps_probe="motion";
ps_t=.5;
ps_side=1;
ps_rear=false;
ps_remove=0;
ps_fault=0;
ps_dx=0;
ps_clear=.2;
ps_eps=.02;
ps_v_half_angle=45;
ps_pin_r=cam_pin_d/2;
ps_v_apex=cam_follower_offset-ps_pin_r/sin(ps_v_half_angle);
ps_v_z=2.4;
ps_seat_y0=cam_pin_shoulder_start_y;
ps_seat_y1=cam_carrier_width/2;
ps_block_front=cam_follower_offset+ps_pin_r;
ps_block_thickness=1.6;
ps_block_back=ps_block_front+ps_block_thickness;
ps_block_y0=1;
ps_nose_y0=ps_seat_y0+.2;
ps_lower_front_setback=.7;
ps_block_half_z=2.2;
ps_lip_y0=3.7;
ps_lip_x0=ps_block_back-.2;
ps_lip_x1=27.1;
ps_lip_half_z=2.8; // ears captured by existing +Y guide lands while installed
ps_adjust_retracted=.3;
ps_adjust_advance=.5; // design compensation, NOT measured manufacturing error
ps_advance_stop=.6;
ps_retract_stop=.4;
ps_jack_y=1.5;
ps_jack_z=0;
ps_jack_d=2;
ps_jack_length=4;
ps_jack_socket=.9;
ps_jack_hole=2.4;
ps_nut_x0=25;
ps_nut_h=1.6;
ps_nut_x1=ps_nut_x0+ps_nut_h;
ps_nut_af=4;
ps_nut_slot_af=4.3;
ps_tool_d=2;
ps_tool_end=100;

assert(ps_seat_y0==cam_pin_shoulder_start_y);
assert(ps_block_back+ps_jack_length+ps_adjust_retracted<
    cam_carrier_inner_offset+cam_carrier_length);
assert(ps_lower_front_setback>ps_advance_stop);
assert(ps_advance_stop>ps_adjust_advance&&ps_retract_stop>ps_adjust_retracted);
assert(ps_block_back+ps_jack_length-ps_adjust_advance>=ps_nut_x1);
assert(ps_nut_x1<cam_carrier_inner_offset+cam_carrier_length);
assert(ps_jack_y+ps_nut_af/2<ps_lip_y0);
assert(ps_block_half_z+ps_clear<revision_datum_z0);

module ps_box(x0,x1,y0,y1,z0,z1){translate([x0,y0,z0])cube([x1-x0,y1-y0,z1-z0]);}
module ps_x_cyl(x0,x1,y,z,d){support_x_hole(y,z,x0,x1-x0,d);}
module ps_x_hex(x0,x1,y,z,af){
    translate([x0,y,z])rotate([0,90,0])cylinder(h=x1-x0,d=af/cos(30),$fn=6);
}
module ps_v_void(){
    // XZ polygon, extruded along +Y. Only the two inner diagonal faces locate.
    translate([0,ps_seat_y1+ps_eps,0])rotate([90,0,0])
        linear_extrude(height=ps_seat_y1-ps_seat_y0+ps_eps)
            polygon([[ps_v_apex,0],[ps_v_apex+ps_v_z,ps_v_z],
                [ps_block_back+.5,ps_v_z],[ps_block_back+.5,-ps_v_z],
                [ps_v_apex+ps_v_z,-ps_v_z]]);
}
module ps_new_cuts(){
    ps_v_void();
    // The block cavity starts at X22: tangent to, never undercutting, the
    // original D4/D3.4 axial shoulder's bearing annulus at Y1.75.
    ps_box(ps_block_front,ps_block_back+ps_retract_stop,
        ps_block_y0-ps_clear,ps_seat_y1+ps_eps,
        -ps_block_half_z-ps_clear,ps_block_half_z+ps_clear);
    ps_box(ps_lip_x0-ps_advance_stop,ps_lip_x1+ps_retract_stop,
        ps_lip_y0-ps_clear,ps_seat_y1+ps_eps,
        -ps_lip_half_z-ps_clear,ps_lip_half_z+ps_clear);
    ps_x_hex(ps_nut_x0-ps_clear,ps_nut_x1,ps_jack_y,ps_jack_z,ps_nut_slot_af);
    // Nut drops in from +Y BEFORE the block. The block's return lip retains it.
    ps_box(ps_nut_x0-ps_clear,ps_nut_x1,ps_jack_y,
        ps_seat_y1+ps_eps,-ps_nut_slot_af/(2*cos(30)),ps_nut_slot_af/(2*cos(30)));
    // Relief follows the screw's advanced tip; otherwise the cone/thread
    // would hit the lower cavity floor before the stated advance travel.
    ps_x_cyl(ps_block_back-ps_advance_stop,cam_carrier_inner_offset+cam_carrier_length+ps_eps,
        ps_jack_y,ps_jack_z,ps_jack_hole);
}
module ps_carrier_local(){difference(){
    union(){
        cam_finger_local();
        // Restore only the old oversized shoulder bore, with .25mm radial
        // overlap into its host; then cut the fixed V. Do not fill M3 passage.
        cam_y_cylinder([cam_follower_offset,0],ps_seat_y0,
            ps_seat_y1-ps_seat_y0,cam_pin_d+4*radial_print_clearance);
    }
    ps_new_cuts();
}}
module ps_block_local(dx=0,remove=0){translate([dx,remove,0])union(){
    // Recess the lower heel, keeping the original axial shoulder intact.
    // The pin-contact nose begins .2mm ABOVE the shoulder. The heel must not
    // bottom at X22 before the nose reaches an undersize/displaced pin.
    ps_box(ps_block_front+ps_lower_front_setback,ps_block_back,
        ps_block_y0,ps_nose_y0,-ps_block_half_z,ps_block_half_z);
    ps_box(ps_block_front,ps_block_back,ps_nose_y0,ps_seat_y1,
        -ps_block_half_z,ps_block_half_z);
    ps_box(ps_lip_x0,ps_lip_x1,ps_lip_y0,ps_seat_y1,
        -ps_lip_half_z,ps_lip_half_z);
}}
module ps_block_y_sweep(dx=0,travel=12){translate([dx,0,0])union(){
    // Exact translation of EACH convex block, not the convex hull of the L.
    ps_box(ps_block_front+ps_lower_front_setback,ps_block_back,
        ps_block_y0,ps_nose_y0+travel,-ps_block_half_z,ps_block_half_z);
    ps_box(ps_block_front,ps_block_back,ps_nose_y0,ps_seat_y1+travel,
        -ps_block_half_z,ps_block_half_z);
    ps_box(ps_lip_x0,ps_lip_x1,ps_lip_y0,ps_seat_y1+travel,
        -ps_lip_half_z,ps_lip_half_z);
}}
module ps_block_x_sweep(lo=-ps_adjust_advance,hi=ps_adjust_retracted){union(){
    ps_box(ps_block_front+ps_lower_front_setback+lo,ps_block_back+hi,
        ps_block_y0,ps_nose_y0,-ps_block_half_z,ps_block_half_z);
    ps_box(ps_block_front+lo,ps_block_back+hi,ps_nose_y0,ps_seat_y1,
        -ps_block_half_z,ps_block_half_z);
    ps_box(ps_lip_x0+lo,ps_lip_x1+hi,ps_lip_y0,ps_seat_y1,
        -ps_lip_half_z,ps_lip_half_z);
}}
module ps_nut_local(){difference(){
    ps_x_hex(ps_nut_x0,ps_nut_x1,ps_jack_y,0,ps_nut_af);
    ps_x_cyl(ps_nut_x0-ps_eps,ps_nut_x1+ps_eps,ps_jack_y,0,ps_jack_d);
}}
module ps_jack_local(dx=0){
    // DIN913 total length includes no protruding head. Tip diameter1 is the
    // catalogued flat end, represented by a short transition to thread OD2.
    translate([dx,0,0])union(){
        translate([ps_block_back,ps_jack_y,0])rotate([0,90,0])
            cylinder(h=.25,d1=1,d2=ps_jack_d,$fn=24);
        ps_x_cyl(ps_block_back+.25,ps_block_back+ps_jack_length,ps_jack_y,0,ps_jack_d);
    }
}
module ps_at(side=1,rear=false,t=ps_t){
    translate([side*cam_gate_r(rear,t),0,cam_gate_z(rear)])scale([side,1,1])children();
}
module ps_carriers(t=ps_t){for(s=[-1,1],r=[false,true])ps_at(s,r,t)ps_carrier_local();}
module ps_blocks(t=ps_t,dx=0,remove=0){for(s=[-1,1],r=[false,true])ps_at(s,r,t)ps_block_local(dx,remove);}
module ps_added_hardware(t=ps_t){for(s=[-1,1],r=[false,true])ps_at(s,r,t){ps_nut_local();ps_jack_local();}}
module ps_original_pins(t=ps_t,extract=0){for(s=[-1,1],r=[false,true]){
    cam_pin(s,r,t,extract);
    // Real nut seated at pocket's +Y end, not the old display's .1mm gap.
    translate([0,.1,0])cam_follower_nut(s,r,t);
}}
module ps_followers(t=ps_t){ps_carriers(t);ps_blocks(t);ps_added_hardware(t);ps_original_pins(t);}
module ps_tools(t=ps_t,dx=0){for(s=[-1,1],r=[false,true])ps_at(s,r,t)
    ps_x_cyl(ps_block_back+ps_jack_length+dx,ps_tool_end,ps_jack_y,0,ps_tool_d);}
module ps_carrier_sweep(){for(s=[-1,1],r=[false,true])hull()for(rad=[finger_closed_center_r,finger_open_center_r])
    translate([s*rad,0,cam_gate_z(r)])scale([s,1,1]){
        for(dx=[-ps_adjust_advance,ps_adjust_retracted]){ps_block_local(dx);ps_jack_local(dx);}ps_nut_local();
        cam_y_cylinder([cam_follower_offset,0],ps_seat_y0,
            ps_seat_y1-ps_seat_y0,cam_pin_d+4*radial_print_clearance);
    }}
module ps_local(show_pin=true){
    color([.48,.62,.73])ps_carrier_local();color([.98,.65,.20])ps_block_local();
    color([.4,.4,.43]){ps_nut_local();ps_jack_local();}
    if(show_pin)color([.7,.73,.77])translate([cam_follower_offset,0,0])cam_pin_local();
}
module ps_show(){
    color([.63,.69,.73,.4])ic_fixed();color([.3,.52,.7])feeder_carriage(ps_t);
    color([.36,.59,.72])ps_carriers();color([.98,.65,.20])ps_blocks();
    color([.45,.45,.48]){ps_added_hardware();ps_original_pins();}
}
module ps_probe_geometry(){
    if(ps_probe=="motion")intersection(){ic_fixed();union(){feeder_carriage(ps_t);ps_followers();}}
    else if(ps_probe=="frame")intersection(){feeder_carriage(ps_t);ps_followers();}
    else if(ps_probe=="hardware")intersection(){ps_carriers();union(){ps_blocks();ps_added_hardware();ps_original_pins();}}
    else if(ps_probe=="added-sweep")intersection(){ic_fixed();ps_carrier_sweep();}
    else if(ps_probe=="tools")intersection(){ps_tools();union(){ic_fixed();feeder_carriage(ps_t);ps_followers();}}
    else if(ps_probe=="root")intersection(){cam_finger_local();
        cam_y_cylinder([cam_follower_offset,0],ps_seat_y0,ps_seat_y1-ps_seat_y0,cam_pin_d+4*radial_print_clearance);}
    else if(ps_probe=="block-remove")intersection(){ps_carrier_local();ps_block_y_sweep(ps_adjust_retracted);}
    else if(ps_probe=="nut-insert")intersection(){ps_carrier_local();hull()for(dy=[0,12])translate([0,dy,0])ps_nut_local();}
    else if(ps_probe=="nut-retained")intersection(){ps_block_local();translate([0,1,0])ps_nut_local();}
    else if(ps_probe=="nut-retained-compensation")intersection(){ps_block_local(ps_dx);translate([0,1,0])ps_nut_local();}
    else if(ps_probe=="compensation-clear")intersection(){ps_carrier_local();union(){ps_block_local(ps_dx);ps_jack_local(ps_dx);}}
    else if(ps_probe=="compensation-sweep")intersection(){ps_carrier_local();union(){ps_block_x_sweep();hull()for(dx=[-ps_adjust_advance,ps_adjust_retracted])ps_jack_local(dx);}}
    else if(ps_probe=="compensation-tools")intersection(){ps_tools(ps_t,ps_dx);ic_fixed();}
    else if(ps_probe=="jack-remove")intersection(){ps_carrier_local();hull()for(dx=[0,12])ps_jack_local(dx);}
    else if(ps_probe=="pin-insert")intersection(){union(){ps_carrier_local();ps_block_local(ps_adjust_retracted);}
        union(){
            cam_y_cylinder([cam_follower_offset,0],cam_pin_start_y,
                cam_pin_shoulder_start_y-cam_pin_start_y+22,cam_pin_thread_d);
            cam_y_cylinder([cam_follower_offset,0],cam_pin_shoulder_start_y,
                cam_pin_shoulder_end_y-cam_pin_shoulder_start_y+22,cam_pin_d);
            cam_y_cylinder([cam_follower_offset,0],cam_pin_shoulder_end_y,
                cam_pin_head_thickness+22,cam_pin_head_d);
        }}
    else if(ps_probe=="pin-seat-fault")intersection(){union(){ps_carrier_local();ps_block_local();}
        translate([cam_follower_offset+ps_fault,0,0])cam_pin_local();}
    else if(ps_probe=="block-retained")intersection(){ic_fixed();
        ps_at(ps_side,ps_rear,ps_t)ps_block_local(ps_dx,.1);}
    else if(ps_probe=="block-before-frame")intersection(){feeder_carriage(ps_t);
        ps_at(ps_side,ps_rear,ps_t)ps_block_y_sweep(ps_adjust_retracted);}
    else if(ps_probe=="nut-pocket-web")intersection(){
        translate([cam_follower_offset,-cam_carrier_width/2,0])rotate([-90,0,0])
            cylinder(h=nut_depth,d=nut_af/cos(30),$fn=6);
        ps_x_hex(ps_nut_x0-ps_clear,ps_nut_x1,ps_jack_y,0,ps_nut_slot_af);
    }
    else assert(false,"unknown ps_probe");
}
if(ps_part=="assembly")ps_show();
else if(ps_part=="local")ps_local();
else if(ps_part=="section")intersection(){ps_local();ps_box(-4,32,-8,20,-5,.001);}
else if(ps_part=="v_section"){
    // Thin XZ slice exposes both V faces instead of projecting the intact
    // back wall into their opening. Visualization only, not an export part.
    color([.48,.62,.73])intersection(){ps_carrier_local();ps_box(-4,32,2.5,2.6,-5,5);}
    color([.98,.65,.20])intersection(){ps_block_local();ps_box(-4,32,2.5,2.6,-5,5);}
    color([.45,.45,.48])intersection(){union(){ps_nut_local();ps_jack_local();
        translate([cam_follower_offset,0,0])cam_pin_local();}ps_box(-4,32,2.5,2.6,-5,5);}
}
else if(ps_part=="exploded"){
    color([.48,.62,.73])ps_carrier_local();color([.98,.65,.20])ps_block_local(ps_adjust_retracted,8);
    color([.4,.4,.43]){translate([0,4,0])ps_nut_local();translate([8,0,0])ps_jack_local();}
    color([.7,.73,.77])translate([cam_follower_offset,14,0])cam_pin_local();
}
else if(ps_part=="carrier")ps_carrier_local();
else if(ps_part=="block")ps_block_local();
else if(ps_part=="probe")ps_probe_geometry();
else if(ps_part=="dimensions")echo("V apex / shoulder / block / jack",ps_v_apex,ps_seat_y0,ps_block_front,ps_block_back+ps_jack_length);

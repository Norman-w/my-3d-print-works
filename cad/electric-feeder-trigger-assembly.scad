// Selected electric feeder structure with a signal trigger; millimetres.
// The original fixed sh_beam is REPLACED by et_beam, and the separate lever
// pivots toward the grip. Catalog hardware is shown only as references.
// There is still no BY141-3 mounting or two-way drive connection.
use <electric-feeder-assembly.scad>
use <electronic-trigger-candidate.scad>
use <feeder-optical-home.scad>
use <feeder-return-spring.scad>
use <launcher-final-assembly.scad>
use <outlet-retention.scad>
use <inlet-retention-final.scad>

it_part = "assembly"; // assembly, beam, lever, probe
it_angle = 0;          // 0 released, -8 fully pulled
it_feed_t = 0;         // 0..1 maps to the 20 mm feeder stroke
it_probe = "trigger-drive-corridor";

assert(it_angle >= -8 && it_angle <= 0);
assert(it_feed_t >= 0 && it_feed_t <= 1);

module it_fixed_printed(){
    ed_fixed_without_beam();
    oh_left_cap();
    et_beam();
}
module it_moving_printed(t=it_feed_t,a=it_angle){
    ed_moving_printed(t);
    et_lever(a);
}
module it_assembly(t=it_feed_t,a=it_angle){
    color([.60,.70,.77]) ed_fixed_without_beam();
    color([.18,.45,.68]) et_beam();
    color([.17,.46,.67]) oh_left_cap();
    color([.92,.55,.16]) ed_moving_other_printed(t);
    color([.96,.41,.10]) {oh_moving_spacer(t); et_lever(a);}
    color([.12,.13,.15]) {oh_sensor_reference(); et_switch_reference();}
    color([.67,.69,.72]) {ed_fixed_hardware(); ed_moving_hardware(t); et_pivot_reference();}
    et_spring_reference(a);
    color([.22,.67,.40]) rs_spring(t);
    color([.45,.76,.84,.20]) {or_pipe(); ir_hose_reference();}
}
module it_probe_geometry(){
    if(it_probe=="trigger-drive-corridor") intersection(){
        // This is only a free-space check; it does not install a motor.
        translate([20,58,-80]) cube([100,12,140]);
        union(){et_beam(); et_lever(it_angle); et_switch_reference();
                et_pivot_reference(); et_spring_reference(it_angle);}
    }
    else if(it_probe=="lever-other-fixed") intersection(){
        et_lever(it_angle);
        union(){ed_fixed_without_beam(); oh_left_cap();}
    }
    else if(it_probe=="lever-other-moving") intersection(){
        et_lever(it_angle); ed_moving_printed(it_feed_t);
    }
    else if(it_probe=="mount-other-fixed") intersection(){
        et_mount(); union(){ed_fixed_without_beam(); oh_left_cap();}
    }
    else if(it_probe=="beam-self-positive-control") intersection(){
        et_beam(); et_beam();
    }
    else assert(false,"Unknown integrated trigger probe");
}

if(it_part=="assembly") it_assembly();
else if(it_part=="beam") et_beam();
else if(it_part=="lever") et_lever_unposed();
else if(it_part=="probe") it_probe_geometry();
else assert(false,"Unknown integrated trigger part");

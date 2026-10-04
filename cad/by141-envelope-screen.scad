// Conservative seller-gallery packaging screen, millimetres.  This cylinder is
// NOT a BY141-3 CAD model: the shared seller images do not dimension the
// selected SKU's mounting face or output-end retention. The main image says
// white tip Ø22, metal motor Ø21, and separately shows a Ø29 x 68 protective
// sleeve. For this clearance screen the full 99+30 mm length is given Ø22;
// me_d=29 deliberately over-covers the entire length as a worst-case sleeve
// bound. Neither cylinder is a printable motor, mount or linkage.
use <electric-feeder-trigger-assembly.scad>
use <electric-feeder-assembly.scad>
use <electronic-trigger-candidate.scad>
use <feeder-optical-home.scad>
use <feeder-return-spring.scad>
use <outlet-retention.scad>
use <inlet-retention-final.scad>

me_part = "probe"; // probe, envelope, context
me_target = "fixed"; // fixed, moving, hardware
me_x = 85;
me_y = 63;
me_t = 0;
me_angle = 0;

me_d = 29;
me_retracted_length = 99;
me_output_sweep = 30;
me_output_retracted_z = 8; // 45/30 rocker input pin at one nominal end
me_rear_z = me_output_retracted_z - me_retracted_length;

assert(me_t >= 0 && me_t <= 1);
assert(me_angle >= -8 && me_angle <= 0);
assert(me_d==22 || me_d==29);

module me_envelope(){
    translate([me_x,me_y,me_rear_z])
        cylinder(h=me_retracted_length+me_output_sweep,d=me_d,$fn=96);
}
module me_target_geometry(){
    if(me_target=="fixed") it_fixed_printed();
    else if(me_target=="moving") it_moving_printed(me_t,me_angle);
    else if(me_target=="hardware") {
        ed_fixed_hardware(); ed_moving_hardware(me_t);
        oh_sensor_reference(); et_switch_reference(); et_pivot_reference();
        et_spring_reference(me_angle); rs_spring(me_t);
        or_pipe(); ir_hose_reference();
    }
    else assert(false,"Unknown envelope screen target");
}

if(me_part=="probe") intersection(){me_envelope();me_target_geometry();}
else if(me_part=="envelope") me_envelope();
else if(me_part=="context") {
    color([.76,.79,.83]) it_assembly(me_t,me_angle);
    color([.95,.16,.11,.52]) me_envelope();
}
else assert(false,"Unknown envelope screen part");

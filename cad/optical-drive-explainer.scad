// Visualization-only mechanical relationship scene. Millimeters.
// The sensor/carriage geometry is imported from the current exact CAD.
// The motor panel is a NOT-FOR-PRINT schematic of a nominal 30 mm output;
// its mounting face, head retention and force/overrun are not validated.
use <feeder-optical-home.scad>
use <cable-output-interface.scad>
use <feeder-return-spring.scad>
include <parameters.scad>

ex_part = "sensor-chain"; // sensor-chain, motor-principle
ex_motor_mm = 0; // 0..30
ex_feeder_mm = min(ex_motor_mm, cam_stroke);
ex_t = ex_feeder_mm / cam_stroke;
$fn = 56;
assert(ex_motor_mm >= 0 && ex_motor_mm <= 30);

module ex_box(x0,x1,y0,y1,z0,z1){
    translate([x0,y0,z0]) cube([x1-x0,y1-y0,z1-z0]);
}

// Four real mechanical roles, no translucent overlay of the old cap/spacer:
//  fixed guide cap -> sensor; moving frame -> spring spacer -> flag.
module ex_sensor_chain(){
    // Spatial section of the actual moving frame. This removes its distant
    // arms from the explanation, without adding a second carriage solid.
    color([.62,.66,.69]) intersection(){
        co_frame(ex_t);
        ex_box(-105,-35,10,55,-10,65);
    }
    color([.19,.48,.68]) oh_left_cap();
    color([.09,.10,.12]) oh_sensor_reference();
    color([.72,.74,.76]) oh_sensor_fasteners();
    color([.94,.49,.08]) oh_moving_spacer(ex_t);
    color([.74,.75,.78]) rs_endpoint_hardware(false,ex_t);
    color([.20,.65,.37]) rs_spring(ex_t);
    color([.72,.74,.76]) rs_endpoint_hardware(true,0);
}

module ex_helix(z0,length){
    translate([0,0,z0]) linear_extrude(height=length,twist=8*360,slices=112)
        translate([5,0]) circle(d=1.5,$fn=10);
}

// Explicit displacement budget only. The body/moving sleeve are generic
// cylinders; the spring represents a required compliant/overtravel element,
// not a selected manufactured spring or completed feeder coupling.
module ex_motor_principle(){
    u=ex_motor_mm;
    x=ex_feeder_mm;
    spring_z0=100+u;
    spring_length=20+x-u; // 20 mm at u<=20, 10 mm at u=30.
    assert(spring_length>=10 && spring_length<=20);
    color([.65,.68,.70]){
        ex_box(-31,31,-23,23,-4,0);          // display floor
        for(xx=[-25,25]) translate([xx,0,65]) cylinder(h=95,d=4);
        ex_box(-34,-18,-19,19,151,157);     // fixed upper stop pair
        ex_box(18,34,-19,19,151,157);
    }
    color([.14,.18,.23]) cylinder(h=80,d=21); // nominal housing diameter
    color([.30,.38,.45]) translate([0,0,76]) cylinder(h=7,d=23);
    color([.72,.77,.82]) translate([0,0,80]) cylinder(h=20+u,d=12);
    color([.95,.55,.16]) translate([0,0,98+u]) cylinder(h=2,d=17);
    color([.95,.80,.17]) ex_helix(spring_z0,spring_length);
    color([.93,.49,.08]) difference(){
        ex_box(-29,29,-16,16,120+x,130+x); // abstract moving follower
        for(xx=[-25,25]) translate([xx,0,120+x-.05]) cylinder(h=10.1,d=4.7);
    }
}

if(ex_part=="sensor-chain") ex_sensor_chain();
else if(ex_part=="motor-principle") ex_motor_principle();
else assert(false,"Unknown explainer scene");

// SmartPaddle — Programming Pogo Pin Jig
// 3D-printed alignment fixture for flashing firmware
// 5x pogo pins (3.3V, GND, SWD_CLK, SWD_DIO, EN)
// Pogo pins: P75-B1 (1.27mm pitch standard)

include <parameters.scad>

pogo_pin_count = 5;
pogo_pitch = 1.27 * 2;  // 2.54mm between pogo pins
pogo_pin_d = 1.4;        // P75-B1 pin diameter
pogo_body_d = 2.5;       // Spring body diameter (press-fit)
pogo_body_l = 15;        // Spring body length

jig_wall = 3;
jig_body_w = 30;
jig_body_h = 25;
jig_body_l = 20;

module prog_jig() {
    difference() {
        // Main jig body
        translate([0, 0, jig_body_l/2])
            cube([jig_body_w, jig_body_h, jig_body_l], center=true);

        // Pogo pin holes (press-fit)
        for (i = [0:pogo_pin_count-1]) {
            x = (i - (pogo_pin_count-1)/2) * pogo_pitch;
            translate([x, 0, 0]) {
                // Pin hole
                cylinder(d=pogo_body_d, h=jig_body_l+2, center=true, $fn=32);
            }
        }

        // PCB alignment slot (holds edge of PCB)
        translate([0, pcb_cavity_h/2 + 2, jig_body_l/2])
            cube([jig_body_w - jig_wall*2, 3, 8], center=true);

        // Access window (to see pogo pin contact)
        translate([0, -pogo_body_l/2, jig_body_l/2])
            cube([jig_body_w - 10, jig_body_h - 10, 12], center=true);
    }
}

prog_jig();

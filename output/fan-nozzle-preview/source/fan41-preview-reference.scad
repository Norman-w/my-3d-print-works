// Display-only skin of the measured Ø41 fan outlet. NOT a printable part.
// Skin thickness is a rendering aid, NOT a measured fan wall or inner diameter.
include <fan-tee-v5-parameters.scad>
preview_skin = 0.15;
translate([0, 0, v5_fan_back_z]) difference() {
    cylinder(d=v5_fan_od, h=-v5_fan_back_z, $fn=128);
    translate([0, 0, -0.01]) cylinder(d=v5_fan_od-2*preview_skin,
        h=-v5_fan_back_z+0.02, $fn=128);
}

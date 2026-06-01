// SmartPaddle — Full Assembly
// Combines handle, battery cover, and blade reference geometry
// For visualization, export individual parts from their .scad files

include <parameters.scad>

module blade_reference() {
    // Paddle blade for visual reference only
    // Not printed — the blade is CNC wood
    color("burlywood", 0.7)
    translate([0, 0, handle_length/2 + blade_neck_l])
        scale([1.5, 1.6, 0.055])
            sphere(r=handle_width, $fn=80);
}

module assembly() {
    // Handle
    translate([0, 0, 0])
        import("handle.scad");

    // Battery cover (at handle bottom)
    translate([0, 0, -handle_length/2 + battery_cavity_l/2 + 10])
        rotate([0, 0, 0])
            import("battery_cover.scad");

    // Reference blade
    blade_reference();
}

// Uncomment to render assembly:
// assembly();

// Render individual views (for STL export, uncomment one at a time):
// handle_body is rendered from handle.scad
// battery_cover is rendered from battery_cover.scad
// prog_jig is rendered from prog_jig.scad

echo("=== SmartPaddle Enclosure ===");
echo("Handle: Open handle.scad, render, export STL");
echo("Battery Cover: Open battery_cover.scad, render, export STL");
echo("Programming Jig: Open prog_jig.scad, render, export STL");
echo("All parameters in parameters.scad — adjust for hand size");

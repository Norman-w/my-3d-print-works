// SmartPaddle — Parametric Enclosure Parameters
// All dimensions in millimeters

// === Handle (Butterfly Timo Boll ALC FL: 100×25×34 mm) ===
handle_length = 100;
handle_neck_w = 24;       // width at blade junction
handle_butt_w = 34;       // width at butt (FL flare)
handle_thickness = 25;    // front-back thickness
handle_corner_r = 3;      // cross-section corner radius
// Legacy aliases used by battery cover / jig
handle_width = handle_butt_w;
handle_height = handle_thickness;
wall_thickness = 2.0;

// === Internal Cavities ===
pcb_cavity_w = 29;    // PCB is 28mm wide, +0.5mm clearance each side
pcb_cavity_h = 8;     // Board + components height
pcb_cavity_l = 85;    // PCB is 85mm long
pcb_y_offset = -3;    // PCB cavity vertical offset from handle center

battery_cavity_w = 21;
battery_cavity_h = 6;
battery_cavity_l = 40;
battery_y_offset = pcb_y_offset + pcb_cavity_h/2 + battery_cavity_h/2 + 1; // Below PCB

// === USB-C cutout ===
usb_cutout_w = 9;
usb_cutout_h = 3.5;
usb_cutout_z = 2;     // Height from handle back face

// === Mounting bosses ===
boss_diameter = 4.2;  // M2 clearance hole
boss_height = 5;
boss_wall = 2;

// === Ventilation ===
vent_slot_w = 1.5;
vent_slot_l = 15;
vent_count = 3;

// === Blade junction ===
blade_neck_w = 24;    // FL neck width where handle meets blade
blade_neck_l = 15;    // Length of neck section
blade_neck_h = 6;     // Neck thickness

// === Battery Cover ===
cover_tolerance = 0.2; // Snap-fit clearance
cover_lip_h = 1.5;     // Lip height for snap fit
cover_lip_w = 1.0;     // Lip width
cover_fingernail_r = 5; // Fingernail opening radius

// === Battery ===
battery_w = 20;
battery_h = 5;
battery_l = 35;

// === Hex grip pattern ===
hex_size = 4;
hex_depth = 0.5;
hex_spacing = 6;

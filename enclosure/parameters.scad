// SmartPaddle — Parametric Shell Parameters
// Front/back split paddle enclosure for 3D printing
// All dimensions in mm

// === Blade (Butterfly Timo Boll ALC reference) ===
blade_width          = 150;       // Max blade width (X)
blade_tip_y          = 78.5;      // Tip Y (center origin)
blade_face_bottom_y  = -71.7;     // Face bottom Y
blade_ellipse_a      = 75;        // Ellipse semi-axis X
blade_ellipse_cy     = -10;       // Ellipse center Y offset
blade_ellipse_b      = 88;        // Ellipse semi-axis Y
blade_core_t         = 6.0;       // Blade total thickness (Z)

// === Shoulder / Neck transition ===
shoulder_top_y       = -71.7;     // Y where shoulder starts
shoulder_bottom_y    = -78.5;     // Y where handle body begins (handle join)
tang_half_w          = 9;         // Tang/neck half-width at blade-handle junction

// === Handle (FL — flared) ===
handle_length        = 100;       // Total handle length along Y
handle_thickness     = 26;        // Total handle thickness (Z)
handle_neck_w        = 24;        // Width at blade junction (X)
handle_butt_w        = 34;        // Width at butt (X)
handle_corner_r      = 4;         // Cross-section corner radius
// Derived
handle_join_y        = -78.5;     // Y where handle meets blade
handle_butt_y        = -178.5;    // Y of handle butt

// === Wall & Cavity ===
wall_t               = 2.0;       // Outer wall thickness
handle_cavity_inset  = 1.5;       // Extra inset from wall for cavity (total clearance = wall_t + inset)
rib_t                = 2.0;       // Internal rib thickness
rib_spacing          = 18;        // Rib spacing in blade area (mm)
blade_inner_floor    = 1.5;       // Floor thickness above piezo pockets in blade

// === Screw Bosses (M2 self-tapping into PETG) ===
screw_d_clearance    = 2.4;       // Clearance hole for M2 screw
screw_d_boss         = 5.5;       // Boss outer diameter
screw_d_pilot        = 1.8;       // Pilot hole for self-tapping M2 into PETG
screw_head_d         = 4.6;       // M2 countersunk head diameter
screw_head_angle     = 90;        // Countersink angle
plug_recess_d        = 6.0;       // Silicone plug recess diameter
plug_recess_depth    = 2.0;       // Silicone plug recess depth

// Screw positions [X, Y] — centered Y=0 is ellipse center
screw_positions = [
    [0,    65],   // tip center
    [48,   35],   // upper right
    [-48,  35],   // upper left
    [50,  -25],   // mid right
    [-50, -25],   // mid left
    [30,  -76],   // neck right
    [-30, -76],   // neck left
    [22, -145],   // handle (inside FL outline)
    [-22,-145],
];

// === Piezo Sensor Pockets ===
piezo_disc_d         = 20;        // Piezo disc diameter
piezo_disc_depth     = 1.0;       // Recess depth from inner surface
piezo_trench_w       = 3.0;       // Wire trench width
piezo_trench_d       = 2.0;       // Wire trench depth
// Keep disc centers inside blade outline (20 mm disc + ~3 mm edge margin).
piezo_positions = [
    [38,  52],   // upper right (near tip / 拍头区)
    [-38, 52],   // upper left
    [44, -52],   // lower right (shoulder)
    [-44,-52],   // lower left
];

// === USB-C at handle butt ===
usb_c_w              = 9.2;       // USB-C female connector width (with tolerance)
usb_c_h              = 3.6;       // USB-C female connector height
usb_c_depth          = 8;         // How deep to carve into handle

// === Alignment Pins ===
pin_d                = 3.0;       // Alignment pin diameter
pin_h                = 4.0;       // Pin height
pin_socket_clearance = 0.3;       // Socket clearance over pin
pin_positions = [
    [45,  40], [-45, 40],
    [48, -30], [-48,-30],
    [10, -120], [-10,-120],
];

// === Print / Material ===
print_tolerance      = 0.15;      // Mating surface clearance
layer_h              = 0.16;      // Target layer height

// === Derived ===
blade_half_t = blade_core_t / 2;  // Each half thickness
handle_half_t = handle_thickness / 2;

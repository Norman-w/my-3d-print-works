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
screw_d_clearance    = 2.2;       // Clearance hole for M2 screw (2.0mm shank + 0.2mm)
screw_d_boss         = 5.5;       // Boss outer diameter
screw_d_pilot        = 1.5;       // Pilot hole for self-tapping M2 into PETG (M2 Ø=2.0, 75% engagement)
screw_head_d         = 3.8;       // M2 countersunk head diameter (standard ~3.8mm)
screw_head_angle     = 90;        // Countersink angle
plug_recess_d        = 6.0;       // Silicone plug recess diameter
plug_recess_depth    = 2.0;       // Silicone plug recess depth

// Screw positions [X, Y] — centered Y=0 is ellipse center
screw_positions = [
    [0,    65],   // tip center
    [52,   45],   // upper right
    [-52,  45],   // upper left
    [55,    0],   // mid right
    [-55,   0],   // mid left
    [36,  -65],   // lower right
    [-36, -65],   // lower left
    [0,   18],   // PCB 上方 (拍头侧)
    [0,  -33],   // PCB 下方 (拍柄侧)
    [7,  -160],   // handle right
    [-7, -160],   // handle left
    [0,   -89],   // handle neck center
];

// ═══ 方案A (V1) — 拍面甜区电子元器件 ═══
//
// 布局: IM948 裸板 (13×18.5×3mm) + ESP32-C6-N8 (25×18×3mm)
//       沿拍头→拍柄方向 (Y 轴) 上下放置。
//       IMU 在上 (拍头侧)，坐落在拍头-拍柄中线上 (X=0)。
//       MCU 在下 (拍柄侧)，同中线上。
// 压电片模拟信号 → ESP32-C6 内置 12-bit SAR ADC 采集。
// IM948 → I2C/UART → ESP32-C6 直接通信。
// 电源从拍柄电池经左右信号槽引入甜区。
// 正方形槽体：横拍/直拍皆可保持正确的 X-Y 方位。
//
// ⚠️ 已知坑：ESP32-C6 无硬件 FPU（RISC-V 无 F 扩展）。
//    单精度浮点 cos() 比带 FPU 的 ESP32-S3 慢 ~20×（2377 vs 121 周期）。
//    双 IMU 传感器融合（Mahony/Madgwick）必须用定点数实现。
//    方案B (V2) 将升级为带 FPU 的 ESP32-S3。
//
pcb_cavity_center     = [0, -5];     // 槽体中心 [X,Y]，IMU 居拍头-拍柄中线
pcb_cavity_size       = [42, 42];    // 正方形 42×42：Y 向容纳 IMU (18.5) + ESP32 (18) + 间隙
pcb_cavity_depth      = 2.0;         // 每半壳槽深 (总计 4mm)

// 电源通道：电池在拍柄 → ESP32 在拍面甜区。
// 左右各一条槽走 VCC+GND，经由拍面-手柄连接处进入手柄空腔。
signal_trench_w       = 2.0;        // 槽宽（VCC+GND 两条线）
signal_trench_d       = 1.5;        // 槽深

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

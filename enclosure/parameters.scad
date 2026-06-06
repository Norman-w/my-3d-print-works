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
// 选用 PZT-5A 翻边型裸陶瓷片 (家铭电子), 20mmØ × 1mm 厚
// 翻边型正负极同面，安装时平面一侧贴拍面内壁，电极面向内腔。
// 尺寸含 FDM 打印容差 + 拆装间隙。
piezo_disc_d         = 20.5;      // 槽位直径 (PZT 20mm + 0.5mm 容差)
piezo_disc_depth     = 1.3;       // 槽深 (PZT 1mm + 0.3mm 容纳焊点与线)
piezo_trench_w       = 3.0;       // Wire trench width
piezo_trench_d       = 2.0;       // Wire trench depth
// Keep disc centers inside blade outline (20 mm disc + ~3 mm edge margin).
piezo_positions = [
    [38,  52],   // upper right (near tip / 拍头区)
    [-38, 52],   // upper left
    [44, -52],   // lower right (shoulder)
    [-44,-52],   // lower left
];

// PZT 信号调理耳槽：1MΩ 电阻 (0603) + BAT54S 双肖特基二极管 (SOT-23)
// 紧贴 PZT 槽边缘，朝向 MCU 汇聚点方向延伸，最短信号路径。
resistor_ear_w        = 5.0;       // 耳槽宽度（容纳 0603 + SOT-23 并排）
resistor_ear_l        = 7.0;       // 耳槽长度（从 PZT 槽边缘往外）
resistor_ear_d        = 1.3;       // 耳槽深度（与 PZT 槽同深）

// === USB-C at handle butt ===
// Type-C 开口横跨前后壳分型面 (Z=0)，中心在 (0,0)，前后各占一半。
// 布局（拍柄底面从外看）：
//         +X (右侧)
//   Z=+13 ═══════════ 前壳外表面
//          ● 充电灯(红绿共用)   Z=+2, X=-5 (左上)
//   Z=0   ═══════════════════ 分型面
//          ╔═══ USB-C ═══╗    中心 (0,0)
//          ╚═════════════╝
//          ○ 按钮  两段式      X=+9 (右, 远离)
//          ● WS2812彩色        Z=-5, X=-5 (左下)
//   Z=-13 ═══════════ 后壳外表面
usb_c_w              = 3.6;       // USB-C 宽度 (旋转后窄边为 X)
usb_c_h              = 9.8;       // USB-C 高度 (旋转后宽边为 Z, 含容差)
usb_c_depth          = 13;        // 向内切深度 (8mm 标准 + 5mm 贝塞尔容差)
usb_c_z              = 0;         // Z 中心在分型面 → 前后各一半

// === 充电状态 LED 导光孔 (TP4056 红/绿共用) ===
// 单孔 2mm，位于左上 (X<0, Z>0)，仅前壳。Y 深度余量 +5mm。
led_hole_d           = 2.0;       // 导光柱孔直径
led_hole_depth       = 13;        // 钻孔深度 (8mm 标准 + 5mm 余量)
led_charge_x         = -5;        // 充电灯 X (左侧)
led_charge_z         = 2;         // 充电灯 Z (前壳侧)

// === 软开关按钮（两段式台阶孔）===
// 6×6mm 轻触开关，触头 ~3.2mm，开关体 6×6mm。
//   - 外孔 Ø3.5mm：让触头帽露出（前后壳各切半个圆 → 合并后完整通孔）。
//   - 内孔 Ø7mm：从壳体内侧往外切，深度容纳开关体，台阶卡住开关不脱落。
//   - X=+9：与 USB-C 右缘 (X=+1.8) 间距 >5mm，不挤。
// 中心在分型面 (Z=0)，前后壳各切一半。
button_cap_d         = 3.5;       // 触头帽外孔直径 (开关触头 3.2 + 容差)
button_body_d        = 7.0;       // 开关体卡环内孔直径 (6×6 开关 + 容差)
button_depth         = 13;        // 外孔总深度 (8mm 基准 + 5mm 贝塞尔容差)
button_body_depth    = 6;         // 卡环从内壁往里挖的深度 (容纳 5mm 高开关体)
button_x             = 9;         // 按钮 X (右侧)
button_z             = 0;         // 按钮 Z (分型面)
// 软开关电路小槽 (AO3401 + 1N4148×2 + 100kΩ — 死虫焊)
soft_power_cavity_w  = 6;         // 槽宽
soft_power_cavity_l  = 8;         // 槽长
soft_power_cavity_d  = 1.5;       // 槽深

// === 用户交互 LED (WS2812-2020) ===
// 微型 RGB LED，位于左下 (X<0, Z<0)，仅后壳。2mm 导光孔。
ws2812_led_hole_d     = 2.0;      // 导光孔直径
ws2812_led_hole_depth = 10;       // 钻孔深度 (5mm 标准 + 5mm 贝塞尔容差)
ws2812_led_x          = -5;       // LED X (左侧)
ws2812_led_z          = -5;       // LED Z (后壳侧)

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

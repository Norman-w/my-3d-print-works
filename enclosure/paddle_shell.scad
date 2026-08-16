// SmartPaddle — 分体式球拍壳体
// 正/反面半壳，贴热床面朝下打印，PETG 材质
//
// 用法:
//   HALF = "front"  → 前壳（红色胶皮面，螺丝过孔）
//   HALF = "back"   → 后壳（黑色胶皮面, USB-C, 引导孔）
//   HALF = "both"   → 组装预览

include <parameters.scad>
include <../docs/mechanical-handoff/mechanical-contract.scad>

// ═══ 配置 ═══
USE_BEZIER_PROFILES = true; // false = 传统椭圆 + FL 手柄
// 外部皮肤: OpenSCAD CSG 并集（水密）。实时 STL 合拢仅为预览。
USE_IMPORTED_OUTER = false;
// "front"/"back" = 半壳组装件; "blade_front"|"blade_back"|"handle_front"|"handle_back" = 四零件
// "split_assembly" = 四个分打零件按装配位置叠放预览
HALF = "front";
TIP_LENGTH = 25;  // handle_back_tip 切片长度 (mm), 可由 -D 覆盖
LOFT_SLICES = USE_BEZIER_PROFILES ? 64 : 150;

// 由 scripts/bezier_to_openscad.py 生成（USE_BEZIER_PROFILES=true 时必须）
include <generated/bezier_geometry.scad>
include <bezier_profile.scad>
include <stl/interference/tail_board_cuts.scad>

// 拍柄开孔基准：以外壳实体底面为准。
// 平底裁切后 BEZIER_Y0 可能比参数 handle_butt_y 更靠拍头；若仍取 min() 会落到实体外，
// half_z_at 退回拍面半厚，充电 PCB 基台/夹持会被切坏。
actual_butt_y = USE_BEZIER_PROFILES ? BEZIER_Y0 : handle_butt_y;
handle_butt_cut_y = actual_butt_y - handle_extend_y;

$fn = 80;
eps = 0.02;
overcut = 0.5;  // Z=0 截面过切量，确保切槽干净穿透分型面
// 布尔裁剪辅助立方体；尺寸需超过拍体最大延展（Y 约 257 mm）。
BIG = 1000;

// ═══ 工具函数 ═══

function smoothstep(t) = t * t * (3 - 2 * t);

function fl_half_w(t) =
    let(waist_t = 0.32, n = handle_neck_w/2, b = handle_butt_w/2)
    t <= waist_t
        ? n * (1 - 0.06 * sin(t / waist_t * 90))
        : n * 0.94 + (b - n * 0.94) * smoothstep((t - waist_t) / (1 - waist_t));

function blade_hx(y) =
    let(t = (y - blade_ellipse_cy) / blade_ellipse_b)
    abs(t) >= 1 ? 0 : blade_ellipse_a * sqrt(1 - t*t);

function legacy_paddle_hx(y) =
    y >= shoulder_top_y ? blade_hx(y) :
    y >= shoulder_bottom_y ?
        blade_hx(shoulder_top_y) + (handle_neck_w/2 - blade_hx(shoulder_top_y)) *
            smoothstep((y - shoulder_top_y) / (shoulder_bottom_y - shoulder_top_y)) :
    y >= handle_butt_y ? fl_half_w((y - handle_join_y) / (-handle_length)) : 0;

function legacy_half_z_at(y) =
    y >= shoulder_top_y ? blade_half_t :
    y >= shoulder_bottom_y ?
        blade_half_t + (handle_half_t - blade_half_t) *
            smoothstep((y - shoulder_top_y) / (shoulder_bottom_y - shoulder_top_y)) :
    handle_half_t;

function paddle_hx(y) = legacy_paddle_hx(y);

function half_z_at(y) =
    USE_BEZIER_PROFILES ? bezier_half_z_at(y) : legacy_half_z_at(y);

function envelope_hx(y) =
    USE_BEZIER_PROFILES ? bezier_envelope_hx(y) : paddle_hx(y);

function sign(x) = x >= 0 ? 1 : -1;

function screw_position_ok(p) =
    let(x = p[0], y = p[1], hz = half_z_at(y), hx = envelope_hx(y))
    hz > wall_t + 0.3
    && abs(x) < hx - 4
    && y > handle_butt_y + 12
    && y < blade_tip_y - 10;

function screw_in_blade(p) = screw_position_ok(p) && p[1] >= shoulder_bottom_y - 2;

function screw_in_handle(p) = screw_position_ok(p) && p[1] <= shoulder_bottom_y - 10;

function screw_throughs_pcb(p) =
    len([
        for (q = pcb_through_screw_positions)
            if (p[0] == q[0] && p[1] == q[1]) 1
    ]) > 0;

// 压电槽必须完全在拍面胶皮区域内（不能越界到肩部/手柄）。
function piezo_in_blade_ok(p) =
    let(x = p[0], y = p[1], hx = envelope_hx(y), r = piezo_disc_d / 2 + 3)
    y >= shoulder_bottom_y - 2
    && y <= blade_tip_y - 12
    && abs(x) + r < hx;
    
function pin_position_ok(p) =
    let(x = p[0], y = p[1], hz = half_z_at(y), hx = envelope_hx(y))
    hz > wall_t + pin_h + 1.5 && abs(x) < hx - 3;

module z_half_space(front = true) {
    if (front) {
        // 前部半空间，保留 Z >= 0。
        translate([0, 0, BIG / 2 - eps])
            cube([BIG, BIG, BIG], center = true);
    } else {
        // 后部半空间，保留 Z <= 0。
        translate([0, 0, -BIG / 2 + eps])
            cube([BIG, BIG, BIG], center = true);
    }
}

module bezier_blade_half(front = true) {
    intersection() {
        bezier_blade_solid();
        z_half_space(front);
    }
}

module bezier_handle_half(front = true) {
    intersection() {
        bezier_handle_solid();
        z_half_space(front);
    }
}

// ═══ 圆角矩形 (XZ 平面) ═══

module rounded_rect(w, h, r) {
    rr = min(r, w/2 - eps, h/2 - eps);
    hull()
        for (sx = [-1, 1], sy = [-1, 1])
            translate([sx * (w/2 - rr), sy * (h/2 - rr)])
                circle(r = rr);
}

// ═══ 完整拍体外壳（以 Z=0 为中心） ═══

module paddle_outer() {
    if (USE_BEZIER_PROFILES && USE_IMPORTED_OUTER) {
        import("stl/outer_envelope.stl", convexity = 10);
    } else if (USE_BEZIER_PROFILES) {
        bezier_paddle_outer();
    } else {
        steps = LOFT_SLICES;
        y0 = handle_butt_y;
        y1 = blade_tip_y;
        dh = (y1 - y0) / steps;
        for (i = [0:steps-1]) {
            ym = y0 + (i + 0.5) * dh;
            hx = paddle_hx(ym);
            hz = half_z_at(ym);
            if (hx > 0.05) {
                translate([0, ym, 0])
                rotate([90, 0, 0])
                    linear_extrude(height = dh + eps, center = true) {
                        if (ym >= shoulder_top_y) {
                            scale([hx, hz]) circle(r = 1);
                        } else {
                            rounded_rect(hx * 2, hz * 2, handle_corner_r);
                        }
                    }
            }
        }
    }
}

// ═══ 内部空腔（从外部几何中减去） ═══

module protected_battery_fit_cavity() {
    fit_d = protected_14500_max_d + 2 * protected_14500_fit_radial_clearance;
    fit_l = protected_14500_max_l + 2 * protected_14500_fit_axial_clearance;
    translate(protected_14500_center)
        rotate([90, 0, 0])
            cylinder(d = fit_d, h = fit_l, center = true);
}

module handle_wire_corridor_cavities() {
    y_mid = (handle_wire_corridor_y0 + handle_wire_corridor_y1) / 2;
    y_len = handle_wire_corridor_y1 - handle_wire_corridor_y0;
    for (sx = [-1, 1]) {
        // Straight 2×2-conductor passage beside the protected 14500.
        translate([sx * handle_wire_corridor_center_x, y_mid, 0])
            cube([
                handle_wire_corridor_size,
                y_len,
                handle_wire_corridor_size,
            ], center = true);
        // Fan into the existing ±4 mm neck branches above the cell.
        hull() {
            translate([sx * handle_wire_corridor_center_x, handle_wire_corridor_y1, 0])
                cube([handle_wire_corridor_size, 0.2, handle_wire_corridor_size], center = true);
            translate([sx * handle_wire_neck_center_x, handle_wire_neck_y, 0])
                cube([handle_wire_corridor_size, 0.2, handle_wire_corridor_size], center = true);
        }
    }
}

module handle_cavity() {
    // 仅手柄中空；拍面保持实心。受保护 14500 和两束线只局部扩大
    // 原空腔；不整体放大拍柄外轮廓。
    union() {
        if (USE_BEZIER_PROFILES) {
            bezier_handle_cavity();
        } else {
            steps = 80;
            y0 = handle_butt_y + wall_t;
            y1 = shoulder_top_y + 5;
            dh = (y1 - y0) / steps;
            for (i = [0:steps-1]) {
                ym = y0 + (i + 0.5) * dh;
                outer_hx = paddle_hx(ym);
                outer_hz = half_z_at(ym);
                inner_hx = outer_hx - wall_t - handle_cavity_inset;
                inner_hz = outer_hz - wall_t - handle_cavity_inset;
                if (inner_hx > 0.5 && inner_hz > 0.5) {
                    translate([0, ym, 0])
                    rotate([90, 0, 0])
                        linear_extrude(height = dh + eps, center = true) {
                            if (ym >= shoulder_top_y) {
                                scale([inner_hx, inner_hz]) circle(r = 1);
                            } else {
                                rounded_rect(inner_hx * 2, inner_hz * 2,
                                    max(1.5, handle_corner_r - 1));
                            }
                        }
                }
            }
        }
        protected_battery_fit_cavity();
        handle_wire_corridor_cavities();
    }
}

// ═══ 螺丝 Boss（正向圆柱） ═══

module screw_bosses() {
    for (p = screw_positions)
        if (screw_position_ok(p)) {
            x = p[0]; y = p[1];
            hz = half_z_at(y);
            boss_h = hz - wall_t;
            if (boss_h > 1) {
                translate([x, y, 0])
                    cylinder(d = screw_d_boss, h = boss_h, center = false);
            }
        }
}

// 后壳半部 Boss（负 Z 方向）
module screw_bosses_back() {
    for (p = screw_positions)
        if (screw_position_ok(p)) {
            x = p[0]; y = p[1];
            hz = half_z_at(y);
            boss_h = hz - wall_t;
            if (boss_h > 1) {
                translate([x, y, -boss_h])
                    cylinder(d = screw_d_boss, h = boss_h, center = false);
            }
        }
}

// ═══ 穿过刚性 PCB 的两颗螺丝 boss ═══
// PCB 板上已留 Ø7 让位孔；boss 实心柱穿孔而过，螺丝通道由零件外层 difference 重新钻出。

// 拍面部分：填满 PCB 槽深并向拍面实心多伸 1mm 融合（两个孔位都在拍面轮廓内）。
module pcb_through_bosses_blade(front = true) {
    pocket_d = max(pcb_cavity_depth, piezo_trench_d, resistor_ear_d);
    h = min(pocket_d + 1, blade_half_t);
    for (p = pcb_through_screw_positions)
        translate([p[0], p[1], front ? 0 : -h])
            cylinder(d = screw_d_boss, h = h);
}

// 拍柄部分：从壳体内顶垂到拍面表面（留插装间隙），紧贴拍面而不悬空。
// 顶端多伸 0.5mm 嵌入壁厚以保证融合；超出部分由外层塞坑/沉孔重切修平。
module pcb_through_bosses_handle(front = true) {
    z_base = blade_half_t + handle_blade_socket_clearance;
    for (p = pcb_through_screw_positions)
        if (screw_in_handle(p)) {
            let(x = p[0], y = p[1], hz = half_z_at(y),
                h = hz - wall_t - z_base + 0.5)
            if (h > 0.5)
                translate([x, y, front ? z_base : -z_base - h])
                    cylinder(d = screw_d_boss, h = h);
        }
}

// 拍面正面：沉头螺丝从正面穿入，只开沉头间隙孔。
module blade_front_screw_channels() {
    screw_holes_clearance_blade();
    blade_pass_through_for_handle_screws();
}

// 拍面背面：保留外表皮，在 boss 内开盲引导孔供 M2 自攻。
// 穿 PCB 的螺丝需要更长咬合，孔底仅保留 0.8mm 外表皮；
// 其余拍面螺丝沿用原设计的较浅引导孔。
module blade_back_screw_channels() {
    blade_pass_through_for_handle_screws();
    for (p = screw_positions)
        if (screw_in_blade(p)) {
            let(
                x = p[0],
                y = p[1],
                hz = half_z_at(y),
                drill_h = screw_throughs_pcb(p)
                    ? hz - 0.8
                    : (hz - wall_t) * 0.7
            )
            if (drill_h > 0.2)
                translate([x, y, -drill_h])
                    cylinder(d = screw_d_pilot, h = drill_h + eps);
        }
}

module handle_screw_channels() {
    screw_holes_clearance();
    plug_recesses();
    screw_holes_pilot();
}

// ═══ 螺丝孔 ═══

module screw_holes_clearance() {
    for (p = screw_positions)
        if (screw_position_ok(p)) {
        x = p[0]; y = p[1];
        hz = half_z_at(y);
        // 间隙孔，从分型面到锥体底部
        cone_h = 1.8;  // M2 沉头螺丝帽厚度
        cone_top = hz - plug_recess_depth;
        translate([x, y, -eps])
            cylinder(d = screw_d_clearance, h = cone_top - cone_h + eps);
        // 锥形沉头：宽口在硅胶塞坑底面，向内收窄。
        translate([x, y, cone_top - cone_h])
            cylinder(d1 = screw_d_clearance, d2 = screw_head_d, h = cone_h + eps);
        }
}

module screw_holes_clearance_blade() {
    for (p = screw_positions)
        if (screw_in_blade(p)) {
        x = p[0]; y = p[1];
        hz = half_z_at(y);
        // 间隙孔，从分型面到锥体底部
        cone_h = 1.8;  // M2 沉头螺丝帽厚度
        translate([x, y, -eps])
            cylinder(d = screw_d_clearance, h = hz - cone_h + eps);
        // 锥形沉头：宽口在外表面，向内收窄。
        translate([x, y, hz - cone_h])
            cylinder(d1 = screw_d_clearance, d2 = screw_head_d, h = cone_h + eps);
        }
}

// 落在拍面鬓角内的手柄螺丝：拍面部件需要开通孔让螺丝穿过。
//（拍面多边形经鬓角延伸至 y≈-103，覆盖部分手柄螺丝位。）
module blade_pass_through_for_handle_screws() {
    for (p = screw_positions)
        if (screw_in_handle(p) && screw_position_ok(p)
            && abs(p[0]) < envelope_hx(p[1]) - 3) {
        x = p[0]; y = p[1];
        hz = half_z_at(y);
        // 螺杆间隙过孔：贯穿前后拍面（±hz 全高，正/背零件各取其半）。
        translate([x, y, -hz - eps])
            cylinder(d = screw_d_clearance, h = 2 * hz + 2 * eps);
        }
}

module screw_holes_pilot() {
    for (p = screw_positions)
        if (screw_position_ok(p)) {
        x = p[0]; y = p[1];
        hz = half_z_at(y);
        // 从分型面向内钻约 60% 壁厚的引导孔
        drill_h = (hz - wall_t) * 0.7;
        translate([x, y, -drill_h])
            cylinder(d = screw_d_pilot, h = drill_h + eps);
        }
}

// ═══ 硅胶塞凹坑（外壳外侧） ═══

module plug_recesses() {
    for (p = screw_positions)
        if (screw_position_ok(p)) {
        x = p[0]; y = p[1];
        hz = half_z_at(y);
        translate([x, y, hz - plug_recess_depth + eps])
            cylinder(d = plug_recess_d, h = plug_recess_depth + eps);
        }
}

// ═══ 压电传感器凹槽 ═══

module piezo_pockets(front = true) {
    for (p = piezo_positions) if (piezo_in_blade_ok(p)) {
        x = p[0]; y = p[1];
        hz = half_z_at(y);
        pd = min(piezo_disc_depth, hz - wall_t - 0.3);
        if (pd > 0.2) {
            if (front)
                translate([x, y, -overcut])
                    cylinder(d = piezo_disc_d, h = pd + overcut + eps);
            else
                translate([x, y, -pd - eps])
                    cylinder(d = piezo_disc_d, h = pd + eps + overcut);
        }
    }
}

// ═══ PZT 信号调理电阻耳槽 ═══
//
// 每片 PZT 旁边紧贴一个小矩形槽，容纳:
//   - 1MΩ 并联电阻 (0603 封装, 1.6×0.8mm)
//   - BAT54S 双肖特基钳位二极管 (SOT-23-3, 2.9×2.5mm)
// 总占用 ≈ 5×7mm。耳槽沿 PZT→MCU 汇聚点方向延伸，信号路径最短。
// 耳槽与 PZT 槽内侧有 1mm 重叠以保证两槽连通。
module resistor_ears(front = true) {
    cx = pcb_cavity_center[0];
    hub_y = pcb_cavity_center[1];
    for (p = piezo_positions) if (piezo_in_blade_ok(p)) {
        px = p[0]; py = p[1];
        hz = half_z_at(py);
        ed = min(resistor_ear_d, hz - wall_t - 0.3);
        if (ed > 0.2) {
            dx = cx - px; dy = hub_y - py;
            angle = atan2(dy, dx);
            ear_center_offset = piezo_disc_d / 2 + resistor_ear_l / 2 - 2;
            ear_cx = px + ear_center_offset * cos(angle);
            ear_cy = py + ear_center_offset * sin(angle);
            if (front)
                translate([ear_cx, ear_cy, ed/2])
                    rotate([0, 0, angle])
                        cube([resistor_ear_l, resistor_ear_w, ed + 2*overcut + eps], center = true);
            else
                translate([ear_cx, ear_cy, -ed/2])
                    rotate([0, 0, angle])
                        cube([resistor_ear_l, resistor_ear_w, ed + 2*overcut + eps], center = true);
        }
    }
}

// ═══ 刚性 PCB 嵌入槽 / KiCad 对照背衬源 ═══
//
// 这个 2D 轮廓是 rigid_pcb/tools/mech_geometry.py 中 SCAD_SLOT_POINTS 的机械基准。
//
// 点分类（共 38 点）：
//   - 14 个大陆接壤点：X/Y 从 pcb_cavity_center + pcb_cavity_size 自动推导
//   - 24 个 PZT 码头/尾巴点：固定几何值，独立于大陆区尺寸
// 修改 pcb_cavity_center 或 pcb_cavity_size 后，14 个接壤点自动跟随。
//
// KiCad 中会把同一批点转换为 Edge.Cuts，并在 Dwgs.User 上画背衬对照。

// ── 大陆区边界：从 cavity 参数自动推导，最终零硬编码 ──
_ml_x_l = -pcb_cavity_size[0] / 2;                           // 大陆左边界 X (-21)
_ml_x_r =  pcb_cavity_size[0] / 2;                           // 大陆右边界 X (+21)
_ml_y_t =  pcb_cavity_center[1] + pcb_cavity_size[1] / 2;   // 大陆上边界 Y (+24)
_ml_y_b =  pcb_cavity_center[1] - pcb_cavity_size[1] / 2;   // 大陆下边界 Y (-26)

// ── 栈道/尾巴几何常量（独立于大陆区尺寸的设计选择） ──
_gw_corner = 1.61;      // 栈道与大陆底角的内收量，避免锐角应力集中
_gw_bl_w   = 16.75;     // 下栈道外缘 |X|，决定下栈道宽度 = _ml_x_r - _gw_bl_w = 4.25mm
_gw_tl_outer = 19.48;   // 上栈道外缘 |X|，拍头左侧
_gw_tl_inner = 14.75;   // 上栈道内缘 |X|，拍头左侧 (6.25mm 宽)
// PCB 尾巴: MX1.25 正反各 5P 卧贴；粗栈道半宽 9mm，在 _tail_neck_y 平收（无金手指窄尖）
_tail_base_hw   = 9.00;   // 粗栈道 / 尾端半宽
_tail_mouth_hw  = 14.00;  // 大陆入口嘴口半宽（漏斗最宽）
_tail_neck_y    = -100.00; // 尾端平齐线（KiCad 板尾）
_tail_funnel_y  = -36.00;  // 粗栈道开始漏斗（靠近大陆下缘 _ml_y_b=-26）
// 兼容旧参数名（已不再画窄尖）
_tail_hw        = _tail_base_hw;
_tail_y         = _tail_neck_y;

rigid_pcb_slot_points = [
    // ─ 尾巴（平收 → 粗栈道 → 大陆入口漏斗） ─
    [ _tail_base_hw,  _tail_neck_y],            //  0 右尾端
    [-_tail_base_hw,  _tail_neck_y],            //  1 左尾端
    [-_tail_base_hw,  _tail_funnel_y],          //  2 漏斗起点（左）
    [-_tail_mouth_hw, _ml_y_b],                 //  3 大陆入口嘴口（左）
    // ─ 左下栈道 → 左侧下 PZT 码头 ─
    [-_gw_bl_w,   _ml_y_b],
    [-29.99, -40.11],
    [-28.24, -41.75],
    [-35.08, -49.05],
    [-41.65, -42.90],
    [-34.81, -35.60],
    [-33.06, -37.24],
    // ─ 大陆左侧边缘 ─
    [_ml_x_l,   _ml_y_b + _gw_corner],
    [_ml_x_l,   _ml_y_t],
    // ─ 左上栈道 → 左侧上 PZT 码头 ─
    [-_gw_tl_outer, _ml_y_t],
    [-29.66, 35.62],
    [-31.62, 34.32],
    [-37.17, 42.64],
    [-29.68, 47.63],
    [-24.13, 39.31],
    [-26.15, 37.97],
    [-_gw_tl_inner, _ml_y_t],
    // ─ 右上栈道 → 右侧上 PZT 码头 ─
    [ _gw_tl_inner, _ml_y_t],
    [ 26.15, 37.97],
    [ 24.13, 39.31],
    [ 29.68, 47.63],
    [ 37.17, 42.64],
    [ 31.62, 34.32],
    [ 29.66, 35.62],
    [ _gw_tl_outer, _ml_y_t],
    // ─ 大陆右侧边缘 ─
    [_ml_x_r,   _ml_y_t],
    [_ml_x_r,   _ml_y_b + _gw_corner],
    // ─ 右下栈道 → 右侧下 PZT 码头 ─
    [ 33.06, -37.24],
    [ 34.81, -35.60],
    [ 41.65, -42.90],
    [ 35.08, -49.05],
    [ 28.24, -41.75],
    [ 29.99, -40.11],
    [ _gw_bl_w,         _ml_y_b],
    // ─ 尾巴（右：嘴口 → 漏斗 → 尾端） ─
    [_tail_mouth_hw,    _ml_y_b],
    [_tail_base_hw,     _tail_funnel_y],
    [_tail_base_hw,     _tail_neck_y],
];

module rigid_pcb_profile_2d() {
    polygon(points = rigid_pcb_slot_points);
}

module rigid_pcb_cavity(front = true) {
    d = max(pcb_cavity_depth, piezo_trench_d, resistor_ear_d);
    if (front)
        translate([0, 0, d / 2])
            linear_extrude(height = d + 2 * overcut + eps, center = true)
                rigid_pcb_profile_2d();
    else
        translate([0, 0, -d / 2])
            linear_extrude(height = d + 2 * overcut + eps, center = true)
                rigid_pcb_profile_2d();
}

module pzt_solder_reliefs(front = true) {
    base_d = max(pcb_cavity_depth, piezo_trench_d, resistor_ear_d);
    total_d = base_d + pzt_solder_relief_extra_depth;
    z0 = front ? -overcut : -total_d - overcut;
    for (p = pzt_solder_pad_centers_scad)
        translate([p[0], p[1], z0])
            cylinder(d = pzt_solder_relief_d, h = total_d + 2 * overcut + eps);
}

// ═══ 导线通道 ═══

module wire_channels(front = true) {
    cx = pcb_cavity_center[0];  hub_y = pcb_cavity_center[1];
    hub_d = 10;
    td = piezo_trench_d;
    z0 = front ? -overcut : -td - overcut;
    zh = td + 2*overcut + eps;
    for (sx = [-1, 1]) {
        points = [for (p = piezo_positions) if (piezo_in_blade_ok(p) && sign(p[0]) == sx) p];
        if (len(points) > 0) {
            for (p = points) {
                px = p[0]; py = p[1];
                hull() {
                    translate([px, py, z0])
                        cylinder(d = piezo_trench_w, h = zh);
                    translate([cx, hub_y, z0])
                        cylinder(d = piezo_trench_w, h = zh);
                }
            }
        }
    }
    translate([cx, hub_y, z0])
        cylinder(d = hub_d, h = zh);
}

// ═══ 电源通道（拍柄电池 → 甜区 ESP32） ═══

module signal_bus_to_handle(front = true) {
    trench_w = signal_trench_w;
    trench_d = signal_trench_d;
    // 统一 Z 底起点 + 总高度，cube 和 cylinder 共用，避免 hull 渐变
    z0    = front ? -overcut : -trench_d - overcut;
    zh    = trench_d + 2*overcut + eps;
    zcube = z0 + zh / 2;                     // cube center=true 要用中心点
    pcb_left  = pcb_cavity_center[0] - pcb_cavity_size[0] / 2 + 2.5;
    pcb_right = pcb_cavity_center[0] + pcb_cavity_size[0] / 2 - 2.5;
    pcb_y     = pcb_cavity_center[1];
    entry_y_join = shoulder_bottom_y;
    entry_y_deep = shoulder_bottom_y - 20;
    entry_x      = 5;
    for (sx = [-1, 1]) {
        pcb_entry_x = sx > 0 ? pcb_right : pcb_left;
        handle_entry_x = sx * entry_x;
        hull() {
            translate([pcb_entry_x, pcb_y, zcube])
                cube([2, trench_w, zh], center = true);
            translate([handle_entry_x, entry_y_join, z0])
                cylinder(d = trench_w * 1.5, h = zh);
        }
        hull() {
            translate([handle_entry_x, entry_y_join, z0])
                cylinder(d = trench_w * 1.5, h = zh);
            translate([handle_entry_x, entry_y_deep, z0])
                cylinder(d = trench_w * 1.5, h = zh);
        }
    }
}

// ═══ PCB 安装凹槽 ═══

module pcb_main_cavity(front = true) {
    xy = pcb_cavity_center;
    wh = pcb_cavity_size;
    d  = pcb_cavity_depth;
    if (front)
        translate([xy[0], xy[1], d/2])
            cube([wh[0], wh[1], d + 2*overcut + eps], center = true);
    else
        translate([xy[0], xy[1], -d/2])
            cube([wh[0], wh[1], d + 2*overcut + eps], center = true);
}

// ═══ USB-C 母座两段式台阶开口 ═══
//
// 内圈（壳外可见）：公头大小，穿透 2mm 挡皮。
// 外圈（腔体内）：母座外壳 + 0.5mm，深约 13mm 入腔体。
// 母座从腔体向外推入，外圈容纳母座体，2mm 台阶卡住不脱出。

// ── 辅助：圆角矩形 2D 轮廓 (XZ 平面) ──
module _usb_c_rounded_rect(op_x, op_z, r) {
    hull() {
        for (x = [-1, 1], z = [-1, 1])
            translate([x * (op_x/2 - r), z * (op_z/2 - r)])
                circle(r = r);
    }
}

module usb_c_cutout() {
    // 1. 内圈：穿透挡皮 (handle_butt_cut_y → +wall端)，公头大小
    translate([0, handle_butt_cut_y, usb_c_z])
        rotate([-90, 0, 0])
            linear_extrude(height = handle_extend_y + usb_c_retain_t + eps)
                _usb_c_rounded_rect(usb_c_opening_x, usb_c_opening_z, usb_c_opening_r);

    // 2. 外圈：从挡皮后侧往腔体挖深，母座外壳 + 0.5mm
    socket_start_y = handle_butt_cut_y + handle_extend_y + usb_c_retain_t;
    translate([0, socket_start_y, usb_c_z])
        rotate([-90, 0, 0])
            linear_extrude(height = 7 + eps)
                _usb_c_rounded_rect(usb_c_socket_x, usb_c_socket_z, usb_c_socket_r);

    // 3. 线路板槽：母座右侧 +X 方向，1.6mm 板厚
    //    X: 母座外圈右缘 (+2.0) → +3.6
    //    Y: 母座挡槽 +1mm 起 15.8mm 深
    //    Z: ±6mm (前后壳共享)
    pcb_x  = usb_c_socket_x / 2;                    // PCB X 起点 (母座外圈右缘)
    pcb_dz = 6;                                     // PCB 槽 Z 半高
    pcb_y  = socket_start_y + 1;                    // PCB 槽 Y 起点 (挡槽 + 1mm)
    translate([pcb_x, pcb_y, -pcb_dz])
        cube([1.6, 15.8, pcb_dz * 2]);

    // 4. 元器件/接线空间槽：外圈切完 7mm 后的 Y 位置为起点，高 6mm。
    //    X 贯穿基台全宽，Z 为线路板高 12mm (±6mm)。
    //    用于漏出负载接线通往开关侧，以及线路板正面电子元件空间。
    clr_x  = -(usb_c_socket_x / 2);                 // 基台 X 起点 (母座外圈左侧)
    clr_w  = usb_c_socket_x + 1.6 + 2;              // 基台 X 全宽
    clr_y  = socket_start_y + 7;                    // 外圈 Y 尾端
    translate([clr_x, clr_y, -pcb_dz])
        cube([clr_w, 6, pcb_dz * 2]);

    // 5. 电池线焊点/导线空间槽：第4刀 Y 尾端为起点，直到基台 Y 末端。
    //    X: 从线路板左面 (X=+2.0) 到基台左侧 (X=-2.0)，宽 4mm。
    //    Z: ±6mm。
    //    用于腾出充电板背面电池线焊点及导线位置。
    bat_x = -(usb_c_socket_x / 2);                  // 起点 X (基台左侧)
    bat_w = usb_c_socket_x;                         // 宽 (母座外圈全宽 4mm)
    bat_y = clr_y + 6;                               // Y 起点 (第4刀尾端)
    bat_h = (actual_butt_y + 2 + 19) - bat_y + eps;  // 高 (到基台 Y 末端)
    translate([bat_x, bat_y, -pcb_dz])
        cube([bat_w, bat_h, pcb_dz * 2]);
}

// ═══ 充电 PCB 实心基台 (加法实体, 后续挖空放线路板) ═══
//
// USB-C 母座焊接在线路板上, 线路板在母座 +X 方向。
// 从台阶后 2mm 起向 Y+ 深 19mm (台阶1mm + 母座缝1mm)。
// 前后壳各贡献一半, 合壳后形成完整块, 后续挖空容纳充电模块。

module usb_c_pcb_block(front = true) {
    // 方块按尾端半高生成，但外壳截面是圆角——必须裁进外形，否则角会戳出壳外。
    hz = half_z_at(actual_butt_y);
    blk_y = actual_butt_y + 2;       // Y 起点 (台阶 1mm + 母座缝隙 1mm, 往 +Y)

    blk_x = -(usb_c_socket_x / 2);          // X 起点 (母座外圈左侧)
    blk_w = usb_c_socket_x + 1.6 + 2;      // X 宽 (母座 + 板厚 + 2mm 容差)
    intersection() {
        bezier_handle_half(front);
        if (front) {
            translate([blk_x, blk_y, 0])
                cube([blk_w, 19, hz]);
        } else {
            translate([blk_x, blk_y, -hz])
                cube([blk_w, 19, hz]);
        }
    }
}

// ═══ USB-C 母座左侧夹持固定销 (加法实体) ═══
//
// 从母座外圈左侧 (X=-2.0) 往 X- 方向伸出 1.5mm 宽的销柱。
// Y: 从墙体内侧 (actual_butt_y + 1) 向拍头 +5mm。
// Z: 从分型面向 ±3mm (前后壳各延伸 3mm)。
// 用于辅助夹持固定 USB-C 母座，防止左右窜动。

module usb_c_left_clamp(front = true) {
    clamp_x = -(usb_c_socket_x / 2) - 1.5;   // X 起点 (母座左侧往 X- 1.5mm)
    clamp_y = actual_butt_y + usb_c_retain_t; // Y 起点 (墙体内侧)
    intersection() {
        bezier_handle_half(front);
        if (front) {
            translate([clamp_x, clamp_y, 0])
                cube([1.5, 5, 3]);
        } else {
            translate([clamp_x, clamp_y, -3])
                cube([1.5, 5, 3]);
        }
    }
}

// ═══ LED 导光柱孔（拍柄底部） ═══
//
// 充电模块位于拍柄底部内腔。两个 TP4056 LED 指示灯 (红/绿)
// 通过导光柱孔通向外部，位于 USB-C 上方。

module led_light_guide_holes() {
    // 红绿共用单孔，位于左上 (X<0, Z>0)，仅在前壳打孔。
    translate([led_charge_x, handle_butt_cut_y, led_charge_z])
        rotate([-90, 0, 0])
            linear_extrude(height = led_hole_depth + eps)
                circle(d = led_hole_d);
}

// ═══ 软开关按钮孔 ═══
//
// 4.5×4.5mm 轻触开关，从分型面 (Z=0) 直接安入。
// 矩形通道 5×5mm 从外壁内侧直通腔体 (~9mm深)。
// 前 3mm 容纳开关塑料体，后 6mm 为立柱+焊爪区。
// 立柱 X=3 Y=5 Z=壳厚，Z 向接到外壳壁面提供结构支撑。
// 开关焊爪从立柱两侧 1mm 间隙伸入内腔。
// P-MOSFET 自锁电路：按下 → 上电 → ESP32 GPIO 拉低自锁。
// 长按 2s → ESP32 释放 GPIO → 关机。

module button_cutout() {
    // 按钮柱通孔: Ø3mm，穿透外壁 (button_wall_t=1mm)
    translate([button_x, handle_butt_cut_y, button_z])
        rotate([-90, 0, 0])
            linear_extrude(height = handle_extend_y + button_wall_t + eps)
                circle(d = button_cap_d);

    // 矩形通道: 5×5mm，从外壁内侧直通腔体 9mm
    // 前 3mm 容纳 4.5×4.5 开关体，后 6mm 为立柱（5mm）+ 焊爪间隙（1mm）
    pocket_start = actual_butt_y + button_wall_t;
    translate([button_x, pocket_start, button_z])
        rotate([-90, 0, 0])
            linear_extrude(height = 9 + eps)
                square([button_pocket_w, button_pocket_w], center = true);
}

// ═══ 按钮立柱（加法实体，接驳到 Z 向外壳壁） ═══
//
// 立柱 X=3 Y=5 Z=壳厚，位于开关体后壁 (pocket_start+3)。
// Z 向从分型面 (0) 直通外壳表面，与壳壁一体化，非悬浮片。
// 开关焊爪从立柱两侧 1mm 间隙 (X方向) 伸入内腔。

module button_retention_column(front = true) {
    pocket_start = actual_butt_y + button_wall_t;
    hz = half_z_at(actual_butt_y);   // 拍柄尾端半高
    col_y = pocket_start + 3;        // 立柱 Y 起点 (开关体槽后壁)
    col_x = button_x - 1.5;          // 立柱 X 起點 (3mm 宽居中)

    // 方块裁进外壳，接到外壁但不戳破圆角外形。
    intersection() {
        bezier_handle_half(front);
        if (front) {
            translate([col_x, col_y, 0])
                cube([3, 5, hz]);
        } else {
            translate([col_x, col_y, -hz])
                cube([3, 5, hz]);
        }
    }
}

// ═══ 软开关电路元件槽 ═══
//
// 容纳 AO3401 P-MOSFET + 1N4148×2 + 100kΩ 电阻 (死虫焊)。
// 位于按钮內侧旁。

module soft_power_circuit_cavity() {
    // 放在按钮孔内侧壁上（后壳侧），容纳贴片元件。
    translate([button_x + 5, handle_butt_cut_y + 2, button_z - 3])
        rotate([90, 0, 0])
            cube([soft_power_cavity_w, soft_power_cavity_l, soft_power_cavity_d + eps], center = true);
}

// ═══ 用户交互 LED 导光孔 (WS2812-2020) ═══
//
// WS2812-2020 智能 RGB LED（1.6×1.6mm），位于按钮左侧。
// 状态指示灯：蓝闪配网 / 绿常亮AP / 红闪低电量 / 紫闪OTA。
// LED 贴在拍柄底部内壁，焊线引出到 PCB 区域侧。

module ws2812_led_hole() {
    translate([ws2812_led_x, handle_butt_cut_y, ws2812_led_z])
        rotate([-90, 0, 0])
            linear_extrude(height = ws2812_led_hole_depth + eps)
                circle(d = ws2812_led_hole_d);
}

// ═══ 定位销 & 定位孔 ═══

module alignment_pins() {
    for (p = pin_positions)
        if (pin_position_ok(p)) {
        x = p[0]; y = p[1];
        hz = half_z_at(y);
        if (hz > wall_t + pin_h + 1) {
            translate([x, y, 0])
                cylinder(d = pin_d, h = pin_h);
        }
        }
}

module alignment_sockets() {
    for (p = pin_positions)
        if (pin_position_ok(p)) {
        x = p[0]; y = p[1];
        hz = half_z_at(y);
        if (hz > wall_t + pin_h + 1) {
            translate([x, y, -eps])
                cylinder(d = pin_d + pin_socket_clearance * 2, h = pin_h + 1);
        }
        }
}

// ═══ 拍面内部加强筋 ═══

module blade_ribs() {
    for (y = [shoulder_top_y + rib_spacing : rib_spacing : blade_tip_y - 15]) {
        hx = paddle_hx(y) - wall_t - 3;
        hz = half_z_at(y) - wall_t - blade_inner_floor;
        if (hx > 3 && hz > 0.3) {
            translate([0, y, wall_t])
            rotate([90, 0, 0])
                linear_extrude(height = rib_t, center = true)
                    scale([hx, hz])
                        circle(r = 1);
        }
    }
}

module outer_skin_front() {
    if (USE_BEZIER_PROFILES) {
        union() {
            bezier_blade_half(true);
            bezier_handle_half(true);
        }
    } else {
        intersection() {
            paddle_outer();
            z_half_space(true);
        }
    }
}

module outer_skin_back() {
    if (USE_BEZIER_PROFILES) {
        union() {
            bezier_blade_half(false);
            bezier_handle_half(false);
        }
    } else {
        intersection() {
            paddle_outer();
            z_half_space(false);
        }
    }
}

// ═══ 通用螺丝 Boss 立柱（带末端扩展） ═══
// h: 总高度。前后 boss 均使用 direction=+1。
// 扩展端（宽头）在远端——前壳在外部壁面，后壳在分型面。
module screw_boss_column(h, direction) {
    flare_h = 1.2;
    flare_d = 7;
    shaft_d = 6;
    if (h > 0.3) {
        union() {
            // 从起始点向内的直杆
            if (h > flare_h) {
                translate([0, 0, direction * 0.01])
                    cylinder(d = shaft_d, h = h - flare_h, center = false);
            }
            // 末端的扩展
            hull() {
                translate([0, 0, direction * (h - flare_h)])
                    cylinder(d = shaft_d, h = 0.02, center = false);
                translate([0, 0, direction * (h - 0.01)])
                    cylinder(d = flare_d, h = 0.02, center = false);
            }
        }
    }
}

// ═══ 分打拍柄：朝拍头端 U 型插口 ═══
// 仅 handle_* / four 预览启用；front/back 整半壳仍靠 union(拍面) 填实，不留插装缝。

function handle_open_blade_socket() =
    HALF == "handle_front"
    || HALF == "handle_back"
    || HALF == "handle_back_tip"
    || HALF == "four"
    || HALF == "split_assembly";

module handle_blade_insert_socket() {
    // 用完整拍面（前后两半合并后的实体）直接减拍柄，得到与拍面颈部同形的夹持口。
    // XY 用 offset 留装配间隙，Z 同步加厚；拍面轮廓延伸到柄内约 25mm，
    // 因而相减后朝拍头端自然敞开，外围不会再残留闭合端环。
    clr = handle_blade_socket_clearance;
    linear_extrude(height = blade_core_t + 2 * clr, center = true)
        offset(delta = clr)
            polygon(points = BEZIER_BLADE_POLY);
}

// ═══ 四个可打印零件（拍面/拍柄 × 前/后） ═══

module blade_front_part() {
    module _cutouts() {
        screw_holes_clearance_blade();
        blade_pass_through_for_handle_screws();
        piezo_pockets(front = true);
        wire_channels(front = true);
        signal_bus_to_handle(front = true);
        rigid_pcb_cavity(front = true);
        pcb_main_cavity(front = true);
        pzt_solder_reliefs(front = true);
    }
    difference() {
        union() {
            difference() {
                union() {
                    bezier_blade_half(true);
                    blade_ribs();
                }
                _cutouts();
            }
            // PCB 槽切完后补 boss，再由外层重钻螺丝通道（保住沉孔）。
            pcb_through_bosses_blade(front = true);
        }
        blade_front_screw_channels();
    }
    for (p = pin_positions)
        if (pin_position_ok(p) && p[1] > shoulder_bottom_y) {
            let(x = p[0], y = p[1], hz = half_z_at(y))
            if (hz > wall_t + pin_h + 1)
                translate([x, y, 0])
                    cylinder(d = pin_d, h = pin_h);
        }
}

module blade_back_part() {
    module _cutouts() {
        blade_pass_through_for_handle_screws();
        piezo_pockets(front = false);
        wire_channels(front = false);
        signal_bus_to_handle(front = false);
        rigid_pcb_cavity(front = false);
        pcb_main_cavity(front = false);
        pzt_solder_reliefs(front = false);
    }
    difference() {
        union() {
            difference() {
                union() {
                    bezier_blade_half(false);
                    blade_ribs();
                    for (p = screw_positions)
                        if (screw_in_blade(p)) {
                            let(x = p[0], y = p[1], hz = half_z_at(y),
                                boss_h = hz - wall_t)
                            if (boss_h > 0.2)
                                translate([x, y, -boss_h])
                                    cylinder(d = screw_d_boss, h = boss_h);
                        }
                }
                _cutouts();
            }
            // PCB 槽切完后补 boss，再由外层重钻贯穿引导孔。
            pcb_through_bosses_blade(front = false);
        }
        blade_back_screw_channels();
    }
    for (p = pin_positions)
        if (pin_position_ok(p) && p[1] > shoulder_bottom_y) {
            let(x = p[0], y = p[1], hz = half_z_at(y))
            if (hz > wall_t + pin_h + 1)
                translate([x, y, -eps])
                    cylinder(d = pin_d + pin_socket_clearance * 2, h = pin_h + 1);
        }
}

module handle_front_part() {
    difference() {
        union() {
            difference() {
                union() {
                    // 先挖空壳体，再加 boss 立柱，避免空腔把 boss 切掉。
                    difference() {
                        bezier_handle_half(true);
                        handle_cavity();
                    }
                    for (p = screw_positions)
                        if (screw_in_handle(p) && !screw_throughs_pcb(p)) {
                            let(x = p[0], y = p[1], hz = half_z_at(y),
                                boss_h = hz - wall_t - 3)
                            if (boss_h > 0.5)
                            intersection() {
                                bezier_handle_half(true);
                                translate([x, y, 0])
                                    screw_boss_column(boss_h, 1);
                            }
                        }
                    // 旧外购充电总成基台/夹持已废弃：充电在 pcb-tail 自研尾板实现。
                    // USB/按钮/LED 开孔由 Step6 按 KiCad 位姿干涉，不再在此硬编码。
                }
                rigid_pcb_cavity(front = true);
                pcb_main_cavity(front = true);
                if (handle_open_blade_socket())
                    handle_blade_insert_socket();
            }
            // PCB 螺丝 boss：从内顶垂到拍面表面，插口切完后再补。
            pcb_through_bosses_handle(front = true);
        }
        handle_screw_channels();
    }
}

module handle_back_part() {
    difference() {
        union() {
            difference() {
                union() {
                    difference() {
                        bezier_handle_half(false);
                        handle_cavity();
                    }
                    for (p = screw_positions)
                        if (screw_in_handle(p) && !screw_throughs_pcb(p)) {
                            let(x = p[0], y = p[1], hz = half_z_at(y),
                                boss_h = hz - wall_t)
                            intersection() {
                                bezier_handle_half(false);
                                translate([x, y, -boss_h])
                                    cylinder(d = screw_d_boss, h = boss_h);
                            }
                        }
                    // 旧外购充电总成基台/夹持/软开关槽已废弃（见 handle_front_part）。
                }
                rigid_pcb_cavity(front = false);
                pcb_main_cavity(front = false);
                if (handle_open_blade_socket())
                    handle_blade_insert_socket();
            }
            // PCB 螺丝 boss：从内顶垂到拍面表面，插口切完后再补。
            pcb_through_bosses_handle(front = false);
        }
        handle_screw_channels();
    }
}

// ═══ 组装半壳（拍面 + 拍柄，同侧 Z 分割） ═══

module front_half() {
    union() {
        blade_front_part();
        handle_front_part();
    }
}

module back_half() {
    union() {
        blade_back_part();
        handle_back_part();
    }
}

// ═══ M6 四层连续承力结构 ═══
// 第 2/3 层都是“拍头 + 完整拍柄”主板；第 1/4 层仅为拍柄外贴层。
// 旧 blade_* / handle_* 模块保留为电子槽和螺丝结构的实现细节，不再直接导出。

module m6_full_planform_2d() {
    union() {
        polygon(points = BEZIER_BLADE_POLY);
        bezier_handle_planform_2d();
    }
}

module m6_full_planform_prism() {
    linear_extrude(height = BIG * 2, center = true)
        m6_full_planform_2d();
}

// ═══ 工程推演预览体（非打印件） ═══
// 这些实体把最终模型的设计依据拆开，供“按步骤”模式解释实际建模思路。
module m6_stage_planform() {
    linear_extrude(height = 0.8, center = true)
        m6_full_planform_2d();
}

module m6_stage_handle_envelope() {
    union() {
        bezier_handle_half(true);
        bezier_handle_half(false);
    }
}

module m6_stage_continuous_blank() {
    union() {
        m6_core_blank(true);
        m6_core_blank(false);
    }
}

module m6_stage_voids() {
    intersection() {
        union() {
            handle_cavity();
            wire_channels(front = true);
            wire_channels(front = false);
            signal_bus_to_handle(front = true);
            signal_bus_to_handle(front = false);
            rigid_pcb_cavity(front = true);
            rigid_pcb_cavity(front = false);
            pcb_main_cavity(front = true);
            pcb_main_cavity(front = false);
            pzt_solder_reliefs(front = true);
            pzt_solder_reliefs(front = false);
        }
        m6_full_planform_prism();
    }
}

// M6 最终装配是 Z=0 分型的正/反两个大件，不再在第 2/3 层间使用榫槽。
// 侧边阵列由第 2→1 / 3→4 层向外攻丝；三颗 M2 由第 1→4 层贯穿；拍面由第 2→3 层。
m6_tail_screw_y = max(actual_butt_y + 12.5, tail_if_pcb_y + 6.5);
m6_tail_screw_x = envelope_hx(m6_tail_screw_y) - m6_handle_boss_d / 2 - 0.5;
m6_tail_screw_positions = [
    [-m6_tail_screw_x, m6_tail_screw_y],
    [ m6_tail_screw_x, m6_tail_screw_y],
];

function m6_side_screw_x(y) =
    envelope_hx(y) - m6_handle_boss_d / 2 - 0.6;

function m6_move_screw_to_side(p) = [
    (p[0] < 0 ? -1 : 1) * m6_side_screw_x(p[1]),
    p[1]
];

// 旧 ±7/-160 贯穿位不再混入侧边短螺丝阵列；迁位后的三颗贯穿 M2
// 由 parameters.scad 的 m6_handle_through_screw_centers 单独管理。
function m6_existing_handle_screw_positions() = [];

function m6_extra_handle_screw_positions() =
    m6_tail_screw_positions;

function m6_all_handle_screw_positions() =
    USE_BEZIER_PROFILES
        ? BEZIER_M6_SCREW_POSITIONS
        : concat(m6_existing_handle_screw_positions(), m6_extra_handle_screw_positions());

function m6_handle_through_screw_positions() = [
    // 三点第 1→4 层贯穿闭环：尾部迁位后的左右两点 + PCB 尾部中轴点。
    for (p = m6_handle_through_screw_centers)
        if (screw_in_handle(p)) p
];

function m6_blade_screw_positions() = [
    for (p = screw_positions)
        if (screw_in_blade(p)) p
];

function m6_safe_screw_lengths() = [
    for (l = m6_handle_screw_lengths)
        if (
            l >= m6_core_half_t + m6_handle_engagement_min
            && l <= m6_core_half_t + m6_handle_engagement_max
        ) l
];

function m6_split_screw_length() =
    len(m6_safe_screw_lengths()) > 0
        ? min(m6_safe_screw_lengths())
        : max(2, floor(2 * m6_core_half_t - m6_handle_back_skin_min));

function m6_handle_back_engagement(p) =
    max(0.5, min(m6_handle_engagement_max,
        half_z_at(p[1]) - m6_core_half_t - m6_handle_back_skin_min));

function m6_handle_through_screw_length(p) =
    2 * half_z_at(p[1]) - plug_recess_depth - m6_handle_back_skin_min;

// 侧边阵列：从第 2/3 层贴合面分别向第 1/4 层安装短沉头螺丝。
module m6_core_outward_screw_channels(positions) {
    for (p = positions) {
        translate([p[0], p[1], m6_handle_screw_head_h - eps])
            cylinder(d = m6_handle_screw_clearance,
                h = m6_core_half_t - m6_handle_screw_head_h + 2 * eps);
        translate([p[0], p[1], -eps])
            cylinder(d1 = m6_handle_screw_head_d,
                d2 = m6_handle_screw_clearance,
                h = m6_handle_screw_head_h + eps);
    }
}

module m6_outer_skin_pilot_channels(positions) {
    engagement = m6_split_screw_length() - m6_core_half_t;
    for (p = positions)
        translate([p[0], p[1], m6_core_half_t - eps])
            cylinder(d = m6_handle_screw_pilot, h = engagement + 2 * eps);
}

module m6_side_front_screw_channels() {
    m6_core_outward_screw_channels(m6_all_handle_screw_positions());
    m6_outer_skin_pilot_channels(m6_all_handle_screw_positions());
}

module m6_side_back_screw_channels() {
    mirror([0, 0, 1]) m6_side_front_screw_channels();
}

// 拍柄合壳孔：第 1 层外表面沉头，1/2/3 层为过孔，第 4 层为盲底孔。
module m6_handle_through_screw_channels(positions = m6_handle_through_screw_positions()) {
    for (p = positions) {
        hz = half_z_at(p[1]);
        engagement = m6_handle_back_engagement(p);
        head_top = hz - plug_recess_depth;
        translate([p[0], p[1], -m6_core_half_t - eps])
            cylinder(
                d = screw_d_clearance,
                h = head_top - screw_head_h + m6_core_half_t + 2 * eps
            );
        translate([p[0], p[1], head_top - screw_head_h])
            cylinder(
                d1 = screw_d_clearance,
                d2 = screw_head_d,
                h = screw_head_h + eps
            );
        // 硅胶盖凹位位于沉头之上，盖面装好后与拍柄外表面齐平。
        translate([p[0], p[1], head_top])
            cylinder(d = plug_recess_d, h = plug_recess_depth + eps);
        translate([p[0], p[1], -m6_core_half_t - engagement])
            cylinder(d = screw_d_pilot, h = engagement + 2 * eps);
    }
}

// 拍面孔：第 2 层正面沉头并贯穿，第 3 层保留 0.8mm 背皮作盲底孔。
module m6_blade_front_screw_channels(positions = m6_blade_screw_positions()) {
    for (p = positions) {
        translate([p[0], p[1], -eps])
            cylinder(d = screw_d_clearance,
                h = m6_core_half_t - screw_head_h + 2 * eps);
        translate([p[0], p[1], m6_core_half_t - screw_head_h])
            cylinder(d1 = screw_d_clearance,
                d2 = screw_head_d,
                h = screw_head_h + eps);
    }
}

module m6_blade_back_screw_channels(positions = m6_blade_screw_positions()) {
    engagement = screw_blade_length - m6_core_half_t;
    for (p = positions)
        translate([p[0], p[1], -engagement])
            cylinder(d = screw_d_pilot, h = engagement + eps);
}

module m6_handle_screw_boss_group(front, positions, boss_d) {
    for (p = positions) {
        x = p[0];
        y = p[1];
        hz = half_z_at(y);
        if (front) {
            intersection() {
                bezier_handle_half(true);
                translate([x, y, -eps])
                    cylinder(
                        d = boss_d,
                        h = hz - wall_t + 0.5 + eps
                    );
            }
        } else {
            intersection() {
                bezier_handle_half(false);
                translate([x, y, -hz + wall_t - 0.5])
                    cylinder(
                        d = boss_d,
                        h = hz - wall_t + 0.5 + eps
                    );
            }
        }
    }
}

module m6_handle_screw_bosses(front = true) {
    m6_handle_screw_boss_group(front, m6_all_handle_screw_positions(), m6_handle_boss_d);
}

// 三颗贯穿 M2 boss 属于第 1/4 层：像插柱一样穿过第 2/3 层，在 Z=0 分型面相接。
// 不再横向桥接侧壁，以免形成侵占 PCB 深入空间的“爪子”。
module m6_handle_through_boss_columns(front = true) {
    for (p = m6_handle_through_screw_positions()) {
        hz = half_z_at(p[1]);
        if (front)
            intersection() {
                bezier_handle_half(true);
                translate([p[0], p[1], -eps])
                    cylinder(d = screw_d_boss, h = hz - wall_t + 0.5 + eps);
            }
        else
            intersection() {
                bezier_handle_half(false);
                translate([p[0], p[1], -hz + wall_t - 0.5])
                    cylinder(d = screw_d_boss, h = hz - wall_t + 0.5 + eps);
            }
    }
}

module m6_handle_through_boss_clearance() {
    for (p = m6_handle_through_screw_positions())
        translate([p[0], p[1], -m6_core_half_t - eps])
            cylinder(d = screw_d_boss + 0.20,
                h = 2 * m6_core_half_t + 2 * eps);
}

module m6_core_screw_support_group(front, positions, boss_d) {
    for (p = positions) {
        x = p[0];
        y = p[1];
        side = x < 0 ? -1 : 1;
        anchor_x = side * (envelope_hx(y) - m6_handle_wall_t / 2);
        hull() {
            translate([x, y, front ? 0 : -m6_core_half_t])
                cylinder(d = boss_d, h = m6_core_half_t);
            translate([anchor_x, y, front ? 0 : -m6_core_half_t])
                cylinder(d = boss_d, h = m6_core_half_t);
        }
    }
}

module m6_core_screw_supports(front = true) {
    intersection() {
        m6_core_blank(front);
        union() {
            // 侧边细螺丝与贯穿 M2 使用各自柱径，并桥接到最近侧壁。
            m6_core_screw_support_group(front, m6_all_handle_screw_positions(), m6_handle_boss_d);
        }
    }
}

// 大镂空区中的 PCB 穿透 M2 位必须在第 2/3 层补回完整承力柱。
// 腔体先被 difference 切除，因此该柱必须与侧边承力柱一样在切腔后
// 重新 union；最后再由对应的过孔/盲底孔通道钻孔。
module m6_blade_pcb_screw_supports(front = true) {
    intersection() {
        m6_core_blank(front);
        union()
            for (p = pcb_through_screw_positions)
                if (screw_in_blade(p))
                    translate([p[0], p[1], front ? 0 : -m6_core_half_t])
                        cylinder(d = screw_d_boss, h = m6_core_half_t);
    }
}

module m6_core_blank(front = true) {
    translate([0, 0, front ? 0 : -m6_core_half_t])
        linear_extrude(height = m6_core_half_t)
            m6_full_planform_2d();
}

module m6_core_front() {
    difference() {
        union() {
            difference() {
                m6_core_blank(true);
                handle_cavity();
                piezo_pockets(front = true);
                wire_channels(front = true);
                signal_bus_to_handle(front = true);
                rigid_pcb_cavity(front = true);
                pcb_main_cavity(front = true);
                pzt_solder_reliefs(front = true);
            }
            // 内腔挖空后补回第 2 层螺丝承力柱，否则螺丝会悬空。
            m6_core_screw_supports(true);
            m6_blade_pcb_screw_supports(true);
        }
        m6_side_front_screw_channels();
        m6_handle_through_boss_clearance();
        m6_handle_through_screw_channels();
        m6_blade_front_screw_channels();
    }
}

module m6_core_back() {
    difference() {
        union() {
            difference() {
                m6_core_blank(false);
                handle_cavity();
                piezo_pockets(front = false);
                wire_channels(front = false);
                signal_bus_to_handle(front = false);
                rigid_pcb_cavity(front = false);
                pcb_main_cavity(front = false);
                pzt_solder_reliefs(front = false);
            }
            // 第 3 层镜像承力柱，供螺丝穿过后向第 4 层攻丝。
            m6_core_screw_supports(false);
            m6_blade_pcb_screw_supports(false);
        }
        m6_side_back_screw_channels();
        m6_handle_through_boss_clearance();
        m6_handle_through_screw_channels();
        m6_blade_back_screw_channels();
    }
}

module m6_handle_skin_front(overlap = 0) {
    difference() {
        union() {
            intersection() {
                handle_front_part();
                m6_full_planform_prism();
                translate([-BIG, -BIG, m6_core_half_t - overlap])
                    cube([BIG * 2, BIG * 2, BIG]);
            }
            intersection() {
                m6_handle_screw_bosses(true);
                translate([-BIG, -BIG, m6_core_half_t - overlap])
                    cube([BIG * 2, BIG * 2, BIG]);
            }
            m6_handle_through_boss_columns(true);
        }
        m6_side_front_screw_channels();
        m6_handle_through_screw_channels();
    }
}

module m6_handle_skin_back(overlap = 0) {
    difference() {
        union() {
            intersection() {
                handle_back_part();
                m6_full_planform_prism();
                translate([-BIG, -BIG, -BIG])
                    cube([BIG * 2, BIG * 2, BIG - m6_core_half_t + overlap]);
            }
            intersection() {
                m6_handle_screw_bosses(false);
                translate([-BIG, -BIG, -BIG])
                    cube([BIG * 2, BIG * 2, BIG - m6_core_half_t + overlap]);
            }
            m6_handle_through_boss_columns(false);
        }
        m6_side_back_screw_channels();
        m6_handle_through_screw_channels();
    }
}

module m6_monolithic_front() {
    difference() {
        union() {
            m6_core_front();
            m6_handle_skin_front(m6_union_overlap);
            m6_handle_screw_bosses(true);
        }
        m6_side_front_screw_channels();
        m6_handle_through_screw_channels();
        m6_blade_front_screw_channels();
    }
}

module m6_monolithic_back() {
    difference() {
        union() {
            m6_core_back();
            m6_handle_skin_back(m6_union_overlap);
            m6_handle_screw_bosses(false);
        }
        m6_side_back_screw_channels();
        m6_handle_through_screw_channels();
        m6_blade_back_screw_channels();
    }
}

module m6_front_fasteners() {
    screw_l = m6_split_screw_length();
    shank_h = screw_l - m6_handle_screw_head_h;
    for (p = m6_all_handle_screw_positions()) {
        color([0.72, 0.75, 0.78])
        union() {
            translate([p[0], p[1], m6_handle_screw_head_h - eps])
                cylinder(d = m6_handle_screw_d, h = shank_h + eps);
            translate([p[0], p[1], 0])
                cylinder(
                    d1 = m6_handle_screw_head_d,
                    d2 = m6_handle_screw_d,
                    h = m6_handle_screw_head_h
                );
        }
    }
}

module m6_back_fasteners() {
    mirror([0, 0, 1]) m6_front_fasteners();
}

module m6_through_fasteners() {
    for (p = m6_handle_through_screw_positions()) {
        hz = half_z_at(p[1]);
        screw_l = m6_handle_through_screw_length(p);
        shank_h = screw_l - screw_head_h;
        head_top = hz - plug_recess_depth;
        color([0.78, 0.81, 0.84]) union() {
            translate([p[0], p[1], head_top - screw_l])
                cylinder(d = screw_d_nominal, h = shank_h + eps);
            translate([p[0], p[1], head_top - screw_head_h])
                cylinder(d1 = screw_d_nominal,
                    d2 = screw_head_d,
                    h = screw_head_h);
        }
    }
}

module m6_silicone_plugs() {
    for (p = m6_handle_through_screw_positions()) {
        hz = half_z_at(p[1]);
        color([0.08, 0.10, 0.12])
            translate([p[0], p[1], hz - plug_recess_depth])
                cylinder(d = plug_recess_d - 0.15, h = plug_recess_depth);
    }
}

module m6_blade_fasteners() {
    screw_l = screw_blade_length;
    shank_h = screw_l - screw_head_h;
    for (p = m6_blade_screw_positions()) {
        color([0.72, 0.75, 0.78])
        union() {
            translate([p[0], p[1], m6_core_half_t - screw_l])
                cylinder(d = screw_d_nominal, h = shank_h + eps);
            translate([p[0], p[1], m6_core_half_t - screw_head_h])
                cylinder(d1 = screw_d_nominal,
                    d2 = screw_head_d,
                    h = screw_head_h);
        }
    }
}

module m6_fasteners() {
    m6_front_fasteners();
    m6_back_fasteners();
    m6_through_fasteners();
    m6_blade_fasteners();
}

module m6_assembly() {
    color([0.12, 0.45, 0.90, 0.80]) m6_handle_skin_front();
    color([0.85, 0.20, 0.18]) m6_core_front();
    color([0.45, 0.08, 0.06]) m6_core_back();
    color([0.08, 0.25, 0.55, 0.80]) m6_handle_skin_back();
}

module m6_exploded() {
    translate([0, 0, 12]) m6_handle_skin_front();
    translate([0, 0, 4]) m6_core_front();
    translate([0, 0, -4]) m6_core_back();
    translate([0, 0, -12]) m6_handle_skin_back();
}

// Non-manufacturing inspection scenes used by docs/mechanical-handoff.
module protected_battery_preview() {
    color([0.15, 0.65, 0.28])
        translate(protected_14500_center)
            rotate([90, 0, 0])
                cylinder(d = protected_14500_max_d, h = protected_14500_max_l, center = true);
    // The user's circular protection PCB is contained within the same diameter
    // and within the 52 mm total envelope; mark the final 2 mm only for visual
    // orientation, not as an additional length.
    color([0.12, 0.35, 0.16])
        translate([0, protected_14500_center[1] - protected_14500_max_l / 2 + 1, 0])
            rotate([90, 0, 0])
                cylinder(d = protected_14500_max_d, h = 2, center = true);
}

module harness_preview() {
    colors = [
        [0.90, 0.10, 0.08], [0.05, 0.05, 0.05],
        [0.95, 0.70, 0.05], [0.95, 0.35, 0.05],
        [0.92, 0.92, 0.92], [0.10, 0.65, 0.20],
        [0.12, 0.35, 0.90], [0.55, 0.20, 0.80],
    ];
    wire_len = handle_wire_corridor_y1 - handle_wire_corridor_y0;
    for (branch = [0, 1], ix = [-1, 1], iz = [-1, 1]) {
        index = branch * 4 + (ix > 0 ? 2 : 0) + (iz > 0 ? 1 : 0);
        sx = branch == 0 ? -1 : 1;
        color(colors[index])
            translate([
                sx * handle_wire_corridor_center_x + ix * handle_wire_od / 2,
                (handle_wire_corridor_y0 + handle_wire_corridor_y1) / 2,
                iz * handle_wire_od / 2,
            ])
                rotate([90, 0, 0])
                    cylinder(d = handle_wire_od, h = wire_len, center = true, $fn = 24);
    }
}

module mechanical_fit_preview() {
    // Handle-only cutaway: keep the real back-side shell, remove the front
    // half, and place the battery/wires at their contractual coordinates.
    // Opaque geometry renders consistently in both OpenCSG and Manifold and
    // makes the deliberately tight two-corridor fit readable in screenshots.
    color([0.68, 0.75, 0.84])
        intersection() {
            union() {
                m6_core_back();
                m6_handle_skin_back();
            }
            translate([-30, -172, -20]) cube([60, 78, 20]);
        }
    // Only the two tail M2 fasteners fall inside this crop.  Showing them in
    // metal makes the layer-1→4 closure visible without adding fake geometry.
    intersection() {
        m6_through_fasteners();
        translate([-30, -172, -20]) cube([60, 78, 40]);
    }
    protected_battery_preview();
    harness_preview();
}

module mechanical_pzt_relief_preview() {
    // OpenSCAD diagnostic overlay on the shell's rigid-PCB cavity profile.
    // Copper is clipped by that profile so the intended half-hole form is not
    // hidden by a complete gold annulus.  The documentation PNG is generated
    // separately from live KiCad Edge.Cuts and is the authoritative 2D view.
    color([0.10, 0.42, 0.25])
        difference() {
            linear_extrude(height = 0.8, center = true)
                rigid_pcb_profile_2d();
            for (p = pzt_solder_pad_centers_scad)
                translate([p[0], p[1], -1])
                    cylinder(d = pzt_wire_pad_drill, h = 2, $fn = 36);
        }
    for (p = pzt_solder_pad_centers_scad) {
        color([1.0, 0.42, 0.02])
            translate([p[0], p[1], 0.42])
                difference() {
                    cylinder(d = pzt_solder_relief_d, h = 0.12, $fn = 48);
                    translate([0, 0, -0.02])
                        cylinder(d = pzt_wire_pad_d, h = 0.16, $fn = 48);
                }
        color([0.94, 0.70, 0.12])
            intersection() {
                translate([p[0], p[1], 0.42])
                    difference() {
                        cylinder(d = pzt_wire_pad_d, h = 0.16, $fn = 48);
                        translate([0, 0, -0.02])
                            cylinder(d = pzt_wire_pad_drill, h = 0.20, $fn = 36);
                    }
                translate([0, 0, 0.40])
                    linear_extrude(height = 0.20)
                        rigid_pcb_profile_2d();
            }
    }
}

// ═══ 渲染 ═══

assert(
    len(m6_handle_through_screw_positions()) == 3,
    "M6/M7 handle closure requires exactly three layer-1→4 M2 fasteners"
);

if (HALF == "m6_core_front") {
    m6_core_front();
} else if (HALF == "m6_core_back") {
    m6_core_back();
} else if (HALF == "m6_skin_front") {
    m6_handle_skin_front();
} else if (HALF == "m6_skin_back") {
    m6_handle_skin_back();
} else if (HALF == "m6_monolithic_front") {
    m6_monolithic_front();
} else if (HALF == "m6_monolithic_back") {
    m6_monolithic_back();
} else if (HALF == "m6_handle_back_tip") {
    intersection() {
        m6_monolithic_back();
        translate([-BIG, handle_butt_cut_y, -BIG])
            cube([BIG*2, TIP_LENGTH, BIG*2]);
    }
} else if (HALF == "m6_assembly") {
    m6_assembly();
} else if (HALF == "m6_exploded") {
    m6_exploded();
} else if (HALF == "m6_fasteners") {
    m6_fasteners();
} else if (HALF == "m6_fasteners_front") {
    m6_front_fasteners();
} else if (HALF == "m6_fasteners_back") {
    m6_back_fasteners();
} else if (HALF == "m6_fasteners_through") {
    m6_through_fasteners();
} else if (HALF == "m6_fasteners_blade") {
    m6_blade_fasteners();
} else if (HALF == "m6_silicone_plugs") {
    m6_silicone_plugs();
} else if (HALF == "m6_stage_planform") {
    m6_stage_planform();
} else if (HALF == "m6_stage_handle_envelope") {
    m6_stage_handle_envelope();
} else if (HALF == "m6_stage_continuous_blank") {
    m6_stage_continuous_blank();
} else if (HALF == "m6_stage_voids") {
    m6_stage_voids();
} else if (HALF == "mechanical_fit_preview") {
    mechanical_fit_preview();
} else if (HALF == "mechanical_pzt_relief_preview") {
    mechanical_pzt_relief_preview();
} else {
    echo(str("Unknown M6 HALF: ", HALF));
}

echo(str("=== SmartPaddle Shell ==="));
echo(str("Profile: ", USE_IMPORTED_OUTER ? "Live outer STL (Three.js)" :
    USE_BEZIER_PROFILES ? "bezier SCAD loft" : "legacy ellipse"));
echo(str("Loft slices: ", LOFT_SLICES));
echo(str("Total height: ", blade_tip_y - handle_butt_cut_y, "mm"));
echo(str("Blade: ", blade_width, "mm wide × ", blade_core_t, "mm thick"));
echo(str("Handle: ", handle_thickness, "mm thick, butt Y=", handle_butt_y));
echo(str("Half: ", HALF));
echo(str(
    "M6 available screw wall: ", m6_fastener_available_wall,
    "mm → M", m6_handle_screw_d,
    "×", m6_split_screw_length(),
    " countersunk self-tapping stainless"
));
echo(str(
    "M6 fastening: side 2→1 / 3→4; three M2 points 1→4; blade 2→3"
));
for (l = [5, 6, 7])
    echo(str(
        "M", m6_handle_screw_d, "×", l, ": ",
        l < m6_core_half_t + m6_handle_engagement_min ? "engagement too short" :
        l > m6_core_half_t + m6_handle_engagement_max
            ? str("outer engagement too deep: ", l - m6_core_half_t, "mm")
            : "safe"
    ));

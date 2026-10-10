// 打印用 Y 三通。单位 mm。FDM / PETG。
// 原点在风机承口止挡中心。+Z 出球。进球支管在 +X，向外朝风机侧，与参考件同为 135°。
// 这个角度还没按实物重测。
// 进球段外径 50，从端口起内径就是 42，插入送料模块出口。
// 风机承口内径 50。球走的弯和出球段内径都是 42。50 收到 42 的台阶只在风机口里，球不经过。
// 弯道中心线半径 100，转 45°，弧长大于球径。局部断面保持内径 42。
// 球在弯里同时只转二十多度，进直管时方向已经摆正，不会一头进直管、球身还在斜段里撞壁。
// 外壳：风机承口外径 56 用一段曲率收到出球管外径 47。支管保持外径 50，不再把交汇处撑粗。
// 打印时出球口贴热床。稳定圈和管壁之间留缝，只在贴床一侧用八处两层窄连接，打完掰掉。球路内径不变。

// ===== 分区：导入/依赖 =====

include <parameters.scad>

// ===== 分区：常量/配置 =====

yt_ball_id = 42;
yt_ball_od = barrel_od;
yt_fan_id = 50;
yt_fan_wall = 3;
yt_exit_wall = 2.5;
yt_fan_depth = y_stub_engagement;
yt_air_step = 3;
yt_rho = 100;
yt_z0 = 114;                 // 出球直段切点。和大半径弯一起抬高，球才不探进风机口
yt_turn = 45;
yt_branch_angle = 135;
yt_branch_l = 64;            // 末端至少 25 mm 是露出的圆柱，用来插入送料口
yt_exit_l = 106;             // 切点上移后缩短直段，出球口高度不变
yt_mouth_chamfer = 0.6;
yt_arc_steps = 12;
yt_shoulder_len = 22;        // 风机承口外径收到出球管，两端斜率归零
yt_bed_ring_width = 18;      // 出球口贴床面，向外加宽的稳定圈
yt_bed_ring_t = 2.4;         // 多层圈，不是单层裙边
yt_bed_ring_proud = 0.4;     // 略高出出球端面，避免和端面共面碎成非流形
yt_bed_ring_gap = 1.6;       // 圈和管壁之间的缝，方便下手拆
yt_bed_ring_tab_n = 8;       // 两层很薄，多留几处才撑得住整件
yt_bed_ring_tab_w = 6;       // 每处连接的周向宽度
yt_bed_ring_tab_t = 0.4;     // 缝里只留两层 0.2 mm，打完能掰掉
yt_bed_ring_tab_bite = 0.45; // 搭进管壁和圈体，避免只相切
yt_bed_ring_chamfer = 0.8;   // 背向热床的外缘倒角
yt_fn = 64;
yt_eps = 0.08;
yt_used_part = is_undef(yt_part) ? "tee" : yt_part;

// ===== 分区：模型/类型 =====

yt_fan_od = yt_fan_id + 2 * yt_fan_wall;
yt_exit_od = yt_ball_id + 2 * yt_exit_wall;
yt_fan_z0 = -yt_fan_depth;
yt_outward = [sin(yt_branch_angle), 0, cos(yt_branch_angle)];

function yt_on_arc(a) = [
    yt_rho * (1 - cos(a)),
    0,
    yt_z0 + yt_rho * sin(a)
];
function yt_arc_points() = [
    for (i = [0:yt_arc_steps]) yt_on_arc(-yt_turn + yt_turn * i / yt_arc_steps)
];
function yt_branch_mouth() = yt_on_arc(-yt_turn) + yt_branch_l * yt_outward;
function yt_clamp(t) = max(0, min(1, t));
function yt_smooth(t) = let(u = yt_clamp(t)) u * u * u * (10 + u * (-15 + 6 * u));
function yt_outer_r(z) = z <= 0 ? yt_fan_od / 2
    : z >= yt_shoulder_len ? yt_exit_od / 2
    : yt_fan_od / 2 + (yt_exit_od / 2 - yt_fan_od / 2) * yt_smooth(z / yt_shoulder_len);
function yt_main_profile() = concat(
    [[0, yt_fan_z0]],
    [[yt_outer_r(yt_fan_z0), yt_fan_z0]],
    [for (i = [1:96]) let(z = yt_fan_z0 + (yt_z0 + yt_exit_l - yt_fan_z0) * i / 96)
        [yt_outer_r(z), z]],
    [[0, yt_z0 + yt_exit_l]]
);

// ===== 分区：私有成员 =====

module yt_pipe(points, radius) {
    for (i = [0:len(points) - 2])
        hull() {
            translate(points[i]) sphere(r=radius, $fn=yt_fn);
            translate(points[i + 1]) sphere(r=radius, $fn=yt_fn);
        }
}

module yt_taper_pipe(points, r0, r1) {
    n = len(points) - 1;
    for (i = [0:n - 1])
        hull() {
            translate(points[i])
                sphere(r=r0 + (r1 - r0) * yt_smooth(i / n), $fn=yt_fn);
            translate(points[i + 1])
                sphere(r=r0 + (r1 - r0) * yt_smooth((i + 1) / n), $fn=yt_fn);
        }
}

module yt_half_space() {
    translate([-180, 0, yt_fan_z0 - 40])
        cube([360, 180, yt_z0 + yt_exit_l - yt_fan_z0 + 80]);
}

module yt_branch_place() {
    translate(yt_on_arc(-yt_turn))
        rotate([0, yt_branch_angle, 0])
            children();
}

// ===== 分区：公开 API =====

module yt_main_shell() {
    rotate_extrude(convexity=4, $fn=yt_fn)
        polygon(yt_main_profile());
}

module yt_bed_ring_tab() {
    r_wall = yt_exit_od / 2;
    r0 = r_wall - yt_bed_ring_tab_bite;
    ri = r_wall + yt_bed_ring_gap;
    r1 = ri + yt_bed_ring_tab_bite;
    half = yt_bed_ring_tab_w / 2;
    over = 0.15;
    root = 0.3;
    span = root + yt_bed_ring_tab_t + over;
    difference() {
        intersection() {
            difference() {
                translate([0, 0, -root])
                    cylinder(h=span, r=r1, $fn=yt_fn);
                translate([0, 0, -root - yt_eps])
                    cylinder(h=span + 2 * yt_eps, r=r0, $fn=yt_fn);
            }
            translate([0, 0, -root - yt_eps])
                linear_extrude(span + 2 * yt_eps)
                    polygon([[0, -0.2], [r1 + 1, -half], [r1 + 1, half], [0, 0.2]]);
        }
        translate([0, 0, -root - yt_eps])
            difference() {
                cylinder(h=root + yt_eps, r=ri - 0.05, $fn=yt_fn);
                translate([0, 0, -yt_eps])
                    cylinder(h=root + 3 * yt_eps, r=r_wall + 0.05, $fn=yt_fn);
            }
        translate([0, 0, yt_bed_ring_tab_t])
            difference() {
                cylinder(h=over + yt_eps, r=ri - 0.05, $fn=yt_fn);
                translate([0, 0, -yt_eps])
                    cylinder(h=over + 3 * yt_eps, r=r_wall + 0.05, $fn=yt_fn);
            }
        translate([0, 0, yt_bed_ring_tab_t])
            cylinder(h=over + yt_eps, r=r_wall - 0.05, $fn=yt_fn);
    }
}

module yt_bed_ring() {
    z1 = yt_z0 + yt_exit_l;
    ro = yt_exit_od / 2 + yt_bed_ring_width;
    ri = yt_exit_od / 2 + yt_bed_ring_gap;
    face = yt_bed_ring_t + yt_bed_ring_proud;
    translate([0, 0, z1 - yt_bed_ring_t])
        rotate_extrude(convexity=2, $fn=yt_fn)
            polygon([
                [ri, 0],
                [ro - yt_bed_ring_chamfer, 0],
                [ro, yt_bed_ring_chamfer],
                [ro, face],
                [ri, face]
            ]);
    translate([0, 0, z1 + yt_bed_ring_proud - yt_bed_ring_tab_t])
        for (i = [0:yt_bed_ring_tab_n - 1])
            rotate([0, 0, i * 360 / yt_bed_ring_tab_n])
                yt_bed_ring_tab();
}

module yt_outer() {
    yt_main_shell();
    yt_taper_pipe(yt_arc_points(), yt_ball_od / 2, yt_exit_od / 2);
    yt_branch_place()
        cylinder(h=yt_branch_l, d=yt_ball_od, $fn=yt_fn);
    yt_bed_ring();
}

module yt_bore() {
    translate([0, 0, yt_fan_z0 - yt_eps])
        cylinder(h=yt_fan_depth + yt_eps, d=yt_fan_id, $fn=yt_fn);
    translate([0, 0, -yt_eps])
        cylinder(h=yt_air_step + 2 * yt_eps, d1=yt_fan_id, d2=yt_ball_id, $fn=yt_fn);
    translate([0, 0, yt_air_step - yt_eps])
        cylinder(h=yt_z0 - yt_air_step + yt_eps, d=yt_ball_id, $fn=yt_fn);
    yt_pipe(concat(yt_arc_points(), [[0, 0, yt_z0 + yt_exit_l]]), yt_ball_id / 2);
    yt_branch_place()
        translate([0, 0, -yt_eps])
            cylinder(h=yt_branch_l + 1, d=yt_ball_id, $fn=yt_fn);
    yt_branch_place()
        translate([0, 0, yt_branch_l - yt_mouth_chamfer])
            cylinder(h=yt_mouth_chamfer + 1,
                d1=yt_ball_id, d2=yt_ball_id + 2 * yt_mouth_chamfer, $fn=yt_fn);
}

module yt_tee() {
    difference() {
        yt_outer();
        yt_bore();
    }
}

// ===== 分区：视图层 =====

module yt_section() {
    difference() {
        yt_tee();
        yt_half_space();
    }
}

// ===== 分区：业务逻辑 =====

assert(yt_ball_od == 50, "进球段外径应为 50");
assert(yt_ball_id == 42, "球道路径内径应为 42");
assert(yt_fan_id == 50, "风机口内径应为 50");
assert(yt_ball_id > ball_max_d, "42 mm 轨道必须大于球径包络");
assert(yt_rho > yt_ball_id / 2, "弯道半径必须大于气道半径，断面才不会自交");
assert(yt_rho * yt_turn * PI / 180 > ball_max_d * 1.5,
    "弯道弧长至少要有球径的 1.5 倍，球才不会横跨整个拐弯");
assert(ball_max_d / yt_rho * 180 / PI < 30, "球在弯道里同时转过的角度应小于 30 度");
assert(yt_on_arc(-yt_turn).z - ball_max_d / 2 > yt_air_step,
    "球在弯道入口应完全离开风机收口");
assert(yt_branch_mouth().z - (yt_ball_od / 2) * sin(yt_turn) >= yt_fan_z0,
    "进球口不能低于风机端面，否则整件超高");
assert(yt_branch_l > y_stub_engagement, "进球直段要留出插入长度");
assert(yt_exit_wall >= 2, "出球段壁厚至少 2 mm");
assert(yt_exit_od / 2 - yt_bed_ring_tab_bite - yt_ball_id / 2 >= 1.5,
    "稳定圈连接搭进管壁后，出球段剩余壁厚至少 1.5 mm");
assert(yt_bed_ring_tab_n == 8, "稳定圈留八处连接");
assert(yt_bed_ring_tab_n * yt_bed_ring_tab_w < PI * yt_exit_od * 0.5,
    "连接加起来不能把缝封上");
assert(yt_bed_ring_tab_w <= 8, "每处连接不要太宽");
assert(yt_bed_ring_tab_t == 0.4, "缝里的连接只留两层");
assert(yt_bed_ring_gap >= 1.2, "稳定圈和管壁之间要留得下刀");
assert(yt_bed_ring_t > yt_bed_ring_tab_t + 0.8, "连接上方要留出敞开的缝");
assert(yt_bed_ring_width >= 12, "稳定圈径向宽度至少 12 mm");
assert(yt_branch_mouth().x > yt_exit_od / 2 + yt_ball_od / 2 + 2,
    "进球端口要伸出出球管，才插得进送料口");
assert(yt_branch_l - (yt_exit_od / 2 + yt_ball_od / 2 - yt_on_arc(-yt_turn).x) / sin(yt_branch_angle)
    >= y_stub_engagement, "露出的圆柱插入段至少要有 25 mm");
for (t = [0:5:yt_branch_l]) {
    p = yt_on_arc(-yt_turn) + t * yt_outward;
    if (p.z - ball_max_d / 2 < yt_air_step)
        assert(p.x > yt_fan_id / 2 + ball_max_d / 2 + 1,
            "球在进球段上不能跨进风机口");
}
echo(yt_fan_od=yt_fan_od);
echo(yt_exit_od=yt_exit_od);
echo(yt_branch_join=yt_on_arc(-yt_turn));
echo(yt_arc_len=yt_rho * yt_turn * PI / 180);
echo(yt_muzzle_z=yt_z0 + yt_exit_l);

// ===== 分区：方法/工具 =====

if (yt_used_part == "tee") {
    yt_tee();
} else if (yt_used_part == "section") {
    yt_section();
} else {
    assert(false, "未知零件选择");
}

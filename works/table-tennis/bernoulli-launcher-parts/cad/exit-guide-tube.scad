// 出球引导管。单位 mm。FDM / PETG / 0.4 mm 喷嘴。
// 原点在轴线上。z=0 是插入三通后顶到内肩的端面，+Z 为球的前进方向，也是打印朝上方向。
// 不再套外径 50 的硬管，也不再装旋转头。直管壁厚 1.5。插入段外径就是 50，
// 安装余量在 Y 形三通承口上。入口内径因此是 47；球从这里用短锥走进 42，之后内径保持 42 直到出口。
// 端面有 0.3 的导入倒角，配合外径仍是 50。三通止挡深度还没量过。

// ===== 分区：导入/依赖 =====

include <parameters.scad>

// ===== 分区：常量/配置 =====

xb_wall = 1.5;
xb_throat_id = 42;
xb_spigot_length = y_stub_engagement;
xb_taper_length = 12;
xb_free_length = 150;
xb_entry_chamfer = 0.3;
xb_spigot_chamfer = 0.3;
xb_tip_chamfer = 0.4;
xb_fn = 96;
// 命令行 -D 'xb_part="section"' 可覆盖；文件内不要再赋值。
xb_used_part = is_undef(xb_part) ? "tube" : xb_part;

// ===== 分区：模型/类型 =====

xb_spigot_od = barrel_od;
xb_entry_id = xb_spigot_od - 2 * xb_wall;
xb_throat_od = xb_throat_id + 2 * xb_wall;
xb_z_mouth = xb_entry_chamfer;
xb_z_taper = xb_z_mouth + xb_taper_length;
xb_z_tip = xb_spigot_length + xb_free_length;
xb_taper_radial = (xb_entry_id - xb_throat_id) / 2;
xb_taper_half_angle = atan(xb_taper_radial / xb_taper_length);

function xb_profile_points() = [
    [xb_entry_id / 2 + xb_entry_chamfer, 0],
    [xb_entry_id / 2, xb_z_mouth],
    [xb_throat_id / 2, xb_z_taper],
    [xb_throat_id / 2, xb_z_tip],
    [xb_throat_od / 2 - xb_tip_chamfer, xb_z_tip],
    [xb_throat_od / 2, xb_z_tip - xb_tip_chamfer],
    [xb_throat_od / 2, xb_spigot_length],
    [xb_spigot_od / 2, xb_spigot_length],
    [xb_spigot_od / 2, xb_spigot_chamfer],
    [xb_spigot_od / 2 - xb_spigot_chamfer, 0]
];

// ===== 分区：私有成员 =====

module xb_half_space() {
    translate([-xb_spigot_od, -xb_spigot_od, -20])
        cube([xb_spigot_od, xb_spigot_od * 2, xb_z_tip + 40]);
}

module xb_reference_socket() {
    translate([0, 0, -30])
        difference() {
            cylinder(h=xb_spigot_length + 30, d=barrel_od + 8, $fn=xb_fn);
            translate([0, 0, -0.2])
                cylinder(h=30.2, d=barrel_id, $fn=xb_fn);
            translate([0, 0, 29.8])
                cylinder(h=xb_spigot_length + 0.4, d=barrel_od, $fn=xb_fn);
        }
}

module xb_reference_ball() {
    translate([0, -(xb_entry_id - ball_min_d) / 2, -ball_min_d / 2])
        sphere(d=ball_min_d, $fn=xb_fn);
}

// ===== 分区：公开 API =====

module xb_tube() {
    rotate_extrude(convexity=8, $fn=xb_fn)
        polygon(xb_profile_points());
}

// ===== 分区：视图层 =====

module xb_section() {
    difference() {
        xb_tube();
        xb_half_space();
    }
}

module xb_assembly_section() {
    difference() {
        union() {
            color([0.85, 0.45, 0.12]) xb_tube();
            color([0.90, 0.68, 0.10, 0.35]) xb_reference_socket();
            color([0.92, 0.92, 0.90]) xb_reference_ball();
        }
        xb_half_space();
    }
}

// ===== 分区：业务逻辑 =====

assert(xb_wall == 1.5, "直管壁厚应按 1.5 mm 保持");
assert(xb_spigot_od == barrel_od, "插入段外径应与硬管外径同为 50");
assert(xb_entry_id > ball_max_d, "入口必须让球走得进去");
assert(xb_throat_id > ball_max_d, "42 mm 直管必须大于球径包络");
assert(abs(xb_throat_od - (xb_throat_id + 2 * xb_wall)) < 1e-6, "直管壁厚必须是 1.5 mm");
assert(xb_z_taper < xb_spigot_length, "收口应在离开三通之前完成");
assert(xb_taper_length < ball_min_d / 3, "收口应短于球径的三分之一");
assert(xb_free_length > ball_max_d, "42 mm 直管应长过一颗球");
assert(xb_taper_half_angle > 8 && xb_taper_half_angle < 20, "收口半角应能让球爬进去，又不能变成长锥");
echo(xb_spigot_od=xb_spigot_od);
echo(xb_entry_id=xb_entry_id);
echo(xb_throat_od=xb_throat_od);
echo(xb_taper_radial=xb_taper_radial);
echo(xb_taper_half_angle=xb_taper_half_angle);
echo(xb_z_taper=xb_z_taper);
echo(xb_z_tip=xb_z_tip);

// ===== 分区：方法/工具 =====

if (xb_used_part == "tube") {
    xb_tube();
} else if (xb_used_part == "section") {
    xb_section();
} else if (xb_used_part == "assembly") {
    xb_assembly_section();
} else {
    assert(false, "未知零件选择");
}

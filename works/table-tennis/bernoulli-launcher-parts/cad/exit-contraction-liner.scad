// 出球管内衬。单位 mm。FDM / PETG / 0.4 mm 喷嘴。
// 原点在轴线上，z=0 是法兰来球面，+Z 为球的前进方向，也是打印朝上方向。
// 法兰外径与出球管外径同为 50。1 mm 壁从管内壁进入，先走直段，再收到内径 42。
// 球从法兰进入，从 42 端离开。42 端之后应突然回到管内径 48，不应再接缓锥。
// 0.20 mm 单边间隙只为能塞进内径 48 的硬管；壁厚仍是 1.00 mm。配合尚未实物试装。

// ===== 分区：导入/依赖 =====

include <parameters.scad>


// ===== 分区：常量/配置 =====

ecl_flange_od = barrel_od;
ecl_flange_thickness = 2;
ecl_wall = 1;
ecl_radial_clearance = 0.20;
ecl_throat_id = 42;
ecl_pilot_length = 12;
ecl_taper_length = 8;
ecl_land_length = 20;
ecl_entry_chamfer = 0.8;
ecl_tip_chamfer = 0.3;
ecl_fn = 96;
// 命令行 -D 'ecl_part="section"' 可覆盖；文件内不要再赋值。
ecl_used_part = is_undef(ecl_part) ? "liner" : ecl_part;


// ===== 分区：模型/类型 =====

ecl_sleeve_od = barrel_id - 2 * ecl_radial_clearance;
ecl_entry_id = ecl_sleeve_od - 2 * ecl_wall;
ecl_throat_od = ecl_throat_id + 2 * ecl_wall;
ecl_z_sleeve = ecl_flange_thickness;
ecl_z_taper = ecl_z_sleeve + ecl_pilot_length;
ecl_z_land = ecl_z_taper + ecl_taper_length;
ecl_z_tip = ecl_z_land + ecl_land_length;
ecl_taper_radial = (ecl_entry_id - ecl_throat_id) / 2;
ecl_taper_half_angle = atan(ecl_taper_radial / ecl_taper_length);

function ecl_profile_points() = [
    [ecl_entry_id / 2 + ecl_entry_chamfer, 0],
    [ecl_entry_id / 2, ecl_entry_chamfer],
    [ecl_entry_id / 2, ecl_z_taper],
    [ecl_throat_id / 2, ecl_z_land],
    [ecl_throat_id / 2, ecl_z_tip],
    [ecl_throat_od / 2 - ecl_tip_chamfer, ecl_z_tip],
    [ecl_throat_od / 2, ecl_z_tip - ecl_tip_chamfer],
    [ecl_throat_od / 2, ecl_z_land],
    [ecl_sleeve_od / 2, ecl_z_taper],
    [ecl_sleeve_od / 2, ecl_z_sleeve],
    [ecl_flange_od / 2, ecl_z_sleeve],
    [ecl_flange_od / 2, 0]
];


// ===== 分区：私有成员 =====

module ecl_half_space() {
    translate([-ecl_flange_od, -ecl_flange_od, -1])
        cube([ecl_flange_od, ecl_flange_od * 2, ecl_z_tip + 40]);
}

module ecl_reference_tube() {
    translate([0, 0, ecl_z_sleeve])
        difference() {
            cylinder(h=ecl_z_tip + 24, d=barrel_od, $fn=ecl_fn);
            translate([0, 0, -0.2])
                cylinder(h=ecl_z_tip + 24.4, d=barrel_id, $fn=ecl_fn);
        }
}

module ecl_reference_ball() {
    translate([0, -(barrel_id - ball_min_d) / 2, -ball_min_d / 2 + 2])
        sphere(d=ball_min_d, $fn=ecl_fn);
}


// ===== 分区：公开 API =====

module ecl_liner() {
    rotate_extrude(convexity=8, $fn=ecl_fn)
        polygon(ecl_profile_points());
}


// ===== 分区：视图层 =====

module ecl_section() {
    difference() {
        ecl_liner();
        ecl_half_space();
    }
}

module ecl_assembly_section() {
    difference() {
        union() {
            color([0.85, 0.45, 0.12]) ecl_liner();
            color([0.62, 0.68, 0.72]) ecl_reference_tube();
            color([0.92, 0.92, 0.90]) ecl_reference_ball();
        }
        ecl_half_space();
    }
}


// ===== 分区：业务逻辑 =====

assert(ecl_flange_od == barrel_od, "法兰外径应与出球管外径一致");
assert(ecl_wall == 1, "筒壁应按 1 mm 保持");
assert(ecl_sleeve_od < barrel_id, "进入段外径必须小于出球管内径");
assert(ecl_throat_id > ball_max_d, "42 mm 收口必须大于球径包络");
assert(ecl_taper_length < ball_min_d / 4, "收口长度应短于球径的四分之一");
assert(ecl_taper_half_angle > 8 && ecl_taper_half_angle < 20, "收口半角应落在可爬坡、又不形成长锥的范围");
echo(ecl_entry_id=ecl_entry_id);
echo(ecl_sleeve_od=ecl_sleeve_od);
echo(ecl_throat_od=ecl_throat_od);
echo(ecl_taper_radial=ecl_taper_radial);
echo(ecl_taper_half_angle=ecl_taper_half_angle);
echo(ecl_z_tip=ecl_z_tip);


// ===== 分区：方法/工具 =====

if (ecl_used_part == "liner") {
    ecl_liner();
} else if (ecl_used_part == "section") {
    ecl_section();
} else if (ecl_used_part == "assembly") {
    ecl_assembly_section();
} else {
    assert(false, "未知零件选择");
}

// CH1 03C 花键轴 Z+ 侧小齿轮 + Y− 侧狗牙
//
// Mechanical contract
// process: FDM fit prototype; PLA/PETG first article, resin only for fit checks
// material: printed compound candidate; no metal load rating is assumed
// parting_plane: n/a (single annular compound part)
// opening_direction: n/a
// fastener: a nominal Ø3 mm round shaft passes through the Y-axis gear/dog bore
// seal: n/a
// print_orientation: lay the Y axis down only after slicer review; the thumbnail
//   keeps the real assembly direction visible instead of baking in a print pose
// units: mm
// axis: gear and dog are both coaxial with world Y; profile is in world XZ
// placement: gear center is on the Z+ side of the long spline shaft
//
// This file models the literal arrangement: a small gear at Z+ and a rounded-
// triangle dog interface protruding directly below it along Y−.

//#region 导入/依赖
include <parts/ch1_03c_spline_gear_dog_params.scad>
//#endregion

//#region 常量/配置
$fa = 5;
$fs = 0.18;
//#endregion

//#region 模型/类型
// solid     printable gear + lower rounded-triangle dog interface
// thumbnail same part plus the matching lower receiver and a short translucent
// spline-shaft context at Z=0
//#endregion

//#region 私有成员：轮廓与轴向拉伸
module spline_profile_2d(teeth, root_r, tip_r) {
    polygon(spline_gear_points(teeth, root_r, tip_r));
}

module y_profile_extrude(points, center_x, center_y, center_z, thickness) {
    // Local +Z maps to world −Y; the translated interval is centered at center_y.
    translate([center_x, center_y + thickness / 2, center_z])
        rotate([90, 0, 0])
            linear_extrude(
                height = thickness,
                convexity = 8
            )
                polygon(points);
}

module y_bore(center_x, center_y, center_z, diameter, thickness) {
    // Local +Z maps to world +Y, starting just below the lower face.
    translate([
        center_x,
        center_y - thickness / 2 - SPLINE_GEAR_EPS,
        center_z
    ])
        rotate([-90, 0, 0])
            cylinder(
                d = diameter,
                h = thickness + 2 * SPLINE_GEAR_EPS,
                $fn = 48
            );
}

module y_cylinder_at(center_x, center_z, center_y, radius, height, sides = 32) {
    // A Y-axis cylinder whose center is at center_y; its +Z local direction
    // points toward world Y− so the interface grows downward from the base.
    translate([center_x, center_y + height / 2, center_z])
        rotate([90, 0, 0])
            cylinder(r = radius, h = height, $fn = sides);
}

module rounded_triangle_prism(center_y, height, extra_radius = 0) {
    // Convex hull of three round-ended lobes: a printable rounded triangle.
    hull() {
        for (i = [0:2]) {
            angle = SPLINE_DOG_TRI_ROTATION_DEG + i * 120;
            y_cylinder_at(
                SPLINE_GEAR_CENTER_X
                    + SPLINE_DOG_TRI_VERTEX_R * cos(angle),
                SPLINE_GEAR_CENTER_Z
                    + SPLINE_DOG_TRI_VERTEX_R * sin(angle),
                center_y,
                SPLINE_DOG_TRI_HEAD_R + extra_radius,
                height
            );
        }
    }
}

module rounded_claw_volume(
    index,
    center_y,
    height,
    extra_radius = 0
) {
    // Backup three-claw interface kept available through SPLINE_DOG_INTERFACE.
    angle = index * 360 / SPLINE_DOG_CLAW_COUNT;
    hull() {
        y_cylinder_at(
            SPLINE_GEAR_CENTER_X
                + SPLINE_DOG_CLAW_ROOT_CENTER_R * cos(angle),
            SPLINE_GEAR_CENTER_Z
                + SPLINE_DOG_CLAW_ROOT_CENTER_R * sin(angle),
            center_y,
            SPLINE_DOG_CLAW_HEAD_R + extra_radius,
            height
        );
        y_cylinder_at(
            SPLINE_GEAR_CENTER_X
                + SPLINE_DOG_CLAW_TIP_CENTER_R * cos(angle),
            SPLINE_GEAR_CENTER_Z
                + SPLINE_DOG_CLAW_TIP_CENTER_R * sin(angle),
            center_y,
            SPLINE_DOG_CLAW_HEAD_R + extra_radius,
            height
        );
    }
}

module dog_interface_volume(center_y, height, extra_radius = 0) {
    if (SPLINE_DOG_INTERFACE == "rounded_triangle") {
        rounded_triangle_prism(center_y, height, extra_radius);
    } else {
        for (i = [0:SPLINE_DOG_CLAW_COUNT - 1]) {
            rounded_claw_volume(i, center_y, height, extra_radius);
        }
    }
}
//#endregion

//#region 公开 API：打印件
module spline_side_gear() {
    gear_root_r = spline_gear_root_r(
        SPLINE_GEAR_TEETH,
        SPLINE_GEAR_PITCH_MM,
        SPLINE_GEAR_TOOTH_DEPTH
    );
    gear_tip_r = spline_gear_tip_r(
        SPLINE_GEAR_TEETH,
        SPLINE_GEAR_PITCH_MM,
        SPLINE_GEAR_TOOTH_DEPTH
    );
    difference() {
        y_profile_extrude(
            spline_gear_points(
                SPLINE_GEAR_TEETH,
                gear_root_r,
                gear_tip_r
            ),
            SPLINE_GEAR_CENTER_X,
            SPLINE_GEAR_CENTER_Y,
            SPLINE_GEAR_CENTER_Z,
            SPLINE_GEAR_T
        );
        y_bore(
            SPLINE_GEAR_CENTER_X,
            SPLINE_GEAR_CENTER_Y,
            SPLINE_GEAR_CENTER_Z,
            SPLINE_GEAR_BORE_D,
            SPLINE_GEAR_T
        );
    }
}

module dog_base_ring() {
    difference() {
        translate([
            SPLINE_GEAR_CENTER_X,
            SPLINE_DOG_BASE_CENTER_Y + SPLINE_DOG_BASE_T / 2,
            SPLINE_GEAR_CENTER_Z,
        ])
            rotate([90, 0, 0])
                cylinder(
                    r = SPLINE_DOG_BASE_R,
                    h = SPLINE_DOG_BASE_T,
                    $fn = 64
                );
        y_bore(
            SPLINE_GEAR_CENTER_X,
            SPLINE_DOG_BASE_CENTER_Y,
            SPLINE_GEAR_CENTER_Z,
            SPLINE_DOG_BORE_D,
            SPLINE_DOG_BASE_T
        );
    }
}

module lower_dog_ring() {
    union() {
        dog_base_ring();
        dog_interface_volume(
            SPLINE_DOG_INTERFACE_CENTER_Y,
            SPLINE_DOG_INTERFACE_H_Y
        );
    }
}

module dog_mate_receiver() {
    pocket_height = SPLINE_DOG_MATE_POCKET_DEPTH
        + 2 * SPLINE_GEAR_EPS;
    pocket_top_y = SPLINE_DOG_MATE_CENTER_Y
        + SPLINE_DOG_MATE_T / 2
        + SPLINE_GEAR_EPS;
    pocket_center_y = pocket_top_y - pocket_height / 2;
    difference() {
        translate([
            SPLINE_GEAR_CENTER_X,
            SPLINE_DOG_MATE_CENTER_Y + SPLINE_DOG_MATE_T / 2,
            SPLINE_GEAR_CENTER_Z
        ])
            rotate([90, 0, 0])
                cylinder(
                    r = SPLINE_DOG_MATE_R,
                    h = SPLINE_DOG_MATE_T,
                    $fn = 64
                );
        y_bore(
            SPLINE_GEAR_CENTER_X,
            SPLINE_DOG_MATE_CENTER_Y,
            SPLINE_GEAR_CENTER_Z,
            SPLINE_DOG_MATE_BORE_D,
            SPLINE_DOG_MATE_T
        );
        dog_interface_volume(
            pocket_center_y,
            pocket_height,
            SPLINE_DOG_MATE_POCKET_CLEARANCE
        );
    }
}

module spline_gear_dog_solid() {
    // Positive axial overlap joins the annular base and the interface while
    // retaining the through bore. The rounded-triangle face is on Y−.
    union() {
        spline_side_gear();
        lower_dog_ring();
    }
}
//#endregion

//#region 公开 API：缩略图背景
module spline_shaft_thumbnail_context() {
    shaft_root_r = spline_gear_root_r(
        SPLINE_TEETH,
        SPLINE_PITCH_MM,
        SPLINE_TOOTH_DEPTH
    );
    shaft_tip_r = spline_gear_tip_r(
        SPLINE_TEETH,
        SPLINE_PITCH_MM,
        SPLINE_TOOTH_DEPTH
    );
    // Only a short section is shown; the actual shaft remains the separate
    // 159 mm long part. Its center is at X=0, Z=0, so the candidate is visibly
    // placed on the Z+ side by SPLINE_GEAR_CENTER_Z.
    color("#6c7a86", 0.24)
        y_profile_extrude(
            spline_gear_points(SPLINE_TEETH, shaft_root_r, shaft_tip_r),
            0,
            0,
            0,
            36
        );
}

module spline_gear_dog_thumbnail() {
    spline_shaft_thumbnail_context();
    color("#e2a84b")
        spline_side_gear();
    color("#5d7885")
        lower_dog_ring();
    color("#8b9298", 0.65)
        dog_mate_receiver();
}
//#endregion

//#region 业务逻辑
if (SPLINE_GEAR_DOG_MODEL == "solid") {
    spline_gear_dog_solid();
} else if (SPLINE_GEAR_DOG_MODEL == "thumbnail") {
    spline_gear_dog_thumbnail();
} else {
    assert(false, str("unknown SPLINE_GEAR_DOG_MODEL: ", SPLINE_GEAR_DOG_MODEL));
}

echo(
    "spline_gear_dog",
    "model",
    SPLINE_GEAR_DOG_MODEL,
    "axis",
    "Y",
    "profile_plane",
    "XZ",
    "gear_teeth",
    SPLINE_GEAR_TEETH,
    "gear_pitch_mm",
    SPLINE_GEAR_PITCH_MM,
    "gear_outer_d_mm",
    spline_gear_outer_d(),
    "gear_t_mm",
    SPLINE_GEAR_T,
    "gear_bore_d_mm",
    SPLINE_GEAR_BORE_D,
    "gear_center_z_mm",
    spline_gear_center_distance(),
    "dog_interface",
    SPLINE_DOG_INTERFACE,
    "dog_claw_count_backup",
    SPLINE_DOG_CLAW_COUNT,
    "dog_interface_outer_d_mm",
    2 * spline_gear_dog_interface_outer_r(),
    "dog_base_outer_d_mm",
    2 * SPLINE_DOG_BASE_R,
    "dog_interface_h_y_mm",
    SPLINE_DOG_INTERFACE_H_Y,
    "dog_t_mm",
    SPLINE_DOG_T,
    "dog_center_y_mm",
    SPLINE_DOG_INTERFACE_CENTER_Y,
    "dog_bore_d_mm",
    SPLINE_DOG_BORE_D,
    "dog_spline_clearance_mm",
    spline_gear_dog_spline_clearance(),
    "mate_outer_d_mm",
    2 * SPLINE_DOG_MATE_R,
    "radial_envelope_outer_d_mm",
    2 * SPLINE_DOG_RADIAL_ENVELOPE_R,
    "mate_spline_clearance_mm",
    spline_gear_dog_mate_spline_clearance(),
    "mate_pocket_clearance_mm",
    SPLINE_DOG_MATE_POCKET_CLEARANCE
);
//#endregion

//#region 方法/工具
// 导出 solid：-D 'SPLINE_GEAR_DOG_MODEL="solid"'
// 预览 thumbnail：-D 'SPLINE_GEAR_DOG_MODEL="thumbnail"'
//#endregion

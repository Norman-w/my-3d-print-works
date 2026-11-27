// CH1 03C 长齿轮轴 — Y 向长齿 + 两端 Ø3 mm D 轴
//
// Mechanical contract
// process: FDM fit prototype; PETG/nylon preferred for the solid shaft, rigid resin only for fit checks
// material: to be confirmed; the printed Ø3 mm end stubs are not a steel-shaft substitute
// parting_plane: n/a (single axis-aligned printed part)
// opening_direction: n/a
// fastener: timing pulleys slide onto the two nominal Ø3 mm D end stubs in solid mode
// seal: n/a
// print_orientation: lay the part along Y only for assembly; for FDM, print standing or split only after slicer review
// units: mm
// axis: world Y; gear cross-section: world XZ
//
// PRESET values:
//   x1c_fine — 10T / 2.4 mm pitch / 0.60 mm tooth depth, selected for the stock 0.4 mm nozzle
//   standard — legacy 12T / 3.0 mm pitch / 0.82 mm tooth depth, for current 3 mm-pitch mating parts
//
// MODEL values:
//   solid  — full gear section plus an integral 6 mm D stub at each end
//   sleeve — same long gear section with a clearance D bore for an external metal D shaft

//#region 导入/依赖
include <parts/ch1_03c_long_gear_shaft_params.scad>
//#endregion

//#region 常量/配置
$fa = 6;
$fs = 0.24;
//#endregion

//#region 模型/类型
// The 2D profile is authored in local XY and rotated so local +Z becomes world +Y.
//#endregion

//#region 私有成员：截面与轴段
module long_gear_profile_2d() {
    polygon(long_gear_points());
}

// Parameterized library API used by assemblies whose mating gear has a
// different pitch preset.  The standalone entry below still uses the global
// preset from the parameter file; callers should use this module when they
// need to keep their own mating datum authoritative.
function long_gear_points_param(
    teeth,
    pitch_mm,
    tooth_depth,
    tip_start,
    tip_end,
    root_end
) = let(
    pitch_r = teeth * pitch_mm / (2 * PI),
    root_r = pitch_r - tooth_depth,
    tip_r = pitch_r + tooth_depth
) [
    for (i = [0:teeth - 1])
        for (p = [
            [0.00, root_r],
            [tip_start, tip_r],
            [tip_end, tip_r],
            [root_end, root_r]
        ])
            let (a = (i + p[0]) * 360 / teeth)
                [p[1] * cos(a), p[1] * sin(a)]
];

module long_gear_profile_2d_param(
    teeth,
    pitch_mm,
    tooth_depth,
    tip_start,
    tip_end,
    root_end
) {
    polygon(long_gear_points_param(
        teeth,
        pitch_mm,
        tooth_depth,
        tip_start,
        tip_end,
        root_end
    ));
}

module d_profile_2d(
    d,
    flat_depth,
    radial_clearance = 0,
    flat_clearance = 0
) {
    outer_d = d + 2 * radial_clearance;
    difference() {
        circle(d = outer_d);
        // The square removes the +X side, leaving the D flat in the XZ section.
        translate([
            d / 2 - flat_depth + flat_clearance,
            -(outer_d + 2 * LONG_GEAR_EPS)
        ])
            square([
                outer_d + 2 * LONG_GEAR_EPS,
                2 * (outer_d + 2 * LONG_GEAR_EPS)
            ]);
    }
}

module long_gear_body_param(
    teeth,
    pitch_mm,
    tooth_depth,
    tip_start,
    tip_end,
    root_end,
    length
) {
    // Gear body is centered at Y=0 and spans -L/2..+L/2.
    translate([0, -length / 2, 0])
        rotate([-90, 0, 0])
            linear_extrude(
                height = length,
                convexity = max(8, teeth)
            )
                long_gear_profile_2d_param(
                    teeth,
                    pitch_mm,
                    tooth_depth,
                    tip_start,
                    tip_end,
                    root_end
                );
}

module long_gear_body() {
    long_gear_body_param(
        LONG_GEAR_TEETH,
        LONG_GEAR_PITCH_MM,
        LONG_GEAR_TOOTH_DEPTH,
        LONG_GEAR_TIP_START,
        LONG_GEAR_TIP_END,
        LONG_GEAR_ROOT_END,
        LONG_GEAR_LENGTH
    );
}

module d_axis_segment_y(y0, length) {
    // A local +Z extrusion becomes a world +Y D cylinder.
    translate([0, y0, 0])
        rotate([-90, 0, 0])
            linear_extrude(height = length, convexity = 4)
                d_profile_2d(
                    LONG_GEAR_END_D,
                    LONG_GEAR_END_FLAT_DEPTH
                );
}

module d_axis_segment_y_param(y0, length, end_d, end_flat_depth) {
    // A local +Z extrusion becomes a world +Y D cylinder.
    translate([0, y0, 0])
        rotate([-90, 0, 0])
            linear_extrude(height = length, convexity = 4)
                d_profile_2d(end_d, end_flat_depth);
}

module d_bore_cut() {
    // The sleeve bore is cut only through the gear body. The real metal shaft
    // is expected to continue beyond both gear faces for pulley mounting.
    translate([
        0,
        -LONG_GEAR_LENGTH / 2 - LONG_GEAR_EPS,
        0
    ])
        rotate([-90, 0, 0])
            linear_extrude(
                height = LONG_GEAR_LENGTH + 2 * LONG_GEAR_EPS,
                convexity = 4
            )
                d_profile_2d(
                    LONG_GEAR_END_D,
                    LONG_GEAR_END_FLAT_DEPTH,
                    LONG_GEAR_BORE_RADIAL_CLEARANCE,
                    LONG_GEAR_BORE_FLAT_CLEARANCE
                );
}
//#endregion

//#region 公开 API：两种打印件
module long_gear_shaft_solid_param(
    teeth,
    pitch_mm,
    tooth_depth,
    tip_start,
    tip_end,
    root_end,
    length,
    end_stub_length,
    stub_overlap,
    end_d,
    end_flat_depth,
    lower_end_stub_length = undef,
    upper_end_stub_length = undef
) {
    lower_stub = is_undef(lower_end_stub_length)
        ? end_stub_length
        : lower_end_stub_length;
    upper_stub = is_undef(upper_end_stub_length)
        ? end_stub_length
        : upper_end_stub_length;
    // The overlap is hidden inside the gear body so each D stub is materially
    // connected rather than merely touching a coplanar end face.
    union() {
        long_gear_body_param(
            teeth,
            pitch_mm,
            tooth_depth,
            tip_start,
            tip_end,
            root_end,
            length
        );
        d_axis_segment_y_param(
            -length / 2 - lower_stub,
            lower_stub + stub_overlap,
            end_d,
            end_flat_depth
        );
        d_axis_segment_y_param(
            length / 2 - stub_overlap,
            upper_stub + stub_overlap,
            end_d,
            end_flat_depth
        );
    }
}

module long_gear_shaft_solid() {
    long_gear_shaft_solid_param(
        LONG_GEAR_TEETH,
        LONG_GEAR_PITCH_MM,
        LONG_GEAR_TOOTH_DEPTH,
        LONG_GEAR_TIP_START,
        LONG_GEAR_TIP_END,
        LONG_GEAR_ROOT_END,
        LONG_GEAR_LENGTH,
        LONG_GEAR_END_STUB_LENGTH,
        LONG_GEAR_STUB_OVERLAP,
        LONG_GEAR_END_D,
        LONG_GEAR_END_FLAT_DEPTH
    );
}

module long_gear_shaft_sleeve() {
    difference() {
        long_gear_body();
        d_bore_cut();
    }
}

module long_gear_shaft_comparison() {
    // Preview-only side-by-side check; never use this entry for a printable STL.
    translate([-11, 0, 0])
        long_gear_shaft_solid();
    translate([11, 0, 0])
        long_gear_shaft_sleeve();
}
//#endregion

//#region 业务逻辑
if (LONG_GEAR_MODEL == "solid") {
    long_gear_shaft_solid();
} else if (LONG_GEAR_MODEL == "sleeve") {
    long_gear_shaft_sleeve();
} else if (LONG_GEAR_MODEL == "comparison") {
    long_gear_shaft_comparison();
} else {
    assert(false, str("unknown LONG_GEAR_MODEL: ", LONG_GEAR_MODEL));
}

echo(
    "long_gear_shaft",
    "model",
    LONG_GEAR_MODEL,
    "preset",
    LONG_GEAR_PRESET,
    "axis",
    "Y",
    "profile_plane",
    "XZ",
    "teeth",
    LONG_GEAR_TEETH,
    "pitch_mm",
    LONG_GEAR_PITCH_MM,
    "gear_length_mm",
    LONG_GEAR_LENGTH,
    "end_stub_length_mm",
    LONG_GEAR_END_STUB_LENGTH,
    "overall_length_mm",
    LONG_GEAR_LENGTH + 2 * LONG_GEAR_END_STUB_LENGTH,
    "outer_d_mm",
    long_gear_outer_d(),
    "root_d_mm",
    2 * long_gear_root_r(),
    "tip_land_mm",
    long_gear_tip_land_mm(),
    "root_gap_mm",
    long_gear_root_gap_mm(),
    "end_d_mm",
    LONG_GEAR_END_D
);
//#endregion

//#region 方法/工具
// 导出示例：-D LONG_GEAR_MODEL="solid" 或 "sleeve"。
//#endregion

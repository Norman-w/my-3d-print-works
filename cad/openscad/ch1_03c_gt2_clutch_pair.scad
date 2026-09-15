// CH1 03C 打印版 GT2 复合子母轮
//
// Mechanical contract
// process: FDM fit prototype; PETG preferred for the first functional article,
//          PLA is acceptable for a fit check, nylon is an optional wear upgrade
// material: printed low-load drawer mechanism; no metal load rating is assumed
// parting_plane: none; each STL is one complete axis-aligned printed part
// opening_direction: the male rounded-triangle dog enters the female pocket
//                  along world Y+ during assembly
// fastener: nominal Ø3 mm D shaft passes through both printed parts; no adhesive
// seal: n/a
// print_orientation: local Z is the shaft axis; both exported STLs print flat
//                  with the gear/pulley face on the build plate
// units: mm
// assembly_axis: world Y; assembly profile plane: world XZ
//
// MODEL values:
//   male     — 15T / 2.4 mm child gear + unchanged rounded-triangle dog
//   female   — unchanged mother pocket + integrated 12T / 2 mm GT2 pulley
//   assembly — colored clearance check with the long spline shaft and belt
//              back-envelope reference; never use this mode as a print STL

//#region 导入/依赖
include <parts/ch1_03c_gt2_clutch_pair_params.scad>
//#endregion

//#region 常量/配置
$fa = 5;
$fs = 0.12;

GT2_MOTHER_GAP = is_undef(GT2_MOTHER_GAP)
    ? 0.35
    : GT2_MOTHER_GAP;
//#endregion

//#region 私有成员：二维轮廓与轴孔
module z_profile_extrude(points, z0, height) {
    translate([0, 0, z0])
        linear_extrude(
            height = height,
            convexity = 12
        )
            polygon(points);
}

module d_bore_2d() {
    outer_d = GT2_D_AXIS_D + 2 * GT2_D_BORE_RADIAL_CLEARANCE;
    flat_x = GT2_D_AXIS_D / 2
        - GT2_D_AXIS_FLAT_DEPTH
        + GT2_D_BORE_FLAT_CLEARANCE;
    difference() {
        circle(d = outer_d, $fn = 64);
        // Remove the +X cap to leave the D flat facing +X.
        translate([
            flat_x,
            -(outer_d + 2 * GT2_EPS)
        ])
            square([
                outer_d + 2 * GT2_EPS,
                2 * (outer_d + 2 * GT2_EPS)
            ]);
    }
}

module d_bore_cut(z0, height) {
    translate([0, 0, z0])
        linear_extrude(
            height = height,
            convexity = 4
        )
            d_bore_2d();
}

module rounded_triangle_prism(z0, height, extra_radius = 0) {
    // The convex hull of three circular heads gives the same continuous,
    // rounded-triangle dog used by the committed predecessor part.
    hull() {
        for (i = [0:2]) {
            angle = GT2_DOG_INTERFACE_ROTATION_DEG + i * 120;
            translate([
                GT2_DOG_INTERFACE_R * cos(angle),
                GT2_DOG_INTERFACE_R * sin(angle),
                z0
            ])
                cylinder(
                    r = GT2_DOG_INTERFACE_HEAD_R + extra_radius,
                    h = height,
                    $fn = 32
                );
        }
    }
}
//#endregion

//#region 私有成员：子轮与母轮局部几何
module male_gear_local() {
    z_profile_extrude(
        gt2_male_gear_points(),
        0,
        GT2_MALE_GEAR_T
    );
}

module male_dog_base_local() {
    dog_base_z0 = GT2_MALE_GEAR_T
        - GT2_DOG_GEAR_OVERLAP;
    cylinder(
        r = GT2_DOG_BASE_R,
        h = GT2_DOG_BASE_T,
        $fn = 64
    );
}

module male_dog_interface_local() {
    dog_base_z0 = GT2_MALE_GEAR_T
        - GT2_DOG_GEAR_OVERLAP;
    interface_z0 = dog_base_z0
        + GT2_DOG_BASE_T
        - GT2_DOG_INTERFACE_OVERLAP;
    rounded_triangle_prism(
        interface_z0,
        GT2_DOG_INTERFACE_H
    );
}

module male_local_raw() {
    union() {
        male_gear_local();
        translate([0, 0, GT2_MALE_GEAR_T - GT2_DOG_GEAR_OVERLAP])
            male_dog_base_local();
        male_dog_interface_local();
    }
}

module male_local() {
    male_total_h = GT2_MALE_GEAR_T
        - GT2_DOG_GEAR_OVERLAP
        + GT2_DOG_BASE_T
        - GT2_DOG_INTERFACE_OVERLAP
        + GT2_DOG_INTERFACE_H;
    difference() {
        male_local_raw();
        d_bore_cut(
            -GT2_EPS,
            male_total_h + 2 * GT2_EPS
        );
    }
}

module gt2_pulley_local() {
    union() {
        z_profile_extrude(
            gt2_pulley_points(),
            0,
            GT2_PULLEY_FACE_T
        );
        // Thin radial guide lips sit at both belt edges. Their outside radius
        // is only a little beyond the conservative belt-back envelope, so
        // they retain the belt without recreating a 12 mm commercial hub.
        gt2_belt_guide_lip(0);
        gt2_belt_guide_lip(
            GT2_PULLEY_FACE_T - GT2_BELT_GUIDE_LIP_T
        );
    }
}

module gt2_belt_guide_lip(z0) {
    translate([0, 0, z0])
        difference() {
            cylinder(
                r = gt2_belt_guide_r(),
                h = GT2_BELT_GUIDE_LIP_T,
                $fn = 96
            );
            translate([0, 0, -GT2_EPS])
                cylinder(
                    r = gt2_pulley_tip_r() - 0.05,
                    h = GT2_BELT_GUIDE_LIP_T + 2 * GT2_EPS,
                    $fn = 96
                );
        }
}

module mother_receiver_local_raw() {
    receiver_bottom_z = GT2_PULLEY_FACE_T
        - GT2_MOTHER_PULLEY_OVERLAP;
    translate([0, 0, receiver_bottom_z])
        cylinder(
            r = GT2_MOTHER_OUTER_R,
            h = GT2_MOTHER_T,
            $fn = 64
        );
}

module mother_receiver_local() {
    receiver_bottom_z = GT2_PULLEY_FACE_T
        - GT2_MOTHER_PULLEY_OVERLAP;
    receiver_top_z = receiver_bottom_z + GT2_MOTHER_T;
    mother_total_h = receiver_top_z;
    difference() {
        mother_receiver_local_raw();
        // The pocket opens toward local +Z. During assembly this face is
        // rotated toward world +Y, opposite the male dog that points world Y−.
        rounded_triangle_prism(
            receiver_top_z
                - GT2_MOTHER_POCKET_DEPTH
                - GT2_EPS,
            GT2_MOTHER_POCKET_DEPTH + 2 * GT2_EPS,
            GT2_MOTHER_POCKET_CLEARANCE
        );
        d_bore_cut(
            receiver_bottom_z - GT2_EPS,
            GT2_MOTHER_T + 2 * GT2_EPS
        );
    }
}

module female_local() {
    receiver_bottom_z = GT2_PULLEY_FACE_T
        - GT2_MOTHER_PULLEY_OVERLAP;
    receiver_top_z = receiver_bottom_z + GT2_MOTHER_T;
    female_total_h = receiver_top_z;
    difference() {
        union() {
            gt2_pulley_local();
            mother_receiver_local_raw();
        }
        // Keep one continuous D bore through both axial layers.
        d_bore_cut(
            -GT2_EPS,
            female_total_h + 2 * GT2_EPS
        );
        // Pocket opens on the mother face and remains independent of the
        // GT2 tooth layer below it.
        rounded_triangle_prism(
            receiver_top_z
                - GT2_MOTHER_POCKET_DEPTH
                - GT2_EPS,
            GT2_MOTHER_POCKET_DEPTH + 2 * GT2_EPS,
            GT2_MOTHER_POCKET_CLEARANCE
        );
    }
}
//#endregion

//#region 私有成员：装配缩略图背景
module y_profile_extrude(points, center_y, center_z, length) {
    // Local +Z becomes world −Y; the resulting interval is centered at
    // center_y and keeps the real assembly direction visible.
    translate([0, center_y + length / 2, center_z])
        rotate([90, 0, 0])
            linear_extrude(
                height = length,
                convexity = 12
            )
                polygon(points);
}

module long_spline_shaft_context() {
    color("#687783", 0.28)
        y_profile_extrude(
            gt2_long_gear_points(),
            0,
            0,
            54
        );
}

module y_ring(center_y, center_z, outer_r, inner_r, width) {
    translate([0, center_y + width / 2, center_z])
        rotate([90, 0, 0])
            difference() {
                cylinder(r = outer_r, h = width, $fn = 96);
                translate([0, 0, -GT2_EPS])
                    cylinder(
                        r = inner_r,
                        h = width + 2 * GT2_EPS,
                        $fn = 96
                    );
            }
}

module male_assembly() {
    male_total_h = GT2_MALE_GEAR_T
        - GT2_DOG_GEAR_OVERLAP
        + GT2_DOG_BASE_T
        - GT2_DOG_INTERFACE_OVERLAP
        + GT2_DOG_INTERFACE_H;
    // Gear center is at world Y=0; local +Z becomes world Y− so the dog
    // points downward toward the mother pocket.
    color("#e2a84b")
        translate([0, GT2_MALE_GEAR_T / 2, gt2_center_distance()])
            rotate([90, 0, 0])
                male_local();
}

module female_assembly() {
    male_total_h = GT2_MALE_GEAR_T
        - GT2_DOG_GEAR_OVERLAP
        + GT2_DOG_BASE_T
        - GT2_DOG_INTERFACE_OVERLAP
        + GT2_DOG_INTERFACE_H;
    male_dog_bottom_y = GT2_MALE_GEAR_T / 2
        - male_total_h;
    female_y = male_dog_bottom_y
        - GT2_MOTHER_GAP
        - (GT2_PULLEY_FACE_T
            - GT2_MOTHER_PULLEY_OVERLAP
            + GT2_MOTHER_T);
    color("#5d7885")
        translate([0, female_y, gt2_center_distance()])
            rotate([-90, 0, 0])
                female_local();

    // A translucent belt-back envelope is only a clearance aid. It is not a
    // tooth-perfect belt and is deliberately excluded from both print STLs.
    color("#bd5d68", 0.22)
        y_ring(
            female_y + GT2_PULLEY_FACE_T / 2,
            gt2_center_distance(),
            gt2_belt_envelope_r(),
            max(
                gt2_pulley_pitch_r() - 0.20,
                GT2_D_AXIS_D / 2 + 0.20
            ),
            GT2_BELT_WIDTH
        );
}

module assembly_thumbnail() {
    long_spline_shaft_context();
    male_assembly();
    female_assembly();
}
//#endregion

//#region 业务逻辑
if (GT2_CLUTCH_MODEL == "male") {
    male_local();
} else if (GT2_CLUTCH_MODEL == "female") {
    female_local();
} else if (GT2_CLUTCH_MODEL == "assembly") {
    assembly_thumbnail();
}

echo(
    "gt2_clutch_pair",
    "model",
    GT2_CLUTCH_MODEL,
    "axis_print",
    "Z",
    "axis_assembly",
    "Y",
    "male_teeth",
    GT2_MALE_TEETH,
    "male_pitch_mm",
    GT2_MALE_PITCH_MM,
    "male_gear_outer_d_mm",
    2 * gt2_male_tip_r(),
    "center_distance_mm",
    gt2_center_distance(),
    "center_shift_from_old_12t_mm",
    gt2_center_shift(),
    "gt2_teeth",
    GT2_PULLEY_TEETH,
    "gt2_pitch_mm",
    GT2_PULLEY_PITCH_MM,
    "gt2_belt_width_mm",
    GT2_BELT_WIDTH,
    "gt2_tooth_outer_d_mm",
    2 * gt2_pulley_tip_r(),
    "gt2_belt_envelope_outer_d_mm",
    2 * gt2_belt_envelope_r(),
    "gt2_belt_guide_outer_d_mm",
    2 * gt2_belt_guide_r(),
    "male_dog_outer_d_mm",
    2 * gt2_triangle_outer_r(),
    "mother_outer_d_mm",
    2 * GT2_MOTHER_OUTER_R,
    "mother_pocket_outer_d_mm",
    2 * gt2_mother_pocket_outer_r(),
    "belt_clearance_to_long_spline_mm",
    gt2_belt_clearance_to_long_shaft(),
    "belt_guide_clearance_to_long_spline_mm",
    gt2_belt_guide_clearance_to_long_shaft(),
    "mother_clearance_to_long_spline_mm",
    gt2_mother_clearance_to_long_shaft(),
    "mother_gap_mm",
    GT2_MOTHER_GAP
);
//#endregion

//#region 方法/工具
// Export with -D 'GT2_CLUTCH_MODEL="male"', "female", or "assembly".
// Only male and female are printable STLs; assembly includes translucent
// diagnostic background geometry.
//#endregion

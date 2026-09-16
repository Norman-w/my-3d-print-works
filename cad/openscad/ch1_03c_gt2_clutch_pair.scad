// CH1 03C 打印版 GT2 复合子母轮
//
// Mechanical contract
// process: FDM fit prototype; PETG preferred for the first functional article,
//          PLA is acceptable for a fit check, nylon is an optional wear upgrade
// material: printed low-load drawer mechanism; no metal load rating is assumed
// parting_plane: none; each STL is one complete axis-aligned printed part
// opening_direction: the male rounded-triangle dog enters the female pocket
//                  along world Y+ during assembly
// fastener: a short nominal Ø3 mm D shaft engages only the gear/pulley bodies;
//           the mating dog/receiver centers are reserved for Ø2 mm magnets
// seal: n/a
// print_orientation: local Z is the shaft axis; both exported STLs print flat
//                  with the gear/pulley face on the build plate
// units: mm
// assembly_axis: world Y; assembly profile plane: world XZ
//
// MODEL values:
//   male     — lower 15T / 2.4 mm child gear + 3 mm deep shallow-taper rounded dog
//   female   — upper 3.25 mm deep relieved mother pocket + integrated 12T / 2 mm GT2 pulley
//   assembly — colored clearance check with the long spline shaft and belt
//              back-envelope reference; never use this mode as a print STL

//#region 导入/依赖
include <parts/ch1_03c_gt2_clutch_pair_params.scad>
//#endregion

//#region 常量/配置
$fa = 5;
$fs = 0.12;

// The standalone file exports one of its three preview modes. The cabinet
// scene includes the same modules as an embedded library and owns the output
// dispatch, so suppress standalone top-level geometry in that context.
GT2_CLUTCH_EMBEDDED = is_undef(GT2_CLUTCH_EMBEDDED)
    ? false
    : GT2_CLUTCH_EMBEDDED;
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

module magnet_pocket_cut(z0, height) {
    // The magnet pockets are deliberately concentric. The male pocket opens
    // at the dog nose; the female pocket opens at the floor of the mother
    // slot, so the two Ø2 mm magnets face each other when engaged.
    translate([0, 0, z0])
        cylinder(
            d = GT2_MAGNET_POCKET_D,
            h = height,
            $fn = 48
        );
}

module rounded_triangle_tapered_prism(
    z0,
    height,
    root_center_r,
    tip_center_r,
    root_head_r,
    tip_head_r
) {
    // A hull between two thin, rounded-triangle sections makes a shallow
    // rounded trapezoid in side view: the root remains strong, while the
    // smaller leading end can enter the receiver without a square vertical
    // wall or a sharp cone. The cylinders are deliberately very short so the
    // two end faces remain flat and the full specified insertion depth is usable.
    assert(height > 2 * GT2_EPS, "rounded triangle height is too small");
    hull() {
        for (level = [0:1]) {
            center_r = level == 0 ? root_center_r : tip_center_r;
            head_r = level == 0 ? root_head_r : tip_head_r;
            z = level == 0 ? z0 : z0 + height - GT2_EPS;
            for (i = [0:2]) {
                angle = GT2_DOG_INTERFACE_ROTATION_DEG + i * 120;
                translate([
                    center_r * cos(angle),
                    center_r * sin(angle),
                    z
                ])
                    cylinder(
                        r = head_r,
                        h = GT2_EPS,
                        $fn = 32
                    );
            }
        }
    }
}

module mother_pocket_prism(z0, height) {
    // One continuous rounded-triangle frustum: the mouth has the larger
    // running clearance and narrows smoothly toward the pocket floor. There
    // is deliberately no step, ledge, or sudden entry flare that could catch
    // the rounded male dog while it is being inserted or pulled out.
    rounded_triangle_tapered_prism(
        z0 - GT2_EPS,
        height + 2 * GT2_EPS,
        GT2_DOG_INTERFACE_R,
        gt2_triangle_tip_center_r(),
        GT2_DOG_INTERFACE_HEAD_R + GT2_MOTHER_POCKET_CLEARANCE,
        GT2_DOG_INTERFACE_TIP_HEAD_R + GT2_MOTHER_ENTRY_CLEARANCE
    );
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

module male_dog_interface_local() {
    // Start directly in the last 0.20 mm of the gear band. There is no
    // separate circular washer/collar between the gear and the dog.
    interface_z0 = GT2_MALE_GEAR_T - GT2_DOG_GEAR_OVERLAP;
    rounded_triangle_tapered_prism(
        interface_z0,
        GT2_DOG_INTERFACE_H,
        GT2_DOG_INTERFACE_R,
        gt2_triangle_tip_center_r(),
        GT2_DOG_INTERFACE_HEAD_R,
        GT2_DOG_INTERFACE_TIP_HEAD_R
    );
}

module male_local_raw() {
    union() {
        male_gear_local();
        male_dog_interface_local();
    }
}

module male_local() {
    difference() {
        male_local_raw();
        // Short blind D socket from the gear underside. It stops before the
        // dog, leaving the dog center solid for the concentric magnet pocket.
        d_bore_cut(-GT2_EPS, GT2_D_BORE_DEPTH + GT2_EPS);
        // Blind Ø2.2 mm printed pocket for a nominal Ø2 mm magnet, opening
        // from the rounded dog nose.
        magnet_pocket_cut(
            gt2_male_magnet_pocket_z0(),
            GT2_MAGNET_POCKET_H + GT2_EPS
        );
    }
}

module gt2_pulley_local() {
    union() {
        // Full lower retainer: a 1 mm thick circular plate closes the lower
        // end of the belt path and gives the print a broad, stable first
        // layer. The short blind D socket is cut in female_local() below.
        cylinder(
            r = gt2_belt_guide_r(),
            h = GT2_BELT_LOWER_RETAINER_T,
            $fn = 96
        );
        z_profile_extrude(
            gt2_pulley_points(),
            gt2_pulley_face_bottom_z(),
            GT2_PULLEY_FACE_T
        );
        // The upper guide lip remains thinner so a closed loop belt can be
        // fitted from the side; the lower side is held by the full retainer.
        gt2_belt_guide_lip(
            gt2_pulley_face_top_z()
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
    receiver_bottom_z = gt2_mother_receiver_bottom_z();
    translate([0, 0, receiver_bottom_z])
        cylinder(
            r = GT2_MOTHER_OUTER_R,
            h = GT2_MOTHER_T,
            $fn = 64
        );
}

module mother_receiver_local() {
    receiver_bottom_z = gt2_mother_receiver_bottom_z();
    receiver_top_z = gt2_mother_receiver_top_z();
    difference() {
        mother_receiver_local_raw();
        // The pocket opens toward local +Z. During assembly this face is
        // rotated toward world Y−, opposite the lower male dog that points Y+.
        mother_pocket_prism(
            receiver_top_z - GT2_MOTHER_POCKET_DEPTH,
            GT2_MOTHER_POCKET_DEPTH
        );
        // Keep the magnet pocket at the center of the mother-slot floor; it
        // does not continue through the receiver as a D bore.
        magnet_pocket_cut(
            gt2_female_magnet_pocket_z0(),
            GT2_MAGNET_POCKET_H + GT2_EPS
        );
    }
}

module female_local() {
    receiver_bottom_z = gt2_mother_receiver_bottom_z();
    receiver_top_z = gt2_mother_receiver_top_z();
    difference() {
        union() {
            gt2_pulley_local();
            mother_receiver_local_raw();
        }
        // Short blind D socket from the underside of the GT2 wheel. The
        // receiver above it remains free for the centered magnet pocket.
        d_bore_cut(-GT2_EPS, GT2_D_BORE_DEPTH + GT2_EPS);
        // Pocket opens on the mother face and remains independent of the
        // GT2 tooth layer below it.
        mother_pocket_prism(
            receiver_top_z - GT2_MOTHER_POCKET_DEPTH,
            GT2_MOTHER_POCKET_DEPTH
        );
        // The opening is at the mother-slot floor, not at the outside face;
        // this leaves the triangular receiver geometry intact around it.
        magnet_pocket_cut(
            gt2_female_magnet_pocket_z0(),
            GT2_MAGNET_POCKET_H + GT2_EPS
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
    // Lower child wheel: local +Z becomes world Y+, so the dog points upward
    // toward the upper mother pocket. The gear underside is the Y=0 datum.
    color("#e2a84b")
        translate([0, 0, gt2_center_distance()])
            rotate([-90, 0, 0])
                male_local();
}

module female_assembly() {
    // Upper mother wheel: its local +Z face points world Y−. Put its mouth
    // one controlled gap above the male nose, leaving room for release.
    male_dog_tip_y = gt2_male_total_h();
    female_y = male_dog_tip_y
        + GT2_MOTHER_GAP
        + gt2_female_total_h();
    color("#5d7885")
        translate([0, female_y, gt2_center_distance()])
            rotate([90, 0, 0])
                female_local();

    // A translucent belt-back envelope is only a clearance aid. It is not a
    // tooth-perfect belt and is deliberately excluded from both print STLs.
    color("#bd5d68", 0.22)
        y_ring(
            female_y
                - gt2_pulley_face_bottom_z()
                + GT2_PULLEY_FACE_T / 2,
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
if (!GT2_CLUTCH_EMBEDDED) {
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
    "male_gear_band_t_mm",
    GT2_MALE_GEAR_T,
    "male_dog_interface_h_mm",
    GT2_DOG_INTERFACE_H,
    "male_dog_tip_outer_d_mm",
    2 * gt2_triangle_tip_outer_r(),
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
    "belt_lower_retainer_t_mm",
    GT2_BELT_LOWER_RETAINER_T,
    "belt_upper_guide_lip_t_mm",
    GT2_BELT_GUIDE_LIP_T,
    "male_dog_outer_d_mm",
    2 * gt2_triangle_outer_r(),
    "mother_outer_d_mm",
    2 * GT2_MOTHER_OUTER_R,
    "mother_pocket_outer_d_mm",
    2 * gt2_mother_pocket_outer_r(),
    "mother_receiver_t_mm",
    GT2_MOTHER_T,
    "mother_pocket_depth_mm",
    GT2_MOTHER_POCKET_DEPTH,
    "mother_floor_t_mm",
    gt2_mother_floor_t(),
    "belt_clearance_to_long_spline_mm",
    gt2_belt_clearance_to_long_shaft(),
    "belt_guide_clearance_to_long_spline_mm",
    gt2_belt_guide_clearance_to_long_shaft(),
    "mother_clearance_to_long_spline_mm",
    gt2_mother_clearance_to_long_shaft(),
    "mother_gap_mm",
    GT2_MOTHER_GAP,
    "mother_effective_insertion_mm",
    GT2_MOTHER_EFFECTIVE_INSERTION,
    "clutch_stroke_mm",
    GT2_CLUTCH_ENGAGE_STROKE_MM,
    "mother_bottom_clearance_mm",
    GT2_MOTHER_BOTTOM_CLEARANCE,
    "actuator_trigger_spacing_mm",
    GT2_ACTUATOR_TRIGGER_SPACING_MM,
    "d_bore_depth_mm",
    GT2_D_BORE_DEPTH,
    "magnet_nominal_d_mm",
    GT2_MAGNET_NOMINAL_D,
    "magnet_pocket_d_mm",
    GT2_MAGNET_POCKET_D,
    "magnet_pocket_h_mm",
    GT2_MAGNET_POCKET_H,
    "magnet_center_r_mm",
    0,
    "male_magnet_pocket_z0_mm",
    gt2_male_magnet_pocket_z0(),
    "female_magnet_pocket_z0_mm",
    gt2_female_magnet_pocket_z0()
    );
}
//#endregion

//#region 方法/工具
// Export with -D 'GT2_CLUTCH_MODEL="male"', "female", or "assembly".
// Only male and female are printable STLs; assembly includes translucent
// diagnostic background geometry.
//#endregion

// Mechanical contract
// process: assembly visualization — one 12T D-shaft drive sprocket; all green guide wheels are small 8T blunt bearing idlers
// material: pointed drive sprocket resin/PETG TBD; chain carbon steel 03C; blunt idlers PETG
// parting_plane: n/a for chain; cabinet back face remains Y = D
// opening_direction: n/a
// fastener: rear-view lower-right snake_drive_c() sprocket uses the 3 mm D-shaft; other wheels use 3 mm round bearing seats; the motor follows a rounded rectangular Ω clamp with four bottom holes that slide over Ø5 floor Boss posts (12 mm post section) and M3 downward screws into blind pilots, and is pressed in the former tensioner slot by a spring screw
// seal: n/a
// print_orientation: sprocket hub down; do not 3D-print the chain
// units: mm
// note: 5x3 row-major snake through every bay center; rear-view right return; the only snake motor is at the lower-right return/tensioner position (snake_drive_c()); all wheels are face-flipped; bearings are separate display/purchase geometry

//#region 导入/依赖
QUALITY = is_undef(QUALITY) ? 2 : QUALITY;
// cabinet.scad and ch1_03c_roller_chain.scad both own a global PART selector.
// Keep the chain export selector in its own namespace so an included library
// cannot silently turn a one-part export back into the full assembly.
CHAIN_PART = is_undef(CHAIN_PART) ? "assembly" : CHAIN_PART;
EXPLODE = is_undef(EXPLODE) ? 48 : EXPLODE;
CHAIN_LIB_ONLY = true;
CABINET_LIB_ONLY = true;
include <cabinet.scad>
include <../ch1_03c_roller_chain.scad>
include <cabinet_chain_path.scad>
use <../parts/ch1_03c_sprocket.scad>
use <../parts/ch1_03c_blunt_idler.scad>
use <../parts/ch1_03c_bearing_visual.scad>
use <../parts/motor_pololu_micro_metal_100_1_hp_6v.scad>
use <../parts/motor_pololu_mount_cover.scad>
include <../parts/ch1_03c_gt2_clutch_pair_params.scad>
include <../parts/ch1_03c_chain_trigger_params.scad>
//#endregion

//#region 常量/配置
$fa = 8;
$fs = 0.22;
CHAIN_Y = MOTOR_MOUNT_CHAIN_Y;
// One 03C link is augmented by a printed side-car carrier. The shared
// parameter file is the only source of the M5 magnet and carrier dimensions.
CHAIN_TRIGGER_MAGNET_SEGMENT_INDEX = CHAIN_TRIGGER_SEGMENT_INDEX;
CHAIN_TRIGGER_MAGNET_D = CHAIN_TRIGGER_MAGNET_DIAMETER;
CHAIN_TRIGGER_MAGNET_L = CHAIN_TRIGGER_MAGNET_LENGTH;
CHAIN_TRIGGER_MAGNET_AXIAL_START_OFFSET =
    CHAIN_TRIGGER_CARRIER_AXIAL_START_OFFSET;
//#endregion

//#region 模型/类型
// 销轴路径在 cabinet_chain_path.scad；本文件只做后仓装配。
//#endregion

//#region 私有成员
echo("snake_pins", len(snake_pins()), "length_mm", len(snake_pins()) * P);
echo("snake_drive", snake_drive_c(), "upper_guide", power_c(), "entry", entry_c(), "service_return", drive_c(), "service_press", service_press_c(), "tensioner", ten_path_c(), "ten_z", TEN_Z);

module snake_in_rear() {
    translate([0, CHAIN_Y, 0])
        rotate([90, 0, 0])
            children();
}

module place_xz(c) {
    translate([c[0], CHAIN_Y, c[1]])
        children();
}

module place_geared(c) {
    place_xz(c)
        rotate([90, 0, 0])
            rotate([0, 0, wheel_pose_rot(c[0], c[1])])
                rotate([180, 0, 0])
                    children();
}

module place_power_motor(c) {
    // The flipped power wheel presents its D bore toward +Y. The motor sits behind
    // that face, with local +Z rotated to world -Y so the shaft enters the wheel.
    translate([c[0], CHAIN_Y + HUB_H / 2, c[1]])
        rotate([90, 0, 0])
            children();
}

module place_power_motor_cover(c) {
    translate([c[0], CHAIN_Y, c[1]])
        children();
}

module rear_blunt_idlers() {
    for (c = blunt_centers())
        place_geared(c) ch1_03c_bearing_blunt_idler(BLUNT_TEETH);
}

module rear_guide_idlers() {
    // 所有绿色固定导向位统一替换为小尺寸 8T 钝齿轮；路径求解器已同步
    // 把这些位置的弯折半径和切线改为 8T，不能只替换外形而保留 12T 节圆。
    for (c = concat([entry_c(), power_c()], right_turn_sprockets_without_power(), left_turn_sprockets(), [drive_c(), service_press_c()]))
        place_geared(c) ch1_03c_bearing_blunt_idler(BLUNT_TEETH);
    rear_blunt_idlers();
}

module rear_bearing_visuals() {
    // 与轴承版齿轮一一对应；旧高 X 转向位 power_c() 现在也是普通轴承轮，
    // 右下 snake_drive_c() 才是 D 轴动力轮。
    for (c = concat([entry_c(), power_c()], right_turn_sprockets_without_power(), left_turn_sprockets(), [drive_c(), service_press_c()]))
        place_geared(c) ch1_03c_bearing_visual();
    for (c = blunt_centers())
        place_geared(c) ch1_03c_bearing_visual();
}

module chain_idler_shoulder_screw_local() {
    // The rendered axle is a purchased M3 shoulder screw: the smooth Ø3
    // shoulder passes through the MR63 inner race, the short threaded tip
    // enters the printed Ø2.4 blind pilot, and the head/washer stays on the
    // chain's -Z side. It is a static reference; the green wheel/bearing
    // group may rotate around it.
    color("#aeb6bf") {
        translate([0, 0, -8.45])
            cylinder(d = 2.40, h = 4.20, $fn = 36);
        translate([0, 0, -4.25])
            cylinder(d = 3.00, h = 8.50, $fn = 48);
        translate([0, 0, 4.25])
            cylinder(d = 5.50, h = 1.60, $fn = 48);
    }
}

module rear_idler_axles() {
    // WHEEL_POSES[0] is the blue 12T motor sprocket. Only the nine generated
    // 8T green guide positions receive a fixed shoulder axle.
    for (i = [1:len(WHEEL_POSES) - 1])
        place_geared([WHEEL_POSES[i][0], WHEEL_POSES[i][1], 0])
            chain_idler_shoulder_screw_local();
}

module rear_sprockets() {
    // 右下回程/张紧位承接唯一 D 轴动力；所有其它位置都在 rear_guide_idlers() 中。
    place_geared(snake_drive_c()) ch1_03c_sprocket(SPROCKET_TEETH);
}

module plates_on_path(pins) {
    // The current mechanism uses the real 03C chain envelope throughout.
    // There is no special highlighted connector or extended clutch link in
    // the installed logic; a normal chain link remains at every segment.
    n = len(pins);
    axis = [0, 0, 1];
    for (i = [0:n - 1])
        place_from_to(pins[i], pins[(i + 1) % n], axis) {
            if (i % 2 == 0)
                outer_plates();
            else
                inner_plates();
        }
}

module trigger_carrier_root() {
    // One full 03C outer-link footprint with two true pin holes. Its axial
    // thickness is the net length between the two purchased U-clip grooves;
    // the two long pins therefore capture this root as one real part.
    // It is not a second chain link or a separate box.
    translate([0, CHAIN_TRIGGER_CARRIER_ROOT_AXIAL_END_Y, 0])
        rotate([90, 0, 0])
            linear_extrude(
                height = CHAIN_TRIGGER_CARRIER_PLATE_THICKNESS,
                convexity = 8
            )
                plate_profile(CHAIN_TRIGGER_CARRIER_PIN_HOLE_DIAMETER);
}

module clutch_trigger_carrier_reference() {
    p0 = snake_pins()[CHAIN_TRIGGER_MAGNET_SEGMENT_INDEX];
    p1 = snake_pins()[(CHAIN_TRIGGER_MAGNET_SEGMENT_INDEX + 1) % len(snake_pins())];
    snake_in_rear()
        place_from_to(p0, p1, [0, 0, 1])
            color("#d9933d")
                union() {
                    trigger_carrier_root();
                    chain_trigger_tail_body();
                }
}

module clutch_trigger_magnet_reference() {
    // The M5 magnet sits in the rear rounded tail. The exported STL cylinder
    // axis is STL Z after the path-frame transform; the pre-transform SCAD
    // local axis is only an implementation detail, not the delivered datum.
    p0 = snake_pins()[CHAIN_TRIGGER_MAGNET_SEGMENT_INDEX];
    p1 = snake_pins()[(CHAIN_TRIGGER_MAGNET_SEGMENT_INDEX + 1) % len(snake_pins())];
    tail_d = CHAIN_TRIGGER_CARRIER_TAIL_DEPTH;
    magnet_center_y = CHAIN_TRIGGER_CARRIER_ROOT_AXIAL_CENTER_Y;
    magnet_start_normal =
        CHAIN_TRIGGER_CARRIER_TAIL_CENTER_NORMAL
            + CHAIN_TRIGGER_CARRIER_TAIL_HEIGHT / 2
            - CHAIN_TRIGGER_MAGNET_POCKET_DEPTH;
    snake_in_rear()
        place_from_to(p0, p1, [0, 0, 1])
            translate([
                CHAIN_TRIGGER_CARRIER_MAGNET_CENTER_ALONG_LINK,
                magnet_center_y,
                magnet_start_normal
            ])
                color("#5b6670")
                    cylinder(
                        d = CHAIN_TRIGGER_MAGNET_D,
                        h = CHAIN_TRIGGER_MAGNET_L,
                        $fn = 64
                    );
}

module clutch_trigger_connecting_pins_reference() {
    // Existing purchased 03C extended connecting pins: two grooves are
    // retained by the two separate U clips; +P/2 places the pin centers on
    // p0 and p1 exactly.
    p0 = snake_pins()[CHAIN_TRIGGER_MAGNET_SEGMENT_INDEX];
    p1 = snake_pins()[(CHAIN_TRIGGER_MAGNET_SEGMENT_INDEX + 1) % len(snake_pins())];
    snake_in_rear()
        place_from_to(p0, p1, [0, 0, 1])
            translate([P / 2, 0, 0])
                color("#b08d57")
                    chain_trigger_extended_connecting_pin_pair();
}

module clutch_trigger_retaining_clip_reference() {
    // Existing purchased U-shaped retaining clips in both extended-pin
    // grooves. They stay separate from the orange printed carrier.
    p0 = snake_pins()[CHAIN_TRIGGER_MAGNET_SEGMENT_INDEX];
    p1 = snake_pins()[(CHAIN_TRIGGER_MAGNET_SEGMENT_INDEX + 1) % len(snake_pins())];
    snake_in_rear()
        place_from_to(p0, p1, [0, 0, 1])
            translate([P / 2, 0, 0])
                color("#9aa7b6")
                    chain_trigger_extended_retaining_clips();
}

// Local diagnostic assembly for the 03C trigger carrier.  This intentionally
// reuses the same path/link modules as the full snake assembly; it is only a
// camera-friendly window around the mounted segment, not a second chain model.
module clutch_trigger_window_chain() {
    pins = snake_pins();
    n = len(pins);
    first = CHAIN_TRIGGER_MAGNET_SEGMENT_INDEX - 5;
    last = CHAIN_TRIGGER_MAGNET_SEGMENT_INDEX + 5;

    // The path points are authored in cabinet XZ.  Apply the same rear-hub
    // transform as every other chain component before placing this window;
    // otherwise the chain would be at local Y=0 while the carrier is at the
    // real rear datum CHAIN_Y.
    snake_in_rear() {
        // Keep enough adjacent links visible to prove that the two carrier
        // bores are on actual neighboring chain pins rather than floating
        // beside them.
        for (j = [first:last]) {
            i = (j + n) % n;
            place_from_to(pins[i], pins[(i + 1) % n], [0, 0, 1]) {
                if (i % 2 == 0)
                    color("#68717d") outer_plates();
                else
                    color("#7b8490") inner_plates();
            }
        }

        // Rollers are point features at the pin centers.  The two trigger
        // pins below replace only the ordinary pin solids; their rollers
        // remain real chain hardware and are therefore visible through the
        // carrier holes.
        for (j = [first:last]) {
            i = (j + n) % n;
            place_at_path_pin(pins, i)
                color("#d7dde3") roller_solid();
        }

        for (j = [first:last]) {
            i = (j + n) % n;
            if (i != CHAIN_TRIGGER_MAGNET_SEGMENT_INDEX
                && i != (CHAIN_TRIGGER_MAGNET_SEGMENT_INDEX + 1) % n)
                place_at_path_pin(pins, i)
                    color("#a9793d") pin_solid();
        }
    }
}

module pins_on_path(pins) {
    // Trigger pin positions are supplied by the separate purchased elongated
    // pin STL below; omit them here to avoid duplicate fake pins in assembly.
    n = len(pins);
    axis = [0, 0, 1];
    for (i = [0:n - 1])
        if (i != CHAIN_TRIGGER_MAGNET_SEGMENT_INDEX
            && i != (CHAIN_TRIGGER_MAGNET_SEGMENT_INDEX + 1) % n)
            place_from_to(pins[i], pins[(i + 1) % n], axis)
                pin_solid();
}

module bay_center_dots() {
    for (i = [0:N_COL - 1], j = [0:N_ROW - 1])
        translate([col_center_x(i), CHAIN_Y, row_center_z(j)])
            sphere(d = 2.2);
}

module emit_chain(name) {
    if (CHAIN_PART == "assembly" || CHAIN_PART == name)
        children();
}
//#endregion

//#region 公开 API
if (CHAIN_PART == "power_check") {
    // Diagnostic close-up only: the motor shaft enters the lower-right
    // return/tensioner D wheel and the Ω sleeve surrounds the motor body.
    // Include the one canonical cabinet-floor Boss set here so the four Ø5
    // posts can be inspected through the Ω-seat holes without loading a
    // second copy of the cabinet in the normal assembly tree.
    color("#6f8f9a", 0.92)
        cabinet_motor_mount_floor_seats_local();
    color("#e07a3d") place_geared(snake_drive_c())
        ch1_03c_sprocket(SPROCKET_TEETH);
    place_power_motor(snake_drive_c())
        pololu_micro_metal_motor_100_1_hp_6v_colored();
    color("#56616d", 0.28)
            place_power_motor_cover(snake_drive_c())
                ch1_03c_power_motor_cover();
}

if (CHAIN_PART == "mesh_check") {
    // Focused diagnostic: show only the real chain path and the one pointed
    // drive sprocket.  Keeping the motor carriage and tensioner out of this
    // branch makes bend interference visible instead of hiding it in a dense
    // assembly preview.
    color("#8A919C") snake_in_rear()
        plates_on_path(snake_pins());
    color("#E8EDF2") snake_in_rear()
        rollers_on_path(snake_pins());
    color("#B08D57") snake_in_rear()
        pins_on_path(snake_pins());
    clutch_trigger_connecting_pins_reference();
    clutch_trigger_retaining_clip_reference();
    color("#5b9fd6") place_geared(snake_drive_c())
        ch1_03c_sprocket(SPROCKET_TEETH);
}

if (CHAIN_PART == "trigger_assembly") {
    // Direct, local view of the installed carrier.  The chain is the same
    // path used by the full assembly; all four trigger components follow the
    // same segment frame and are shown in their actual mounted relationship.
    clutch_trigger_window_chain();
    clutch_trigger_carrier_reference();
    clutch_trigger_connecting_pins_reference();
    clutch_trigger_retaining_clip_reference();
    clutch_trigger_magnet_reference();
}

if (CHAIN_PART == "assembly") {
    %cabinet_shell();
    %drawer_ghosts();
    color("#ff4d4d", 0.9) bay_center_dots();
}

emit_chain("plates") {
    if (CHAIN_PART == "assembly")
        color("#8A919C") snake_in_rear()
            plates_on_path(snake_pins());
    else
        snake_in_rear() plates_on_path(snake_pins());
}
emit_chain("rollers") {
    if (CHAIN_PART == "assembly") color("#E8EDF2") snake_in_rear() rollers_on_path(snake_pins());
    else snake_in_rear() rollers_on_path(snake_pins());
}
emit_chain("pins") {
    if (CHAIN_PART == "assembly") color("#B08D57") snake_in_rear() pins_on_path(snake_pins());
    else snake_in_rear() pins_on_path(snake_pins());
}
emit_chain("sprockets") {
    if (CHAIN_PART == "assembly") {
        color("#5b9fd6") place_geared(snake_drive_c())
            ch1_03c_sprocket(SPROCKET_TEETH);
    } else {
        rear_sprockets();
    }
}
emit_chain("idlers") {
    if (CHAIN_PART == "assembly") color("#7dcc4a") rear_guide_idlers();
    else rear_guide_idlers();
}
emit_chain("bearings") {
    if (CHAIN_PART == "assembly") color("#b9c2ca") rear_bearing_visuals();
    else rear_bearing_visuals();
}
emit_chain("idler_axles") {
    if (CHAIN_PART == "assembly") rear_idler_axles();
    else rear_idler_axles();
}
emit_chain("clutch_trigger_carrier") {
    clutch_trigger_carrier_reference();
}
emit_chain("clutch_trigger_magnet") {
    clutch_trigger_magnet_reference();
}
emit_chain("clutch_trigger_connecting_pins") {
    clutch_trigger_connecting_pins_reference();
}
emit_chain("clutch_trigger_retaining_clip") {
    clutch_trigger_retaining_clip_reference();
}
emit_chain("motor") {
    if (CHAIN_PART == "assembly")
        place_power_motor(snake_drive_c())
            pololu_micro_metal_motor_100_1_hp_6v_body_colored();
    else
        place_power_motor(snake_drive_c())
            pololu_micro_metal_motor_100_1_hp_6v_body();
}
emit_chain("motor_shaft") {
    if (CHAIN_PART == "assembly")
        place_power_motor(snake_drive_c())
            color("#d6d9dc") d_shaft();
    else
        place_power_motor(snake_drive_c()) d_shaft();
}
emit_chain("motor_cover") {
    if (CHAIN_PART == "assembly")
        color("#56616d", 0.92)
            place_power_motor_cover(snake_drive_c())
                ch1_03c_power_motor_cover();
    else
        place_power_motor_cover(snake_drive_c())
            ch1_03c_power_motor_cover();
}
emit_chain("motor_spring_hardware") {
    // Four purchased spring/screw sets sit on the four moving-seat holes.
    // They are kept as one assembly part so the tree has no duplicate copy;
    // the printed cabinet bosses and Omega cover remain their own real parts.
    if (CHAIN_PART == "assembly")
        color("#c9a227", 0.95)
            cabinet_motor_mount_spring_hardware_local();
    else
        cabinet_motor_mount_spring_hardware_local();
}
//#endregion

//#region 视图层
// 预览用 CHAIN_PART=assembly；power_check 仅用于近距离确认动力轮、电机轴和固定罩的相对位置。
// 链条外购件分 plates / rollers / pins 导出。
//#endregion

//#region 业务逻辑
// 闭环按真实节距闭合；底端张紧轮吃掉余量。长于 210L×1 m SKU，只做后仓走线可视化。
// 红点是每格矩形中心；水平段节圆线必须穿过这些点。
// 蓝色 snake_drive_c() 背面右下/正面左下 12T 承接 D 轴动力，并在轮后接入真实 Pololu 1101 电机模型与贴合电机外形、下向固定的 Ω 夹套；
// 全部 9 个绿色固定导向位统一使用小尺寸 8T 钝齿轴承轮，路径与轮心由求解器
// 按 8T 节圆重算；并显示独立的 3×6×2 轴承。所有导向轮不再使用蓝色尖齿外形。
// 所有轮子安装面翻转 180°。
// 蛇链电机 Ω 套的四个底部固定孔对应柜底四个独立圆形承托/限位基台，
// 每孔向上套入 Ø5、柱段高 12 mm 的实体导向柱；硬弹簧套在导向柱外，M3 大蘑菇头螺钉从上向下拧入柱顶盲孔，
// 这组采购件单独作为 motor_spring_hardware 显示，不与柜体或固定套合并。
// 链条不再叠加旧的高亮接头、加长离合座或 681 随动件；
// 触发件改为一套双销侧挂载架：真实 03C 链节保持原节距，打印载架只承接
// M5 磁铁，触发位置使用两根加长钢销，载架本体不是链条承力替代件。
// 电机本体固定，独立 D 输出轴与动力轮 1:1 转动。
//#endregion

//#region 方法/工具
// 导出: -D CHAIN_PART='"plates"' / '"rollers"' / '"pins"' / '"sprockets"' / '"idlers"' / '"bearings"' / '"idler_axles"' / '"clutch_trigger_carrier"' / '"clutch_trigger_magnet"' / '"motor"' / '"motor_shaft"' / '"motor_cover"' / '"motor_spring_hardware"'
// 检查视图: -D CHAIN_PART='"power_check"'。
//#endregion

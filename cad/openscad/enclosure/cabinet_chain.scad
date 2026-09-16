// Mechanical contract
// process: assembly visualization — one 12T D-shaft drive sprocket; all other wheels are blunt bearing idlers
// material: pointed drive sprocket resin/PETG TBD; chain carbon steel 03C; blunt idlers PETG
// parting_plane: n/a for chain; cabinet back face remains Y = D
// opening_direction: n/a
// fastener: rear-view lower-right snake_drive_c() sprocket uses the 3 mm D-shaft; other wheels use 3 mm round bearing seats; the motor follows a rounded rectangular Ω clamp with two short outward bottom seats and downward Y-axis fixing holes, and is pressed in the former tensioner slot by a spring screw
// seal: n/a
// print_orientation: sprocket hub down; do not 3D-print the chain
// units: mm
// note: 5x5 row-major snake through every bay center; rear-view right return; the only snake motor is at the lower-right return/tensioner position (snake_drive_c()); all wheels are face-flipped; bearings are separate display/purchase geometry

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
use <../parts/ch1_03c_connecting_link_params.scad>
use <../parts/ch1_03c_extended_link_params.scad>
use <../parts/motor_pololu_micro_metal_100_1_hp_6v.scad>
use <../parts/motor_pololu_mount_cover.scad>
//#endregion

//#region 常量/配置
$fa = 8;
$fs = 0.22;
CHAIN_Y = MOTOR_MOUNT_CHAIN_Y;
CONNECTOR_LINK_INDEX = 20;       // 顶部直线段上的一节；不放在转向轮上
CONNECTOR_HIGHLIGHT = "#ff2fd0";
CLUTCH_CONNECTOR_LINK_INDEX = 140; // 中部第三层横直段上的一节；避开转向轮
CLUTCH_CONNECTOR_HIGHLIGHT = "#00d9ff";
// 方案 1：每个抽屉位置一组同轴的常转输入轮与受力输出轮；两张狗牙面
// 默认轴向留 2.6 mm，只有停稳后的拨叉把目标输出狗牙推过去才闭合。
// These are retained as standalone diagnostic/export parts, but the old
// scheme is deliberately absent from the canonical world assembly.  The
// current drawer drive is the separate Y-spline/HTD belt system; keeping this
// switch here prevents an old diagnostic wheel pair from being mistaken for
// the current clutch while preserving every source and STL entry.
SHOW_SCHEME1_IN_ASSEMBLY = is_undef(SHOW_SCHEME1_IN_ASSEMBLY)
    ? false
    : SHOW_SCHEME1_IN_ASSEMBLY;
SCHEME1_POWER_Y_OFFSET = -5.20;
SCHEME1_OUTPUT_Y_OFFSET = 5.20;
SCHEME1_DOG_INPUT_Y_OFFSET = -1.80;
SCHEME1_DOG_OUTPUT_Y_OFFSET = 1.80;
SCHEME1_DOG_T = 1.00;
SCHEME1_DOG_OD = 9.00;
SCHEME1_DOG_BORE_D = 3.40;
SCHEME1_DOG_LUG_W = 2.00;
SCHEME1_DOG_LUG_H = 1.60;
SCHEME1_SELECTOR_HIGHLIGHT = "#72e06a";
// 加长销模型的固定头内侧面是局部 Y=0；把它移到链条后侧外板面，
// 销杆沿局部 +Y 经过链板并伸向前方，拨叉平台/离合座因此朝前。
CLUTCH_CONNECTOR_PIN_FACE_OFFSET = -outer_face;
//#endregion

//#region 模型/类型
// 销轴路径在 cabinet_chain_path.scad；本文件只做后仓装配。
//#endregion

//#region 私有成员
echo("snake_pins", len(snake_pins()), "length_mm", len(snake_pins()) * P);
echo("snake_drive", snake_drive_c(), "upper_guide", power_c(), "entry", entry_c(), "service_return", drive_c(), "tensioner", ten_path_c(), "ten_z", TEN_Z);

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

module scheme1_place_y(c, y) {
    translate([c[0], y, c[1]])
        rotate([90, 0, 0])
            children();
}

function scheme1_station_centers() = [
    for (j = [0:N_ROW - 1], i = [0:N_COL - 1])
        [col_center_x(i), row_center_z(j), 0]
];

function scheme1_selector_center() = [
    col_center_x(0),
    row_center_z(N_ROW - 1),
    0
];

module scheme1_axis_cylinder(d, h, y) {
    translate([0, y, 0])
        rotate([90, 0, 0])
            cylinder(d = d, h = h, center = true);
}

module scheme1_dog_ring() {
    union() {
        difference() {
            cylinder(d = SCHEME1_DOG_OD, h = SCHEME1_DOG_T, center = true);
            cylinder(d = SCHEME1_DOG_BORE_D, h = SCHEME1_DOG_T + 2 * EPS, center = true);
        }
        // 四个轴向端面凸齿；两组凸齿相对，默认留出开口间隙。
        for (a = [0:3])
            rotate([0, 0, a * 90])
                translate([SCHEME1_DOG_OD / 2 - SCHEME1_DOG_LUG_W / 2, 0, 0])
                    cube([
                        SCHEME1_DOG_LUG_W,
                        SCHEME1_DOG_LUG_H,
                        SCHEME1_DOG_T
                    ], center = true);
    }
}

module scheme1_dog_carrier(y_gear, y_dog) {
    scheme1_axis_cylinder(
        5.30,
        abs(y_gear - y_dog),
        (y_gear + y_dog) / 2
    );
}

module scheme1_power_wheels() {
    for (c = scheme1_station_centers())
        scheme1_place_y(c, CHAIN_Y + SCHEME1_POWER_Y_OFFSET)
            ch1_03c_sprocket(SPROCKET_TEETH);
}

module scheme1_output_wheels() {
    for (c = scheme1_station_centers())
        scheme1_place_y(c, CHAIN_Y + SCHEME1_OUTPUT_Y_OFFSET)
            rotate([180, 0, 0])
                ch1_03c_bearing_sprocket(SPROCKET_TEETH);
}

module scheme1_clutch_faces() {
    for (c = scheme1_station_centers()) {
        translate([c[0], 0, c[1]]) {
            scheme1_dog_carrier(
                CHAIN_Y + SCHEME1_POWER_Y_OFFSET,
                CHAIN_Y + SCHEME1_DOG_INPUT_Y_OFFSET
            );
            scheme1_dog_carrier(
                CHAIN_Y + SCHEME1_OUTPUT_Y_OFFSET,
                CHAIN_Y + SCHEME1_DOG_OUTPUT_Y_OFFSET
            );
        }
        scheme1_place_y(c, CHAIN_Y + SCHEME1_DOG_INPUT_Y_OFFSET)
            scheme1_dog_ring();
        scheme1_place_y(c, CHAIN_Y + SCHEME1_DOG_OUTPUT_Y_OFFSET)
            scheme1_dog_ring();
    }
}

module scheme1_bearings() {
    for (c = scheme1_station_centers())
        scheme1_place_y(c, CHAIN_Y + SCHEME1_OUTPUT_Y_OFFSET)
            ch1_03c_bearing_visual();
}

module scheme1_selector() {
    c = scheme1_selector_center();
    // 8T 选择轮固定在拨叉本体中；它随链条走到哪个格口，就对应哪个离合站。
    scheme1_place_y(c, CHAIN_Y)
        rotate([180, 0, 0])
            ch1_03c_bearing_blunt_idler(BLUNT_TEETH);
    // 两个叉指伸向输出侧狗牙，只有停稳后才会把目标狗牙推过开口间隙。
    color(SCHEME1_SELECTOR_HIGHLIGHT)
        translate([c[0], CHAIN_Y + 2.35, c[1]]) {
            for (x = [-4.0, 4.0])
                translate([x, 0, 0])
                    cube([1.40, 4.70, 2.40], center = true);
            cube([9.40, 1.40, 2.40], center = true);
            translate([0, -2.10, 0])
                cube([6.80, 1.80, 3.20], center = true);
        }
}

module rear_blunt_idlers() {
    for (c = blunt_centers())
        place_geared(c) ch1_03c_bearing_blunt_idler(BLUNT_TEETH);
}

module rear_guide_idlers() {
    // 非动力位沿用 12T 节圆，但改为绿色钝齿外形；这样链条仍走原来的
    // 12T 圆弧/切线，不会因为把 12T 硬换成 8T 而脱离节距，同时消除尖齿
    // 在层间切换时与绿色导向轮的外包络干涉。
    for (c = concat([entry_c(), power_c()], right_turn_sprockets_without_power(), left_turn_sprockets(), [drive_c()]))
        place_geared(c) ch1_03c_bearing_blunt_idler(SPROCKET_TEETH);
    rear_blunt_idlers();
}

module rear_bearing_visuals() {
    // 与轴承版齿轮一一对应；旧高 X 转向位 power_c() 现在也是普通轴承轮，
    // 右下 snake_drive_c() 才是 D 轴动力轮。
    for (c = concat([entry_c(), power_c()], right_turn_sprockets_without_power(), left_turn_sprockets(), [drive_c()]))
        place_geared(c) ch1_03c_bearing_visual();
    for (c = blunt_centers())
        place_geared(c) ch1_03c_bearing_visual();
}

module rear_sprockets() {
    // 右下回程/张紧位承接唯一 D 轴动力；所有其它位置都在 rear_guide_idlers() 中。
    place_geared(snake_drive_c()) ch1_03c_sprocket(SPROCKET_TEETH);
}

module connector_plain_plate() {
    // The clip is on the +Y outer side of the pink connecting link.  The
    // opposite side is a normal single outer 8-shaped plate, not a second
    // clip and not a solid replacement link.  chain_plate() uses the generic
    // 0..P pin datum, while the connecting-pin/clip pair uses -P/2..+P/2;
    // re-center the generic plate before highlighted_connector() applies its
    // +P/2 placement so all three features share p0/p1 exactly.
    translate([-P / 2, -(inner_width / 2 + T), 0])
        chain_plate(d2 + clearance);
}

module plates_on_path_with_connector_replacement(pins) {
    // Reserve the opposite-side plate at the pink connection position for
    // highlighted_connector().  Keeping it out of the base plates STL avoids
    // a coincident duplicate; the highlighted pink part supplies that plate.
    n = len(pins);
    axis = [0, 0, 1];
    for (i = [0:n - 1]) {
        place_from_to(pins[i], pins[(i + 1) % n], axis) {
            if (i == CONNECTOR_LINK_INDEX && i % 2 == 0)
                translate([0, inner_width / 2 + 2 * T, 0])
                    chain_plate(d2 + clearance);
            else if (i % 2 == 0)
                outer_plates();
            else
                inner_plates();
        }
    }
}

module highlighted_connector() {
    // 接头只替换这两个销位的普通销：链板保持原位，带槽双穿销和夹片
    // 必须共用普通销的中心线，不能再叠加一套外板。
    p0 = snake_pins()[CONNECTOR_LINK_INDEX];
    p1 = snake_pins()[(CONNECTOR_LINK_INDEX + 1) % len(snake_pins())];
    snake_in_rear()
        place_from_to(p0, p1, [0, 0, 1])
            translate([P / 2, 0, 0])
                color(CONNECTOR_HIGHLIGHT) {
                    ch1_03c_connecting_pin_pair();
                    ch1_03c_retaining_clip();
                    connector_plain_plate();
                }
}

module highlighted_clutch_connector_bearing() {
    p0 = snake_pins()[CLUTCH_CONNECTOR_LINK_INDEX];
    p1 = snake_pins()[(CLUTCH_CONNECTOR_LINK_INDEX + 1) % len(snake_pins())];
    snake_in_rear()
        place_from_to(p0, p1, [0, 0, 1])
            translate([P / 2, CLUTCH_CONNECTOR_PIN_FACE_OFFSET, 0])
                ch1_03c_clutch_bearing_visual();
}

module highlighted_clutch_connector() {
    // 第二处接头仍复用原链板和原销中心，只替换两根普通销；加长销、双夹片和离合座
    // 共用这两个中心线。这里不再 mirror Y：局部 +Y 在 snake_in_rear() 中映射到柜体前方，
    // 所以加长部分和离合座面都朝前；平台内的 681 轴承轴向仍保持 Z（上下）。
    p0 = snake_pins()[CLUTCH_CONNECTOR_LINK_INDEX];
    p1 = snake_pins()[(CLUTCH_CONNECTOR_LINK_INDEX + 1) % len(snake_pins())];
    snake_in_rear()
        place_from_to(p0, p1, [0, 0, 1])
            translate([P / 2, CLUTCH_CONNECTOR_PIN_FACE_OFFSET, 0])
                color(CLUTCH_CONNECTOR_HIGHLIGHT) {
                    ch1_03c_extended_connecting_pin_pair();
                    ch1_03c_extended_retaining_clips();
                    ch1_03c_clutch_platform();
                    ch1_03c_clutch_bearing_retainer();
                }
}

module pins_on_path_without_connectors(pins) {
    // 从普通销集合中拿掉两处接头各自占用的两个销位，由两个高亮接头补回对应销。
    n = len(pins);
    axis = [0, 0, 1];
    connector_b = (CONNECTOR_LINK_INDEX + 1) % n;
    clutch_connector_b = (CLUTCH_CONNECTOR_LINK_INDEX + 1) % n;
    for (i = [0:n - 1])
        if (
            i != CONNECTOR_LINK_INDEX
            && i != connector_b
            && i != CLUTCH_CONNECTOR_LINK_INDEX
            && i != clutch_connector_b
        )
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
        plates_on_path_with_connector_replacement(snake_pins());
    color("#E8EDF2") snake_in_rear()
        rollers_on_path(snake_pins());
    color("#B08D57") snake_in_rear()
        pins_on_path_without_connectors(snake_pins());
    color("#5b9fd6") place_geared(snake_drive_c())
        ch1_03c_sprocket(SPROCKET_TEETH);
}

if (CHAIN_PART == "assembly") {
    %cabinet_shell();
    %drawer_ghosts();
    color("#ff4d4d", 0.9) bay_center_dots();
}

emit_chain("plates") {
    if (CHAIN_PART == "assembly")
        color("#8A919C") snake_in_rear()
            plates_on_path_with_connector_replacement(snake_pins());
    else
        snake_in_rear() plates_on_path_with_connector_replacement(snake_pins());
}
emit_chain("rollers") {
    if (CHAIN_PART == "assembly") color("#E8EDF2") snake_in_rear() rollers_on_path(snake_pins());
    else snake_in_rear() rollers_on_path(snake_pins());
}
emit_chain("pins") {
    if (CHAIN_PART == "assembly") color("#B08D57") snake_in_rear() pins_on_path_without_connectors(snake_pins());
    else snake_in_rear() pins_on_path_without_connectors(snake_pins());
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
emit_chain("motor_tensioner") {
    // Legacy centerline tensioner hardware is kept as a standalone source part
    // for reference.  The current world uses the four-hole Omega motor seat;
    // the old bolt/spring assembly is hidden from the default preview manifest
    // until it is redesigned around that seat instead of crossing the drive wheel.
    if (CHAIN_PART == "motor_tensioner")
        tensioner_hardware();
}
emit_chain("connector") {
    highlighted_connector();
}
emit_chain("clutch_connector") {
    highlighted_clutch_connector();
}
emit_chain("clutch_bearing") {
    // Separate from the cyan structural highlight so the purchased bearing
    // is visibly silver in the assembly and follows the connector as one part.
    if (CHAIN_PART == "assembly")
        color("#cfd4da") highlighted_clutch_connector_bearing();
    else
        highlighted_clutch_connector_bearing();
}
emit_chain("scheme1_power_wheels") {
    if (CHAIN_PART == "assembly") {
        if (SHOW_SCHEME1_IN_ASSEMBLY)
            color("#e6a23c") scheme1_power_wheels();
    } else {
        scheme1_power_wheels();
    }
}
emit_chain("scheme1_output_wheels") {
    if (CHAIN_PART == "assembly") {
        if (SHOW_SCHEME1_IN_ASSEMBLY)
            color("#5b9fd6") scheme1_output_wheels();
    } else {
        scheme1_output_wheels();
    }
}
emit_chain("scheme1_clutch_faces") {
    if (CHAIN_PART == "assembly") {
        if (SHOW_SCHEME1_IN_ASSEMBLY)
            color("#f0c36a") scheme1_clutch_faces();
    } else {
        scheme1_clutch_faces();
    }
}
emit_chain("scheme1_bearings") {
    if (CHAIN_PART == "assembly") {
        if (SHOW_SCHEME1_IN_ASSEMBLY)
            color("#cfd4da") scheme1_bearings();
    } else {
        scheme1_bearings();
    }
}
emit_chain("scheme1_selector") {
    if (CHAIN_PART == "assembly") {
        if (SHOW_SCHEME1_IN_ASSEMBLY)
            color(SCHEME1_SELECTOR_HIGHLIGHT) scheme1_selector();
    } else {
        scheme1_selector();
    }
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
// 其它 7 个 12T 转向/回程位全部是绿色 12T 钝齿轴承导向轮；5 个绿色 8T 平移轮也保留为轴承版，
// 并显示独立的 3×6×2 轴承。所有导向轮不再使用蓝色尖齿外形。
// 所有轮子安装面翻转 180°。
// 蛇链电机 Ω 套的四个底部固定孔对应柜底两条 4 mm 一级台阶导轨，
// 每孔向上长 20 mm 空心导向柱；硬弹簧套在导向柱外，大蘑菇头螺钉从上向下压紧，
// 这组采购件单独作为 motor_spring_hardware 显示，不与柜体或固定套合并。
// 高亮 CONNECTOR_LINK_INDEX 节为普通 03C 接头：普通双销换成带槽销和夹片，
// 夹片对侧由高亮零件补一块普通单面 8 字外链板；CLUTCH_CONNECTOR_LINK_INDEX 节为加长接头，
// 保持原链板并加装双夹片、前向离合座；681 轴承单独导出为银色随动零件。
// 两个接头以及单独轴承都会随链条运动；电机本体固定，独立 D 输出轴与动力轮 1:1 转动。
// 旧方案 1 的输入/输出轮、狗牙面、轴承和选择轮保留为独立诊断输出，
// 但默认不进入 canonical world assembly；SHOW_SCHEME1_IN_ASSEMBLY=true
// 才会把它们重新放回总装配。
//#endregion

//#region 方法/工具
// 导出: -D CHAIN_PART='"plates"' / '"rollers"' / '"pins"' / '"sprockets"' / '"idlers"' / '"bearings"' / '"motor"' / '"motor_shaft"' / '"motor_cover"' / '"motor_spring_hardware"' / '"connector"' / '"clutch_connector"' / '"clutch_bearing"' / '"scheme1_power_wheels"' / '"scheme1_output_wheels"' / '"scheme1_clutch_faces"' / '"scheme1_bearings"' / '"scheme1_selector"'
// 检查视图: -D CHAIN_PART='"power_check"'。
//#endregion

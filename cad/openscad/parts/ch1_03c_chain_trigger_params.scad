// CH1 03C 蛇链触发磁铁侧挂件参数真值源
// 单位：mm。打印件是一个侧挂的一体式磁铁座；真实 03C 钢链仍承担链条拉力。

include <../ch1_03c_params.scad>
include <ch1_03c_connecting_link_params.scad>

// 触发点仍落在中心服务直线段；两根加长穿销占据相邻两个销位。
CHAIN_TRIGGER_SEGMENT_INDEX = 182;

// 与中心离合输入套筒使用同规格的 M5 圆柱磁铁。为了使新磁铁的
// 工作上沿保持旧 Ø2 参考件的高度，增大的半径全部向链条 Z−侧让出。
CHAIN_TRIGGER_MAGNET_DIAMETER = 5.00;
CHAIN_TRIGGER_MAGNET_LENGTH = 4.00; // M5×4；比 03C 总链宽薄，工作上沿保持不变
CHAIN_TRIGGER_MAGNET_POCKET_DIAMETER = 5.25;
CHAIN_TRIGGER_MAGNET_POCKET_CLEARANCE =
    (CHAIN_TRIGGER_MAGNET_POCKET_DIAMETER - CHAIN_TRIGGER_MAGNET_DIAMETER) / 2;
// The carrier is now exactly as thick as the M5×4 magnet in the normal
// direction. Magnet retention is intentionally left to the user's screw;
// there is no printed lip or bottom wall in this version.
CHAIN_TRIGGER_MAGNET_RETENTION_LIP = 0.00;
CHAIN_TRIGGER_MAGNET_BACK_WALL = 0.00;
// The magnet seat is a through-seat: its depth is exactly the magnet length.
CHAIN_TRIGGER_MAGNET_POCKET_DEPTH =
    CHAIN_TRIGGER_MAGNET_RETENTION_LIP + CHAIN_TRIGGER_MAGNET_LENGTH;

// 旧 Ø2 参考件的高度基准不再用于这个 M5 拖尾。新的装配基准是：
// 链条侧的 8 字形根部与左侧圆角矩形的水平中心线重合。
// 因此拖尾和磁铁孔都以同一个 local normal=0 中心线定位。
CHAIN_TRIGGER_MAGNET_REFERENCE_DIAMETER = 2.00;
CHAIN_TRIGGER_MAGNET_REFERENCE_NORMAL_OFFSET =
    (h2 - CHAIN_TRIGGER_MAGNET_REFERENCE_DIAMETER) / 2;
CHAIN_TRIGGER_MAGNET_NORMAL_OFFSET = 0.00;
CHAIN_TRIGGER_MAGNET_TOP_CLEARANCE = 0.00;

// 打印件位于链条一侧。根部完整复刻一节 03C 外链板的双孔关系，
// 再沿行进方向的后方做一个左端圆角的矩形拖尾；矩形与根部相交为一个实体，
// 不是另一个要装配的盒子。
CHAIN_TRIGGER_CARRIER_PIN_CLEARANCE = 0.18;
CHAIN_TRIGGER_CARRIER_PIN_HOLE_DIAMETER =
    d2 + CHAIN_TRIGGER_CARRIER_PIN_CLEARANCE;
// 真实配件：第一道卡槽保留原连接节位置，第二道卡槽在后面承托侧挂件。
// 黄色打印磁台沿穿销轴（STL-Y）冻结为 10 mm；根部的实际厚度不再拿磁铁
// 长度代替，而是由两片 U 形卡的内侧净距反推。两卡之间的名义净距为 10 mm，
// 卡片厚度为 0.60 mm，因此两道卡槽中心距必须是 10.60 mm。
CHAIN_TRIGGER_EXTENDED_PIN_BASE_LENGTH = CONNECTING_PIN_LENGTH;
CHAIN_TRIGGER_EXTENDED_FIRST_CLIP_Y =
    CHAIN_TRIGGER_EXTENDED_PIN_BASE_LENGTH - CONNECTING_PIN_GROOVE_FROM_TIP;
CHAIN_TRIGGER_EXTENDED_NET_PLATFORM_CLEAR = 10.00;
CHAIN_TRIGGER_EXTENDED_SECOND_CLIP_Y =
    CHAIN_TRIGGER_EXTENDED_FIRST_CLIP_Y
        + CHAIN_TRIGGER_EXTENDED_NET_PLATFORM_CLEAR
        + RETAINING_CLIP_T;
CHAIN_TRIGGER_EXTENDED_PIN_LENGTH =
    CHAIN_TRIGGER_EXTENDED_SECOND_CLIP_Y + CONNECTING_PIN_GROOVE_FROM_TIP;
CHAIN_TRIGGER_CARRIER_PIN_LENGTH = CHAIN_TRIGGER_EXTENDED_PIN_LENGTH;
CHAIN_TRIGGER_CARRIER_RETAINING_CLIP_THICKNESS = RETAINING_CLIP_T;
// 8 字根部的轴向厚度由两道 U 卡的内侧净距计算，并完整占满该净距。
// 这样两根长销穿过根部后，根部两端分别贴住两道卡的内侧，不能沿销轴窜动。
// 整个“双销 + 载架 + 双 U 卡”刚性组件沿 STL-Y 向链条外板收进 3.40 mm，
// 让链条出板后只保留约 0.3 mm 的卡子装配间隙，不再露出长段光杆。
// SCAD 路径局部轴向与最终 STL-Y 方向相反，因此各模块使用该值做局部 Y 减法。
CHAIN_TRIGGER_CARRIER_AXIAL_SHIFT_TOWARD_CHAIN = 3.40;
CHAIN_TRIGGER_CARRIER_ROOT_AXIAL_START_Y =
    CHAIN_TRIGGER_EXTENDED_FIRST_CLIP_Y
        + CHAIN_TRIGGER_CARRIER_RETAINING_CLIP_THICKNESS / 2;
CHAIN_TRIGGER_CARRIER_ROOT_AXIAL_END_Y =
    CHAIN_TRIGGER_EXTENDED_SECOND_CLIP_Y
        - CHAIN_TRIGGER_CARRIER_RETAINING_CLIP_THICKNESS / 2;
CHAIN_TRIGGER_CARRIER_ROOT_AXIAL_CENTER_Y =
    (CHAIN_TRIGGER_CARRIER_ROOT_AXIAL_START_Y
        + CHAIN_TRIGGER_CARRIER_ROOT_AXIAL_END_Y) / 2;
CHAIN_TRIGGER_CARRIER_PLATE_THICKNESS =
    CHAIN_TRIGGER_CARRIER_ROOT_AXIAL_END_Y
        - CHAIN_TRIGGER_CARRIER_ROOT_AXIAL_START_Y;
CHAIN_TRIGGER_CARRIER_HARDWARE_MODE =
    "purchased-03C-extended-pin-pair-plus-two-U-clips";
CHAIN_TRIGGER_CARRIER_CONNECTING_PINS_PART =
    "cabinet-chain/cabinet_chain_clutch_trigger_connecting_pins";
CHAIN_TRIGGER_CARRIER_RETAINING_CLIP_PART =
    "cabinet-chain/cabinet_chain_clutch_trigger_retaining_clip";

// 磁铁矩形座按用户给的 SketchUp 参考布置：双孔“8”字根部在链节侧，
// 矩形磁台从第二个（+X 侧）销孔向外伸出；与根部连接的一端保持平齐，
// 外侧末端做圆角。不能把矩形座放到第一个销孔的 -X 侧。
CHAIN_TRIGGER_CARRIER_TAIL_WALL = 0.80;
CHAIN_TRIGGER_CARRIER_TAIL_LENGTH = 11.00;
CHAIN_TRIGGER_CARRIER_TAIL_HEIGHT = CHAIN_TRIGGER_MAGNET_LENGTH;
CHAIN_TRIGGER_CARRIER_TAIL_RADIUS = 1.20;
// 轴向是两根加长穿销的 STL-Y。矩形座沿该轴向同样为 10 mm，并和“8”字根部
// 共用由两道 U 卡内侧定义的捕获厚度；磁铁的 STL-Z 长度不能决定这个 Y 厚度。
CHAIN_TRIGGER_CARRIER_TAIL_DEPTH = CHAIN_TRIGGER_CARRIER_PLATE_THICKNESS;
// 收紧拖尾根部与两根销轴所在“8”字根部的实体搭接。原 0.80 mm
// 只是在边缘擦到，预览中会像拖尾脱离销轴而下坠；增加 0.80 mm
// 后，在第二销轴附近形成连续承力过渡，同时保留足够的拖尾长度。
CHAIN_TRIGGER_CARRIER_TAIL_ROOT_OVERLAP_X = 1.60;
CHAIN_TRIGGER_CARRIER_TAIL_ROOT_X =
    P - CHAIN_TRIGGER_CARRIER_TAIL_ROOT_OVERLAP_X;
CHAIN_TRIGGER_CARRIER_TAIL_X_MIN =
    CHAIN_TRIGGER_CARRIER_TAIL_ROOT_X;
CHAIN_TRIGGER_CARRIER_TAIL_X_MAX =
    CHAIN_TRIGGER_CARRIER_TAIL_ROOT_X + CHAIN_TRIGGER_CARRIER_TAIL_LENGTH;
// 8 字形根部的水平中心线就是 local normal=0；圆角矩形和 M5 贯通座
// 必须共用这条中心线，不能再用“磁铁上沿”反推拖尾位置。
CHAIN_TRIGGER_CARRIER_TAIL_CENTER_NORMAL = 0.00;
CHAIN_TRIGGER_CARRIER_TAIL_TOP_NORMAL =
    CHAIN_TRIGGER_CARRIER_TAIL_CENTER_NORMAL
        + CHAIN_TRIGGER_CARRIER_TAIL_HEIGHT / 2;
CHAIN_TRIGGER_CARRIER_MAGNET_CENTER_ALONG_LINK =
    CHAIN_TRIGGER_CARRIER_TAIL_X_MAX
        - CHAIN_TRIGGER_CARRIER_TAIL_WALL
        - CHAIN_TRIGGER_MAGNET_POCKET_DIAMETER / 2;
CHAIN_TRIGGER_CARRIER_MAGNET_CENTER_NORMAL =
    CHAIN_TRIGGER_CARRIER_TAIL_CENTER_NORMAL;

// 载架放在链条的 -Y 外侧；磁铁的工作面朝同一外侧，沿链条轴向布置。
CHAIN_TRIGGER_CARRIER_AXIAL_START_OFFSET =
    outer_face + CHAIN_TRIGGER_MAGNET_RETENTION_LIP;

// The two purchased connecting pins remain along STL Y. The trigger magnet
// is deliberately rotated 90 degrees into STL Z, so the plane containing
// the magnet axis and the two pin axes is perpendicular to the 8-shaped link
// face. Its pole faces are STL-Z−/Z+.
CHAIN_TRIGGER_CARRIER_MAGNET_AXIS = "stl-Z";
CHAIN_TRIGGER_CARRIER_MAGNET_CENTER_REFERENCE =
    "rear-rounded-tail-hole-center";

//#region 公开几何 API
// 这些模块只描述加长穿销和两道 U 卡的采购件参考几何，供装配文件引用。
// 载架本体在 cabinet_chain.scad 中与链节路径绑定，避免同一零件重复建模。
module chain_trigger_extended_pin_groove_cut(x, groove_y) {
    translate([
        x,
        groove_y - CONNECTING_PIN_GROOVE_W / 2,
        0
    ])
        rotate([-90, 0, 0])
            difference() {
                cylinder(
                    d = CONNECTING_PIN_SHAFT_D + 0.60,
                    h = CONNECTING_PIN_GROOVE_W
                );
                translate([0, 0, -eps])
                    cylinder(
                        d = CONNECTING_PIN_GROOVE_D,
                        h = CONNECTING_PIN_GROOVE_W + 2 * eps
                    );
            }
}

module chain_trigger_extended_pin_one(x) {
    translate([0, -CHAIN_TRIGGER_CARRIER_AXIAL_SHIFT_TOWARD_CHAIN, 0])
        difference() {
            union() {
                translate([x, 0, 0])
                    rotate([-90, 0, 0])
                        cylinder(
                            d = CONNECTING_PIN_SHAFT_D,
                            h = CHAIN_TRIGGER_EXTENDED_PIN_LENGTH
                        );
                translate([x, 0, 0])
                    rotate([-90, 0, 0])
                        cylinder(
                            d = CONNECTING_PIN_HEAD_D,
                            h = CONNECTING_PIN_HEAD_H
                        );
            }
            chain_trigger_extended_pin_groove_cut(
                x,
                CHAIN_TRIGGER_EXTENDED_FIRST_CLIP_Y
            );
            chain_trigger_extended_pin_groove_cut(
                x,
                CHAIN_TRIGGER_EXTENDED_SECOND_CLIP_Y
            );
        }
}

module chain_trigger_extended_connecting_pin_pair() {
    for (x = [-CONNECTING_PIN_PAIR_SPACING / 2,
              CONNECTING_PIN_PAIR_SPACING / 2])
        chain_trigger_extended_pin_one(x);
}

module chain_trigger_extended_retaining_clip_at(y) {
    translate([
        0,
        y - CHAIN_TRIGGER_CARRIER_AXIAL_SHIFT_TOWARD_CHAIN,
        0
    ])
        rotate([90, 0, 0])
            linear_extrude(
                height = RETAINING_CLIP_T,
                center = true,
                convexity = 6
            )
                retaining_clip_profile_2d();
}

module chain_trigger_extended_retaining_clips() {
    chain_trigger_extended_retaining_clip_at(
        CHAIN_TRIGGER_EXTENDED_FIRST_CLIP_Y
    );
    chain_trigger_extended_retaining_clip_at(
        CHAIN_TRIGGER_EXTENDED_SECOND_CLIP_Y
    );
}

// 这里的 local +X 是按用户参考图定义的“8”字根部之后：左端平齐搭接，
// 只有外侧右端做圆角。轮廓随后沿 local Y 挤出；磁铁孔从拖尾外侧
// normal+ 面开设，经过路径变换后导出 STL 的磁铁轴为 STL-Z。
module chain_trigger_rounded_right_rect_2d(x_min, x_max, h, r) {
    union() {
        translate([x_min, -h / 2])
            square([x_max - x_min - r, h]);
        hull() {
            translate([x_max - r, -h / 2 + r])
                circle(r = r, $fn = 32);
            translate([x_max - r, h / 2 - r])
                circle(r = r, $fn = 32);
        }
    }
}

module chain_trigger_tail_body() {
    tail_center_y =
        CHAIN_TRIGGER_CARRIER_ROOT_AXIAL_CENTER_Y
            - CHAIN_TRIGGER_CARRIER_AXIAL_SHIFT_TOWARD_CHAIN;
    tail_face_y =
        tail_center_y + CHAIN_TRIGGER_CARRIER_TAIL_DEPTH / 2;
    tail_top_normal =
        CHAIN_TRIGGER_CARRIER_TAIL_CENTER_NORMAL
            + CHAIN_TRIGGER_CARRIER_TAIL_HEIGHT / 2;
    difference() {
        translate([
            0,
            tail_face_y,
            CHAIN_TRIGGER_CARRIER_TAIL_CENTER_NORMAL
        ])
            rotate([90, 0, 0])
                linear_extrude(
                    height = CHAIN_TRIGGER_CARRIER_TAIL_DEPTH,
                    convexity = 8
                )
                    chain_trigger_rounded_right_rect_2d(
                        CHAIN_TRIGGER_CARRIER_TAIL_X_MIN,
                        CHAIN_TRIGGER_CARRIER_TAIL_X_MAX,
                        CHAIN_TRIGGER_CARRIER_TAIL_HEIGHT,
                        CHAIN_TRIGGER_CARRIER_TAIL_RADIUS
                    );

        // The rectangular tail starts just before the second (+X) pin so it
        // overlaps the 8-shaped root as one printed part. That overlap must
        // not fill the second pin bore: the same long pin passes through the
        // carrier and the chain link at this location.
        translate([
            P,
            tail_center_y - CHAIN_TRIGGER_CARRIER_TAIL_DEPTH / 2 - eps,
            0
        ])
            rotate([-90, 0, 0])
                cylinder(
                    d = CHAIN_TRIGGER_CARRIER_PIN_HOLE_DIAMETER,
                    h = CHAIN_TRIGGER_CARRIER_TAIL_DEPTH + 2 * eps,
                    $fn = 48
                );

        // 磁铁从拖尾的 normal+ 外侧沿 local +Z 开贯通座；螺丝固定由用户
        // 处理，Y 只负责把磁铁座放在拖尾轴向中心。
        translate([
            CHAIN_TRIGGER_CARRIER_MAGNET_CENTER_ALONG_LINK,
            tail_center_y,
            tail_top_normal - CHAIN_TRIGGER_MAGNET_POCKET_DEPTH - eps
        ])
            cylinder(
                d = CHAIN_TRIGGER_MAGNET_POCKET_DIAMETER,
                h = CHAIN_TRIGGER_MAGNET_POCKET_DEPTH + 2 * eps,
                $fn = 64
            );
    }
}
//#endregion

assert(abs(CHAIN_TRIGGER_EXTENDED_SECOND_CLIP_Y
        - CHAIN_TRIGGER_EXTENDED_FIRST_CLIP_Y
        - RETAINING_CLIP_T - CHAIN_TRIGGER_EXTENDED_NET_PLATFORM_CLEAR) < 0.001);
assert(abs(CHAIN_TRIGGER_CARRIER_PLATE_THICKNESS
        - CHAIN_TRIGGER_EXTENDED_NET_PLATFORM_CLEAR) < 0.001);
assert(CHAIN_TRIGGER_CARRIER_ROOT_AXIAL_START_Y
        > CHAIN_TRIGGER_EXTENDED_FIRST_CLIP_Y);
assert(CHAIN_TRIGGER_CARRIER_ROOT_AXIAL_END_Y
        < CHAIN_TRIGGER_EXTENDED_SECOND_CLIP_Y);
assert(CHAIN_TRIGGER_EXTENDED_PIN_LENGTH > CONNECTING_PIN_LENGTH);
assert(CHAIN_TRIGGER_CARRIER_TAIL_X_MIN > 0);
assert(CHAIN_TRIGGER_CARRIER_TAIL_X_MIN < P);
assert(CHAIN_TRIGGER_CARRIER_TAIL_X_MAX > P);
assert(CHAIN_TRIGGER_CARRIER_TAIL_X_MAX - P
        >= CHAIN_TRIGGER_CARRIER_TAIL_ROOT_OVERLAP_X);
assert(CHAIN_TRIGGER_CARRIER_TAIL_RADIUS < CHAIN_TRIGGER_CARRIER_TAIL_HEIGHT / 2);
assert(abs(CHAIN_TRIGGER_CARRIER_TAIL_DEPTH
        - CHAIN_TRIGGER_CARRIER_PLATE_THICKNESS) < 0.001);
assert(CHAIN_TRIGGER_CARRIER_TAIL_HEIGHT
        >= CHAIN_TRIGGER_MAGNET_POCKET_DEPTH
        + CHAIN_TRIGGER_MAGNET_BACK_WALL - 0.001);

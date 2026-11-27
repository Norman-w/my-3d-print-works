// 洗手盆下水管转接件
//
// 坐标约定：
//   z=0       下段入口，接收外径/大径约 51.2 mm 的外丝
//   +Z        上段入口，接收外径/大径约 35.7 mm 的外丝
//   两端均按“打印内螺纹接实物外螺纹”建模，默认右旋。
//
// 本模型使用连续 polyhedron 螺旋切削体，不把每一圈单独 union，避免
// 螺纹分段接缝导致的非流形边。所有尺寸单位为 mm。

$fn = 96;

// ---------- 打印与配合参数 ----------
slices_per_turn = 64;
radial_clearance = 0.25;       // 母牙相对实物外丝每侧径向余量
female_axial_clearance = 0.16; // 母沟相对外丝牙型的轴向余量，每侧
thread_root_embed = 0.18;      // 螺旋切削体向基础内孔的嵌入量
thread_cut_overrun = 0.15;     // 螺旋切削体越过母沟底的数值余量
thread_root_width_fraction = 0.72;
thread_crest_width = 0.18;     // 截顶宽；保留有限宽度，避免数学针尖
entry_extra_diameter = 0.80;   // 两端导入喇叭口额外直径
eps = 0.01;

// 仅用于生成剖切预览，不用于打印交付。可用 OpenSCAD -D 覆盖为 true。
preview_cutaway = is_undef(preview_cutaway) ? false : preview_cutaway;

// ---------- 上段：接收 35.7 / 35.0 外丝 ----------
top_male_major_d = 35.7;       // 外丝峰径/最大外径
top_male_root_d = 35.0;        // 外丝低洼处/根径
top_pitch = 22.6 / 10;         // 10 道纹路约 22.6 mm -> 2.26 mm
top_thread_turns = 15;         // 总计 15 道纹路
top_lead_length = 1.20;        // +Z 端入口导入长度
top_wall = 3.80;

// ---------- 下段：接收 51.2 / 50.0 外丝 ----------
lower_male_major_d = 51.2;     // 外丝尖端/最大外径
lower_male_root_d = 50.0;      // 外丝低洼处/根径
lower_pitch = 1.50;            // 用户给定的约 1.5 mm 齿距
lower_thread_turns = 16;       // 下段长度未给定，暂按 16 道 = 24 mm
lower_lead_length = 1.20;      // -Z 端入口导入长度
lower_wall = 4.20;

// ---------- 主体过渡 ----------
transition_length = 10.0;       // 拉长缩径段，降低薄肩处的应力集中
transition_profile_steps = 64;  // 连续外轮廓的离散精度

function female_minor_d(male_root_d) = male_root_d + 2 * radial_clearance;
function female_major_d(male_major_d) = male_major_d + 2 * radial_clearance;

top_female_minor_d = female_minor_d(top_male_root_d);
top_female_major_d = female_major_d(top_male_major_d);
top_thread_length = top_pitch * top_thread_turns;

lower_female_minor_d = female_minor_d(lower_male_root_d);
lower_female_major_d = female_major_d(lower_male_major_d);
lower_thread_length = lower_pitch * lower_thread_turns;

lower_section_height = lower_lead_length + lower_thread_length;
transition_z0 = lower_section_height;
transition_z1 = transition_z0 + transition_length;
top_thread_z0 = transition_z1;
top_thread_z1 = top_thread_z0 + top_thread_length;
total_height = top_thread_z1 + top_lead_length;

lower_outer_d = lower_female_major_d + 2 * lower_wall;
top_outer_d = top_female_major_d + 2 * top_wall;

assert(top_male_major_d > top_male_root_d, "上段外丝大径必须大于根径");
assert(lower_male_major_d > lower_male_root_d, "下段外丝大径必须大于根径");
assert(top_pitch > 0 && lower_pitch > 0, "螺距必须大于 0");
assert(top_thread_turns >= 1 && lower_thread_turns >= 1, "螺纹道数必须大于 0");
assert(top_wall > 1.5 && lower_wall > 1.5, "打印壁厚过小");
assert(transition_profile_steps >= 8, "过渡曲线采样点过少");

// 0 和 1 处导数都为 0，使曲线分别与下段、上段圆柱相切。
function smooth_transition(t) = (1 - cos(180 * t)) / 2;
function transition_radius(t) =
    lower_outer_d / 2
        + (top_outer_d / 2 - lower_outer_d / 2) * smooth_transition(t);

// profile 中的点为 [半径, 相对螺旋中心的 z 偏移]。
// 这是一个截顶三角形：两侧为斜面，顶端保留有限宽度以适配 FDM。
function thread_profile(male_major_d, male_root_d, pitch) =
    let(
        female_minor = female_minor_d(male_root_d),
        female_major = female_major_d(male_major_d),
        root_radius = female_minor / 2 - thread_root_embed,
        valley_radius = female_major / 2 + thread_cut_overrun,
        root_width = pitch * thread_root_width_fraction + 2 * female_axial_clearance,
        crest_width = min(thread_crest_width + 2 * female_axial_clearance,
                           root_width - 0.10)
    ) [
        [root_radius, -root_width / 2],
        [valley_radius, -crest_width / 2],
        [valley_radius, crest_width / 2],
        [root_radius, root_width / 2]
    ];

function reverse_indices(count) = [for (i = [count - 1 : -1 : 0]) i];
function end_indices(profile_count, section_count) =
    [for (i = [0 : profile_count - 1]) (section_count - 1) * profile_count + i];

function sweep_points(profile, section_count, z0, thread_length, turns, hand = 1, phase = 0) =
    [
        for (i = [0 : section_count - 1], p = profile)
            let(
                t = i / (section_count - 1),
                theta = phase + hand * 360 * turns * t,
                z = z0 + thread_length * t + p[1]
            ) [p[0] * cos(theta), p[0] * sin(theta), z]
    ];

function sweep_side_faces(profile_count, section_count) =
    [
        for (i = [0 : section_count - 2], j = [0 : profile_count - 1])
            [
                i * profile_count + j,
                i * profile_count + (j + 1) % profile_count,
                (i + 1) * profile_count + (j + 1) % profile_count,
                (i + 1) * profile_count + j
            ]
    ];

function sweep_faces(profile_count, section_count) = concat(
    sweep_side_faces(profile_count, section_count),
    [reverse_indices(profile_count)],
    [end_indices(profile_count, section_count)]
);

module helical_cut(profile, z0, thread_length, pitch, turns, hand = 1, phase = 0) {
    section_count = ceil(turns * slices_per_turn) + 1;
    polyhedron(
        points = sweep_points(profile, section_count, z0, thread_length, turns, hand, phase),
        faces = sweep_faces(len(profile), section_count),
        convexity = 10
    );
}

module internal_thread_cut(male_major_d, male_root_d, pitch, turns, z0, hand = 1, phase = 0) {
    helical_cut(
        thread_profile(male_major_d, male_root_d, pitch),
        z0,
        pitch * turns,
        pitch,
        turns,
        hand,
        phase
    );
}

module outer_body() {
    // 直接旋转连续的 r-z 外轮廓；这里没有额外贴上的环形加强件。
    rotate_extrude(convexity = 10)
        polygon(points = concat(
            [
                [0, 0],
                [lower_outer_d / 2, 0],
                [lower_outer_d / 2, transition_z0]
            ],
            [
                for (i = [1 : transition_profile_steps - 1])
                    let(t = i / transition_profile_steps)
                        [transition_radius(t),
                         transition_z0 + transition_length * t]
            ],
            [
                [top_outer_d / 2, transition_z1],
                [top_outer_d / 2, total_height],
                [0, total_height]
            ]
        ));
}

module inner_void() {
    union() {
        // 下端导入段：入口略放大，再收至母牙小径。
        translate([0, 0, -eps])
            cylinder(
                d1 = lower_female_major_d + entry_extra_diameter,
                d2 = lower_female_minor_d,
                h = lower_lead_length + eps
            );
        translate([0, 0, lower_lead_length - eps])
            cylinder(d = lower_female_minor_d, h = lower_thread_length + 2 * eps);

        // 中间过渡，同时保持通水通道连续。
        translate([0, 0, transition_z0 - eps])
            cylinder(
                d1 = lower_female_minor_d,
                d2 = top_female_minor_d,
                h = transition_length + 2 * eps
            );

        translate([0, 0, transition_z1 - eps])
            cylinder(d = top_female_minor_d, h = top_thread_length + 2 * eps);

        // 上端导入段，入口在 +Z 端。
        translate([0, 0, top_thread_z1 - eps])
            cylinder(
                d1 = top_female_minor_d,
                d2 = top_female_major_d + entry_extra_diameter,
                h = top_lead_length + 2 * eps
            );
    }
}

module adapter() {
    difference() {
        outer_body();
        inner_void();

        // 下段内螺纹：从 -Z 端接收 51.2 / 50.0 外丝。
        internal_thread_cut(
            lower_male_major_d,
            lower_male_root_d,
            lower_pitch,
            lower_thread_turns,
            lower_lead_length
        );

        // 上段内螺纹：从 +Z 端接收 35.7 / 35.0 外丝。
        internal_thread_cut(
            top_male_major_d,
            top_male_root_d,
            top_pitch,
            top_thread_turns,
            top_thread_z0
        );
    }
}

module model_output() {
    if (preview_cutaway) {
        // 保留 y<0 半体，露出上下两段内螺纹和中间通道。
        intersection() {
            adapter();
            translate([-100, -100, -eps])
                cube([200, 100, total_height + 2 * eps]);
        }
    } else {
        adapter();
    }
}

// 最终打印实体；剖切预览通过命令行 -D preview_cutaway=true 单独生成。
model_output();

echo(str("top pitch=", top_pitch, ", turns=", top_thread_turns,
         ", length=", top_thread_length));
echo(str("lower pitch=", lower_pitch, ", turns=", lower_thread_turns,
         ", length=", lower_thread_length));
echo(str("overall height=", total_height,
         ", lower outer diameter=", lower_outer_d,
         ", top outer diameter=", top_outer_d));

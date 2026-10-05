// 轴向牙型驱动的粗牙螺纹生成器。
//
// 与把径向—切向薄片直接 linear_extrude/twist 不同，这里先定义真正的
// 轴向剖面（半径 r × 轴向 z），再把这个牙型沿螺旋路径整体扫掠。
// 外螺纹和内螺纹沟槽共用相同的螺旋相位；内沟只增加轴向/径向配合余量。
// 适用于本项目的 FDM 粗牙旋入接口，不宣称符合某个 ISO/公制标准。

module tp_helical_thread(
    z0,
    length,
    base_r,
    height,
    pitch,
    root_width_fraction = 0.72,
    crest_width_fraction = 0.28,
    axial_clearance = 0,
    slices_per_turn = 64,
    root_overlap = 0.18
) {
    assert(length > 0);
    assert(base_r > 0);
    assert(height > 0);
    assert(pitch > 0);
    assert(root_width_fraction > crest_width_fraction);
    assert(crest_width_fraction > 0);
    assert(axial_clearance >= 0);

    // 先确定牙型：根部宽、两侧斜牙侧、平顶；不是尖针状三角片。
    nominal_root_half = pitch * root_width_fraction / 2;
    root_half = nominal_root_half + axial_clearance;
    crest_half = pitch * crest_width_fraction / 2 + axial_clearance;
    flank_half = crest_half + (root_half - crest_half) * 0.35;
    profile = [
        [base_r - root_overlap, -root_half],
        [base_r + height * 0.68, -flank_half],
        [base_r + height, -crest_half],
        [base_r + height, crest_half],
        [base_r + height * 0.68, flank_half],
        [base_r - root_overlap, root_half]
    ];

    // 再由牙距生成螺旋：公牙与母沟使用同一条中心螺旋相位。
    // 把所有截面合成为一个 polyhedron，而不是把每一小段分别 union；
    // 这样不会在段与段的接缝上留下非流形边。
    travel = length - 2 * nominal_root_half;
    steps = max(1, ceil(travel / pitch * slices_per_turn));
    n = len(profile);
    points = [
        for (i = [0:steps])
            for (p = profile)
                let(
                    theta = 360 * travel / pitch * i / steps,
                    center_z = z0 + nominal_root_half + travel * i / steps
                )
                [p[0] * cos(theta), p[0] * sin(theta), center_z + p[1]]
    ];
    start_cap = [[for (j = [n-1:-1:0]) j]];
    end_offset = steps * n;
    end_cap = [[for (j = [0:n-1]) end_offset + j]];
    side_faces = [
        for (i = [0:steps-1])
            for (j = [0:n-1])
                [
                    i * n + j,
                    i * n + (j + 1) % n,
                    (i + 1) * n + (j + 1) % n,
                    (i + 1) * n + j
                ]
    ];
    polyhedron(
        points = points,
        faces = concat(start_cap, end_cap, side_faces),
        convexity = 10
    );
}

# OpenSCAD 抽屉动力母线与离合机构

入口：`cad/openscad/enclosure/cabinet_clutch.scad`。

这套模型按背面观察的坐标实现：X 为左右列方向，Y 为箱体前后方向，Z 为上下行方向，单位为毫米。它独立复用 `cabinet_params.scad` 的 5×5 柜体和格口尺寸，不依赖 FreeCAD。

## 机构结构

- 当前先锁定左右两根边界轴：左侧是竖直 3 mm D 型轴，右侧张紧轴是 3 mm 圆轴；两根轴各有上下两个同步轮。左轴同步轮为 D 孔，右轴同步轮为圆孔，不能互换。每个同步轮齿圈上下各有一个限位法兰，法兰外径大于齿圈外径。
- 左侧服务区放置竖直朝上的 Pololu 电机包络、3 mm D 型输出轴和延长传动杆。
- 五个抽屉列各有一根贯穿上下的 D 型竖杆，并在上下两端配置 HTD3M 风格同步轮；最右侧再加一根双轮张紧轴。
- 每个格位的竖杆旁有连续齿杆。轴向为 Y 的上层啮合齿轮保持与齿杆关系；其下层为向下的狗牙面。
- 固定的向上狗牙面下方是同轴的取力同步轮：上层是向上的离合齿面，下层是同步轮。
- 后侧同步带沿 Y 传到抽屉前端；前端复合轮的下层是同步轮、上层是较大的 Z 轴齿轮，驱动抽屉底部的直线齿条。
- 右侧圆轴采用参考 SKP 的横向滑台：箱体后侧增加固定接收肋和承托台，固定槽有左右端块、侧壁和上方卡唇；移动台在槽内沿 X 滑动，卡唇限制 Z 向抬起、侧壁限制 Y 向窜动，后侧肋条和右侧肋条把固定槽锁到箱体背板/右侧壁。
- 滑台行程为 8 mm，默认 `TENSIONER_SCREW_OUT_MM = 4`。左端是大孔调节螺杆，螺杆向箱体外侧（+X）拧出时把移动台和右侧圆轴推向 +X；右端是小圆弹簧座，弹簧在移动台和右端止挡之间提供回压。移动台左右端同时保留对应的螺杆盲孔和弹簧盲孔。
- 弹簧把上层离合载架顶起。默认开合间隙是一个狗牙齿高的 2 倍（`CLUTCH_OPEN_GAP = 2 * CLUTCH_DOG_TOOTH_H`）。拨叉压下 T 头沉头螺丝，`ENGAGED=true` 时上层齿轮下移并让螺丝头接近上齿轮顶面。

## 可重复构建

```sh
./scripts/export_cabinet_clutch.sh
./scripts/render_cabinet_clutch.sh
```

可用 `OPENSCAD_BIN=/path/to/OpenSCAD` 指定 CLI，`SELECTED_COLUMN`、`SELECTED_ROW` 指定离合详图格位。

`CLUTCH_PART` 的入口值：

- `assembly`：柜体、抽屉透明包络和完整机构的装配视图；
- `power_bus`：左侧电机轴、五列竖杆、上下水平带和最右滑台张紧轴；
- `drawer_drive`：后前复合取力轮、Y 向同步带和抽屉底部齿条；
- `clutch`：全部格位离合；
- `clutch_detail`：单格离合详图，可配合 `CLUTCH_EXPLODE` 和 `ENGAGED`；
- `cabinet`：导出闭合薄壁柜体外壳以及与滑台相配的固定接收结构；装配图里的格栅和抽屉包络不进入该 STL。

逐件检查入口：当前轴阶段为 `left_d_axis`、`right_round_axis`、`side_axes`；滑台阶段为 `tensioner_slide`、`tensioner_base`、`tensioner_carriage`、`tensioner_spring`、`tensioner_screw`、`tensioner_receiver`；随后还有 `motor`、`column`、`vertical_rack`、`idler`、`bus_belt`、`upper_spur`、`upper_dog`、`lower_dog`、`rear_pulley`、`spring`、`screw`、`fork`、`drawer_belt`、`front_pulley`、`front_gear`、`drawer_rack`。这些入口都固定在同一组装坐标，检查通过后可以直接回放到 `assembly`。

## 参数与待确认项

默认值是可打印性优先的机构包络，不是最终承载规格：同步带按 3 mm 节距、20T，离合和齿条按 3 mm 节距，电机输出按 3 mm D 轴。长竖杆建议使用金属 D 杆；打印齿轮、弹簧、同步带和螺钉均需按实物尺寸复核。

滑台的尺寸按当前轴冻结：右轴为 Ø3 mm 圆轴，圆孔为 Ø3.24 mm；同步轮齿圈外径约 20.82 mm，上下限位法兰外径约 22.82 mm。滑台承托槽内宽 25.6 mm、内高在底面上方留 0.4 mm 运行间隙，固定槽总长约 42.41 mm。SKP 未提供可直接读取的精确标注，因此固定槽/滑台的具体壁厚、行程和孔径是以这些轴尺寸为约束的参数化适配值。

当前模型把“轴向 Y 的上层啮合齿轮”和“轴向 Z 的狗牙离合面”明确成同一个上层载架的两个功能面；后、前同步轮均为轴向 Z，带路在 XY 平面内沿 Y 方向走。当前齿形是可替换的参数化原型轮廓；如果确定使用专门的锥齿/端面齿，可只替换对应轮廓模块，不需要重做整体坐标布局。

STL 不包含单位、弹簧预紧力或切片参数。`cabinet_clutch_assembly.stl`、`cabinet_clutch_all_clutches.stl` 和 `cabinet_clutch_detail_*.stl` 是带有多个相互独立显示体的检查用总成，不能当作打印件；逐件候选 STL 才是后续切片检查的对象。导出后的 `output/inspection/cabinet-clutch/*.json` 只做包围盒、三角形和流形初筛；材料、层高、支撑、齿面强度和实际抽屉负载仍需在切片和首件装配中确认。

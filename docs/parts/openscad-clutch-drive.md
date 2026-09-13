# OpenSCAD 抽屉动力母线与离合机构

入口：`cad/openscad/enclosure/cabinet_clutch.scad`。

这套模型按正面观察的坐标实现：X=0 是从正面看的左侧，X=W 是从正面看的右侧；从背面看时左右顺序反过来。Y 为箱体前后方向，Z 为上下行方向，单位为毫米。它独立复用 `cabinet_params.scad` 的 5×5 柜体和格口尺寸，不依赖 FreeCAD。也就是说，电机/D 轴是正面左侧、背面右侧；圆轴张紧机构是正面右侧、背面左侧。

## 机构结构

- 当前先锁定左右两根边界轴（均以正面观察为准）：左侧是竖直 3 mm D 型驱动轴，右侧是张紧边界。右侧不是一根贯穿上下的轴，而是上下两套独立的 3 mm 圆轴短主轴；每套只承载对应高度的一只同步轮。左轴同步轮为 D 孔，右侧两只同步轮为圆孔，不能互换。每个同步轮齿圈上下各有一个限位法兰，法兰外径大于齿圈外径。
- 正面左侧服务区放置竖直朝上的 Pololu 电机包络、3 mm D 型输出轴和延长传动杆；从背面看它位于右侧。
- 纵轴边界位置明确为 `2 + N_COL = 7`：正面左侧 1 根 D 型驱动轴，中间 5 根抽屉传动轴，正面最右侧 1 个张紧边界位置；这个位置上下各有 1 根独立的圆轴短主轴，D 驱动轴和张紧边界均不计入抽屉列数。从背面看，物理顺序反过来，但仍是同样的 7 个纵轴位置。
- 每个格位的竖杆旁有连续齿杆。轴向为 Y 的上层啮合齿轮保持与齿杆关系；其下层为向下的狗牙面。
- 固定的向上狗牙面下方是同轴的取力同步轮：上层是向上的离合齿面，下层是同步轮。
- 后侧同步带沿 Y 传到抽屉前端；前端复合轮的下层是同步轮、上层是较大的 Z 轴齿轮，驱动抽屉底部的直线齿条。
- 正面右侧的上、下圆轴各自采用参考 SKP 的横向滑台：箱体后侧增加两层独立的固定接收肋和承托台，每层固定槽都有左右端块、侧壁和上方卡唇；对应移动台在自己的槽内沿 X 滑动，卡唇限制 Z 向抬起、侧壁限制 Y 向窜动，后侧肋条和正面右侧肋条把两层固定槽分别锁到箱体背板/右侧壁。
- SKP 中间的圆环按轴承建模，不再把它误当成滑块凸台。每层滑块都有一个轴承座，并单独放入一只 `Ø9 × 2 mm` 轴承环；Ø3 mm 圆轴穿过轴承后再承载该层同步轮。
- 5 列抽屉宽度已经占满箱体右侧，因此张紧滑台的固定接收件向正面右侧外伸一小段；它跨过箱体右侧壁与箱体相连。这样张紧轮不会和第 5 列传动轮重叠，且整个 8 mm 调节行程都保持同步轮法兰净距。
- 每个滑台行程为 8 mm，默认 `TENSIONER_SCREW_OUT_MM = 4`。左端是大孔调节螺杆，螺杆向箱体外侧（+X）拧出时只把对应层的移动台和圆轴推向 +X；右端是小圆弹簧座，弹簧在对应移动台和右端止挡之间提供回压。每层移动台左右端同时保留对应的螺杆盲孔和弹簧盲孔。
- 弹簧把上层离合载架顶起。默认开合间隙是一个狗牙齿高的 2 倍（`CLUTCH_OPEN_GAP = 2 * CLUTCH_DOG_TOOTH_H`）。拨叉压下 T 头沉头螺丝，`ENGAGED=true` 时上层齿轮下移并让螺丝头接近上齿轮顶面。

## 可重复构建

```sh
./scripts/export_cabinet_clutch.sh
./scripts/render_cabinet_clutch.sh
```

可用 `OPENSCAD_BIN=/path/to/OpenSCAD` 指定 CLI，`SELECTED_COLUMN`、`SELECTED_ROW` 指定离合详图格位。

`CLUTCH_PART` 的入口值：

- `assembly`：柜体、抽屉透明包络和完整机构的装配视图；
- `power_bus`：正面左侧 D 驱动轴 + 中间 5 列传动轴 + 正面右侧上下两套滑台圆轴，连同上下水平带；
- `all_vertical_axes`：只显示上述 7 根纵轴的检查入口，不包含水平同步带和抽屉取力机构；
- `tensioner_pulley_top`、`tensioner_pulley_bottom`：只检查上下两套滑台各自的同步轮；`tensioner_bearing`：检查上下两只独立轴承环；`tensioner_stage_top`、`tensioner_stage_bottom`：分别检查带箱体固定接收结构、固定槽、移动台、轴承、弹簧、调节螺杆和短圆轴的完整单层滑台；总装中两层各调用一次；
- `drawer_drive`：后前复合取力轮、Y 向同步带和抽屉底部齿条；
- `clutch`：全部格位离合；
- `clutch_detail`：单格离合详图，可配合 `CLUTCH_EXPLODE` 和 `ENGAGED`；
- `cabinet`：导出闭合薄壁柜体外壳以及与滑台相配的固定接收结构；装配图里的格栅和抽屉包络不进入该 STL。

逐件检查入口：当前轴阶段为 `left_d_axis`、`right_round_axis`、`side_axes`；滑台阶段为 `tensioner_slide`、`tensioner_stage_top`、`tensioner_stage_bottom`、`tensioner_bearing`、`tensioner_base`、`tensioner_carriage`、`tensioner_spring`、`tensioner_screw`、`tensioner_receiver`；随后还有 `motor`、`column`、`vertical_rack`、`idler`、`bus_belt`、`upper_spur`、`upper_dog`、`lower_dog`、`rear_pulley`、`spring`、`screw`、`fork`、`drawer_belt`、`front_pulley`、`front_gear`、`drawer_rack`。这些入口都固定在同一组装坐标，检查通过后可以直接回放到 `assembly`。

## 参数与待确认项

默认值是可打印性优先的机构包络，不是最终承载规格：同步带按 3 mm 节距、20T，离合和齿条按 3 mm 节距，电机输出按 3 mm D 轴。长竖杆建议使用金属 D 杆；打印齿轮、弹簧、同步带和螺钉均需按实物尺寸复核。

滑台的尺寸按当前轴冻结：右侧两套短轴均为 Ø3 mm 圆轴，圆孔为 Ø3.24 mm；同步轮齿圈外径约 20.82 mm，上下限位法兰外径约 22.82 mm；轴承环按 `Ø9 × 2 mm`、轴承座外径约 10.4 mm 适配。每层固定槽的有效 Y 向深度约 33.6 mm，滑块深度 32 mm，底面上方留 0.4 mm 运行间隙；固定槽总长约 38.41 mm，并跨过箱体右侧壁向外延伸。张紧轴与第 5 列传动轴的法兰中心距按 1 mm 净距布置。SKP 未提供可直接读取的精确标注，因此固定槽/滑台的具体壁厚、行程和孔径是以这些轴尺寸为约束的参数化适配值。

当前模型把“轴向 Y 的上层啮合齿轮”和“轴向 Z 的狗牙离合面”明确成同一个上层载架的两个功能面；后、前同步轮均为轴向 Z，带路在 XY 平面内沿 Y 方向走。当前齿形是可替换的参数化原型轮廓；如果确定使用专门的锥齿/端面齿，可只替换对应轮廓模块，不需要重做整体坐标布局。

STL 不包含单位、弹簧预紧力或切片参数。`cabinet_clutch_assembly.stl`、`cabinet_clutch_all_clutches.stl` 和 `cabinet_clutch_detail_*.stl` 是带有多个相互独立显示体的检查用总成，不能当作打印件；逐件候选 STL 才是后续切片检查的对象。导出后的 `output/inspection/cabinet-clutch/*.json` 只做包围盒、三角形和流形初筛；材料、层高、支撑、齿面强度和实际抽屉负载仍需在切片和首件装配中确认。

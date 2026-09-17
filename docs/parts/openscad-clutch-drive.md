# OpenSCAD 抽屉动力母线与中心离合

入口：`cad/openscad/enclosure/cabinet_clutch.scad`。

模型使用项目冻结的世界坐标：X 为箱体宽度，Y 为竖直高度（`+Y` 向上），Z 为箱体
深度（正面 `Z=0`，背面为负 Z），单位为毫米。`cabinet_clutch.scad` 负责柜体定位、
动力母线、抽屉驱动和中心 R3C3 总装；中心承力机构集中在
`cabinet_clutch_carrier.scad`，不靠网页坐标偏移拼出另一套机械结构。

## 默认场景

- 默认只启用中心零基 `col=2,row=2`（R3C3）及其抽屉驱动路径；其余 24 站只有明确
  打开 `SHOW_LEGACY_STATIONS=true` 才用于历史诊断。
- 默认树中的中心离合件是：输入公轮、输出母轮、输入 D-round-D 阶梯轴、下端 D 型
  圆套、Ø5×5 磁铁参考、固定 LM3UU 参考、机构板一体实心轴承座、输出轴承笼/独立短轴/两枚
  `3×6×2` 轴承、可拆机构板。轴和轴承是采购件显示，不伪装成打印件。
- 公轮端没有移动滑架、独立导轨、压盖、止挡、弹簧、螺丝、拨叉或额外旋转轴承组。
  公轮上 D 段固定，Ø3 圆段直接在固定于机构板的 `3×7×10 mm` LM3UU 中上下滑动，
  下 D 段插入上方 D 型圆套；圆套下端为 Ø8 圆形，盲槽容纳 Ø5×5 圆柱磁铁。
- 输出母轮位置固定、只保持旋转，由输出笼中的两枚 `3×6×2` 轴承支撑；输入/输出
  使用两根彼此独立的 3 mm D 轴。

## 中心 R3C3 离合契约

中心契约从 OpenSCAD 回显生成到
`output/3d-print/cabinet-clutch/center_clutch_contract.json`，再进入
`cabinet_chain_motion.json`；网页不另写一套尺寸。当前冻结值为：

| 项目 | 数值 |
| --- | ---: |
| 运动轴/角色 | `+Y`；输入公轮 / 输出母轮 |
| 开位间隙 / 有效插入 / 总行程 | `0.60 / 2.40 / 3.00 mm` |
| 母槽深度 / 合位槽底余量 | `3.25 / 0.85 mm` |
| 直线轴承 | 1× LM3UU，`Ø3×Ø7×10 mm`，固定、与公轮同轴 |
| 一体轴承座 | `Ø7.20` 贯通孔；座体除轴承孔外实心、无 M3 孔，LM3UU 可上下压入，机构板本体 4×M3 |
| 输入轴型 | `D-round-D`，圆滑动段 `Ø3 mm` |
| 圆套 | 上 D + 下 Ø8 圆，盲槽 `Ø5.20×5.20 mm` |
| 磁铁 | 名义 `Ø5×5 mm` 圆柱，圆套底厚 `1.20 mm` |
| 动作条件 | 永磁；停止时接合，返回前释放 |

开合和齿形干涉由 `scripts/validate_center_clutch_geometry.py` 直接重新编译实际
几何检查，浏览器动画只用于显示“输入公轮沿 +Y 移动、输出母轮固定旋转”的流程。

## 动力母线和抽屉驱动

动力母线继续使用 5 根沿世界 Y 的长花键列轴、上下两条 2GT 同步带和低 X 侧张紧
机构；电机接驳 +X 末列。中心 R3C3 通过后侧中心 2GT 皮带把输出母轮的旋转传到
抽屉前端的同步轮、粗齿轮和直线齿排。中心机构板开有按实际皮带包络生成的贯穿槽，
皮带不能被机构板截断；薄后盖不承受中心传动载荷。

中心输入端未接合时，网页不会宣称抽屉已获得动力；选择指/磁力流程停止后，契约的
`3.00 mm` 行程才允许输出母轮、皮带、前端轮和齿排同步运动。释放完成后输入端回到
开位，才允许选择指返回。

## 逐件入口

```text
assembly
world_axes
power_bus
all_vertical_axes
drawer_drive
clutch
clutch_detail
center_input_rotor
center_output_rotor
center_input_shaft
center_input_sleeve
center_input_sleeve_magnet
center_linear_bearings
center_linear_bearing_fit_coupon
center_output_cage
center_output_shaft
center_output_bearings
center_mechanism_plate
center_plate_belt_collision
contract
cabinet
```

导出脚本使用稳定的 `center_*` canonical 名称。旧 `center_input_carriage`、
`center_guide_rails`、`center_stops`、旧压盖/输入轴承组、弹簧、螺丝、拨叉和
`scheme1_*` 入口只为显式 legacy 诊断兼容保留，不进入默认清单。

## 构建和验收边界

```sh
./scripts/export_cabinet_clutch.sh
```

导出脚本会生成预览 manifest、逐件 STL、契约和检查报告；`output/`、`build/` 和本地
预览产物均为可重建文件，不提交 Git。验证器会检查打印件 watertight、阶梯轴刚体
位移、一体轴承座的 LM3UU 贯通孔/无座体固定孔、圆套磁铁盲槽、输出双轴承、齿形/皮带/
机构板干涉以及中间行程。

这些检查只覆盖 CAD/导出层。仍必须打印测试片和首件，实装真实 LM3UU、金属 Ø3 轴、
两枚输出轴承和 Ø5×5 磁铁，确认孔径、滑动阻力、同轴度、磁极和防脱，再完成至少
20 次手动开合循环和后续低速动作测试。低速电机和浏览器预览都不能替代真实抽屉
负载验收；中心首件通过后才复制其余 24 站。

```sh
./scripts/render_cabinet_clutch.sh
```

渲染脚本仅用于可见预览。需要手动启动/停止时在可见 Terminal 运行脚本即可，不增加
常驻服务，不涉及 Nginx、VPN 或外网入口。

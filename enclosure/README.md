# SmartPaddle M6 外壳（OpenSCAD）

M6 将拍体改为传统球拍式连续承力结构。外形来自
`web/src/data/userBezierProfiles.json`，拍柄 loft 在 `handle_join_y`
与拍头实体相交，不再保留用于预览的结构缝。

Z+ 到 Z- 的四层为：

1. 拍柄正面外贴层；
2. 覆盖拍头和完整拍柄轮廓的正面主承力层；
3. 同轮廓的背面主承力层（带连续榫舌）；
4. 拍柄背面外贴层。

第 2/3 层默认各 3 mm，主体实心，只切电子件、走线、螺丝和中控拍柄腔。
两层通过连续榫槽及腔内隐藏 M2 螺丝连接。

## 导出（唯一入口）

```bash
./scripts/export-stl.sh
```

若存在 `pcb-tail/layouts/default/default.kicad_pcb`，导出后自动跑 Step6：用 Edge.Cuts + USB/按钮/LED 干涉已导出拍柄，覆盖 `enclosure/stl/` 最终件。

| 文件 | 用途 |
|------|------|
| `paddle_m6_layer1_handle_skin_front.stl` | 第1层：拍柄正面外贴 |
| `paddle_m6_layer2_core_front.stl` | 第2层：正面完整主承力板 |
| `paddle_m6_layer3_core_back.stl` | 第3层：背面完整主承力板 |
| `paddle_m6_layer4_handle_skin_back.stl` | 第4层：拍柄背面外贴 |
| `paddle_m6_monolithic_{front,back}.stl` | 无缝合体打印件 |
| `paddle_m6_{assembly,exploded}.stl` | 装配/爆炸预览 |
| `paddle_m6_handle_tail.stl` | 完整截面尾段（预览） |
| `paddle_m6_handle_back_tip.stl` | 后侧 tip 试打 |
| `interference/` | 板槽 / UI 开孔诊断 |

```bash
./dev.sh                          # ?tab=process 统一工艺预览
./scripts/preview-stl.sh          # 轻量静态预览
SKIP_STEP6=1 ./scripts/export-stl.sh
QUALITY_MODE=quick ./scripts/export-stl.sh
./scripts/.venv-stl/bin/python scripts/validate_m6_geometry.py
```

旧 `paddle_shell_*`、`paddle_blade_*`、`paddle_handle_*` 文件名已废止，
导出脚本会主动删除它们，避免误打印旧的头柄插装结构。

## 工艺公差

- `m6_print_clearance=0.20`：FDM 榫槽默认单边间隙；
- `m6_cnc_clearance=0.00`：木板/CNC 基准，按刀具和材料实测补偿；
- `m6_union_overlap=0.15`：仅合体 STL 使用，确保头柄和层间存在实体重叠；
- 注塑/玻纤模具应在同一无缝主承力轮廓上另做拔模和收缩补偿，不得恢复头柄缝。

## 目录

```
enclosure/
├── parameters.scad
├── paddle_shell.scad
├── generated/           # bezier_to_openscad.py（勿手改）
└── stl/                 # 最终打印件 + preview/
```

旧外购充电总成固定件已从拍柄 SCAD 移除；USB/键/灯开孔只由 Step6 按 pcb-tail 位姿生成。

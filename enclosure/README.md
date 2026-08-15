# SmartPaddle M6 外壳（OpenSCAD）

当前硬件组合登记为 **M6.C5**：本目录定义模型版本 M6，`pcb/` 与 `pcb-tail/` 的现行源定义电路版本 C5。两条版本线独立编号；M6 已形成现行机械生成闭环，不因 C5 布线而改写脚本或产物命名。

M6 将拍体改为传统球拍式连续承力结构。外形来自
`web/src/data/userBezierProfiles.json`，拍柄 loft 在 `handle_join_y`
与拍头实体相交，不再保留用于预览的结构缝。

Z+ 到 Z- 的四层为：

1. 拍柄正面外贴层；
2. 覆盖拍头和完整拍柄轮廓的正面主承力层；
3. 同轮廓的背面主承力层；
4. 拍柄背面外贴层。

第 2/3 层默认各 3 mm，主体实心，只切电子件、走线、螺丝和中控拍柄腔。
最终打印/制作件按 Z=0 合并为“正面外贴+正面主层”和“背面主层+背面外贴”
两个大件不再使用榫槽；四层分制时，侧边两组沉头螺丝从中间贴合面分别由第 2 层
攻入第 1 层、由第 3 层攻入第 4 层。只有这组细螺丝按核心层与拍柄内腔壁中的
较薄者动态选径，当前可用 3 mm 采用 M1.2。中轴第 1→4 层贯穿螺丝和拍面
第 2→3 层螺丝沿用已采购的 M2 规格。
Type-C 尾端开口左右侧各有一个附加紧固点，防止开口两侧受力变形。

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
| `paddle_m6_fasteners.stl` | 实际规格沉头自攻螺丝装配模拟 |
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

## 工艺与紧固

- `m6_union_overlap=0.15`：仅合体 STL 使用，确保头柄和层间存在实体重叠；
- `m6_handle_wall_t`：由 `wall_t + handle_cavity_inset` 自动得到；
- `m6_handle_screw_d`：按核心层/内腔壁中的较薄者自动选择 M1.0 / M1.2 / M1.4 / M1.6；
- 两组螺丝头镜像坐落在 Z=0 中间贴合面：第 2 层向上攻入第 1 层，
  第 3 层向下攻入第 4 层，外表面不开螺丝入口；
- 长度从 `[4,5,6,7,8,10]` 中选择，要求穿过 3 mm 主层后在对应外层咬合 2–4 mm；
- 当前每侧使用 **M1.2×5 mm 沉头自攻不锈钢螺丝**，外层咬合 2 mm；
- 拍柄中轴 3 颗第 1→4 层贯穿螺丝固定使用 M2，孔径不随薄壁选径变化；
- 三颗中轴 M2 均采用 Ø6×2 mm 硅胶盖凹位，沉头位于凹位底部；
- 拍面 9 颗第 2→3 层沉头螺丝固定使用 M2×5（M2×6 会到达背面）；
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

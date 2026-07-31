# SmartPaddle 外壳（OpenSCAD）

拍面 + 手柄一体分壳，PETG 打印。外形来自 `web/src/data/userBezierProfiles.json` → OpenSCAD 水密 CSG。

## 导出（唯一入口）

```bash
./scripts/export-stl.sh
```

若存在 `pcb-tail/layouts/default/default.kicad_pcb`，导出后自动跑 Step6：用 Edge.Cuts + USB/按钮/LED 干涉已导出拍柄，覆盖 `enclosure/stl/` 最终件。

| 文件 | 用途 |
|------|------|
| `paddle_handle_{front,back}.stl` | 拍柄（含尾板干涉） |
| `paddle_blade_{front,back}.stl` | 拍面 |
| `paddle_shell_{front,back}.stl` | 半壳 |
| `paddle_split_assembly.stl` | 整拍预览 |
| `paddle_handle_tail.stl` | 完整截面尾段（预览） |
| `paddle_handle_back_tip.stl` | 后壳 tip 试打 |
| `interference/` | 板槽 / UI 开孔诊断 |

```bash
./scripts/preview-stl.sh          # 尾部干涉预览（守护进程，不重复弹窗）
SKIP_STEP6=1 ./scripts/export-stl.sh
QUALITY_MODE=quick ./scripts/export-stl.sh
```

## 目录

```
enclosure/
├── parameters.scad
├── paddle_shell.scad
├── generated/           # bezier_to_openscad.py（勿手改）
└── stl/                 # 最终打印件 + preview/
```

旧外购充电总成固定件已从拍柄 SCAD 移除；USB/键/灯开孔只由 Step6 按 pcb-tail 位姿生成。

# SmartPaddle 外壳（OpenSCAD）

拍面 + 手柄一体分壳，PETG 打印。外形来自 `web/src/data/userBezierProfiles.json` → OpenSCAD 水密 CSG。

## 模型版本边界

- `parameters.scad` / `paddle_shell.scad` / `scripts/export-stl.sh` 是可打印壳体源。
- 尾板开孔：**不在 SCAD 硬编码**。若存在 `pcb-tail/layouts/default/default.kicad_pcb`，`export-stl.sh` 会在 OpenSCAD 导出后自动跑 **Step6**，用 Edge.Cuts + USB/按钮/LED 干涉已导出拍柄，覆盖 `enclosure/stl/` 最终件。
- 旧外购充电总成固定件已从拍柄 SCAD 移除；电池匣方案已废弃。

## 导出（唯一入口）

```bash
./scripts/export-stl.sh
```

会生成：

- `paddle_blade_{front,back}.stl`
- `paddle_handle_{front,back}.stl`（Step6 后含尾板干涉）
- `paddle_shell_{front,back}.stl`
- `paddle_split_assembly.stl`
- `paddle_handle_back_tip.stl`
- 诊断：`stl/interference/{board_slot,ui_cuts,all_cuts}.stl`

跳过尾板干涉：`SKIP_STEP6=1 ./scripts/export-stl.sh`  
快速预览：`QUALITY_MODE=quick ./scripts/export-stl.sh`  
仅 tip：`./scripts/export-stl.sh tip`

## 本目录只放「源文件」

```
enclosure/
├── README.md
├── parameters.scad
├── paddle_shell.scad
├── bezier_profile.scad
├── export_outer.scad
├── generated/           # bezier_to_openscad.py 输出（勿手改）
└── stl/                 # export-stl.sh 最终打印件
```

可选本地预览：`./scripts/preview-m5.sh`（读 Step6 镜像到 `m5/build/` 的 tip/诊断）。

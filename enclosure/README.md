# SmartPaddle 外壳（OpenSCAD）

拍面 + 手柄一体分壳，PETG 打印。外形来自 `web/src/data/userBezierProfiles.json` → OpenSCAD 水密 CSG。

## 本目录只放「源文件」

```
enclosure/
├── README.md
├── parameters.scad      # 孔位、壁厚、螺丝/压电/USB
├── paddle_shell.scad    # 主文件：前壳 / 后壳（HALF=front|back|both）
├── bezier_profile.scad  # 腔体 Z 查表
├── export_outer.scad    # 可选：仅导出整件外壳实体
├── generated/           # bezier_to_openscad.py 输出（勿手改）
└── stl/                 # export-stl.sh 输出（切片用）
```

**不在此目录常驻：** `analysis/` 下的 PNG、尺寸表 — 由脚本生成到仓库外路径或自行跑分析（见下）。

## 看模型 / 打印

```bash
./scripts/export-stl.sh
```

产出：

| 文件 | 用途 |
|------|------|
| `stl/paddle_blade_front.stl` | 拍面前半（Z≥0） |
| `stl/paddle_blade_back.stl` | 拍面后半（Z≤0） |
| `stl/paddle_handle_front.stl` | 拍柄前半 |
| `stl/paddle_handle_back.stl` | 拍柄后半（含 USB 开孔） |
| `stl/paddle_shell_front.stl` | 前壳组装 = 拍面前 + 拍柄前 |
| `stl/paddle_shell_back.stl` | 后壳组装 = 拍面后 + 拍柄后 |

```bash
open enclosure/stl/paddle_shell_front.stl enclosure/stl/paddle_shell_back.stl
```

可选整件外壳（无腔、无分型）：

```bash
openscad -o enclosure/stl/outer_envelope.stl enclosure/export_outer.scad
```

## 2D 轮廓核对（贝塞尔 JSON）

```bash
./scripts/.venv-analyze/bin/python scripts/analyze_bezier_views.py \
  --out /tmp/smartpaddle-bezier-design
open /tmp/smartpaddle-bezier-design/blade_silhouette.png
```

默认曾写入 `enclosure/analysis/bezier_design/`；该目录已从仓库清理，避免与源文件混在一起。

## 数据流

```
userBezierProfiles.json → bezier_to_openscad.py → generated/*.scad
                    → paddle_shell.scad → stl/paddle_shell_*.stl
```

设计预览：Web Shape / Live。打印几何：上表 OpenSCAD 链路。

详见 `docs/print-prep.md`。

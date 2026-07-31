# SmartPaddle 尾部线路板（`pcb-tail`）

> 与 `pcb/`（C4 主线）隔离。满截面尾板；充电/USB/按键/LED 在本板。

## 方向约定

| 面 | 朝向 |
|---|---|
| 正面 `F.Cu` | 拍柄末端（世界 −Y） |
| 背面 `B.Cu` | 拍头（世界 +Y） |

- `KiCad X` = 柄 `X`
- `KiCad Y` = 柄 `Z`
- 板厚沿世界 `Y`（1.0 mm）

## 打开

```text
pcb-tail/layouts/default/default.kicad_pro
```

## 工作流

```bash
cd pcb-tail
ato build
python3 generate_outline.py
ato build
```

入口：`main.ato:SmartPaddleTail`（`ato.yaml`）。

外形：`web/src/data/userBezierProfiles.json` + `enclosure/parameters.scad`  
内缩：`wall_t + tail_cavity_inset`；`board_clearance = -0.50` 嵌入环槽。

壳体开孔：`./scripts/export-stl.sh`（含 Step6，按本板位姿干涉）。

## 文件

| 文件 | 说明 |
|------|------|
| `main.ato` | atopile 入口 |
| `layouts/default/default.kicad_pro` | 工程 |
| `generate_outline.py` | 从尾端截面生成 Edge.Cuts |
| `tail-outline-preview.svg` / `.png` | 2D 预览 |
| `geometry-report.txt` / `outline-facts.json` | 尺寸事实 |

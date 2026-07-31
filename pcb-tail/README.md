# SmartPaddle M5 尾部线路板（`pcb-tail`）

> 状态：**外形 + 电源岛器件已入板，按功能组扎堆摆放（未布线）**。  
> 与 `pcb/`（C4 主线）隔离。

## 阶段策略

1. **本阶段**：电池先固定不可换，尾板占满拍柄尾端 **XZ 截面**。
2. **下一阶段**：再做可换电池匣 + 窄侧尾板（原 `M5.C5`）。

## 方向约定

| 面 | 朝向 |
|---|---|
| 正面 `F.Cu` | 拍柄末端（世界 −Y） |
| 背面 `B.Cu` | 拍头（世界 +Y） |

- `KiCad X` = 柄 `X`
- `KiCad Y` = 柄 `Z`
- 板厚沿世界 `Y`（1.0 mm）

## 正确打开路径

不要打开已删除的 `m5-tail-outline.kicad_pcb`。请打开：

```text
pcb-tail/layouts/default/default.kicad_pro
```

或同目录下的 `default.kicad_pcb`。

在 PCB 编辑器中：

1. 右侧图层打开 **Edge.Cuts**
2. 按 `F` / Zoom to Fit 缩放到板
3. 裸板只有边界 + 阻焊填充，无器件铜皮

## 工作流

```bash
cd pcb-tail
ato build
python3 generate_outline.py
ato build
```

入口：`main.ato:SmartPaddleTail`（`ato.yaml`）。

外形输入：`web/src/data/userBezierProfiles.json` + `enclosure/parameters.scad`  
内缩：`wall_t + handle_cavity_inset + 0.30 mm`。  
Edge.Cuts 使用**单个闭合 `gr_poly`**（非散段落线）。

## 文件

| 文件 | 说明 |
|------|------|
| `main.ato` | atopile 入口模块 |
| `ato.yaml` | atopile 0.12.5 工程配置 |
| `layouts/default/default.kicad_pro` | **用这个打开工程** |
| `layouts/default/default.kicad_pcb` | 裸板（闭合 Edge.Cuts） |
| `generate_outline.py` | 从真实尾端截面生成边界 |
| `m5-tail-outline-preview.svg` / `.png` | 2D 预览 |
| `m5-tail-outline-preview-3d.png` | KiCad 3D 渲染核对 |
| `geometry-report.txt` | 尺寸报告 |

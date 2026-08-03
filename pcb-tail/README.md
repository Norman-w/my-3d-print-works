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
| `C4_ADAPTER_HARNESS.md` | 当前 C4 主板与本尾板的 4P→5P 转接、装配及验证 |
| `harness/c4-adapter.json` | 由两块实际 PCB 焊盘网络校验的线束真理源 |

> 注意：本尾板为 2×4P，当前 C4 主板栈道为正反 2×5P，不能直接插接。
> 使用上述转接线束；C4 的 UART TX/RX 保留为独立调试口。

## 嘉立创实验样板资料

从仓库根目录运行：

```sh
# 仅尾板
python3 pcb/scripts/export_order_packages.py --target tail

# 主板、尾板分别形成两个独立订单包
python3 pcb/scripts/export_order_packages.py --target separate
```

尾板为 2 层、板厚 1.00 mm；铜厚、表面处理及颜色尚未冻结，必须在下单页面确认并记录。当前只建议 5 片或厂家最低数量的工程样板。DRC 通过不等于实物验证或量产放行，详细阻塞、网站检查项和线序会随导出包提供。

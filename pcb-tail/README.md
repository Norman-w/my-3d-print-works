# SmartPaddle 尾部线路板（`pcb-tail`）

> 与 `pcb/`（C4 主线）隔离。满截面尾板；充电/USB/按键/LED 在本板。

> **当前设计与旧板安全状态（2026-08-15）：** J1 的 H=5.8 短脚封装和 16 个物理触点映射已按用户数据表修正；J4、B3U、两级 TPS2553 和 KEY 隔离也已同步。当前板为 33 个封装、0 条走线/0 个过孔/0 个覆铜区，DRC 为 0 个规则违规、79 个预期未连接，**不能制造**。所有按旧 J1 错误映射制造或已焊接的尾板及旧制造文件仍不得上电、插 USB 或再次下单，不得现场飞线返修。详见 [`../docs/usb-c-vertical-16p-short/M5-J1-PINOUT-AUDIT.md`](../docs/usb-c-vertical-16p-short/M5-J1-PINOUT-AUDIT.md) 和 [`../docs/power-architecture-rework/README.md`](../docs/power-architecture-rework/README.md)。
>
> `layouts/default/export-preview/` 中除重新生成的 `fp-usb16p-selfcheck.png` 外，其余图像是本次审计前的历史预览，不是当前 J1 或制造状态的证据。

## 方向约定

| 面 | 朝向 |
|---|---|
| 正面 `F.Cu` | 拍柄末端（世界 −Y） |
| 背面 `B.Cu` | 拍头（世界 +Y） |

- `KiCad X` = 柄 `X`
- `KiCad Y` = 柄 `Z`
- 板厚沿世界 `Y`（1.0 mm）

## 专用电池接口（已布局/布线）

- 板端：JST ACH `BM02B-ACHSS-GAN-ETF`，1.20 mm、2P、SMT 顶插；配套线端 `ACHR-02V-S` + `SACH-003G-P0.2`，成品线固定为 AWG28。
- J4 footprint：`Connector_JST:JST_ACH_BM02B-ACHSS-GAN-ETF_1x02-1MP_P1.20mm_Vertical`。电气定义固定为 **Pin 1=`BAT_P`/red**、**Pin 2=`GND`/black**；它与现有 `J2.3 BAT_P` / `J2.2 GND` 并联，电池不得接主板 `SYS_5V_IN`。
- J4 位于 B.Cu `(-2.794,-5.969) mm`、90°；Pad 1 全局 `(-0.919,-5.369) mm`，Pad 2 `(-0.919,-6.569) mm`，两个 `MP` 固定焊盘均 NC。当前两脚都待用户重新布线。
- 选型、采购词、电流门禁和官方资料见 [`../docs/battery-connector-jst-ach-2p/README.md`](../docs/battery-connector-jst-ach-2p/README.md)。旧 PH 方案已明确停用；官方 XH 2.50 与市售“XH2.54”不能凭名称保证互配。

## 用户按键（已换 footprint/布线，待机械试片）

- SW1 已由 4.5×4.5 mm THT 换成 Omron `B3U-1000P` SMD，footprint 为 `Button_Switch_SMD:SW_SPST_B3U-1000P`；保持原锚点 `(-1.651,-5.461) mm` 和 `-90°`，没有移动或旋转其他器件。
- Pad 1=`user_btn`、Pad 2=`GND`，当前待用户重新布线。
- 拍柄采用导向活动推杆，不用固定柱长期压住开关。参数化源已更新为 Ø1.6 mm 推杆/Ø2.0 mm 导向孔、0.05 mm 名义静止间隙；必须先做尾段试片。详见 [`../docs/tail-user-switch-b3u-1000p/README.md`](../docs/tail-user-switch-b3u-1000p/README.md)。本次没有生成或覆盖 STL。
- `python3 pcb-tail/scripts/audit_battery_connector_j4.py` 同时核对 J4 与 SW1 的位姿、针脚网络和项目内资料；铜完整性由跨层制造门禁另行检查。

## 打开

```text
pcb-tail/layouts/default/default.kicad_pro
```

## 工作流

当前尾板是重新布线交接态。J1 封装可重复生成和逐触点检查：

```bash
python3 pcb-tail/scripts/gen_usb_16p_vert_smt_fp.py
python3 pcb-tail/scripts/audit_usb_16p_j1.py
python3 pcb-tail/scripts/audit_battery_connector_j4.py
```

Atopile 只构建到 `layouts/staging/`；必须连续构建两次，再用项目同步脚本安全带入当前板。不得直接让 Atopile 覆盖 `layouts/default/`，`ato build` 的成功退出也不能替代逐触点审计：

```bash
cd pcb-tail
ato build
ato build
cd ..
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 \
  pcb-tail/scripts/sync_power_architecture.py
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 \
  pcb-tail/scripts/place_power_architecture.py
python3 scripts/validate_power_rework.py
```

入口：`main.ato:SmartPaddleTail`（`ato.yaml`）。

外形：`web/src/data/userBezierProfiles.json` + `enclosure/parameters.scad`  
内缩：`wall_t + tail_cavity_inset`；`board_clearance = -0.50` 嵌入环槽。

壳体开孔：`./scripts/export-stl.sh`（含 Step6，按本板位姿干涉，并生成独立 B3U 活动推杆）；当前改动未执行该制造导出。

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

## 已知瑕疵

- 当前 KiCad 3D Viewer 及导出的 3D 预览中，部分器件模型的比例/尺度与实物不一致；这只影响 3D 外观预览，不代表 PCB 焊盘、板框或器件采购尺寸发生变化。
- 3D 模型比例问题本身不用于判断焊盘；但这条说明不适用于 J1。本次已用 H=5.8 短脚主数据表独立纠正 J1 land pattern，旧 J1 板批不可用。
- 下一版装配图或下单前，应按供应商机械图和实物重新校准 `pcb-tail/lib/3dmodels/` 下的模型比例、原点和高度，并重新检查 Type-C、MX1.25 和按键的壳体干涉。

## 嘉立创实验样板资料

> 当前没有运行 `--target tail` / `--target separate`，也没有生成新的尾板 Gerber/ZIP。制造脚本会因无布线、79 个未连接和 B3U 推杆最坏公差未闭合而拒绝导出；此前所有尾板制造包仍禁止继续使用。

从仓库根目录运行：

```sh
# 仅尾板
python3 pcb/scripts/export_order_packages.py --target tail

# 主板、尾板分别形成两个独立订单包
python3 pcb/scripts/export_order_packages.py --target separate
```

尾板为 2 层、板厚 1.00 mm；铜厚、表面处理及颜色尚未冻结。只有两板布线/铺地完成、0 未连接、B3U 尾段试片实测闭合公差且跨层 release gate 通过后，才可考虑工程样板。DRC 通过不等于实物验证或量产放行。

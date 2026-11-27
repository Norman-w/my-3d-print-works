# SmartPaddle 尾部线路板（`pcb-tail`）

> 当前 **M7.C5** 组合的独立满截面尾板，与 `pcb/` 主板分开维护；充电、USB、按键和 LED 均在本板。版本只记录在说明与 KiCad 标题栏，工程、PCB、同步脚本和交接文件使用跨版本通用名称。

> **当前设计与旧板安全状态（2026-08-17）：** 已完成的板内候选已提升为正式 M7.C5 尾板：33 个封装、502 段走线、53 个过孔和双面 GND 覆铜，KiCad DRC 为 0 error / 0 unconnected。J1 16触点、J4/SW1、电源拓扑、8芯线束与 M7 机械干涉门禁均通过。剩余警告仅为 J3/J4 已审计本地封装实例差异及 C6 丝印截断，不影响铜或钻孔。整机 release gate 仍会因主板尚未布线而阻止整机制造；尾板单独制作前仍须目检 Gerber/钻孔和锁定板厚、铜厚、表面处理。所有按旧 J1 错误映射制造或已焊接的尾板及旧制造文件仍不得上电、插 USB 或再次下单。
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

## 专用电池接口（已放置、已布线）

- 板端：JST ACH `BM02B-ACHSS-GAN-ETF`，1.20 mm、2P、SMT 顶插；配套线端 `ACHR-02V-S` + `SACH-003G-P0.2`，成品线固定为 AWG28。
- J4 footprint：`Connector_JST:JST_ACH_BM02B-ACHSS-GAN-ETF_1x02-1MP_P1.20mm_Vertical`。电气定义固定为 **Pin 1=`BAT_P`/red**、**Pin 2=`GND`/black**；它与现有 `J2.3 BAT_P` / `J2.2 GND` 并联，电池不得接主板 `SYS_5V_IN`。
- J4 位于 B.Cu `(-2.794,-7.000) mm`、90°；Pad 1 全局 `(-0.919,-6.400) mm`，Pad 2 `(-0.919,-7.600) mm`，两个 `MP` 固定焊盘均 NC。它只沿 KiCad Y 平移 1.031 mm，为插合后的 J2 线端留出净空；当前两脚已完成布线并通过 DRC。
- 选型、采购词、电流门禁和官方资料见 [`../docs/battery-connector-jst-ach-2p/README.md`](../docs/battery-connector-jst-ach-2p/README.md)。旧 PH 方案已明确停用；官方 XH 2.50 与市售“XH2.54”不能凭名称保证互配。

## 用户按键（已换 footprint、已布线；针孔可用，推杆可选）

- SW1 已由 4.5×4.5 mm THT 换成 Omron `B3U-1000P` SMD，footprint 为 `Button_Switch_SMD:SW_SPST_B3U-1000P`；保持原锚点 `(-1.651,-5.461) mm` 和 `-90°`，没有移动或旋转其他器件。
- Pad 1=`user_btn`、Pad 2=`GND`，当前已布线并接入双面 GND 覆铜。
- 拍柄基准操作方式为 SW1 中心 Ø2.0 mm 直通针孔，可用针尖/笔尖操作，不用固定柱长期压住开关。另有从壳内装入、Ø3.0 mm 法兰防外脱的 Ø1.6 mm 可选活动推杆；推杆批量使用前仍须做行程试片。详见 [`../docs/tail-user-switch-b3u-1000p/README.md`](../docs/tail-user-switch-b3u-1000p/README.md) 和 [`../docs/tail-handle-interference/README.md`](../docs/tail-handle-interference/README.md)。当前四层制造 STL 和两张 `paddle_m7_*` 打印拼板已按正式尾板干涉事实重新生成。
- `python3 pcb-tail/scripts/audit_battery_connector_j4.py --allow-copper` 同时核对 J4 与 SW1 的位姿、针脚网络和项目内资料；铜完整性由尾板独立制造门禁另行检查。

## 主板线束接口（卧插、已布线）

- J2/J3 均为 Molex PicoBlade `53261-0471`、1.25 mm、4P、卧插 SMT；与原 53398 立插使用同一 `51021-0400` 4P 线端体系，但两种板端 footprint 不能互换。
- J2 位于 B.Cu `(-11.300,-0.600) mm`、−90°；J3 位于 B.Cu `(+6.300,-5.800) mm`、180°。两只插口均朝板内侧，线束平行 PCB 离开；逐脚网络仍以 [`ADAPTER_HARNESS.md`](ADAPTER_HARNESS.md) 为准。
- 最终紧凑布局已经由 `audit_power_architecture.py` 锁定：C1/C2 两颗同值 100 nF 分别就近服务 D1 与 U1，U3/L1/C3/C4/C6 构成已审计的本地功率岛。J2/J3/J4 的完整插合包络已写入机械干涉事实并由壳体导出链消费。
- 原厂证据、封装快照、Pin 1 方向及机械说明见 [`../docs/molex-picoblade-53261-4p-horizontal/README.md`](../docs/molex-picoblade-53261-4p-horizontal/README.md)。

## 打开

```text
pcb-tail/layouts/default/default.kicad_pro
```

## 工作流

当前尾板是已布线生产基线。J1 封装仍可重复生成和逐触点检查：

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
python3 scripts/validate_power_rework.py --release-gate --target tail
```

入口：`main.ato:SmartPaddleTail`（`ato.yaml`）。

外形：`web/src/data/userBezierProfiles.json` + `enclosure/parameters.scad`  
内缩：`wall_t + tail_cavity_inset`；`board_clearance = -0.50` 嵌入环槽。

壳体开孔：`./scripts/export-stl.sh`（含 Step6，按本板位姿干涉，并生成独立 B3U 活动推杆）；当前 M7.C5 已按正式尾板重新生成 `paddle_m7_*` 四层件和两张打印拼板。

## 文件

| 文件 | 说明 |
|------|------|
| `main.ato` | atopile 入口 |
| `layouts/default/default.kicad_pro` | 工程 |
| `generate_outline.py` | 从尾端截面生成 Edge.Cuts |
| `tail-outline-preview.svg` / `.png` | 2D 预览 |
| `geometry-report.txt` / `outline-facts.json` | 尺寸事实 |
| `ADAPTER_HARNESS.md` | 当前主板与本尾板的 4P→5P 转接、装配及验证 |
| `harness/adapter.json` | 由两块实际 PCB 焊盘网络校验的线束真理源 |

> 注意：本尾板为 2×4P，当前主板栈道为正反 2×5P，不能直接插接。
> 使用上述转接线束；主板的 UART TX/RX 保留为独立调试口。

## 已知瑕疵

- 当前 KiCad 3D Viewer 及导出的 3D 预览中，部分器件模型的比例/尺度与实物不一致；这只影响 3D 外观预览，不代表 PCB 焊盘、板框或器件采购尺寸发生变化。
- 3D 模型比例问题本身不用于判断焊盘；但这条说明不适用于 J1 或 J2/J3。J1 已按 H=5.8 短脚主数据表逐触点纠正；J2/J3 使用 KiCad 9 stock 53261 footprint/STEP，并另按 Molex 销售图审计 land 与 3.40 mm 配合高度。
- 下一版装配图或下单前，仍应按供应商机械图和首件实物重新检查 Type-C、卧插线束的弯曲半径、按键孔和打印公差。

## 嘉立创实验样板资料

> 已运行尾板独立门禁并生成新的工程样板包；旧包仍禁止使用。尾板当前为 0 DRC error / 0 unconnected，Ø2.0 mm 针孔是独立可用的按键基准，可选推杆的试片状态不会掩盖电气验收。整机 `--target separate` 仍会因主板未布线而拒绝导出。

从仓库根目录运行：

```sh
# 仅尾板
python3 pcb/scripts/export_order_packages.py --target tail

# 主板、尾板分别形成两个独立订单包
python3 pcb/scripts/export_order_packages.py --target separate
```

当前尾板工程样板包位于 `pcb-tail/output/fab/20260817-tail-m7c5/`（本地制造输出，不纳入 Git），其中上传 ZIP 与审阅 ZIP 分离。尾板为 2 层、板厚 1.00 mm；下单页仍须人工冻结铜厚、表面处理及颜色。建议首板使用 1 oz 铜、沉金、绿色阻焊；若改用其他工艺应记录订单参数。该放行只覆盖尾板工程样板，不等于主板、整机或量产放行。

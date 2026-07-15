## 四步 PCB 生成管线

管线的机械基准来自 `enclosure/paddle_shell.scad` 的 `rigid_pcb_slot_points`。
每一步都是独立的 Python 脚本，按顺序执行：

| Step | 脚本 | 功能 | 操作层 |
| --- | --- | --- | --- |
| 1 | `scripts/step1_clear_and_reference.py` | 清空全部元素，绘制 SCAD 参考轮廓、坐标十字、PZT 腔体圆、X±/Y± 方向标记 | `Dwgs.User` |
| 2 | `scripts/step2_substrate_outline.py` | 清空 `Edge.Cuts`，绘制 PCB 基材外形（内缩 0.30mm、PZT 码头缩回、拍柄截断） | `Edge.Cuts` |
| 3 | `scripts/step3_module_cutouts.py` | 刷新 ESP32 和 IMU 模块矩形开孔，并生成 IMU 嵌入焊接 rule area | `Edge.Cuts` + rule area |
| 4.4 | `scripts/step4.4_tail_finger_stiffener.py` | 左右独立 8×8 加强小板（不改主板外形） | 独立 Edge.Cuts + 封装 |

Step1 是破坏性的（清空后重新开始），Step2~4 仅修改各自负责的层。

### 运行方式

```sh
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
PCB=pcb/layouts/default/default.kicad_pcb

# 完整重建（从零开始，丢弃原有封装）:
$KPY pcb/scripts/step1_clear_and_reference.py
$KPY pcb/scripts/step2_substrate_outline.py
$KPY pcb/scripts/step3_module_cutouts.py
# atopile build 生成封装...
$KPY pcb/scripts/step4_ato_placement.py --force
```

### 部分更新（保留封装）

```sh
# 仅重绘机械层，不影响已有封装:
$KPY pcb/scripts/step1_clear_and_reference.py   # 清机械层+重绘参考线
$KPY pcb/scripts/step2_substrate_outline.py      # 重绘基材外形
$KPY pcb/scripts/step3_module_cutouts.py         # 重绘模块开孔和 IMU rule area
$KPY pcb/scripts/step4.4_tail_finger_stiffener.py  # 可选：左右加强小板（不改主板外形）
$KPY pcb/scripts/step4_ato_placement.py          # 仅移动仍位于 ato 网格位置的封装
```

step4.4 只增删自己的独立小板外形与 `TAIL_*` 封装，**不会**改 step2 侧墙。若旧脚本挖坏了外形，先重跑 step2→step3。
```
### 截图验证

```sh
kicad-cli pcb render --side top --width 1600 --height 1200 --background opaque --quality high \
  -o pcb/output/stepN_top.png pcb/layouts/default/default.kicad_pcb
```

### 器件布局分区

| 区域 | 内容 | 列数 |
| --- | --- | --- |
| MCU X+ | 电源锁存电路 + LED 接口（Q×2、D×1、R×3、LDO×1、C×2） | 2 |
| MCU X- | 调试焊盘 *仅此*（GND、VCC、VBAT、UART_TX、UART_RX） | 1 |
| IMU X- | LDO 滤波电容（c_in、c_out） | 1 |
| IMU X+ | 剩余调试焊盘（EN、BOOT、PWR_LATCH、IMU_KEY、IMU_GPIO、VBUS、LED_DATA） | 2 |

### 电气逻辑

电气连接定义在 `main.ato`，`ato.yaml` 指向 `main.ato:SmartPaddleRigid`。

```sh
cd pcb
source ~/.atopile-env/bin/activate
ato validate main.ato
ato build --keep-designators --keep-net-names
```

封装以 `atopile_address` 属性作为电气真源实例。

管线脚本不处理布线，KiCad 仍负责:

- 元件放置决策
- 所有走线、过孔、敷铜和 DRC 清理
- 原理图 / 网表同步

### 嵌入式 IMU 半孔接口

`layouts/lib/footprints.pretty/IM948_CUTOUT.kicad_mod` 将 IM948 建模为内嵌模块接口:

- IMU 模块本体进入 `step3_module_cutouts.py` 生成的内部开孔，不与主 PCB 厚度方向叠放。
- 16 个 IMU 引脚使用 PTH 圆孔焊盘；开孔边线切过这些焊盘，形成主 PCB 侧的半孔/邮票孔焊接界面。
- KiCad 电气上仍把 `IMU_IM948` 当作普通元件，所以可以直接从这些焊盘往主板引线。
- `layouts/default/default.kicad_dru` 用 `IMU_EMBEDDED_CASTELLATED_EDGE` rule area 仅在 IMU 嵌入接口附近放宽 `edge_clearance`；普通板边仍按 0.5mm 检查。
- `layouts/default/default.kicad_pro` 的工程级 `min_copper_edge_clearance` 保持为 0mm，这是为了允许 custom rule 对 IMU 区域设置负的 edge clearance。不要删除 `.kicad_dru`，否则普通板边的 0.5mm 规则不会被恢复。

## Status

当前分支已包含四步管线重建的 PCB。后续工作:

- 决定嵌入模块半孔应保留为电镀槽/半孔还是改为更宽的焊锡架
- 根据更新后的参考手工布线电源、USB/UART、LED、按钮和 PZT 网络
- 在制造前添加沉槽开孔的 fab 注释

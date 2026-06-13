## 四步 PCB 生成管线

管线的机械基准来自 `enclosure/paddle_shell.scad` 的 `rigid_pcb_slot_points`。
每一步都是独立的 Python 脚本，按顺序执行：

| Step | 脚本 | 功能 | 操作层 |
| --- | --- | --- | --- |
| 1 | `scripts/step1_clear_and_reference.py` | 清空全部元素，绘制 SCAD 参考轮廓、坐标十字、PZT 腔体圆、X±/Y± 方向标记 | `Dwgs.User` |
| 2 | `scripts/step2_substrate_outline.py` | 清空 `Edge.Cuts`，绘制 PCB 基材外形（内缩 0.30mm、PZT 码头缩回、拍柄截断） | `Edge.Cuts` |
| 3 | `scripts/step3_module_cutouts.py` | 追加 ESP32 和 IMU 模块矩形开孔 | `Edge.Cuts`（追加） |
| 4 | `scripts/step4_ato_placement.py` | 规范化 ato 封装元数据，将元器件按相对坐标布置到各区 | 封装位置 / 属性 |

Step1 是破坏性的（清空后重新开始），Step2~4 仅修改各自负责的层。

### 运行方式

```sh
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
PCB=rigid_pcb/layouts/default/default.kicad_pcb

# 完整重建（从零开始，丢弃原有封装）:
$KPY rigid_pcb/scripts/step1_clear_and_reference.py
$KPY rigid_pcb/scripts/step2_substrate_outline.py
$KPY rigid_pcb/scripts/step3_module_cutouts.py
# atopile build 生成封装...
$KPY rigid_pcb/scripts/step4_ato_placement.py --force
```

### 部分更新（保留封装）

```sh
# 仅重绘机械层，不影响已有封装:
$KPY rigid_pcb/scripts/step1_clear_and_reference.py   # 清机械层+重绘参考线
$KPY rigid_pcb/scripts/step2_substrate_outline.py      # 重绘基材外形
$KPY rigid_pcb/scripts/step3_module_cutouts.py         # 重绘模块开孔
$KPY rigid_pcb/scripts/step4_ato_placement.py          # 仅移动仍位于 ato 网格位置的封装
```

### 截图验证

```sh
kicad-cli pcb render --side top --width 1600 --height 1200 --background opaque --quality high \
  -o rigid_pcb/output/stepN_top.png rigid_pcb/layouts/default/default.kicad_pcb
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
cd rigid_pcb
source ~/.atopile-env/bin/activate
ato validate main.ato
ato build --keep-designators --keep-net-names
```

封装以 `atopile_address` 属性作为电气真源实例。

管线脚本不处理布线，KiCad 仍负责:

- 元件放置决策
- 所有走线、过孔、敷铜和 DRC 清理
- 原理图 / 网表同步

## Status

当前分支已包含四步管线重建的 PCB。后续工作:

- 决定嵌入模块半孔应保留为电镀槽/半孔还是改为更宽的焊锡架
- 根据更新后的参考手工布线电源、USB/UART、LED、按钮和 PZT 网络
- 在制造前添加沉槽开孔的 fab 注释

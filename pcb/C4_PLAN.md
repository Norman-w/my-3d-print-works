# 电路 C4 改板计划

## 范围

C3（刚性 PCB，Gerber `20260724-081156`）已下单。下一版电路升为 **C4**：

1. PZT I²C 可调门槛比较器前端（DAC + 四比较器 + 高阻 ADC 窥探）
2. MCU 换 **ESP32-S3**（或更强；基线 S3-WROOM，具体闪存/PSRAM 选型改板时定）
3. 尾插 MX1.25 正反 5P **线序重排**：同一板坐标 X 上，正面 VCC 正对背面 GND（以及 USB/UART 成对），消除 C3 因背面 Flip+180° 造成的左右对调观感
4. 原 C4 规划项并入：电池焊盘、LED 等尽量直接拉到拍尾，减少飞线焊

外壳 SCAD 本轮不改（比较器/DAC 放大陆区）。版本表见 [`docs/README.md`](../docs/README.md)。

## 1. PZT 比较器前端

### 背景

- 四角压电做 TDOA 定位。
- C3：`PZTDock` = `1M + 4.7k + BAT54S` 直进 MCU GPIO；固件数字边沿。实测敲击常 ~0.1–0.5 V，偶发 ~2 V，到不了数字阈值；3V3 强制跳线可出 `IMPACT`。
- 不做：固定电阻门槛；只换 MCU 不改模拟前端。

### 架构

- 1× MCP4728（I²C 四路 DAC）→ 比较器 Vref
- 1× 四路比较器（优先 TLV1804；开漏则每路 10k 上拉到 3V3）
- 码头：`PZT → 1M∥地 → 4.7k → 钳位 → CMP_INx`
- 比较器输出 → MCU 四路边沿 GPIO（脚位随 S3 重分配）
- DEBUG：CMP 输入侧经 1M + 0Ω 跳线 → 独立 ADC 脚
- I²C：MCP4728，地址典型 `0x60`

### 工作项

- 写 `docs/PZT/comparator-frontend.md`（框图、脚位、0Ω、BOM、校准）
- 改 `pcb/main.ato`：`PZTDock` 模拟净 + `PztThresholdFrontend`
- 零件库：MCP4728 / 比较器 / 上拉
- netlist → 大陆区布局 → DRC
- 固件：I²C 设门槛；ADC 读窥探脚；边沿仍听比较器输出脚

### 验收

- 静置无误触发；贴 `JP_ADC*` 可见底噪
- 轻敲约 150–300 mV 门槛可出 `IMPACT`，对角 `first=` 正确
- 不贴 `JP_ADC*` 定位仍正常

## 2. MCU：ESP32-S3（或更强）

- 相对 C6：硬件 FPU、更多 RMT RX、GPIO/ADC 更宽裕（利于四路边沿 + 四路窥探 + I²C）。
- 基线：**ESP32-S3-WROOM-1**；若后续要双 IMU / 更重 onboard 融合，可再评估 P4 等。
- 连带：`pcb/lib` 模组封装与开孔、`pinmap`、固件 target、USB-JTAG/UART 脚位全部按新模组重做。
- 主线仍可先保持单 IMU；MCU 升级不强制跳到主线 V2（双 IMU）。

## 3. 尾插线序（相对 C3）

C3 背面插座 Flip+180° 后，板坐标上 **F.pn 与 B.p(6−n) 对齐**，导致正面 `sys_5v_in`(F.p1) 正对背面 `uart_rx`(B.p5)，而 GND 在另一端。接线别扭。

C4 目标：在**不改机械朝向**的前提下重排网络，使同 X 成对合理。详表见 [`docs/1.25x10p/README.md`](../docs/1.25x10p/README.md)「C4 目标线序」。

原则：

| 同 X 成对 | 正面 | 背面 |
|-----------|------|------|
| 电源 | `sys_5v_in` | `gnd` |
| USB | `usb_dp` | `usb_dn` |
| UART | `uart_tx` | `uart_rx` |

（其余脚：`sys_5v_sw` / `btn_sw` / `led_din` / `bat_cell_p` 按同原则排入。）

改 `main.ato` 里 `tail.conn_f` / `conn_b` 网络映射，并同步装配图 / 接线 HTML。

## 4. 原 C4 机械/电源拉尾

- 电池焊盘、LED 供电与数据尽量在拍尾就近出线，减少飞线焊（与尾插重排一并布局）。

## 本版不做

- 不改 SCAD 耳槽尺寸
- 不用片内 ADC 做正式 TDOA 时间源
- 不在比较器输出脚上兼做 ADC

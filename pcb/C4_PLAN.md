# 电路 C4 改板计划

## 范围

C3（刚性 PCB，Gerber `20260724-081156`）已下单。下一版电路升为 **C4**：

1. PZT I²C 可调门槛比较器前端（DAC + 四比较器 + 高阻 ADC 窥探）
2. MCU 换 **ESP32-S3-WROOM-1-N16R8**（16 MB Flash + 8 MB Octal PSRAM）
3. 尾插 MX1.25 正反 5P **线序重排**：同一板坐标 X 上，正面 VCC 正对背面 GND（以及 USB/UART 成对），消除 C3 因背面 Flip+180° 造成的左右对调观感
4. 原 C4 规划项并入：电池焊盘、LED 等尽量直接拉到拍尾，减少飞线焊

外壳 SCAD 本轮不改（比较器/DAC 放大陆区）。版本表见 [`docs/README.md`](../docs/README.md)。

当前交接状态：电气源、封装/脚位、固件及 atopile 0.12.5 的 Step 3.1→3.2 生成/复核由 Codex 完成；ESP-IDF 5.5.1 的 `esp32s3` 干净构建已通过。器件由 Norman 在 KiCad 手工摆放，完成后再由 Codex 回存 snapshot/放置脚本；KiCad 铜线仍由 Norman 手工完成，清单见 [`C4_ROUTING_HANDOFF.md`](C4_ROUTING_HANDOFF.md)。C3 铜线不迁移到 C4。

## 1. PZT 比较器前端

### 背景

- 四角压电做 TDOA 定位。
- C3：`PZTDock` = `1M + 4.7k + BAT54S` 直进 MCU GPIO；固件数字边沿。实测敲击常 ~0.1–0.5 V，偶发 ~2 V，到不了数字阈值；3V3 强制跳线可出 `IMPACT`。
- 不做：固定电阻门槛；只换 MCU 不改模拟前端。

### 架构

- 1× MCP4728（I²C 四路 DAC）→ 比较器 Vref
- 1× TLV1814PWR 四路比较器（3.3 V、推挽输出；无需输出上拉）
- 码头：`PZT → 1M∥地 → 4.7k → 钳位 → CMP_INx`
- 比较器输出 → MCU 四路边沿 GPIO（脚位随 S3 重分配）
- DEBUG：CMP 输入侧经 1M + 0Ω 跳线 → 独立 ADC 脚
- I²C：MCP4728，地址典型 `0x60`

> 料号更正：TI 没有计划中所写的 `TLV1804`；对应四路推挽型号是 `TLV1814`。若改用开漏 `TLV1824`，才需要四路上拉。

### 工作项

- [x] 写 `docs/PZT/comparator-frontend.md`（框图、脚位、0Ω、BOM、校准）
- [x] 改 `pcb/main.ato`：`PZTDock` 模拟网 + `PztThresholdFrontend`
- [x] 零件库：MCP4728 / TLV1814 / I²C 上拉 / 去耦
- [x] 以受审 C4 pad→net 表迁移板文件、加入元件并清空 C3 铜线；`validate_c4_unrouted_board.py` 复核交接态
- [x] 收口 Step 3.2 C4 安全导入器：实际历史 `.net` 格式/嵌套路径解析、源文件时效门禁、64 地址 + 183 已连接焊盘号拓扑核对、旧 C3/拆网/并网/已有铜线拒绝
- [x] 生成并渲染复核 C4 可打印装配包（16 页 A4、64 封装、DNP/Pad 1/顶底面/检查清单）及 MX1.25 尾插图；PCB 标题栏写入 C4
- [x] 经项目标准入口 `scripts/scad_to_kicad.sh` 的 Step 3.1，用标准路径实际版本 atopile 0.12.5 生成新 C4 网表；Step 3.2 自动复核/导入及无摆放元数据收尾均通过
- [x] C4 制造说明、`Cmts.User` Fab 注释与安全导出门禁完成；A4 Fab 图渲染复核通过，未布线状态只产预检报告且禁止 Gerber/钻孔/ZIP
- [ ] KiCad 手工摆放器件（Norman）；完成后由 Codex 用 Step 4.1e 回存 64 器件 `c4_placement_snapshot.json`、接入放置脚本并重生成装配资料
- [ ] KiCad 手工布线、铺铜与最终 DRC（Norman）
- [x] 固件：I²C 设门槛；独立 ADC 窥探；边沿只听比较器输出脚

### 验收

- 静置无误触发；贴 `JP_ADC*` 可见底噪
- 轻敲约 150–300 mV 门槛可出 `IMPACT`，对角 `first=` 正确
- 不贴 `JP_ADC*` 定位仍正常

## 2. MCU：ESP32-S3（或更强）

- 相对 C6：硬件 FPU、更多 RMT RX、GPIO/ADC 更宽裕（利于四路边沿 + 四路窥探 + I²C）。
- 锁定：**ESP32-S3-WROOM-1-N16R8**；16 MB Flash、8 MB Octal PSRAM。GPIO35–37 被 PSRAM 占用，不分配。
- 连带：`pcb/lib` 模组封装与开孔、`pinmap`、固件 target、USB-JTAG/UART 脚位全部按新模组重做。
- 主线仍可先保持单 IMU；MCU 升级不强制跳到主线 V2（双 IMU）。

## 3. 尾插线序（相对 C3）

C3 背面插座 Flip+180° 后，板坐标上 **F.pn 与 B.p(6−n) 对齐**，导致正面 `sys_5v_in`(F.p1) 正对背面 `uart_rx`(B.p5)，而 GND 在另一端。接线别扭。

C4 已在电气源中按**不改机械朝向**的原则重排网络。现行表见 [`docs/1.25x10p/README.md`](../docs/1.25x10p/README.md)。

原则：

| 同 X 成对 | 正面 | 背面 |
|-----------|------|------|
| 电源 | `sys_5v_in` | `gnd` |
| USB | `usb_dp` | `usb_dn` |
| UART | `uart_tx` | `uart_rx` |

（其余脚：`sys_5v_sw` / `btn_sw` / `led_din` / `bat_cell_p` 按同原则排入。）

映射必须同时出现在 `main.ato`、`step3_import_netlist.py`、`step4_ato_placement.py`、`apply_tail_mx125.py` 与 C4 迁移校验表，并同步装配图 / 接线 HTML。

## 4. 原 C4 机械/电源拉尾

- 电池分压、LED 供电去耦与数据串阻放到拍尾、在 MX1.25 前方就近布线，减少飞线焊。

## 本版不做

- 不改 SCAD 耳槽尺寸
- 不用片内 ADC 做正式 TDOA 时间源
- 不在比较器输出脚上兼做 ADC

# 主板与尾板 KiCad 手工布线交接

本文件是当前 **M7.C5** 组合在 2026-08-15 电源架构重整及机械/射频固化后的手工布线清单。版本号只记录在标题栏与说明中；本文件名、同步脚本和 PCB 文件名均保持跨版本通用。电气真理源为 `main.ato`；MCU 脚位为 `lib/esp32s3wroom1/pinmap.py`；尾插为 `docs/1.25x10p/README.md`；跨层依据见 `docs/power-architecture-rework/README.md` 与 `docs/mechanical-handoff/README.md`。

## 开始前门禁

- 板上 MCU 必须是 `MCU_ESP32_S3` / ESP32-S3-WROOM-1-N16R8，不得残留 C6 封装。
- MCU footprint 必须含且只含一个 `ESP32_ANTENNA_HOST_KEEP_OUT`：覆盖 F.Cu/B.Cu，并同时禁止 tracks、vias、pads、copper pour 和 footprints；它是规则区，不计入 copper-zone 数量。
- `PZT_DAC_MCP4728`、`PZT_CMP_TLV9034`、四颗 `JP_ADC_*` 与两颗去耦必须都在板上。
- 尾插背面必须为 B.p1=`uart_rx`、B.p2=`usb_dn_conn`、B.p3=`bat_cell_p`、B.p4=`led_din`、B.p5=`gnd`。
- `SW_BOOT`、`SW_EN`、`SW_PWR` 必须均为 Omron `B3U-1000P` SMD 且 Value 含 DNP；不得为三只调试键另开壳孔。
- 开始布线时应为 67 个封装、0 track、0 via、0 copper zone、141 个未连接；该数字必须与 `validate_power_rework.py` 门禁基线一致。`TP_3V3` / `TP_5VSW` 已删，电源仍从 buck 输出电容、负载 MOS 源极或夹持点测量。

2026-08-23 当前工作区已完成上述主板/尾板手工布线和 GND 铺铜；主板为 1062 段线/142 过孔，尾板为 502 段线/53 过孔。PZT 四角焊盘簇保持既定位姿，主板天线规则区未被铜或器件侵入。两板已通过 `validate_power_rework.py --release-gate --target all`，当前可作为工程样板下单；回板实测仍未完成。

当前制造放行复核命令：

```sh
python3 scripts/validate_power_rework.py --release-gate --target all
```

旧 C4 无布线交接曾为 63/64 件；这些数字及 `c4_unrouted_drc.json` 都是历史快照。当前电源、按键、USB 和 MCU 支撑器件扩展、并去掉两颗 bringup 测试焊盘后，Atopile/PCB 均为 67 个唯一 `atopile_address`，必须使用新的同步与审计脚本。

板文件标题栏为 `SmartPaddle Main PCB / C5`，尾板标题栏为 `SmartPaddle Tail PCB / C5`。Atopile 0.12.5 只允许构建 `layouts/staging/`，连续构建两次后再由 `sync_power_architecture.py` 按地址和 pad 显式同步；不能运行旧 `step3_import_netlist.py` 改写当前板。同步后运行：

```sh
/usr/bin/env python3 pcb/scripts/validate_esp32s3wroom1_pinmap.py
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 \
  pcb/scripts/audit_power_architecture.py
```

BR ADC 使用 GPIO8/pad12，GPIO5/pad5 保持未用；IMU UART 为 GPIO41/pad34 TX、GPIO40/pad33 RX。项目锁定的 ESP-IDF 5.5.1 `esp32s3` 已在本轮完整构建通过，16 MB Flash、80 MHz、Octal PSRAM 配置生效，最小 2 MB app 分区剩余 58%。

旧版摆放、布线、铺铜、63 件位置快照和装配包均已失效，仅供 Git 历史参考。当前 67 件位姿已写入 PCB 和 `place_power_architecture.py`；用户应在现板上重新布线，不要套用 C3/C4 旧铜或旧装配图。

## 建议顺序

先完成全部元件手工摆放并回存位置脚本，确认尾插正反面、S3/IMU 半孔和 PZT 焊线焊盘方向，再进入以下布线顺序。

### 主板

1. 先布 TPS62162 开关回路：`SYS_5V_SW -> C_IN/VIN`、`SW -> XFL3012 -> C_OUT/3V3`、PGND/AGND/EP 与电容地最短闭环；再布 `sys_5v_in`、`sys_5v_sw` 与其余 3V3/GND。
2. S3 perimeter GND pad 1、pad 40 分别短接地并就近打接地过孔。嵌入开孔无法接 EP41，不可漏做。模块天线朝 `−X`；任何铜、焊盘、过孔或器件都不得进入 `ESP32_ANTENNA_HOST_KEEP_OUT`，也不得用天线侧绕 TPS62162 或数字线。
3. 原生 USB：F.p4 `usb_dp_conn` / B.p2 `usb_dn_conn` 成对走到靠近 MCU 的 22Ω；阻后 `usb_dp/usb_dn` 再分别短接 S3 pad14/pad13。成对、等环境、少过孔。
4. PZT 模拟：四个 `CMP_IN_*` 到 TLV9034 IN+；四个 DAC VREF 到 IN−。避开 LED/电源开关网。`PZT_C_CMP_100N` 必须贴 TLV9034 pin 3/12，不要放到 USB 22R 那一行。
5. PZT 数字边沿：TL/TR/BL/BR → GPIO16/15/6/7，保持短且环境相近。TL/TR 有意使用 TLV9034 通道 2/1，使 `CMP_IN_TL/TR` 分别落到 pin 7/5，避免比较器前交叉。
6. I²C GPIO17/18；IMU UART 为 GPIO41/pad34 TX→IMU RXD/pad13、GPIO40/pad33 RX←IMU TXD/pad14；再处理 UART0 GPIO43/44、控制键与 LED。三只主板 B3U 均为 DNP 调试件，不为其布置外壳日常操作结构。
7. 拍尾局部：电池分压、LED 供电/数据到 MX1.25；确认 `bat_cell_p` 绝不是 5V 网。
8. 最后处理四路 1M+`JP_ADC_*`；BR ADC 使用 GPIO8/pad12，GPIO5/pad5 保持未用。跳线标注 DNP，不能把 ADC 接到比较器输出。

### 尾板

1. 先布 USB 入口电源：J1 VBUS 四触点汇合后到 `u_vbus_limit`、输入 100nF 与 59k ILIM；GND 触点与外壳就近回地。A8/B8、两颗 `/FAULT` 均保持 NC。
2. 再布 IP5305T 充电/升压功率环：`vbus_limited -> VIN` 及两级输入电容；`BAT_P -> c_bat/J4/J2.3/L_boost`；`SW -> L_boost -> BAT_P` 与 `VOUT -> c_vout/c_vout2` 均按最短高电流闭环处理，SW 铜岛不得靠近 USB 数据线、CC、按键或 LED 数据。
3. 布系统 5V 限流：`vout_5v_raw -> u_system_limit -> vout_5v/J2.1`，43.2k ILIM 和输入/输出 100nF 紧贴芯片；不要把 `BAT_P`、`vout_5v_raw`、`vout_5v` 混成同一铜岛。
4. 完成上述功率区的连续 GND 回流和 IP5305T EP 散热/接地，再处理其 LED1/LED2/LED3 指示支路与 KEY 单向隔离。
5. J1 D+/D− 从触点对先到 USBLC6，再由 `usb_dp/usb_dn` 成对走到 J3；保持等环境、少过孔，远离 SW 节点、两颗限流器 ILIM 与 LED 开关电流。
6. 布 B3U `user_btn`、J3.3、KEY 隔离，再布 AHCT/WS2812 的 `v5_sw_return`、去耦和 `led_data`。AHCT 去耦与尾灯去耦各自贴近供电脚。
7. 最后收尾 J2/J3/J4，并逐芯复核 [`../pcb-tail/ADAPTER_HARNESS.md`](../pcb-tail/ADAPTER_HARNESS.md)：J4.1/J2.3 只能是 `BAT_P`，J4.2/J2.2 为 GND，J2.4 是主板开关后的 5V 回线。

## 收尾门禁（工程样板状态）

- [x] 两板布线和铺地完成；主板/尾板 DRC 均 0 error、0 未连接（尾板保留 3 条已审计 warning）。
- [ ] TPS62162 高频回路、USB 差分、PZT 模拟/数字、两板电源和地回流逐网人工复核。
- [x] 无无网络铜；67 件位姿未被意外移动；S3/IM948 开槽和尾插机械复核。
- [x] Atopile 源、关键物理 pin/net、J1 16 触点、线束和 ESP-IDF 5.5.1 构建已通过自动审计。
- [x] 受保护 14500 最大包络、左右两束 4×28AWG 通道和 8 个 PZT 圆孔中心让位已写入同一机械契约，并由当前 PCB 坐标反查通过；预览见 [`../docs/mechanical-handoff/README.md`](../docs/mechanical-handoff/README.md)。
- [x] 主板三只 B3U 的 DNP/位姿与 ESP32 双面天线规则区已纳入同步审计；布线过程中不得移动既有元件或删掉规则区。
- [x] B3U 中心 Ø2.0mm 直通针孔已与当前 SW1 位姿和 3D 壳体核对，可作为独立操作基准。
- [ ] 若产品采用可选 B3U 防脱推杆，再用尾段试片闭合其最坏行程公差；该附件不替代针孔基准。
- [ ] 回板后验证实际焊点、供电、USB、PZT、射频和热；机器门禁不能替代这些实物项。

布线完成后先运行跨层门禁：

```sh
python3 scripts/validate_power_rework.py --release-gate
```

只有跨层门禁通过，制造导出脚本才会继续；失败门禁不能用 `--allow-errors` 或跳过旧网表参数绕过。当前独立 Gerber、钻孔和上传 ZIP 已生成于 `fab/jlcpcb-orders/20260823-m7c5/`。

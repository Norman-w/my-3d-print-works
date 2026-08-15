# C4 KiCad 手工布线交接

本文件是 2026-08-15 电源架构重整后的手工布线清单。电气真理源为 `main.ato`；MCU 脚位为 `lib/esp32s3wroom1/pinmap.py`；尾插为 `docs/1.25x10p/README.md`；跨层依据见 `docs/power-architecture-rework/README.md`。

## 开始前门禁

- 板上 MCU 必须是 `MCU_ESP32_S3` / ESP32-S3-WROOM-1-N16R8，不得残留 C6 封装。
- `PZT_DAC_MCP4728`、`PZT_CMP_TLV1814`、四颗 `JP_ADC_*` 与两颗去耦必须都在板上。
- 尾插背面必须为 B.p1=`uart_rx`、B.p2=`usb_dn_conn`、B.p3=`bat_cell_p`、B.p4=`led_din`、B.p5=`gnd`。
- 开始布线时应为 69 个封装、0 track、0 via、0 copper zone；当前 DRC 的 149 个未连接是这一交接态的预期值。

当前无铜交接态复核命令：

```sh
python3 scripts/validate_power_rework.py
```

旧 C4 无布线交接曾为 63/64 件；这些数字及 `c4_unrouted_drc.json` 都是历史快照。当前电源、按键、USB 和 MCU 支撑器件扩展后，Atopile/PCB 均为 69 个唯一 `atopile_address`，必须使用新的同步与审计脚本。

板文件标题栏为 `SmartPaddle Rigid PCB / C4`。Atopile 0.12.5 只允许构建 `layouts/staging/`，连续构建两次后再由 `sync_power_architecture.py` 按地址和 pad 显式同步；不能运行旧 `step3_import_netlist.py` 改写当前板。同步后运行：

```sh
/usr/bin/env python3 pcb/scripts/validate_esp32s3wroom1_pinmap.py
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 \
  pcb/scripts/audit_power_architecture.py
```

BR ADC 使用 GPIO8/pad12，GPIO5/pad5 保持未用；IMU UART 为 GPIO41/pad34 TX、GPIO40/pad33 RX。项目锁定的 ESP-IDF 5.5.1 `esp32s3` 已在本轮完整构建通过，16 MB Flash、80 MHz、Octal PSRAM 配置生效，最小 2 MB app 分区剩余 58%。

旧版摆放、布线、铺铜、63 件位置快照和装配包均已失效，仅供 Git 历史参考。当前 69 件位姿已写入 PCB 和 `place_power_architecture.py`；用户应在现板上重新布线，不要套用 C3/C4 旧铜或旧装配图。

## 建议顺序

先完成全部元件手工摆放并回存位置脚本，确认尾插正反面、S3/IMU 半孔和 PZT 焊线焊盘方向，再进入以下布线顺序。

1. 先布 TPS62162 开关回路：`SYS_5V_SW -> C_IN/VIN`、`SW -> XFL3012 -> C_OUT/3V3`、PGND/AGND/EP 与电容地最短闭环；再布 `sys_5v_in`、`sys_5v_sw` 与其余 3V3/GND。
2. S3 perimeter GND pad 1、pad 40 分别短接地并就近打接地过孔。嵌入开孔无法接 EP41，不可漏做。
3. 原生 USB：F.p4 `usb_dp_conn` / B.p2 `usb_dn_conn` 成对走到靠近 MCU 的 22Ω；阻后 `usb_dp/usb_dn` 再分别短接 S3 pad14/pad13。成对、等环境、少过孔。
4. PZT 模拟：四个 `CMP_IN_*` 到 TLV1814 IN+；四个 DAC VREF 到 IN−。避开 LED/电源开关网。
5. PZT 数字边沿：TL/TR/BL/BR → GPIO16/15/6/7，保持短且环境相近。TL/TR 有意使用 TLV1814 通道 2/1，使 `CMP_IN_TL/TR` 分别落到 pin 7/5，避免比较器前交叉。
6. I²C GPIO17/18；IMU UART 为 GPIO41/pad34 TX→IMU RXD/pad13、GPIO40/pad33 RX←IMU TXD/pad14；再处理 UART0 GPIO43/44、控制键与 LED。
7. 拍尾局部：电池分压、LED 供电/数据到 MX1.25；确认 `bat_cell_p` 绝不是 5V 网。
8. 最后处理四路 1M+`JP_ADC_*`；BR ADC 使用 GPIO8/pad12，GPIO5/pad5 保持未用。跳线标注 DNP，不能把 ADC 接到比较器输出。

## 收尾门禁（当前全部重新开放）

- [ ] 两板布线和铺地完成；主板/尾板 DRC 均 0 规则违规、0 未连接。
- [ ] TPS62162 高频回路、USB 差分、PZT 模拟/数字、两板电源和地回流逐网人工复核。
- [ ] 无无网络铜；69 件位姿未被意外移动；S3/IM948 开槽和尾插机械复核。
- [x] Atopile 源、关键物理 pin/net、J1 16 触点、线束和 ESP-IDF 5.5.1 构建已通过自动审计。
- [ ] B3U 活动推杆尾段试片闭合最坏公差，并把 `tolerance_closed` 改为有实测证据的 true。
- [ ] 回板后验证实际焊点、供电、USB、PZT、射频和热；机器门禁不能替代这些实物项。

布线完成后先运行跨层门禁：

```sh
python3 scripts/validate_power_rework.py --release-gate
```

只有跨层门禁通过，制造导出脚本才会继续；失败门禁不能用 `--allow-errors` 或跳过旧网表参数绕过。当前任务明确不生成 Gerber、钻孔或上传 ZIP。

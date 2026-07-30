# C4 KiCad 手工布线交接

本文件是 C4 电气生成完成后的手工摆放/布线清单。电气真理源为 `main.ato`；MCU 脚位为 `lib/esp32s3wroom1/pinmap.py`；尾插为 `docs/1.25x10p/README.md`。

## 开始前门禁

- 板上 MCU 必须是 `MCU_ESP32_S3` / ESP32-S3-WROOM-1-N16R8，不得残留 C6 封装。
- `PZT_DAC_MCP4728`、`PZT_CMP_TLV1814`、四颗 `JP_ADC_*` 与两颗去耦必须都在板上。
- 尾插背面必须为 B.p1=`uart_rx`、B.p2=`usb_dn`、B.p3=`bat_cell_p`、B.p4=`led_din`、B.p5=`gnd`。
- 开始布线时应为 0 track、0 via、0 非规则 copper zone；C3 铜线只保留在 Git/Gerber `20260724-081156` 中参考。

只读复核命令：

```sh
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 \
  pcb/scripts/validate_c4_unrouted_board.py
```

最初的无布线交接板为 64 件；Norman 开始手工工作后明确取消仅供 bringup 的独立 `TP_GND`，当前电气源、网表与板统一为 63/63 个 `atopile_address`。已归档的 [DRC 基线](layouts/default/output/c4_unrouted_drc.json)仍是取消测试盘前的 64 件历史快照，只用于说明当时不存在非布线 error；当前在制板必须以实时 DRC 为准。

板文件标题栏已经写入 `SmartPaddle Rigid PCB / C4`。2026-07-30 用项目标准路径实际运行 atopile 0.12.5，Step 3.1 明确 `Build successful`；取消 `TP_GND` 及对调 TL/TR 通道后，Step 3.2 只读门禁通过 63 地址/182 个已连接焊盘号，当前板 188 个相应实体焊盘全部对网。Atopile 安全包装器构建前后保持 PCB 字节哈希一致。Norman 已开始布线，因此后续只运行 pinmap 校验与 `--check-only`，不得让 Step 3.2 改写板文件：

```sh
/usr/bin/env python3 pcb/scripts/validate_esp32s3wroom1_pinmap.py
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 \
  pcb/scripts/step3_import_netlist.py --check-only
```

同日进一步把 BR ADC 从 GPIO5/pad5 移到更靠右的 GPIO8/pad12，并在 MCU 侧交换 IMU UART 角色以消除飞线交叉：GPIO41/pad34 为 TX，GPIO40/pad33 为 RX。项目锁定的 ESP-IDF 5.5.1 `esp32s3` 干净构建通过：16 MB Flash、80 MHz、Octal PSRAM 配置生效，`smartpaddle.bin` 为 873,488 字节，最小 2 MB app 分区剩余 58%。QIO 选择下烧录参数显示 DIO 是 ESP-IDF 的预期行为：ROM/首段以 DIO 装载，二级 bootloader 再切换 Quad 模式。

Norman 确认手工摆放完成后，Codex 已从项目菜单运行 **Step 4.1e**，一次备份全部 63 个 `atopile_address` 的坐标、绝对角度和正反面到 `layouts/default/c4_placement_snapshot.json`。快照默认拒绝覆盖；确需替换时必须显式使用 `--replace`。Step 4 在最终保存前会优先恢复这份全板快照，覆盖旧大陆/码头/栈道/尾插区域默认值；制造预检也会拒绝缺失或与当前板不一致的全板快照。

Norman 已完成摆放、布线和铺铜；本文件以下顺序保留作设计记录。Step 4.1e 已回存并复核 63 件全板快照，最终 14 页装配包已按当前 PCB SHA 生成到本地 `output/pdf/smartpaddle-ai-assembly/`。不能沿用摆放前 16 页包，也不能混用 C3/V3 装配图。可制造性与回板测试边界见 [`C4_FAB_READINESS.md`](C4_FAB_READINESS.md)。

## 建议顺序

先完成全部元件手工摆放并回存位置脚本，确认尾插正反面、S3/IMU 半孔和 PZT 焊线焊盘方向，再进入以下布线顺序。

1. 3V3、`sys_5v_in`、`sys_5v_sw` 与 GND；先完成 DAC/比较器/MCU 去耦回路。
2. S3 perimeter GND pad 1、pad 40 分别短接地并就近打接地过孔。嵌入开孔无法接 EP41，不可漏做。
3. 原生 USB：F.p4 D+ ↔ S3 GPIO20/pad14；B.p2 D− ↔ GPIO19/pad13。成对、等环境、少过孔。
4. PZT 模拟：四个 `CMP_IN_*` 到 TLV1814 IN+；四个 DAC VREF 到 IN−。避开 LED/电源开关网。
5. PZT 数字边沿：TL/TR/BL/BR → GPIO16/15/6/7，保持短且环境相近。TL/TR 有意使用 TLV1814 通道 2/1，使 `CMP_IN_TL/TR` 分别落到 pin 7/5，避免比较器前交叉。
6. I²C GPIO17/18；IMU UART 为 GPIO41/pad34 TX→IMU RXD/pad13、GPIO40/pad33 RX←IMU TXD/pad14；再处理 UART0 GPIO43/44、控制键与 LED。
7. 拍尾局部：电池分压、LED 供电/数据到 MX1.25；确认 `bat_cell_p` 绝不是 5V 网。
8. 最后处理四路 1M+`JP_ADC_*`；BR ADC 使用 GPIO8/pad12，GPIO5/pad5 保持未用。跳线标注 DNP，不能把 ADC 接到比较器输出。

## 收尾门禁（2026-07-30 已完成机器项）

- [x] 更新铺铜后 DRC 0 error / 0 未连接；72 项 warning 已分类复核。
- [x] USB D+/D−、四路比较器边沿、四路 ADC、I²C、UART 与全部电源网由网表、物理焊盘和 DRC 三层门禁复核。
- [x] 无无网络铜；63 件位置快照与当前板一致。
- [x] S3/IM948 内部开槽、正反 MX1.25、Fab 图与钻孔图人工复核。
- [x] S3 pinmap、Atopile 0.12.5 安全构建和 ESP-IDF 5.5.1 干净构建通过。
- [ ] 回板后验证实际焊点、供电、USB、PZT、射频和热；机器门禁不能替代这些实物项。

先运行只产报告/Fab 图的生产预检：

```sh
python3 pcb/scripts/export_jlcpcb.py --preflight-only
```

只有输出 `Preflight OK` 时，才可去掉 `--preflight-only` 生成 Gerber、钻孔和上传 ZIP；失败门禁不能用 `--allow-errors` 绕过生成 ZIP。订单参数与厂家备注见 [`C4_FAB_NOTES.md`](C4_FAB_NOTES.md)。

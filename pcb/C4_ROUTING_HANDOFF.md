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

当前基线结果为 64/64 个 `atopile_address` 全 pad 对网、0 track/via、0 非规则铜区。[DRC 基线](layouts/default/output/c4_unrouted_drc.json)记录 0 个非布线 error、137 个预期未连接项和 38 个 warning（17×板边丝印、14×丝印压阻焊、7×丝印相交）；不含间距、短路、封装重叠、库版本差异或镜像文本错误。剩余警告来自必须保留识别文字的 PZT 边缘焊盘，以及尾插/开关等跨阻焊的元件轮廓。

板文件标题栏已经写入 `SmartPaddle Rigid PCB / C4`。2026-07-29 已由项目标准入口实际运行 atopile 0.12.5，Step 3.1 明确 `Build successful`；Step 3.2 随后通过 64 地址/183 个已连接焊盘号门禁，给 189 个实体焊盘赋网，并在不改变任何元件坐标/角度/板层的前提下恢复可读字段、DNP 和背面尾插几何。Norman 手工摆放完成后应先让 Codex 回存 snapshot/放置脚本，再开始布线。若已经开始布线，只做只读拓扑核对，避免写板：

```sh
/usr/bin/env python3 pcb/scripts/validate_esp32s3wroom1_pinmap.py
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 \
  pcb/scripts/step3_import_netlist.py --check-only
```

同日用项目锁定的 ESP-IDF 5.5.1 完成 `esp32s3` 干净构建：16 MB Flash、80 MHz、Octal PSRAM 配置生效，`smartpaddle.bin` 为 873,456 字节，最小 2 MB app 分区剩余 58%。QIO 选择下烧录参数显示 DIO 是 ESP-IDF 的预期行为：ROM/首段以 DIO 装载，二级 bootloader 再切换 Quad 模式。

Norman 确认手工摆放完成后，由 Codex 从项目菜单运行 **Step 4.1e**，一次备份全部 64 个 `atopile_address` 的坐标、绝对角度和正反面到 `layouts/default/c4_placement_snapshot.json`。快照默认拒绝覆盖；确需替换时必须显式使用 `--replace`。Step 4 在最终保存前会优先恢复这份全板快照，覆盖旧大陆/码头/栈道/尾插区域默认值；制造预检也会拒绝缺失或与当前板不一致的全板快照。

可打印 C4 装配包见 [`output/pdf/assembly-package/`](../output/pdf/assembly-package/)；现有文件是摆放前快照，不能作为最终装配依据。Norman 完成摆放并由 Codex 回存位置后须重新生成；完成布线后还需再生成一次，不能沿用 C3/V3 装配图。

## 建议顺序

先完成全部元件手工摆放并回存位置脚本，确认尾插正反面、S3/IMU 半孔和 PZT 焊线焊盘方向，再进入以下布线顺序。

1. 3V3、`sys_5v_in`、`sys_5v_sw` 与 GND；先完成 DAC/比较器/MCU 去耦回路。
2. S3 perimeter GND pad 1、pad 40 分别短接地并就近打接地过孔。嵌入开孔无法接 EP41，不可漏做。
3. 原生 USB：F.p4 D+ ↔ S3 GPIO20/pad14；B.p2 D− ↔ GPIO19/pad13。成对、等环境、少过孔。
4. PZT 模拟：四个 `CMP_IN_*` 到 TLV1814 IN+；四个 DAC VREF 到 IN−。避开 LED/电源开关网。
5. PZT 数字边沿：TL/TR/BL/BR → GPIO15/16/6/7，保持短且环境相近。
6. I²C GPIO17/18、IMU UART GPIO40/41、UART0 GPIO43/44、控制键与 LED。
7. 拍尾局部：电池分压、LED 供电/数据到 MX1.25；确认 `bat_cell_p` 绝不是 5V 网。
8. 最后处理四路 1M+`JP_ADC_*`；跳线标注 DNP，不能把 ADC 接到比较器输出。

## 收尾门禁

- 更新铺铜后 DRC 0 error；逐项解释或消除 warning。
- USB D+/D−、四路比较器边沿、四路 ADC、I²C、UART 与全部电源网逐网连通。
- 无悬空铜、无意外同网短接、无跨开槽铜皮。
- 用 3D Viewer 检查 S3/IM948 半孔、正反 MX1.25 与拍尾器件的面/朝向。
- 生产文件导出前重新运行 S3 pinmap 校验与固件 S3 构建。

先运行只产报告/Fab 图的生产预检：

```sh
python3 pcb/scripts/export_jlcpcb.py --preflight-only
```

只有输出 `Preflight OK` 时，才可去掉 `--preflight-only` 生成 Gerber、钻孔和上传 ZIP；失败门禁不能用 `--allow-errors` 绕过生成 ZIP。订单参数与厂家备注见 [`C4_FAB_NOTES.md`](C4_FAB_NOTES.md)。

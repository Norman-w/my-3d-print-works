# C4 PZT 可调门槛比较器前端

## 目标与边界

C4 仍以四路比较器输出的上升沿做 TDOA。片内 ADC 只用于调试窥探，不能作为正式时间源，也不能与比较器输出复用脚位。

```
PZT ── 1M 泄放 ── 4.7k ── BAT54S 钳位 ── CMP_INx ── TLV1814 IN+
                                              │
MCP4728 VOUTx ─────────────────────────────── TLV1814 IN−
                                              │
                                              └── OUTx ── S3 边沿 GPIO

CMP_INx ── 1M ── JP_ADC_x（0R，默认 DNP）── S3 独立 ADC1 GPIO
```

比较器输入超过 DAC 门槛时输出高电平。TLV1814 是 3.3 V 供电的推挽输出器件，因此四路输出不装 10k 上拉；早期计划里的 `TLV1804` 是料号笔误。

## 器件与无源件

| 数量 | 器件 | 料号 / 封装 | 备注 |
|---:|---|---|---|
| 1 | 四路 DAC | MCP4728-E/UN，MSOP-10 | I²C 地址 `0x60`，内部 2.048 V 基准，增益 ×1 |
| 1 | 四路比较器 | TLV1814PWR，TSSOP-14 | 2.4–40 V、轨到轨输入、推挽输出 |
| 2 | I²C 上拉 | 4.7k，0603 | SDA/SCL → 3V3 |
| 2 | 去耦 | 100nF，0603 | DAC 与比较器各一颗，贴近电源脚 |
| 4 | ADC 隔离 | 1M，0603 | 从 `CMP_INx` 到调试节点 |
| 4 | ADC 跳线 | 0R，0603 | `JP_ADC_TL/TR/BL/BR`，量产默认 DNP |
| 每码头 | 原 PZT 网络 | 1M + 4.7k + BAT54S | 码头侧保留，输出改名为 `CMP_INx` |

器件依据：[MCP4728 产品页与数据手册](https://www.microchip.com/en-us/product/MCP4728)、[TLV1814 产品页与数据手册](https://www.ti.com/product/TLV1814)。

## 通道与脚位真理表

| 位置 | MCP4728 | TLV1814 通道 | 比较器边沿 GPIO | ADC 窥探 GPIO |
|---|---|---:|---:|---:|
| TL | A / VOUTA pin 1 | 1：IN− pin 4、IN+ pin 5、OUT pin 2 | GPIO15 | GPIO1 / ADC1_CH0 |
| TR | B / VOUTB pin 2 | 2：IN− pin 6、IN+ pin 7、OUT pin 1 | GPIO16 | GPIO2 / ADC1_CH1 |
| BL | C / VOUTC pin 3 | 3：IN− pin 8、IN+ pin 9、OUT pin 14 | GPIO6 | GPIO4 / ADC1_CH3 |
| BR | D / VOUTD pin 4 | 4：IN− pin 10、IN+ pin 11、OUT pin 13 | GPIO7 | GPIO5 / ADC1_CH4 |

公共脚：MCP4728 pin 5=GND、6=`/LDAC`→GND、7=SCL/GPIO18、8=SDA/GPIO17、9=3V3、10=`/RDY`悬空；TLV1814 pin 3=3V3、12=GND。

MCU 全表以 `pcb/lib/esp32s3wroom1/pinmap.py` 为准。N16R8 的 GPIO35–37 被八线 PSRAM 占用，不得分配。

## 固件行为

- `pzt_frontend::init()` 以 400 kHz 初始化 I²C0，并把 A/B/C/D 写成 220 mV。
- MCP4728 使用 Multi-Write，仅更新输入寄存器，不写 EEPROM；`/LDAC` 接地使输出随写入更新。
- 内部基准增益 ×1 时 LSB 为 0.5 mV；换算为 `code = clamp(round(mV × 4096 / 2048), 0, 4095)`。
- 比较器四路使用 GPIO 上升沿中断与 CPU cycle 时间戳。
- `PZT_ADC_PEEK_ENABLE=0` 为默认；只有焊上对应 `JP_ADC_*` 后才可改成 1。未焊跳线时禁止声称 ADC 数据有效。
- DAC 不在线时仅禁用 PZT 碰撞采集，IMU、网络和维护功能继续运行。

## 调试与校准

1. 保持四颗 `JP_ADC_*` DNP，上电确认四路比较器静置无连续边沿。
2. 如需查看底噪，只焊一颗对应跳线并启用 `PZT_ADC_PEEK_ENABLE`；调试完恢复 DNP。
3. 从 300 mV 开始逐路轻敲，按 10–20 mV 步进下降；目标工作区约 150–300 mV。
4. 每路记录“静置无误触发”的最低门槛，再增加至少 20 mV 裕量。
5. 按 TL/TR/BL/BR 逐角敲击，确认日志 `first=` 与物理角一致，再做 TDOA 标定。

## PCB 放置与用户布线交接

- DAC、比较器、I²C 上拉、去耦和 ADC 跳线已由 `step4_ato_placement.py` 放在大陆下左区；电池分压与 LED 接口移到拍尾。
- 两颗 100nF 必须最短回到各自电源/地脚；DAC VOUT 与四路比较器输入按模拟信号处理，远离 LED 数据和开关节点。
- 比较器 OUT→S3 的四路尽量等环境、短且不跨槽；它们不是 ADC 网。
- S3 嵌入式开孔无法连接模组底部 EP41。布线时必须把 perimeter GND pad 1 与 pad 40 各自短接地，并在附近增加足够接地过孔；这是 C4 手工布线的强制检查项。
- 量产前验收仍需实板：静置误触发、150–300 mV 轻敲、四角 `first=`、DNP ADC 下的定位与 N16R8 PSRAM 启动。

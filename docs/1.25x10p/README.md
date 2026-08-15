# docs/1.25x10p — C4 MX1.25 卧贴尾插（正反 5P）

本板正反面各使用一颗 1.25 mm 间距、卧式贴片 5P 插座，校本件为 Molex PicoBlade 53261-0571。C4 保持 C3 的机械朝向，只重排背面网络，使板坐标上 5V/GND、USB 和 UART 正对成对。

装配资料：

- HTML：[`output/assembly/smartpaddle_tail_wiring.html`](../../output/assembly/smartpaddle_tail_wiring.html)
- 端面图：[`output/assembly/smartpaddle_tail_mx125_pinout.png`](../../output/assembly/smartpaddle_tail_mx125_pinout.png)

## KiCad 对应标准件

| 项 | 路径 |
|---|---|
| 封装 | `pcb/layouts/lib/footprints.pretty/Molex_PicoBlade_53261-0571_1x05-1MP_P1.25mm_Horizontal.kicad_mod` |
| 3D | `pcb/layouts/lib/3dmodels/Molex_PicoBlade_53261-0571_*.{wrl,step}` |
| 库名 | `SmartPaddle:Molex_PicoBlade_53261-0571_1x05-1MP_P1.25mm_Horizontal` |

来源为 KiCad 9 官方 `Connector_Molex` / `Connector_Molex.3dshapes` 几何的项目内副本。单颗 10P 因宽度逼近拍柄内腔已废弃。

## 放置真理源

`pcb/layouts/default/tail_snapshot.json`：

| Ref | 面 | 位置 | 旋转 | Flip |
|---|---|---|---:|---|
| `TAIL_MX125_F` | F.Cu | `(0, 87.1)` | 0° | 否 |
| `TAIL_MX125_B` | B.Cu | `(0, 87.1)` | 180° | 是 |

两插座开口均朝板外（+Y / 拍尾）。背面 Flip+180° 后，板坐标上 `F.pn` 对齐 `B.p(6−n)`，所以不能按“正反同号叠放”接线。

## C4 现行线序（Pad 号 → 网络）

Pad 号以封装丝印 / KiCad pad 为准。

| 面 | Pad | 网络 | 用途 |
|---|---:|---|---|
| F `TAIL_MX125_F` | 1 | `sys_5v_in` | 充电总成 5V OUT |
| F | 2 | `sys_5v_sw` | 开关后 5V / LED 供电 |
| F | 3 | `btn_sw` | 电源键，对地短接开机 |
| F | 4 | `usb_dp_conn` | USB D+（连接器侧，主板 22Ω 前） |
| F | 5 | `uart_tx` | S3 GPIO43 / U0TXD |
| B `TAIL_MX125_B` | 1 | `uart_rx` | S3 GPIO44 / U0RXD |
| B | 2 | `usb_dn_conn` | USB D−（连接器侧，主板 22Ω 前） |
| B | 3 | `bat_cell_p` | 可选电芯 B+ 采样，绝不是 5V |
| B | 4 | `led_din` | WS2812 DIN |
| B | 5 | `gnd` | 系统地 |
| — | MP | 机械焊耳 | 可就近接地 |

atopile 地址为 `tail.conn_f` / `tail.conn_b`；导入、放置、补尾与 C4 迁移脚本中的显式映射也必须与本表一致。

## 板坐标成对关系

端面视图以元件面朝上、拍尾朝观察者为准：

```
        −X MCU 天线侧                         +X
     ┌───────────────────────────────────────────┐
  F  │ p1 5V │ p2 5V_SW │ p3 BTN │ p4 D+ │ p5 TX │
     ├───────┼──────────┼────────┼───────┼───────┤
  B  │ p5 GND│ p4 LED_DIN│p3 BAT+│ p2 D− │ p1 RX │
     └───────────────────────────────────────────┘
                    拍尾端面 / +Y
```

| 板坐标 X | 正面 F | 背面 B | 意图 |
|---:|---|---|---|
| −2.5 | F.p1 `sys_5v_in` | B.p5 `gnd` | 电源对 |
| −1.25 | F.p2 `sys_5v_sw` | B.p4 `led_din` | LED 供电/数据 |
| 0 | F.p3 `btn_sw` | B.p3 `bat_cell_p` | 中位低速信号 |
| +1.25 | F.p4 `usb_dp_conn` | B.p2 `usb_dn_conn` | USB 差分对（22Ω 前） |
| +2.5 | F.p5 `uart_tx` | B.p1 `uart_rx` | UART 对 |

## 烧录与外接速查

| 用途 | C4 接法 |
|---|---|
| 系统供电 | 5V OUT→F.p1；GND→B.p5 |
| 外接电源键 | F.p3 与 B.p5 之间接瞬时按键 |
| WS2812 | VDD→F.p2；DIN→B.p4；GND→B.p5 |
| USB Serial/JTAG | D+→F.p4；D−→B.p2；GND→B.p5；板上需有 3V3 |
| USB-TTL | 适配器 RX←F.p5(TX)；适配器 TX→B.p1(RX)；GND→B.p5 |
| 下载模式 | 按住 BOOT→点 EN→保持 BOOT→执行 `idf.py flash` |

## C3 已下单线序归档

C3 Gerber `20260724-081156` 仅作回板参考。C3 正面与 C4 相同，背面曾为：B.p1=`gnd`、B.p2=`led_din`、B.p3=`bat_cell_p`、B.p4=`usb_dn`、B.p5=`uart_rx`。不要把 C3 线束位置直接套到 C4。

## 机械与布线注意

- PCB 尾端保持粗栈道平收；旧金手指、`TAIL_TIP`、`TAIL_STIFF` 已废弃。
- 插座 Fab 半宽约 5.7 mm，栈道半宽约 9.0 mm；正反各高约 3.5 mm。
- C4 电池分压与 LED 串阻/去耦放在尾插前方，优先在拍尾就近布线。
- USB D+/D−必须按 F.p4↔B.p2 成对走到靠近 ESP32-S3 的 22Ω 串阻，串阻 MCU 侧才叫 `usb_dp/usb_dn`；`bat_cell_p` 不得与任一 5V 网混淆。

当前主板为 69 个封装、0 走线/0 过孔/0 覆铜的重新布线交接态，本页只定义连接器物理线序，不表示已经连通或可以制造。

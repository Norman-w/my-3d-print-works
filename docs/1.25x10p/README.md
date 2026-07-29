# docs/1.25x10p — MX1.25 卧贴尾插（正反 5P）

淘宝「从芯 / MX1.25 卧贴」一类 **1.25 mm 间距、卧式贴片** 线对板插座。
本板：**正反面各一颗 5P**（同族可买 2–10P）。

尺寸（5P，Molex 53261-0571）：Fab 约 ±5.7 mm 宽，拍尾端面局部 +Y=2.6。

接线示意图（装配用）：
- HTML：[`output/assembly/smartpaddle_tail_wiring.html`](../../output/assembly/smartpaddle_tail_wiring.html)
- 端面图：[`output/assembly/smartpaddle_tail_mx125_pinout.png`](../../output/assembly/smartpaddle_tail_mx125_pinout.png)

## KiCad 对应标准件（已校本化）

与 Molex **PicoBlade 53261-0571** 同族（1×5 + 安装焊盘、卧贴）：

| 项 | 路径 |
|---|---|
| 封装 | `pcb/layouts/lib/footprints.pretty/Molex_PicoBlade_53261-0571_1x05-1MP_P1.25mm_Horizontal.kicad_mod` |
| 3D | `pcb/layouts/lib/3dmodels/Molex_PicoBlade_53261-0571_*.{wrl,step}` |
| 库名 | `SmartPaddle:Molex_PicoBlade_53261-0571_1x05-1MP_P1.25mm_Horizontal` |

来源：本机 KiCad 9 官方库 `Connector_Molex` + `Connector_Molex.3dshapes`（未手搓几何）。

> 曾用单颗 10P（53261-1071）因 Fab 半宽 ≈8.825 顶拍柄内腔（cav_hx≈8.5）；改正反 5P 后半宽 ≈5.7，侧向余量约 +2.8 mm。

## 放置（真理源：`tail_snapshot.json`）

| Ref | 面 | 位置 | 旋转 | Flip |
|-----|----|------|------|------|
| `TAIL_MX125_F` | F.Cu | `(0, 87.1)` | `0°` | 否 |
| `TAIL_MX125_B` | B.Cu | `(0, 87.1)` | `180°` | 是 |

两插座开口均朝板外（+Y / 拍尾）。背面 **Flip + 180°** 是为开口朝外；代价是 **焊盘号在板坐标 X 上左右对调**（见下）。

## 引脚网络 — C3 现行（Pad 号 → 网络）

> C4 目标线序见文末「C4 目标线序」。下列为 **C3 已下单板** 映射。

Pad 号以 **封装丝印 / KiCad pad** 为准（不是“端面从左数第几个”的直觉）。

| 面 | Pad | 网络 | 说明 |
|---|---:|---|---|
| F `TAIL_MX125_F` | 1 | `sys_5v_in` | 充电总成 5V OUT |
| F | 2 | `sys_5v_sw`（`LED_PLUS`） | 开关后 5V / LED 供电 |
| F | 3 | `btn_sw` | 电源键一路（对地短接开机） |
| F | 4 | `usb_dp` | USB D+ |
| F | 5 | `uart_tx` | MCU TXD0（向外发） |
| B `TAIL_MX125_B` | 1 | `gnd` | 系统地 |
| B | 2 | `led_din` | WS2812 DIN |
| B | 3 | `bat_cell_p` | 可选电芯 B+ 采样（**不是** 5V） |
| B | 4 | `usb_dn` | USB D− |
| B | 5 | `uart_rx` | MCU RXD0（接收） |
| — | MP | （机械） | 焊耳；可就近 GND |

atopile：`tail.conn_f` / `tail.conn_b`（`pcb/main.ato`）。

## 关键：正反面不是金手指那种「上下同号叠放」

旧金手指：同一根手指 F/B 在同一 X，**正 5 = TX 的正下方就是背 5 = RX**。

现 MX1.25（F@0° + B@180°&Flip）在板坐标上：

| 板坐标 X（天线 −X ← → +X） | 正面 F | 背面 B |
|---|---|---|
| **−2.5（MCU 天线侧）** | **F.p1** `sys_5v_in` | **B.p5** `uart_rx` |
| −1.25 | F.p2 | B.p4 `usb_dn` |
| 0 | F.p3 | B.p3 `bat_cell_p` |
| +1.25 | F.p4 `usb_dp` | B.p2 `led_din` |
| **+2.5（对侧）** | **F.p5** `uart_tx` | **B.p1** `gnd` |

因此：

- 正面靠 **+X** 那端的 P5 = **TXD0** —— 正下方不是 RX，而是 **GND（B.p1）**
- **RXD0** 在背面靠 **−X / MCU 天线侧** 那端（B.p5）
- 串口接线：**适配器 RX ← 正面 P5(TX)**，**适配器 TX → 背面天线侧那脚(B.p5 / RX)**，共地 → 背面另一端的 **B.p1**

> 不要按「正面第 N 脚正对背面第 N 脚」去找 RX/TX；按上表板坐标或实测通到模块 pad24/25。

## 端面视图（元件面朝上，拍尾朝观察者）

```
        −X MCU天线侧              +X
     ┌─────────────────────────────┐
  F  │ p1 5V │ p2 │ p3 │ p4 D+ │ p5 TX │  ← 元件面插座
     ├───────┼────┼────┼───────┼───────┤
  B  │ p5 RX │ p4 │ p3 │ p2 DIN│ p1 GND│  ← 背面插座（同板坐标，非镜像重画）
     └─────────────────────────────┘
              拍尾端面 / +Y
```

## 烧录 / 调试速查

| 用途 | 接法 |
|------|------|
| USB Serial/JTAG | F.p4 D+、B.p4 D−、B.p1 GND；板子需有 3V3（按住 SW_PWR 或 F.p1 有 5V） |
| 外置 USB‑TTL | TTL RX←F.p5(TX)，TTL TX→B.p5(RX)，GND→B.p1 |
| 下载模式 | 按住 BOOT → 点 EN → 保持 BOOT，再 flash |

## C4 目标线序（相对 C3 重排）

C3 背面 Flip+180° 后，板坐标上 **F.pn 对齐 B.p(6−n)**，于是正面 `sys_5v_in`(F.p1) 正对背面 `uart_rx`(B.p5)，GND 在另一端——接线别扭。C4 **不改插座朝向**，只重排网络，使同 X 成对合理。

目标（端面、元件面朝上、拍尾朝观察者；Pad 号仍以封装为准）：

```
        −X MCU天线侧              +X
     ┌─────────────────────────────┐
  F  │ p1 5V │ p2 SW│ p3 BTN│ p4 D+ │ p5 TX │
     ├───────┼─────┼──────┼───────┼───────┤
  B  │ p5 GND│ p4 ? │ p3 ? │ p2 D− │ p1 RX │
     └─────────────────────────────┘
```

| 板坐标 X | 正面 F | 背面 B | 成对意图 |
|----------|--------|--------|----------|
| −2.5 | F.p1 `sys_5v_in` | B.p5 `gnd` | 电源 |
| −1.25 | F.p2 `sys_5v_sw` | B.p4（`led_din` 或 `bat_cell_p`） | 辅电/信号 |
| 0 | F.p3 `btn_sw` | B.p3（余下那路） | 中位 |
| +1.25 | F.p4 `usb_dp` | B.p2 `usb_dn` | USB |
| +2.5 | F.p5 `uart_tx` | B.p1 `uart_rx` | UART |

相对 C3 的实质变化：背面 **GND 从 B.p1 改到 B.p5**；**UART_RX 从 B.p5 改到 B.p1**；USB_DN / LED / BAT 按上表挪到与 DP 等成对的位置。实现时改 `pcb/main.ato` 的 `tail.conn_*`，并更新本页 C3 表上方的「现行线序」为 C4 后归档 C3。

## 机械注意

- **PCB 尾端**以粗栈道宽度平收（无金手指窄尖）；金手指 / `TAIL_STIFF` 已废弃。
- Fab 半宽 ≈5.7 mm ≪ 栈道半宽 ≈9.0 / 拍柄 cav_hx≈8.5；Z 向正反各高 ≈3.5 mm。
- 装配：正反各一根 MX1.25-5P 线束（或双头束）。

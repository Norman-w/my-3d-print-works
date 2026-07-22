# docs/1.25x10p — MX1.25 卧贴 10P（尾插）

淘宝「从芯 / MX1.25 卧贴」一类 **1.25 mm 间距、卧式贴片、2–10P（本板用 10P）** 线对板插座。
尺寸表（10P）：A=11.25 / B=17.50 / C=10.00，带左右焊耳。

## KiCad 对应标准件（已校本化）

与 Molex **PicoBlade 53261-1071** 同族（1×10 + 安装焊盘、卧贴）：

| 项 | 路径 |
|---|---|
| 封装 | `pcb/layouts/lib/footprints.pretty/Molex_PicoBlade_53261-1071_1x10-1MP_P1.25mm_Horizontal.kicad_mod` |
| 3D | `pcb/layouts/lib/3dmodels/Molex_PicoBlade_53261-1071_*.{wrl,step}` |
| 库名 | `SmartPaddle:Molex_PicoBlade_53261-1071_1x10-1MP_P1.25mm_Horizontal` |

来源：本机 KiCad 9 官方库 `Connector_Molex` + `Connector_Molex.3dshapes`（未手搓几何）。

## 引脚约定（替代原 5×双面金手指）

| Pad | 网络 | 原金手指 |
|---:|---|---|
| 1 | `sys_5v_in` | TAIL_PWR F |
| 2 | `gnd` | TAIL_PWR B |
| 3 | `sys_5v_sw` | TAIL_LED F |
| 4 | `led_din` | TAIL_LED B |
| 5 | `btn_sw` | TAIL_CTL F |
| 6 | `bat_cell_p` | TAIL_CTL B |
| 7 | `usb_dp` | TAIL_USB F |
| 8 | `usb_dn` | TAIL_USB B |
| 9 | `uart_tx` | TAIL_UART F |
| 10 | `uart_rx` | TAIL_UART B |
| MP | 机械焊耳（可不布电气，或就近 GND） | — |

## 机械注意

- **PCB 尾端**已取消金手指窄尖：在原 `_tail_neck_y`（KiCad Y≈90）以粗栈道宽度平收。
- 插座 **拍尾 F.Fab 面**与板尾边齐平（原点约 `(0, 87.1)`）。
- 封装 courtyard 约 ±9.7 mm，粗栈道半宽约 8.7–9 mm：侧耳仍可能贴墙，以 DRC/实装为准。

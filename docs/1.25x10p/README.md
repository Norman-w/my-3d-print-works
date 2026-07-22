# docs/1.25x10p — MX1.25 卧贴尾插（正反 5P）

淘宝「从芯 / MX1.25 卧贴」一类 **1.25 mm 间距、卧式贴片** 线对板插座。
本板：**正反面各一颗 5P**（同族可买 2–10P）。

尺寸（5P，Molex 53261-0571）：Fab 约 ±5.7 mm 宽，拍尾端面局部 +Y=2.6。

## KiCad 对应标准件（已校本化）

与 Molex **PicoBlade 53261-0571** 同族（1×5 + 安装焊盘、卧贴）：

| 项 | 路径 |
|---|---|
| 封装 | `pcb/layouts/lib/footprints.pretty/Molex_PicoBlade_53261-0571_1x05-1MP_P1.25mm_Horizontal.kicad_mod` |
| 3D | `pcb/layouts/lib/3dmodels/Molex_PicoBlade_53261-0571_*.{wrl,step}` |
| 库名 | `SmartPaddle:Molex_PicoBlade_53261-0571_1x05-1MP_P1.25mm_Horizontal` |

来源：本机 KiCad 9 官方库 `Connector_Molex` + `Connector_Molex.3dshapes`（未手搓几何）。

> 曾用单颗 10P（53261-1071）因 Fab 半宽 ≈8.825 顶拍柄内腔（cav_hx≈8.5）；改正反 5P 后半宽 ≈5.7，侧向余量约 +2.8 mm。

## 引脚约定（正面 = 原金手指 F；背面 = 原金手指 B）

| 面 | Pad | 网络 | 原金手指 |
|---|---:|---|---|
| F `TAIL_MX125_F` | 1 | `sys_5v_in` | TAIL_PWR F |
| F | 2 | `sys_5v_sw` | TAIL_LED F |
| F | 3 | `btn_sw` | TAIL_CTL F |
| F | 4 | `usb_dp` | TAIL_USB F |
| F | 5 | `uart_tx` | TAIL_UART F |
| B `TAIL_MX125_B` | 1 | `gnd` | TAIL_PWR B |
| B | 2 | `led_din` | TAIL_LED B |
| B | 3 | `bat_cell_p` | TAIL_CTL B |
| B | 4 | `usb_dn` | TAIL_USB B |
| B | 5 | `uart_rx` | TAIL_UART B |
| — | MP | 机械焊耳（可不布电气，或就近 GND） | — |

atopile：`tail.conn_f` / `tail.conn_b`。

## 机械注意

- **PCB 尾端**在 `_tail_neck_y`（KiCad Y≈90）以粗栈道宽度平收（无金手指窄尖）。
- 两插座原点同约 `(0, 87.1)`；拍尾 F.Fab 与板尾边齐平；背面就地 Flip，开口仍朝板外。
- Fab 半宽 ≈5.7 mm ≪ 栈道半宽 ≈9.0 / 拍柄 cav_hx≈8.5；Z 向正反各高 ≈3.5 mm，内腔半高 ≈7 mm 仍够。
- 装配：两根（或一束双头）MX1.25-5P 线束。

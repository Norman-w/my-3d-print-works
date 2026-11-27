# Molex PicoBlade 53261-0471 4P 卧插板端

本目录记录 M7.C5 尾板 J2/J3 从 53398-0471 立插改为 **53261-0471 卧插 SMT** 的证据与可重复封装基线。改动目的仅是让两束线平行 PCB 离开并避开尾部两颗 M2 贯穿柱；连接器的四路电气功能与线束针序不变。

## 主证据与配套件

- [Molex 53261-0471 产品页](https://www.molex.com/en-us/products/part-detail/532610471)：4 circuits、right angle、surface mount、1.25 mm pitch、1.0 A/contact，mated height 3.40 mm。
- [Molex 53261 系列销售图 532610271_sd.pdf](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/532/53261/532610271_sd.pdf)：包含 4P 的 53261-0471 外形与推荐 PCB pattern。
- [Molex 51021-0400 外壳图 510210500_sd.pdf](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/510/51021/510210500_sd.pdf)：4P 外壳本体 6.75×3.95×3.20 mm。
- [Molex 51021 应用规范](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/applicationspecificationspdf/510/51021/510210000-AS-000.pdf?inline=)：明确 51021 压接外壳可配 53261 卧插板端，也可配旧 53398 立插板端。
- 线端：`51021-0400` 4P housing，配与实购 UL1571 28AWG 成品线一致的合格端子/成品线。板端姿态改变不要求改现有 4P 线序。

官方资料证明的是同一 PicoBlade 配合体系，并不表示 53261 与 53398 的 **PCB land pattern** 可以互换：两者板端焊盘和机械方向不同，旧 53398 footprint 不得用于 53261。

## 项目内封装证据

- 精确快照：[`kicad/Molex_PicoBlade_53261-0471_1x04-1MP_P1.25mm_Horizontal.kicad_mod`](kicad/Molex_PicoBlade_53261-0471_1x04-1MP_P1.25mm_Horizontal.kicad_mod)
- 3D 快照：[`kicad/Molex_PicoBlade_53261-0471_1x04-1MP_P1.25mm_Horizontal.step`](kicad/Molex_PicoBlade_53261-0471_1x04-1MP_P1.25mm_Horizontal.step)
- KiCad 9 stock footprint：`Connector_Molex:Molex_PicoBlade_53261-0471_1x04-1MP_P1.25mm_Horizontal`
- footprint SHA-256：`b177546df583a5dd26f4014428716db6733ab55483712201ca3afc315c415253`
- KiCad stock STEP：`${KICAD9_3DMODEL_DIR}/Connector_Molex.3dshapes/Molex_PicoBlade_53261-0471_1x04-1MP_P1.25mm_Horizontal.step`
- STEP SHA-256：`9c491a4fe35352e64f0576351c8f9e371e406bd158a0c6610bedb3421f8972d2`

项目内同时保存 footprint 与 STEP 的精确快照；同步脚本仍从 KiCad 9 stock library 载入几何，并由审计锁定两份快照哈希以及四个 0.80×1.60 mm 信号焊盘、1.25 mm pitch、两个 2.10×3.00 mm SMT 固定焊盘及 8.85 mm 固定焊盘中心距。Atopile 0.12.5 的 staging 只作为 pad-to-net 来源；不能用 build 成功退出或 staging 内嵌旧描述替代目标 PCB 的实物几何审计。

## 当前 J2/J3 针序与方向

两颗均在 `B.Cu`（朝拍头）并采用卧插；线端从插口沿 PCB 平面进入/离开。当前插口均朝板内侧，最终压线弯曲半径与壳体开口仍须在首件装配时确认。

| 接口 | Pad | 网络 | 当前 pad 中心（KiCad mm） |
| --- | ---: | --- | --- |
| J2 | 1 | `vout_5v` | `(-13.700,-2.475)` |
| J2 | 2 | `GND` | `(-13.700,-1.225)` |
| J2 | 3 | `bat_p` | `(-13.700,+0.025)` |
| J2 | 4 | `v5_sw_return` | `(-13.700,+1.275)` |
| J3 | 1 | `usb_dn` | `(+8.175,-8.200)` |
| J3 | 2 | `usb_dp` | `(+6.925,-8.200)` |
| J3 | 3 | `user_btn` | `(+5.675,-8.200)` |
| J3 | 4 | `led_data` | `(+4.425,-8.200)` |

Pin 1 由 stock footprint 的 pin-1 标记和 pad 编号共同定义；装配与成品线验收必须按上述 pad/net 表做逐芯通断，不能只看线色或从连接器背面凭肉眼数脚。

## 为完整插合包络腾出的最小改动

- J2/J3 换封装并采用经机械审计的位姿；J2 相对首个卧插候选仅沿 KiCad Y 平移 `+0.300 mm`，避开 J1 外壳槽焊点。
- C2 移到 `F.Cu (2.000,1.000), 0°`；C2 与 C1 都是 `V5_SW_RETURN–GND` 的 100 nF。现在 C2 靠近 U1，C1 仍靠近 D1，分别形成局部去耦。
- 51021-0400 插入 J2 后，外壳在 footprint 局部坐标占 `X=-3.375…+3.375 mm`、`Y=+2.450…+6.400 mm`。因此把低电流的 LED2/LED3 状态脚电阻 R6 移到 `B.Cu (-10.500,6.200), 0°`，并把 J4 沿 KiCad Y 从 `-5.969` 平移到 `-7.000 mm`。两者网络、方向和器件选型均不变。
- C3 保持 `B.Cu (8.001,-1.397), 0°`，U3 保持 `B.Cu (3.110,4.318), 0°`，L1 保持 `B.Cu (9.078,1.905), 90°`。C3 是 `BAT_P–GND` 10 µF，不能为连接器让位而拉长 IP5305T BAT/SW 高脉冲电流回路。

当前 PCB 仍为无铜交接态：没有为本改动布线、覆铜或生成制造文件。必须完成手工布线并通过 release gate 后才能制造。

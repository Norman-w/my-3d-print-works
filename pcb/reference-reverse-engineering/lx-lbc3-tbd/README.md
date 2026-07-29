# LX-LBC3 充放电板参考逆向子工程

> 状态：`reference-reverse-engineering` / `TBD` / **不可生产**

## 验证状态（必须保留）

截至 2026-07-29，本目录完成的只有：实物照片像素标定、器件外形/位置/方向记录、
公开商品参数与候选资料整理，以及无网络/无走线的 KiCad 视觉预览。

**尚未进行任何实物电气验证：**没有测过连续性、阻容值、电感 DCR/饱和电流、U1
引脚功能、充电曲线、5 V 升压带载、欠压/过流/短路保护、待机功耗、Type-C CC
行为或 VBUS 反灌。因此本目录中的 `JNEC`、`2R2`、R4 方框/口形标记和 LED
方向属于外观证据；所有网络、精确料号与功能归属仍是 `TBD`。

本基准复刻到此作为研究记录保留，不继续直接演化为 SmartPaddle 量产电路。下一阶段
另行评估 IP5306/IP5306H 等有公开数据手册、可独立设计验证的方案；若采用替代方案，
必须在独立原理图/PCB 中实现，不能把本视觉板的推测网络复制过去。

这个子工程只用于在 KiCad 中查看现有 16 mm × 12 mm 小板的大致板框、器件
封装、相对摆放和 3D 体积。它不属于 SmartPaddle C4 电气设计，不含已证实网表，
也不应被当作可投板、可采购或可照抄的原理图。

本目录只画**现有基准样板**。未来 SmartPaddle 改进版必须放在另一个兄弟子工程，
不得与本板共用同一 PCB、同一装配图层或同一 3D 场景。

## 交付内容

- `reference.ato`：可引用的 Atopile 机械/占位定义；没有虚构连接。
- `footprints.pretty/`：6 焊脚电源型 Type-C、绕线电感和焊线盘参考封装。
- `lx-lbc3-reference-tbd.kicad_pcb`：16 mm × 12 mm 最小预览板；0 条走线、0 个过孔、0 个铜区。
- `output/reference_top.svg`：顶面 2D 装配预览。
- `output/reference_bottom.svg`：底面 5V 焊盘预览（镜像）。
- `output/reference_3d_top.png`：KiCad 3D 顶视预览。
- `output/reference_3d_iso.png`：KiCad 3D 斜视预览。
- `output/photo_calibrated_layout.svg/.png`：按照片像素标定的元件包络/方向审计图。
- `layout_spec.py`：照片像素坐标、板坐标、方向和防压叠包络的单一真理源。
- `validate_reference_preview.py`：只校验参考板机械/安全契约，不把它当生产 DRC。
- `evidence-and-inference.md`：照片、用户目测、商品文案、候选芯片和待测项的分层证据链。

## 坐标约定

预览板按横向显示：

- 原点为板左上角，`X` 向右、`Y` 向下。
- Type-C 在左侧；按顶面照片逆时针旋转后，B+ 在右上、B- 在右下。
- 这是用户照片中“Type-C 在上、B 焊线盘在下”的同一块板旋转 90° 后的视图。
- 板外形 16 mm × 12 mm 来自同款公开规格；顶面元件以原图约
  `116.7 px/mm` 标定并保留原始像素中心，中心误差暂按约 ±0.3 mm 管理。
  局部缺口、焊盘铜形和器件本体尺寸仍不能用于生产封装。

详见 `evidence-and-inference.md` 的坐标表。

## 重新生成和验证

需要 KiCad 9 自带 Python 与命令行工具：

```sh
cd pcb/reference-reverse-engineering/lx-lbc3-tbd
./generate-reference-preview.sh
```

脚本只重建本目录中的参考封装、预览板和 `output/`；不会读取或修改 C4 主板。
生成末尾必须出现 `PASS`：板框 16×12 mm、15 个占位、J1 六焊脚、所有顶面
可见器件包络至少保留 0.12 mm、不发生压叠、0 个命名网络、0 条走线/过孔、
0 个铜区。由于这是刻意无网表的照片占位板，生产型 DRC 没有意义，也不得用
DRC“清零”来反向编造连接。

打开 `lx-lbc3-reference-tbd.kicad_pcb` 即可查看 2D/3D。板上所有 `TBD`、
`CANDIDATE` 和 `NO NETS` 文本都必须保留，直到实物测量完成。

Atopile 源采用仓库锁定的 0.12.5 语法风格，但本机没有可执行的 0.12.5；已安装的
0.15.7 命令自身在导入 `atopile.compiler.front_end` 时失败，因此本次没有伪称
Atopile 编译通过。KiCad 9.0.6 预览板与输出已独立生成并通过机械/安全契约校验。

## 放行边界

在下列项目完成前，本子工程不得升级为电气复现：

1. 已记录 U1 的 `JNEC`、`C` 下划线、左下圆点和六脚外观；仍需用 pin-map/功能测试确认精确料号。
2. 断电测量 U1 各脚到电感、B+/B-、VBUS、LED 与地的连续性。
3. 测量 Type-C 六焊脚次序以及 CC1/CC2 到地或电源的阻值。
4. 分别验证充电、满充、空载、带载、欠压和移除外部 5V 时的电压/电流。
5. 验证无输入时 VBUS 是否反灌，以及作为 USB-C Source 时是否存在合规的 Rp/DRP 行为。

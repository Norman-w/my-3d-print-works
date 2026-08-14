# USB Type-C 立贴超短体 16P（尾板选用）

> 选型冻结：**身体高度 5.8 mm** 的 16P 立贴短脚母座。  
> 用途：`pcb-tail` 拍柄末端；外壳口与母座金属端面平齐，板面内缩。

## 主数据表与来源

- 主证据：[`Type-C-16PIN-vertical-H5.8-short-datasheet.pdf`](Type-C-16PIN-vertical-H5.8-short-datasheet.pdf)
- 来源：用户于 2026-08-13 提供的本地文件 `/Users/norman/Downloads/Type-C 母座16PIN立贴 H=5.8 副本.pdf`；本目录文件为原样复制。
- SHA-256：`8d8f9afa88a8fc6049e041b519745d119b16f8eccdcf78de7f4090ee294dff23`
- 用途：作为 M5 独立尾部电源小板 J1 的机械尺寸、16 个物理触点顺序及引脚定义的首要依据。下方旧商品图仅作选型背景或辅助说明；如有冲突，以该 PDF 为准。
- 派生局部图：[`Type-C-16PIN-vertical-H5.8-short-footprint-detail.png`](Type-C-16PIN-vertical-H5.8-short-footprint-detail.png)，由上述 PDF 第 1 页以 600 dpi 渲染后仅裁出推荐 PCB 图；SHA-256 `d5d6ead0e190da5bb2ac3242848733a270ed4addb6261e7ea451a1fcdcd6ac34`。
- J1 逐触点结论与安全状态：[`M5-J1-PINOUT-AUDIT.md`](M5-J1-PINOUT-AUDIT.md)

## 关键尺寸（本档）

| 项 | 值 | 来源 |
|---|---:|---|
| 身体高度 `H_typec` | **5.8 mm** | 主数据表及 [`height-5.8-annotated.jpg`](height-5.8-annotated.jpg) |
| 16 个 SMT 触点焊盘 | **0.43 × 1.40 mm** | 主数据表第 1 页推荐 PCB 图 |
| 触点节距 / 单排中心跨度 | **0.78 / 5.46 mm** | 同上 |
| 两排焊盘总外跨度 / 中心距 / 边间隙 | **3.70 / 2.30 / 0.90 mm** | 同上；后两项由 3.70−1.40 推得 |
| 两个外壳槽中心距 | **8.68 mm** | 同上；局部 X=`±4.34` |
| 外壳槽孔 / 铜焊盘 | **0.50 × 1.25 / 0.80 × 1.55 mm** | 同上；外铜 `R0.40`，孔/外形共用 0.75 mm 直段 |
| 系列可选高度 | 5.8 / 6.0 / 6.5 / 6.8 mm | [`series-height-options.jpg`](series-height-options.jpg) |
| 短脚 | ~0.7 mm | 同系列商品文案 |
| 接点 | 16P（USB2.0：VBUS/GND/CC/D±/SBU） | [`pinout-16p.jpg`](pinout-16p.jpg) |

## 板位几何含义

```text
Y_butt     = 拍柄最尾端外表面（世界 −Y 极值）
Y_pcb      = Y_butt + H_typec          # F.Cu 所在截面；母座口与外壳平齐
外形       ≈ 该 Y 处内壁 XZ（wall_t + cavity_inset 内缩后）+ 微小装配间隙
```

实现见 `pcb-tail/generate_outline.py` 常量 `USB_BODY_HEIGHT_MM = 5.8`。

## 引脚（16P）

主数据表推荐 PCB 图的板视角顺序：

- 上排左→右：A1、A4、A5、A6、A7、A8、A9、A12
- 下排左→右：B12、B9、B8、B7、B6、B5、B4、B1

功能定义：

- A1/A12/B1/B12 = GND  
- A4/A9/B4/B9 = VBUS  
- A5=CC1，B5=CC2  
- A6/B6=D+，A7/B7=D−  
- A8=SBU1，B8=SBU2（本板可不接）

## 参考图（已压缩）

| 文件 | 说明 |
|---|---|
| `height-5.8-annotated.jpg` | 实物标注身体高度 5.8 |
| `pinout-16p.jpg` | 接点定义 |
| `series-height-options.jpg` | 同系列多高度文案 |
| `footprint-pads-family-ref.jpg` | 同族立贴焊盘示意 |
| `pcb-layout-family-longpin.png` | 旧长脚同族参考，尺寸与本次 H=5.8 短脚数据表不一致；**不得再用于生成 J1 封装** |

## KiCad 封装

- 生成脚本：`pcb-tail/scripts/gen_usb_16p_vert_smt_fp.py`
- 封装：`pcb-tail/lib/footprints.pretty/USB_C_Receptacle_16P_Vertical_SMT_Short.kicad_mod`
- 制造前逐触点门禁：`python3 pcb-tail/scripts/audit_usb_16p_j1.py`
- 焊盘号直接采用数据表触点名 `A1`…`B12`；`A8/B8` 明确 NC，两个外壳槽共用 `S1=GND`。
- 旧 `USB_C_Receptacle_GCT_USB4120-03-C_VERT*`（USB4115 四角圆孔）已弃用。

## 注意

- 下单型号、卖家图纸和收货实物必须与本目录主数据表一致；旧长脚图不能替代该核对。
- 身体高度选 5.8；不要用 6.5 尺寸图当板位高度。

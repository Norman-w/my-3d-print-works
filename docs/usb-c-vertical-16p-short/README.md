# USB Type-C 立贴超短体 16P（尾板选用）

> 选型冻结：**身体高度 5.8 mm** 的 16P 立贴短脚母座。  
> 用途：`pcb-tail` 拍柄末端；外壳口与母座金属端面平齐，板面内缩。

## 关键尺寸（本档）

| 项 | 值 | 来源 |
|---|---:|---|
| 身体高度 `H_typec` | **5.8 mm** | [`height-5.8-annotated.jpg`](height-5.8-annotated.jpg) 标注「身体高度:5.8」 |
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

与常见 USB2.0 Type-C 16P 一致（正视口）：

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
| `pcb-layout-family-longpin.png` | **推荐 PCB**（16 贴片 + 左右腰圆；生成封装用） |

## KiCad 封装

- 生成脚本：`pcb-tail/scripts/gen_usb_16p_vert_smt_fp.py`
- 封装：`pcb-tail/lib/footprints.pretty/USB_C_Receptacle_16P_Vertical_SMT_Short.kicad_mod`
- 同族高度（5.0/5.5/5.8/6.0/6.5/6.8）共用焊盘；本板机械按 **H=5.8**。
- 旧 `USB_C_Receptacle_GCT_USB4120-03-C_VERT*`（USB4115 四角圆孔）已弃用。

## 注意

- 下单仍须核对卖家图纸与 `pcb-layout-family-longpin.png` 一致。  
- 身体高度选 5.8；不要用 6.5 尺寸图当板位高度。

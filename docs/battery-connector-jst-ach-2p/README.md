# M5 尾板 2P 电池接口：JST ACH 1.2 顶插

状态：**已写入 Atopile 并保持既有 B.Cu 位姿；当前 PCB 已清除全部铜，J4 待重新布线。本次不生成制造文件。**

## 已确认器件

| 位置 | 精确型号 | 说明 |
| --- | --- | --- |
| PCB 板端 | JST `BM02B-ACHSS-GAN-ETF` | ACH、1.20 mm、2P、SMT、顶插（线束由侧面送出） |
| 线端外壳 | JST `ACHR-02V-S` | 与上述板端配套的 2P 壳体 |
| 压接端子 | JST `SACH-003G-P0.2` | AWG 30–28；本项目成品线固定用 AWG 28 |
| KiCad 封装 | `Connector_JST:JST_ACH_BM02B-ACHSS-GAN-ETF_1x02-1MP_P1.20mm_Vertical` | KiCad 9 stock footprint |

主证据为归档的 [JST ACH 官方数据表](JST-ACH-official.pdf)，来源为 [JST 官方 PDF](https://www.jst-mfg.com/product/pdf/eng/eACH.pdf)，SHA-256 `d1f9e9375b1c0dfc4814d5f633997484d84da6c0b03f712104df3bbdf462131b`。官方定义 1–3P、AWG28 时额定 2 A AC/DC；2P 板端本体约 4.2 mm 宽、4.3 mm 深、1.4 mm 高。

项目使用的可复现资产全部放在本目录：

- `kicad/JST_ACH_BM02B-ACHSS-GAN-ETF_1x02-1MP_P1.20mm_Vertical.kicad_mod`：KiCad 9 stock footprint 的逐字归档，SHA-256 `dad2081506a292c544881eed161e70d1094ac79ea579526652e5616722d0942c`。
- `kicad/JST_ACH_BM02B-ACHSS-GAN-ETF_simplified-preview.scad` 与同名 `.wrl`/`.stl`：按官方 4.2×4.3×1.4 mm 外包络制作的预览模型；PCB 使用 KiCad 可直接加载的 `.wrl`。内部凹槽只是便于辨认方向，**不得用于公差、干涉或制造判断**。

JST 的官方 STEP 下载需要提交许可表和个人邮箱，本项目没有代用户提交表单；因此 PCB 明确引用上述 docs 内的简化预览 WRL，而不是伪称原厂 3D 模型。

## 固定电气定义

| 针脚 | 网络 | 线色/用途 |
| ---: | --- | --- |
| 1 | `BAT_P` | 红，受保护单节锂电正极 |
| 2 | `GND` | 黑，电池负极/系统地 |

J4 与既有 `J2.3=BAT_P`、`J2.2=GND` 同网并联；J2.3 继续向主板提供电芯电压。电池不得接 `vout_5v` 或主板 `SYS_5V_IN`。线色不是极性证据，每批成品线首次使用前须以通断档确认红线实际落到 J4.1。

KiCad footprint 的局部焊盘为：Pad 1 `(-0.60,-1.875)`、Pad 2 `(+0.60,-1.875)`，均为 0.60×0.85 mm SMT；两个 `MP` 固定焊盘无网络。stock footprint SHA-256 为 `dad2081506a292c544881eed161e70d1094ac79ea579526652e5616722d0942c`。

## 采购与电流边界

成品线搜索词：`JST ACHR-02V-S 1.2 2P 28AWG 红黑 单头 镀锡 电池端子线`。要求卖家明确外壳 `ACHR-02V-S`、端子适配 AWG28、Pin1 红/Pin2 黑；先买少量与原厂板端实插并核线序，不自行压端子。

本项目建议连续电池电流不超过 1.5 A，任何状态不得超过 ACH 在 AWG28 下的 2 A 额定值；首次样机仍须实测最低电芯电压、无线发射和 LED 最坏状态下的电流、压降和温升。

## PCB 当前布局状态

J4 位于 `B.Cu` `(-2.794,-5.969) mm`、`90°`。Pad 1=`BAT_P` 的全局坐标为 `(-0.919,-5.369) mm`，Pad 2=`GND` 为 `(-0.919,-6.569) mm`；两个 `MP` 固定焊盘仍为 NC。当前板为无铜交接态，两只电气焊盘都待重新布线；逐焊盘几何与网络由审计脚本独立核对。

顶插只描述插合方向；线束从壳体侧面离开，最终拔插空间、导线弯折半径及应力释放仍须结合拍柄实物确认。

运行 `python3 pcb-tail/scripts/audit_battery_connector_j4.py` 可核对 J4/SW1 的 footprint、坐标、针脚网络与资料校验；布线完整性必须另由跨层 release gate 证明。

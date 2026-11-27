# IM948 手册插图归档

来源：语雀 [IM948系列模块使用说明 V1.5](https://www.yuque.com/cxqwork/lkw3sg/yqa3e0)  
下载日期：2026-07-28 · 共 34 张 + 厂商底板原理图 PDF  
原始 URL 见同目录 [`manifest.json`](manifest.json)

> 文件名是按下载顺序的启发式命名；下列「实际内容」以目视核对为准（部分文件名与内容不符）。

## 排障优先（硬件）

| 文件 | 实际内容 | 用途 |
|------|----------|------|
| [`08_module_side_or_detail.png`](08_module_side_or_detail.png) | **管脚顶视图 + 模块 PCB 实物对照** | 数脚、对 VBUS/GND；对照热风后是否掉件 |
| [`03_module_photo_or_size.png`](03_module_photo_or_size.png) | 宣传图 + **裸板俯视**（13×18.5 mm） | 对照 IC / 无源件布局 |
| [`07_module_pinout_diagram.png`](07_module_pinout_diagram.png) | 机械尺寸 + TOP VIEW + 推荐焊盘 | 封装与 RF 净空 |
| [`09_pin_table_wide.png`](09_pin_table_wide.png) | **典型应用原理图**（5V + UART 电平转换） | VBUS/去耦/二极管压降≈4.8V |
| [`10_pin_desc_1.png`](10_pin_desc_1.png) | **锂电池应用原理图** | VBUS+VBAT+KEY 接法 |
| [`11_pin_desc_2.png`](11_pin_desc_2.png) | 管脚/说明续（待对照） | — |
| [`vendor_baseboard_schematic_V2.11.pdf`](vendor_baseboard_schematic_V2.11.pdf) | 厂商底板原理图（support 包复制） | 充电/开关电源参考 |

### 关键管脚（顶视图，天线/坐标丝印一侧为「上」）

| Pin | 名称 | 说明 |
|-----|------|------|
| 1 | VSS | GND |
| **2** | **VBUS** | **主电源输入（通常 5V）— SmartPaddle 接 `SYS_5V_SW`** |
| 3 | VBAT | 电池（本板悬空） |
| 4 | VDDIO | IO 电平（本板悬空） |
| 13 | RXD | ← C4 MCU TX（GPIO40 / S3 pad33） |
| 14 | TXD | → C4 MCU RX（GPIO41 / S3 pad34） |
| 16 | VSS | GND |

## 完整清单

| # | 文件 | 实际内容（核对后） |
|---|------|-------------------|
| 01 | `01_buy_qr.png` | 购买/网盘二维码 |
| 02 | `02_product_selection.png` | 型号选型表 |
| 03 | `03_module_photo_or_size.png` | 产品图 + 裸板俯视尺寸 |
| 04 | `04_application_fields.jpg` | 应用领域 |
| 05 | `05_coordinate_axes.jpg` | 坐标轴示意 |
| 06 | `06_module_top_view.png` | 带壳模块轴向示意 |
| 07 | `07_module_pinout_diagram.png` | 机械尺寸 / 焊盘 |
| 08 | `08_module_side_or_detail.png` | **管脚图 + PCB 实物** |
| 09 | `09_pin_table_wide.png` | **典型应用原理图**（非管脚表） |
| 10 | `10_pin_desc_1.png` | **锂电池应用原理图** |
| 11 | `11_pin_desc_2.png` | 管脚/说明续 |
| 12 | `12_led_status.png` | LED 状态 |
| 13–14 | `13/14_power_note_*.png` | BLE 调试 / 供电相关截图 |
| 15 | `15_typical_application_schematic.png` | **STM32 移植说明（非原理图）** |
| 16 | `16_block_or_mech_diagram.png` | **串口测试日志样例（健康模块参考）** |
| 17 | `17_hardware_diagram_2024.png` | RViz IMU 插件步骤 |
| 18 | `18_ros_example.png` | ROS 示例 |
| 19–20 | `19/20_software_ui_*.png` | 上位机 UI |
| 21 | `21_protocol_ui.png` | 协议相关 UI |
| 22 | `22_ble_connect_steps.png` | BLE 连接步骤 |
| 23–26 | `23–26_calib_*.png/jpg` | 加速度校准 |
| 27–29 | `27–29_*orientation*.png` | 轴向 / 安装矩阵 |
| 30 | `30_factory_save.png` | 出厂保存 |
| 31–33 | `31–33_*log*.png/jpg` | 充电参数 / 数据记录 |
| 34 | `34_misc_2024.png` | 杂项 2024 |

## 健康模块参考输出（图 16）

正常主动上报应类似：`temperature≈28`、`AZ≈9.3`（重力）、四元数非 `-1,0,0,0`。  
当前 SmartPaddle 日志若 `rawA=0` / `temp=0.00` 而 UART 仍有帧，优先查 **Pad2 VBUS** 与模块 MEMS 是否完好。

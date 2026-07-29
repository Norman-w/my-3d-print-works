# SmartPaddle 上的 IM948 集成

## 板级接线（V4 / `main.ato`）

| IM948 | 板网 | 说明 |
|-------|------|------|
| VBUS (pad2) | `SYS_5V_SW` | 唯一供电：充电总成 5 V → 软开关后系统 5 V |
| VBAT (3/15) | **悬空** | 不用模块锂电充电路径 |
| VDDIO (4) | **悬空** | 由模块在 VBUS 场景下内部产生 ≈3.0 V IO |
| GND | GND | |
| RXD (13) | C4 MCU **GPIO40**（UART1 TX，pad 33） | MCU→IMU |
| TXD (14) | C4 MCU **GPIO41**（UART1 RX，pad 34） | IMU→MCU |

设计意图：IMU **独占 UART1**，与尾插 UART0（TXD0/RXD0）隔离，避免烧录抢线。  
封装：`pcb/layouts/lib/footprints.pretty/IM948_CUTOUT.kicad_mod`。

> C3 历史板使用 ESP32-C6 GPIO23/22；不要把这组编号套到 C4。旧版反焊/接 GPIO4/5 的诊断见 [`../ESP32C6N8/reverse-mount-and-reboot-audit.md`](../ESP32C6N8/reverse-mount-and-reboot-audit.md)。

## 固件路径

| 文件 | 职责 |
|------|------|
| `firmware/main/config.h` | `IMU_UART_*`、`SKIP_IMU_INIT`、波特率 |
| `firmware/main/im948_sdk.*` | UART + 组包/拆包 |
| `firmware/main/im948_sensor.*` | 唤醒、配置、流、校准 |
| `firmware/main/im948_data.h` | 换算系数、订阅枚举、`ImuFrame` |
| `firmware/main/main.cpp` | `init_imu()` / `imu_loop` |

典型上电顺序：`wake(0x03)` → 配参 `0x12`/`0x33`/`0x40` → 可选升波特 `0x47` → `0x19` 主动上报 → 解析 `0x11`。

## 推荐订阅（击球分析）

至少包含：含重力加速度、角速度、四元数或欧拉角。当前固件在 115200 baud 下配置 **100 Hz**；精简订阅后的 **250 Hz** 仍是待实测目标。
不需要的 bit 不要订，避免蓝灯三闪带宽告警。

## 校准建议（产品级）

1. 加速计：优先球型多面拟合（`0x17`），简易水平校准（`0x07`）仅应急  
2. 磁力计：九轴融合时必须校；远离磁铁  
3. 可选 Z 轴 / 坐标系清零；改量程后重校加速度  
4. 保存出厂校准 `0x15` / 恢复 `0x14`（见手册）

## 本地物料与示例

见 `firmware/support/IMU/IM948/readme.txt`：上位机、USB-TTL 驱动、PCB 封装、底板外壳、Arduino/STM32 SDK 摘录。

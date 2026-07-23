# SmartPaddle V1 回板问题清单（改板待办）

> 第一次打板（JLCPCB `20260706-212523`）装配 / 上电 / 烧录实测结论。  
> 改下一版前必须消化；勿只改聊天记录。  
> 实施步骤见 **[`V1_REWORK_PLAN.md`](V1_REWORK_PLAN.md)**。

## V2 实施进度（2026-07 更新）

已落地：
- SCAD：MCU 开窗、漏斗宽栈道、**尾端平收**（无金手指窄尖）
- 尾插：**正反各一颗 MX1.25 5P**（Molex 53261-0571）；金手指 / `TAIL_STIFF` 已废弃
- 宽栈道：`SW_BOOT` / `SW_EN` / `SW_PWR`；MCU 旁 `LED_MCU_PWR` + `R_MCU_PWR_1K`
- IMU UART1：`GPIO23/22`（pad 21/20）；与 UART0 / 尾插隔离
- 管线 step1→4 + pinmap 校验；**手布线与 DRC 由你完成**

## 1. MCU 封装几何错误（装不进 / 要对齐得磨模块）

**现象：** SGFK ESP32-C6-N8 放入开窗后焊盘对不齐，需磨掉一块才能勉强对上部分半孔。

**根因（对照模块尺寸图）：**
- 本体应为 **18 × 25.5 mm**，节距 **1.27 mm**，半孔 **Ø0.85**，**底边 → 最下一排焊盘中心 = 1.5 mm**。
- 当前 `SGFK_ESP32-C6-N8_CUTOUT.kicad_mod`：节距对，但焊盘沿长边整体偏移约 **0.5 mm**（现约 0.98 mm 边距，应为 1.5 mm）。
- 焊盘为纯 SMD，未按 Ø0.85 半孔建模。

**改法：**
- [x] 重做 `.kicad_mod`（几何 + 半孔）— `thru_hole` Ø0.85，焊盘中心在本体边线与模块半孔同心
- [x] 核对 / 收紧 `mech_geometry.ESP32_CUTOUT` 与 step3 开窗
- [ ] 同步 3D / Fab 轮廓

## 2. MCU 引脚定义与 `main.ato` 映射错误

**现象：** 手册脚位与 `SGFK_ESP32C6N8_Cutout` 的 `pin N → 信号` 不一致（例如把 IO2/IO3/BOOT/USB/UART 绑到错误半孔）。

**手册要点（天线在上；左 1→14 向下；右底→上多为 15→28）：**
| 信号 | 正确半孔（约） | V1 ato 错误绑法 |
|------|----------------|-----------------|
| IO2 / IO3 | pin 27 / 26 | pin 4 / 5 |
| IO8 LED | pin 10 | pin 8（实为 IO0） |
| IO9 BOOT | pin 15 | pin 9（实为 IO1） |
| TXD0 / RXD0 | pin 25 / 24 | 与现 TX/RX 对调 |
| USB D−/D+（IO12/13） | pin 13 / 14 | DN 绑到 pin 16 |

**改法：**
- [x] 修正 `pcb/main.ato` / `pinmap.py` 全部绑定（含 IMU→IO23/22）
- [x] 固件 `config.h` GPIO 与 pinmap 一致（`validate_esp32c6n8_pinmap.py`）
- [x] **mod + ato + 固件** 同源

## 3. IMU 与 MCU UART0 共总线 → 烧录极不方便

**现状：** `imu.RXD/TXD` 与 `mcu.UART_TX/RX`（及尾插 UART）挂在**同一对** `uart_tx/uart_rx` 上。

**问题：**
- 烧录/日志若走 UART0，IMU 会抢线或必须拆焊 IMU TX。
- 业务跑起来后串口给 IMU，以后再烧又要物理断开 → 不可接受。

**改板目标：**
- [x] **IMU 独占 UART1**（GPIO23/22），与 TXD0/RXD0 **电气隔离**
- [x] UART0 仅尾插 / 调试；不并 IMU
- [ ] **烧录主路径：USB Serial/JTAG**（回板后实测枚举；供电走 `SYS_5V_*`）

**IMU UART1 脚位选型（2026-07-14 再更正，以实物为准）：**

> 实物确认：MCU **靠近拍柄/IMU** 一侧丝印为 **GND → 3V3 → EN → IO4 → …**（footprint pin1–14，−Y）。  
> **对侧**才是 IO2 / IO3 / UART0（pin15–28，+Y）。此前「IO2/IO3 正对 IMU」作废。  
> **不旋转 MCU**，只改脚映射。

| 候选 | 相对 IMU | 结论 |
|------|----------|------|
| **IO22 / IO23** | **正对 IMU（拍头侧 pad20/21）** | **UART1**；面对面平行交叉，无过孔交叉 |
| **IO4 / IO5** | 拍柄侧 | 空闲（strapping，勿强驱） |
| IO6 / IO7 | 同侧稍后 | PZT BL/BR |
| IO2 / IO3 | 背对 IMU | PZT TL/TR（角上可绕） |
| TXD0 / RXD0 | 对侧 | 仅调试，**禁止给 IMU** |

**当前分配：**
- **IMU UART1：** `IO23 (TX) → IMU RXD`，`IO22 (RX) ← IMU TXD`（平行交叉）
- **PZT：** TL=`IO2`，TR=`IO3`，BL=`IO6`，BR=`IO7`
- 固件：`config.h` 与上表一致

## 4. MCU 开窗短边偏松，可再收窄

**现状：** `ESP32_CUTOUT` 短边方向 = `18.0 + 2×0.20 = 18.4 mm`。

**现象：** 短边方向仍偏空，模块横向晃动余量偏大。

**改法：**
- [ ] 非半孔边（短边）单边间隙收到 **0.05～0.10 mm**（先按实物卡规再定）
- [ ] 半孔长边间隙与焊盘几何一起重算，勿与短边用同一 `MODULE_CUTOUT_CLEARANCE`

## 5. IMU 开窗短边空隙更大

**现状：**
- Fab 轮廓约 **18.5 × 13.0 mm**
- `IMU_CUTOUT` 宽 `18.5+0.2=18.7`，高 **13.4**（本体 13.0 + 2×0.20；焊盘在 ±6.50 与半孔同心）

**现象：** 模块放入后短边方向空隙明显大于 MCU，定位差、焊接难。

**改法：**
- [ ] 用实物 / 厂家尺寸图复核 IM948 本体宽高
- [ ] 短边（无半孔边）收紧到与 MCU 同级小间隙
- [x] 半孔边单独 setback，避免「整圈 +0.2」导致短边过大空
- [x] 同步改 `IM948_CUTOUT.kicad_mod` 焊盘中心与开窗一致性

## 6. 电源软开关：`PW_D_BTN` 冷启动误开（已实测）→ V3 隔离读键

**现象：** 接电池不按键也会半开 / 常电；拆掉肖特基 `PW_D_BTN` 后门极可回到 ≈VBAT，开关恢复关断。

**根因：** 开机二极管把 `P_GATE` 接到带 3V3 上拉的按键网，冷启动回灌拉低门极。

**临时：** 本版可保持 `PW_D_BTN` 不装，用门极对地点触开机。

**改板（V3，`main.ato` PowerLatchAndRegulator）：**
- [x] 开机拉低门极 与 MCU 读键 **二极管隔离**：`d_btn_start`（1N4148W）阳极=`P_GATE`、阴极=`BUTTON_RAW`；MCU 经 1k 读 `BUTTON_GPIO`
- [x] 文档「拉高 GPIO 自锁」与电路极性对齐（`PWR_LATCH` 高 → NMOS 拉低 P-MOS 门极）
- [x] 固件 `power_control`：上电尽早拉高 GPIO10；尾键 GPIO18 长按 ≥2s 关机
- [x] pad 命名：`PWR_LATCH`=pad11/GPIO10；用户键=`GPIO18_USER_BTN`=pad16（勿再标成 GPIO10）

## 6b. IM948 VDDIO / LDO 电源 OR（V3）

- [x] `imu.VDDIO` **不再**接到板载 3V3（锂电供电时悬空，由模块内稳压约 3.0V）
- [x] `D_LDO_BAT` / `D_LDO_USB` 改为 **SS14（SOD-123，1A 级）**，替换串主路径的 BAT54
- [x] KiCad：`D_BTN_START` 隔离保留；**已删** `D_LDO_BAT`/`D_LDO_USB`；网名 `SYS_5V_IN`/`SYS_5V_SW`；IMU VBUS←SYS_5V_SW，VBAT/VDDIO 悬空；`BAT_CELL_P` 供可选 B+ 采样
- [ ] **手布电源区**（本轮不自动布线）：见下方 V4 手布清单

### V4 手布清单（你来布）

1. `TAIL_PWR.F (SYS_5V_IN)` → `PW_Q_LOAD` source → drain `SYS_5V_SW`
2. `SYS_5V_SW` → `PW_LDO` VIN/EN、`PW_C_IN`、`IMU.VBUS`、`TAIL_LED.F`、状态灯电容
3. 按键：`P_GATE` → `D_BTN_START` 阳极；阴极/`btn_sw` → `PW_R_BTN_SER` → `MCU pad16 (user_btn)`；`MCU pad11`=`PWR_LATCH`
4. 可选：`BAT_CELL_P` → `BAT_R_TOP`（不要接到 SYS_5V）
5. 清掉宽栈道里误穿的 USB/BOOT/UART 与旧 VBAT 残铜；`D_BTN_START` 勿压到 `PW_R_LATCH_PD`（btn_sw↔gnd 间距）
6. 半孔 `copper_edge_clearance`：手布完成后对 **逐项** 加 KiCad exclusion（不要整类放行）

目标：非豁免 error=0；主板本体 unconnected=0（加强片空气线可另计/单独下单说明）。

### V4 ECO 当前板况（手布前）

- Bringup TP：仅 **`TP_3V3` / `TP_SYS_5V_SW`**（大陆电源区）；`TP_GND` / `TP_MCU_*` 已删。位置进 `mainland_snapshot`（step4.1b）。
- 宽栈道快照仅剩 **SW_BOOT / SW_EN**（step4.1c）。
- DRC：**error = 0，unconnected = 0**（手布完成）。剩余 warning 仅为丝印 + `lib_footprint_mismatch`。
- 半孔：`default.kicad_dru` 已对 IMU/MCU/PZT/尾插做 edge_clearance 例外。
- **勿用** `20260715-092443` 导包；正式 ZIP 在验收通过后再导出。

## 6c. SS14 未解决压差（打板前必须选型）→ **V4 已取消**

业务已定：充电总成自带 4.2V 充 / 2.9V 过放 / ~1.2A 过流 / **5V 升压 OUT**。  
**不做** USB/电池双路 OR，**删除** SS14。唯一系统输入：

`充电总成 5V OUT → SYS_5V_IN → PMOS 软开关 → SYS_5V_SW → AP2112 → 3V3`

IM948：`VBUS←SYS_5V_SW`；`VBAT`/`VDDIO` **悬空**。  
低电采样若需要：另引电芯 **B+** → 尾插 `BAT_CELL_P` / 分压，**禁止**测 `SYS_5V_*`。  
烧录：充电仓 Type-C **通常无 D+/D−**，用柄尾 MX1.25 的 USB D+/D−（上电靠总成 5V OUT 或向 `SYS_5V_IN` 注入 5V）。

## 6d. 电源锁存 vs MCU 复位（故障安全）

硬件：`PWR_LATCH` 经 100k 下拉；固件上电拉高 GPIO10 保持开机。

电池供电下，下列事件会使 GPIO10 回到高阻/复位默认，下拉释放锁存 → **整机掉电**（不是自动重启）：
- `esp_restart()`
- 看门狗复位 / 崩溃复位
- BOOT 恢复出厂后的重启

**当前定义为预期故障安全行为**（复位即关机，需再按尾键开机）。若产品要求复位后自动保持开机，必须另做硬件保持（RC/专用锁存 IC）或改锁存拓扑——暂未做。

固件/文档：`power_control` + `docs/user-guide/button-operations.md` 已注明。

## 7. 宽栈道 BOOT / EN / 电源键 — **已完成**

- [x] 漏斗宽栈道 + `SW_BOOT` / `SW_EN` / `SW_PWR`（4.5×4.5）
- [x] 未占用 PZT 窄栈道
- [x] 大陆 bringup TP 精简为 `TP_3V3` / `TP_SYS_5V_SW`（不再强制 `TP_MCU_*`）

**下载手势：** 按住 **BOOT** → 点一下 **EN** → 松 BOOT。

> ~~金手指延伸~~ 已废弃：尾端改 MX1.25 正反 5P + 平收外形。

## 8. MCU 旁 0603 电源指示灯 — **已完成**

- [x] `LED_MCU_PWR` + `R_MCU_PWR_1K`：`vcc` → LED → `gnd`（不占 GPIO）
- [x] 位于 MCU 开窗旁大陆主岛；**可不贴（DNP）**

## 9. 其它已暴露、改板一并处理

- [ ] USB 原生枚举：回板后实测（半孔映射已按 pinmap；供电走 `SYS_5V_*`）
- [ ] 尾插电源/电芯反接保护（可选，当前无）
- [ ] C6 仅 2 路 RMT RX，4 路压电走 GPIO ISR（见 `TODOS.md`）——换 MCU 才是根本

## 10. 板厚（下单选项）

**建议：** 嘉立创等选 **PCB Thickness = 0.8 mm**（更贴拍面）。  
尾插已是 **MX1.25 卧贴端子**，**不再**做金手指叠焊加强片；板厚与尾座夹持无关。

## 建议改板文件触及面

| 文件 | 原因 |
|------|------|
| `pcb/lib/esp32c6n8/pinmap.py` | MCU 半孔 ↔ 工程绑定 ↔ 固件 GPIO |
| `pcb/main.ato` | 网络与尾插 MX1.25 |
| `pcb/tools/mech_geometry.py` / `step3_module_cutouts.py` | 开窗与 rule area |
| `firmware/main/config.h` | GPIO 变化时 |

## 验收（手布线 + 回板后）

1. MCU/IMU **不磨**即可落入开窗，半孔与焊盘目视同心。  
2. 不接 IMU 也能 USB 或尾插 UART0 稳定烧录；接上 IMU 后烧录仍不必拆焊。  
3. 冷启动默认关断；按键开机、固件自锁/关机逻辑正确。  
4. 板载 **BOOT + EN** 可进下载；调试键未占 PZT 窄栈道。  
5. 尾插正反 MX1.25 网络与 `docs/1.25x10p/README.md` 一致。  
6. MCU 旁 `LED_MCU_PWR` 焊位可用；DNP 时开路无影响。  
7. DRC：非豁免 error=0，主板 unconnected=0。

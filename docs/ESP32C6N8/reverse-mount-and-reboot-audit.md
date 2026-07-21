# 反焊朝向核对 × 循环重启审计（2026-07-21）

结合：商品图脚位（[`pinout-and-dimensions.md`](pinout-and-dimensions.md)）、`pcb/main.ato`、`TODOS.md` 通断实测、本次串口抓取。

## 1. 商品图 vs 板设计「长边朝哪」

### 厂商顶视（天线在上）

```
        ← 天线端 →
   1 GND          GND 28
   2 3V3          IO2 27
   3 EN           IO3 26
   4 IO4         TXD0 25
   5 IO5         RXD0 24
   …                …
  11 IO10         IO18 16
  14 IO13      IO9/BOOT 15
```

### 当前 footprint / ato 约定

`SGFK_ESP32-C6-N8_CUTOUT`：`ANT` 在 **−X**；**pin1–14 在 −Y**；pin15–28 在 **+Y**。

`main.ato` 注释写：pin1–14 = 拍柄/IMU 侧 = `GND/3V3/EN/IO4…`。

### 与装配意图的冲突（已有记录）

| 来源 | 靠 IMU（拍柄）一侧丝印 |
|------|------------------------|
| `V1_REWORK_PLAN` / `TODOS` 实装意图 | `GND · IO2 · IO3 · TXD · RXD`（即 **pin28 边**） |
| 当前 `main.ato` / bringup 后改表述 | `GND · 3V3 · EN · IO4 · IO5`（即 **pin1 边**） |
| 你目视（天线端起数） | 拍头侧 = `GND 3V3 EN IO4…`；拍柄侧 = `GND IO2 IO3…IO9` |

→ 你目视的丝印顺序与**商品图 + 正确顶视**一致；与「ato 说 pin1–14 在拍柄」**不一致**（要么模块相对 footprint 转了/翻了，要么 ato 注释把 −Y 当成了拍柄但布板 −Y 其实朝拍头）。

### 通断铁证（`TODOS.md`）

> 金手指以为 `UART_TX`→pad25，实际通到模块丝印 **IO4**；背面通 **IO5**。

按商品图：IO4/IO5 = **pad 4/5**；TXD0/RXD0 = **pad 25/24**。  
pad25 摸到 IO4 ⟹ **两长边在电气上对调了**（相对「顶面朝上、天线 −X」的正确落入）。

等价几何：相对正确顶视，模块像绕长轴翻了 180°（元件朝板背面），或 footprint 把 pin1–14 / 15–28 写在了反边。

---

## 2. 「反焊」时 pad 落点（天线端不动、左右对调）

同一 X 上：`pad k`（1–14 边）↔ `pad (29−k)`（15–28 边）。

| PCB pad（设计网络） | 设计以为模块脚 | 长边对调后实际模块脚 |
|---------------------|----------------|----------------------|
| 1 GND | 1 GND | 28 GND（仍 GND） |
| 2 3V3 | 2 3V3 | **27 IO2** ← 危险 |
| 3 EN | 3 EN | **26 IO3** |
| 4 IMU TX | 4 IO4 | **25 TXD0** |
| 5 IMU RX | 5 IO5 | **24 RXD0** |
| 10 LED | 10 IO8 | **19 IO21** |
| **11 PWR_LATCH** | **11 IO10** | **18 IO20** |
| 13/14 USB | 12/13 | 17/16 … |
| **15 BOOT** | **15 IO9** | **14 IO13 (USB_D+)** |
| **16 USER_BTN** | **16 IO18** | **13 IO12 (USB_D−)** |
| 24/25 调试 UART | 24/25 RX/TX | **5/4 IO5/IO4** |
| 26/27 PZT | 26/27 IO3/2 | **3/2 EN/3V3** ← 危险 |

你为纠正「天线/小件朝板背面」而反焊后：

- 若反焊后变成**顶面朝上**：应对照上表看当前到底是「对调中」还是「已纠正」；
- 若通断仍是 pad25↔IO4，则**电气仍按对调表**，固件里的「GPIO 号」与板网络名错位。

---

## 3. 循环重启：串口已定性（2026-07-21）

监听：`/dev/cu.usbmodem12301` @ 115200（阿哆诺桥，无 DTR/RTS）。

### 现象摘要

- 每次：`rst:0x1 (POWERON)`（**不是** `0x9` brownout，也**没有** Guru Meditation）
- SoftAP / HTTP / `WebSocket 数据推送服务已初始化` 能跑完  
- **下一句本应是 `init_imu()` → UART1 配 GPIO4/5**，从未出现任何 `IM948` / `UART1 初始化` 日志  
- 立刻再进 `ESP-ROM`，周期约 **2.7 s**（含 WiFi 里 2 s delay）

### 含义

| 排除 | 依据 |
|------|------|
| 纯软件 panic / `ESP_ERROR_CHECK` abort | 无 backtrace，且复位码是 POWERON |
| 典型 BOD 日志 | 无 `rst:0x9` |
| PWR_LATCH 没拉高导致「松手掉电」 | 日志有 `PWR_LATCH GPIO10 已拉高`；且你观察到一直有电（也可能 USB/桥接在供 3V3） |
| 尾键 2 s 软关机导致循环 | 与是否按键无关；且死点在 IMU init 之前 |

| 高度可疑 | 依据 |
|----------|------|
| **进 `init_imu` 时配置/驱动 IO4·IO5，EN 或 3V3 被拉塌** | 死点卡在 WS init 之后、IMU 首条日志之前；复位码 POWERON ≈ EN 脉冲或轨掉电 |
| **长边对调导致「固件以为的 IO4/5」与板上 EN/电源网纠缠** | 对调表里 pad4/5↔TXD0/RXD0，pad26/27↔EN/3V3；若 PZT/飞线/连锡再叠一层，极易在 UART init 时打 EN |
| 反焊后 3V3↔IO2 等电源脚错位 | 对调表 pad2↔IO2；严重时表现为上电异常或轨塌（你已能跑到 WiFi，说明至少有一路 3V3 进了芯片） |

### 与 GPIO10 / GPIO18「看起来正常」如何并存

- 日志里的 `gpio_set_level(GPIO10)` 只保证**芯片内部**该脚被驱动，不保证 pad11 铜皮接到锁存管。  
- 阿哆诺 USB 常能直接给 3V3/系统供电，**软开关是否真正自锁会被掩盖**。  
- 尾键「能识别按住 2 秒」说明 GPIO18 采样路径大致通，但在对调安装下 pad16 可能接到的是别的模块脚——需用丝印 **IO18** 对 pad16 再通断一次确认。

---

## 4. 建议核对步骤（按优先级）

1. **通断（断电）**  
   - 模块丝印 **IO10** ↔ 板 `PWR_LATCH` / pad11  
   - 丝印 **EN** ↔ 板 EN 网 / pad3  
   - 丝印 **IO4/IO5** ↔ 板 IMU TX/RX（勿通到 EN）  
   - 丝印 **TXD0/RXD0** ↔ 尾插 UART 金手指  
   - 若 IO4↔金手指 TX、IO10不通 pad11 → 仍处于长边对调

2. **复位瞬间示波/表笔**  
   - EN、TP_3V3：是否在 `init_imu` 时刻同步掉落

3. **固件 A/B**  
   - 临时注释 `init_imu()`；若循环消失 → 坐实 IMU UART / IO4·IO5 电气问题  
   - 再试：只 `uart_set_pin` 不开 IMU 供电/不发字节，缩范围

4. **改板（已在 TODOS）**  
   - 按商品图顶视重绑 footprint 长边 + `main.ato`  
   - 明确：顶面朝上、天线 −X、哪一长边朝 IMU  
   - IMU 与 UART0 隔离策略与通断结果对齐后再定 IO2/3 还是 IO4/5

---

## 5. 相关文件

| 路径 | 角色 |
|------|------|
| `docs/ESP32C6N8/pinout-and-dimensions.md` | 商品图脚位真理源 |
| `pcb/main.ato` | 当前 pad→网绑定 |
| `pcb/layouts/lib/footprints.pretty/SGFK_ESP32-C6-N8_CUTOUT.kicad_mod` | 几何与 pad 编号 |
| `firmware/main/config.h` | 固件 GPIO |
| `firmware/main/main.cpp` | `init_network` → `init_imu` 顺序 |
| `pcb/V1_BRINGUP_ISSUES.md` / `TODOS.md` | 历史脚位/通断记录 |

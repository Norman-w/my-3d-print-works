# SmartPaddle TODOs

## 压电 / RMT

- [ ] 标定/实测：量化 GPIO ISR 抖动对定位 RMSE 的影响，确认现方案是否够用
- [ ] 可选增强：GPIO glitch filter、或 GPTIMER 统一时基（仍非 RMT 波形捕获）
- [ ] 换带更多 RMT RX 的 MCU（如 ESP32-S3）再评估迁回 RMT

## 固件（firmware/）

- [ ] **Phase 1: WiFi + WebSocket 客户端** — IMU MessagePack + Impact JSON 上行
- [ ] **环形缓冲区管理** — 64KB ring buffer 缓冲 IMU/Impact，支持断线续传
- [ ] **LED 反馈** — WS2812C 按击球位置与定位置信度显示颜色
- [ ] **OTA 固件升级** — WiFi OTA
- [ ] **电池电量上报** — ADC 读 `BAT_CELL_P`，WebSocket status 帧上报

## 服务端（server/）

- [ ] **多球拍并发支持** — 验证多设备同时采集时的 SQLite 写入与线程安全
- [ ] **MessagePack 解码** — IMU 批量帧从 JSON 迁到 MessagePack
- [ ] **碰撞检测与分段** — 从 IMU 流自动检测挥拍段
- [ ] **轨迹重建优化** — 自适应 ZUPT / 磁力计辅助航向
- [ ] **标定网格纸自动生成** — 按 `grid_size` 动态生成 PDF

## 前端（web/）

- [ ] **击球热力图** — 3D 拍面叠加击球热力
- [ ] **Session 详情页** — IMU 曲线 + 击球列表 + 3D 回放
- [ ] **标定流程自动化** — WebSocket 直连固件自动采集，替代串口复制
- [ ] **贝塞尔编辑器撤销/重做**
- [ ] **多语言支持** — i18n（英/中/日）
- [ ] **移动端适配** — 重点 iPad 教练场景

## 硬件

- [ ] **C3 回板焊接 / bringup** — 历史批次（Gerber `20260724-081156`）；**当前以 C4 为主**，除非仍有一块 C3 待焊
- [ ] **C4 电路（当前刚性主板）** — 见 [`pcb/C4_PLAN.md`](pcb/C4_PLAN.md)；**裸板已到手**（Revision C4，PCB SHA `86389d959e48d7393d59ea44571635a1011f239213585d538611171193bb0b70`）
  - [x] PZT I²C 可调门槛比较器前端（MCP4728 + TLV1814 + 高阻 ADC 窥探 / 0Ω DNP）
  - [x] MCU 换 ESP32-S3-WROOM-1-N16R8；固件 target / 分区 / PSRAM / 脚位同步
  - [x] 尾插 MX1.25 线序重排：板坐标上 5V 正对 GND，USB/UART 成对（见 `docs/1.25x10p`）
  - [x] 电池分压、LED 数据串阻/去耦移到拍尾
  - [x] C4 63 个器件生成、受审 pad→net 表和无铜线 KiCad 交接板；独立 `TP_GND` 经 Norman 确认取消
  - [x] Step 3.2 C4 网表安全导入/复核器：真实 `.net` 解析、63 地址全拓扑门禁、旧/过时网表与已有铜线拒绝
  - [x] C4 PCB 标题栏、摆放前 16 页可打印装配包与 MX1.25 尾插装配图（渲染 QA 通过；63 件最终包待摆放回存后重生成）
  - [x] 经 `scripts/scad_to_kicad.sh` Step 3.1 用标准路径的 atopile 0.12.5 生成新 C4 网表；Step 3.2 完成 63 地址/182 连接焊盘号复核、188 实体焊盘对网及无摆放元数据流程
  - [x] C4 制造说明、板上 Fab 注释和安全导出门禁；未布线/未铺铜/未连通时禁止生产 ZIP
  - [x] C4 KiCad 手工布线/铺铜已回存（`828f6e1`）；KiCad 9.0.6 检查为 0 未连接、0 error，72 项丝印/库封装一致性 warning 已分类复核
  - [x] 手工布线完成后以 Step 4.1e 备份并只读复核 63 器件到 `c4_placement_snapshot.json`/放置脚本
  - [x] 铺铜、最终 DRC、物理焊盘连通性、Gerber/钻孔/ZIP 试导出与最终 14 页装配包；详见 [`pcb/C4_FAB_READINESS.md`](pcb/C4_FAB_READINESS.md)
  - [ ] C4 回板 bring-up（进行中）：对照 `output/pdf/smartpaddle-ai-assembly/smartpaddle-c4-solder-assembly.pdf` 手焊；内部槽边焊接、限流 5 V 上电、AP2112 温升、USB 数据尾线、MCP4728/TLV1814 PZT 链、IMU UART、射频与功耗
- [ ] **一体尾板与可换电池（规划）** — 整机/电气见 [`pcb/C5_PLAN.md`](pcb/C5_PLAN.md)；现行满截面尾板+壳体见 [`pcb-tail/`](pcb-tail/) 与 [`enclosure/README.md`](enclosure/README.md)
  - [x] 冻结总体架构：主板不延长；固定窄尾板与封闭14500电池匣沿 X 并排；电池匣从 `Y−` 向 `Y+` 推入
  - [x] 冻结交互：一个用户电气按键；侧面横向机械滑扣解锁；内端弱弹簧只顶出 3–5mm
  - [x] 冻结电气基线：IP5305T + 完整16P USB 2.0 Type-C + 单8P线束；D+/D−直达ESP32-S3；AP2112改TPS62162
  - [x] 冻结电池包基线：单节14500候选 K10；匣内 DW01A-G + FS8205A；禁止裸电芯直接供用户插拔
  - [ ] Gate 0：C4 布线、铺铜、DRC 和生产审计已完成；还需小批量回板关键 bring-up，再正式派生 C5
  - [ ] Gate 1：机械样块与接口尺寸冻结（现行路径：`export-stl.sh` + `pcb-tail`）
  - [ ] Gate 2：新建独立 `pcb/c5-tail/` 原理图/PCB，验证充电、升压、USB、按键、灯显、温升和轻载关机
  - [ ] Gate 3：从已冻结 C4 派生 C5 主板，更新 TPS62162、8P接口、USB串阻和生产门禁
  - [ ] Gate 4：M5.C5 整机换电、振动、汗液、USB、无线、跌落和插拔寿命验证
  - [ ] Gate 5：电芯批次/温度/运输资料、保护阈值、DFM和量产测试全部完成后移除“未验证”标记
- [ ] **主线 V2** — 双 IMU + 更强 MCU；拍柄 IMU 基台与模型/电路协同
- [ ] **软件自动发版** — SemVer + CI（固件/服务端/前端）

## 测试与文档

- [ ] **端到端集成测试** — 固件 → 服务器 → 前端联调
- [ ] **标定精度验证** — 机械臂或已知敲击点
- [ ] **API 文档** — OpenAPI 补全示例与错误响应
- [ ] **开发者指南** — 本地环境搭建说明

## 远期

- [ ] **移动 App（React Native / Flutter）**
- [ ] **多球拍赛事系统** — 2–4 拍同时接入与对战统计
- [ ] **云端 SaaS 部署** — Docker + PostgreSQL，多租户
- [ ] **AI 击球质量评分** — 基于 IMU + 定位数据

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

- [ ] **C3 回板焊接 / bringup** — 通电、烧录、软开关、IMU UART、PZT、WS2812
- [ ] **M5 外壳** — 拍头↔拍柄连接优化；评估充电板 Type-C 卡槽
- [ ] **C4 电路** — 电池焊盘、LED 等直接布到拍尾，避免飞线焊
- [ ] **主线 V2** — 双 IMU + ESP32-S3；拍柄 IMU 基台与模型/电路协同
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

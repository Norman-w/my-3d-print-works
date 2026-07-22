# SmartPaddle TODOs

### 压电 4 通道 vs ESP32-C6 RMT（2026-07）

**硬件已定：** 拍面四角 4× 压电 → GPIO2 / 3 / 6 / 7，必须同时采 4 路做 TDOA。

**芯片限制：** ESP32-C6 RMT 共 4 通道，但仅 **2 个 RX 候选 + 2 个 TX 候选**（`SOC_RMT_RX_CANDIDATES_PER_GROUP=2`）。无法用 RMT 同时接收 4 路边沿；再叠加板载 WS2812 占用 1 路 RMT TX，冲突更明显。

**当前方案（固件已落地）：** `piezo_capture` 改为 **GPIO 上升沿 ISR + `esp_cpu_get_cycle_count()` 锁存**，保留 4 路同时首边沿时间戳；LED 继续用 `led_strip` 新 RMT。相对原设计的纯硬件 RMT（~12.5ns、低抖动），现为 CPU cycle 相对时差（约 6–12ns 量化）+ ISR 进场抖动。

**代码位置：** `firmware/main/piezo_capture.{h,cpp}`、`config.h` 注释。

**后续可选升级（不改现板则无法回到 4×RMT）：**
- [ ] 标定/实测：量化 ISR 抖动对定位 RMSE 的影响，确认现方案是否够用
- [ ] 可选增强：GPIO glitch filter、或 GPTIMER 统一时基（仍非 RMT 波形捕获）
- [ ] V2 换带更多 RMT RX 的 MCU（如 ESP32-S3 等）再评估迁回 RMT / 新 RMT RX API
- [ ] 文档：`docs/README.md` 仍写「12.5ns RMT」——需与现实现对齐后更新

## 固件（firmware/）

- [ ] **Phase 1: WiFi + WebSocket 客户端** — 将 Phase 0 的串口输出升级为 WiFi 连接，实现 IMU 二进制帧（MessagePack）和 Impact JSON 帧的 WebSocket 上行
- [ ] **ICM-42688-P IMU 驱动** — SPI 初始化、FIFO 读取、1kHz 采样配置，与压电采集共用时间基准
- [ ] **环形缓冲区管理** — 在 64KB ring buffer 中同时缓冲 IMU 帧和 Impact 事件，支持断线续传
- [ ] **LED 反馈** — WS2812C 根据击球位置和定位置信度显示颜色反馈
- [ ] **OTA 固件升级** — 通过 WiFi OTA 推送新固件
- [ ] **电池电量上报** — ADC 读取电池电压，定期通过 WebSocket status 帧上报

## 服务端（server/）

- [ ] **多球拍并发支持** — 当前 session 管理支持多连接，需验证多设备同时采集时的 SQLite 写入性能和线程安全
- [ ] **MessagePack 解码** — IMU 批量帧从 JSON 迁移到 MessagePack 二进制格式，减少传输带宽
- [ ] **碰撞检测与分段** — 从连续 IMU 流中自动检测挥拍段（swing segmentation），替代当前的简单计数
- [ ] **轨迹重建优化** — 当前 ZUPT 阈值为固定值，可改为自适应阈值或引入磁力计辅助航向
- [ ] **标定网格纸自动生成** — 根据 `grid_size` 参数动态生成 PDF 网格纸（当前 `grids/` 目录为空）

## 前端（web/）

- [ ] **击球热力图** — 在 3D 拍面上叠加击球位置热力分布
- [ ] **Session 详情页** — 点击 SessionBrowser 列表项进入详细回放视图（IMU 曲线 + 击球列表 + 3D 回放）
- [ ] **标定流程自动化** — 当前需手动从串口复制 TDOA 数据到输入框，应通过 WebSocket 直连固件实现自动采集
- [ ] **贝塞尔编辑器的撤销/重做** — 当前无历史栈
- [ ] **多语言支持** — i18n（英/中/日）
- [ ] **移动端适配** — 响应式布局，重点适配 iPad 端教练场景

## 硬件

### 版本路线

| 版本 | 方案 | 详情 |
|------|------|------|
| **V1 历史** | 第一次打板（已回板） | 初次装配暴露封装/脚位/开窗/UART 等问题 |
| **V2 当前** | 刚性骨架 PCB + ESP32-C6-N8 + IM948 | 装配验证中；V2→V3 布局/封装反馈已落盘，待布线与打板 |
| **V3 下一版** | 消化反馈后的打板 | 布局侧已改完（二极管 HandSolder、码头旋转、4.5 THT 测试键、TP_GND）；布线清理后出 Gerber |

### 待办

- [ ] **外壳 3D 打印试装** — 四零件(paddle_shell)打印与装配验证
- [ ] **压电传感器选型与安装方案** — 20mm 陶瓷片 ×4，确定粘贴位置、引线走法
- [ ] **电池选型** — 确定电池容量、尺寸、充电方案（USB-C, TP4056）
- [ ] **远期：双 IMU + ESP32-S3** — 拍头+拍柄 IM948，拍柄 IMU 基台设计
- [ ] **远期：柔性 PCB** — 分立芯片集成，柔性 FPC 铺满拍面消除空鼓感（`pcb_V3_flex_backup/`）

## 测试与文档

- [ ] **端到端集成测试** — 固件 → 服务器 → 前端完整链路实测（当前各层独立开发，未联调）
- [ ] **标定精度验证** — 使用机械臂或已知敲击点验证定位精度
- [ ] **API 文档** — OpenAPI YAML 已有但未补全示例和错误响应
- [ ] **开发者指南** — 补充本地开发环境搭建说明（dev.sh 已有但缺文档）

## 远期

- [ ] **移动 App（React Native / Flutter）** — 替代 Web 端用于场边实时分析
- [ ] **多球拍赛事系统** — 同时接入 2-4 支球拍，生成对战统计
- [ ] **云端 SaaS 部署** — Docker 化 + PostgreSQL 替代 SQLite，支持多租户
- [ ] **AI 击球质量评分** — 基于 IMU+ 定位数据训练挥拍质量模型

# pcb_V3_flex_backup

> **V3 阶段恢复使用**：当前 V1/V2 为成品模块飞线方案，atopile 不在主工程中使用。

## V3 计划

- 将 ESP32 模组、IMU 芯片（ICM-42688-P）、充电芯片、LDO、运放等分立元件集成到一块定制 PCB 上
- **柔性 FPC** 铺满整个拍面区域，消除空鼓感
- 手柄部分用刚性 PCB，拍面部分用柔性 FPC，刚柔结合
- 重新使用 atopile 进行电路原理图/PCB 设计

## 当前备份内容

- `main.ato` — 原 SmartPaddleBoard 电路设计（ESP32-S3 + ICM-42688-P + 电源 + 4ch 压电前端）
- `ato.yaml` — atopile 0.12.4 项目配置
- `layouts/` — 生成的 KiCad PCB 版图
- `build/` — 最后一次构建产物（2026-05-30）

## todo

V3 时需根据最终芯片选型重新设计，当前备份仅供参考。

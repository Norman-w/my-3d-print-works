# 已废弃：C5 主板延长/电池长窗机械预览

> **SUPERSEDED / 禁止继续实施 / 禁止据此投板。**

本目录曾用于预览“把 C4 主 PCB 一直延长到拍尾，并在中间开长窗放一节14500”的方案。该方案已经被正式否决，不代表当前 C5：

- 主板不再延长到拍尾。
- 不再在主 PCB 中间给电池开窗。
- 不再让电池、USB和主板共用一块长板。
- 本目录中的 `.kicad_pcb`、预览图、生成脚本和尺寸报告即使仍存在，也只能作为废弃概念的历史证据；不得作为新板外形、封装坐标、SCAD尺寸或布线输入。

当前 M7.C5 的设计真理源是：

- [`../../docs/power-architecture-rework/README.md`](../../docs/power-architecture-rework/README.md)
- [`../ROUTING_HANDOFF.md`](../ROUTING_HANDOFF.md)
- [`../../pcb-tail/README.md`](../../pcb-tail/README.md)
- [`../../enclosure/README.md`](../../enclosure/README.md)

现行方向为：

> 主板保持现有大陆/栈道结构；独立满截面尾板集成完整 USB 2.0 Type-C、IP5305T、ACH 电池接口、B3U 与两级限流，通过现行 2×4P→2×5P 线束连接 C5 主板，并由 M6 连续承力外壳与尾段干涉模型约束。

现行实现已经位于通用 `pcb/` 与 `pcb-tail/`，不得再建立版本号专用实施目录，也不得复用本目录的长板文件。

# 蛇链触发中心离合动态演示

- 记录日期：2026-10-02
- 目的：记录蛇形链条上的触发载台接近中心离合、磁铁对齐、公轮沿 `+Y` 合入母轮、保持、释放离开的过程。
- 动态素材：
  - [MP4 原始动态演示](assets/chain-clutch-event-full-v2.mp4)
  - [GIF 预览（适合直接在文档中查看）](assets/chain-clutch-event-full-v2.gif)

## 视图与装配范围

采用固定等轴视角，同时显示：

- 真实 03C 链板、滚子和销轴；
- 触发载台、两根加长穿销、卡簧和触发磁铁；
- 中心输入公轮、D-round-D 轴、圆套/磁铁、LM3UU 参考；
- 输出母轮、短轴和上下 3×6×2 轴承参考。

为保证链条和离合主体都可见，承载板在这份过程记录的检查视图中隐藏；生产 STL/网页装配关系没有因此删除承载板。

## 动作阶段

1. 链条带着触发组件接近；
2. 触发磁铁与公轮下方磁套对齐；
3. 输入公轮沿 `+Y` 推入母轮；
4. 合位保持；
5. 释放后公轮回到开位，链条离开。

## 来源与验证

- 网页运动绑定：[web/cabinet-preview/js/cabinet-chain-play.js](../../../web/cabinet-preview/js/cabinet-chain-play.js)
- 中心离合审计：[docs/parts/center-clutch-interference-audit.md](../../parts/center-clutch-interference-audit.md)
- 链条同步验证：[scripts/validate_cabinet_chain_sync.py](../../../scripts/validate_cabinet_chain_sync.py)
- 视频由 OpenSCAD 原生 `$t` 动画帧编码生成：960×720、24 fps、2 秒；GIF 为 640×480、16 fps、2 秒。

该记录证明的是源几何/装配预览和动态关系，不替代真实打印件、磁极、轴承压入、防脱、干涉和负载循环验收。

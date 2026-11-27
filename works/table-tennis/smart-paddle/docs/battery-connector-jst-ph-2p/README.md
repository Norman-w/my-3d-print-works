# 尾板 2P 电池接口：JST PH 历史候选（已停用）

状态：**不再用于当前 Atopile 或 PCB。** 早期曾把 J4 定义为 `S2B-PH-K-S(LF)(SN)` 通孔侧插；实物空间复核后，已由更小的 [JST ACH 1.2 2P 顶插方案](../battery-connector-jst-ach-2p/README.md)替代。旧 PH footprint、F.Cu 待摆坐标和相关 DRC 数字均不得作为当前板依据。

此目录仅保留当时的 [JST PH 官方目录](JST-PH-official-catalog-2025.pdf)作为选型溯源，来源为 [JST 官方 PDF](https://www.jst.com/wp-content/uploads/2025/06/ePH.pdf)，SHA-256 `5878e549f54c42a0d544d26fa75a666ad6f0f9486aaf4b4f44f1279cead9e524`。

停用原因：PH 2P 侧插/THT 的机械包络和通孔占用都大于 ACH，不符合本版尾板背面余量；现已购买/确认的 ACH 成品线可以满足“不自行压端子”的采购目标。PH 与 ACH 的壳体、节距、端子完全不同，不能互插，也不要把已购 PH 线硬接到 ACH 板端。

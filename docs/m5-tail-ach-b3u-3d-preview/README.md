# M5 尾板 ACH + B3U 3D 预览

本目录是本轮选型的 KiCad 3D 视觉核对，不是制造输出。

## 图像含义

- `current-front-isometric.png`：当前源 PCB 正面。SW1 已是原厂 B3U-1000P 3D 模型。
- `current-back-isometric.png`：2026-08-14 拆铜前的历史源 PCB 背面，J4 位于 `(-2.794,-5.969) mm`、`90°`。
- `candidate-back-orthographic.png`：布线前的历史候选图；当时仅在预览副本中把 J4 临时放到 B.Cu `(-3.050,-7.425) mm`、`90°`。
- `candidate-back-isometric.png`：同一个布线前历史候选的背面透视图。

候选图只记录布线前的空间判断；当前图才代表用户完成布线后的 PCB。所有图都不含插入后的 ACHR-02V-S 线端外壳、导线和弯折半径，最终机械朝向仍要结合拍柄空腔确认。

## 3D 模型证据边界

- B3U 使用 `docs/tail-user-switch-b3u-1000p/kicad/SW_SPST_B3U-1000P.step`，是 KiCad 9 stock STEP。
- ACH 使用 `docs/battery-connector-jst-ach-2p/kicad/JST_ACH_BM02B-ACHSS-GAN-ETF_simplified-preview.wrl`。JST 官方 STEP 需要提交许可表和个人邮箱，本项目未代用户提交；该模型仅复现官方 PDF 的 4.2×4.3×1.4 mm 外包络，内部细节是示意。
- OpenSCAD VRML 坐标在 KiCad 中按 2.54 倍解释，J4 模型块已使用 `0.393701` 缩放恢复毫米外形。该比例已经通过 KiCad 实际渲染核对。

这些图片均是本轮电源重整前的历史选型预览，不代表当前 PCB。当前源板为 33 个封装、0 条走线、0 个过孔、0 个覆铜区；最新预览放在 `docs/power-architecture-rework/previews/`。本次没有生成制造文件。

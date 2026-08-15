# M5 尾板用户键：Omron B3U-1000P

状态：**Atopile 与 PCB footprint 已换成 B3U-1000P；SW1 保持原锚点与角度，当前 PCB 已清除全部铜并待重新布线，拍柄制造 STL 没有在本次生成。**

## 器件与封装

- 精确型号：Omron `B3U-1000P`，顶按、SPST-NO、无接地端、无定位柱、SMT。
- 官方资料：[Omron B3U 产品页](https://components.omron.com/us-en/products/switches/B3U)与 [B3U 数据表](https://components.omron.com/us-en/system/files/2023-01/datasheet_pdf/A162-E1.pdf)。数据表给出本体 3.0×2.5×1.2 mm、操作高度 1.6 mm、操作力 1.50±0.49 N、预行程 0.15 mm、执行头直径 1.5 mm。
- KiCad footprint：`Button_Switch_SMD:SW_SPST_B3U-1000P`，stock footprint SHA-256 `cde2d6cafc390e73f300ce36157ec6d8933f1bd4d2aa4758a9aa98beee6aff1e`。
- Pad 1=`user_btn`，Pad 2=`GND`；按下短接，电路意图未改变。

## 项目内归档

- `Omron-B3U-A162-E1-07-official.pdf`：Omron 官方文件服务器提供的 A162-E1-07 版本，SHA-256 `271b3d35eb58fac7449cb36bbe6a78b36439baa29281e74da83bede2b7ba8b01`。当前官网 A162-E1-08 的器件尺寸页与本选型一致。
- `kicad/SW_SPST_B3U-1000P.kicad_mod`：KiCad 9 stock footprint 原文件。
- `kicad/SW_SPST_B3U-1000P.step`：KiCad 9 stock 3D model 原文件，SHA-256 `4b5ee4da023d76030db22a90f5835f3691d5e4e9fc41b3f37b2c5922c65d307b`。

PCB 的 SW1 模型路径已经改为项目内 `docs/` 相对路径，因此换电脑打开 KiCad 时不依赖本机是否安装同版本的 stock 3D library。

## PCB 与机械约束

SW1 仍在 F.Cu 原锚点 `(-1.651,-5.461) mm`、`-90°`；只替换 footprint，没有移动或旋转它。Pad 1=`user_btn`、Pad 2=`GND`，当前待重新布线。

拍柄不得使用刚性固定柱持续压住开关。基准操作方式是在 SW1 执行头中心生成 **Ø2.0 mm 直通针孔**，可用笔尖、针尖或细棒直接按下；该方式不依赖打印推杆行程，也不增加尾板空间占用。

项目同时保留一只可选的**导向活动推杆**：Ø1.6 mm 轴配 Ø2.0 mm 导向孔，从壳内装入；内侧 Ø3.0×0.5 mm 法兰大于孔径，装配后不能向壳外掉出，尾板上的 SW1 又限制其向壳内迁移。静止端面与开关留 0.05 mm 名义间隙，壳外名义露出 0.30 mm；从静止到触发的理论位移为 0.05+0.15=0.20 mm。B3U 自身弹力负责回位。拆下尾板时应同时取出并收好推杆。

0.30 mm 外露/最大行程目前只是推杆试片参数，还不是已经验证的机械止挡。数据表预行程范围 0.05…0.35mm；加 0.05mm 静止间隙后，最坏触发需要 0.40mm，超过当前 0.30mm 最大行程。因此推杆仍标记为可选试片附件，批量采用前必须按材料与打印精度验证；这不阻塞已经独立成立的 Ø2.0 mm 针孔基准方案。

`pcb-tail/scripts/export_tail_interference.py` 以实际 SW1 位姿输出 B3U 本体、执行头、针孔和推杆事实；`scripts/step6_tail_board_interfere_handle.py` 据此生成直通针孔及独立防脱推杆。本次只在临时目录生成诊断件，不覆盖用户当前制造 STL。

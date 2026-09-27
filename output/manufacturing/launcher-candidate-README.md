# 点射可调旋转版：数字制作候选包

这是供审阅、切片设置复核和成品制作准备的候选快照，**不是制造发布，也不保证首次实物一次通过**。没有连接打印机、发送打印任务或下单。

包内含 43 个打印 STL：送料 33 件、旋转头 10 件；审查 3MF 为送料 20 板、旋转头 10 板。每板已经包含清单所示数量，同一板不要再按数量重复打印。金属五金、PC 管和弹簧参考体、历史失败板及诊断相交体均不作为打印件收入。

先读 `docs/final-assembly.md`；送料姿态和支撑清理见 `docs/final-feeder-print.md`，旋转头见 `docs/final-spin-print.md`、`docs/spin-complete-hardware.md`。密封按 `docs/final-sealing-process.md`，误差边界见 `docs/final-gate-error-bound.md`。CAD 入口为 `cad/launcher-final-assembly.scad` 与 `cad/spin-head.scad`，二者接在原机不同位置，不能同轴叠装。

所选板以 `manifest.json` 的 `selected_plates` 为准，文件保持原仓库相对路径。3MF 自带实际 G-code；打包时已核对其与所选报告、源 STL、源 CAD 和外部 G-code 的哈希关系，不额外复制裸 G-code。保留审查结果原状态：送料 `BOUNDED_OFFLINE_SLICE_REVIEW_PASS_PHYSICAL_OPEN`；旋转头 `OFFLINE_SPIN_SLICES_AND_BOUNDED_SUPPORT_ACCESS_PASS_PHYSICAL_OPEN`。送料未关闭的报告检查：`{}`。

机器配置为 X1C / 0.4 mm；送料 33 件及旋转头 9 件用 PETG，唯一柔性件 `spin-pad.stl` 用 Bambu TPU 95A HF、100% 填充、外置料盘。Generic PETG 品牌和纹理 PEI 为分析配置假设；用户确认了 PETG 和 PEI，尚未确认实际 PETG 品牌及 PEI 纹理。打开审查板后核对实际机器、床面、材料和支撑清理安排；本包不自动发打印。

尚未关闭的边界：

- 入口钢丝软管的桥箍尚未按实物螺距/凸起锁定；织带负责卸载，不等于气密箍。
- 全行程总位置误差尚未认证为 ±1 mm；现有可调压条不能直接消除公共架固定 Y 导向的全部滚转。
- 真实打印配合、支撑去除后的表面、V 座/M2 预紧保持、PETG 变形/蠕变、密封、夹持及弹簧回位均未实物验收。
- 点射一次一球与旋转效果没有完成整机测试；初始球就位、完整扣动和完整回位仍是操作前提。

`manifest.json` 是包内文件哈希、来源与板/实例清单；`SHA256SUMS` 包含其自身以外的所有包内文件（包括 manifest）。可在解压根目录运行 `shasum -a 256 -c SHA256SUMS` 检查传输完整性。哈希通过只证明文件未变，不提升任何制造或物理状态。

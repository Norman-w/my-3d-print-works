# 当前卡簧轴方案的制造重绑

最终入口：[56 件 manifest](binding-02/manifest.json)，SHA256 `b0d076467560470934fcf75f54f06ab507ec731640b62fb10fb8950761fe0572`；[逐实例模型证明](binding-02/report.json)，SHA256 `0ccb49b7d61353517842f244cbbc4c193cda4f92a932e0bbb9e6966e73a64ba8`。

新导出为 `output/cable-scene-export/20260927T153058669616Z/report.json`（整体 PASS）。未使用首轮失败总报告作为最终绑定，未重切片、未提交打印，也未覆盖旧 top-level 制造 manifest。

- 52 件在原 CAD 坐标的全部有向三角面多重集合精确相同；其中 38 件 STL 字节相同，其余差异不被当作几何变化。
- 端球捕获盖严格满足新 CAD 到旧 CAD 的 `[0,+3,0]` 平移。其实际 3MF normal mesh 再验证无缺面/新增面/塌面，最大角点数值转换位移 5.57196863e-07 mm；原支撑、G-code 与局部特征坐标映射均保留，局部映射最大差 1.42e-14 mm。
- 主体、杠杆、固定盖三件改形，`needs_reslice=true`、`pending_review=true`、`selected_3mf=null`。旧板只存为历史证据，不进入当前选定板。

结果：56 件中 53 件绑定、3 件待重切，39 个选定板；共板数量再次核对，同一板只打印一次。每件保留原绑定报告、3MF、G-code 的 SHA；材料仍为 55 PETG＋1 TPU95A HF。老报告的整套源身份没有冒充当前状态；既有精度归一化 FLAG、支撑清理条件和物理限制随绑定报告继承。所有放行字段保持 false。

## 坐标与历史调用

新增 `analysis/cable_slice_contract.py`：只从 invocation 中 SHA 绑定的 export-report / 冻结 inventory 取 ci 与 cr。旧切片仍用 origin `[75,-82,5]`，本版用 `[75,-85,5]`；不读取当前全局清单来回填历史坐标。老低精度 ECHO 的 45° 基只使用源中明确的 sqrt(.5) 形式；缺少 route 标量时仅对已知旧 route 源 SHA 使用旧解析标量。当前源不匹配旧报告时明确记录 historical drift。

三个审查入口已消费该坐标来源。原 wrap 槽杠杆/定距管盖 ROI 仍有版本闸，不能拿来给新轴孔、六角套窝和根部让位孔放行；这三件需要新特征审查。端球旧诊断脚本的旧候选身份闸仍保留，不将其旧直拉运动公式冒用为本版完整检查。

[坐标回归结果](coordinate-check.json) 已实际读旧 3MF 并恢复映射；旧/新第三弧相同。错误报告 SHA、错误输入 STL、未知路线常量、反向面及 1 nm 改点均拒绝。[代码差异](interface.diff) 针对采用前冻结源。binding-01 是补依赖哈希前的试跑，不作为最终入口。

复跑使用 FreeCAD Python：`scripts/rebind_eclip_manufacturing.py --export-report output/cable-scene-export/20260927T153058669616Z/report.json --baseline-manifest output/cable-eclip-adoption/20260927T151752917841Z/manufacturing/pre-adoption/manifest.json --output <新的空目录>`；坐标检查为本目录 `test-contracts.py`。完整几何/工艺和正式首机验收仍按根任务分项执行。

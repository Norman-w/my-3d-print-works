# 未发布的几何候选

这里的 STL 用于工程审查，不是整套可打印交付包。当前仍有机构误差预算、密封、实际接口、弹簧/软垫及实物功能证据未闭合，不能据此声称首次打印通过。

当前清单导出使用 `p01-` 至 `p15-` 的稳定文件名前缀，对应 `docs/candidate-bom.json`。身份、网格、尺寸和数量记录在 `output/analysis/candidate-inventory.json`；共15种基线几何、19件，不含可调导向替代方案及未选件。其他未列入清单的文件是历史研究或单项导出，不应混入制造清单。可用 `python3 scripts/export_candidate_inventory.py` 重新生成。

两件 feeder-body 网格分别是沿 X=0 分开的壳体。源文件为 `cad/feeder-body.scad`，名义外包络每半 35.5 × 90 × 195 mm；坐标保留装配位置，未平移到打印床。STL 单位本身不记录，源设计按 mm。

候选件变更后需重导出并核对源哈希。最终零件清单、支撑策略、打印方向及 Bambu 切片包尚未发布。

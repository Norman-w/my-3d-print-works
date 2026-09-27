# 卡簧空间参考层接入检查

代码已就绪；未调用 inventory sync 主入口、未导出 CAD、未发布 LAN。

新增 `feeder/cable-input-eclip-space` / `input-eclip-space`，`role=reference`、`motion.kind=fixed`。显示字段为 `display={kind:space-requirement,default_visible:false,color:#f2a340,opacity:0.22}`。名称明确“E卡簧安装空间要求（非环实体）”，勾选项提示不代表工具已经适配。它保持隐藏默认值；勾选、取消、整体附件层开关和三种表面模式不会把透明空间变成实体。

同步脚本只追加这一个参考实例，幂等；清单期望 86＝56 打印＋23 采购组＋7 参考。原 85 个 ID 不变；输入 body 和 fixed-hardware 均明确 CGAL。新增参考亦用 CGAL。发布脚本将 display 深复制透传到两个 manifest，并发布新增 `web/scene-display.mjs`。真实五金分组未拆分或增加。

本地行为测试执行了生产 metadata/publisher helper，以及实际 `applyRecord`、`rowColor` 和目录勾选回调。通过 7 项显示/动态契约检查、85 行保留及幂等检查、JS/Python 语法检查。测试采用假网格路径与 DOM/材质桩，不声称真实浏览器已验证。正式 inventory 字节未改；几何与浏览器验收由根线程统一继续。

复跑：`python3 output/cable-eclip-adoption/20260927T151752917841Z/frontend/test-metadata.py`，随后 `node output/cable-eclip-adoption/20260927T151752917841Z/frontend/test-display.mjs`。

[报告](report.json)；[相对冻结前源的差异](interface.diff)。不把显示层、候选销或空间预算认作真实 E 环实体或已验证的装拆工具。

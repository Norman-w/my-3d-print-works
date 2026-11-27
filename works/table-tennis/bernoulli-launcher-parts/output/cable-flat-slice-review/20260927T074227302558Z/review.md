# 四个平面拉索件：实际打印路径复核

采用输入盖 0.1 mm、输出保持盖 0.1 mm、导向盖 0.2 mm、下托 0.2 mm 的离线路径。四件所检孔口和向上开放沉窝均无内部支撑；检查的是实际 G-code，不以切片退出码作结论。

| 零件 | 采用层高 | 关键结果 |
|---|---:|---|
| 输入盖 | 0.1 mm | 轴套窝 4.5 mm、方窝 4.3 mm 承面准确落层；原 0.2 mm 反例保留 |
| 输出保持盖 | 0.1 mm | Y39.9 承面落在打印高 3.3 mm，后续层扩大到垫圈窝 |
| 输出弯道导向盖 | 0.2 mm | 6 孔与连续开槽有净空；OD5 护套包络逐层无路径侵入 |
| 导向夹具下托 | 0.2 mm | 4 个六角螺母窝开放，Z81.3 承面落在打印高 3.4 mm |

原输入盖 0.2 mm 路径把两个承面分别做成 4.6 / 4.4 mm，占用 0.1 mm 名义配合余量。此次仅由根任务重切输入盖，未改 CAD、未覆盖反例。不能据此反例断言实物必装不进。

每份报告保存源、STL、G-code 与 3MF 身份、完整坐标变换、每层净空数值及已查看的关键层图片：

- [cable-input-cover](/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/print-review/current-cable/20260927T074227302558Z/cable-input-cover/flat-path-review/report.json)；[关键层图](/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/print-review/current-cable/20260927T074227302558Z/cable-input-cover/flat-path-review/key-layers.png)
- [cable-output-cap](/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/print-review/current-cable/20260927T073454146325Z/cable-output-cap/flat-path-review/report.json)；[关键层图](/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/print-review/current-cable/20260927T073454146325Z/cable-output-cap/flat-path-review/key-layers.png)
- [cable-route-cap](/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/print-review/current-cable/20260927T073454146325Z/cable-route-cap/flat-path-review/report.json)；[关键层图](/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/print-review/current-cable/20260927T073454146325Z/cable-route-cap/flat-path-review/key-layers.png)
- [cable-route-lower](/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/print-review/current-cable/20260927T073454146325Z/cable-route-lower/flat-path-review/report.json)；[关键层图](/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/print-review/current-cable/20260927T073454146325Z/cable-route-lower/flat-path-review/key-layers.png)

[输入盖原 0.2 mm 反例](/Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/print-review/current-cable/20260927T073454146325Z/cable-input-cover/flat-path-review/report.json)。

支撑清理：这四件没有生成内部支撑，只需在零件外围处理 5 mm brim；孔口/窝口仍须防止首层挤压或毛边占用间隙。此项不证明首层实际尺寸、PETG 承载/蠕变或装配寿命，也不覆盖高导向底座的层间抗弯。无试片、无打印发送。

# v4 单外壳打印交付

本目录最终可用文件：

- `slice/fan-tee-v4-native-project.3mf`：拓竹桌面端保存的可编辑项目，只有一个外壳。
- `slice/fan-tee-v4-native-actual.gcode.3mf`：桌面端最终切片，设备标识 `BL-P001`；本次已从同名原生项目发送。
- `../stl/fan-tee-v4-connector-clean.stl`：干净模型，无内置支撑。
- `native-slice-audit.json`：最终原生切片、两侧卡扣支撑接触及STL逐三角面一致性记录。
- `print-status.json`：本次设备执行观察记录；不要把切片验收当成打印完成或实配通过。

X1C 0.4 mm，纹理PEI，AMS A3灰色PETG，0.2 mm层高、4层墙、25%填充。喷嘴255°C，热床70°C。自动树形支撑，阈值45°，仅热床生成、不移除小悬空，顶间隙0.2 mm、XY间隙0.25 mm；外侧Brim 6 mm、间隙0.1 mm。自动调平和动态流量校准在发送时均开启，延时摄影关闭。

最终估计7232秒、60.54 g、492层。所有普通支撑与支撑接触层均不超过打印Z=8.6 mm，两侧圆片下方各有接触路径；螺纹处无支撑。原生项目网格与干净STL在0.001 mm比较精度内逐三角面一致，立放且没有缩放。启动和结束G-code与上次原生成功项目快照完全相同。

`config/` 是可独立复现的预设快照，不依赖已移入废纸篓的旧目录。`scripts/prepare_fan_tee_v4_print.py` 可重建CLI预检切片，但CLI产生的项目打开时可能恢复为系统默认工艺，且其切片设备ID可能为空；**不能直接拿CLI预检包发送**。应使用上面的原生项目，或重新在桌面端核对工艺、切片、导出并审查。不要修改账号、语言或打印机绑定来处理包内预设问题。

核验最终包：

```sh
python3 scripts/verify_fan_tee_v4_print.py \
  output/fan-tee-direct-print-v4-20261007/print/slice/fan-tee-v4-native-actual.gcode.3mf \
  --geometry-package output/fan-tee-direct-print-v4-20261007/print/slice/fan-tee-v4-native-project.3mf \
  --lug-support-ceiling 12 \
  --report output/fan-tee-direct-print-v4-20261007/print/native-slice-audit.json
```

本次只打一个外壳，旧风嘴芯不重打。风机卡扣槽底深度、三通实际松紧和母牙强度仍需首件实配确认。

## 仓库交付范围

仓库保留最终干净STL、上面两个原生3MF、预设快照、审查图片、兼容性参考网格和文字验证记录。原始G-code、重复CLI预检包、临时切片元数据、日志、缓存和可重建的 `review/*.stl` 不提交；辅助网格可用几何交付说明中的导出命令重建。

`../verification/owned-files.json` 是原几何生成现场的散列清单，包含本地生成的日志和辅助网格，并非Git跟踪清单。`print-status.json` 只记录其 `observed_at` 时刻的设备观察，不表示当前打印状态、最终完成或实物装配验收。

# 双风机当前装配与交付入口（2026-10-07）

当前两种方案均由打印主体直接插入 Y 三通，不使用中间透明管，也不使用旧外套夹紧结构。

| 风机 | CAD / 交付包 | 螺距 | 机构有效行程 | 气嘴出口内径 |
| --- | --- | --- | --- | --- |
| Ø76 | `cad/fan76-direct-v1.scad` / `output/fan76-direct-longtravel-v1-20261007/` | P4 | 80 mm / 20 圈 | 15、20、25、30 mm |
| Ø41 | `cad/fan-tee-narrow-v5.scad` / `output/fan-tee-narrow-nozzles-v5-20261007/` | P4 | 40 mm / 10 圈 | 15、20、25、30 mm |

Ø76 主体高 222 mm、气嘴长 160 mm；Ø41 主体高 146.5 mm、气嘴长 106 mm。两款直插段外径均为 50 mm，配用户实测约 50.2 mm 的三通承口。延长行程依靠增加母丝圈数，不依靠增大螺距。气嘴从 Y 侧旋入，调整时只移动和旋转气嘴，主体、风机与三通固定。

## 同一个预览页面

[局域网装配预览](http://192.168.7.187:8877/fan-nozzle/#fan76-direct) 在原 8877 端口，通过 Tab 切换。旧 `#fan76-tube` 链接会落到当前默认 Ø76 直插方案；不要再使用 8899 独立服务。

- 页面明确显示 CAD 版本、P4、行程；气嘴单选，不叠加四个模型。
- 滑块及运动阶段按每圈 4 mm 同步平移和旋转。可查看完全缩回、中间及完全伸出位置。
- 两个方案共享视角、缩放、全局透明度、爆炸比例、搜索及面板布局；分别记住气嘴和行程。
- 主体默认半透明，内芯使用有深度测试的真实实体，不绘制替代螺旋片；可下载主体与所选气嘴的干净 STL。
- Y 参考件已按商品首图独立重建三端加厚承口/口沿，支管向上并向风机侧后倾，进球顺主气流；不再使用历史简化圆筒参考体。承口按实测 50.2 mm，长度 128 mm / 最大外径 56.38 mm 取自商家 50 规格图、未实测；交汇点及止挡深度为参考，不可据此认定全行程通球安全。见[图像来源及方向契约](y-tee-reference.md)。
- Ø41 风机参考仅显示外表面薄壳，显示厚度不代表风机真实内径或 L 槽。参考件不属于打印清单。

## 生成、发布与验证

可维护页面源码和带 MIT 许可证的固定 Three.js r166 在 `web/fan-nozzle/`；生成清单与来源快照在 `output/fan-nozzle-preview/`；服务部署目录 `output/revision-review/fan-nozzle/` 不入库。不要直接修改部署副本。

```sh
python3 scripts/publish_fan_nozzle_preview.py
node scripts/test_fan_nozzle_preview.mjs http://192.168.7.187:8877/fan-nozzle/
python3 scripts/test_fan_nozzle_print_package.py
python3 scripts/fan_nozzle_preview_lan.py status
```

发布器要求 Python 3、OpenSCAD（默认 macOS 应用路径，可用 `--openscad` 指定），复核 CAD 与导出快照 SHA、OpenSCAD 求值参数、10 个干净 STL 与原生切片审查的对应关系、两份原生工程及两份真实 G-code 包的 SHA。打印件不会重新建模或切片；只生成显示用参考体。STL URL 包含内容哈希，资源先发布、清单后发布；不另开端口，不连接打印机。

预览可离线复建的源模型/工程/固定前端依赖均纳入版本管理。现有共享服务依赖已安装的 `stl-http-preview` 技能；无该环境时可先生成预览，再用普通静态 HTTP 服务查看 `output/fan-nozzle-preview/`。未在全新电脑验证完整工程复跑。

## 打印文件与证据边界

每个交付目录的 `stl/` 下恰好是主体 1 件和气嘴 4 件；保留 `print/slice/*-native-project.3mf` 和 `*-native-actual.gcode.3mf` 以及 `print/native-slice-audit.json`。旧 prepared 拼盘、提取出来的重复预设、重建副本、日志与缓存不入库。

CAD 阶段 `manifest.json`、README 与 SHA256SUMS 是冻结的几何阶段记录；它们早于原生切片，仍可能写着“切片待完成”。后续切片证据以 `print/README.md` / `print/native-slice-audit.json` 为准，机器阶段以有时间戳的 `print/print-status.json` 为准，不能把历史快照当实时状态。

Ø76 最后已确认快照为 2026-10-07 11:10:23 CST 开始第一层；此次预览同步没有查询或操作打印机，也不宣称打印完成。Ø41 已有原生五件切片审查通过，但未发送。两款均未完成本版实物装配及功能验收。

本次回归验证包含：两款清单及全部 HTTP 网格哈希、原始 STL/打印审查一致性、螺旋运动及行程端点、固定主体/Y 框架、无缩放、前端源码/部署副本一致性，以及打印包的 6 项回归测试。三通新增验证：单一封闭连通网格、零退化面/非流形边、三个通口开通、三端承口与口沿、无根部假法兰、支口向上且进球顺主气流。

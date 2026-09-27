# 当前 13 件新增/变化送料件的离线切片绑定

13 个实际实例已按当前 STL 生成 8 盘。全部通过本轮实际 3MF 模型身份、盘内数量、G-code 身份、原生警告/修复、配置和床界核对；12 件通过下列有限孔槽/支撑检查，**入口后夹仍为 pending_review，不进入可采用盘**。未改变 CAD、旧报告或共享预设，未连接打印机或发送打印。

当前源为 `docs/cable-assembly-inventory.json` 与 `output/cable-scene-export/20260927T091627124663Z/report.json`。原生切片及审查文件在 `runs/20260927T094300899015Z/`，所有 STL 和递归源在调用前后保持身份。每个当前 STL 与实际 3MF normal mesh 逐面有向对应，无缺面、新增面或合并面；最大角点转换差约 0.000001912 mm。不是只核对切片退出码。

| 盘 | 数量 | 摆向/支撑 | 本轮有限结果 |
|---|---:|---|---|
| right-support | 1 | X75朝床，树支撑；侧隙0.50、顶隙0.40 | 载体开口6条2×2挑针和2条M3孔芯清理路径明确；Y工作带/新增Y20带无支撑；X54实际面无支撑交叠 |
| left-support | 1 | X−76朝床，树支撑 | 同样核对开口、M3孔芯及Y工作面；实际挑针通道可达支撑 |
| y-cap | 2 | Y39锁母台朝床，树支撑 | 压条/螺母开口朝上且无支撑，4条M3孔芯保持开放 |
| frame-y-gib | 2 | Y27.1共面背脊/耳朝床，无支撑 | 实际没有生成支撑，工作齿无支撑污染 |
| y-keeper | 4 | Y−17.5后背朝床，无支撑 | 每件3条M3有限孔芯与实际模型珠体无交叠，螺母口向上 |
| inlet-rear | 1 | Z−156锚板端面朝床，树支撑 | M4孔/螺母口、M2.5孔、绑带槽有限挑针及中央喉口已核；**完整外树的剪断取出序列尚未闭合** |
| inlet-front | 1 | Z−123端面朝床，无支撑 | M4有限孔芯、中央喉口无支撑；横孔顶桥接仍不等同实物孔径保证 |
| inlet-backplate | 1 | Y−57背面朝床，无支撑 | 两条M2.5有限孔芯保持开放 |

原生均无警告；实际配置 X1C / 0.4 / PETG、0.20层、4墙、25%填充。Generic PETG与Textured PEI是原有分析配置，耗材品牌及PEI纹理并未由用户确认。所有关键路径使用真实3MF变换及G-code层高/线宽，弧弦差上界0.00125 mm，圆周外扩保守余量0.002 mm。判定是有限名义空间，不等同于整孔尺寸、PETG剥离力、工具抓握、残渣、承载或寿命认证。

支座原第一版M3挑针误从Y14开始，越过实际Y16盲孔底；原失败与审查源码保存在 `first-probe-definition/`。补查将入口明确为+Y、止于Y16.1，未改零件或重新切片。两支座正确入口的名义STL和模型珠体均不阻塞，且可触及实际支撑。该修正不解释为打印件存在穿孔缺陷。

`mapping.json` / CSV供统一清单合并；每行显式保留 `needs_reslice` 和 `pending_review`。本轮 `needs_reslice` 全为false，只说明当前切片身份有效；入口后夹 `pending_review=true`，3MF仅是待审候选。映射绑定总报告路径/哈希，总报告绑定逐盘报告/哈希及选定3MF/G-code哈希，避免循环自哈希。

每盘 `layer-path-review.png` 是实际路径图：蓝色模型、橙色支撑。先清外部树枝，再从开口分块取出，后装螺母、压条、外盖、管件与主机。没有要求另印试片，但成品的尺寸、清理和物理动作仍未验证。

复跑（前者会新建时间戳切片；后者只审已有切片）：

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/python output/current-manufacturing/feeder-new/slice.py
/Applications/FreeCAD.app/Contents/Resources/bin/python output/current-manufacturing/feeder-new/review.py
```

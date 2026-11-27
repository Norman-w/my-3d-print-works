# 当前旋转头十件切片复用核对

状态：`TEN_SPIN_SELECTED_SLICES_REUSABLE_DIGITAL_SCOPE_PHYSICAL_OPEN`。10件各1个实例；全部 `needs_reslice=false`，仅表示这次CAD更新没有造成重新切片的需求，不是实物制造放行。

权威当前模型来自 `output/cable-scene-export/20260927T091627124663Z/report.json`，采用板来自 `output/print-review/final-spin/report.json`。脚本只读原源和产物，未调用Bambu/OpenSCAD，未发送打印。

| 实例 | 面数（当前/实际3MF） | 当前→3MF最大数值位移 mm | 材料 | 复用 |
|---|---:|---:|---|---|
| spin/body | 7448/7448 | 3.87033881e-06 | PETG | 是 |
| spin/carriage | 3316/3316 | 2.10190976e-06 | PETG | 是 |
| spin/pad | 44/44 | 2.78668014e-06 | TPU95A HF | 是 |
| spin/pad-keeper | 884/884 | 1.15769375e-06 | PETG | 是 |
| spin/opposite-guide | 648/648 | 5.69410614e-06 | PETG | 是 |
| spin/cover | 6800/6800 | 3.87590177e-06 | PETG | 是 |
| spin/spring-cage | 2192/2192 | 2.47949179e-06 | PETG | 是 |
| spin/spring-seat | 572/572 | 1.84629196e-06 | PETG | 是 |
| spin/pull-cap | 576/576 | 1.90071551e-06 | PETG | 是 |
| spin/hold-fork | 1190/1190 | 3.88758076e-06 | PETG | 是 |

每件均验证：当前STL→原切片STL→实际3MF normal mesh；顶点一一映射、有向三角面多重集合（不接受反向面）及面数一致。序列化差不超过既定1e−5 mm数值界限，当前和旧STL的字节SHA并不相同。四个校核自测确认面顺序变化可接受、反面/缺面/0.01 mm几何变化被拒绝。

实际3MF只含一个normal mesh及一个可打印实例。完整source_offset、component、build和工具偏移均保存在报告，嵌入G-code与独立G-code字节一致。十件原CAD三文件SHA仍相同，材料配置、私有配置身份、原官方模板检查、实际首层M109/M190、真实特征路径数和native警告均核对。每板无native警告，3MF修复字段均0且面数没有静默减少。

PETG九件为0.20 mm、4壁、25% grid、255/70°C；TPU摩擦垫为Bambu TPU95A HF、100% concentric、230/35°C，单独板。选定的是成功的concentric版本，没有引用被拒的rectilinear版本。

## 修正了旧证据的两个限定

弹簧笼、弹簧座和拉帽的3MF build包含额外打印Z排版旋转。组件摆向仍分别为−90°、+90°、−90°绕Y；本报告保留完整build×component。旧支撑脚本只使用component，弹簧笼的旧支撑路径映射因此不完整，未将其原通过结论直接继承。初始诊断报告保存在`initial-review.json`。

共享路径解析器的模型弧线步长为1 mm、角步长≤0.1 rad，保守弓高上界为0.0125 mm。旧支撑通道报告所写0.00125 mm仅适用于其更密的支撑采样。本次用0.0125 mm重新检查实际模型线珠（完整层厚与线宽）的全部已定义通道：主体8、外盖3、弹簧笼3，全部0相交；它们的原STL通道检查则由源网格完整身份继承。没有改旧报告或放宽判据。

所有声明打印层的实际正挤出（含支撑及存在的brim）线珠包络在256×256×250 mm范围内，远离X1C禁区。启动清料路径不在这个模型挤出检查范围内。

## 未扩大的结论

支撑清理仍要在装配前进行，窄工具通道不能证明支撑折断力、全部碎块可自动取出或无残屑。其余七件实际无Support路径，关键孔/燕尾/渐变边缘由全网格对应确认未变；本报告没有补造此前不存在的逐层孔径、沉头贴合或实物通规认证。

Textured PEI仍是分析床型假设（用户只确认PEI）；实物孔径/直线度、夹持、层间强度、TPU摩擦与磨损、床附着、球路/风机/旋转效果均未实物验收。上述边界不要求打印试片，也不影响此次有证据的旧产物复用。

复跑（只读原证据，只更新本目录）：

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/python -B output/current-manufacturing/spin-reuse/review.py
python3 output/current-manufacturing/spin-reuse/write_mapping.py
```

`report.json`保存全部映射和检查，`mapping.json`供根制造清单引用。第二条命令把精简映射绑定到新report SHA；当前映射已绑定本次报告。

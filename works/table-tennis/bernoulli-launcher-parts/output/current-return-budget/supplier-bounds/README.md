# 拉索和弹簧：供应力学数据与正式首机记录

**公开资料仍不能给出当前整链的可靠回位下界。** 已选 Lee Spring LEM063CA 03 M 有初拉力 1.67 N、刚度 0.25 N/mm 的目录名义值；norelem 03096-14-1000 未取得启动阻力、运行阻力或最低传动效率。本目录没有修改主预算、CAD 或采购状态，也没有实际测力数据。

| 已核资料 | 可用范围 / 尚缺项 |
|---|---|
| [Lee 官方目录](https://www.leespring.co.uk/sites/default/files/2020-01/Extension_Springs_Lee_Spring_UK_Eng.pdf)，印刷页 165、177 | 型号、琴钢丝、名义 F0/k/L0 有依据；这几项的组合实物下限未获得。 |
| [Lee 公差说明](https://www.leespring.co.uk/engineering-notes-and-tolerances) | 通用拉伸弹簧段公布刚度 ±10%；DIN2097 例外脚注连接外径表，不能据此断言刚度一定豁免，也不能把 ±10% 当成初拉力允差。该型号的 F0 和自由长允差仍缺，不能构造可信 Fs 最小值。 |
| [norelem 03096-14 官方说明](https://www.norelemusa.com/en-us/Product-Overview/Flexible-standard-component-system/03000/Accessory-for-indexing-plungers-cam-action-indexing-plungers-and-ball-lock-pins/Bowden-cables-for-indexing-plungers-with-remote-actuation/p/agid.32096) | R≥65 mm、安装时也不得过弯、护套仅承压；没有公开数值把弯角换算为 η 或摩擦。 |

上述“缺”只指本轮可访问的指定官方资料；不是声称厂家的所有非公开资料都不存在。检索返回的其他 Lee 型号初拉力允差，以及 norelem 05596-01 的 1000 N 标注，均未移植到所选件。

后续可由同型号、同布线条件的供应接受文件给出所需界限；否则使用正式组件实测。优先直接测整链，不必分别拟合 η/R/D/τ，也不要求额外打印试片。

## 正式首机完成后怎样测

这是一份待总成及五金装配条件完成后的记录办法，**不是要求现在操作未完成总成**。首次在无球、断电无风状态进行，不涉及加压或超压。

1. 固定同一已装总成和持握姿态，保留实际护套路线、夹线和止挡设置。受控拆下回位弹簧；拉力计在原移动弹簧挂点，沿原弹簧挂线向回位方向拉，记录整链的起动峰值和慢速回程曲线，同时拍到滑架与扳机。
2. 用同一根实际弹簧、相同 Ø4 挂针及相同挂点间距，记录回缩过程各位置的弹簧拉力。保持相同空间朝向并校正测量附件自重；不用目录名义值代填读数。
3. 助手把读数/曲线和姿态整理为[配对表](paired-return.csv)。每个已测条件比较“弹簧实测最小力减误差”与“整链实测最大回程力加误差”。重新装好原弹簧，再记录从各已测位置松手后输入、输出是否都回到零位；不给扳机额外助推。

人只需提供原始读数或录像、姿态和当时球/风状态。配置、源 SHA、路线身份和证据文件路径由脚本/助手填写，不需要用户手填 30 列。量程、测点、误差及记录边界见[技术步骤](measurement-protocol.md)。

每行 `margin > 0` 只代表该次、该姿态、该采样范围的准静态余量；少量点不能证明全行程、所有手持朝向、带球带风、寿命或结构强度。整链实测已经包含的重力和摩擦不得再次从余量扣除。主线程的模型质量预算不能冒充实物测量。

[机器字段约定](measurement-schema.json) · [供应证据与缺口](report.json) · [可复跑取证脚本](build.py)。当前 CSV 仅表头，实测记录为 0，实际回位未放行。

复跑本目录报告，不联网、不跑 CAD：

```sh
python3 -B output/current-return-budget/supplier-bounds/build.py
```

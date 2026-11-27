# 满扣止挡：修正后的条件计算

**止挡要让球充分通过，并在输出硬止挡之前停下。当前仍没有可直接照调的刻度。** 新[报告](runs/20260927T163722528406Z/report.json)修正了两处旧计算：通球示例改用分体球道的条件阈值，分面延迟证明补上了名义终点之后的接触区间。没有修改 CAD、重新切片或发送打印。

## 两处修正

1. 旧示例的18.421388 mm来自同轴球心包络。当前[分体球道分析](../current-joint-tolerance/gate-ball-joint-review/README.md)给出 **共同分析相位 u>18.596709041727 mm** 的条件阈值。它要求四挡指在同一相位下满足Bx≤1 mm以及报告列明的有限接触、球径和装配条件；Bx≤1还未证明，分析相位与实物释放零位的关系也未证明。因此它只能更新条件示例，不能填入实际F。
2. 旧分面延迟界只把导数算到名义配置22 mm，实际多边形接触会稍晚。当前局部证明延至22.1 mm，得 **p≤0.013809121 mm**；22+p仍小于22.1，且支持顶点仍在D3螺钉端面内。22.1仅为局部数学证明范围；源码配置上限仍22，整机工作范围仍0～20 mm。

新轴采用后，旧报告不是整体有效的当前证据。当前脚本核对43个未变的球道分析依赖；变化的输入轴、护套路由和场景文件不作为球心包络前提。输入局部止挡另用当前源重新计算。该转用不包含整机碰撞、轴实际偏心、受载变形或制造公差。

## 计算关系

后续[公共相位复核](../current-joint-tolerance/common-phase-registration/README.md)已定义一体输出耳的同零位读数，并给出允许任一侧先触止面的条件映射与有限外包。它没有证明Bx≤1、实际零位可达性或负载下的读数关系，故本页实际F/H仍未填，也不把相位外包另加一次到F。

输出位移都必须从同一实际释放零位算起。设C为名义收线设置，b为名义分面延迟，e为其余止挡误差，ℓ为实际输入收线减实际输出位移，则：

```text
u_out = C + b + e − ℓ，0≤b≤p
C > F + ℓ_max − e_min
C < H + ℓ_min − e_max − p
```

F是该共同装配域的充分放行阈值，H是最早硬止挡位置。输入与输出仍须处于已有0～20 mm检查范围。误差不能重复计入，也不能把未知项设零以取得安装值。相位基准转换尚未闭合时，分析u的阈值不等于实际F。充分箱域为空仅表示这些界不能保证成功，不等于已经找到了真实卡死姿态。

仅在**分析相位恰与实际零位对齐、全部联合条件成立、H=20、失程与其他止挡误差均为零**的示例中：

| 示例量 | mm |
|---|---:|
| 名义设置严格区间 | 18.596709041727～19.986190879 |
| 区间宽度 | 1.389481837273 |
| 示例中点 | 19.291449960364 |
| 中点两侧保守余量 | 各0.694740918636 |

**以上不是安装尺寸。** 真实F/H、失程、止挡误差和相位关系仍未填。槽端正向约束、夹线保持和带载回位也没有被这张表认证。

## 复算入口

使用[新脚本](../../scripts/review_current_stop_contract.py)，依赖本机已有的mpmath区间运算；每次写独立运行目录。旧[review.py](review.py)、[report.json](report.json)和[原说明](runs/20260927T163722528406Z/previous-docs/output/current-stop-contract/README.md)仅保留历史。

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/python scripts/review_current_stop_contract.py
```

外部JSON可用`--bounds`输入`functional_output_upper_mm`、`earliest_hard_stop_mm`、`net_loss_mm`、`other_input_stop_error_mm`；前两项是数值，后两项是两端区间。必须先有同一真实零位与装配域的依据，脚本不为缺值补零，也不认证输入声明。严格零余量、2 mm恒定失程越过当前工作域、缺项、NaN与倒置区间均有拒绝检查。

`actual_joint_domain_certified=false`、`phase_reference_alignment_certified=false`、`physical_setting_authorized=false`、`manufacturing_release=false`、`physical_acceptance=false`。

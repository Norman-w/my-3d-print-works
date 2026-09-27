# 正式 CAD 采用记录

已仅修改 `cad/cable-trigger-input.scad`、`cad/cable-housing-route.scad`、`cad/cable-scene-export.scad`。输入原点改为 `[75,-85,5]`，四孔/背板/安装M4全球坐标原样。采用HCDG8-30名义销、两尾垫、AF12 POM套、AF12.4杠杆孔、两ID10内部推力垫和198侧向路线。没有伪造NETW7安装态实体；`eclip-space`始终是独立工程空间要求，既不计为打印件，也不进入真实五金联合。

## 独立基准与几何等价

`frozen-baseline/` 的正式源由根任务冻结的 `pre-adoption-source.tar.gz` 提取；候选SCAD另复制并逐个对照最新隔离报告的SHA。候选相对路径因此解析到冻结旧CAD，**不会引用采用后的正式CAD**。`baseline.json`记录归档身份、36个候选/依赖SCAD身份和来源。`adopted-source/`保留最终三份源码；`adoption.patch`是采用前→最终差异。

最终 `runs/20260927T152453184055Z/report.json`：21项几何对照通过，14项STL同字节、7项独立STL原生对称差为空。主体双方采用CGAL；其他项目为Manifold。项目包括body、cover、销、尾垫、内部推力垫、轴/环空间、其他固定五金、完整固定五金，以及u=0/10/20的杠杆/端球盖/活动五金/芯线。错位盖的阳性控制检出非空。

首次 `runs/20260927T152335437711Z/report.json`保留为未通过记录：布尔简化使盖/杠杆孔壁的三角划分变化，原生差集非空，未按“体积很小”豁免。最终恢复与冻结候选相同的布尔构造分区（圆构造孔完全被六角孔包含、盖内构造孔完全被D8.3贯孔包含），保留相同实际形状后重新检查；盖与三姿态杠杆成为同字节STL。没有删面、缩小包络或向网格加epsilon。

本对照是**名义设计迁移的几何身份**，不替代同轴以外误差域、实际卡簧变形/装拆、打印公差、载荷、摩擦、回位或整机实物验收。

## 正式接口

原 `ci_body/ci_cover/ci_lever/ci_terminal_cap/ci_fixed_hardware/ci_moving_hardware/ci_cable` 保留。新增：

| 公共模块（全球CAD） | cse selector | 用途 |
|---|---|---|
| `ci_eclip_space()` | `input-eclip-space` | 独立E环安装空间要求，参考层 |
| `ci_axis_space()` | `input-axis-space` | 同轴工程包络，仅诊断 |
| `ci_axis_pin()` | `input-axis-pin` | 目录中点值名义显示，非厂家精确CAD |
| `ci_tail_washers()` | `input-tail-washers` | 两尾垫名义显示 |
| `ci_thrust_washers()` | `input-thrust-washers` | 两内部推力垫 |
| `ci_bush(u)` | `input-bush` | 随扳机转动的六角POM套 |

输入本文件选择器使用去掉`input-`前缀的名称。`ci_local_fixed_axis_hardware()`只含销/尾垫/内部推力垫，`ci_local_other_fixed_hardware(delta)`只含其他局部固定件；`ci_local_fixed_hardware(delta)`合并两者。四全球主机M4仅由公共`ci_fixed_hardware()`加入一次。活动件拆为`ci_local_bush(u)`及`ci_local_other_moving_hardware(u)`，后者只有端球和端球盖五金，不重画杠杆/打印盖。

`ci_spec()`为唯一公共合同；旧重复 `ci_direct_contract()`现在只回显同一合同。删除旧`metal_sleeve_z`、`metal_sleeve_od_id_length`、`replaceable_bush_od_id_length`和有歧义的`total_axial_float`。新键包括：

- `axis_design`、`axis_pin_part`、`axis_clip_part`、`axis_pin_nominal`、`axis_pin_catalog_bounds`。
- `axis_bom_columns=[id,part,quantity,accounting,nominal]`及`axis_bom`五行：销套件1、随附环1（非加和成员）、尾垫2、加工POM1、内部推力垫2。
- `axis_pin_q_domain_nominal_H26=[0,1.54]`、`axis_pin_capture_float_limit_nominal_H26=[.4,1.54]`；`rotor_nominal_axial_float=.5`明确是另一个内腔量。
- `axis_actual_span_acceptance_requirement=[25.7,26.3]`及对应夹持浮量[.1,1.84]仅为设计接受条件；`axis_space_scope`明确本次空间仍只覆盖名义H26/q0..1.54，未把实际跨度预算冒充已验证更大包络。
- `axis_engineering_bounds_not_supplier_guarantees`、`axis_clip_space_role`和两个false安装/工具认证标记。
- `axis_tail_washer_*`、`bush_af_id_length`、`bush_acceptance_requirements`、`bush_socket_*`、`thrust_washer_*`。
- `motion_law=fixed-guide-direct-pull-v2`及全部既有运动/线芯/端口键保留。`cr_contract`新增`nominal_input_run/nominal_side_run/nominal_apex_z`，路线名义侧长198，拒绝旧原点/195侧长。

精确原生输出：`runs/20260927T152453184055Z/scene-contract-precise.echo`。解码文件 `scene-contract-decoded.json` 包含 `scene_contract.ci/co/cr/retention` 和原echo SHA；数值来自原生`cc_pack`的12位小数编码，不用普通6位echo代替。

## 复核命令与采用后范围

在仓库根运行：

```sh
python3 output/cable-eclip-adoption/20260927T151752917841Z/cad-review/verify.py
python3 output/cable-eclip-adoption/20260927T151752917841Z/cad-review/check_contract.py
```

前者生成新21项几何身份/合同提取目录；后者比较冻结候选与正式合同的12组输入数值、5个δ路线，以及旧原点/侧长/越界δ的拒绝。后者最新指针为`contract-latest.json`，不覆盖过去输出。精确合同可单独用OpenSCAD `-D 'cse_part="contract-precise"' -o <new.echo> cad/cable-scene-export.scad`提取。

`adopt.py`与`preserve_native_partition.py`只记录本次编辑过程，**不是对当前正式源可重复运行的更新命令**，避免重复执行破坏状态。本轮不改 scripts/web/docs，不运行全量场景发布、切片或打印。后续统一清单/网页/材料包应从新合同重新绑定；这份CAD采用不能把旧包的来源哈希改写为新结果。

## 最终收尾

`contract-comparison/20260927T152636854068Z/report.json`全部通过：12组输入反解/路径/端点输出完全一致；δ=−2/−1/0/+1/+2五组新旧路线精确编码完全一致；旧原点、195侧长和δ2.01均被原生断言拒绝。没有以普通六位echo比较高精度常数。`route-function-identity.json`另记录全组路线几何函数逐字相同、参数一致与输出源同字节。

最终总证据索引见`report.json`。三份正式CAD、全部等价检查依赖和冻结基准在收尾时再次核对SHA一致。本目录所有结论保持数字设计迁移范围；后续全套检查/发布/制造绑定由根任务独立处理。

#!/usr/bin/env python3
"""Read frozen native outputs and independently audit bounded envelope math."""
from pathlib import Path
import hashlib,json,re,math
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[3];BASE=ROOT/'output/current-axis-through-candidate';RUN=BASE/'runs/20260927T123821871099Z';OUT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
r=json.loads((RUN/'report.json').read_text());assert all(sha(ROOT/p)==h for p,h in r['source_sha256'].items())
for row in r['cases']:
 log=(RUN/(row['case']+'.log')).read_text();assert sha(RUN/(row['case']+'.log'))==row['log_sha256'];assert not re.search(r'(?m)(ERROR|WARNING):',log)
 if row['native_empty']:assert row['returncode']==1 and 'Current top level object is empty.'in log and not (RUN/(row['case']+'.stl')).exists()
 else:assert row['returncode']==0 and sha(RUN/(row['case']+'.stl'))==row['stl_sha256']
v=[tuple(map(float,m))for m in re.findall(r'vertex\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)',(RUN/'plastic-probe.stl').read_text())]
tri=[v[i:i+3]for i in range(0,len(v),3)];counts={'-12':0,'14':0};maxerr=0
for t in tri:
 errors=[max(abs(p[2]-z)for p in t)for z in [-12,14]];which=0 if errors[0]<=errors[1]else 1
 assert errors[which]<1e-10,t
 counts[str([-12,14][which])]+=1;maxerr=max(maxerr,errors[which])
report={
 'status':'BOUNDED_COAXIAL_AXIAL_ENVELOPE_REVIEW_PASS_WITH_EXPLICIT_SCOPE','created_utc':datetime.now(timezone.utc).isoformat(),
 'reviewed_run':str(RUN.relative_to(ROOT)),'reviewed_report_sha256':sha(RUN/'report.json'),'reviewed_source_sha256':r['source_sha256'],'all_sources_and_artifacts_match':True,
 'method':'Read-only source, report and existing ASCII-STL audit; no CAD/export/test rerun, no production changes.',
 'envelope_derivation':{'symbols':'L in [26.98,27.02]; q in [-(L-26)/2, +(L-26)/2]; lo=1-L/2+q, hi=1+L/2+q. Front/back thicknesses may independently lie in [.9,1.1].','lo_bounds':[-13.02,-12],'hi_bounds':[14,15.02],'correct_axis_sweep_bounds':{'tube':[-13.02,15.02],'rear_washer':[-14.12,-12],'front_washer':[14,16.12],'bolt_shank':[-20.1,16.12],'head':[14.9,20.12],'nut':[-17.32,-12.9]},'logic':'Each separate solid is covered by its axial interval. The union drops correlations and may overfill, conservatively. Nominal radial registration only.','nominal_actual_axis':'L27,q0,t1.1 -> tube[-12.5,14.5], rear washer[-13.6,-12.5], front washer[14.5,15.6], head[15.6,19.6], shank[-19.4,15.6], nut[-16.8,-13.6].'},
 'through_bore_source_check':{'body':'Original ci_local_body minus D8.3 over z[-13,15]; fully passes axis body[-12,-4].','cover':'Original ci_local_cover minus D8.3 over z[7,15]; fully passes axis cover[8,14].','old_seats_removed':True,'source_paths_resolve_to_current_production':True},
 'plastic_contacts':{'triangles':len(tri),'per_triangle_single_plane_counts':counts,'maximum_same_plane_z_error':maxerr,'no_triangle_connects_the_two_contact_planes':True,'interpretation':'Actual output is entirely defined end-stop surface contact at z=-12 or14. No skin subtraction.','review_script_gate':'Latest review.py now checks each triangle lies wholly on one specified plane, closing the earlier per-vertex-only classification weakness.'},
 'neighbor_union':{'plastic_probe':['candidate body','candidate cover'],'metal_probe':['ci_local_fixed_hardware(0) minus centered D16.2,z[-25,25] cylinder','two thrust washers explicitly re-added'],'radial_exclusion_check':'The D16.2 subtraction removes old main-axis hardware and OD16 thrust washers. The remaining M3 cheek, M6 adjuster and stop hardware are radially outside that exclusion cylinder.','rotor_probe':['ci_local_lever(0)','ci_local_moving_hardware(0), including bush, ball and terminal fasteners'],'not_directly_in_union':['printed terminal cap','ci_mount_hardware_cad','ci_local_cable','all external feeder/spin/host modules'],'terminal_cap_analytic_check':'Its blank is a radius7 hull of centers [0,54] and [0,66], so minimum radius>=47, unchanged by axial rotation. Entire axis envelope radius<=6. Cuts only remove material. Thus it is separated analytically, but absent from candidate assembly/section rendering.'},
 'rotor_rotation_argument':{'axis_max_radius_in_rotor_z':4,'rotating_bush_bore_inscribed_radius':4.1*math.cos(math.pi/72),'radial_lower_gap':4.1*math.cos(math.pi/72)-4,'rotor_z':[-3.5,7.5],'outer_hardware_z_separated':True,'scope':'Any angular rotation of the coaxial nominal rotor about local z, not eccentricity, bore offset, tilt, altered axial rotor stack, or free cable.'},
 'positive_control':{'case':'actual_axis(25.9,0,1.1)','expected_per_end_intrusion_into_print_mm':.05,'volume_mm3':r['cases'][-1]['mesh']['signed_volume_mm3'],'interpretation':'Real short-sleeve outer-washer overlap detected, not force/strength result.'},
 'scope_verdict':'Only isolated nominal-radial coaxial continuous axial envelope and analytic rotor angular invariance. Not complete input rendering, global service/collision, catalogue approval, manufacturing release or physical acceptance.',
 'production_CAD_modified':False,'manufacturing_release':False,'physical_acceptance':False,'independent_script_sha256':sha(__file__)}
(OUT/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
md=f'''# 贯穿轴隔离候选：独立短审

**在“名义径向同轴、名义打印几何”范围内，连续轴向包络及旋转不变论证成立。** 读取现有源码和产物完成，未增加导出或测试；不能扩写成整机、实际供货或制造通过。

[机器审查](review.json)对应[123821原始报告](../runs/20260927T123821871099Z/report.json)。全部5个源、4个日志、2个非空STL身份一致；两个空交没有残留STL，退出码和原生日志相符。

## 包络与通孔

设`L∈[26.98,27.02]`、`q∈[−(L−26)/2, +(L−26)/2]`，管端`lo=1−L/2+q`、`hi=1+L/2+q`。lo在−13.02..−12，hi在14..15.02。两片垫片各自取0.9..1.1，也被下列范围覆盖：

| 实体 | 连续轴向外包络 |
|---|---|
| 管 | −13.02..15.02 |
| 后 / 前垫片 | −14.12..−12 / 14..16.12 |
| 螺杆 | −20.1..16.12 |
| 头 | 14.9..20.12 |
| 螺母 | −17.32..−12.9 |

[candidate.scad](../candidate.scad)逐项一致。包络丢弃变量相关性，只会更保守。主体Ø8.3切除覆盖z−13..15，盖切除覆盖7..15，确实贯穿原轴端壁。名义L27/q0/t1.1时外垫片为−13.6..−12.5和14.5..15.6，已跟随管端正确外移。

## 产物与旋转论证

塑料交集638片不是原生空。独立逐三角形检查：**{counts['-12']}片在z−12，{counts['14']}片在z14，最大平面误差{maxerr:g}**，没有跨两平面的三角形。最新版脚本也已按每片三个顶点必须位于同一端面收紧判据，之前仅逐顶点归属两平面的不足已关闭。

金属与转件交集均为原生空。25.9短管阳性把两外垫片各侵入打印外面0.05，得到5.891641 mm³真实交叠。

转件共享Z区间内，轴组半径≤4；72边形轴套内孔内切圆半径为`4.1 cos(π/72)={4.1*math.cos(math.pi/72):.9f}`，名义径向下界为{4.1*math.cos(math.pi/72)-4:.9f}。螺钉头、大外垫片和螺母均在转件Z范围以外，故任意同轴角度旋转保持分离。它没有覆盖径向偏心或倾斜耦合。

## 邻件范围

固定金属的Ø16.2排除体只删去原主轴和两片推力垫片，推力垫片已重新加入；它不是完整外部邻件集合。

转件probe未直接加入打印端球盖。由其两个中心半径54/66、外圆半径7可得最小径向距离≥47，远大于整个轴组最大半径6，旋转不改变此界；可解析补足这件局部遗漏。但候选`assembly/section`也没有显示端球盖，不能叫完整输入总成画面。输入四M4×60安装五金、内芯/护套和整机外部邻件均未直接纳入这些probe。

根线程[当前候选说明](../README.md)已明确这些范围及未采用状态。真实轴/孔/垫片偏心与倾斜、打印端面、两侧M3承载、防松、摩擦和蠕变继续开放。当前判定只支持受控浮动轴组的限定几何候选。
'''
(OUT/'README.md').write_text(md)
for link in re.findall(r'\]\(([^)]+)\)',md):assert (OUT/link).resolve().exists(),link
print(json.dumps({'review':str((OUT/'review.json').relative_to(ROOT)),'review_sha256':sha(OUT/'review.json'),'readme_sha256':sha(OUT/'README.md'),'planes':counts,'max_error':maxerr},indent=2))

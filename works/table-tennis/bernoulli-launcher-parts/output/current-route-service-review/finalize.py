#!/usr/bin/env python3
"""Freeze bounded current retainer service findings; no new CAD execution."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[2]
BASE=Path(__file__).resolve().parent
RUN=BASE/'runs/20260927T120853849188Z'
LOCAL=RUN/'contact-localization/20260927T121447873790Z'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rel(p):return str(Path(p).resolve().relative_to(ROOT))
def artifact(p):return {'path':rel(p),'sha256':sha(p)}
a=json.loads((RUN/'report.json').read_text());b=json.loads((LOCAL/'report.json').read_text())
assert b['status']=='CURRENT_RIGID_PATHS_CONDITIONAL_PASS_WRONG_ORDER_DETECTED'
assert all(sha(ROOT/p)==h for p,h in b['source_sha256'].items())
for raw in a['cases']+[a['contract']]+b['native_localizations']:
 for field in ['artifact','log']:
  if raw.get(field):assert sha(ROOT/raw[field])==raw[field+'_sha256']
assert abs(b['native_localizations'][2]['mesh']['components'][0]['volume_mm3']-788.64)<1e-8
report={
 'status':'CURRENT_RELEASED_RIGID_CAP_AND_LOWER_PATHS_CONDITIONALLY_VERIFIED',
 'created_utc':datetime.now(timezone.utc).isoformat(),
 'scope':'Only cap +N50 and lower -Z8 then -Y100 rigid nominal service trajectories, at t=0 and input adjuster delta=0, under listed disassembly/support prerequisites.',
 'native_case_count':7,'contract_echo_count':1,
 'inventory':a['original_source_export_inventory'],
 'source_sha256':b['source_sha256'],
 'finalizer':artifact(__file__),
 'sources_stable_at_freeze':True,
 'raw_four_cases':artifact(RUN/'report.json'),
 'contact_and_positive_localization':artifact(LOCAL/'report.json'),
 'current_path_results':[
  {'case':'cap-current','path':{'direction_from_precise_current_contract':b['known_mating_planes'][0]['plane']['normal_cad'],'distance_mm':50},'current_external_native_result':'EMPTY with no warnings/errors, returncode 1 expected for empty CSG','full_assembly_result':'470 triangles wholly on intended initial local N=0 base/cap mating plane; not an empty native file','max_mating_plane_residual_mm':b['known_mating_planes'][0]['max_intended_plane_residual_mm'],'prerequisites':a['preconditions']['cap-current']},
  {'case':'lower-current','path':[{'cad_translation':[0,0,-8]},{'cad_translation':[0,-100,0]}],'current_external_native_result':'EMPTY with no warnings/errors, returncode 1 expected for empty CSG','full_assembly_result':'8 triangles wholly and exactly on initial Z=84.7 lower/base mating plane; no skin subtraction','prerequisites':a['preconditions']['lower-current']},
  {'case':'lower-baseline','result':'The same 8 planar triangles on Z=84.7; reduced current original-feeder diagnostic only. Not a historic own-removal validation.'}
 ],
 'wrong_order_positive':{**b['wrong_order_exact_pair'],'native_volume_at_60_mm':b['native_localizations'][2]['mesh']['components'][0]['volume_mm3'],'full_current_wrong_sweep_other_components':'Additional actual solid intersections are retained in raw report. Only the output bridge root pair is localized here; 52.5 mm is not claimed as first collision among all neighbors.'},
 'continuous_geometry_argument':{
  'cap':'crr_band_2d is extruded local N=0..5. Groove is a union of convex sphere hulls, all centers in N=0, so removed XY cross-sections shrink monotonically for N>=0. The largest mouth-relief sphere radius is 4 mm, smaller than the 5 mm cap depth. Translating toward +N produces the same initial near-plane cross-section and full material above the groove; the long extrusion minus the original groove therefore covers the continuous sweep. Axial through holes remain parallel to travel.',
  'lower':'crr_lower_sweep(8) fills own screw/nut holes and bounds all first-stage poses. Three filled rectangles at Z70.5..76.7 cover every rearward displacement 0..100. This conservative envelope passed; no claim is based only on sample poses.',
  'contact':'External-only native checks are genuinely empty. The remaining all-neighbor native triangles are on source-defined initial mating planes and movement immediately separates them. No widening clearance or thin-skin subtraction was used.',
  'documentation_correction':'Source comment and initial localization explanatory string say solid above groove 3.1. That is the straight groove radius, not the mouth-relief maximum. Correct sweep argument uses the actual maximum radius 4 mm and cap depth 5 mm. Native geometry and native outcomes are unchanged.'
 },
 'old_evidence':a['old_report'],
 'remaining_digital_scope_not_performed':['Removal of the remaining base, screw withdrawal and tool shafts/handles, arbitrary input/output actuation during maintenance, adjuster delta family, loose hardware trajectories, and flexible line disconnection/deformation are not checked here.','The feeder group is complete by 65 inventory identities; 18 spin and 2 hold items are excluded because their overall mounted world pose is unmeasured/illustrative. Blower and unmeasured Y fitting absent.'],
 'remaining_physical_limits':['External support must carry both base and lower after all four M3x25 screws are removed. No hand reach/grip or load/force proof.','Nominal CAD only; real tolerances, printed surfaces, housing deformation and hardware handling remain unverified.'],
 'manufacturing_release':False,'physical_acceptance':False,'sent_to_printer':False,
}
(BASE/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
readme='''# 当前护套中段导向：限定刚性拆装复核

当前数字检查支持两条已声明的刚性拆装路径：弧盖沿其法向退出 **50 mm**；下托先沿 CAD −Z 下降 **8 mm**，再沿 CAD −Y 后抽 **100 mm**。释放位 `t=0`、输入调节器 `delta=0`，下列拆件与外部承托前提必须同时成立。此结论不是整套导向任意拆装、制造放行或实物验收。

| 对象 | 必须先做 | 当前完整送料/拉索邻件结果 |
|---|---|---|
| 弧盖 | 拆六颗 M3×16 及对应垫片；四颗 M3×25 安装螺钉仍保留；弧盖螺母留在原位置 | 对 57 个刚性外邻件和 4 个名义柔线实例，连续扫掠原生空交。全邻件结果另含 470 个初始 N=0 配合面三角片，最大平面残差 9.52×10⁻¹¹ mm。 |
| 下托 | 先拆弧盖、解除并取开柔线；四颗 M3×25 和上垫片全拆；**基座与下托分别由外部承托**；下托螺母移除或保持在填孔扫掠包络内 | 对 57 个刚性外邻件连续扫掠原生空交。全邻件仅 8 个严格位于 CAD Z=84.7 的初始配合面三角片。 |

四颗安装螺钉全拆后，不存在本次模型证明的自行悬挂保持，不能把“外部承托”省掉。这次假定螺钉已经移除，没有重新证明螺钉工具、拧松次序、握持或柔线实际取出的动作。

## 错误顺序阳性

保持上述下托拆件前提，却直接下降 70 mm，会发生真实干涉。明确定位的一对为 **下托右腿 / 输出固定桥根**：

- 下托右腿初始 Z=78.5..84.7，桥根 Z=18..26；当下降量 `52.5 < d < 66.7 mm` 时，该对有严格实体交叠。
- `d=60 mm` 的原生单姿态交集为 **788.6400000000019 mm³**，边界 X=−49.6..−39、Y=−58..−46、Z=18.5..24.7。
- 整条错误扫掠还与其他邻件有实体交叠，原始结果保留。本区间不是所有邻件的最早碰撞区间。

正确路径下降只到 8 mm，随后在 Z=70.5..76.7 后抽；不能换成长距离直下。

## 证据及边界

[最终机器报告](report.json)保存完整身份、前提和结果。[四 case 原始报告](runs/20260927T120853849188Z/report.json)保留全部 native 交集，不把非空 STL 伪称原生空；[接触归属与阳性定位](runs/20260927T120853849188Z/contact-localization/20260927T121447873790Z/report.json)另有两个真实外邻件空交和一个实体阳性。共 7 个有限目标的原生 CSG 计算，未重跑全局运动。

邻件来自当前正式 [85 项场景清单](../../docs/cable-assembly-inventory.json)中的完整 65 项 feeder 组：57 个外部刚性项、4 个柔线项、4 个导向自有项。自动逐安装项调用并核对源身份；不是根据旧图摆放。旋转头 18 项和保持档 2 项的整机安装位置仍是示意、未实测，未冒充当前导向外邻件；风机和未知斜三通外形也未加入。

旧 [070337 报告](../cable-retention-service/20260927T070337333817Z/report.json)检查的是新增导向对既有服务工具通道的影响，且有 5 个依赖源已变；它原本就把导向自身装拆列为未验证。这里不将其改名或借用为本次路径通过证据。`lower-baseline` 只是当前原始送料模块的减少邻件对照，同样不能冒充历史全装结果。

连续性来自源码扫掠，不来自离散无碰撞：下托采用填满自身孔的保守矩形扫掠；弧盖采用连续法向挤出。源码注释及最初定位报告将 3.1 mm 写作槽上方全实心界限，但口部实际有半径 **4 mm** 的放宽球面。正确论证用 4 mm 小于 5 mm 盖厚，和以 N=0 为中心的槽截面随正 N 单调缩小；native 几何与结果不受该文字修正影响。未删除 0.0001 mm 接触皮层来隐藏干涉。

余下范围包括整基座的后续拆除、实际柔线松解/弯曲、螺钉与工具、手部与外部承托、实物公差及受力。本次冻结状态始终为 `manufacturing_release=false`、`physical_acceptance=false`、`sent_to_printer=false`。
'''
(BASE/'README.md').write_text(readme)
# Check every local markdown reference and every frozen evidence hash.
links=re.findall(r'\]\(([^)]+)\)',readme)
for link in links:assert (BASE/link).resolve().exists(),link
assert all(sha(ROOT/p)==h for p,h in b['source_sha256'].items())
checks={'status':'FROZEN','created_utc':datetime.now(timezone.utc).isoformat(),'report':artifact(BASE/'report.json'),'readme':artifact(BASE/'README.md'),'local_links_checked':len(links),'sources_rechecked':len(b['source_sha256']),'evidence_artifact_and_log_hashes_checked':sum(1 for raw in a['cases']+[a['contract']]+b['native_localizations']for f in ['artifact','log']if raw.get(f))}
(BASE/'freeze.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(checks,indent=2,ensure_ascii=False))

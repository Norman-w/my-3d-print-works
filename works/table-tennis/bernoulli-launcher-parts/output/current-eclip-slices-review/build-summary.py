#!/usr/bin/env python3
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[2];O=ROOT/'output/current-eclip-slices-review'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p):return str(p.relative_to(ROOT))
rows=[]
for stamp,part,role in [('20260927T155733716437Z','cable-input-body','negative-control-original-two-enforcers'),('20260927T155752390241Z','cable-input-body','body-full-backplate-support-candidate'),('20260927T155733716437Z','cable-input-lever','lever-current-slice'),('20260927T155733716437Z','cable-input-cover','negative-control-cover-minus-Z-ring'),('20260927T160923352541Z','cable-input-cover','cover-plus-Z-pocket-support-candidate')]:
 p=O/stamp/part/'report.json';x=json.loads(p.read_text())
 for f,h in x['evidence_sha256'].items():assert sha(ROOT/f)==h,(f,role)
 rows.append({'part':part,'process_role':role,'report':rel(p),'report_sha256':sha(p),'slice_folder':x['slice_folder'],'local_print_growth_sign':x['local_print_growth_sign'],'model_intrusions':sum(e['results']['model']['possible_intrusion_commands']for e in x['envelopes']),'support_intrusions':sum(e['results']['support']['possible_intrusion_commands']for e in x['envelopes']),'holes':[{k:h[k]for k in ['name','minimum_clear_diameter_lower_mm']}for h in x['axis_and_fastener_holes']], 'downward_faces':x['downward_faces'],'thrust_face_material':x['thrust_face_material'],'manufacturing_release':False,'physical_acceptance':False})
result={'status':'BOUNDED_CURRENT_ECLIP_ACTUAL_PATH_REVIEW_COMPLETE','source_sha256':x['source_sha256'],'script':'analysis/cable_eclip_axis_slice_review.py','script_sha256':sha(ROOT/'analysis/cable_eclip_axis_slice_review.py'),'rows':rows,'scope':'Real frozen meshes and actual G-code, 5 process variants for 3 distinct parts. Root owns full artifact and body lateral-channel reviews. No slicing or printing performed by this reviewer.','excluded_success_claims':['physical dimensions and tolerance fit','PETG bridge/surface strength','support cleaning force and damage','actual E-ring installation/removal tooling','full mechanical operation or automatic return'], 'history':['history/first-pass-before-cover-handedness-fix','history/before-cover-plus-growth'],'evidence_stable':True,'manufacturing_release':False,'physical_acceptance':False,'sent_to_printer':False}
(O/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
md=['# 新版 Eclip 输入机构：实际切片路径审查','', '三个新件共五个工艺对照已读完。来源和G-code均以每份artifact-review的SHA锁定；没有改CAD、重新切片或发送打印。所有检查仍是离线路径层级。','', '| 零件/候选 | 模型进入要求金属/线芯包络的命令数 | 关键结果 |','|---|---:|---|']
for r in rows:
 descriptions=[]
 for h in r['holes']:
  if 'axis' in h['name'] or 'root' in h['name']:descriptions.append(h['name']+' 净径下界'+format(h['minimum_clear_diameter_lower_mm'],'.5f')+' mm')
 for d in r['downward_faces']:
  if d.get('area_mm2',0)>4000:descriptions.append('背板支撑投影'+format(d['support_projection_area_on_face_mm2'],'.2f')+'/'+format(d['area_mm2'],'.2f')+' mm²')
 md.append('| '+r['part']+' / '+r['process_role']+' | '+str(r['model_intrusions'])+' | '+'；'.join(descriptions)+' |')
md+=['','- 主体原两enforcer对新增背板底面没有支撑；补全背板后的投影明显改善。原无支撑候选作为失败对照保留，不可凭两M3支撑或native warning为空推整块背板可打印。','- 原盖−Z摆放在2.7→2.8 mm有0.45 mm径向悬边，无支撑。沿圆周缺下承路径19.7168 mm不是桥接跨度；独立近距图和距离界在cover-step目录。+Z摆放消去此环形下表面，改为核验两M3方窝顶的支撑。','- 杠杆使用当前固定导向直拉公式、完整旋转30°AF12 POM六角，而非旧圆形或旧−28.8导向公式。球Ø5和钢芯Ø1.5近端12 mm在u0/10/20/22均对命令线珠留正余量；四点不是连续运动证明。','- 螺母窝/方窝内生成的支撑真实占用装配空间，须在五金装配前从打印床一侧清理。投影覆盖和有入口不等于已经证明支撑可拆净、孔不受伤或底面合格。','- 推力面单列PETG源面与实际路径投影；没有把六角孔内的独立POM件虚构成PETG实体，也没有把0.5 mm转子名义浮动等同于整根销的捕获浮动。','','脚本：`analysis/cable_eclip_axis_slice_review.py`；复跑单件：','','```sh','/Applications/FreeCAD.app/Contents/Resources/bin/python analysis/cable_eclip_axis_slice_review.py --folder output/current-eclip-slices/20260927T160923352541Z/cable-input-cover --output output/current-eclip-slices-review/20260927T160923352541Z/cable-input-cover','```','','自测覆盖当前非线性4姿态、完整六角、零厚承面接触和反向盖法向手性。所有JSON和图像路径及SHA见summary.json及逐件report.json。没有强度、实际清理或首机功能放行。']
(O/'README.md').write_text('\n'.join(md)+'\n');print(json.dumps({'summary':rel(O/'summary.json'),'sha256':sha(O/'summary.json'),'script_sha256':result['script_sha256'],'variants':len(rows)},ensure_ascii=False))

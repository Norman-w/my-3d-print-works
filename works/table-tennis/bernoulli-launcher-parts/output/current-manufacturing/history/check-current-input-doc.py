from pathlib import Path
import re,json,hashlib,math,datetime
ROOT=Path(__file__).resolve().parents[3];DOC=ROOT/'docs/cable-trigger-input.md'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
text=DOC.read_text();backup=ROOT/'output/current-manufacturing/history/cable-trigger-input-pre-direct-pull-v2-20260927T094525771226Z.md'
assert sha(backup)=='f7b91fd1511ad6315da8e6ba3978b4dfda16795f8f4acf8b7d424cd82363b9e2'
links=[]
for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',text):
 if target.startswith(('http:','https:')):continue
 target=target.split('#',1)[0];p=(DOC.parent/target).resolve();assert p.exists(),p;links.append(dict(target=target,file=str(p),exists=True))
source=ROOT/'cad/cable-trigger-input.scad';assert sha(source)=='e243be6b39956ae2ac28bda58c8f3d92bcf4e9a04b28818d8b37d65dea276d07';assert sha(source)in text
p=ROOT/'output/cable-actuation-v2/20260927T091604751038Z/report.json';r=json.loads(p.read_text());i=r['source_contract']['input'];assert r['status']=='IDEAL_DIRECT_PULL_CONTRACT_CHECKS_PASS';assert all(sha(ROOT/n)==h for n,h in r['source_sha256'].items())
assert i['motion_law']=='fixed-guide-direct-pull-v2'and i['origin']==[75.,-82.,5.]
assert i['fairlead_center']==[-24.,0.,2.]and i['fairlead_core_radius']==60 and i['fairlead_surface_radius']==59.25 and i['radius_finger']==36
assert i['metal_sleeve_od_id_length']==[8.,4.3,15.]and i['replaceable_bush_od_id_length']==[12.,8.2,11.]and i['thrust_washer_od_id_t']==[16.,8.4,.25]and i['total_axial_float']==.5
assert i['mount_holes_cad']==[[-16.,-94.,-60.],[-16.,-94.,3.],[16.,-94.,-60.],[16.,-94.,3.]]
assert i['mount_plate_y']==[-94.,-86.]and i['mount_rib_y']==[-86.,-54.]and i['mount_bolt']=='M4x60; replace old M4x20'
assert i['adjuster_delta_range']==[-2.,2.]and i['adjuster_washer_od_id_t']==[12.,6.4,1.6]and i['adjuster_nut_sw_t']==[10.,3.2]and i['adjuster_seat_x']==[-45.,-37.]and i['stop_setting_range']==[16.,22.]
checks=[]
for q in r['rows']:
 theta=math.radians(q['angle_deg']);bx=60*math.sin(theta);by=60*math.cos(theta);d=math.hypot(bx+24,by);phi=max(0,math.atan2(bx+24,by)-math.acos(60/d))
 for delta in [-2,0,2]:
  L=5-delta+60*phi+math.sqrt(d*d-3600);rest=29-delta;err=abs(L-rest-q['output_travel_mm']);assert err<1e-8
  checks.append(dict(u=q['output_travel_mm'],delta=delta,path_formula_error_mm=err))
last=r['rows'][-1];first=r['rows'][0]
assert abs(last['angle_deg']-19.334251925)<.000000001 and abs(last['finger_rearward_mm']-11.918827663)<.000000001
assert abs(last['effective_cable_arm_mm_per_rad']-58.0457)<.00005 and abs(first['finger_force_spring_only_N']-4.958)<.0005 and abs(last['finger_force_spring_only_N']-13.627)<.0005
assert min(3.2-2,3.2+2)==1.2000000000000002
src=source.read_text();assert 'ci_cap_bolts=[[2,54],[2,66]]'in src and 'ci_zbolt(p[0],p[1],4.5,8,3,5.5,3,2.5)'in src and 'ci_web([0,54],[0,66],7,3.1,7.5+sweep)'in src
assembly=ROOT/'output/cable-trigger-system/20260927T091437982269Z/report.json';a=json.loads(assembly.read_text());assert a['status']=='SAMPLED_GEOMETRY_PASS'and len(a['results'])==244;assert all(sha(ROOT/n)==h for n,h in a['source_sha256'].items())
for old in ['19.0986','11.779','01d2b748','14.07','16.210','18.555','17.787']:assert old not in text
m=ROOT/'output/current-manufacturing/input-process/manifest.json';mr=json.loads(m.read_text());assert len(mr['items'])==4
result=dict(status='CURRENT_INPUT_DOCUMENT_LINKS_AND_NUMERICS_PASS',document=str(DOC),document_sha256=sha(DOC),version='2026-09-27 direct-pull-v2-adopted',backup=str(backup),backup_sha256=sha(backup),backup_preserved=True,current_source_sha256=sha(source),local_links=links,numeric_contract_source=str(p),numeric_contract_sha256=sha(p),formula_cases=checks,scope='Read-only source/report arithmetic and local-link verification; no CAD, frozen report, slicer or physical test.',manufacturing_release=False)
out=ROOT/'output/current-manufacturing/history/current-input-doc-review.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':result['status'],'links':len(links),'formula_cases':len(checks),'document_sha256':result['document_sha256'],'report':str(out)},indent=2))

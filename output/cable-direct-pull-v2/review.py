from pathlib import Path
import subprocess,concurrent.futures,hashlib,json,re,datetime,time
B=Path(__file__).resolve().parent
S=B/'candidate.scad';H=hashlib.sha256(S.read_bytes()).hexdigest()
O=B/'runs'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+H[:10]);O.mkdir(parents=True)
SCAD='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
jobs=[]
def add(name,code,backend='Manifold',defines=(),expect='empty'):
 jobs.append((name,code,backend,defines,expect))
add('body','cdp_body();','CGAL',expect='solid')
for name,call in [('lever','cdp_lever(0)'),('terminal-cap','cdp_terminal_cap(0)'),('cover','cdp_cover()')]:add(name,call+';',expect='solid')
for d in [-2,0,2]:
 add(f'contract-d{d}','cdp_direct_contract();',defines=(f'cdp_delta={d}',),expect='echo')
 for u in list(range(21))+[22]:
  defs=(f'cdp_delta={d}',f'cdp_stop_setting={22 if u==22 else 20}')
  # Remove only the TWO identified intentional thrust contact surfaces.
  add(f'motion-u{u}-d{d}',f'intersection(){{union(){{cdp_body();cdp_cover();difference(){{cdp_fixed_hardware({d});cdp_to_cad()for(z=[-3.75,7.5])cdp_zring(0,0,z,.25,16,8.4);}}}}cdp_moving({u});}}',defines=defs)
  # Guide/core contact is assessed separately by exact circle geometry.
  add(f'core-free-u{u}-d{d}',f'intersection(){{union(){{difference(){{cdp_body();cdp_to_cad()cdp_guide_solid();}}cdp_cover();cdp_lever({u});cdp_terminal_cap({u});}}cdp_cable({u},{d});}}',defines=defs)
 add(f'adjuster-print-d{d}',f'intersection(){{union(){{cdp_body();cdp_cover();}}union(){{cdp_adjuster({d});cdp_ferrule({d});}}}}')
 add(f'adjuster-tools-d{d}',f'intersection(){{union(){{cdp_body();cdp_lever(0);cdp_fixed_hardware({d});}}cdp_to_cad()for(i=[0,1])cdp_local_adjuster_tool(i,25);}}')
for u in [0,10,20,22]:
 defs=(f'cdp_stop_setting={22 if u==22 else 20}',)
 add(f'core-contact-u{u}',f'intersection(){{cdp_body();cdp_cable({u},0);}}',defines=defs,expect='analytic-contact')
 add(f'ball-fit-u{u}',f'intersection(){{union(){{cdp_lever({u});cdp_terminal_cap({u});}}cdp_to_cad()translate(cdp_B(cdp_angle({u})))sphere(d=5);}}',defines=defs)
 add(f'cap-hardware-u{u}',f'intersection(){{union(){{cdp_lever({u});cdp_terminal_cap({u});}}cdp_to_cad()rotate([0,0,-cdp_angle({u})])cdp_local_terminal_fasteners();}}',defines=defs,expect='clamping-contact')
 add(f'cap-removal-u{u}',f'intersection(){{union(){{cdp_body();cdp_lever({u});cdp_to_cad()translate(cdp_B(cdp_angle({u})))sphere(d=5);}}cdp_to_cad()rotate([0,0,-cdp_angle({u})])cdp_local_terminal_cap(20);}}',defines=defs,expect='split-plane-contact')
 add(f'cap-bolt-removal-u{u}',f'intersection(){{union(){{cdp_body();cdp_lever({u});cdp_terminal_cap({u});}}cdp_to_cad()rotate([0,0,-cdp_angle({u})])for(p=cdp_cap_bolts){{cdp_zcyl(p[0],p[1],-3.5,8+16,3);cdp_zcyl(p[0],p[1],4.5,3+16,5.5);}}}}',defines=defs,expect='head-seat-contact')
add('terminal-insertion','intersection(){cdp_lever(0);cdp_to_cad()hull(){translate([0,60,2])sphere(d=5);translate([0,60,22])sphere(d=5);}}')
add('cover-removal','intersection(){union(){cdp_body();cdp_lever(0);cdp_terminal_cap(0);cdp_moving_hardware(0);}cdp_to_cad()cdp_local_cover(25);}',expect='post-plane-contact')
add('print-mating','intersection(){cdp_lever(0);cdp_terminal_cap(0);}',expect='split-plane-contact')
add('overtravel-positive','intersection(){cdp_fixed();cdp_moving(22);}',expect='positive-solid')
# Exact union of the exterior sections swept through delta in [-2,2].
# No hull over the whole stepped part: that would invent a taper.
sweep='cdp_to_cad(){cdp_xhex(60,2,-65,14,8);cdp_xcyl(60,2,-55,28,6);cdp_xcyl(60,2,cdp_ferrule_mouth(-2),15,5.5);}'
add('adjuster-continuous-range',f'intersection(){{union(){{cdp_body();cdp_cover();}}{sweep}}}')
for axis in range(3):
 for sign in [-1,1]:
  v=[0,60,2];v[axis]+=4*sign
  add(f'ball-exit-a{axis}-s{sign}',f'intersection(){{union(){{cdp_lever(0);cdp_terminal_cap(0);}}cdp_to_cad()translate({v})sphere(d=5);}}',expect='positive-solid')
def run(job):
 name,code,backend,defs,expect=job;p=O/(name+'.scad');p.write_text(f'include <{S}>\n'+code+'\n')
 out=O/(name+('.csg' if expect=='echo' else '.stl'))
 cmd=[SCAD,'--hardwarnings','--backend',backend]
 if expect!='echo':cmd+=['--export-format','asciistl']
 for d in defs:cmd+=['-D',d]
 cmd+=['-o',str(out),str(p)]
 start=time.monotonic();r=subprocess.run(cmd,capture_output=True,text=True);log=r.stdout+r.stderr;p.with_suffix('.log').write_text(log)
 return dict(name=name,expect=expect,command=cmd,backend=backend,returncode=r.returncode,seconds=time.monotonic()-start,empty='Current top level object is empty.' in log,warnings_or_errors=bool(re.search(r'WARNING:|ERROR:',log)),file=str(out) if out.exists() else None,sha256=hashlib.sha256(out.read_bytes()).hexdigest() if out.exists() else None)
print(str(O),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 results=[]
 for item in pool.map(run,jobs):
  results.append(item)
  if item['expect']=='solid' or item['warnings_or_errors']:print(json.dumps(item),flush=True)
report=dict(source_sha256_before=H,source_sha256_after=hashlib.sha256(S.read_bytes()).hexdigest(),results=results,status='NATIVE_DIAGNOSTIC_REQUIRES_INTERPRETATION',manufacturing_release=False)
(O/'native-report.json').write_text(json.dumps(report,indent=2)+'\n')
(B/'latest-run.json').write_text(json.dumps({'folder':str(O),'report':str(O/'native-report.json'),'source_sha256':H},indent=2)+'\n')
print(json.dumps({'folder':str(O),'checks':len(results),'unexpected_nonempty':[x['name'] for x in results if x['expect']=='empty' and not x['empty']],'warnings':[x['name'] for x in results if x['warnings_or_errors']]}),flush=True)

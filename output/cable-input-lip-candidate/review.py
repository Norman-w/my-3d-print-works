from pathlib import Path
import subprocess,concurrent.futures,hashlib,json,re,time,datetime
BASE=Path(__file__).resolve().parent
S=BASE/'candidate.scad'
SOURCE_HASH=hashlib.sha256(S.read_bytes()).hexdigest()
O=BASE/'runs'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+SOURCE_HASH[:10])
O.mkdir(parents=True)
SCAD='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
jobs={
 'body':'cil_body();','lever':'cil_lever(0);','terminal-cap':'cil_terminal_cap(0);','cover':'cil_cover();',
 'contract':'cil_direct_contract();',
}
for u in list(range(0,21))+[22]:
 jobs[f'motion-{u}']=f'intersection(){{cil_fixed();cil_moving({u});}}'
 if u in [0,10,20]:
  jobs[f'motion-except-thrust-contact-{u}']=f'intersection(){{union(){{cil_body();cil_cover();difference(){{cil_fixed_hardware();cil_to_cad()for(z=[-3.75,7.5])cil_zring(0,0,z,.25,16,8.4);}}}}cil_moving({u});}}'
 jobs[f'core-{u}']=f'intersection(){{union(){{cil_body();cil_lever({u});cil_terminal_cap({u});cil_cover();}}cil_cable({u});}}'
for u in [0,10,20,22]:
 jobs[f'ball-fit-{u}']=f'intersection(){{union(){{cil_lever({u});cil_terminal_cap({u});}}cil_to_cad()translate(cil_B(cil_angle({u})))sphere(d=5);}}'
 jobs[f'cap-hardware-{u}']=f'intersection(){{union(){{cil_lever({u});cil_terminal_cap({u});}}cil_to_cad()rotate([0,0,-cil_angle({u})])cil_local_terminal_fasteners();}}'
jobs['terminal-insertion']='intersection(){cil_lever(0);cil_to_cad()hull(){translate([0,60,2])sphere(d=5);translate([0,60,22])sphere(d=5);}}'
jobs['terminal-cap-removal']='intersection(){union(){cil_lever(0);cil_to_cad()translate([0,60,2])sphere(d=5);}cil_to_cad()cil_local_terminal_cap(20);}'
jobs['cover-removal']='intersection(){union(){cil_body();cil_lever(0);cil_terminal_cap(0);cil_moving_hardware(0);}cil_to_cad()cil_local_cover(25);}'
jobs['print-mating']='intersection(){cil_lever(0);cil_terminal_cap(0);}'
def run(k,code):
 p=O/(k+'.scad');p.write_text(f'include <{S}>\n'+code+'\n')
 out=O/(k+('.csg' if k=='contract' else '.stl'))
 cmd=[SCAD,'--hardwarnings','--backend','Manifold','--export-format','asciistl','-o',str(out),str(p)]
 r=subprocess.run(cmd,capture_output=True,text=True)
 log=r.stdout+r.stderr;(O/(k+'.log')).write_text(log)
 return dict(name=k,command=cmd,returncode=r.returncode,empty='Current top level object is empty.' in log,warnings=bool(re.search(r'WARNING:|ERROR:',log)),file=str(out) if out.exists() else None,sha256=hashlib.sha256(out.read_bytes()).hexdigest() if out.exists() else None)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
 results=list(ex.map(lambda item:run(*item),jobs.items()))
report={'candidate_sha256_at_start':SOURCE_HASH,'candidate_sha256_at_end':hashlib.sha256(S.read_bytes()).hexdigest(),'results':results,'status':'DIAGNOSTIC_NATIVE_REVIEW_REQUIRED','print_release':False}
(O/'native-report.json').write_text(json.dumps(report,indent=2)+'\n')
(BASE/'latest-run.json').write_text(json.dumps({'folder':str(O),'report':str(O/'native-report.json'),'candidate_sha256':SOURCE_HASH},indent=2)+'\n')
print(str(O))
print(json.dumps([{k:r[k] for k in ['name','returncode','empty','warnings']} for r in results if not r['empty']],indent=2))

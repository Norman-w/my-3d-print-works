from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import datetime,hashlib,json,re,subprocess,sys
R=Path(__file__).resolve().parents[4];O=Path(__file__).resolve().parent;B=O/'frozen-baseline';EX='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
rel=lambda p:str(Path(p).relative_to(R))
RUN=O/'runs'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');RUN.mkdir(parents=True)
def closure(p):
 out={};todo=[Path(p)]
 while todo:
  q=todo.pop().resolve()
  if q in out:continue
  out[q]=sha(q);todo.extend(q.parent/n for n in re.findall(r'\b(?:use|include)\s*<([^>]+)>',q.read_text()))
 return out
src=closure(R/'cad/cable-scene-export.scad');src[Path(__file__).resolve()]=sha(__file__)
base=json.loads((O/'baseline.json').read_text());assert all(sha(B/n)==h for n,h in base['source_sha256'].items())
baseline_pre='$fn=72;\n'+''.join('use <'+str(B/n)+'>\n'for n in ['cad/cable-trigger-input.scad','output/current-axis-eclip-candidate/candidate.scad','output/current-axis-offset-candidate/candidate.scad','output/current-axis-retention-review/candidate.scad'])
formal_pre='$fn=72;\nuse <'+str(R/'cad/cable-trigger-input.scad')+'>\n'
cases=[('body','ci_to_cad()ec_body();','ci_body();','CGAL'),('cover','ci_to_cad()ec_cover();','ci_cover();','Manifold'),('pin','ci_to_cad()ec_pin();','ci_axis_pin();','Manifold'),('tail-washers','ci_to_cad()ec_tail_washers();','ci_tail_washers();','Manifold'),('thrust-washers','ci_to_cad()ar_thrust();','ci_thrust_washers();','Manifold'),('axis-space','ci_to_cad()ec_axis_space();','ci_axis_space();','Manifold'),('eclip-space','ci_to_cad()ec_clip_space();','ci_eclip_space();','Manifold'),('other-fixed','ci_to_cad()other_fixed_metal();','ci_to_cad()ci_local_other_fixed_hardware();','Manifold'),('fixed-hardware','ci_to_cad(){ec_pin();ec_tail_washers();ar_thrust();offset_fixed_metal();}','ci_fixed_hardware();','Manifold')]
# other_fixed_metal is imported explicitly; use is not transitive for callers.
baseline_pre+='use <'+str(B/'output/current-axis-through-candidate/candidate.scad')+'>\n'
for u in [0,10,20]:
 cases.extend([(f'lever-u{u}',f'ci_to_cad()ar_lever({u});',f'ci_lever({u});','Manifold'),(f'cap-u{u}',f'ci_terminal_cap({u});',f'ci_terminal_cap({u});','Manifold'),(f'moving-hardware-u{u}',f'ci_to_cad(){{ar_bush({u});ar_other_moving_hardware({u});}}',f'ci_moving_hardware({u});','Manifold'),(f'wire-u{u}',f'ci_cable({u});',f'ci_cable({u});','Manifold')])
def native(scad,target,backend='Manifold',defs=()):
 cmd=[EX,'--hardwarnings','--backend',backend,'--export-format','asciistl']
 for d in defs:cmd+=['-D',d]
 cmd+=['-o',str(target),str(scad)]
 r=subprocess.run(cmd,cwd=R,capture_output=True,text=True);log=r.stdout+r.stderr;target.with_suffix('.log').write_text(log)
 empty='Current top level object is empty.'in log
 return {'command':cmd,'returncode':r.returncode,'log':rel(target.with_suffix('.log')),'native_empty':empty,'valid':not any(x in log for x in ['WARNING:','ERROR:'])and(r.returncode==0 or empty),'file':rel(target)if target.exists()else None,'sha256':sha(target)if target.exists()else None}
def run_case(c):
 name,oldcode,newcode,backend=c;d=RUN/name;d.mkdir()
 old=d/'baseline.scad';new=d/'adopted.scad';old.write_text(baseline_pre+oldcode+'\n');new.write_text(formal_pre+newcode+'\n')
 a=native(old,d/'baseline.stl',backend,['ci_origin=[75,-85,5]']);b=native(new,d/'adopted.stl',backend)
 result={'name':name,'baseline':a,'adopted':b,'comparison':None,'passed':False}
 if a['valid']and b['valid']and a['file']and b['file']:
  if sha(R/a['file'])==sha(R/b['file']):result.update(comparison={'method':'identical-STL-bytes'},passed=True)
  else:
   probe=d/'symmetric-difference.scad';aa=json.dumps(str(R/a['file']));bb=json.dumps(str(R/b['file']));probe.write_text('union(){difference(){import('+aa+');import('+bb+');}difference(){import('+bb+');import('+aa+');}}\n')
   q=native(probe,d/'symmetric-difference.stl');result['comparison']={'method':'native-symmetric-difference-on-exported-STLs','native':q};result['passed']=q['valid']and q['native_empty']
 print(name,result['passed'],flush=True);return result
with ThreadPoolExecutor(max_workers=2)as pool:results=list(pool.map(run_case,cases))
# Precise contract generated directly from the adopted official adapter.
echo=RUN/'scene-contract-precise.echo';cmd=[EX,'--hardwarnings','-D','cse_part="contract-precise"','-o',str(echo),str(R/'cad/cable-scene-export.scad')];p=subprocess.run(cmd,cwd=R,capture_output=True,text=True);log=p.stdout+p.stderr;(RUN/'contract.log').write_text(log)
emitted=echo.read_text()if echo.exists()else'';contract={'command':cmd,'returncode':p.returncode,'echo':rel(echo),'sha256':sha(echo)if echo.exists()else None,'passed':p.returncode==0 and not any(x in log+emitted for x in ['ERROR:','WARNING:'])}
# Positive control keeps source import/operator pipeline honest.
d=RUN/'positive-control';d.mkdir();model=RUN/'cover/adopted.stl';scad=d/'probe.scad';scad.write_text('difference(){import('+json.dumps(str(model))+');translate([10,0,0])import('+json.dumps(str(model))+');}\n');control=native(scad,d/'probe.stl');control['passed']=control['valid']and not control['native_empty']and bool(control['file'])
stable=all(sha(p)==h for p,h in src.items())and all(sha(B/n)==h for n,h in base['source_sha256'].items())
r={'status':'PASS'if all(x['passed']for x in results)and contract['passed']and control['passed']and stable else'REVIEW_REQUIRED','source_sha256':{rel(p):h for p,h in src.items()},'baseline_identity':base,'baseline_directory':rel(B),'cases':results,'contract':contract,'positive_control':control,'sources_stable':stable,'scope':'Frozen old CAD plus frozen candidate SCAD versus adopted public modules; nominal geometry at stated poses. No real E-ring generated; no full manufacturing/physical acceptance.','manufacturing_release':False,'physical_acceptance':False}
(RUN/'report.json').write_text(json.dumps(r,indent=2)+'\n');(O/'latest.json').write_text(json.dumps({'report':rel(RUN/'report.json'),'sha256':sha(RUN/'report.json'),'status':r['status']},indent=2)+'\n');print(json.dumps({'report':rel(RUN/'report.json'),'status':r['status'],'failed':[x['name']for x in results if not x['passed']]},indent=2),flush=True)

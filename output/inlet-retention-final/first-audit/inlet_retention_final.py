#!/usr/bin/env python3
"""Independent inlet candidate geometry checks, never physical clamping proof."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse,hashlib,importlib.util,json,re,subprocess,sys
from feeder_integration import classify
from launcher_final_assembly import exact_area_and_links

ROOT=Path(__file__).resolve().parents[1]
CAD=ROOT/'cad/inlet-retention-final.scad'
OUT=ROOT/'output/inlet-retention-final'
EXE='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
spec=importlib.util.spec_from_file_location('mesh', '/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py')
MESH=importlib.util.module_from_spec(spec);spec.loader.exec_module(MESH)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def sources():
 paths={Path(__file__).resolve(),ROOT/'analysis/feeder_integration.py',ROOT/'analysis/launcher_final_assembly.py'};pending=[CAD]
 while pending:
  p=pending.pop().resolve()
  if p in paths:continue
  paths.add(p);pending.extend(p.parent/d for d in re.findall(r'\b(?:use|include)\s*<([^>]+)>',p.read_text()))
 return {str(p.relative_to(ROOT)):sha(p)for p in sorted(paths)}
def run(name,defs,backend='Manifold',suffix='.stl',extra=()):
 path=OUT/(name+suffix);path.unlink(missing_ok=True)
 cmd=[EXE,'--hardwarnings','--backend',backend]
 if suffix=='.stl':cmd+=['--export-format','asciistl']
 for k,v in defs.items():cmd+=['-D',f'{k}={json.dumps(v)}']
 cmd+=list(extra)+['-o',str(path),str(CAD)]
 p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);log=p.stdout+p.stderr;(OUT/(name+'.log')).write_text(log)
 empty='Current top level object is empty'in log and not path.exists()
 valid=not('WARNING:'in log or'ERROR:'in log)and(p.returncode==0 or empty)
 return path,{'command':cmd,'return_code':p.returncode,'empty':empty,'execution_valid':valid,'log':str((OUT/(name+'.log')).relative_to(ROOT))}
def export(name):
 path,result=run(name,{'ir_part':name},'CGAL')
 if not path.exists():return {'name':name,**result,'passed':False}
 mesh=MESH.inspect(path,1e-6);exact=exact_area_and_links(path);components=len(classify(path)['components'])
 passed=result['execution_valid']and mesh['watertightByEdgeTopology']and components==1 and not exact['exact_zero_area_face_indices']and not exact['non_ring_vertex_links']
 # Actual CGAL Boolean re-import of this exported mesh; no original source shortcut.
 check=OUT/(name+'-reimport.scad');check.write_text('intersection(){import('+json.dumps(path.name)+');cube([10000,10000,10000],center=true);}\n')
 target=OUT/(name+'-reimport.stl');cmd=[EXE,'--hardwarnings','--backend','CGAL','--export-format','asciistl','-o',str(target),str(check)];p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);log=p.stdout+p.stderr;(OUT/(name+'-reimport.log')).write_text(log);readback=p.returncode==0 and target.exists()and'WARNING:'not in log and'ERROR:'not in log
 print('export',name,passed,readback,flush=True)
 return {'name':name,**result,'path':str(path.relative_to(ROOT)),'sha256':sha(path),'mesh':mesh,'exact_area_and_vertex_links':exact,'components':components,'boolean_reimport':{'passed':readback,'command':cmd},'passed':passed and readback}
def probe(job):
 name,defs,expected=job;path,result=run(name,{'ir_part':'probe',**defs})
 geometry=classify(path)if path.exists()else{'components':[],'has_solid_or_unclassified_overlap':False}
 passed=result['execution_valid']and geometry['has_solid_or_unclassified_overlap']==expected
 print('probe',name,passed,flush=True)
 return {'name':name,'definitions':defs,'expected_overlap':expected,**result,**geometry,'passed':passed}
def jobs():
 rows=[]
 for u in [0,1,2]:
  for k in ['neighbors','new_hardware_fit','new_hardware_neighbors','halves','hard_hose','front_remove','clamp_driver']:
   rows.append((f'{k}-u{u}',{'ir_probe':k,'ir_closure':u},False))
 for t in [.5,1]:rows.append((f'neighbors-t{t}',{'ir_probe':'neighbors','ir_t':t},False))
 for k in ['key_insert_bench','backplate_insert_bench','beam_install','anchor_driver','anchor_spanner','m4_nut_insert','m25_nut_insert_bench','strap_feed','ball_path']:
  rows.append((k,{'ir_probe':k},False))
 for k in ['wrong_rear_install_control','m25_nut_hose_control']:rows.append((k,{'ir_probe':k},True))
 for d in [-.5,.5]:rows.append((f'key-end-{d}',{'ir_probe':'key_end_control','ir_fault':d},True))
 rows.append(('soft-pad-overlap-control',{'ir_probe':'soft_overlap','ir_closure':2},True))
 return rows
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--only',nargs='*');parser.add_argument('--skip-images',action='store_true');a=parser.parse_args();OUT.mkdir(parents=True,exist_ok=True);before=sources()
 if a.only is not None:
  selected=[j for j in jobs()if j[0]in a.only]
  with ThreadPoolExecutor(max_workers=2)as pool:rows=list(pool.map(probe,selected))
  dump(OUT/'targeted-checks.json',{'source_sha256':before,'cases':rows});return
 with ThreadPoolExecutor(max_workers=2)as pool:parts=list(pool.map(export,['rear','front','backplate']))
 with ThreadPoolExecutor(max_workers=2)as pool:cases=list(pool.map(probe,jobs()))
 pictures=[]
 if not a.skip_images:
  views=[('assembly',{},'0,-18,-127,66,0,32,400'),('front',{},'0,-15,-126,90,0,0,370'),('top',{},'0,-12,-122,0,0,0,390'),('section',{'ir_part':'section'},'0,-20,-127,68,0,48,380'),('exploded',{'ir_part':'exploded'},'0,-10,-126,62,0,32,470')]
  for name,defs,camera in views:
   p,r=run(name,{'ir_part':'assembly',**defs},suffix='.png',extra=['--render','--imgsize=1500,1150','--projection=o',f'--camera={camera}']);pictures.append({**r,'path':str(p.relative_to(ROOT)),'sha256':sha(p)if p.exists()else None})
 stable=before==sources();passed=stable and all(r['passed']for r in parts+cases)and all(r['execution_valid']for r in pictures)
 report={'status':'NOMINAL_INLET_CANDIDATE_GEOMETRY_PASS_PHYSICAL_OPEN'if passed else'FAILURES_RECORDED','source_sha256':before,'sources_stable':stable,'parts':parts,'cases':cases,'pictures':pictures,
 'independent_inequalities':{'clamp_Z_inside_supported_spigot':[-123,-101],'spigot_Z':[-126,-98],'axial_end_margin_each_mm':3,'slot_vs_key_width_clearance_each_mm':(3-2.6)/2,'slot_vs_key_end_clearance_each_mm':(22-21.2)/2,'key_depth_vs_host_thickness_gap_mm':6-5.8,'nominal_M2_5_thread_projection_mm':20-(3+6+6+1+2),'hard_collar_vs_nominal_OD55_min_Y_radial_gap_at_full_closure_mm':61/2-2-55/2},
 'scope':['Frozen host/beam/assembly are read, never edited. Three new candidate printed components only.','Cylindrical OD55/ID50 hose and 3mm liner are assumed display envelopes, not measured corrugation or material.','Full Y translation uses Minkowski with conservative +/-0.001mm X/Z cover; not a convex hull of concave parts.','Existing mechanism motion checked at t0,.5,1; no whole tolerance/dynamic claim.','M2.5 hardware is an explicitly bounded provisional envelope, commercial SKU not frozen. M4 package follows existing DIN-like reference dimensions.','Nominal pad/hose overlap is an intentional deformation demand, never a predicted pressure or safe compression.','No friction coefficient, clamp torque, PETG strength or anti-pull rating assigned. No print or slice performed.'],
 'physical_acceptance':False,'manufacturing_release':False,'integrated_into_frozen_assembly':False,'sent_to_printer':False}
 dump(OUT/'report.json',report);print(report['status'],flush=True)
 for row in cases:
  if not row['passed']:print('FAILED',row['name'],row.get('components'),flush=True)
 return 0 if passed else 1
if __name__=='__main__':sys.exit(main())

from pathlib import Path
import subprocess,json,hashlib,math,importlib.util
out=Path(__file__).resolve().parent;root=out.parents[2];src=out/'probe.scad';rows=[]
sp=importlib.util.spec_from_file_location('ins','/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py');ins=importlib.util.module_from_spec(sp);sp.loader.exec_module(ins)
for name,mode,u in [('source-parity','source-parity',0),('source-containment','source-containment',0)]+[(f'u{u}','collision',u) for u in range(21)]+[('control','positive-control',0),('target-engagement','target-engagement',0)]:
 dst=out/(name+'.stl')
 if dst.exists():dst.unlink()
 r=subprocess.run(['/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD','--backend=Manifold','-o',str(dst),'-D',f'mode="{mode}"','-D',f'u={u}',str(src)],capture_output=True,text=True);dst.with_suffix('.log').write_text(r.stdout+r.stderr)
 row={'name':name,'mode':mode,'u':u,'exit':r.returncode,'empty':'Current top level object is empty' in r.stderr,'error':'ERROR' in r.stderr}
 if dst.exists():row['mesh']=ins.inspect(dst,1e-6)
 rows.append(row)
 report={'scope':'nominal budget tool continuous +/-15 deg around local X; target locknut intentionally excluded from obstacle set; actual wrench and force not certified','source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'dependencies':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [root/'cad/cable-trigger-input.scad',root/'cad/cable-service-contract.scad']},'axial_expansion_each_side':.001,'angular_step_deg':.5,'nearest_sample_error_deg':.25,'maximum_rotation_radius':math.hypot(45,2.5),'yz_dilation_bound':2*math.hypot(45,2.5)*math.sin(math.radians(.125)),'reconstruction_guard':.001,'offset_radius':(2*math.hypot(45,2.5)*math.sin(math.radians(.125))+.001)/math.cos(math.pi/144),'results':rows}
 (out/'report.json').write_text(json.dumps(report,indent=2))
 print(name,'empty' if row['empty'] else row.get('mesh',{}).get('volume'),flush=True)

from pathlib import Path
import json,re,subprocess,concurrent.futures,hashlib,math
import numpy as np
O=Path(__file__).resolve().parent
R=Path(json.loads((O/'latest-run.json').read_text())['folder'])
S=O/'candidate.scad'
def mesh(path):
 t=np.array(re.findall(rb'vertex\s+([-+eE.0-9]+)\s+([-+eE.0-9]+)\s+([-+eE.0-9]+)',path.read_bytes()),float).reshape(-1,3,3)
 if not len(t):return None
 a=t.reshape(-1,3);q=math.sqrt(.5)
 loc=np.column_stack([q*(-a[:,0]+75+a[:,2]-5),q*(a[:,0]-75+a[:,2]-5),a[:,1]+82])
 radial=np.hypot(loc[:,0]+28.8,loc[:,1])
 return dict(triangles=len(t),signed_volume_mm3=float(np.einsum('ij,ij->i',t[:,0],np.cross(t[:,1],t[:,2])).sum()/6),local_bounds=[loc.min(0).tolist(),loc.max(0).tolist()],guide_radial_interval=[float(radial.min()),float(radial.max())],guide_radius_penetration_bound=max(0,float(59.25-radial.min())))
native=json.loads((R/'native-report.json').read_text())
stats={}
for a in native['results']:
 if not a['empty'] and a['file'] and a['file'].endswith('.stl'):stats[a['name']]=mesh(Path(a['file']))
extra=R/'supplement';extra.mkdir(exist_ok=True)
jobs={}
for u in list(range(13,21))+[22]:
 jobs[f'core-except-analytic-contact-{u}']=f'intersection(){{union(){{difference(){{cil_body();cil_to_cad()cil_guide_solid();}}cil_lever({u});cil_terminal_cap({u});cil_cover();}}cil_cable({u});}}'
for axis in range(3):
 for sign in [-1,1]:
  v=[0,60,2];v[axis]+=sign*4
  jobs[f'ball-exit-axis{axis}-sign{sign}']=f'intersection(){{union(){{cil_lever(0);cil_terminal_cap(0);}}cil_to_cad()translate({v})sphere(d=5);}}'
def run(item):
 k,c=item;p=extra/(k+'.scad');p.write_text(f'include <{S}>\n'+c+'\n');out=extra/(k+'.stl')
 cmd=['/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD','--hardwarnings','--backend','Manifold','--export-format','asciistl','-o',str(out),str(p)]
 r=subprocess.run(cmd,capture_output=True,text=True);log=r.stdout+r.stderr;(extra/(k+'.log')).write_text(log)
 empty='Current top level object is empty.' in log
 return dict(name=k,command=cmd,returncode=r.returncode,empty=empty,warnings=bool(re.search(r'WARNING:|ERROR:',log)),mesh=mesh(out) if out.exists() and not empty else None)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:more=list(pool.map(run,jobs.items()))
report=dict(candidate_sha256=hashlib.sha256(S.read_bytes()).hexdigest(),native_report=str(R/'native-report.json'),mesh_stats=stats,supplement=more,
 guide_contact={'centerline_R':60,'wire_radius':.75,'guide_max_R':59.25,'guide_facet_step_deg':.1,'guide_sagitta_mm':59.25*(1-math.cos(math.radians(.05))),'wire_arc_step_deg_at_most':.05,'wire_inner_surface_chord_sagitta_bound':59.25*(1-math.cos(math.radians(.025))),'interpretation':'The analytic circular core inner boundary and guide have zero-volume intentional contact. The displayed wire torus has inscribed angular chords which can dip inside that radius. This is a local construction bound, not a global collision tolerance; all other printed geometry is checked separately.'},
 status='LIMITED_DIAGNOSTIC_NOT_RELEASED')
(R/'interpretation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({r['name']:{'empty':r['empty'],'warnings':r['warnings']} for r in more},indent=2))
print(R/'interpretation.json')

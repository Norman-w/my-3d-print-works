from pathlib import Path
import hashlib,json,re,subprocess,datetime,concurrent.futures
BASE=Path(__file__).resolve().parent
S=BASE/'candidate.scad'
HASH=hashlib.sha256(S.read_bytes()).hexdigest()
O=BASE/'adjuster-travel'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
O.mkdir(parents=True)
def measure(path):
 p=[tuple(map(float,m)) for m in re.findall(rb'vertex\s+([-+eE.0-9]+)\s+([-+eE.0-9]+)\s+([-+eE.0-9]+)',path.read_bytes())]
 def cross(a,b):return(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
 v=sum(sum(x*y for x,y in zip(p[i],cross(p[i+1],p[i+2]))) for i in range(0,len(p),3))/6
 return dict(triangles=len(p)//3,volume_mm3=v,local_bounds=[[min(v[i] for v in p) for i in range(3)],[max(v[i] for v in p) for i in range(3)]])
def run(dx):
 k=str(dx).replace('.','p');p=O/f'shift-{k}.scad';out=p.with_suffix('.stl')
 p.write_text(f'include <{S}>\nintersection(){{translate([{dx},0,0])cil_local_adjuster();cil_guide_solid();}}\n')
 cmd=['/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD','--hardwarnings','--backend','CGAL','--export-format','asciistl','-o',str(out),str(p)]
 r=subprocess.run(cmd,capture_output=True,text=True);log=r.stdout+r.stderr;p.with_suffix('.log').write_text(log)
 empty='Current top level object is empty.' in log
 return dict(shift_x_mm=dx,metal_tip_x=-29+dx,guide_start_x=-28.8,nominal_axial_gap_mm=.2-dx,command=cmd,returncode=r.returncode,empty=empty,warnings_or_errors=bool(re.search(r'WARNING:|ERROR:',log)),intersection=measure(out) if out.exists() and not empty else None)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,[0,.2,.5,1]))
report=dict(scope='Translate only the existing M6 metal adjuster along local +X against unchanged fixed guide; local coordinates, no source changes.',source=str(S),source_sha256_before=HASH,source_sha256_after=hashlib.sha256(S.read_bytes()).hexdigest(),results=results,assessment='Nominal .2 mm is clearance, not a certified adjustment range. At +.2 the end plane touches the guide; positive overlap above it is a real collision. Input setting must remain a locked datum for the present fixed-Q contract. Rearward travel is not certified by these four checks.',manufacturing_release=False)
(O/'report.json').write_text(json.dumps(report,indent=2)+'\n')
(BASE/'adjuster-travel'/'latest.json').write_text(json.dumps({'folder':str(O),'report':str(O/'report.json')},indent=2)+'\n')
print(json.dumps(report,indent=2))

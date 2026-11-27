from pathlib import Path
import json,subprocess,hashlib
out=Path(__file__).resolve().parent
inv=json.loads((out/'invocation.json').read_text())
cmd=['/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD','--hardwarnings','--backend','CGAL','--export-format','asciistl','-o',str(out/'body-cgal.stl'),str(out/'body.scad')]
inv['command']=cmd
(out/'invocation.json').write_text(json.dumps(inv,indent=2)+'\n')
p=subprocess.run(cmd,capture_output=True,text=True)
(out/'body-cgal.log').write_text(p.stdout+p.stderr)
inv.update(returncode=p.returncode,source_sha256_after=hashlib.sha256(Path(inv['source']).read_bytes()).hexdigest(),reference_sha256_after=hashlib.sha256(Path(inv['reference']).read_bytes()).hexdigest())
inv['source_unchanged']=inv['source_sha256_after']==inv['source_sha256_before']
inv['reference_unchanged']=inv['reference_sha256_after']==inv['reference_sha256_before']
(out/'invocation.json').write_text(json.dumps(inv,indent=2)+'\n')
print(json.dumps({k:inv[k]for k in ['returncode','source_unchanged','reference_unchanged']}))
print(p.stdout+p.stderr)

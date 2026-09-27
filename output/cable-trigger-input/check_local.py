"""Replayable local input-candidate checks, not manufacturing acceptance."""
from pathlib import Path
import collections, hashlib, importlib.util, json, math, subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SRC = ROOT / 'cad/cable-trigger-input.scad'
EXE = '/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
spec = importlib.util.spec_from_file_location('inspect_stl', '/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py')
inspector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inspector)
SOURCE = hashlib.sha256(SRC.read_bytes()).hexdigest()
CHECK = OUT / ('checks-' + SOURCE[:12])
CHECK.mkdir(exist_ok=True)

def run(name, definitions, part=False):
    dest = (OUT if part else CHECK) / (name + '.stl')
    if dest.exists(): dest.unlink()
    command = [EXE, '--backend=Manifold', '-o', str(dest)]
    for value in definitions: command.extend(['-D', value])
    command.append(str(SRC))
    result = subprocess.run(command, capture_output=True, text=True)
    dest.with_suffix('.log').write_text(result.stdout + result.stderr)
    row = dict(name=name, command=command, exit=result.returncode,
               empty='Current top level object is empty' in result.stderr)
    if dest.exists():
        row['mesh'] = inspector.inspect(dest, 1e-6)
        row['artifact_sha256'] = hashlib.sha256(dest.read_bytes()).hexdigest()
    return row, dest

def local(p):
    s = math.sqrt(.5)
    return ((-p[0]+75+p[2]-5)*s, (p[0]-75+p[2]-5)*s, p[1]+82)

def contact_planes(path):
    counts = collections.Counter()
    unknown = 0
    for tri in inspector._read_triangles(path)[1]:
        points = [local(p) for p in tri]
        key = None
        for z in [-12, -9, -5.5, -3.5, 7.5, 8, 9.5, 14]:
            if all(abs(p[2]-z)<1e-7 for p in points): key = f'local Z={z}'; break
        if not key:
            for x in [-45, -37, -32.6, -29]:
                if all(abs(p[0]-x)<1e-7 for p in points): key = f'local X={x}'; break
        if not key and all(abs(-math.sin(math.radians(183))*p[0]+math.cos(math.radians(183))*p[1])<1e-7 for p in points):
            key = 'zero stop radial face'
        if key: counts[key] += 1
        else: unknown += 1
    return dict(triangle_planes=dict(counts), unknown_plane_triangle_count=unknown)

def components(path):
    adjacency = collections.defaultdict(set)
    for tri in inspector._read_triangles(path)[1]:
        v = [tuple(round(a,6) for a in p) for p in tri]
        for a,b in zip(v,v[1:]+v[:1]): adjacency[a].add(b); adjacency[b].add(a)
    left = set(adjacency); sizes=[]
    while left:
        stack=[left.pop()]; count=0
        while stack:
            v=stack.pop(); count+=1
            for nxt in adjacency[v]:
                if nxt in left: left.remove(nxt); stack.append(nxt)
        sizes.append(count)
    return sorted(sizes, reverse=True)

results=[]
for part in ['body','lever','cover','fixed-hardware','moving-hardware','adjuster','ferrule','cable']:
    row, path = run(part, [f'ci_part="{part}"'], part=True)
    if path.exists(): row['vertex_component_sizes']=components(path)
    row['role']='print-candidate' if part in ['body','lever','cover'] else 'hardware-reference'
    results.append(row)
for kind in ['motion','hardware-fit','cable-fit','terminal-entry','printed-fixed','cover-removal','adjuster-washer-fit','adjuster-tool']:
    for u in ([0,5,10,15,20] if kind in ['motion','hardware-fit','cable-fit'] else [0,20]):
        row, path=run(f'{kind}-{u}', ['ci_part="probe"',f'ci_probe_kind="{kind}"',f'ci_u={u}'])
        if path.exists(): row['contact_diagnostic']=contact_planes(path)
        results.append(row)

stops=[]
for setting in [16,20,22]:
    def cx(u): return -4*math.cos(u/60)-26*math.sin(u/60)
    def cy(u): return 4*math.sin(u/60)-26*math.cos(u/60)
    def min_vertex(u): return min((cx(u)+5.5*math.cos(math.radians(i*5)-u/60),cy(u)+5.5*math.sin(math.radians(i*5)-u/60)) for i in range(72))
    tip=cx(setting)-5.5; lo=setting-.1; hi=setting+.1
    for _ in range(60):
        mid=(lo+hi)/2
        if min_vertex(mid)[0]<tip: hi=mid
        else: lo=mid
    actual=(lo+hi)/2; contact=min_vertex(actual)
    stop=dict(setting=setting,tip_x=tip,center_y=cy(setting),first_contact_actual_polyhedron_u=actual,
              contact_local_xy=contact,within_tip_disk=abs(contact[1]+24)<1.5)
    for u in [setting,setting+.02]:
        row,path=run(f'stop-{setting}-u{u}', ['ci_part="probe"','ci_probe_kind="stop-contact"',f'ci_stop_setting={setting}',f'ci_u={u}'])
        stop[str(u)]=dict(empty=row['empty'],volume=(row.get('mesh') or {}).get('volume',0))
    row,path=run(f'stop-tool-{setting}', ['ci_part="probe"','ci_probe_kind="stop-tool"',f'ci_stop_setting={setting}',f'ci_u={setting}'])
    stop['tool_empty']=row['empty']; stops.append(stop)

assert SOURCE == hashlib.sha256(SRC.read_bytes()).hexdigest(), 'Source changed during checks'
report=dict(source_sha256=SOURCE, scope='Local nominal geometry only; no manufacturing, loaded, or whole-system release',results=results)
(OUT/'final-report.json').write_text(json.dumps(report,indent=2))
(OUT/'stop-adjustment-report.json').write_text(json.dumps(dict(source_sha256=SOURCE,results=stops),indent=2))
for row in results:
    print(row['name'], 'empty' if row['empty'] else row.get('mesh',{}).get('volume'), row.get('vertex_component_sizes',''), row.get('contact_diagnostic',''))
print('source',SOURCE)

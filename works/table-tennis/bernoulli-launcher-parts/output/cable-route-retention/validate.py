import ast, collections, concurrent.futures, hashlib, importlib.util, json, math, pathlib, re, subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
SOURCE = ROOT / 'cad/cable-route-retention.scad'
SCAD = '/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
spec = importlib.util.spec_from_file_location('stl_inspect', '/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py')
inspector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inspector)

def run(name, defs, suffix='stl'):
    path = OUT / (name + '.' + suffix)
    if path.exists(): path.unlink()
    command = [SCAD, '--backend=Manifold', '-o', str(path)]
    if suffix == 'stl': command += ['--export-format', 'asciistl']
    for key, value in defs.items(): command += ['-D', key + '=' + json.dumps(value)]
    command += [str(SOURCE)]
    proc = subprocess.run(command, capture_output=True, text=True)
    log = proc.stdout + proc.stderr
    (OUT / (name + '.log')).write_text(log)
    result = {'name': name, 'returncode': proc.returncode, 'empty': 'Current top level object is empty.' in log,
              'warnings': [s for s in log.splitlines() if 'WARNING' in s or 'ERROR' in s]}
    if path.exists() and suffix == 'stl': result['mesh'] = inspector.inspect(path, 1e-6)
    print(name, 'empty' if result['empty'] else result.get('mesh', {}).get('volume', proc.returncode), flush=True)
    return result

jobs = [(n, {'crr_part': n}) for n in ['base', 'cap', 'lower', 'hardware']]
jobs += [('final-' + n, {'crr_part': 'probe', 'crr_test': n}) for n in [
    'host', 'housing', 'parts', 'parts-without-contact-skins', 'output-tools',
    'output-screw-ray', 'spring-continuous', 'cap-removal', 'lower-removal',
    'service-without-contact-skins', 'tools', 'base-installation', 'positive-control']]
# Three poses are local screening only; parent performs the complete integration.
jobs += [('final-host-' + str(t), {'crr_part': 'probe', 'crr_test': 'host', 'crr_t': t}) for t in [.5, 1]]
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    results = list(pool.map(lambda j: run(*j), jobs))

def triangles(path):
    vertices = [tuple(map(float, v)) for v in re.findall(r'\bvertex\s+([-+\deE.]+)\s+([-+\deE.]+)\s+([-+\deE.]+)', path.read_text())]
    return [vertices[i:i+3] for i in range(0, len(vertices), 3)]

def strict(path):
    tris = triangles(path); zero = 0; graph = collections.defaultdict(set)
    for tri in tris:
        a = [tri[1][k]-tri[0][k] for k in range(3)]
        b = [tri[2][k]-tri[0][k] for k in range(3)]
        cross = [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]
        zero += all(v == 0 for v in cross)
        pts = [tuple(round(v, 6) for v in p) for p in tri]
        for i in range(3): graph[pts[i]].add(pts[(i+1)%3]); graph[pts[(i+1)%3]].add(pts[i])
    components = 0; seen = set()
    for p in graph:
        if p in seen: continue
        components += 1; queue = [p]; seen.add(p)
        while queue:
            q = queue.pop()
            for r in graph[q]:
                if r not in seen: seen.add(r); queue.append(r)
    return {'exact_zero_area_triangles': zero, 'connected_components_at_1e-6': components}

for r in results:
    if r['name'] in ['base', 'cap', 'lower']:
        r['strict'] = strict(OUT / (r['name'] + '.stl'))

# Fetch the ACTUAL source frame without OpenSCAD echo's six-significant-digit loss.
# Decimal chunks are <= six integer digits, and reconstruct twelve decimal places.
frame_source = OUT / 'frame-contract.scad'
frame_source.write_text('use <' + str(SOURCE) + '>\nfunction pack(v)=[for(x=v)let(i=floor(x),j=floor((x-i)*1e6))[i,j,round(((x-i)*1e6-j)*1e6)]];\necho("FRAME12",[pack(crr_C()),pack(crr_N())]);\n')
frame_echo = OUT / 'frame-contract.echo'
p = subprocess.run([SCAD, '-o', str(frame_echo), str(frame_source)], capture_output=True, text=True)
raw = frame_echo.read_text().split('"FRAME12", ')[1].strip()
chunks = ast.literal_eval(raw)
C, N = [[i+j*1e-6+k*1e-12 for i,j,k in axis] for axis in chunks]
planes = [('global-Z-' + str(z), [0,0,1], z) for z in [81.3,84.7,99.3]]
planes += [('guide-N-' + str(z), N, sum(C[i]*N[i] for i in range(3))+z) for z in [-4,0,5]]
contact_classification = {}
for name in ['final-parts', 'final-cap-removal', 'final-lower-removal']:
    path = OUT / (name + '.stl')
    if not path.exists(): continue
    maximum = 0; counts = collections.Counter(); worst_triangle = None
    for idx, tri in enumerate(triangles(path)):
        errors = [(max(abs(sum(p[i]*n[i] for i in range(3))-d) for p in tri), label) for label,n,d in planes]
        error, label = min(errors); counts[label] += 1
        if error > maximum: maximum = error; worst_triangle = idx
    contact_classification[name] = {'triangle_count_by_single_plane': counts, 'max_triangle_vertex_distance_to_its_single_plane_mm': maximum,
        'worst_triangle': worst_triangle, 'all_triangles_within_one_known_contact_plane_1e-8mm': maximum <= 1e-8,
        'meaning': 'Every triangle must lie near ONE plane, not one independently chosen plane per vertex. This classifies numeric contact residues; source separation proof is in the document.'}

captures = {}
for axis in 'xyz':
    for sign in [-1,1]:
        path = OUT / ('capture-' + axis + str(sign) + '.stl')
        if path.exists(): captures[axis+str(sign)] = inspector.inspect(path, 1e-6)

report = {'status': 'local_geometry_candidate_not_print_or_strength_release',
          'sources_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [SOURCE, ROOT/'cad/cable-output-interface.scad', ROOT/'cad/cable-trigger-input.scad', ROOT/'cad/cable-housing-route.scad', ROOT/'cad/cable-trigger-system.scad']},
          'results': results, 'capture_positive_controls_translation_mm': .35, 'capture_controls': captures,
          'source_frame_C_N': [C,N], 'raw_contact_classification': contact_classification,
          'scope': 'Local third bend only. Free route and physical installation/strength remain unresolved. Parent separately checks complete service envelopes.'}
(OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print('REPORT', OUT/'report.json', flush=True)

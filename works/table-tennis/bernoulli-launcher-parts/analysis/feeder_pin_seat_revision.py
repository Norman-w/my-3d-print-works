#!/usr/bin/env python3
"""Independent pin V-seat candidate: nominal CSG, no physical preload release."""
from pathlib import Path
import concurrent.futures
import hashlib
import importlib.util
import json
import math
import re
import subprocess
from feeder_integration import classify

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/feeder-pin-seat-revision'
CAD=ROOT/'cad/feeder-pin-seat-revision.scad'
EXE='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
def sources():
    paths={Path(__file__).resolve(),ROOT/'analysis/feeder_integration.py'};todo=[CAD]
    while todo:
        p=todo.pop().resolve()
        if p in paths:continue
        paths.add(p)
        for d in re.findall(r'\b(?:include|use)\s*<([^>]+)>',p.read_text()):todo.append(p.parent/d)
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted(paths)}
def run(name,defs,suffix='.stl',extra=(),backend='Manifold'):
    target=OUT/(name+suffix);target.unlink(missing_ok=True)
    cmd=[EXE,'--hardwarnings','--backend',backend]
    if suffix=='.stl':cmd+=['--export-format','asciistl']
    for k,v in defs.items():cmd+=['-D',f'{k}={json.dumps(v)}']
    cmd+=list(extra)+['-o',str(target),str(CAD)]
    r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);log=r.stdout+r.stderr
    (OUT/(name+'.log')).write_text(log)
    empty='Current top level object is empty'in log
    if 'WARNING:'in log or 'ERROR:'in log or(r.returncode and not(empty and not target.exists())):
        raise RuntimeError(f'{name}: exit {r.returncode}\n{log}')
    if not target.exists()and not empty:raise RuntimeError(f'{name}: missing output\n{log}')
    return target
def vertex_fans(path,tolerance=1e-6):
    """A closed triangle surface needs one connected degree-2 link per vertex."""
    v=[tuple(round(float(x)/tolerance)for x in m.groups())for m in re.finditer(
        r'^\s*vertex\s+([-+\deE.]+)\s+([-+\deE.]+)\s+([-+\deE.]+)',path.read_text(),re.M)]
    links={};degenerate=0
    for i in range(0,len(v),3):
        tri=v[i:i+3]
        if len(set(tri))!=3:degenerate+=1;continue
        for j,a in enumerate(tri):
            b,c=tri[(j+1)%3],tri[(j+2)%3]
            graph=links.setdefault(a,{})
            graph.setdefault(b,[]).append(c);graph.setdefault(c,[]).append(b)
    bad=[]
    for a,graph in links.items():
        todo=set(graph);components=0
        while todo:
            components+=1;stack=[todo.pop()]
            while stack:
                for b in graph[stack.pop()]:
                    if b in todo:todo.remove(b);stack.append(b)
        wrong=sum(len(edges)!=2 for edges in graph.values())
        if components!=1 or wrong:bad.append({'vertex_mm':[x*tolerance for x in a],
            'link_components':components,'non_degree_2_nodes':wrong})
    return {'weld_tolerance_mm':tolerance,'vertices_checked':len(links),
        'degenerate_after_weld':degenerate,'invalid_vertex_links':bad,
        'passed':not bad and not degenerate and bool(links)}
def probe(job):
    name,defs,expected=job;p=run(name,{'ps_part':'probe',**defs})
    info=classify(p)if p.exists()else{'components':[],'has_solid_or_unclassified_overlap':False}
    return {'name':name,'definitions':defs,'expected_overlap':expected,
        'passed':info['has_solid_or_unclassified_overlap']==expected,**info}
def main():
    OUT.mkdir(parents=True,exist_ok=True);before=sources()
    (OUT/'report.json').unlink(missing_ok=True)
    cases=[]
    for t in [0,.2,.4,.5,.6,.8,1]:
        for kind in ['motion','frame','hardware','tools']:
            cases.append((f'{kind}-{t}',{'ps_probe':kind,'ps_t':t},False))
    for kind in ['added-sweep','block-remove','nut-insert','jack-remove','pin-insert','nut-pocket-web']:
        cases.append((kind,{'ps_probe':kind},False))
    for kind in ['root','nut-retained']:
        cases.append((kind,{'ps_probe':kind},True))
    for s in [-1,1]:
        for r in [False,True]:
            for kind in ['block-before-frame','block-retained']:
                cases.append((f'{kind}-{s}-{r}',{'ps_probe':kind,'ps_side':s,'ps_rear':r},True))
    for offset in [-.17,.17]:
        cases.append((f'old-offset-rejected-{offset}',{'ps_probe':'pin-seat-fault','ps_fault':offset},True))
    for dx in [-.5,.3]:
        for kind,expected in [('compensation-clear',False),('compensation-tools',False),('nut-retained-compensation',True)]:
            cases.append((f'{kind}-{dx}',{'ps_probe':kind,'ps_dx':dx},expected))
        for side in [-1,1]:
            for rear in [False,True]:cases.append((f'ear-compensation-{dx}-{side}-{rear}',
                {'ps_probe':'block-retained','ps_dx':dx,'ps_side':side,'ps_rear':rear},True))
    cases.append(('compensation-sweep',{'ps_probe':'compensation-sweep'},False))
    for dx in [-.65,.45]:cases.append((f'compensation-hardstop-{dx}',{'ps_probe':'compensation-clear','ps_dx':dx},True))
    with concurrent.futures.ThreadPoolExecutor(max_workers=3)as pool:rows=list(pool.map(probe,cases))
    spec=importlib.util.spec_from_file_location('mesh','/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py')
    mesh=importlib.util.module_from_spec(spec);spec.loader.exec_module(mesh)
    parts=[]
    for sel,cn in [('carrier','V形肩销座挡指'),('block','肩销可拆压块')]:
        p=run(sel,{'ps_part':sel},backend='CGAL');m=mesh.inspect(p,1e-6);c=classify(p);fans=vertex_fans(p)
        parts.append({'selector':sel,'name':cn,'quantity':4,'path':str(p.relative_to(ROOT)),
            'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'export_backend':'CGAL',
            'mesh':m,'vertex_fans':fans,'components':len(c['components']),
            'passed':m['watertightByEdgeTopology']and len(c['components'])==1 and fans['passed']})
    pictures=[]
    for name,sel,cam in [('local','local','20,2,0,65,0,205,82'),
            ('section','section','20,2,0,55,0,25,82'),
            ('v-section','v_section','20,2.6,0,90,0,180,68'),
            ('front','local','20,2,0,90,0,0,82'),
            ('top','local','20,2,0,0,0,0,82'),
            ('exploded','exploded','20,11,0,65,0,205,115'),
            ('assembly','assembly','0,0,-15,65,0,28,650')]:
        p=run(name,{'ps_part':sel},'.png',['--render','--imgsize=1400,1050','--projection=o',f'--camera={cam}'])
        pictures.append({'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    stable=before==sources();passed=stable and all(r['passed']for r in rows+parts)
    # Analytic contact map, not an assumed manufacturing tolerance.
    contact={'pin_diameter_mm':4,'v_half_angle_deg':45,'v_vertex_x_mm':20-2*math.sqrt(2),
        'nominal_center_xz_mm':[20,0],'contact_lines_xz_mm':[[20-math.sqrt(2),math.sqrt(2)],[20-math.sqrt(2),-math.sqrt(2)]],
        'contact_y_mm':[1.75,4.5],'axial_shoulder_y_mm':1.75,
        'position_equations':'x=vertex_x+sqrt(2)*R+(e_plus+e_minus)/sqrt(2); z=(e_minus-e_plus)/sqrt(2)',
        'inputs_not_measured':['V normal offsets/angles and straightness','actual shoulder diameter/chamfer','block preload/contact deformation','loosening and vibration retention'],
        'zero_offset_assumed_in_error_model':False}
    report={'status':'NOMINAL_PIN_SEAT_CANDIDATE_PASS'if passed else'FAIL_OR_STALE',
        'source_sha256':before,'sources_stable':stable,'case_count':len(rows),'pass_count':sum(r['passed']for r in rows),
        'cases':rows,'parts':parts,'pictures':pictures,'contact_contract':contact,
        'manufacturing_release':False,'complete_error_budget_passed':False,
        'hardware':[{'name':'M2x4 flat-point set screw DIN913/ISO4026; .9mm hex','quantity':4},
                    {'name':'M2 hex nut AF4 H1.6','quantity':4}],
        'limits':['Nominal rigid geometry and stated service order only. No friction/preload/strength or printed fit claim.',
            'Seven complete poses plus convex envelope of the added parts over the full 5mm radial travel. Block service requires carrier removal.',
            'A simple nut provides no independent anti-loosening lock; physical retention remains OPEN.',
            'Existing frozen CAD and root BOM/assembly are not changed.']}
    (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(report['status'],report['pass_count'],'/',len(rows),flush=True)
    for r in rows:
        if not r['passed']:print('FAIL',r['name'],r['components'],flush=True)
    return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())

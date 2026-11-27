#!/usr/bin/env python3
"""Re-run supplier-based spring arithmetic and actual CSG/mesh checks."""
from pathlib import Path
from fractions import Fraction
import argparse, concurrent.futures, hashlib, json, re, subprocess, struct
from spin_head_geometry import inspect_mesh
from feeder_integration import classify

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/feeder-return-spring'
SOURCE=ROOT/'cad/feeder-return-spring.scad'
EXE='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'

def sources(path=SOURCE, found=None):
    found=set() if found is None else found
    if path in found:return found
    found.add(path)
    for name in re.findall(r'(?:include|use)\s*<([^>]+)>',path.read_text()):
        sources((path.parent/name).resolve(),found)
    return found

def hashes():
    paths=sources()|{Path(__file__).resolve(),ROOT/'analysis/spin_head_geometry.py',ROOT/'analysis/feeder_integration.py',OUT/'selection-contract.json',OUT/'supplier-evidence.json'}
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}

def triangles(path):
    data=path.read_bytes();n=struct.unpack_from('<I',data,80)[0]
    if len(data)!=84+50*n:raise ValueError('Expected binary STL')
    return [tuple(tuple(row[j:j+3])for j in (3,6,9))for row in
            (struct.unpack_from('<12f',data,84+50*i)for i in range(n))]

def vertex_fans(path,tol=1e-6):
    links={};degenerate=0
    for triangle in triangles(path):
        tri=[tuple(round(x/tol)for x in p)for p in triangle]
        if len(set(tri))!=3:degenerate+=1;continue
        for j,a in enumerate(tri):
            b,c=tri[(j+1)%3],tri[(j+2)%3];graph=links.setdefault(a,{})
            graph.setdefault(b,[]).append(c);graph.setdefault(c,[]).append(b)
    bad=[]
    for a,graph in links.items():
        pending=set(graph);components=0
        while pending:
            components+=1;stack=[pending.pop()]
            while stack:
                for b in graph[stack.pop()]:
                    if b in pending:pending.remove(b);stack.append(b)
        wrong=sum(len(v)!=2 for v in graph.values())
        if components!=1 or wrong:bad.append({'point_mm':[v*tol for v in a],'components':components,'wrong_degree_nodes':wrong})
    return {'weld_tolerance_mm':tol,'vertices_checked':len(links),'degenerate_after_weld':degenerate,
            'invalid_vertex_links':bad,'passed':bool(links)and not bad and not degenerate}

def exact_cross(triangle):
    a,b,c=[tuple(Fraction(v)for v in p)for p in triangle]
    u=tuple(y-x for x,y in zip(a,b));v=tuple(y-x for x,y in zip(a,c))
    return (u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])

def exact_triangle_area(path):
    """Binary32 coordinates are exact dyadic rationals; do not miss collinearity."""
    bad=[];count=0
    for count, triangle in enumerate(triangles(path),1):
        if not any(exact_cross(triangle)):bad.append({'triangle':count-1,'vertices':triangle})
    return {'method':'Exact rational cross product of binary32 coordinates',
            'triangle_count':count,'zero_area_triangles':bad,'passed':bool(count)and not bad}

def section(path,axis,point):
    i,j=[a for a in range(3)if a!=axis];out=set()
    for a,b,c in triangles(path):
        ui,uj,vi,vj=b[i]-a[i],b[j]-a[j],c[i]-a[i],c[j]-a[j];det=ui*vj-uj*vi
        if abs(det)<1e-10:continue
        di,dj=point[i]-a[i],point[j]-a[j];u,v=(di*vj-dj*vi)/det,(ui*dj-uj*di)/det
        if u>=-1e-7 and v>=-1e-7 and u+v<=1+1e-7:out.add(round(a[axis]+u*(b[axis]-a[axis])+v*(c[axis]-a[axis]),5))
    return sorted(out)

def run(name,part,defs=None,empty=False,backend='Manifold'):
    target=OUT/(name+'.stl');target.unlink(missing_ok=True)
    cmd=[EXE,'--hardwarnings','--backend',backend,'--export-format','asciistl' if part=='probe' else 'binstl','-o',str(target),'-D',f'rs_part="{part}"']
    for k,v in (defs or {}).items():cmd+=['-D',f'{k}={json.dumps(v)}']
    cmd.append(str(SOURCE))
    p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    log=p.stdout+p.stderr;(OUT/(name+'.log')).write_text(log)
    is_empty='Current top level object is empty'in log and not target.exists()
    if (p.returncode and not is_empty) or 'WARNING:'in log or 'ERROR:'in log:raise RuntimeError(name+'\n'+log[-2500:])
    r={'name':name,'part':part,'definitions':defs or {},'expected_empty':empty,'empty':is_empty,'command':cmd}
    if target.exists()and part=='probe':
        r['classification']=classified=classify(target)
        r['artifact_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
        r['planar_contact_only']=not classified['has_solid_or_unclassified_overlap']
        is_empty|=r['planar_contact_only']
    elif target.exists():
        r['mesh']=m=inspect_mesh(target)
        r['vertex_fans']=vertex_fans(target)
        r['exact_triangle_area']=exact_triangle_area(target)
        r['artifact_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
        planar=m['volume_mm3']<1e-6 and all(min(b['size'])<1e-6 for b in m['component_bounds_mm'])
        r['planar_contact_only']=planar
        is_empty|=planar
    r['passed']=is_empty==empty
    return r

def probe(job):
    name,kind,defs,empty=job
    return run(name,'probe',{'rs_probe':kind,**defs},empty)

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--render',action='store_true');args=a.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    before=hashes()
    area_controls={'three_distinct_collinear_points_rejected':not any(exact_cross(((0,0,0),(1,1,1),(2,2,2)))),
                   'nonzero_triangle_retained':any(exact_cross(((0,0,0),(1,0,0),(0,1,0))))}
    assert all(area_controls.values())
    parts=[]
    for p in ('fixed-spacer','moving-spacer','left-support'):
        item=run('return-'+p,p)
        if not(item['mesh']['watertight']and item['vertex_fans']['passed']and item['exact_triangle_area']['passed']):
            rejected=item
            old=OUT/('return-'+p+'.stl');old.rename(OUT/('return-'+p+'-manifold-rejected.stl'))
            item=run('return-'+p,p,backend='CGAL');item['rejected_manifold_export']=rejected
        parts.append(item)
    jobs=[]
    for t in (0,.25,.5,.75,1):
        for kind in ('spring-neighbors','spring-hardware','hardware-fit','spacer-fit','tools','pin-feed'):
            jobs.append((f'{kind}-t{t:g}',kind,{'rs_t':t},True))
        for dy in (-.585,.585):
            for kind in ('spring-neighbors','spring-hardware'):
                jobs.append((f'{kind}-t{t:g}-dy{dy:g}',kind,{'rs_t':t,'rs_spring_dy':dy},True))
    for kind in ('spring-sweep','moving-end-sweep','nut-feed','front-bearing-unchanged'):
        jobs.append((kind,kind,{},True))
    jobs += [('relief-real-material','relief-only',{},False),
             ('control-original-nut-margin','old-nut-margin-control',{},False),
             ('control-too-large-washer','oversize-washer-control',{},False),
             ('control-spring-shift-10','spring-fault',{'rs_fault':10},False)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:tests=list(pool.map(probe,jobs))
    c=json.loads((OUT/'selection-contract.json').read_text())
    s=c['spring'];rows=[]
    # Independent existing-interface arithmetic. Spring inside-eye length is
    # pin-centre distance PLUS pin diameter, not just the centre distance.
    zfixed=-14+(3.4-3)/2-.02
    for u in (0,5,10,15,20):
        L=13+u-zfixed+4;e=L-s['free_inside_loop_length_mm']
        rows.append({'stroke_mm':u,'inside_loop_length_mm':L,'overall_length_mm':L+2*s['wire_diameter_mm'],
                     'extension_mm':e,'catalog_nominal_force_N':s['initial_tension_N']+s['rate_N_per_mm']*e})
    maxe=s['catalog_maximum_extended_length_mm']-2*s['wire_diameter_mm']-s['free_inside_loop_length_mm']
    checks={
        '20mm_full_stroke':abs(rows[-1]['inside_loop_length_mm']-rows[0]['inside_loop_length_mm']-20)<1e-8,
        'all_nominally_in_tension':rows[0]['extension_mm']>0,
        'within_catalog_maximum_overall_length':rows[-1]['overall_length_mm']<s['catalog_maximum_extended_length_mm'],
        'within_catalog_80percent_extension_guidance':rows[-1]['extension_mm']<.8*maxe,
        'nominal_max_force_below_catalog_load':rows[-1]['catalog_nominal_force_N']<s['maximum_load_N'],
    }
    left=OUT/'return-left-support.stl'
    zs=section(left,2,[-72,12.5,0]);ys=section(left,1,[-72,0,-10.6])
    mesh_checks={'top_web_1p2_mm':abs(zs[-1]-zs[-2]-1.2)<1e-4,
                 'front_bearing_4mm_unchanged':abs(ys[-1]-ys[-2]-4)<1e-4}
    # Read actual exported metal geometry at separate shaft and nut rays.
    # Hardware is a multi-part REFERENCE, never a manufacturing mesh.
    metal=run('return-hardware-reference','hardware-reference')
    thread_sections=[]
    for z in (zfixed,13):
        shaft=section(OUT/'return-hardware-reference.stl',1,[-72,0,z])
        nut=section(OUT/'return-hardware-reference.stl',1,[-69.75,0,z])
        thread_sections.append({'z_mm':z,'shaft_axis_intersections_y_mm':shaft,
            'off_axis_nut_intersections_y_mm':nut,'tip_projection_mm':nut[0]-shaft[0]})
    mesh_checks['both_thread_tips_project_2p1_mm_nominally']=all(abs(row['tip_projection_mm']-2.1)<1e-4 for row in thread_sections)
    report={'status':'INDEPENDENT_CANDIDATE_NOT_INSTALLED_IN_IC_FIXED_PHYSICAL_RETURN_OPEN',
        'source_sha256':before,'supplier_selection':c,'parts':parts,'entity_checks':tests,
        'all_expected_checks_match':all(t['passed']for t in tests),
        'parts_watertight_single_component':all(p['mesh']['watertight']and p['mesh']['connected_components']==1 and p['vertex_fans']['passed']and p['exact_triangle_area']['passed']for p in parts),
        'independent_mesh_sections':{'z_at_xminus72_y12p5':zs,'y_at_xminus72_zminus10p6':ys},'mesh_section_checks':mesh_checks,
        'hardware_reference':metal,
        'exact_area_predicate_controls':area_controls,
        'thread_stack':{'formula':'F - effective host thickness - bearing washer - nut thickness',
            'F_mm':9,'host_mm':4,'bearing_washer_mm':.5,'nut_mm':2.4,
            'previous_F7_full_nut_projection_mm':.1,'superseded_F7_thin_nut_projection_mm':.7,
            'current_nominal_projection_mm':2.1,'M3_pitch_mm':.5,
            'combined_adverse_stack_budget_to_one_pitch_mm':1.6,
            'mesh_readback':thread_sections,
            'limits':'Full nut gross axial coverage 2.4mm; chamfers reduce full thread flank length. F/host/washer tolerances and screw thread runout not fully specified. The required inequality is F_actual - host_actual - washer_actual - nut_actual >=0.5mm. External sleeves and M4 hook washers do not change thread projection.'},
        'catalog_force_rows':rows,'calculation_checks':checks,
        'conservative_80percent_extension_limit_mm':.8*maxe,
        'nominal_loop_geometry':{'inner_diameter_mm':5.74,'pin_diameter_mm':4,'hook_center_offset_from_pin_mm':.87,
          'coil_start_distance_from_pin_mm':4.37,'washer_outer_radius_mm':4,'nominal_axial_coil_to_washer_margin_mm':.37,
          'hook_axial_free_gap_mm':1.8-.63,'warning':'Reconstructed full-diameter hook, not certified end geometry/tolerance'},
        'hardware':{'LEM063CA03M_extension_spring':1,'MISUMI_HDMSB4_16_F9_M3':1,'MISUMI_HDMSB4_10_F9_M3':1,
                    'M3_full_nut_AF5p5_h2p4':2,'DIN433_M4_washer_OD8_ID4p3_t0p5':4,'M3_washer_OD7_ID3p2_t0p5':2},
        'print_changes':{'new_spacers':2,'replacement_left_support':1,'existing_frozen_sources_changed':False},
        'scope':['Five discrete 20mm stroke poses for complete geometry','Exact fixed-nut and shoulder-pin linear insertion sweeps',
                 'Conservative full spring and moving-end sweeps against current integrated fixed geometry',
                 'Explicit spring hook envelope; no fabricated factory helix or turns'],
        'open':['Actual force required to overcome mechanism friction and ball load','Hook/crossover dimensions and DIN tolerances',
                'PETG creep/strength and fixed slot bearing; 4mm increased shoulder cantilever','Nut locking, screw runout and catalog tolerances not provided for every stack dimension','Metal dimensional stack and real tool/hand access',
                'Spring dynamic fatigue and return impact','Printing and physical assembly acceptance']}
    if args.render:
        report['views']=[]
        for name,part,t,camera in (
            ('return-rest','local',0,'-125,115,60,-66,22,-5'),
            ('return-full-stroke','local',1,'-125,115,60,-66,22,-5'),
            ('return-front','local',0,'-72,160,0,-72,20,0'),
            ('return-top','local',0,'-72,23,180,-72,23,0'),
            ('return-section','section',0,'160,28,0,-72,28,0'),
            ('return-whole-assembly','assembly',0,'210,-260,160,0,0,-5')):
            p=OUT/(name+'.png')
            cmd=[EXE,'--hardwarnings','--backend','Manifold','--render','--projection','o','--viewall','--imgsize','1400,1100','--camera',camera,'-D',f'rs_part="{part}"','-D',f'rs_t={t}','-o',str(p),str(SOURCE)]
            subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,check=True)
            report['views'].append({'file':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    report['sources_stable_during_run']=hashes()==before
    path=OUT/'feeder-return-spring-report.json';path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    failures=[t['name']for t in tests if not t['passed']]
    print(json.dumps({'report':str(path),'tests':len(tests),'failed':failures,'mesh_ok':report['parts_watertight_single_component'],'mesh_section_checks':mesh_checks,'calculation_checks':checks,'sources_stable':report['sources_stable_during_run']},ensure_ascii=False))
    if failures or not report['parts_watertight_single_component']or not all(checks.values())or not all(mesh_checks.values())or not report['sources_stable_during_run']:raise SystemExit(2)

if __name__=='__main__':main()

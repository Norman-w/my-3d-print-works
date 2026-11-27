#!/usr/bin/env python3
"""Independent Y-guide candidate: actual CSG, export/reimport and scoped contacts.

Does not change frozen CAD, slicer files, or manufacturing/physical state.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse
import hashlib
import json
import re
import subprocess
from feeder_integration import classify
from support_export_fix import mesh

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/feeder-frame-y-guide'
CAD=ROOT/'cad/feeder-frame-y-guide.scad'
REVIEW=ROOT/'cad/feeder-frame-y-guide-review.scad'
EXE='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def sources():
    seen=set()
    def visit(p):
        p=p.resolve()
        if p in seen:return
        seen.add(p)
        for s in re.findall(r'\b(?:include|use)\s*<([^>]+)>',p.read_text()):visit(p.parent/s)
    visit(CAD);visit(REVIEW)
    for p in [Path(__file__),ROOT/'analysis/feeder_integration.py',ROOT/'analysis/support_export_fix.py']:seen.add(p.resolve())
    assert ROOT/'cad/launcher-final-assembly.scad' not in seen,'Harness must not depend on changing root entry'
    return {str(p.relative_to(ROOT)):digest(p)for p in sorted(seen)}


def render(name,defs=None,source=REVIEW,backend='Manifold',suffix='.stl',extra=()):
    target=OUT/(name+suffix);target.unlink(missing_ok=True)
    cmd=[EXE,'--hardwarnings','--backend',backend,'-o',str(target)]
    if suffix=='.stl':cmd+=['--export-format','asciistl']
    for k,v in (defs or {}).items():cmd+=['-D',f'{k}={json.dumps(v)}']
    cmd+=list(extra)+[str(source)]
    p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=240)
    log=p.stdout+p.stderr;(OUT/(name+'.log')).write_text(log)
    empty='Current top level object is empty'in log
    bad=bool(re.search('WARNING:|ERROR:|CGAL error|assertion violation',log))
    ok=not bad and ((p.returncode==0 and target.exists())or(empty and not target.exists()))
    return {'name':name,'definitions':defs,'command':cmd,'returncode':p.returncode,
            'empty':empty,'passed':ok,'file':str(target.relative_to(ROOT))if target.exists()else None,
            'warnings_or_errors':bad}


def known_contacts(r):
    # Only explicit nominal contact planes; never volume cancellation alone.
    # Every component is preserved in report, and every triangle must lie on
    # one of these planes for an otherwise nonplanar zero-thickness union.
    planes=[(1,16),(1,20),(1,24),(1,24.2),(1,31.1),(1,35.5),(1,39),
            (0,53.3),(0,-53.3),(0,58.7),(0,-58.7),(0,58.1),(0,-58.1),
            (0,60.7),(0,-60.7),(2,-33.7),(2,3.7),(2,-18.2),(2,-11.8)]
    if not r.get('file')or not r.get('has_solid_or_unclassified_overlap'):return
    if any(c['volume_mm3']>1e-7 for c in r['components']):return
    raw=(ROOT/r['file']).read_text()
    vv=[tuple(map(float,m))for m in re.findall(r'vertex\s+(\S+)\s+(\S+)\s+(\S+)',raw)]
    residual=[min(max(abs(v[a]-p)for v in vv[i:i+3])for a,p in planes)for i in range(0,len(vv),3)]
    verified=bool(residual)and max(residual)<1e-6
    r['explicit_contact_plane_union']={'verified':verified,'planes':planes,
        'maximum_triangle_residual_mm':max(residual,default=None),'original_components_preserved':True}
    if verified:r['has_solid_or_unclassified_overlap']=False


def probe(job):
    name,defs,solid=job
    r=render(name,{'yg_review_part':'probe',**defs})
    if not r['passed']:return r
    r.update(classify(ROOT/r['file'])if r['file']else{'components':[],'has_solid_or_unclassified_overlap':False})
    if not solid:known_contacts(r)
    r['expected_solid']=solid;r['passed']=r['has_solid_or_unclassified_overlap']==solid
    return r


def jobs():
    result=[]
    for i,t in enumerate([0,.2,.4,.5,.6,.8,1]):
        result.append((f'motion-{i}',{'yg_probe':'motion','yg_t':t},False))
    for dy in [0,.1]:
        for dx in [0,.1]:
            result.append((f'rail-sweep-{dx}-{dy}',{'yg_probe':'rail-sweep','yg_rail_dx':dx,'yg_rail_dy':dy},False))
    for dx in [-.2,.2]:
        for dz in [-.2,.2]:
            result.append((f'gib-float-{dx}-{dz}',{'yg_probe':'gib-fit','yg_gib_dx':dx,'yg_gib_dz':dz},False))
            result.append((f'float-rail-sweep-{dx}-{dz}',{'yg_probe':'rail-sweep','yg_gib_dx':dx,'yg_gib_dz':dz,'yg_rail_dy':.1},False))
    for face in [23.8,24.1,25]:
        result.append((f'compensation-pocket-{face}',{'yg_probe':'gib-fit','yg_face':face},False))
        result.append((f'fasteners-{face}',{'yg_probe':'hardware','yg_face':face},False))
        result.append((f'fastener-pairs-{face}',{'yg_probe':'hardware-pairs','yg_face':face},False))
    for face in [23.8,25]:
        for dx in [-.2,.2]:
            for dz in [-.2,.2]:
                result.append((f'compensation-float-{face}-{dx}-{dz}',
                    {'yg_probe':'gib-fit','yg_face':face,'yg_gib_dx':dx,'yg_gib_dz':dz},False))
    for pitch in [-.15,.15]:
        for kind in ['gib-fit','rail-sweep','hardware','tools']:
            result.append((f'differential-{pitch}-{kind}',{'yg_probe':kind,'yg_pitch':pitch},False))
    for t in [0,1]:
        for kind in ['tools','mount-tools']:
            result.append((f'{kind}-{t}',{'yg_probe':kind,'yg_t':t},False))
        result.append((f'stop-bearing-{t}',{'yg_probe':'fixed-stop-face','yg_t':t},True))
    for side in [-1,1]:
        for kind in ['cap-remove','gib-remove']:
            for distance in [0,.1,1,10,25]:
                result.append((f'{kind}-{side}-{distance}',{'yg_probe':kind,'yg_side':side,'yg_remove':distance},False))
        for kind in ['cap-remove-sweep','gib-remove-sweep']:
            result.append((f'{kind}-{side}',{'yg_probe':kind,'yg_side':side},False))
    result += [('nut-entry',{'yg_probe':'new-nut-feed'},False),
               ('datum-embedded-root',{'yg_probe':'datum-root'},True),
               ('wrong-nut-order-control',{'yg_probe':'wrong-nut-sequence'},True),
               ('wrong-gib-order-control',{'yg_probe':'wrong-gib-sequence'},True),
               ('legacy-lock-height-control',{'yg_probe':'legacy-lock-height-control'},True),
               ('front-overrun-control',{'yg_probe':'gib-fit','yg_face':23.6},True),
               ('back-overrun-control',{'yg_probe':'gib-fit','yg_face':25.3},True),
               ('undersize-setting-with-nominal-rail-control',{'yg_probe':'rail-sweep','yg_face':23.8},True),
               ('negative-Y-play-control',{'yg_probe':'rail-sweep','yg_rail_dy':-.05},True),
               ('positive-Y-play-control',{'yg_probe':'rail-sweep','yg_rail_dy':.15},True)]
    result += [('left-cap-screw-path',{'yg_probe':'left-cap-screw-path'},False),
               ('left-rib-preserved',{'yg_probe':'left-rib-preserved'},False),
               ('left-rib-positive-connection',{'yg_probe':'left-rib-positive-connection'},True),
               ('old-left-cap-path-control',{'yg_probe':'old-left-cap-path-control'},True),
               ('excess-differential-control',{'yg_probe':'rail-sweep','yg_pitch':.5},True)]
    for pitch in [-.15,.15]:
        result.append((f'legacy-flat-tip-contact-control-{pitch}',
            {'yg_probe':'hardware','yg_pitch':pitch,'yg_legacy_jack_center_contact':True},True))
    return result


def part(item):
    name,selector,side,title=item
    r=render(name,{'yg_part':selector,'yg_side':side},CAD,'CGAL')
    r.update(title=title,quantity=1,units='mm',selector={'yg_part':selector,'yg_side':side})
    if not r['passed']or not r['file']:return r
    r['mesh']=mesh(ROOT/r['file']);r['passed']&=r['mesh']['passed']
    wrapper=OUT/(name+'-reimport.scad')
    wrapper.write_text(f'intersection(){{import("{name}.stl");cube([1000,1000,1000],center=true);}}\n')
    check=render(name+'-reimport',source=wrapper,backend='CGAL')
    r['CGAL_boolean_reimport']=check
    r['passed']&=check['passed']and bool(check['file'])
    if check['file']:
        r['reimport_mesh']=mesh(ROOT/check['file'])
        r['passed']&=r['reimport_mesh']['passed']
    return r


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--checks-only',action='store_true');ap.add_argument('--parts-only',action='store_true')
    ap.add_argument('--refresh-root-and-flat-tip',action='store_true',
        help='Refresh the documented datum-root and inclined-flat-tip changes; retain unchanged checks with provenance.')
    ap.add_argument('--refresh-pictures',action='store_true',help='Refresh camera-only PNGs, retaining verified geometry results and their source identity.')
    args=ap.parse_args();OUT.mkdir(parents=True,exist_ok=True);before=sources()
    parts=[];cases=[];pictures=[];prior=None;reused=[]
    if args.refresh_pictures:
        prior_path=OUT/'before-camera-refresh/report.json'
        prior=json.loads(prior_path.read_text())
        changed={p for p,h in prior['source_sha256'].items()if before.get(p)!=h}
        assert changed<={'analysis/feeder_frame_y_guide.py'},changed
        assert prior['status']=='INDEPENDENT_FRAME_Y_GUIDE_DIGITAL_PASS'
        parts=prior['parts'];cases=prior['cases'];reused=[c['name']for c in cases]
    elif args.refresh_root_and_flat_tip:
        prior_path=OUT/'before-deeper-datum-and-flat-tip/report.json'
        prior=json.loads(prior_path.read_text())
        changed={p for p,h in prior['source_sha256'].items()if before.get(p)!=h}
        assert changed<={'cad/feeder-frame-y-guide.scad','analysis/feeder_frame_y_guide.py'},changed
        # Exact edit scope: support datum depth and the tilted jack end offset.
        # Cap/gib printed geometry and their dimensions are unchanged.
        assert all(p['passed']for p in prior['parts'])
    if not args.checks_only and not args.refresh_pictures:
        specs=[('right-support','right-support',1,'右支座含公共架Y基准'),
               ('left-support','left-support',-1,'左弹簧支座含公共架Y基准'),
               ('right-cap','cap',1,'右公共架Y调隙盖'),('left-cap','cap',-1,'左公共架Y调隙盖'),
               ('right-gib','gib',1,'右公共架Y压条'),('left-gib','gib',-1,'左公共架Y压条')]
        if prior:
            parts=[{**p,'reused_unchanged_geometry':True,'prior_report_sha256':digest(prior_path)}
                   for p in prior['parts']if p['name']not in ['right-support','left-support']]
            specs=specs[:2]
        with ThreadPoolExecutor(max_workers=2)as pool:parts+=list(pool.map(part,specs))
    if not args.parts_only and not args.refresh_pictures:
        tasks=jobs()
        if prior:
            old={c['name']:c for c in prior['cases']}
            affected=lambda n:(n.startswith(('motion-','rail-sweep-','float-rail-sweep-',
                'differential-','fasteners-','stop-bearing-','legacy-flat-tip-'))or n in
                ['datum-embedded-root','undersize-setting-with-nominal-rail-control',
                 'negative-Y-play-control','positive-Y-play-control','excess-differential-control',
                 'left-cap-screw-path','left-rib-preserved','left-rib-positive-connection'])
            for job in tasks:
                n=job[0]
                if not affected(n):
                    assert n in old and old[n]['passed'],n
                    cases.append({**old[n],'reused_unaffected_check':True,
                        'prior_report_sha256':digest(prior_path)})
                    reused.append(n)
            tasks=[j for j in tasks if affected(j[0])]
        with ThreadPoolExecutor(max_workers=2)as pool:
            for row in pool.map(probe,tasks):
                cases.append(row)
                if not row['passed']:print('FAILED',row['name'],flush=True)
    if not args.checks_only:
        views=[
            ('assembly',{},'0,0,-12,65,0,32,950'),
            ('section',{'yg_review_part':'section'},'61,29,-30.5,0,0,0,160'),
            ('cap-front',{'yg_part':'cap'},'59,29,-15,90,0,0,130'),
            ('cap-top',{'yg_part':'cap'},'59,31,-15,270,0,0,140'),
            ('cap-iso',{'yg_part':'cap'},'59,29,-15,65,0,35,145')]
        if prior and not args.refresh_pictures:
            pictures=[{**p,'reused_unchanged_geometry':True,'prior_report_sha256':digest(prior_path)}
                for p in prior['pictures']if p['name'].startswith('cap-')]
            views=views[:2]
        for name,definitions,camera in views:
            pictures.append(render(name,definitions,CAD if 'yg_part'in definitions else REVIEW,
                suffix='.png',extra=['--render','--imgsize=1400,1050',f'--camera={camera}']))
    stable=before==sources()
    passed=stable and all(p['passed']for p in parts+cases+pictures)
    report={'status':'INDEPENDENT_FRAME_Y_GUIDE_DIGITAL_PASS'if passed else'FAIL_OR_STALE',
        'source_sha256':before,'sources_stable':stable,'parts':parts,'cases':cases,'pictures':pictures,
        'case_count':len(cases),'pass_count':sum(c['passed']for c in cases),
        'refreshed_case_count':len(cases)-len(reused),'reused_unaffected_cases':reused,
        'refresh_scope':None if not prior else{'prior_report_sha256':digest(prior_path),
            'changed_dependencies':sorted(changed),
            'reason':('Camera-only refresh. Geometry dependencies match the prior 91/91 report; all geometry results retained.' if args.refresh_pictures else 'Only lower datum depth and inclined flat-tip contact formula changed. Two support meshes and affected root/motion/hardware checks refreshed; unchanged cap/gib geometry and unaffected checks retain explicit prior provenance.')},
        'source_scope':'Pure geometry library plus explicit old33 harness; no dependency on root launcher-final entry.',
        'contact_contract':{'rail_Y_mm':[20,24],'fixed_lower_datum_Y_mm':20,'shown_gib_Y_mm':24.1,
            'work_face_Y_mm':[23.8,25],'mechanical_limit_Y_mm':[23.7,25.2],
            'old_parallel_Y_mm':[-.2,.2],'shown_parallel_Y_mm':[0,.1],
            'bearing_bands_Z_mm':[[-33.5,-27.5],[-2.5,3.5]],'unchanged_fixed_stop_Z_mm':[-35,5],
            'gib_XZ_float_each_mm':.2,'minimum_gib_to_fixed_stop_Z_mm':1.3,
            'bounded_differential_pitch_demonstration_deg':[-.15,.15]},
        'hardware_delta':{'replace_old_M3x12_cap_bolts':4,'new_M3x20_cap_bolts':4,
            'additional_M3x16_jacks':4,'additional_M3_nuts':8,'additional_M3_washers':4,
            'reuse_old_mount_nuts_and_washers':4,'net_added_printed_instances':2},
        'limits':['Nominal geometry, not measured FDM adjustment or strength.',
            'Straight tool envelope is declared, not a purchased tool model.',
            'Both jack settings must be adjusted alternately; independent differential settings are not a global loaded error proof.',
            'Full-stroke rail sweep is exact for the selected axis-aligned translation; total 3D tolerance remains separate.',
            'No print/coupon/order sent; root assembly and existing slice package remain untouched.'],
        'manufacturing_release':False,'physical_acceptance':False}
    path=OUT/('checks-report.json'if args.checks_only else'parts-report.json'if args.parts_only else'report.json')
    path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(report['status'],len(cases),report['pass_count'],flush=True)
    return 0 if passed else 1


if __name__=='__main__':raise SystemExit(main())

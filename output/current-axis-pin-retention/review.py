#!/usr/bin/env python3
"""Conditional replacement-pin geometry; does not release manufacture."""
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
import importlib.util, hashlib, json, re

OUT=Path(__file__).resolve().parent; ROOT=OUT.parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
rel=lambda p:str(Path(p).relative_to(ROOT))
helperfile=ROOT/'output/current-axis-offset-candidate/host-review/review.py'
spec=importlib.util.spec_from_file_location('previous_host',helperfile)
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
SNAP=ROOT/'output/cable-scene-export/20260927T091627124663Z/report.json'

def main():
    folder=OUT/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder.mkdir(parents=True)
    snapshot=json.loads(SNAP.read_text())
    sources={rel(SNAP):sha(SNAP),rel(Path(__file__)):sha(__file__),rel(helperfile):sha(helperfile)}
    pending=[OUT/'candidate.scad',ROOT/'output/current-axis-offset-candidate/route/candidate.scad']
    while pending:
        p=pending.pop().resolve();n=rel(p)
        if n in sources:continue
        sources[n]=sha(p)
        pending.extend(p.parent/s for s in re.findall(r'\b(?:use|include)\s*<([^>]+)>',p.read_text()))
    for p in ['supplier/report.json','supplier/evidence/ampg-transmission.pdf']:
        sources[rel(OUT/p)]=sha(OUT/p)
    for p,v in snapshot['source_sha256'].items():
        if p.startswith('cad/'):
            assert sha(ROOT/p)==v,p
            sources[p]=v
    for row in snapshot['parts']:assert sha(ROOT/row['file'])==row['sha256'],row['id']
    pre='$fn=72;\nuse <'+str(ROOT/'cad/cable-trigger-input.scad')+'>\nuse <'+str(OUT/'candidate.scad')+'>\n'
    def probe(item):
        name,code=item
        r=helper.run(pre+code,name,folder)
        if not r['native_empty']:
            _,raw=helper.mesh(ROOT/r['file'])
            r['only_capture_planes']=all(any(all(Fraction(v[2])==z for v in raw[i:i+3]) for z in [-12,14]) for i in range(0,len(raw),3))
            if name=='short-pin-forced-washer-control':
                r['raw_geometry']=helper.classify(ROOT/r['file'])
        print(name,'empty' if r['native_empty'] else 'nonempty',flush=True)
        return r
    jobs=[]
    for env in ['axis','cotter']:
        for target,code in [('plastic','pin_plastics()'),('metal','offset_fixed_metal()')]:
            # The old offset module is explicitly imported for fixed hardware.
            extra='use <'+str(ROOT/'output/current-axis-offset-candidate/candidate.scad')+'>\n'
            jobs.append((env+'-'+target,extra+'intersection(){pin_'+env+'_envelope();'+code+';}\n'))
        for u in [0,10,20]:
            extra='use <'+str(ROOT/'output/current-axis-retention-review/candidate.scad')+'>\n'
            jobs.append((env+'-rotor-'+str(u),extra+'intersection(){pin_'+env+'_envelope();ar_rotor('+str(u)+');}\n'))
    jobs.append(('short-pin-forced-washer-control','intersection(){pin_ring(14-25-2.25/2+1.75/2,3.2,15,8.4);pin_plastics();}\n'))
    with ThreadPoolExecutor(max_workers=2) as pool:local=list(pool.map(probe,jobs))
    objects={}
    for env in ['axis','cotter']:
        objects[env]=helper.run(pre+'ci_to_cad()pin_'+env+'_envelope();\n',env+'-world-envelope',folder)
    excluded=[];hosts=[]
    for row in snapshot['parts']:
        if 'cable-input-' in row['id'] or row['id']=='feeder/cable-core-input':excluded.append(row['id'])
        elif row['id'] in ['feeder/cable-housing','feeder/cable-core-route']:excluded.append(row['id'])
        else:hosts.append(row)
    pairs=[];native=[]
    for env,obj in objects.items():
        A=obj['bounds']
        for host in hosts:
            B=host['mesh']['bounds'];kind=host['motion']['kind']
            gaps=[max(B['min'][a]-A['max'][a],A['min'][a]-B['max'][a]) for a in range(3)]
            row={'candidate':env,'host':host['id'],'sha256':host['sha256'],'axis_gaps_mm':gaps}
            if kind!='fixed':
                if kind in ['translate','radial']:assert host['motion']['axis'][1]==0
                elif kind=='spring':assert host['motion'].get('axis',[0,0,1])[1]==0
                else:assert kind=='output-wire'
                assert gaps[1]>0,row
                row['status']='CONTINUOUS_Y_SEPARATION'
            elif max(gaps)>0:row['status']='FIXED_AABB_SEPARATION'
            else:
                name=env+'-host-'+host['id'].replace('/','__')
                code='intersection(){import('+json.dumps(str(ROOT/obj['file']))+');import('+json.dumps(str(ROOT/host['file']))+');}\n'
                r=helper.run(code,name,folder);native.append(r)
                row['status']='NATIVE_EMPTY' if r['native_empty'] else 'UNCLASSIFIED_INTERSECTION'
                row['native_probe']=name
            pairs.append(row)
    routepre=pre+'use <'+str(ROOT/'output/current-axis-offset-candidate/route/candidate.scad')+'>\n'
    route=[]
    for env in ['axis','cotter']:
        code=routepre+'intersection(){ci_to_cad()pin_'+env+'_envelope();union(){cr_housing();cr_wire();}}\n'
        route.append(helper.run(code,env+'-route-zero-adjustment',folder))
    checks={
        'local_expected_clear_or_capture_plane':all(r['native_empty'] or (r['name']=='axis-plastic' and r.get('only_capture_planes',False)) for r in local if r['name']!='short-pin-forced-washer-control'),
        'short_pin_forced_washers_interfere':any(c['volume_mm3']>.001 for r in local if r['name']=='short-pin-forced-washer-control' for c in r.get('raw_geometry',{}).get('components',[])),
        'host_all_declared_pairs_clear':all(r['status']!='UNCLASSIFIED_INTERSECTION' for r in pairs),
        'revised_route_zero_adjustment_clear':all(r['native_empty'] for r in route),
        'source_stable':all(sha(ROOT/p)==v for p,v in sources.items()),
    }
    report={'status':'CONDITIONAL_STANDARD_PIN_GEOMETRY_PASS' if all(checks.values()) else 'REVIEW_REQUIRED',
        'source_sha256':sources,'checks':checks,'local_probes':local,'objects':objects,'host_pairs':pairs,
        'native_host_probes':native,'route_probes':route,'excluded_snapshot_instances':excluded,
        'axis_conditions':{'origin':[75,-85,5],'E_near_hole_edge_fixed_mm':30,'L_fixed_mm':35,
            'both_washers_at_rear':True,'nominal_housing_outer_span_mm':26,'coaxial_float_outer_mm':[0,2],
            'root_requirement_NOT_supplier_guarantee':{'max_d_mm':9,'max_under_head_length_mm':2.5},
            'cotter_installed_shape_NOT_supplier_guarantee':{'max_radius_from_main_axis_including_play_mm':24,'max_absolute_distance_from_straight_leg_centre_plane_mm':1,'plane_perpendicular_to_main_axis':True,'in_hole_axial_centre_play_bound_mm':.4},
            'washer_OD_fixed_nominal_mm':15},
        'not_checked':['E/L actual tolerances, head-root supplied geometry and actual printed outer span','Off-axis motion, washer/pin tilt, formed cotter acceptance and force retention','Cotter plier forming/extraction, actual hardware stock/roughness, load capacity and wear','Rotor beyond three sampled poses, free hose motion, route adjustment beyond zero','Physical release/return, air/ball function and first assembly'],
        'unchanged_components':'Body, cover, rotor and host mounting reused from prior offset/retention candidates; not newly approved for loads.',
        'adopted':False,'manufacturing_release':False,'physical_acceptance':False}
    (folder/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (OUT/'latest.json').write_text(json.dumps({'directory':rel(folder),'report_sha256':sha(folder/'report.json')},indent=2)+'\n')
    print(json.dumps({'status':report['status'],'directory':rel(folder),'checks':checks,'host_pairs':len(pairs)},indent=2),flush=True)

if __name__=='__main__':main()

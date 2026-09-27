#!/usr/bin/env python3
"""Native space-budget review; does not certify the installed E-clip envelope."""
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
import hashlib, importlib.util, json, math, re

OUT=Path(__file__).resolve().parent; ROOT=OUT.parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
rel=lambda p:str(Path(p).relative_to(ROOT))
helperfile=ROOT/'output/current-axis-offset-candidate/host-review/review.py'
spec=importlib.util.spec_from_file_location('host_helper',helperfile)
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
SNAP=ROOT/'output/cable-scene-export/20260927T091627124663Z/report.json'

def main():
    folder=OUT/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');folder.mkdir(parents=True)
    sources={rel(Path(__file__)):sha(__file__),rel(helperfile):sha(helperfile),rel(SNAP):sha(SNAP)}
    todo=[OUT/'candidate.scad',ROOT/'output/current-axis-offset-candidate/route/candidate.scad']
    while todo:
        p=todo.pop().resolve(); n=rel(p)
        if n in sources:continue
        sources[n]=sha(p)
        todo.extend(p.parent/s for s in re.findall(r'\b(?:use|include)\s*<([^>]+)>',p.read_text()))
    for n in ['output/current-axis-circlip-reference/alternate-supplier/report.json',
              'output/current-axis-eclip-reference/ring/report.json',
              'output/current-axis-pin-retention/feasibility/continuous-rotation.json']:
        sources[n]=sha(ROOT/n)
    scene=json.loads(SNAP.read_text())
    for n,h in scene['source_sha256'].items():
        if n.startswith('cad/'):
            assert sha(ROOT/n)==h,n;sources[n]=h
    for row in scene['parts']:assert sha(ROOT/row['file'])==row['sha256'],row['id']
    pre='$fn=72;\n'+''.join('use <'+str(ROOT/p)+'>\n' for p in [
        'cad/cable-trigger-input.scad','output/current-axis-eclip-candidate/candidate.scad',
        'output/current-axis-offset-candidate/candidate.scad','output/current-axis-retention-review/candidate.scad'])
    jobs=[]
    for name in ['axis','clip']:
        for target,code in [('plastic','ec_plastics()'),('metal','offset_fixed_metal()')]:
            jobs.append((name+'-'+target,'intersection(){ec_'+name+'_space();'+code+';}'))
        for u in [0,10,20]:jobs.append((name+'-rotor-'+str(u),'intersection(){ec_'+name+'_space();ar_rotor('+str(u)+');}'))
    # Forcing the two washers behind an L25 groove consumes body volume.
    jobs.append(('short-axis-positive-control','intersection(){ec_ring(14-25-.95+.8,3.2,15,8.4);ec_plastics();}'))
    def probe(item):
        name,code=item;r=helper.run(pre+code,name,folder)
        if not r['native_empty']:
            _,raw=helper.mesh(ROOT/r['file'])
            r['only_capture_planes']=all(any(all(Fraction(v[2])==z for v in raw[i:i+3]) for z in [-12,14]) for i in range(0,len(raw),3))
            if name=='short-axis-positive-control':r['raw_geometry']=helper.classify(ROOT/r['file'])
        print(name,'empty' if r['native_empty'] else 'nonempty',flush=True);return r
    with ThreadPoolExecutor(max_workers=2) as pool:local=list(pool.map(probe,jobs))
    objects={name:helper.run(pre+'ci_to_cad()ec_'+name+'_space();',name+'-world-space',folder) for name in ['axis','clip']}
    pin=helper.run(pre+'ci_to_cad()ec_pin();','pin-reference',folder)
    pin['geometry']=helper.classify(ROOT/pin['file'])
    excluded=[];hosts=[]
    for row in scene['parts']:
        if 'cable-input-' in row['id'] or row['id'] in ['feeder/cable-core-input','feeder/cable-housing','feeder/cable-core-route']:
            excluded.append(row['id'])
        else:hosts.append(row)
    pairs=[];native=[]
    for name,obj in objects.items():
        A=obj['bounds']
        for host in hosts:
            B=host['mesh']['bounds'];kind=host['motion']['kind']
            gaps=[max(B['min'][i]-A['max'][i],A['min'][i]-B['max'][i]) for i in range(3)]
            row={'candidate':name,'host':host['id'],'host_sha256':host['sha256'],'axis_gaps_mm':gaps}
            if kind!='fixed':
                if kind in ['translate','radial']:assert host['motion']['axis'][1]==0
                elif kind=='spring':assert host['motion'].get('axis',[0,0,1])[1]==0
                else:assert kind=='output-wire'
                assert gaps[1]>0,row;row['status']='CONTINUOUS_Y_SEPARATION'
            elif max(gaps)>0:row['status']='FIXED_AABB_SEPARATION'
            else:
                r=helper.run('intersection(){import('+json.dumps(str(ROOT/obj['file']))+');import('+json.dumps(str(ROOT/host['file']))+');}',name+'-host-'+host['id'].replace('/','__'),folder)
                native.append(r);row['status']='NATIVE_EMPTY' if r['native_empty'] else 'UNCLASSIFIED_INTERSECTION'
            pairs.append(row)
    route=[]
    routepre=pre+'use <'+str(ROOT/'output/current-axis-offset-candidate/route/candidate.scad')+'>\n'
    for name in ['axis','clip']:
        route.append(helper.run(routepre+'intersection(){ci_to_cad()ec_'+name+'_space();union(){cr_housing();cr_wire();}}',name+'-route-zero',folder))
    # Independent arithmetic from the source-bound supplier values, in exact decimals.
    F=Fraction
    min_capture=F('30')-F('3.6');max_capture=F('30.1')+F('1')-F('.76')-F('2.8')
    stack={'capture_span_mm':[float(min_capture),float(max_capture)],
           'float_limit_at_nominal_H26_mm':[float(min_capture-26),float(max_capture-26)],
           'float_limit_if_actual_H25_7_to26_3_mm':[float(min_capture-F('26.3')),float(max_capture-F('25.7'))],
           'actual_H_range_is_design_acceptance_not_printer_guarantee':True,
           'native_body_remains_nominal_H26':True,
           'clip_slot_thickness_clearance_mm':[float(F('.9')-F('.84')),float(F('1')-F('.76'))]}
    continuous={'scope':'Source-bound unchanged complete ar_rotor(u), coaxial rigid model; space volumes only.',
                'rotor_z_mm':[-3.75,7.75],
                'shaft_radius_upper_mm':4/math.cos(math.pi/72),
                'bush_empty_radius_lower_mm':4.1*math.cos(math.pi/72),
                'radial_gap_lower_mm':4.1*math.cos(math.pi/72)-4/math.cos(math.pi/72),
                'root_axial_gap_mm':3.75,'head_axial_gap_mm':6.25,'tail_washer_axial_gap_mm':8.25,
                'clip_space_axial_gap_mm':9.71,
                'clip_actual_installed_envelope_certified':False}
    checks={
        'local_space_clear_or_exact_capture_plane':all(r['native_empty'] or (r['name']=='axis-plastic' and r.get('only_capture_planes',False)) for r in local if r['name']!='short-axis-positive-control'),
        'positive_control_solid_interference_detected':any(c['volume_mm3']>.001 for r in local if r['name']=='short-axis-positive-control' for c in r.get('raw_geometry',{}).get('components',[])),
        'host_pairs_clear':all(r['status']!='UNCLASSIFIED_INTERSECTION' for r in pairs),
        'revised_route_clear_at_zero':all(r['native_empty'] for r in route),
        'native_float_bound_covers_nominal_stack':max_capture-26<=F('1.54'),
        'continuous_rotor_radial_gap_positive':continuous['radial_gap_lower_mm']>0,
        'source_stable':all(sha(ROOT/n)==h for n,h in sources.items())}
    d={'status':'DECLARED_ECLIP_SPACE_BUDGET_CLEAR' if all(checks.values()) else 'REVIEW_REQUIRED',
       'source_sha256':sources,'checks':checks,'stack':stack,'continuous_rotor':continuous,
       'local_probes':local,'objects':objects,'pin_reference':pin,'host_pairs':pairs,'native_host_probes':native,
       'route_probes':route,'excluded_snapshot_instances':excluded,
       'engineering_bounds_not_supplier_guarantees':{'head_d_max':16,'tail_N_max':6,'root_d_max':9,'root_length_max':2.5,
           'washer_OD_fixed_nominal':15,'clip_installed_radius_max':10,'clip_max_axial_overhang_beyond_groove':1},
       'not_proved':['Actual installed clip remains in the required volume, including tilt and elastic deformation',
           'Head/root/tail supplied form and actual printed dimensions','Full radial insertion deformation, push tool and removal path',
           'Load capacity, friction, return, first assembly and ball/air performance'],
       'formal_CAD_changed':False,'adopted':False,'manufacturing_release':False,'physical_acceptance':False}
    (folder/'report.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
    (OUT/'latest.json').write_text(json.dumps({'directory':rel(folder),'report_sha256':sha(folder/'report.json')},indent=2)+'\n')
    print(json.dumps({'status':d['status'],'directory':rel(folder),'checks':checks,'host_pairs':len(pairs)},indent=2),flush=True)

if __name__=='__main__':main()

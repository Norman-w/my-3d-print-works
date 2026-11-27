#!/usr/bin/env python3
"""Bounded through-axle candidate checks; never modifies adopted CAD or prints."""
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,re,subprocess

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
SCAD=OUT/'candidate.scad'
BIN='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def inspect(path):
    s=path.read_text()
    vertices=[tuple(map(float,m)) for m in re.findall(r'vertex\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)',s)]
    assert vertices and len(vertices)%3==0
    def det(a,b,c):return a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0])
    vol=sum(det(*vertices[i:i+3])/6 for i in range(0,len(vertices),3))
    return {'triangles':len(vertices)//3,'signed_volume_mm3':vol,
            'bounds_mm':[[min(v[i] for v in vertices),max(v[i] for v in vertices)] for i in range(3)],
            'all_vertices_on_external_contact_planes':all(min(abs(v[2]+12),abs(v[2]-14))<1e-7 for v in vertices),
            'each_triangle_on_one_contact_plane':all(
                any(all(abs(v[2]-z)<1e-7 for v in vertices[i:i+3]) for z in [-12,14])
                for i in range(0,len(vertices),3))}

def main():
    run=OUT/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');run.mkdir(parents=True)
    sources=['cad/cable-trigger-input.scad','cad/parameters.scad',str(SCAD.relative_to(ROOT)),
             str(Path(__file__).resolve().relative_to(ROOT)),'docs/current-assembly-selections.json']
    identity={n:sha(ROOT/n) for n in sources}
    def one(name):
        stl=run/(name+'.stl');log=run/(name+'.log')
        cmd=[BIN,'--export-format=asciistl','-D','part="'+name+'"','-o',str(stl),str(SCAD)]
        p=subprocess.run(cmd,capture_output=True,text=True);log.write_text(p.stdout+p.stderr)
        assert 'ERROR:' not in log.read_text() and 'WARNING:' not in log.read_text(),log
        empty='Current top level object is empty.' in log.read_text()
        info=None if empty else inspect(stl)
        return {'case':name,'command':cmd,'returncode':p.returncode,'native_empty':empty,
                'mesh':info,'log_sha256':sha(log),'stl_sha256':None if empty else sha(stl)}
    with ThreadPoolExecutor(max_workers=2) as pool:cases=list(pool.map(one,['plastic-probe','metal-probe','rotor-probe','short-positive']))
    by={r['case']:r for r in cases}
    for name in ['metal-probe','rotor-probe']:assert by[name]['native_empty'],by[name]
    plastic=by['plastic-probe']
    assert plastic['native_empty'] or (abs(plastic['mesh']['signed_volume_mm3'])<1e-7 and plastic['mesh']['each_triangle_on_one_contact_plane']),plastic
    assert not by['short-positive']['native_empty'] and by['short-positive']['mesh']['signed_volume_mm3']>.001
    assert all(sha(ROOT/n)==h for n,h in identity.items())
    report={'status':'ISOLATED_FLOATING_THROUGH_AXLE_CANDIDATE_LIMITED_CHECKS_PASSED',
      'source_sha256':identity,'sources_stable':True,'cases':cases,
      'existing_geometry':{'external_faces_z_mm':[-12,14],'external_span_mm':26,
        'internal_faces_z_mm':[-4,8],'internal_span_mm':12,'rotating_stack_nominal_mm':11.5},
      'candidate':{'tube_nominal_mm':{'OD':8,'ID':4.3,'L':27},'tube_length_bounds_mm':[26.98,27.02],
        'washer_nominal_mm':{'OD':12,'ID':4.3,'t':1.1},'washer_thickness_bounds_mm':[.9,1.1],
        'external_total_axial_float_if_nominal_housing_mm':[.98,1.02],
        'bolt_nominal':'M4x35 socket cap; no exact length tolerance consumed',
        'nut_nominal':'M4 AF7 H3.2; height tolerance and locking not consumed',
        'rotor_nominal_axial_float_mm':.5},
      'sufficient_conditions':[
        'Actual tube minimum length exceeds actual maximum outside span, including outer-face tilt, tube tilt and local bulges.',
        'Both enlarged washers retain the through bores with sufficient actual overlap; washer and bolt eccentricity belong to the same assembly.',
        'Side M3 joints locate and carry the cover; main axis bolt no longer clamps the plastic housing.',
        'Actual inner cavity minus actual rotor/bush/thrust stack retains positive axial float under load.'
      ],
      'scope':'Continuous axial envelope at coaxial nominal radial registration and nominal plastic geometry only. Rotor intersection is rotation-invariant in the shared axial interval: axis radius<=4 and the 72-sided rotor bore contains a circle of radius 4.1*cos(pi/72)>4.096. External heads/washers/nut are outside rotor Z extent.',
      'catalog_basis':[
        {'part':'SPMSS-D8-V4.3-L27','status':'Derived catalog configuration, not online confirmed',
         'url':'https://jp.misumi-ec.com/vona2/detail/110411266569/?optPageSCate=seriesList',
         'basis':'Same published SPMSS domain and tolerances as the frozen L15 review; L27<=8*V=34.4.',
         'source_report':'output/current-axis-supply-review/report.json'},
        {'part':'Accu HPW-M4-V2-A4','status':'Official indexed specification read 2026-09-27, not purchased',
         'url':'https://www.accu.co.uk/metric-flat-washers/406775-HPW-M4-V2-A4',
         'OD_mm':[11.57,12],'ID_mm':[4.3,4.48],'thickness_mm':[.9,1.1]},
        {'part':'Accu SSC-M4-35-A2','status':'Shape/thread-length reference only; exact bolt length tolerance still unknown',
         'url':'https://www.accu.co.uk/metric-cap-head-screws/2832-SSC-M4-35-A2',
         'nominal_length_mm':35,'minimum_thread_length_mm':20,'thread_pitch_mm':.7}
      ],
      'not_checked':['Radial/tilt coupled fit','Actual bush and thrust washer selection','Printed dimensions and side-post deflection','Anti-rotation or positive axis locking','Torque, washer bending, friction, fatigue and creep','Printed terminal cap (radially remote), cable, and host mount hardware not in native neighbor probes','Full-system and manufacturing candidate adoption'],
      'production_CAD_modified':False,'adopted':False,'manufacturing_release':False,'physical_acceptance':False,'sent_to_printer':False}
    (run/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (OUT/'latest.json').write_text(json.dumps({'directory':str(run.relative_to(ROOT)),'report_sha256':sha(run/'report.json')},indent=2)+'\n')
    print(json.dumps({'directory':str(run.relative_to(ROOT)),'status':report['status'],'cases':[{k:r[k] for k in ['case','native_empty','mesh']} for r in cases]},ensure_ascii=False,indent=2))

if __name__=='__main__':main()

#!/usr/bin/env python3
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,subprocess,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'analysis'))
from feeder_integration import classify
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
SOURCE=HERE.parent/'candidate.scad';EXPECTED='f76a83eeb95644bd3c856922b31da749cc47c083d688d271116f946493994588'
assert sha(SOURCE)==EXPECTED
OUT=HERE/'tool-review-upper-sector';OUT.mkdir(exist_ok=True)
before={str(p):sha(p) for p in [SOURCE,ROOT/'cad/parameters.scad',HERE/'tool-probes.scad',Path(__file__)]}
def one(kind,fault=False):
    name=kind+('-positive-control'if fault else'');path=OUT/(name+'.stl')
    cmd=['/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD','--hardwarnings','--backend','Manifold','--export-format','asciistl',
     '-D','it_kind='+json.dumps(kind),'-D','it_fault='+str(fault).lower(),'-o',str(path),str(HERE/'tool-probes.scad')]
    run=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True);log=run.stdout+run.stderr
    (OUT/(name+'.log')).write_text(log)
    empty='Current top level object is empty' in log and not path.exists()
    bad='WARNING:' in log or 'ERROR:' in log
    detail=classify(path) if path.exists() else None
    contact_only=False
    if kind=='loose-nut' and detail:
        # Keep raw triangles. All components must be confined to one of the
        # two exact, declared washer/nut bearing planes; no skin is deleted.
        contact_only=all(c['planar_contact_only'] and any(max(abs(v-plane) for v in c['bounds'][0])<1e-10 for plane in (-46.6,-35.4)) for c in detail['components'])
    expected=not empty if fault else (empty or contact_only)
    return {'name':name,'kind':kind,'fault':fault,'command':cmd,'returncode':run.returncode,'native_empty':empty,
      'has_warning_or_error':bad,'intersection':detail,'mesh_sha256':sha(path) if path.exists() else None,
      'declared_washer_contact_only':contact_only,
      'bounded_check_passed':expected and not bad,'acceptance':'Empty raw intersection except identified washer bearing planes; positive control must be nonempty. No contact skins removed.'}
jobs=[('sw8-motion',False),('sw10-entry',False),('sw10-torque',False),('sw10-upper-entry',False),('loose-nut',False),('loose-nut-printed',False),('target-fit',False),('sw8-motion',True)]
with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(lambda p:one(*p),jobs))
report={'scope':'Bench-only local input assembly service. Main cover removed, host detached, housing/ferrule disconnected and parked, core released at output, lever at rest. SW8 counterholds; SW10 nuts create axial translation. Does not claim service on the host.',
 'source_hashes_before':before,'source_hashes_after':{p:sha(Path(p)) for p in before},'source_unchanged':sha(SOURCE)==EXPECTED,
 'tool_budgets':{'status':'Geometric budgets only; no supplier tool certification',
   'sw8':{'jaw_gap_mm':8.4,'thickness_mm':3,'head_od_mm':18,'head_plane_local_x_nominal':[-61,-58],'axial_delta_mm':[-2,2],'entry_local_y_mm':25,'handle_relative_y_range_mm':[9,70],'handle_relative_z_range_mm':[-3,3],'rotation':'held at nominal flat orientation; not used to spin the adjuster'},
   'sw10':{'jaw_gap_mm':10.4,'thickness_mm':3,'head_od_mm':20,'entry_radial_mm':25,'fixed_planes_local_x':[[-49.7,-46.7],[-35.3,-32.3]],'working_angle_range_deg':[0,60],'rotation_segment_deg':2,'continuous_rotation_chord_cover_mm':.011,'continuous_entry_handle_chord_cover_mm':.015,'handle_relative_y_range_mm':[9,70],'handle_relative_z_range_mm':[-3,3]},
   'loose_nut':{'maximum_axial_gap_mm':.2,'worst_nominal_thread_end_margin_mm':1.0,'minimum_tool_nut_axial_overlap_mm':2.9,'nut_rotation':'all angles conservatively enclosed by circumscribed AF10 cylinder'}},
 'rows':rows,'all_checks_passed':all(r['bounded_check_passed'] for r in rows),
 'limitations':['No actual wrench jaw strength, available supplied tool, fastener thread runout, torque/preload or printed tolerance proven.','Gap and thread margins are nominal. Source has no physical +/-2 stop.','This is a procedural small-step adjustment budget, not one-shot retreat of a nut by 2-4 mm.','The full route and end-fitting positioning after reseating require separate checks.']}
(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'source_unchanged':report['source_unchanged'],'all_checks_passed':report['all_checks_passed'],'rows':[{k:r[k] for k in ('name','returncode','native_empty','has_warning_or_error','bounded_check_passed','intersection')} for r in rows]},indent=2))

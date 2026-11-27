#!/usr/bin/env python3
"""Classify the four frozen native results; localize, do not widen a tolerance."""
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,re,subprocess,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
BASE=Path(__file__).resolve().parent
RUN=BASE/'runs/20260927T120853849188Z'
sys.path.insert(0,str(ROOT/'analysis'))
from feeder_integration import classify
EXE='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rel(p):return str(Path(p).resolve().relative_to(ROOT))
def verts(p):return np.array([[float(x)for x in m]for m in re.findall(r'vertex\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)',Path(p).read_text())])
def main():
    report=json.loads((RUN/'report.json').read_text())
    assert all(sha(ROOT/p)==h for p,h in report['source_sha256'].items())
    out=RUN/'contact-localization'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
    probe=out/'probe.scad'
    probe.write_text(f'''include <{ROOT/'cad/parameters.scad'}>\nuse <{RUN/'scene-obstacles.scad'}>\nuse <{ROOT/'cad/cable-route-retention.scad'}>\nuse <{ROOT/'cad/cable-output-interface.scad'}>\nkind="cap-external";\nif(kind=="cap-external")intersection(){{crr_cap_sweep(50);union(){{rs_current_rigid();rs_nominal_flexible();}}}}\nelse if(kind=="lower-external")intersection(){{crr_lower_service_sweep();rs_current_rigid();}}\nelse if(kind=="wrong-bridge-at-60")intersection(){{crr_lower(60);co_fixed_bridge();}}\n''')
    watched={**report['source_sha256'],rel(probe):sha(probe),rel(Path(__file__)):sha(__file__)}
    def run(kind):
        target=out/(kind+'.stl');assert not target.exists()
        cmd=[EXE,'--hardwarnings','--backend','Manifold','-D','kind='+json.dumps(kind),'--export-format','asciistl','-o',str(target),str(probe)]
        r=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True);log=r.stdout+r.stderr;logpath=out/(kind+'.log');logpath.write_text(log)
        empty='Current top level object is empty'in log and not target.exists()
        ok=not re.search(r'(?m)(ERROR|WARNING):',log)and(r.returncode==0 or empty)
        row={'case':kind,'command':cmd,'returncode':r.returncode,'execution_ok':bool(ok),'native_empty_message':empty,'log':rel(logpath),'log_sha256':sha(logpath),'artifact':rel(target)if target.exists()else None,'artifact_sha256':sha(target)if target.exists()else None}
        if target.exists():row['mesh']=classify(target)
        print(kind,'empty',empty,'ok',ok,flush=True);return row
    with ThreadPoolExecutor(max_workers=2)as pool:rows=list(pool.map(run,['cap-external','lower-external','wrong-bridge-at-60']))
    inventory=json.loads((ROOT/'docs/cable-assembly-inventory.json').read_text());arc=inventory['scene_contract']['cr']['arcs'][2];C=np.array(arc[2]);N=np.cross(arc[3],arc[4]);N=N/np.linalg.norm(N)
    planes=[]
    for raw in report['cases']:
        if raw['case']=='lower-wrong-straight-down':continue
        v=verts(ROOT/raw['artifact'])
        if raw['case']=='cap-current':
            residual=np.abs((v-C)@N);plane={'origin_cad':C.tolist(),'normal_cad':N.tolist(),'source':'crr_arc_base [-7,0] and cap [0,5] in crr_basis; cap exits toward +N','codec_precision':'packed source contract has 12 fractional decimal digits; basis cross accumulates less than 1e-9 mm here'}
        else:
            residual=np.abs(v[:,2]-84.7);plane={'origin_cad':[0,0,84.7],'normal_cad':[0,0,1],'source':'crr_lower original maximum Z=84.7 matches cr r clamp side contact minimum Z=84.7; first stage exits downward'}
        planes.append({'case':raw['case'],'vertices':len(v),'max_intended_plane_residual_mm':float(residual.max()),'all_on_specified_mating_plane':bool(residual.max()<1e-8),'plane':plane,'interpretation':'Known initial mating boundary; no skin subtraction and no arbitrary thin-solid acceptance.'})
    external=rows[:2];witness=rows[2]
    stable=all(sha(ROOT/p)==h for p,h in watched.items())
    passed=stable and all(x['execution_ok']for x in rows)and all(x['native_empty_message']for x in external)and all(x['all_on_specified_mating_plane']for x in planes)and witness.get('mesh',{}).get('has_solid_or_unclassified_overlap',False)
    result={'status':'CURRENT_RIGID_PATHS_CONDITIONAL_PASS_WRONG_ORDER_DETECTED'if passed else 'REVIEW_REQUIRED','created_utc':datetime.now(timezone.utc).isoformat(),'four_case_report':{'path':rel(RUN/'report.json'),'sha256':sha(RUN/'report.json')},'source_sha256':watched,'sources_stable':stable,'known_mating_planes':planes,'native_localizations':rows,'wrong_order_exact_pair':{'moving':'crr_lower right leg','fixed':'co_fixed_bridge root included in feeder/beam-grip','lower_box_before_motion':[[-49.6,-39],[-65,20],[78.5,84.7]],'bridge_root_box':[[-65,12],[-58,-46],[18,26]],'strict_drop_interval_mm':[52.5,66.7],'interval_derivation':'max(78.5-d,18)<min(84.7-d,26) iff 52.5<d<66.7; X and Y strictly overlap throughout. This identifies this pair, not the earliest collision among all neighbors.','full_sweep_pair_volume_mm3':10.6*12*8,'native_witness_drop_mm':60,'witness_expected_box':[[-49.6,-39],[-58,-46],[18.5,24.7]],'witness_expected_volume_mm3':10.6*12*6.2},'continuous_envelope_basis':{'cap':'The +N removal envelope retains the initial groove; initial cap is solid above local N=3.1. A translated point moves monotonically into that material above the groove; axial bolt holes remain aligned. Source uses an exact/covering continuous extrusion, not sampled poses.','lower':'First drop envelope fills its own holes and covers every 0..8 mm translation. The three filled rectangles at Z70.5..76.7 then cover every rearward 0..100 mm translation. Filled holes make this conservative.'},'manufacturing_release':False,'physical_acceptance':False,'sent_to_printer':False,'limits':['Released t=0, nominal adjuster delta=0 and current feeder/cable inventory geometry only.','Four lower mounting screws and top washers removed before lower motion; base and lower externally supported. Cap and nominal flexible line envelopes are removed first.','Cap sweep is only after six cap screws/washers removal; four main mounting screws remain.','This does not verify screw withdrawal/tools, loose nut handling, grip, flexible line disconnection/deformation, or removal of the entire remaining guide base.','No blower or unmeasured Y fitting; spin and hold modules have no measured placement in this feeder CAD scene.','No manufacturing tolerance, force, material separation, physical reach or load acceptance.']}
    (out/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('FINAL',out/'report.json',result['status'],flush=True)
if __name__=='__main__':main()

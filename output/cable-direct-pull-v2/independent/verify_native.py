#!/usr/bin/env python3
"""Assert the frozen candidate functions against independent numerical values."""
from pathlib import Path
import hashlib,json,subprocess
import review_adjuster

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SOURCE=HERE.parent/'candidate.scad'
EXPECTED='f76a83eeb95644bd3c856922b31da749cc47c083d688d271116f946493994588'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(SOURCE)==EXPECTED,'Candidate changed; stop and re-read before verification'
samples=[[i*.05,review_adjuster.inverse(i*.05)] for i in range(441)]
text='include <'+str(SOURCE)+'>\n'
text+='assert(cdp_fairlead_C==[-24,0,2] && cdp_fairlead_R==60 && cdp_ball_arm_R==60);\n'
text+='assert(cdp_delta_bounds==[-2,2] && cdp_adjuster_nut_x==[-49.8,-35.4] && cdp_adjuster_nut_t==3.2);\n'
text+='assert(cdp_adjuster_washer_x==[-46.6,-37] && cdp_adjuster_washer_t==1.6);\n'
text+='checks='+json.dumps(samples)+';\n'
text+='for(row=checks,d=[-2,0,2]){assert(abs(cdp_angle(row[0],d)-row[1])<1e-8);assert(abs(cdp_takeup(row[1],d)-row[0])<1e-8);}\n'
text+='for(d=[-2,0,2]){assert(cdp_exit(d)==[-29+d,60,2]);assert(abs(cdp_ferrule_mouth(d)-(-65.125+d))<1e-8);assert(cdp_thread_exposure(d)==[3.2-d,3.2+d]);assert(abs(cdp_axial_leadin(d)-(5-d))<1e-8);}\n'
text+='echo("NATIVE_V2_ASSERTIONS_PASS",len(checks)*3);\n'
text+='cdp_direct_contract();\n'
(HERE/'native-assertions.scad').write_text(text)
command=['/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD','--hardwarnings','-o',str(HERE/'native-assertions.csg'),str(HERE/'native-assertions.scad')]
run=subprocess.run(command,cwd=ROOT,text=True,capture_output=True)
(HERE/'native-assertions.log').write_text(run.stdout+run.stderr)
report={'source':str(SOURCE),'source_sha256_before':EXPECTED,'source_sha256_after':sha(SOURCE),'command':command,
 'returncode':run.returncode,'parameters_source_sha256':sha(ROOT/'cad/parameters.scad'),
 'u_grid_mm':[0,22,.05],'delta_samples_mm':[-2,0,2],'angle_and_takeup_assertion_tolerance':1e-8,
 'passed':run.returncode==0 and 'NATIVE_V2_ASSERTIONS_PASS' in run.stderr and 'ERROR:' not in run.stderr and 'WARNING:' not in run.stderr,
 'review_script_sha256':sha(Path(__file__)),'wrapper_sha256':sha(HERE/'native-assertions.scad'),
 'geometry_exported':False,'scope':'Source functions and parameter declarations only; CSG has no geometry.'}
assert report['source_sha256_after']==EXPECTED
(HERE/'native-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))

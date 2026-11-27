"""Candidate-specific ideal length and force budget; not measured return force."""
from pathlib import Path
import importlib.util, math, json, hashlib, subprocess, re, ast

B=Path(__file__).resolve().parent; ROOT=B.parents[1]
spec=importlib.util.spec_from_file_location('independent_v2',B/'independent/review_adjuster.py')
kin=importlib.util.module_from_spec(spec);spec.loader.exec_module(kin)

def main():
    out=B/'actuation';out.mkdir(exist_ok=True)
    sources=[B/'candidate.scad',B/'independent/review_adjuster.py',
      B/'housing-route/numeric/report.json',B/'independent/native-verification.json',
      ROOT/'cad/cable-output-interface.scad',ROOT/'cad/feeder-return-spring.scad',
      ROOT/'cad/parameters.scad',Path(__file__)]
    before={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    wrapper=out/'datums.scad'
    wrapper.write_text(f'''use <{B/'candidate.scad'}>
use <{ROOT/'cad/cable-output-interface.scad'}>
use <{ROOT/'cad/feeder-return-spring.scad'}>
echo("ACTUATION_DATUMS",[co_A(0),co_housing_entry(),co_adjuster_tip(),rs_L(0),rs_L(1)]);
''')
    cmd=['/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD','--hardwarnings','-o',str(out/'datums.echo'),str(wrapper)]
    r=subprocess.run(cmd,capture_output=True,text=True)
    (out/'native.log').write_text(r.stdout+r.stderr)
    assert r.returncode==0 and 'ERROR:' not in r.stderr and 'WARNING:' not in r.stderr
    text=(out/'datums.echo').read_text().split('"ACTUATION_DATUMS", ',1)[1].strip()
    A,port,tip,rest,full=ast.literal_eval(text)
    assert A[:2]==port[:2]==tip[:2] and abs(full-rest-20)<1e-9
    spring=(ROOT/'cad/feeder-return-spring.scad').read_text()
    def literal(name):
        m=re.search(r'^'+re.escape(name)+r'\s*=\s*([\d.]+)\s*;',spring,re.M)
        assert m,name
        return float(m[1])
    F0,k,L0=map(literal,['rs_spring_F0','rs_spring_k','rs_spring_L0'])
    route=json.loads((B/'housing-route/numeric/report.json').read_text())
    rows=[]
    for u in [0,5,10,15,20]:
        g=kin.geometry(kin.inverse(u));theta=math.radians(g['theta_deg'])
        force=F0+k*(rest+u-L0)
        ratio=g['effective_arm_mm_per_rad']/(36*math.cos(theta))
        row=dict(output_travel_mm=u,theta_deg=g['theta_deg'],
          finger_rearward_mm=36*math.sin(theta),effective_input_arm_mm_per_rad=g['effective_arm_mm_per_rad'],
          source_spring_force_N=force,horizontal_finger_force_ratio_ideal=ratio,
          spring_only_horizontal_finger_force_N=force*ratio,settings=[])
        for d in [-2,0,2]:
            gd=kin.geometry(g['theta_deg'],d)
            input_length=34+gd['Q_to_ball_path_mm']
            output_length=port[2]-A[2]-u
            total=route['outside_port_route_length']+input_length+output_length+8
            expected=route['outside_port_route_length']+63-d+(port[2]-A[2])+8
            assert abs(total-expected)<1e-9
            row['settings'].append(dict(delta=d,input_outer_port_to_ball_mm=input_length,
              output_outer_port_to_nipple_mm=output_length,total_core_centreline_with_8mm_tail_mm=total,
              total_length_drift_over_stroke_mm=total-expected))
        rows.append(row)
    result=dict(status='CANDIDATE_IDEAL_LENGTH_AND_FORCE_BUDGET_COMPLETE',source_sha256=before,
       sources_stable=before=={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
       native_command=cmd,native_datums=dict(output_nipple_rest=A,output_outer_port=port,output_inner_tip=tip,spring_length_rest=rest,spring_length_full=full),
       rows=rows,kinematics_identity_evidence='independent/native-verification.json',
       input_fixed_internal_prefix_mm=34,modelled_tail_mm=8,
       manufactured_core_cut_length=None,manufactured_housing_cut_length=None,
       interpretation='For any fixed locked delta, input path gains u and output path loses u. The same nonelastic core has constant geometric length through a trigger cycle. Changing delta changes the required total core length by -delta, so the output clamp/zero must be reset. The route family keeps its outer-port length constant.',
       limitations=['Bare wire and sheath friction, cam/slider friction, ball load, hysteresis and pretension are not included',
         'Spring force is a nominal source value, not a measured margin or return guarantee',
         'The modelled 8 mm free tail is not a supplier-certified minimum clamping tail',
         'No current CAD/web or print release is created by this isolated budget'],
       manufacturing_release=False,physical_acceptance=False)
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],sources_stable=result['sources_stable'],
      source_spring_force_range=[rows[0]['source_spring_force_N'],rows[-1]['source_spring_force_N']],
      ideal_horizontal_finger_force_range=[rows[0]['spring_only_horizontal_finger_force_N'],rows[-1]['spring_only_horizontal_finger_force_N']],
      delta0_core_path=rows[0]['settings'][1]['total_core_centreline_with_8mm_tail_mm']),indent=2))

if __name__=='__main__':main()

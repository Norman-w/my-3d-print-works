#!/usr/bin/env python3
"""Source-derived ideal cable kinematics and force budget; no measured force claim."""
from pathlib import Path
import ast
import hashlib
import json
import math
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/cable-trigger-system'
EXE='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    target=OUT/'contract.echo'
    command=[EXE,'--hardwarnings','-o',str(target),'-D','ct_part="contract"',
             str(ROOT/'cad/cable-trigger-system.scad')]
    run=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
    if run.returncode:
        raise RuntimeError(run.stdout+run.stderr)
    lines=target.read_text().splitlines()
    line=next(x for x in lines if x.startswith('ECHO: "CT_CONTRACT", '))
    text=line.split('ECHO: "CT_CONTRACT", ',1)[1]
    text=re.sub(r'\bundef\b','None',text)
    text=re.sub(r'\btrue\b','True',text)
    text=re.sub(r'\bfalse\b','False',text)
    spec=dict(ast.literal_eval(text))
    inp=dict(spec['input']);out=dict(spec['output'])
    spring_source=(ROOT/'cad/feeder-return-spring.scad').read_text()
    def literal(name):
        match=re.search(r'^'+re.escape(name)+r'\s*=\s*([\d.]+)\s*;',spring_source,re.M)
        if not match:raise ValueError('Expected literal supplier parameter '+name)
        return float(match[1])
    preload=literal('rs_spring_F0');rate=literal('rs_spring_k');free=literal('rs_spring_L0')
    R=inp['radius_cable'];r=inp['radius_finger'];stroke=inp['stroke']
    A=out['moving_wire_axis_t0'];tip=out['adjuster_wire_tip']
    assert A[:2]==tip[:2], 'Output free wire must be collinear with carriage travel'
    origin=inp['origin'];axes=[inp['basis_x'],inp['basis_y'],inp['basis_z']]
    def cad(p):return [origin[i]+sum(p[j]*axes[j][i] for j in range(3)) for i in range(3)]
    rows=[]
    for u in [0,stroke/4,stroke/2,3*stroke/4,stroke]:
        theta=u/R
        force=preload+rate*(spec['spring_length_rest']+u-free)
        ratio=R/(r*math.cos(theta))
        rows.append({'output_travel_mm':u,'angle_deg':math.degrees(theta),
          'finger_rearward_mm':r*math.sin(theta),
          'input_wrapped_length_change_mm':R*theta,
          'output_free_wire_length_mm':tip[2]-A[2]-u,
          'free_wire_length_change_sum_mm':R*theta-u,
          'spring_force_catalog_nominal_N':force,
          'horizontal_finger_force_ratio_ideal':ratio,
          'finger_force_spring_only_N':ratio*force,
          'finger_force_if_additional_output_resistance_5N':ratio*(force+5)})
    sources=[ROOT/'cad/cable-trigger-input.scad',ROOT/'cad/cable-output-interface.scad',
             ROOT/'cad/cable-trigger-system.scad',ROOT/'cad/feeder-return-spring.scad',
             ROOT/'cad/cable-housing-route.scad',ROOT/'cad/parameters.scad',Path(__file__).resolve()]
    route_evidence=None
    for path in sorted((ROOT/'output/cable-housing-route').glob('*/report.json'),reverse=True):
        candidate=json.loads(path.read_text())
        if candidate.get('status')!='NOMINAL_ROUTE_LOCAL_GEOMETRY_PASS':continue
        recorded=candidate['source_sha256']
        if not all((ROOT/key).is_file() and hashlib.sha256((ROOT/key).read_bytes()).hexdigest()==value
                   for key,value in recorded.items()):continue
        route_evidence={'report':str(path.relative_to(ROOT)),
          'status':candidate['status'],
          'outside_port_route_length_mm':candidate['independent_length_mm'],
          'nominal_bend_radius_mm':candidate['contract']['arc_radius'],
          'physical_route_retained':False,'manufactured_cut_length_mm':None}
        break
    core_budget = None
    if route_evidence is not None:
        # Read the actual source anchor used by the cable arc. Refuse to invent
        # an angle if the parameterization changes. No STL-derived dimensions.
        input_source=(ROOT/'cad/cable-trigger-input.scad').read_text()
        match=re.search(r'\ba\s*=\s*([\d.]+)\s*-\s*ci_angle\(u\)\s*;',input_source)
        if not match:raise ValueError('Cable anchor angle source changed; review length contract')
        anchor_angle=math.radians(float(match[1]))
        tangent=inp['wire_tangent_local']
        port=[inp['adjuster_overall_x'][0],inp['adjuster_seat_local'][1],inp['wire_z']]
        straight=math.dist(port,tangent)
        wrapped=R*(math.atan2(tangent[1],tangent[0])-anchor_angle)
        tail=out['wire_tail_below_center']
        output_straight=math.dist(out['housing_route_entry'],A)
        L=route_evidence['outside_port_route_length_mm']+straight+wrapped+output_straight+tail
        core_budget={
            'status':'NOMINAL_CENTERLINE_LENGTH_ONLY',
            'route_between_outer_ports_mm':route_evidence['outside_port_route_length_mm'],
            'input_port_to_tangent_mm':straight,'input_initial_wrapped_arc_mm':wrapped,
            'output_port_to_nipple_center_mm':output_straight,
            'tail_below_nipple_center_mm':tail,
            'core_ball_center_to_free_tip_mm':L,
            'candidate_catalog_core_L1_mm':1200,
            'conservative_ball_datum_allowance_mm':inp['ball_d_candidate'],
            'remaining_after_ball_datum_allowance_mm':1200-L-inp['ball_d_candidate'],
            'full_stroke_length_change_mm':rows[-1]['free_wire_length_change_sum_mm'],
            'tail_withdrawal_required_mm':out['core_withdrawal_from_nipple_nominal'],
            'input_take_up_remaining_after_tail_withdrawal_mm':stroke-out['core_withdrawal_from_nipple_nominal'],
            'interpretation':'End seating cancels from a complete port-to-port core path. '
                'The 5 mm allowance covers ball-side-versus-center datum ambiguity conservatively. '
                'This is not a sheath cut length or proof of the final unretained installation route. '
                'Leave the core long until both seats, travel and tail are set; trim core last.'}
    result={'status':'IDEAL_KINEMATICS_ONLY','command':command,
      'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
      'source_contract':spec,'rows':rows,
      'input_cable_exit_cad':cad(inp['adjuster_exit_local']),
      'input_housing_stop':inp['housing_stop_local'],
      'housing_route_verified':False,
      'nominal_route_local_geometry_evidence':route_evidence,
      'nominal_core_length_budget':core_budget,
      'force_interpretation':'Horizontal force at the model finger radius, ideal circular take-up. '
          'Spring values come from the existing catalog-source model. Additional 5 N is a sensitivity case, not a measurement.',
      'return_condition':'At every position the real spring must overcome feeder friction, reverse Bowden losses and input bearing/stop resistance. Those terms are not measured.',
      'unclosed':['actual housing end seating and retained installation route','friction in both directions','cable preload and backlash',
                  'loaded guide deformation','terminal holding force','physical one-ball release'],
      'manufacturing_release':False,'physical_acceptance':False}
    report=OUT/'actuation-budget.json'
    report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'report':str(report),'rows':rows},ensure_ascii=False))


if __name__=='__main__':main()

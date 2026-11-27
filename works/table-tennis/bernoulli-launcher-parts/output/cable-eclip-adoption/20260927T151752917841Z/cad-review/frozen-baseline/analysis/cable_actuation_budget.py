#!/usr/bin/env python3
"""Formal direct-pull kinematics, force and length budget; timestamped, offline.

Legacy reports and the preserved pre-adoption script are never overwritten.
Nothing is sent to a printer, and no physical acceptance is inferred.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import math
import re

from cable_direct_contract import (DirectPullContract, export_contract, number,
                                   pairs, sha, source_hashes, vector)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT/'output/cable-actuation-v2'
INPUT = ROOT/'cad/cable-trigger-input.scad'
OUTPUT = ROOT/'cad/cable-output-interface.scad'
ROUTE = ROOT/'cad/cable-housing-route.scad'
SPRING = ROOT/'cad/feeder-return-spring.scad'
HELPER = ROOT/'analysis/cable_direct_contract.py'
TOL = 1e-8


def require(condition, message):
    if not condition:
        raise ValueError(message)


def spring_catalog_literals():
    """Read named numeric supplier-model literals only, never motion code."""
    source = SPRING.read_text()
    result = {}
    for name in ('rs_spring_F0','rs_spring_k','rs_spring_L0','rs_spring_Fmax','rs_spring_Lmax'):
        pattern = r'^'+re.escape(name)+r'\s*=\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*;'
        matches = list(re.finditer(pattern, source, re.M))
        require(len(matches)==1, 'Expected one numeric spring catalog literal: '+name)
        result[name] = {'value':float(matches[0][1]),
                        'line':source.count('\n',0,matches[0].start())+1}
    return result


def numeric_checks(model):
    domain_max = model.u_domain[1]
    states = [model.state(domain_max*i/220) for i in range(221)]
    residual = max(abs(s['input_path_change_mm']-s['input_take_up_requested_mm']) for s in states)
    derivative_errors = []
    h = 1e-6
    for s in states[1:-1]:
        a = s['angle_deg']
        finite = (model.path_length(a+math.degrees(h))-model.path_length(a-math.degrees(h)))/(2*h)
        derivative_errors.append(abs(finite-s['effective_cable_arm_mm_per_rad']))
    rejected = []
    trials = [('negative-u',lambda:model.solve(math.nextafter(0,-math.inf))),
              ('above-u-domain',lambda:model.solve(math.nextafter(domain_max,math.inf))),
              ('nan-u',lambda:model.solve(math.nan)),('infinite-u',lambda:model.solve(math.inf)),
              ('boolean-u',lambda:model.solve(True)),
              ('delta-below-domain',lambda:model.solve(0,math.nextafter(model.delta_domain[0],-math.inf))),
              ('delta-above-domain',lambda:model.solve(0,math.nextafter(model.delta_domain[1],math.inf))),
              ('angle-above-bracket',lambda:model.path_length(math.nextafter(model.angle_domain[1],math.inf))),
              ('legacy-law',lambda:DirectPullContract(dict(model.spec,motion_law='circular-wrap'))),
              ('missing-law',lambda:DirectPullContract({k:v for k,v in model.spec.items() if k!='motion_law'})),
              ('unsupported-ball-axis',lambda:DirectPullContract(dict(model.spec,wire_terminal_local=[1,model.R,model.z])))]
    for name,call in trials:
        try:
            call()
        except (ValueError,KeyError):
            rejected.append(name)
        else:
            raise ValueError('Exact domain/schema rejection failed: '+name)
    require(residual<TOL, 'Inverse path residual failed')
    require(max(derivative_errors)<1e-6, 'Variable moment-arm derivative failed')
    require(all(b['angle_deg']>a['angle_deg'] for a,b in zip(states,states[1:])), 'Inverse is not strictly monotone')
    return {'input_domain_mm':list(model.u_domain),'sample_count':len(states),
            'max_inverse_residual_mm':residual,'central_difference_step_rad':h,
            'max_arm_derivative_difference_mm_per_rad':max(derivative_errors),
            'exact_rejection_cases_passed':rejected,
            'analytic_uniqueness_basis':'For the explicitly validated equal-radius layout and angle<90 deg, 0<=phi<=theta and dL/dtheta=R*cos(theta-phi)>=R*cos(angle_upper)>0.',
            'analytic_arm_lower_bound_over_solve_interval_mm':model.monotonic_arm_lower_bound}


def native_checks(model, out):
    us = sorted(set([model.u_domain[1]*i/20 for i in range(21)] + [model.stroke*i/4 for i in range(5)]))
    ds = sorted(set([*model.delta_domain,model.delta]))
    expression = ('[for(u='+json.dumps(us)+',d='+json.dumps(ds)+')'
        'let(a=ci_angle(u,d))[u,d,a,ci_phi(a),ci_path_length(a,d),ci_takeup(a,d),ci_effective_arm(u)]]')
    rows,evidence = export_contract(out/'native-motion.scad', expression, [INPUT], cwd=ROOT)
    maxima = [0.0]*5
    for row in rows:
        require(len(row)==7, 'Native motion row schema changed')
        u,d,a,phi,length,takeup,arm = row
        state = model.state(u,d)
        expected = [state['angle_deg'],state['guide_contact_angle_deg'],state['exit_to_ball_path_mm'],state['input_path_change_mm'],state['effective_cable_arm_mm_per_rad']]
        for i,(actual,wanted) in enumerate(zip([a,phi,length,takeup,arm],expected)):
            maxima[i] = max(maxima[i],abs(actual-wanted))
    require(max(maxima)<TOL, 'Formal native functions disagree with contract-derived analysis')
    return {'passed':True,'combination_count':len(rows),'u_samples_mm':us,'delta_samples_mm':ds,
            'comparison_columns':['angle_deg','contact_angle_deg','path_mm','takeup_mm','moment_arm_mm_per_rad'],
            'max_absolute_differences':maxima,'tolerance':TOL,'evidence':evidence,'native_rows':rows}


def analyze(out):
    imports = [INPUT,OUTPUT,ROUTE,SPRING]
    expression = ('[["input",ci_spec()],["output",co_contract_data()],["route",cr_contract()],'
                  '["spring_length_rest",rs_L(0)],["spring_length_pulled",rs_L(1)]]')
    raw,evidence = export_contract(out/'formal-contract.scad',expression,imports,cwd=ROOT)
    contract = pairs(raw)
    inp = pairs(contract['input'],'input');output = pairs(contract['output'],'output');route = pairs(contract['route'],'route')
    model = DirectPullContract(inp)
    require(route.get('route_law')=='fixed-third-arc-equal-length-v1','Unsupported or stale housing route law')
    require(number(route['adjuster_delta'],'route delta')==model.delta,'Input/route adjustment settings differ')
    require(vector(route['adjuster_delta_range'],2,'route delta range')==model.delta_domain,'Input/route adjustment domains differ')
    checks = numeric_checks(model)
    native = native_checks(model,out)
    catalog = spring_catalog_literals()
    spring = {k:v['value'] for k,v in catalog.items()}
    A0 = vector(output['moving_wire_axis_t0'],3,'output A0')
    A1 = vector(output['moving_wire_axis_t1'],3,'output A1')
    tip = vector(output['adjuster_wire_tip'],3,'output wire tip')
    port_out = vector(output['housing_route_entry'],3,'output port')
    require(abs(number(output['stroke'],'output stroke')-model.stroke)<TOL,'Input/output working strokes differ')
    require(all(abs(A1[i]-A0[i])<TOL for i in (0,1)) and abs(A1[2]-A0[2]-model.stroke)<TOL,'Output is not the declared +Z translation')
    require(all(abs(p[i]-A0[i])<TOL for p in [tip,port_out] for i in (0,1)),'Output core/port not collinear')
    require(tip[2]>A1[2], 'Output free wire becomes nonpositive at full working stroke')
    origin = vector(inp['origin'],3,'origin')
    axes = [vector(inp['basis_'+k],3,'basis_'+k) for k in ('x','y','z')]
    require(all(abs(sum(axes[i][k]*axes[j][k] for k in range(3))-(1 if i==j else 0))<1e-10 for i in range(3) for j in range(3)), 'Input frame is not orthonormal')
    def cad(p):return [origin[i]+sum(p[j]*axes[j][i] for j in range(3)) for i in range(3)]
    def local(p):return [sum((p[i]-origin[i])*axes[j][i] for i in range(3)) for j in range(3)]
    port_in_cad = vector(route['input_port'],3,'route input port')
    port_in = local(port_in_cad)
    require(math.dist(route['output_port'],port_out)<TOL,'Route/output port mismatch')
    require(abs(port_in[1]-model.R)<TOL and abs(port_in[2]-model.z)<TOL,'Route entry is not on the input axial core line')
    require(abs(port_in[0]-number(inp['adjuster_head_x'][0],'input head inlet'))<TOL,'Route uses a stale adjustment entry')
    require(port_in[0] <= model.exit_current[0], 'Route port lies beyond the adjuster wire exit')
    internal_axis_length = model.exit_current[0]-port_in[0]
    route_length = number(route['outside_port_route_length'],'route centreline length')
    require(route_length>0,'Nonpositive route length')
    require(abs(number(contract['spring_length_pulled'],'spring pulled')-number(contract['spring_length_rest'],'spring rest')-model.stroke)<TOL,'Spring extension does not follow output stroke')
    tail = number(output['wire_tail_below_center'],'core tail')
    require(tail>=0,'Negative output core tail')
    rows=[]
    for u in [model.stroke*i/4 for i in range(5)]:
        state=model.state(u)
        length=number(contract['spring_length_rest'],'spring rest')+u
        force=spring['rs_spring_F0']+spring['rs_spring_k']*(length-spring['rs_spring_L0'])
        state.update(output_travel_mm=u,output_free_wire_length_mm=tip[2]-A0[2]-u,
            output_free_wire_change_mm=-u,free_wire_length_change_sum_mm=state['input_path_change_mm']-u,
            input_outer_port_to_ball_path_mm=internal_axis_length+state['exit_to_ball_path_mm'],
            output_outer_port_to_nipple_center_mm=port_out[2]-A0[2]-u,
            spring_length_mm=length,spring_force_catalog_nominal_N=force,
            spring_catalog_range_check=length<=spring['rs_spring_Lmax'] and force<=spring['rs_spring_Fmax'],
            finger_force_spring_only_N=state['horizontal_finger_force_ratio_ideal']*force,
            finger_force_if_additional_output_resistance_5N=state['horizontal_finger_force_ratio_ideal']*(force+5))
        state['whole_core_centerline_length_mm']=route_length+state['input_outer_port_to_ball_path_mm']+state['output_outer_port_to_nipple_center_mm']+tail
        rows.append(state)
    conservation=max(abs(r['free_wire_length_change_sum_mm']) for r in rows)
    whole_span=max(r['whole_core_centerline_length_mm'] for r in rows)-min(r['whole_core_centerline_length_mm'] for r in rows)
    require(conservation<TOL and whole_span<TOL,'Core-length conservation failed')
    delta_rows=[]
    for d in sorted(set([*model.delta_domain,model.delta])):
        state=model.state(0,d)
        delta_rows.append({'delta_mm':d,'exit_to_ball_rest_path_mm':state['exit_to_ball_path_mm'],
            'change_from_current_delta_mm':state['exit_to_ball_path_mm']-model.path_length(0),
            'interpretation':'Absolute input length changes; same-delta stroke increments cancel. Whole-core change has this value only if outside route and relative ferrule seating lengths stay constant.'})
    return {'status':'IDEAL_DIRECT_PULL_CONTRACT_CHECKS_PASS','motion_law':inp['motion_law'],
        'formal_contract_evidence':evidence,'source_contract':{'input':inp,'output':output,'route':route,
            'spring_length_rest':contract['spring_length_rest'],'spring_length_pulled':contract['spring_length_pulled']},
        'spring_catalog_model_literals':catalog,'rows':rows,'numeric_checks':checks,'native_function_checks':native,
        'length_conservation':{'max_free_wire_change_residual_mm':conservation,'whole_core_length_span_mm':whole_span,
            'conditions':['Delta is fixed during each stroke','Core is taut, terminals do not slip, and housing endpoints stay seated','The specified convex guide contact and forward tangent branch are maintained','Core stretch, friction and housing deformation are omitted']},
        'adjustment_absolute_length_cases':delta_rows,
        'zero_setting_condition':'After any delta change, reseat/re-route the housing and reset output core slack/preload/zero before locking both adjuster nuts and coordinating the output stop. Incremental invariance is not automatic zero invariance.',
        'input_cable_exit_cad':cad(model.exit_current),'input_housing_stop':inp['housing_stop_local'],
        'nominal_core_length_budget':{'status':'NOMINAL_BALL_CENTRE_TO_FREE_TIP_CENTERLINE_ONLY',
            'route_between_outer_ports_mm':route_length,'input_outer_port_to_adjuster_exit_mm':internal_axis_length,
            'input_rest_exit_to_ball_path_mm':model.path_length(0),
            'output_outer_port_to_nipple_center_rest_mm':port_out[2]-A0[2],
            'tail_below_nipple_center_mm':tail,'core_ball_center_to_free_tip_mm':rows[0]['whole_core_centerline_length_mm'],
            'manufactured_housing_cut_length_mm':None,'manufactured_core_cut_length_mm':None,
            'supplier_ball_datum_and_end_allowances_confirmed':False,
            'interpretation':'Outer ports divide a nominal full core centreline. This number is neither a housing cut length nor an approved core trim instruction. Actual ferrule seating, ball datum, clamp insertion and final installation are unresolved; core is trimmed last.'},
        'force_interpretation':'Ideal horizontal finger force at the contracted finger radius: output resistance times [d(input path)/dtheta]/[d(finger rearward)/dtheta]. The cable arm varies with position. Spring values are catalog-model values; additional 5 N is sensitivity only, not measured feeder friction.',
        'return_condition':'At every position the real spring must exceed feeder friction, reverse Bowden/fixed-guide losses and input bearing/stop resistance; no measured loaded-return claim.',
        'unclosed':['actual ferrule seating and installed free housing shape','bare-core guide bending endurance and friction in both directions','cable preload, backlash, stretch and clamp holding force','PETG loaded deformation/creep and print fit','actual one-ball release and loaded return'],
        'manufacturing_release':False,'physical_acceptance':False,'sent_to_printer':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root',type=Path,default=DEFAULT_OUT)
    args=parser.parse_args()
    out=args.output_root.resolve()/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True,exist_ok=False)
    roots=[INPUT,OUTPUT,ROUTE,SPRING,ROOT/'cad/cable-trigger-system.scad']
    extra=[Path(__file__).resolve(),HELPER]
    before=source_hashes(roots,extra)
    try:
        result=analyze(out)
    except Exception as exc:
        result={'status':'CONTRACT_OR_SOURCE_REJECTED','error':str(exc),'error_type':type(exc).__name__,
                'manufacturing_release':False,'physical_acceptance':False}
    after=source_hashes(roots,extra)
    result.update(source_sha256=before,source_sha256_after=after,sources_stable=before==after,
                  source_hash_scope='All recursive static SCAD include/use dependencies from input/output/route/spring/system roots, plus both analysis scripts.',
                  output_directory=str(out),legacy_results_overwritten=False)
    if before!=after:
        result['status']='SOURCE_CHANGED_DURING_RUN_REJECTED'
    report=out/'report.json';report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'report':str(report),'sources_stable':result['sources_stable'],
                      'source_count':len(before),'error':result.get('error'),'rows':result.get('rows',[])},ensure_ascii=False))
    return 0 if result['status']=='IDEAL_DIRECT_PULL_CONTRACT_CHECKS_PASS' else 1


if __name__=='__main__':
    raise SystemExit(main())

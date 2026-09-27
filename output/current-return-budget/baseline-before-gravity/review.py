#!/usr/bin/env python3
"""Current nominal force/return boundaries. Read-only CAD, no physical claim."""
from pathlib import Path
from datetime import datetime, timezone
import csv, hashlib, json, math, re, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'analysis'))
from cable_direct_contract import DirectPullContract
from cable_actuation_budget import spring_catalog_literals

ACT=ROOT/'output/cable-actuation-v2/20260927T091604751038Z/report.json'
SELECT=ROOT/'output/feeder-return-spring/selection-contract.json'
SUPPLIER=ROOT/'output/feeder-return-spring/supplier-evidence.json'
SERVICE=ROOT/'output/feeder-return-spring/feeder-return-spring-service-report.json'
seen={}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def record(p,expected=None):
    p=Path(p);p=p if p.is_absolute()else ROOT/p
    key=str(p.relative_to(ROOT))if p.is_relative_to(ROOT)else str(p)
    h=sha(p)
    if expected is not None:assert h==expected,('Stale source/evidence',str(p))
    if key in seen:assert seen[key]==h,('Changed while reading',key)
    seen[key]=h;return h
def read(p):record(p);return json.loads(Path(p).read_text())
def dump(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def write_csv(path,rows):
    with Path(path).open('w')as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

class Budget:
    def __init__(self,model,F0,k,L0,Lrest,wire,Lmax,Fmax):
        self.model=model;self.F0=F0;self.k=k;self.L0=L0;self.Lrest=Lrest
        self.wire=wire;self.Lmax=Lmax;self.Fmax=Fmax;self.e0=Lrest-L0
    def spring(self,u,p=0):
        if not math.isfinite(u)or not 0<=u<=self.model.stroke:raise ValueError('Output work domain 0..20 only')
        if not math.isfinite(p)or self.e0+p<0:raise ValueError('Linear extension model requires installed extension >=0')
        return self.F0+self.k*(self.e0+p+u)
    @staticmethod
    def losses(eta,R,D,tau,H=0):
        if not all(math.isfinite(v)for v in [eta,R,D,tau,H])or not 0<eta<=1 or min(R,D,tau,H)<0:
            raise ValueError('Efficiency in (0,1]; named resisting loads finite and nonnegative')
    def pull(self,u,eta,R=0,D=0,tau=0,p=0):
        self.losses(eta,R,D,tau);s=self.model.state(u);A=s['effective_cable_arm_mm_per_rad'];B=s['finger_jacobian_mm_per_rad']
        return A/B*(D+(self.spring(u,p)+R)/eta)+tau/B
    def return_margin(self,u,eta,R=0,D=0,tau=0,H=0,p=0):
        self.losses(eta,R,D,tau,H);s=self.model.state(u);A=s['effective_cable_arm_mm_per_rad'];B=s['finger_jacobian_mm_per_rad']
        # A positive output surplus is also needed: the cable cannot push.
        available=self.spring(u,p)-R
        return {'output_spring_surplus_N':available,'input_torque_margin_Nmm':A*(eta*available-D)-tau-B*H,
            'returns_in_ideal_quasistatic_loss_model':available>0 and A*(eta*available-D)>tau+B*H}
    def catalog_extra_extension_bounds(self,stroke):
        maxext=self.Lmax-2*self.wire-self.L0
        return {'minimum_for_nonnegative_rest_extension_mm':-self.e0,
            'maximum_from_catalog_force_mm':(self.Fmax-self.F0)/self.k-self.e0-stroke,
            'maximum_from_conservative_overall_length_mm':maxext-self.e0-stroke,
            'maximum_from_stored_80percent_extension_guidance_mm':.8*maxext-self.e0-stroke}

def main():
    record(__file__)
    for p in ['analysis/cable_direct_contract.py','analysis/cable_actuation_budget.py','analysis/feeder_return_spring.py',
              'cad/cable-trigger-input.scad','cad/cable-output-interface.scad','cad/cable-housing-route.scad',
              'cad/feeder-return-spring.scad','docs/cable-trigger-input.md','docs/cable-trigger-integration.md','docs/feeder-return-spring.md']:
        record(p)
    act=read(ACT);selection=read(SELECT);supplier=read(SUPPLIER);service=read(SERVICE)
    assert act['status']=='IDEAL_DIRECT_PULL_CONTRACT_CHECKS_PASS'and act['sources_stable']
    for p,h in act['source_sha256'].items():record(p,h)
    spec=act['source_contract']['input'];co=act['source_contract']['output'];route=act['source_contract']['route']
    model=DirectPullContract(spec);cat=selection['spring'];literals=spring_catalog_literals()
    cross={'rs_spring_F0':'initial_tension_N','rs_spring_k':'rate_N_per_mm','rs_spring_L0':'free_inside_loop_length_mm',
        'rs_spring_Fmax':'maximum_load_N','rs_spring_Lmax':'catalog_maximum_extended_length_mm'}
    assert all(literals[k]['value']==cat[v]for k,v in cross.items())
    wire_literal=re.findall(r'^rs_wire\s*=\s*([.\d]+)\s*;', (ROOT/'cad/feeder-return-spring.scad').read_text(),re.M)
    assert len(wire_literal)==1 and float(wire_literal[0])==cat['wire_diameter_mm']
    b=Budget(model,cat['initial_tension_N'],cat['rate_N_per_mm'],cat['free_inside_loop_length_mm'],
        act['source_contract']['spring_length_rest'],cat['wire_diameter_mm'],cat['catalog_maximum_extended_length_mm'],cat['maximum_load_N'])
    assert co['stroke']==model.stroke==20 and spec['stop_setting']==20
    assert co['wire_force_direction']==[0,0,1]and co['t_domain']==[0,1]
    assert route['route_law']=='fixed-third-arc-equal-length-v1'and route['adjuster_delta']==model.delta
    us=np.linspace(0,model.stroke,2001);states=[model.state(float(u))for u in us]
    A=np.array([s['effective_cable_arm_mm_per_rad']for s in states]);B=np.array([s['finger_jacobian_mm_per_rad']for s in states])
    rho=A/B;Fs=np.array([b.spring(float(u))for u in us]);Fideal=rho*Fs
    rows=[]
    for u in [0,5,10,15,20]:
        s=model.state(u);aa=s['effective_cable_arm_mm_per_rad'];bb=s['finger_jacobian_mm_per_rad'];force=b.spring(u)
        rows.append({'stroke_mm':u,'angle_deg':s['angle_deg'],'finger_rearward_mm':s['finger_rearward_mm'],
            'spring_inside_eye_length_mm':b.Lrest+u,'spring_nominal_N':force,'cable_arm_mm':aa,
            'horizontal_finger_arm_mm':bb,'ideal_force_ratio':aa/bb,'ideal_spring_only_pull_N':aa/bb*force,
            'return_input_wire_budget_per_eta_N':force,'return_input_torque_budget_per_eta_Nmm':aa*force,
            'return_horizontal_finger_resistance_budget_per_eta_N':aa/bb*force})
    sensitivities=[]
    for eta in [.2,.4,.6,.8,1.]:
        for u in [0,5,10,15,20]:
            s=model.state(u);force=b.spring(u)
            sensitivities.append({'stroke_mm':u,'illustrative_efficiency_not_measured':eta,
                'pull_spring_only_with_this_eta_N':b.pull(u,eta),
                'return_input_side_wire_resistance_budget_N':eta*force,
                'return_input_bearing_torque_budget_Nmm':eta*force*s['effective_cable_arm_mm_per_rad'],
                'scope':'Other resisting loads zero; the three budgets cannot each be spent simultaneously.'})
    # Independent five-point checks against the previous native-source budget.
    prior_error=max(abs(b.spring(r['input_take_up_requested_mm'])-r['spring_force_catalog_nominal_N'])for r in act['rows'])
    service_error=max(abs(b.spring(r['stroke_mm'])-r['catalog_nominal_force_N'])for r in service['catalog_force_rows'])
    force_error=max(abs(b.pull(r['input_take_up_requested_mm'],1)-r['finger_force_spring_only_N'])for r in act['rows'])
    theta_max=math.radians(states[-1]['angle_deg'])
    # On this equal-radius tangent branch, 0<=phi'<=1 and beta=theta-phi
    # lies in [0,theta]. Therefore A'= -tan(beta)(1-phi') >=-tan(theta_max).
    torque_monotonic_lower=float(b.k*model.R*math.cos(theta_max)-Fs[-1]*math.tan(theta_max))
    assert torque_monotonic_lower>0
    checks={'source_catalog_literals_agree':True,'five_point_force_budget_agrees':max(prior_error,service_error,force_error)<1e-10,
        'positive_geometric_cable_and_horizontal_finger_arms':bool(min(A.min(),B.min())>0),
        'positive_analytic_arm_lower_bound_on_entire_solve_domain':model.monotonic_arm_lower_bound>0,
        'nominal_return_torque_increases_analytic_bound':torque_monotonic_lower>0,
        'nominal_work_stroke_catalog_limits':b.catalog_extra_extension_bounds(model.stroke)['maximum_from_stored_80percent_extension_guidance_mm']>=0,
        'zero_loss_return_positive_all_samples':all(b.return_margin(float(u),1)['returns_in_ideal_quasistatic_loss_model']for u in us)}
    # A boundary is strict; equality is equilibrium, never assured restart.
    boundary_controls=[]
    for u in [0,10,20]:
        s=model.state(u);critical=.6*b.spring(u)*s['effective_cable_arm_mm_per_rad']
        at=b.return_margin(u,.6,tau=critical)['input_torque_margin_Nmm']
        beyond=b.return_margin(u,.6,tau=critical+1e-6)
        boundary_controls.append({'u':u,'eta_hypothetical':.6,'zero_margin_at_critical_torque':abs(at)<1e-10,
            'added_resistance_rejects_return':not beyond['returns_in_ideal_quasistatic_loss_model']})
    assert all(all(v for k,v in row.items()if isinstance(v,bool))for row in boundary_controls)
    rejected=[]
    for label,args in [('zero-efficiency',(0,0,0,0)),('above-unit-efficiency',(1.01,0,0,0)),('negative-resistance',(.8,-1,0,0))]:
        try:b.losses(*args)
        except ValueError:rejected.append(label)
    assert len(rejected)==3
    stops=[]
    for U in [16,18,20,22]:
        s=model.state(U)
        stops.append({'input_stop_requested_mm':U,'input_angle_deg':s['angle_deg'],'finger_rearward_mm':s['finger_rearward_mm'],
            'ideal_requested_output_mm':U,'short_of_20_mm':max(0,20-U),'excess_input_after_output_hard_stop_mm':max(0,U-20),
            'output_work_domain_respected':U<=20,'reaches_full_work_stroke_without_loss':U==20,
            'meaning':'16..22 is the input adjustment domain. Rows above20 do not extend the output system validation domain.'})
    zero_changes=[]
    for delta in [-2,0,2]:
        zero_changes.append({'M6_delta_change_mm':delta,'input_absolute_path_change_mm':-delta,
            'ideal_output_offset_at_input_zero_if_core_stays_taut_mm':-delta,
            'consequence':'2mm slack/lost travel and no guaranteed final input return'if delta>0 else
                          'Output held2mm off zero / cable interference with simultaneous rest datums'if delta<0 else'Nominal coordinated zero',
            'conditions':'Equal outside-route length and unchanged ferrule seating; output clamp not reset. This is a sensitivity identity, not an installation instruction.'})
    total_bend_deg=sum(a[5]for a in route['arcs'])
    report={'status':'CURRENT_RETURN_PARAMETRIC_BOUNDARIES_CALCULATED_PHYSICAL_RETURN_OPEN','created_utc':datetime.now(timezone.utc).isoformat(),
        'input_actuation_report':str(ACT.relative_to(ROOT)),'spring_catalog_selection':cat,
        'procurement_state':supplier['procurement_state'],'checks':checks,'boundary_negative_controls':boundary_controls,'domain_rejections':rejected,
        'work_domain_mm':[0,20],'assumptions':['Quasistatic taut inextensible core on the validated forward guide branch; housing end seats do not move.',
            'Catalog linear spring model F0+k*extension; actual force/rate/initial tension are not measured.',
            'Each direction has its own load-dependent efficiency; direction efficiencies need not be equal.',
            'R is output-side resisting force excluding spring; D is additional input-side wire-equivalent drag not already in eta; tau is input pivot resisting torque; H is residual horizontal finger resistance.',
            'Do not count the same cable/guide loss both in eta and D. Dynamic inertia, impact, hysteresis, jam loads and compliance are not solved.'],
        'definitions':{'u':'output stroke mm','theta':'input rotation rad','A':'du/dtheta, mm/rad','B':'dx_finger/dtheta, mm/rad','rho':'A/B',
            'Fs':'F0+k*(Lrest-L0+p+u), N','p':'Hypothetical extra spring installed extension; NOT the M6 cable adjustment and not an implemented independent preload control.'},
        'formulas':{'pull_horizontal_N':'rho * (D_pull + (Fs + R_pull)/eta_pull) + tau_pull/B',
            'return_torque_margin_Nmm':'A * (eta_return*(Fs - R_return) - D_return) - tau_return - B*H',
            'return_required':'Fs>R_return AND torque_margin>0 at EVERY stroke position; equality does not guarantee breakaway.',
            'return_R_output_upper_N':'Fs - (D_return + tau_return/A + H/rho)/eta_return',
            'return_eta_lower':'(D_return + tau_return/A + H/rho)/(Fs-R_return), provided Fs>R_return; eta must strictly exceed this and be <=1.',
            'preload_extra_extension_lower_mm':'sup_u[(R_return + (D_return+tau_return/A+H/rho)/eta_return - Fs_at_p0)/k]',
            'preload_extra_extension_upper_from_user_force_limit_mm':'inf_u[(eta_pull*((F_limit-tau_pull/B)/rho-D_pull)-R_pull-Fs_at_p0)/k]',
            'preload_feasible_interval':'p>=-e0; p strictly above return lower bound; p<=all catalog upper bounds and any supplied finger-force upper bound. Empty interval means those supplied demands are incompatible.'},
        'stroke_table':rows,'efficiency_sensitivity':sensitivities,
        'continuous_domain_findings':{'nominal_geometric_dead_point':False,
            'analytic_cable_arm_lower_mm_full_0_to_30deg_solve_domain':model.monotonic_arm_lower_bound,
            'analytic_finger_arm_lower_mm_full_0_to_30deg_solve_domain':model.finger_R*math.cos(math.radians(model.angle_domain[1])),
            'sampled_work_stroke_cable_arm_range_mm':[float(A.min()),float(A.max())],
            'sampled_work_stroke_finger_arm_range_mm':[float(B.min()),float(B.max())],
            'sampled_work_stroke_force_ratio_range':[float(rho.min()),float(rho.max())],
            'derivative_lower_bound_for_A_times_Fs_N':float(torque_monotonic_lower),
            'conditional_weakest_return_position':'u=0 for constant nonnegative R,D,H,tau and constant eta. With position-dependent friction/ball loads/efficiency the full pointwise condition is necessary; no endpoint-only actual guarantee.',
            'proof':'0<=phi_prime<=1 and0<=beta<=theta imply dA/du>=-tan(theta_max); d(A*Fs)/du>=k*R*cos(theta_max)-Fs_max*tan(theta_max)>0. A and B are nonincreasing, so subtracting constant nonnegative A*(eta*R+D) and B*H cannot create a weaker endpoint.'},
        'nominal_zero':{'spring_extension_mm':b.e0,'spring_force_N':b.spring(0),
            'return_output_force_budget_before_transmission_N':b.spring(0),
            'input_wire_drag_budget_N':'2.975*eta_return only when other resisting loads are zero',
            'input_pivot_torque_budget_Nmm':'178.5*eta_return only when other resisting loads are zero',
            'horizontal_finger_resistance_budget_N':'4.958333333333333*eta_return only when other resisting loads are zero'},
        'catalog_extra_spring_extension_bounds_at_20mm':b.catalog_extra_extension_bounds(20),
        'catalog_limits_note':'The stored supplier evidence uses maximum extended length conservatively as overall and subtracts2 wire diameters; the stored80% extension guidance is not a measured life/strength allowance.',
        'preload_control_limit':'Current spring anchor datums are fixed. Additional p is a sensitivity variable, not permission to shift anchors. Tightening the core adjuster cannot independently increase spring return force while keeping both rest datums at zero.',
        'input_stop_cases':stops,'M6_without_output_zero_reset':zero_changes,
        'stop_compatibility':{'current_nominal':'Input20/output20 coincide only with coordinated taut zero and zero incremental loss.',
            'with_lost_travel':'For nonnegative net lost travel ell, requested output=max(0,U-ell). Full20 at ell_max needs U>=20+ell_max; avoiding input overpull against output hard stop at ell_min needs U<=20+ell_min.',
            'incompatibility':'If ell_max>ell_min no fixed input stop can satisfy both demands exactly without a separately validated allowance/load limiter or a relaxed endpoint target. Output hard stop prevents travel, but continued pull then creates unbudgeted load, not extra useful stroke.',
            'no_loss_stop_22':'2mm extra input demand after output20 is not allowed output stroke; no spring/strength evaluation of that overpull is claimed.',
            'slack_return':'If core slack appears before input zero, output spring cannot push the core to complete the final input return. There is no separate input return spring.'},
        'route_loss_context':{'route_length_between_outer_ports_mm':route['outside_port_route_length'],
            'nominal_housing_total_absolute_bend_deg':total_bend_deg,'nominal_housing_total_absolute_bend_rad':math.radians(total_bend_deg),
            'bare_guide_contact_angle_deg_at_full':states[-1]['guide_contact_angle_deg'],
            'interpretation':'Geometric bend only. No friction coefficient, capstan efficiency, additive drag or stability of the two free housing bends is inferred.'},
        'physical_inputs_still_needed':['Actual selected spring force versus installed length, including initial tension and hysteresis.',
            'Output-side breakaway/drag versus stroke with the intended balls and airflow state; sign/orientation-dependent gravity can be included as resisting load.',
            'Forward and reverse input/output cable force transfer, with actual ferrule seats, route and guide; or an equivalent measured loss envelope, avoiding double counting.',
            'Input bearing breakaway torque after assembly, core slack/compliance and stop/zero repeatability.',
            'Permitted user finger force and proven cable/clamp/printed load capacities; none has been invented.'],
        'manufacturing_release':False,'physical_acceptance':False,'sent_to_printer':False}
    fig,axs=plt.subplots(1,3,figsize=(15,4.6),layout='constrained')
    axs[0].plot(us,Fs,label='Catalog spring');axs[0].plot(us,Fideal,label='Ideal horizontal pull')
    axs[0].set(xlabel='Output stroke / mm',ylabel='Force / N',title='Nominal force (no loss)');axs[0].legend();axs[0].grid(alpha=.2)
    for eta in [.2,.4,.6,.8,1]:axs[1].plot(us,Fideal/eta,label=f'eta={eta:g}')
    axs[1].set(xlabel='Output stroke / mm',ylabel='Horizontal pull / N',title='Efficiency parameter sweep\nOther drag and pivot torque zero');axs[1].legend();axs[1].grid(alpha=.2)
    etas=np.linspace(0,1,201);rs=np.linspace(0,b.spring(0),201);rr,ee=np.meshgrid(rs,etas);q=ee*(b.spring(0)-rr)
    im=axs[2].pcolormesh(rr,ee,q,shading='auto',cmap='viridis');fig.colorbar(im,ax=axs[2],label='Input wire-equivalent budget q / N')
    axs[2].set(xlabel='Output resisting force at zero / N',ylabel='Reverse efficiency eta',title='Zero-position strict return boundary\nq = D + tau/60 + H/(5/3) must be BELOW budget')
    fig.suptitle('Current direct-pull v2: symbolic loss budget, not measured return performance',fontsize=13)
    fig.savefig(OUT/'budget.png',dpi=160);plt.close(fig)
    write_csv(OUT/'stroke-table.csv',rows);write_csv(OUT/'efficiency-table.csv',sensitivities)
    stable=all(sha(ROOT/k if not k.startswith('/')else Path(k))==h for k,h in seen.items());assert stable
    report.update(source_sha256=seen,sources_stable=stable,figure={'file':'output/current-return-budget/budget.png','sha256':sha(OUT/'budget.png')})
    dump(OUT/'report.json',report)
    print(json.dumps({'status':report['status'],'checks':checks,'sources_stable':stable,'nominal_zero':report['nominal_zero'],
        'preload_bounds':report['catalog_extra_spring_extension_bounds_at_20mm'],'torque_monotonic_lower':torque_monotonic_lower},ensure_ascii=False,indent=2))
if __name__=='__main__':main()

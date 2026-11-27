#!/usr/bin/env python3
"""One final substitution of existing compatible outer bounds. No new CAD work."""
from pathlib import Path
from fractions import Fraction as F
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'analysis'))
from frame_y_guide_bound import upper as up, lower as down, sqrt_lower as sl
def q(v):return F(str(v))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def conv(v):
    if isinstance(v,F):return float(v)
    if isinstance(v,dict):return{k:conv(x)for k,x in v.items()}
    if isinstance(v,(list,tuple)):return[conv(x)for x in v]
    return v

paths={k:f'output/current-joint-tolerance/{n}/report.json' for k,n in {
    'yaw':'common-frame-yaw','pin':'correlated-pin-window',
    'cam':'common-cam-intersection','phase':'common-phase-registration'}.items()}
r={k:json.loads((ROOT/p).read_text())for k,p in paths.items()}
assert r['yaw']['status']=='CONDITIONAL_COMMON_FRAME_YAW_STRICTLY_TIGHTENED_ONLY'
assert r['pin']['status']=='STRICTLY_TIGHTER_SAME_PIN_WINDOW_COMBINATION_NOT_FULL_BX'
assert r['phase']['status']=='CONDITIONAL_COMMON_REFERENCE_PHASE_FINITE_BOUND_NOT_FULL_BX'
files={Path(__file__),*(ROOT/p for p in paths.values())}
expected={}
for key in ['yaw','pin','phase']:
    for p,h in r[key]['source_hashes'].items():
        assert p not in expected or expected[p]==h,('incompatible current source identity',p)
        assert sha(ROOT/p)==h,('current source changed',p)
        expected[p]=h;files.add(ROOT/p)
# Record the limited human-read scope separately from recursive byte checks.
human_full_read=['output/current-joint-tolerance/common-frame-yaw/README.md',
                 'output/current-joint-tolerance/common-frame-yaw/review.py']
for p in human_full_read:files.add(ROOT/p)
before={str(p.relative_to(ROOT)):sha(p)for p in sorted(files)}

y=r['yaw']['numeric'];cam=r['cam'];pin=r['pin'];phase=r['phase']
xy=q(y['new_shared_Qxy_abs_upper']);yx=q(y['new_each_support_Qyx_abs_upper'])
xz=q(y['old_shared_Qxz_abs_upper_reused']);m=F('.625')
# Exact unit row, with Qxx>0 from the inherited normal-angle branch.
# No iteration or use of this result to establish yaw's own prerequisites.
xx=sl(1-xy*xy-xz*xz)
S=q(cam['radial_elimination']['S32_upper_mm'])
limit=q(cam['radial_elimination']['original_J_required_upper_mm'])
assert S+limit==1
gain=up(m/xx)
rows={}
for side in ['right','left']:
    fr=cam['finite_frame_proof']['rows'][side]
    M={k:q(v)for k,v in fr['matrix_abs_upper'].items()}
    oldxx=q(fr['matrix_diagonal_lower'][0])
    assert xy<M['xy'] and yx<M['yx'] and xx>oldxx and xz==M['xz']
    pmy=cam['same_pin_midplane_intersections'][side]['same_intersection_support_Y_interval_mm']
    yr=max(abs(q(v)-22)for v in pmy)
    old={k:q(v)for k,v in cam['radial_elimination']['rows'][side]['same_joint_identity_terms_upper_mm'].items()}
    terms={k:v for k,v in old.items() if k not in ['same_carrier_pin_X_offset','same_window_to_midplane_Z']}
    terms['frame_XX_scale']=up((1-xx)*15)
    terms['combined_frame_Y_coefficient']=up((yx+m*M['yz'])*yr)
    terms['same_pin_window_combined_G']=q(pin['rows'][side]['combined_G_numerator_abs_upper_mm'])
    correction=up(S*(1/xx-xx))
    j0=up(sum(terms.values())/xx+correction)
    lam=q(phase['numeric']['all_active_side_Lambda_phase_upper_mm'][side])
    with_phase=up(j0+gain*lam)
    previous=q(pin['rows'][side]['J0_after_only_this_valid_substitution_upper_mm'])
    assert j0<previous and j0>limit and with_phase>=j0
    rows[side]={
        'old_Qxx_lower':oldxx,'new_Qxx_lower':xx,
        'retained_Qyz_abs_upper':M['yz'],'retained_DeltaYr_abs_upper_mm':yr,
        'new_numerator_terms_upper_mm':terms,
        'eta_forward_inverse_conversion_upper_mm':correction,
        'J0_before_yaw_substitution_upper_mm':previous,
        'J0_combined_upper_mm':j0,'phase_gain_upper':gain,
        'conditional_formula':'J_i <= J0_i + phase_gain * Lambda_i on the SAME declared domain.',
        'inherited_same_domain_Lambda_upper_mm':lam,
        'J_outer_with_inherited_finite_phase_upper_mm':with_phase,
        'target_upper_mm':limit,
        'J0_excess_over_target_mm':up(j0-limit),
        'certifies_J_even_if_Lambda_zero':False,
        'attainable_extreme_or_physical_failure_claimed':False,
    }

result={
    'status':'FINAL_COMPATIBLE_OUTER_BOUND_COMBINATION_INSUFFICIENT_TO_CERTIFY_BX',
    'source_hashes':before,
    'inputs':paths,
    'substitutions':{
        'Qxy_abs_upper':xy,'Qyx_abs_upper':yx,'Qxz_abs_upper_retained':xz,
        'Qxx_lower':xx,
        'Qxx_derivation':'Qxx positive on inherited normal branch; Qxx^2=1-Qxy^2-Qxz^2 from the SAME rotation row. Directed lower sqrt gives the displayed bound. Both sides share Qxx.',
        'changed_terms':['frame_XX_scale=(1-Qxx_lower)*15',
                         'combined_frame_Y_coefficient=(Qyx_bound+.625*old_Qyz_bound)*old_DeltaYr_bound',
                         'division_by_Qxx_and_eta_conversion',
                         'phase_gain=.625/Qxx_lower'],
        'retained':'Correlated G bound, actual yM/yW intersections, finite material/normal branch proofs, other matrix entries, registration residuals, same reference/zero phase bounds, and all physical conditions remain as previously bounded.',
        'no_new_local_chain':True,
    },
    'domain_compatibility':[
        'All inputs use one rigid common C and the same installed H/S_i; seated split/mount X planes and Rx/YZ registration. The canonical left mirror flips X only. Yaw shrinks that same domain rather than selecting an independently favourable pose.',
        'Both guide dprime.Y remain in[0,.1] under the same effective parallel gaps and finite contact branch. Old intersection and material bounds stay valid on the smaller yaw domain and are not recomputed.',
        'G retains the same carrier R and actual pin line P across nut, finite V, Y7 window and real cam mid-plane. Its proof used broader prior Q bounds; it is still a universal bound on this subset.',
        'Lambda retains the same explicit integral output-ear point and same N-axis displacement from C0 with at least one actual zero-stop contact. Its older angle outer remains valid; it is not set zero or replaced by CAD translation.',
        'Radial20..27 guard, maintained loaded contacts, nominal thread coaxiality, rigid shapes and actual unmeasured fabrication/load terms remain conditions. Combining necessary outer bounds does not establish feasible full-domain trajectories or close the guard.',
    ],
    'rows':rows,
    'reading_and_change_audit':{
        'full_text_reread_this_final_merge':human_full_read,
        'reused_previously_reviewed_logic':[
            'correlated-pin-window/review.py exact G decomposition, projection bound and final numerator substitution',
            'common-cam-intersection/review.py radial() and exact_radial_numerator',
            'common-phase-registration exact common reference and single-active-zero phase contract'],
        'parsed_current_report_fields':{
            'yaw':['numeric','coordinate_contract','proof_conditions','source_hashes'],
            'pin':['rows','exact_local_combination','domain_conditions','source_hashes'],
            'cam':['finite_frame_proof.rows','same_pin_midplane_intersections','radial_elimination'],
            'phase':['numeric.all_active_side_Lambda_phase_upper_mm','domain_conditions','source_hashes','historical_source_audit']},
        'recursive_dependencies':'Byte hashes checked; not claimed to have manually reread every CAD or historical report in this final merge. No CAD execution or export.',
        'historical_changes':[x for x in phase['historical_source_audit'] if x['status']!='INHERITED_BYTES_MATCH'],
        'unchanged_historical_dependency_count':sum(x['status']=='INHERITED_BYTES_MATCH' for x in phase['historical_source_audit']),
        'historical_scope':'The previously identified three input/route/export changes remain explicitly excluded from the local constraint reuse; 47 inherited files are unchanged. This merge does not re-sign old full-system reports.',
        'existing_source_files_modified_by_this_stage':[],
        'new_outputs_only':'output/current-joint-tolerance/current-combined-assessment/',
    },
    'conclusion':'现有这些独立外包方法不足：合并后即使相位项取零也不能认证J<=0.602876731024。没有可实现失败姿态，因此不能据此宣称实物故障。本阶段到此停止。',
    'actual_F_H_lost_motion_stop_error':None,
    'phase_reference_alignment_certified':False,
    'current_common_Bx_certified':False,'full_D02_closed':False,
    'manufacturing_release':False,'physical_acceptance':False,
    'method':'One algebraic substitution, Fraction and directed1e-12 bounds. No new geometry, phase proof, local optimization or sampled extrema.',
    'all_sources_stable':all(sha(ROOT/p)==h for p,h in before.items()),
}
assert result['all_sources_stable']
(OUT/'report.json').write_text(json.dumps(conv(result),ensure_ascii=False,indent=2)+'\n')
print(json.dumps(conv({'status':result['status'],'source_count':len(before),
                       'Qxx_lower':xx,'rows':rows,'all_sources_stable':result['all_sources_stable']}),ensure_ascii=False,indent=2))

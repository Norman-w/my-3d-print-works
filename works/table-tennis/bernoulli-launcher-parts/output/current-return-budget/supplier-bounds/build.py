#!/usr/bin/env python3
"""Bounded, offline evidence binding. Does not perform measurements or CAD work."""
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

fields = [
    ('record_id','string','助手分配的记录编号'),
    ('configuration_id','string','实际装配配置编号，不是仅有CAD名'),
    ('assembly_source_sha256','sha256','该配置源身份，由助手填写'),
    ('route_identity','string','实际护套路线、端套和调节器设置的记录身份'),
    ('spring_specimen_id','string','同一实际弹簧编号及型号'),
    ('cable_specimen_id','string','同一实际拉索编号及型号'),
    ('orientation_id','string','同一持握姿态记录身份'),
    ('gravity_cad_unit_x','number','实测姿态下重力CAD单位向量X'),
    ('gravity_cad_unit_y','number','实测姿态下重力CAD单位向量Y'),
    ('gravity_cad_unit_z','number','实测姿态下重力CAD单位向量Z'),
    ('ball_state','string','实际球载状态，首次为empty'),
    ('air_state','string','实际风状态，首次为off-unpowered'),
    ('output_u_mm','number','相对于实际输出零位的位置mm'),
    ('output_u_uncertainty_mm','nonnegative','配对位置区间半宽mm；力误差还须覆盖该区间'),
    ('spring_force_min_N','number','同朝向、同针距实测回缩端力最小值N，不是名义值'),
    ('spring_force_uncertainty_N','nonnegative','弹簧力绝对不利误差界N，包含位置配对影响'),
    ('chain_return_force_max_N','number','整链拆弹簧后的实测回程起动/运行外力最大值N'),
    ('chain_force_uncertainty_N','nonnegative','整链力绝对不利误差界N，包含位置配对影响'),
    ('fixture_unincluded_adverse_bound_N','nonnegative','未已计入测量误差的工装/失配可能助推回程的校正上界N；未知不能填0'),
    ('spring_trials','positive_integer','该条件弹簧实測重复次数'),
    ('chain_trials','positive_integer','该条件整链实測重复次数'),
    ('dwell_s','nonnegative','起动前实际驻留秒数'),
    ('quasistatic_speed_mm_s','positive','实际回程测量速度mm/s'),
    ('core_taut','boolean','实测区间线芯保持张紧；CSV用true/false'),
    ('fixture_matches_spring_line','boolean','外力通过原挂点且与原弹簧力线一致；CSV用true/false'),
    ('spring_trace_ref','evidence_path','弹簧原始曲线/录像和仪表误差依据'),
    ('chain_trace_ref','evidence_path','整链原始曲线/录像、实际姿态/载荷和工装误差依据'),
    ('observer','string','实际记录者或可追溯记录身份'),
    ('timestamp_utc','datetime','实际测量UTC时间；不由报告生成时刻冒充'),
]

sources = [
    'output/current-return-budget/README.md',
    'output/current-return-budget/report.json',
    'output/cable-actuation-v2/20260927T091604751038Z/report.json',
    'output/feeder-return-spring/selection-contract.json',
    'output/feeder-return-spring/supplier-evidence.json',
    'output/feeder-return-spring/lee-extension-catalogue.pdf',
    'output/current-cable-supplier-closure/report.json',
    'output/current-cable-supplier-closure/reviewed-official-evidence.json',
    'cad/feeder-return-spring.scad',
]
start = {p:sha(ROOT/p) for p in sources}
schema = {
    'schema_version':1,
    'file':'paired-return.csv',
    'actual_measurement_required':True,
    'entry_owner':'Assistant/script fills identity, paths and normalization; person provides readings/traces, distances and actual posture/load state.',
    'fields':[{'name':n,'type':t,'required':True,'description':d} for n,t,d in fields],
    'all_numeric_rows_must_be_actual_measurements':True,
    'blank_or_nominal_must_not_pass':True,
    'negative_chain_force':'A measured assisted return is permitted; upper requirement clips at zero. Slack gauge zero is not proof of assisted return.',
    'paired_condition_requirement':'Same specimen, configuration, route, actual pose, u uncertainty interval and associated ball/air state. Spring test reproduces actual pin geometry/orientation; identity fields alone do not prove this.',
    'measurement_error_requirement':'Force bounds must include instrument, alignment, zero drift, attachment gravity and u interval effects, or separately bound remaining favorable fixture effects; no assumed CAD slope.',
    'formula':{
        'S_lower_N':'spring_force_min_N - spring_force_uncertainty_N',
        'Q_upper_N':'max(0, chain_return_force_max_N + chain_force_uncertainty_N) + fixture_unincluded_adverse_bound_N',
        'margin_N':'S_lower_N - Q_upper_N',
        'positive_status':'SAMPLE_POSITIVE_MARGIN only if margin_N > 0 and all evidence/identity/tautness guards pass',
    },
    'overall_pass_from_finite_samples':False,
    'release_video_requirement':'Separately retain refitted spring free-return video at measured starts, observing both input and output zero; table margin alone is not release acceptance.',
    'no_repeated_gravity_or_eta_deduction':True,
}
write_json(OUT/'measurement-schema.json',schema)
table = OUT/'paired-return.csv'
if not table.exists():
    with table.open('w',newline='') as f:
        csv.writer(f).writerow([n for n,_,_ in fields])
with table.open(newline='') as f:
    reader=csv.DictReader(f)
    if reader.fieldnames != [n for n,_,_ in fields]:
        raise ValueError('Existing measurement CSV schema differs; never overwrite measurements.')
    rows=list(reader)

evidence = {
    'review_date':'2026-09-27',
    'method':'Read existing evidence first, then bounded official website/PDF lookup for selected 03096-14 and LEM063CA03M. No supplier contact or purchase.',
    'official_sources':[
        {
            'id':'lee-selected-catalogue',
            'url':'https://www.leespring.co.uk/sites/default/files/2020-01/Extension_Springs_Lee_Spring_UK_Eng.pdf',
            'scope':'Printed pages165,177; local PDF pages1,13 visually inspected.',
            'retrieval':'Official web PDF text retrieved; local prior download with bound SHA used for both inspected renders. Remote page13 screenshot timed out.',
            'facts':{'model':'LEM063CA 03 M','material':'music wire, plated','initial_tension_nominal_N':1.67,'rate_nominal_N_per_mm':0.25,'free_length_inside_hooks_nominal_mm':25.6,'OD_nominal_mm':7,'wire_d_nominal_mm':0.63,'maximum_catalogue_load_N':12.2,'maximum_extended_overall_length_mm':67.21,'loop_position':'INLINE','DIN_note':'DIN2097 design parameters'},
            'force_tolerances_for_selected_part':None,
        },
        {
            'id':'lee-general-tolerances',
            'url':'https://www.leespring.co.uk/engineering-notes-and-tolerances',
            'locator':'Stock Extension Outside Diameter (OD) Tolerances*; web extracted lines267..294',
            'short_quote':'Spring rate: ± 10%',
            'facts':'General extension section publishes rate +/-10%. DIN2097/MIL-SPEC footnote is tied to starred OD heading. Do not claim the footnote unambiguously exempts spring rate; do not transfer rate tolerance to F0.',
            'initial_tension_tolerance':None,'selected_free_length_tolerance':None,
            'usable_combined_force_lower_bound':None,
        },
        {
            'id':'norelem-selected-family',
            'url':'https://www.norelemusa.com/en-us/Product-Overview/Flexible-standard-component-system/03000/Accessory-for-indexing-plungers-cam-action-indexing-plungers-and-ball-lock-pins/Bowden-cables-for-indexing-plungers-with-remote-actuation/p/agid.32096',
            'locator':'Description / Note, extracted lines48..63',
            'facts':'03096-14 transfers pulling force; shortening permitted; free end depends on routing/load and needs readjustment; R>=65 including installation; sheath compression-only.',
            'minimum_efficiency':None,'startup_drag_N':None,'running_drag_N':None,'directional_loss_curve':None,
            'retrieval':'Official web text read; current Downloads exposed no usable PDF link to browser extractor.',
        },
    ],
    'limited_queries':['LEM063CA 03 M initial tension tolerance / exact product','03096-14 friction efficiency / official datasheet'],
    'access_limits':['Exact guessed selected Lee product endpoint and filtered product search were not accessible through web tool. No assertion that every supplier/private document was inspected.'],
    'excluded_substitutions':['Different Lee spring product initial-tension tolerances','norelem05596-01 1000N tensile rating is another product and is not a drag/efficiency bound','R65 and total bend angle cannot establish transmission efficiency'],
}
write_json(OUT/'reviewed-official-evidence.json',evidence)
spring=json.loads((ROOT/'output/feeder-return-spring/selection-contract.json').read_text())['spring']
nominal=[{'u_mm':u,'nominal_pin_distance_mm':26.82+u,'nominal_spring_force_N':round(spring['initial_tension_N']+spring['rate_N_per_mm']*(5.22+u),6),'measurement':False} for u in [0,5,10,15,20]]
checks={
    'selected_model_matches':'LEM063CA 03 M'==spring['model'],
    'catalogue_nominals_match':spring['initial_tension_N']==1.67 and spring['rate_N_per_mm']==.25 and spring['free_inside_loop_length_mm']==25.6,
    'known_nominal_forces_preserved':[r['nominal_spring_force_N'] for r in nominal]==[2.975,4.225,5.475,6.725,7.975],
    'schema_has_no_overall_sample_pass':not schema['overall_pass_from_finite_samples'],
    'do_not_populate_measurement_rows':len(rows)==0,
}
end={p:sha(ROOT/p) for p in sources}
checks['sources_stable']=start==end
artifacts=['build.py','README.md','measurement-protocol.md','measurement-schema.json','paired-return.csv','reviewed-official-evidence.json','evidence/lee-guide-p165.png','evidence/lee-selected-p177.png']
report={
    'status':'OFFICIAL_NOMINALS_CONFIRMED_RETURN_FORCE_BOUNDS_OPEN',
    'generated_at_utc':datetime.now(timezone.utc).isoformat(),
    'scope':'Supplier facts and future formal-component measurement protocol only; not a force test or physical release.',
    'supplier_model_identity':{'spring':'Lee Spring LEM063CA 03 M','bowden_kit':'norelem03096-14-1000'},
    'published_nominal_force_table':nominal,
    'unknown_bounds':{'eta_return_min':None,'eta_pull_min':None,'cable_startup_drag_N':None,'cable_running_drag_N':None,'spring_F0_lower_N':None,'spring_force_actual_lower_curve':None,'R_actual':None,'D_actual':None,'tau_actual':None},
    'general_rate_tolerance_publication':{'relative':.10,'selected_combined_Fs_bound_derived':False,'reason':'F0 and selected free-length bounds missing even if the generic rate tolerance is applicable.'},
    'closure_options':[
        'Supplier acceptance for same model/route/loading and directional startup/running curves; exact spring F0/k/free length or force-at-length bounds.',
        'Formal actual-component matched spring-force and whole-chain return-force measurement per protocol; do not infer eta.',
    ],
    'actual_measurement_rows':len(rows),'measurement_performed':False,'physical_release':False,
    'measurement_schema_file':'measurement-schema.json','measurement_csv':'paired-return.csv',
    'source_sha256_at_start':start,'source_sha256_at_end':end,'source_stable':start==end,
    'artifact_sha256':{a:sha(OUT/a) for a in artifacts},'checks':checks,
    'not_performed':['CAD change/export','main budget rewrite','procurement/cart/contact','print test coupon','overvoltage or powered test','mass/gravity model duplication','invented friction/efficiency','continuous-domain claim from finite samples'],
}
write_json(OUT/'report.json',report)
if not all(checks.values()):
    raise SystemExit('Evidence/schema checks did not pass; inspect report.')
print(json.dumps({'status':report['status'],'actual_measurement_rows':len(rows),'checks':checks,'report_sha256':sha(OUT/'report.json')},ensure_ascii=False))

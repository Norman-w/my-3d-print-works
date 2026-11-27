"""Bounded clamp/locking calculation; no CAD edits, no torque recommendation."""
from pathlib import Path
import math, json, hashlib, datetime

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
paths = [
    'output/current-axis-offset-candidate/candidate.scad',
    'output/current-axis-centering-washer/candidate.scad',
    'output/current-axis-centering-washer/runs/20260927T133352450356Z/report.json',
    'output/current-axis-root-interface/supplier/report.json',
]
area = math.pi * (7.8**2-7.0**2)/4
angle = math.radians(.2)
area_projected = area*math.cos(angle)
fibro = {
    'family':'FIBRO 244.17, h8 shoulder diameter',
    'configured_candidate':'244.17.H8.080.030',
    'legacy_h8_ordering':'244.17.080.030',
    'h8_suffix_evidence':'2025-07 official chapter search index; live download 404 retained',
    'shoulder_diameter_mm':[7.978,8.0],
    'diameter_limit_status':'h8 interpreted with ISO diameter step >6..10; h8 is explicit in downloaded original sheet',
    'shoulder_length_mm':[30,30.25],
    'thread':'M6', 'thread_length_nominal_mm':11,
    'head_nominal_diameter_mm':13, 'head_nominal_height_mm':5.5,
    'hex_key_nominal_mm':4,
    'catalogue_tightening_torque_Nm':13,
    'torque_is_current_cup_joint_instruction':False,
    'head_root_envelope_known':False, 'tail_root_envelope_known':False,
    'material':'heat treated high tensile steel, class 12.9 ISO 898-1; not A2 stainless',
    'suggested_new_cup_design_only':{
        'pilot_depth_mm':[3.50,3.55], 'total_thickness_mm':[5.95,6.05],
        'pilot_diameter_mm':[8.02,8.03],
        'metal_thickness_mm':[5.95-3.55,6.05-3.50],
        'capture_span_mm':[30-3.55,30.25-3.50],
        'float_if_actual_shell_span_26_mm':[30-3.55-26,30.25-3.50-26],
        'old_pilot_eccentricity_bound_if_other_old_conditions_hold_mm':(8.04-7.978)/2+.010+2.60*math.tan(angle),
        'new_pilot_eccentricity_bound_if_other_old_conditions_hold_mm':(8.03-7.978)/2+.010+2.60*math.tan(angle),
        'straight_engagement_assumed_mm':3.40,
        'tilt_ceiling_from_clearance_alone_deg':math.degrees(math.atan((8.03-7.978)/3.40)),
        'clearance_alone_proves_point_2_deg':False,
        'nominal_physical_tail_projection_using_11mm_only_mm':[11-2.55-6,11-2.40-5.7],
        'full_thread_or_nylon_engagement_proven':False,
        'prototype_or_adopted':False,
    },
}
report = {
    'schema':'axis-locking-load-review/v1',
    'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status':'METAL_CLAMP_PATH_DEFINED_TORQUE_FORCE_WINDOW_NOT_CLOSED',
    'source_sha256':{s:sha(ROOT/s) for s in paths},
    'metal_clamp_loop':['M6 nut','CW-01 rear bearing face','cup web','cup floor annulus','integral shaft tail shoulder','integral threaded tail','M6 nut'],
    'petg_is_in_metal_preload_loop':False,
    'geometry':{'annulus_mm':[7.0,7.8], 'area_mm2':area,
                'projected_area_lower_mm2':area_projected,'web_min_mm':2.95-.55-.65,
                'metal_clamp_thickness_mm':[2.95-.55,3.05-.50]},
    'force_window_N':None, 'installation_torque_Nm':None,
    'load_examples_not_limits':[{'F_N':f,'uniform_average_pressure_MPa':f/area} for f in [100,300,1000]],
    'rejected_generic_rule':{
        'description':'A2-50 class reference + full M6 stress area + generic 70% yield rule; not shoulder/cup rating',
        'conditional_Rp02_MPa':210,'conditional_M6_As_mm2':20.1,
        'conditional_70percent_force_N':.7*210*20.1,
        'conditional_average_pressure_MPa':.7*210*20.1/area,
        'accepted':False,
        'why':['special tail root has no specified minimum neck/strength rating',
               'cup material condition/allowable and local bending/contact not established',
               'average pressure is neither maximum local stress nor complete failure criterion']},
    'torque_model':{
        'equation':'T_total = T_prevailing + F*c; c=(p/(2*pi)+mu_thread*d2/(2*cos(30deg))+mu_bearing*r_eff)/1000, dimensions mm, T Nm',
        'scope':'small-helix-angle engineering approximation; no numerical friction or force assumed',
        'robust_setpoint_interval':'Pmax+cmax*Fmin <= T_actual <= Pmin+cmin*Fmax',
        'tool_error_must_also_fit':True,
        'not_known':['required residual Fmin after service loads/settlement',
                     'matched complete shoulder+cup+nut Fmax',
                     'SKU prevailing-torque range and permitted reuse',
                     'thread/bearing friction and effective contact radius'],
    },
    'nut':{'sku':'Accu HNN-M6-A2','catalogue_material':'A2-70',
           'standard':'DIN 985','pitch_mm':1,'overall_height_mm':[5.7,6],
           'published_SKU_proof_load_found':False,'published_SKU_prevailing_torque_found':False,
           'iso2320_steel_table_directly_applied':False,
           'reason':'ISO 2320 scope references nuts with ISO 898-2 mechanical properties; no statement found mapping this A2-70 SKU to that test/table',
           'nylon_feature_is_not_positive_angular_pin':True},
    'selected_next_component_candidate':fibro,
    'comparators':{
       'unbrako_metric_shoulder':{'D8_M6_recommended_seating_Nm':12,
           'thread_neck_min_diameter_mm':4.40,'catalogue_tensile_stress_MPa':1100,
           'minimum_neck_area_mm2':math.pi*4.4**2/4,
           'derived_catalogue_tensile_force_N_not_working_limit':1100*math.pi*4.4**2/4,
           'note':'official current web PDF has values; local download timed out. Not adopted; not proof load and no CW compatibility inferred'},
       'force_defined_disc_spring':{'sku':'SCHNORR 002 050 C','standard':'DIN EN 16983 bold table entry',
           'D_mm':12.5,'d_mm':6.2,'t_mm':.35,'nominal_test_height_mm':.463,
           'nominal_force_at_test_height_N':151,
           'catalogue_force_test_range_N':[151*.925,151*1.25],
           'note':'force tolerance from standard-material table at prescribed test length; not arbitrary installed-height tolerance; no current assembly force claim',
           'current_cup_direct_fit':False,
           'why':['outer edge nominal 12.5 exceeds CW-01 OD <=12; adequate concentric bearing support needs redesign',
                  'added axial height changes nut and service envelope',
                  'spring force is not yet matched to cup allowable or required residual preload'],
           'benefit':'measured installed height/qualified force-deflection can remove most torque-friction conversion dependence, retains separate anti-loosening need'},
       'positive_lock':{'candidate':'slotted/castle nut with cross pin on purposely supplied drilled tail',
           'benefit':'physical angular restraint independent of prevailing friction',
           'not_drop_in':['current tail has no cross hole','one-slot index can back off cup seat unless axial indexing designed','after-drilling hardened catalogue screw invalidates unmodified rating'],
           'adopted':False},
    },
    'decision':{
        'preferred_next_component':'FIBRO h8 L30 catalogue shoulder screw, subject to its own root drawing and redesigned cup fit; no direct swap',
        'current_final_joint_ready_to_tighten_to_catalogue_Nm':False,
        'minimum_remaining_closure':'match complete shoulder/root geometry and cup strength/contact to a required residual force interval, then use qualified torque-tension or force-defined preload with separately qualified locking; no invented torque',
        'not_required':'new FDM fit coupons or printing to discover assembly fit',
    },
    'production_cad_changed':False,'purchased':False,'manufacturing_release':False,'physical_acceptance':False,
}
assert report['geometry']['web_min_mm'] > 1.7499
assert fibro['suggested_new_cup_design_only']['new_pilot_eccentricity_bound_if_other_old_conditions_hold_mm'] < .05
assert fibro['suggested_new_cup_design_only']['old_pilot_eccentricity_bound_if_other_old_conditions_hold_mm'] > .05
(HERE/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':report['status'],'report':str(HERE/'report.json'),'report_sha256':sha(HERE/'report.json')},indent=2))

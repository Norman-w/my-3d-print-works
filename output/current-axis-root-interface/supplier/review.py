#!/usr/bin/env python3
"""Supplier drawing clarification and proposed acceptance limits. No CAD/export."""
from pathlib import Path
import hashlib,json,math

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def budget(e=.05,face_error=.02):
    return {'root_radial_clearance_mm':(6.8-6.6)/2-e,
      'root_axial_clearance_mm':.60-.50-face_error,
      'main_bore_thread_radial_clearance_mm':(6.4-6)/2-e,
      'guaranteed_ring_inner_d_mm':max(7.0,6.9+2*e),
      'guaranteed_ring_outer_d_mm':7.8,
      'ring_projected_area_mm2':math.pi/4*max(0,7.8**2-max(7.0,6.9+2*e)**2),
      'full_thread_before_nut_margin_mm':1.4-1.2,
      'full_thread_beyond_nut_margin_mm':11.0-(1.8+6)}

def main():
    files=sorted(p for p in (OUT/'evidence').iterdir() if p.is_file())+[Path(__file__).resolve(),OUT/'README.md']
    hashes={str(p.relative_to(ROOT)):sha(p) for p in files}
    checks=[]
    def check(name,ok):
        checks.append({'name':name,'passed':bool(ok)});assert ok,name
    b=budget()
    check('conditional_root_radial_positive',b['root_radial_clearance_mm']>0)
    check('conditional_root_axial_positive',b['root_axial_clearance_mm']>0)
    check('conditional_main_bore_positive',b['main_bore_thread_radial_clearance_mm']>0)
    check('conditional_ring_positive',b['ring_projected_area_mm2']>0)
    check('nut_inside_full_thread_window',b['full_thread_before_nut_margin_mm']>0 and b['full_thread_beyond_nut_margin_mm']>0)
    check('off_center_negative_control',budget(.20)['root_radial_clearance_mm']<0)
    head_radial=(9.0-8.7)/2-.1
    head_axial=2.65-2.5-.05
    check('proposed_head_clearance_positive',head_radial>0 and head_axial>0)
    report={
      'status':'HEAD_ROOT_LIMIT_CLARIFIED_TAIL_ACCEPTANCE_CONTRACT_PROPOSED_NOT_SUPPLIER_ACCEPTED',
      'date':'2026-09-27','source_sha256':hashes,
      'official_sources':[
        {'url':'https://jp.misumi-ec.com/vona2/detail/110300249570/',
         'scope':'Current GDSMSB family table and current drawing; direct page intermittently503, prior current indexed table and current CDN graphic available.'},
        {'url':'https://content.misumi-ec.com/image/upload/v1/p/jp/product/wysiwyg/110300249570/110300249570_001_20230913143356.gif',
         'local':'evidence/current-drawing.gif','scope':'Current drawing matches the head-root enlarged detail in the official PDF.'},
        {'url':'https://cn.c.misumi.com.cn/book/sh2_2018_msm_fa_01/pdf/1938.pdf',
         'local':'evidence/misumi-cn-2018-p1938.pdf','printed_page':1897,
         'scope':'Archived Chinese official catalogue, PDF metadata2021; used for legible dimension semantics, not current delivery/configuration ranges.',
         'full_page_visually_inspected':True,'detail_render':'evidence/head-detail-660dpi.png'},
        {'url':'https://my.misumi-ec.com/pdf/fa/2014/p2_215.pdf',
         'scope':'Independent official English archive, web extracted max T and2.5max; local download503.'},
        {'url':'https://uk.misumi-ec.com/en/techblog/product-usage/reamer-bolts-aligned-assembly-advantages/',
         'scope':'Generic discussion of DIN76/DIN509; no claim that either standard defines this GDSMSB thread-end groove.'}],
      'drawing_resolution':{
        'T_is_finished_bolt_root_limit_not_recommended_hole':True,
        'max_T_mm':8.7,'under_head_transition_axial_max_mm':2.5,
        'independent_max_1_dimension_exists':False,
        'reason':'The dimension extension is attached to the bolt enlarged root detail; no mating hole is drawn there. The rotated text reads max T, corroborated by both official PDFs and D8 table.',
        'classification':'Engineering reading of official dimension lines, not a separate written manufacturer FAQ.',
        'supersedes_previous_field':'current-axis-precision-selection/report.json preferred.drawing.under_head_detail_other_mark_max_mm=1 is a reading error; it must not be consumed.',
        'head_shape_envelope':'With b measured from the actual under-head bearing plane toward the shoulder end: all root material0<=b<=2.5 lies inside diameter8.7; beyond that region the specified Dg6 shoulder applies, until the other end transition.',
        'no_support_inference':'This maximum outer envelope gives collision clearance, not minimum solid diameter or full bearing support.'},
      'head_clearance_contract_example':{
        'supplier_recommendation':False,'adopted':False,
        'actual_relief_bore_diameter_mm':[9.0,9.2],
        'actual_relief_depth_from_head_seat_mm':[2.65,2.8],
        'total_radial_registration_error_max_mm':.1,
        'total_extra_axial_error_max_mm':.05,
        'radial_margin_mm':head_radial,'axial_margin_mm':head_axial,
        'current_candidate_coordinates':{'seat_Z_mm':11.5,'minimum_relief_bottom_Z_mm':8.7,'maximum_relief_bottom_Z_mm':8.85,
          'cover_inner_Z_mm':8,'remaining_unrelieved_wall_axial_mm':[.7,.85]},
        'condition':'These are proposed actual-part acceptance windows, not FDM accuracy proven by nominal STL. Root-axis floating upward moves the transition away from the lowest relief boundary.'},
      'thread_end_findings':{
        'M_less_than_D_groove_depicted':True,'explicit_R_or_width_or_depth_found':False,
        'DIN76_binding_to_GDSMSB_found':False,
        'M_equals_D_note_applicable_to_M6_D8':False,
        'complete_tail_geometry_supplied':False,
        'review_limit':'Reviewed current family drawing plus listed official archives and narrowly targeted manufacturer searches. No claim that no unretrieved document exists.'},
      'proposed_tail_procurement_acceptance_contract':{
        'supplier_confirmed':False,'off_the_shelf_verified':False,'adopted':False,
        'scope':'Complete interference/seat/engagement interface envelope for a quoted or inspected part; not a stress, fatigue or torque qualification.',
        'datum':'A is the tail-end shoulder bearing plane; s=0 at A, s>0 toward the M6 tip; all radial values reference the g6 shoulder axis.',
        'shaft_material':'SUS304/A2-50 retained as a request; if custom machining changes certified strength, require supplier certification rather than retaining the catalogue class by name.',
        'shaft':{
          'g6_diameter_mm':[7.986,7.995],'shoulder_plane_spacing_mm':[24.45,24.55],
          'root_external_profile':[
            {'s_mm':[0,.50],'max_diameter_mm':6.60},
            {'s_mm':[.50,12.50],'max_diameter_mm':6.00}],
          'guaranteed_flat_shoulder_material_annulus_diameter_mm':[7.0,7.8],
          'combined_shoulder_and_washer_face_error_max_mm':.02,
          'full_M6x1_external_thread_interval_at_least_s_mm':[1.20,11.00],
          'thread_class_requested':'6g; verify with appropriate GO/NO-GO gauges; catalogue class not inferred.',
          'F_actual_mm':[11.5,12.5],
          'head_acceptance_window_mm':{'D':[12.8,13.2],'H':[5.8,6.2]},
          'burr_and_edge_condition':'No burr, upset or edge break may violate the radial envelopes or the guaranteed shoulder annulus.'},
        'custom_metal_washer':{
          'not_a_plain_DIN125_drop_in':True,
          'material_request':'A2 stainless; hardness/load suitability separately qualified',
          'OD_mm':[11.6,12.0],'thickness_mm':[1.4,1.8],
          'through_bore_mm':[6.4,6.5],
          'shoulder_facing_counterbore_diameter_mm':[6.8,6.9],
          'counterbore_depth_mm':[.60,.65],
          'minimum_remaining_thickness_mm':.75,
          'combined_face_error_max_mm':.02},
        'assembly_registration':{
          'total_radial_eccentricity_max_mm':.05,
          'met_by_current_loose_M6_washer':False,
          'required':'A verified centering feature or independent bounded actual registration is required. The M6 through-bore alone does not guarantee0.05. No manual visual centering assumption is allowed.',
          'if_unmet':'Recompute the root counterbore and remaining annulus with the true eccentricity, or design a positive metal registration. Do not treat the numerical example as closed.'},
        'nut':{'thread_request':'M6x1 compatible internal thread, preferably explicitly6H; catalogue thread class is not inferred.',
          'height_mm':[5.7,6.0],'axial_occupied_interval_s_mm':[1.4,7.8],
          'nylon_locking_zone':'Must lie inside the fully formed screw thread interval after washer seating.',
          'torque_and_reuse':'Obtain declared locking torque, tightening procedure and reuse policy; no torque assigned here.'},
        'computed_conditional_budget':b,
        'inspection_deliverables':['Dimensioned profile or CMM/optical trace referenced toA and the g6 axis for both root regions.',
          'Actual head dimensions and shoulder spacing; root envelopes may be inspected by a profile gauge.',
          'Shoulder annulus and washer counterbore depth/diameter/face-error records.',
          'Thread GO/NO-GO results and full-thread start/end positions.',
          'Evidence of the total assembly registration bound; otherwise the pair remains unaccepted.'],
        'rejection_rule':'Any unmet interface field rejects this specific pairing; source silence or a dimensionless supplier CAD model cannot count as acceptance.'},
      'checked_alternative_ready_made_shoulder':None,
      'alternative_note':'No extra ready-made shoulder was asserted. Existing catalogue candidate plus a declared acceptance contract is the bounded output; manufacturer acceptance and the centering feature remain distinct requirements.',
      'checks':checks,'production_CAD_modified':False,'purchase_or_supplier_contact':False,
      'physical_acceptance':False,'manufacturing_release':False}
    assert all(sha(ROOT/k)==v for k,v in hashes.items())
    (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'checks':len(checks),'report_sha256':sha(OUT/'report.json')},indent=2))

if __name__=='__main__':main()

#!/usr/bin/env python3
"""Bounded catalogue review. No CAD, sourcing or manufacturing mutation."""
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def gap(hole, shaft):
    return [round(hole[0]-shaft[1], 6), round(hole[1]-shaft[0], 6)]

SOURCES = [
    'cad/cable-trigger-input.scad',
    'docs/current-assembly-selections.json',
    'output/current-axis-supply-review/report.json',
    'output/current-axis-supply-review/evidence/igus-g-catalog.pdf',
]
start = {p: sha(ROOT/p) for p in SOURCES}
prior = json.loads((ROOT/SOURCES[2]).read_text())
selected = json.loads((ROOT/SOURCES[1]).read_text())
assert 'SPMSS-D8-V4.3-L15' in json.dumps(selected), 'Do not silently assume a changed shaft selection'
cad = (ROOT/SOURCES[0]).read_text()
for marker in ['[12,8.2,11]', '[16,8.4,.25]', 'ci_zcyl(0,0,-4,12,12.2)', 'ci_zcyl(0,0,-3.5,11,24)']:
    assert marker in cad, f'Current dimension assumption changed: {marker}'

official_sources = [
  {
    'id':'swsps-current-family',
    'url':'https://jp.misumi-ec.com/vona2/detail/110302283610/?msockid=2d0f9e637752607d1ce6881576ae61fa',
    'evidence':'Official indexed current-family table read 2026-09-27; D16 row V6/8/10/12 and t0.25; thickness tolerance +/-0.025. Live opens returned HTTP503.',
    'proves':['catalogue combination 16/8/0.25', 'catalogue combination 16/10/0.25', 't0.25 thickness tolerance'],
    'does_not_prove':['live SKU configuration acceptance', 'current radial drawing revision', 'regional sale or stock'],
  },
  {
    'id':'swsps-official-correction-drawing',
    'url':'https://jp.misumi-ec.com/maker/misumi/catalog/pdf/fa/correction2012/part_p2_127.pdf',
    'evidence':'Official archived correction sheet; indexed drawing description provides V +0.5/0 and D 0/-0.5. t0.25 +/-0.025. Direct PDF download returned HTTP503; no PDF bytes or visual inspection claimed.',
    'status':'ARCHIVED_OFFICIAL_DRAWING_INDEXED_NOT_CURRENT_REVISION_CERTIFIED',
  },
  {
    'id':'swsps-us-2019',
    'url':'https://us.misumi-ec.com/pdf/fa/2019/2019_US_2344.pdf',
    'evidence':'Official 2019 US catalogue indexed drawing: SWSPS V +0.5/0, D 0/-0.5; Polyslider nylon. Download returned HTTP503. Only t0.25 is used; other regional/historical thickness tolerances are not combined.',
    'status':'ARCHIVED_OFFICIAL_CORROBORATION',
  },
  {
    'id':'swsps-incad',
    'url':'https://jp.misumi-ec.com/ec/incadlibrary/detail/000223.html',
    'evidence':'Current official inCAD example lists Polyslider washer family, D16 with V8 or10 and t0.25. Example itself uses t1.0; it is not proof of this trigger application.',
  },
  {
    'id':'shbr-shbz-current',
    'url':'https://jp.misumi-ec.com/vona2/detail/110300031870/',
    'evidence':'Current official page read successfully 2026-09-27. Specification table d8 row; SHBR8-10 and SHBR8-12 listed. SHBR=E7/r6, SHBZ=F7/m6. Special bronze casting. Recommended mating shaft f8 or g6; periodic lubrication; SHBR press-fit; SHBZ anti-rotation screw. Housing 12 H7=12.000..12.018. Reference screw M4x8 for SHBZ.',
    'page_locators':{'type_material_installation':'drawing/specification section, lines235-243 in retrieved page', 'd8_d12_tolerances':'specification table lines266-271', 'housing_and_screw_recommendation':'line290', 'actual_listed_SHBR8_10_and_12':'lines313-314, dimensional rows375-376'},
  },
  {
    'id':'shbr-shbz-official-length-drawing',
    'url':'https://th.misumi-ec.com/en/pdf/fa/2014/p1_391.pdf',
    'support_url':'https://jp.misumi-ec.com/archive/pdf/fa/2018/18-06.pdf',
    'evidence':'Official archived drawings, indexed text, give length L -0.1/-0.3 and recommended f8/g6 shaft. Direct single-page PDF returned HTTP503; full JP catalogue exceeds web size limit. No downloaded drawing or visual inspection claimed.',
    'status':'ARCHIVED_LENGTH_TOLERANCE_REQUIRES_CURRENT_DRAWING_CONFIRMATION',
  },
  {
    'id':'igus-existing-source',
    'url':'https://www.igus.com/ContentData/Products/Downloads/iglide_G300_FM_USen.pdf',
    'evidence':'Reuse prior locally downloaded and visually reviewed official catalogue; GSM-0812-09, shaft7.964..8.000, steel housing12.000..12.018; installed ID8.040..8.130. No new claim of live stock.',
    'local_path':SOURCES[3],
  },
]

shaft=[7.9,8.0]
washers=[]
for ID in [8,10]:
    washers.append({
      'candidate_code':f'SWSPS16-{ID}-0.25',
      'code_status':'CATALOGUE_ROW_COMBINATION_NOT_LIVE_CONFIGURED',
      'material':'Polyslider nylon resin',
      'required_quantity':2,
      'nominal_mm':{'OD':16,'ID':ID,'thickness':.25},
      'bounds_mm':{'OD':[15.5,16], 'ID':[ID,ID+.5], 'thickness':[.225,.275]},
      'bounds_provenance':{'radial':'official archived drawing; current radial revision not downloaded', 'thickness':'current indexed family and archived drawing agree'},
      'shaft_diametral_clearance_mm':gap([ID,ID+.5],shaft),
      'maximum_free_radial_eccentricity_mm':round((ID+.5-shaft[0])/2,6),
      'two_washer_total_thickness_mm':[.45,.55],
      'nominal_changes_from_current':{'ID_mm':round(ID-8.4,6),'OD_mm':0,'thickness_mm':0},
      'disposition':'NOT_GUARANTEED_POSITIVE_SLIP_CLEARANCE' if ID==8 else 'POSITIVE_SHAFT_CLEARANCE_BUT_THRUST_OVERLAP_AND_CAPTURE_NOT_REVIEWED',
    })

bushes=[]
for typ,ib,ob,retention in [
    ('SHBR',[8.025,8.040],[12.023,12.034],'Press-fit in manufacturer-recommended H7 housing'),
    ('SHBZ',[8.013,8.028],[12.007,12.018],'Manufacturer-recommended anti-rotation screw; reference M4x8'),
]:
    for L in [10,12]:
        lb=[round(L-.3,6),round(L-.1,6)]
        bushes.append({
          'candidate_code':f'{typ}8-{L}',
          'code_status':'CURRENT_FAMILY_STANDARD_SIZE; SHBR actual list read; SHBZ family table combination',
          'material':'Special bronze casting; alloy grade not identified in cited page',
          'required_quantity':1,
          'nominal_mm':{'ID':8,'OD':12,'length':L},
          'catalogue_bounds_mm':{'ID':ib,'OD':ob,'length':lb},
          'tolerance_classes':{'ID':'E7' if typ=='SHBR' else 'F7','OD':'r6' if typ=='SHBR' else 'm6'},
          'length_tolerance_provenance':'official archived drawing, not current drawing revision confirmed',
          'recommended_housing_mm':[12,12.018],
          'recommended_shaft_class':['f8','g6'],
          'retention':retention,
          'lubrication':'Manufacturer recommends periodic lubrication despite oil-free family name; lubricant chemistry/application not selected.',
          'current_ideal_12p2_CAD_hole_diametral_gap_mm':gap([12.2,12.2],ob),
          'recommended_housing_diametral_gap_mm':gap([12,12.018],ob),
          'catalogue_free_bore_minus_current_shaft_mm':gap(ib,shaft),
          'free_bore_warning':'Not an installed clearance guarantee; interference insertion can change bore, and PETG housing has not been qualified.',
          'length_minus_current_11mm_rotor_mm':[round(lb[0]-11,6),round(lb[1]-11,6)],
          'centred_each_end_recess_mm': [round((11-lb[1])/2,6),round((11-lb[0])/2,6)] if L==10 else None,
          'centred_each_end_protrusion_mm':[round((lb[0]-11)/2,6),round((lb[1]-11)/2,6)] if L==12 else None,
          'minimum_design_implications':[
              'Replace unspecified ID8.2/OD12/L11 bush contract with exact model and installed-fit specification.',
              'The current nominal PETG bore12.2 is not H7. Define retention and a stable manufactured seat; merely changing the SCAD diameter to12 does not prove H7 or PETG creep resistance.',
              'SPMSS OD7.9..8.0 is not wholly within either recommended shaft tolerance class; shaft finish/roundness and allowable clearance also remain undefined.',
              'L10 is recessed0.55..0.65 at each end if centred in an ideal11mm rotor; requires bearing support/retention/thrust-load review.' if L==10 else 'L12 protrudes0.35..0.45 each end if centred, intersects the existing nominal thrust-washer positions; requires axial redesign.',
              'Choose lubricant compatible with bronze, shaft and adjacent PETG/washer; no torque, load or life release follows from catalogue dimensions.',
          ],
          'drop_in':False,
        })

comparisons={
 'current_ideal_PETG_bore_minus_recommended_housing_max_mm':round(12.2-12.018,6),
 'shbr_interference_in_recommended_housing_mm':[.005,.034],
 'two_0p25_washers_stack_mm':[.45,.55],
 'two_0p25_washers_delta_from_nominal_total_mm':[-.05,.05],
 'full_axial_clamp_budget_assessed_here':False,
 'igus_GSM081209_reused_limits':{
   'nominal_ID_OD_L_mm':[8,12,9],
   'installed_ID_in_specified_steel_housing_mm':[8.040,8.130],
   'shaft_mm':[7.964,8],
   'housing_mm':[12,12.018],
   'SPMSS_minimum_below_recommended_shaft_min_mm':.064,
   'not_drop_in_reasons':['length9 instead of11', 'PETG nominal12.2 is not specified steel H7 housing', 'selected full shaft tolerance outside recommended range'],
 },
}

report={
 'created_utc':datetime.now(timezone.utc).isoformat(),
 'status':'SPECIFIC_STANDARD_CANDIDATES_LOCKED_NO_DROP_IN_AXIS_COMBINATION',
 'scope':'Only bush and t0.25 thrust washer supplier dimensions/installation conditions. No new design, procurement, all-axis fit or strength claim.',
 'source_sha256':start,
 'source_line_evidence':{'cad/cable-trigger-input.scad':[[119,120],[210,210],[243,253],[290,290],[305,306],[346,347]]},
 'official_sources':official_sources,
 'washers':washers,
 'bushes':bushes,
 'comparisons':comparisons,
 'manufacturer_standard_combinations_not_current_assembly_selections':[
    {'bush':'SHBR8-10','shaft':'8 f8 or g6, actual supplier not selected','housing':'12 H7 with qualified press-fit retention','added_conditions':['periodic lubrication','length/thrust arrangement redesign','installed clearance confirmation']},
    {'bush':'SHBZ8-10','shaft':'8 f8 or g6, actual supplier not selected','housing':'12 H7 plus defined anti-rotation screw retention','added_conditions':['reference M4x8 screw is not present in current rotor','periodic lubrication','length/thrust arrangement redesign','installed clearance confirmation']},
 ],
 'next_actions':[
    'Decide whether to retain a purpose-made OD12/ID8.2/L11 bush with an explicit material/fit/retention drawing, or deliberately redesign around one of the listed standard bronze bush installations. Neither route is approved by this report.',
    'For SWSPS16-8-0.25 require positive assembly clearance by an explicitly bounded compatible shaft/washer selection; its nominal size alone cannot establish that condition.',
    'If evaluating SWSPS16-10-0.25, consume up to1.3mm radial eccentricity and actual OD15.5 minimum in a thrust-overlap/capture calculation before adopting it.',
    'Fetch the current SWSPS radial drawing and current bronze-bush length drawing when official service returns; do not silently promote archived-index facts to a current drawing certificate.',
 ],
 'open_fields':['current radial washer drawing revision','current bronze-bush length drawing revision','regional live SKU acceptance/availability','selected actual shaft bearing tolerance and finish','installed bush bore and retention in PETG','rotor/thrust load and clamp-stack acceptance','lubricant/material compatibility'],
 'purchased':False,'cart_modified':False,'manufacturer_contacted':False,
 'CAD_modified':False,'BOM_modified':False,'manufacturing_release':False,'physical_acceptance':False,
 'new_official_PDF_bytes_downloaded':False,
 'no_exact_11mm_off_the_shelf_bush_found_in_reviewed_families':True,
 'not_a_market_exhaustiveness_claim':True,
 'script_sha256':sha(Path(__file__)),
}
end={p:sha(ROOT/p) for p in SOURCES}
report['sources_stable']=start==end
assert report['sources_stable'], 'Source changed during report'
assert washers[0]['shaft_diametral_clearance_mm']==[0,.6]
assert washers[1]['shaft_diametral_clearance_mm']==[2,2.6]
assert bushes[0]['current_ideal_12p2_CAD_hole_diametral_gap_mm']==[.166,.177]
(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':report['status'],'sources_stable':True,'report_sha256':sha(OUT/'report.json')},indent=2))

#!/usr/bin/env python3
"""Reproduce limited supplier facts and conditional stack arithmetic; no CAD or network."""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
P=Path(__file__).resolve().parent
def sh(p):return hashlib.sha256(p.read_bytes()).hexdigest()
pin={
 'manufacturer':'AMPG','supplier':'Accu','sku':'PIN301M8X35',
 'source_url':'https://www.accu.co.uk/clevis-pins/765782-PIN301M8X35',
 'official_drawing_url':'https://ampg.com/public/assets/imgs/uploads/AMPG%20Power%20Transmission%20Catalog.pdf',
 'drawing_printed_page':'F-161','pdf_page_1_based':165,
 'material_exact_supplier':'303 / ASTM A582','material_factory_family':'18-8 stainless steel','finish':'natural',
 'shaft_d_mm':[7.90,7.95],'head_d_mm':[13.62,14.0],'head_h_mm':[2.62,3.0],
 'hole_d_mm':[2.0,2.5],
 'L_nominal_mm':35,'L_definition':'Under-head bearing plane to tail end','L_tolerance_mm':None,
 'E_nominal_mm':30,'E_definition':'Under-head bearing plane to near edge of transverse hole; visually confirmed factory arrow','E_tolerance_mm':None,
 'hole_center_conditional_E30_mm':[31,31.25],
 'head_root_profile':None,'head_root_radius_mm':None,'roughness':None,'retention_load_rating_N':None,
 'availability':'Catalogue part; real-time stock/order not verified',
 'standard_binding':'No explicit ISO2341/DIN1444 conformity claimed for this exact AMPG metric part in inspected page.',
}
washer={
 'supplier':'Accu','sku':'HRDW-M8-A2','quantity':2,'standard':'DIN433','material':'A2 stainless steel',
 'selected_candidate_layout':'both washers at tail side localZ<-12; none under head',
 'source_url':'https://www.accu.co.uk/metric-flat-washers/404901-HRDW-M8-A2',
 'id_mm':[8.4,8.62],'thickness_mm':[1.4,1.8],'od_nominal_mm':15,'od_tolerance_mm':None,
 'scope':'Use exact natural-finish SKU table; do not transfer a separate black-finish SKU OD tolerance.',
}
cotter={
 'supplier':'Accu','sku':'HSPP-2-16-A2','quantity':1,'standard':'DIN94','material':'A2 stainless steel',
 'source_url':'https://www.accu.co.uk/split-pins/63677-HSPP-2-16-A2',
 'nominal_d_mm':2,'actual_d_mm':[1.7,1.8],'length_nominal_mm':16,'length_tolerance_mm':None,
 'eye_width_mm':[3.2,3.6],'eye_length_nominal_mm':4,'eye_length_tolerance_mm':None,
 'leg_length_difference_mm':[1.25,2.5],'recommended_hole_mm':2,
 'bent_installed_envelope':None,'bend_radius_angle_specification':None,'retention_load_rating_N':None,
 'assembly':'Straight legs through hole, then bend legs to retain; exact final envelope requires actual assembly definition.',
}
mbo={
 'manufacturer':'mbo Osswald','drawing_article':'41 08 0032 0274/003','designation':'ISO2341 B 8 h11 x32 x27.4',
 'source_url':'https://www.mbo-osswald.de/daten/mbodrawing/410800320274003-en.pdf',
 'configurator_url':'https://www.mbo-osswald.de/en/configurators/bolts-according-to-din-en-iso/bolts-din-en-22341/iso-2341-form-b',
 'material':'1.0715 / 1.0718 according to DIN EN10277','surface':'bright, lightly oiled',
 'shaft_d_mm':[7.91,8],'head_d_mm':[13.57,14],'head_h_mm':[2.875,3.125],
 'L_mm':[31.5,32.5],'hole_center_from_head_mm':[27.4,27.92],'hole_d_mm':[2,2.14],
 'root_r_nominal_mm':.6,'unindicated_tolerance_note':'ISO2768-m for linear/angular; ISO2768-0.6 symmetry. No numeric radius tolerance imported here.',
 'hole_edge':'broken, no numerical edge break size provided',
 'availability':'Published drawing of a configured part; series says individually manufactured, not verified stock.',
}
S=26;E=30;L=35
tmin,tmax=washer['thickness_mm'];hmin,hmax=pin['hole_d_mm'];dmin,dmax=cotter['actual_d_mm']
cmin=E-2*tmax;cmax=E+hmax-dmin-2*tmin
calculations={
 'assumptions':['E exactly30 and L exactly35 despite missing actual tolerances','Plastic outer span exactly26','Head and flat washers fully flat and coaxial','Cotter straight section properly inserted and approximated by published outside diameter; bent legs/eye separate','No structural capacity inferred'],
 'capture_span_mm':[round(cmin,6),round(cmax,6)],
 'pin_axial_float_mm':[round(cmin-S,6),round(cmax-S,6)],
 'capture_formula':'E - t_tail1 - t_tail2 <= C <= E + hole_D - cotter_D - t_tail1 - t_tail2',
 'instantaneous_pin_shift_domain_mm':[0,round(cmax-S,6)],
 'selected_layout':'both-tail',
 'head_underface_localZ_mm':[14,round(14+cmax-S,6)],
 'head_max_localZ_mm':round(14+cmax-S+pin['head_h_mm'][1],6),
 'head_max_formula':'14+E+hole_D-cotter_D-S-t_tail1-t_tail2+head_h',
 'shaft_tail_min_localZ_mm':round(14-L,6),
 'unselected_head_and_tail_layout':{'head_max_localZ_mm':round(14+E+hmax-dmin-S-tmin+pin['head_h_mm'][1],6),'shaft_tail_min_localZ_mm':round(14+tmin-L,6),'do_not_mix_with_selected':True},
 'given_prior_head_localZ_max_mm':20.75,'given_prior_tail_localZ_min_mm':-25.55,
 'nominal_8_3_bore_radial_clearance_mm':[round((8.3-pin['shaft_d_mm'][1])/2,6),round((8.3-pin['shaft_d_mm'][0])/2,6)],
 'same_bore_extra_radial_clearance_vs_g6_mm':[round((7.995-7.95)/2,6),round((7.986-7.90)/2,6)],
 'mbo_one_washer_max_possible_capture_mm':round(27.92+2.14/2-1.7-1.4,6),
 'AMPG_8x30_E_mm':25,
}
checks={
 'conditional_capture':[26.4,28.0]==calculations['capture_span_mm'],
 'conditional_float':[.4,2.0]==calculations['pin_axial_float_mm'],
 'conditional_head':19==calculations['head_max_localZ_mm'],
 'conditional_tail':-21==calculations['shaft_tail_min_localZ_mm'],
 'mbo_published_32_variant_too_short_even_with_one_washer':calculations['mbo_one_washer_max_possible_capture_mm']<S,
 'AMPG_30_too_short':25<S,
 'no_missing_tolerance_filled':pin['E_tolerance_mm'] is None and pin['head_root_profile'] is None and cotter['bent_installed_envelope'] is None,
}
artifacts=['README.md','build.py','evidence/retrieval.json','evidence/ampg-transmission.pdf','evidence/ampg-f161.png','evidence/mbo-8x32-lh27_4.pdf','evidence/mbo-8x32-lh27_4.png']
report={
 'status':'CATALOGUE_PIN_CANDIDATE_DEFINED_CONDITIONAL_STACK_ONLY',
 'generated_at_utc':datetime.now(timezone.utc).isoformat(),
 'preferred_catalogue_candidate':pin,'standard_washer':washer,'standard_cotter':cotter,
 'more_detailed_but_nonfitting_published_alternative':mbo,'conditional_calculations':calculations,
 'physical_release':False,'purchased':False,'formal_CAD_changed':False,
 'source_facts_method':'Official manufacturer PDF visually inspected; exact supplier technical tables read live. No pixel scaling; no cross-SKU tolerance substitution.',
 'access_limits':['Accu technical image returned403 via direct download; exact technical PDF was accessible via web extraction but not locally downloaded.','AMPG PDF eventually downloaded in one bounded-scope request; E near-edge confirmed visually.','Dynamic supplier pages expose conflicting stock templates; no stock claim made.'],
 'open':['L/E actual tolerances','Head-root full envelope and direct seating on cover with proposed9.2 root relief','Washer OD tolerance/flatness','Cotter exact installed bent-leg/eye envelope and tool path','Actual plastic/bushing fits and load/wear/retention capacity'],
 'checks':checks,'artifact_sha256':{a:sh(P/a) for a in artifacts},
}
(P/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(checks.values()),checks
print(json.dumps({'status':report['status'],'checks':checks,'report_sha256':sh(P/'report.json')},ensure_ascii=False))

#!/usr/bin/env python3
"""Freeze a bounded supplier review; no network, CAD export or purchasing."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
FILES = [
    'cad/cable-trigger-input.scad',
    'docs/cable-trigger-input.md',
    'docs/cable-hardware-evidence.md',
    'docs/current-assembly-selections.json',
    'output/current-assembly-package/cable-hardware/hardware.json',
    'output/procurement/owned-items-to-identify.csv',
]

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

before = {p: sha(ROOT / p) for p in FILES}
cad = (ROOT / FILES[0]).read_text()
for expected in (
    'ci_zcyl(0,0,-5.5,1.6,8.3)',
    'ci_zcyl(0,0,-4,12,12.2)',
    'ci_zring(0,0,-5.5,15,8,4.3)',
    'for(z=[-3.75,7.5])ci_zring(0,0,z,.25,16,8.4)',
    'ci_zring(0,0,-3.5,11,12,8.2)',
):
    assert expected in cad, f'Current source contract changed: {expected}'

hardware = json.loads((ROOT / FILES[4]).read_text())
local_items = [x for x in hardware['items'] if x['item_id'] in
               ['steel-distance-tube', 'replaceable-bush', 'thrust-washer']]
assert len(local_items) == 3
assert [x['assembly_required_new_quantity'] for x in local_items] == [1, 1, 2]

sources = [
    {
        'id': 'misumi-spmss',
        'url': 'https://jp.misumi-ec.com/vona2/detail/110411266569/?optPageSCate=seriesList',
        'title': 'MISUMI metal hollow spacers SPMSS',
        'access': 'Official indexed page read on 2026-09-27; live JP site was in maintenance.',
        'locator': 'Specification table; TYPE table; dimensional conditions; comparison table rows for OD/ID/L tolerances.',
        'configured_code': 'SPMSS-D8-V4.3-L15',
        'code_status': 'Derived from explicitly published configurable template and allowed dimensions; not submitted to live configurator, quoted, ordered or stock-confirmed.',
        'material': 'SUS304, no surface treatment',
        'nominal_mm': {'OD': 8, 'ID': 4.3, 'L': 15},
        'bounds_mm': {'OD': [7.9, 8.0], 'ID': [4.3, 4.4], 'L': [14.98, 15.02]},
        'configuration_domain': {'D': [4, 50, 0.1], 'V': [2, 44, 0.1], 'L': [1, 50, 0.1]},
        'conditions_for_this_size': ['4<=D<=10 implies V<=D-2', 'L<=8*V'],
        'conditions_satisfied': 4 <= 8 <= 10 and 4.3 <= 8 - 2 and 15 <= 8 * 4.3,
        'not_certified': ['shaft finish/roundness or friction qualification', 'PETG actual end-seat geometry', 'whole axial stack', 'regional shipping or live availability'],
    },
    {
        'id': 'accu-hps',
        'url': 'https://www.accu.co.uk/cylindrical-spacers/355171-HPS-8-15-ST',
        'title': 'Accu HPS-8-15-ST cylindrical spacer',
        'part_number': 'HPS-8-15-ST',
        'material': '303 stainless steel, natural finish',
        'bounds_mm': {'OD': [7.5, 8.5], 'ID': [4.15, 4.45], 'L': [14.5, 15.5]},
        'disposition': 'REJECT_AS_TOLERANCE_GUARANTEED_DROP_IN',
        'reason': 'Nominal dimensions match, but permitted OD 8.5 exceeds nominal bush ID 8.2 and fixed-seat bore 8.3.',
        'availability': None,
        'availability_note': 'Parsed page includes conflicting template states; no actual stock or region checkout verified. Direct HTML save returned HTTP 403.',
    },
    {
        'id': 'igus-g',
        'url': 'https://www.igus.com/ContentData/Products/Downloads/iglide_G300_FM_USen.pdf',
        'title': 'igus iglide G official catalog',
        'local_file': 'evidence/igus-g-catalog.pdf',
        'sha256': sha(OUT / 'evidence/igus-g-catalog.pdf'),
        'material': 'iglide G tribopolymer',
        'page_basis': 'PDF pages 13 and 25 rendered and visually inspected; printed pages 99 and 111. Pressfit footnote applies to steel housing.',
        'parts': [
            {'part_number': 'GSM-0812-09', 'nominal_mm': {'ID': 8, 'OD': 12, 'L': 9},
             'length_tolerance_callout': 'h13', 'installed_ID_mm': [8.040, 8.130],
             'required_housing_bore_mm': [12.000, 12.018], 'shaft_size_mm': [7.964, 8.000],
             'condition': 'Installed-ID values based on steel housing pressfit; not transferable to an unmeasured PETG hole.'},
            {'part_number': 'GTM-0815-005', 'nominal_mm': {'ID': 8, 'OD': 15, 't': 0.5},
             'drawing_tolerance_callouts_mm': {'ID': '+0.25', 'OD': '-0.25', 't': '-0.05'},
             'condition': 'Not the current OD16/ID8.4/t0.25 washer.'},
        ],
        'disposition': 'CATALOG_PARTS_NOT_DROP_IN',
        'live_stock_verified': False,
    },
    {
        'id': 'misumi-snms',
        'url': 'https://jp.misumi-ec.com/vona2/detail/110300234960/',
        'title': 'MISUMI SNMS precision collars',
        'material': 'SUS304 for SNMS',
        'length_tolerance_mm': [-0.01, 0.01],
        'ID_increment_mm': 0.5,
        'restriction': 'G/H diameter tolerance selections require D>=9; do not apply H7/g6 to D8 from the general option list.',
        'disposition': 'NOT_EXACT_CURRENT_ID_4P3; SPMSS is the narrower nominal-match lead.',
    },
    {
        'id': 'misumi-resin-collar',
        'url': 'https://jp.misumi-ec.com/vona2/detail/110300236270/?rid=c24-alluser_detail_7_110300236270',
        'title': 'MISUMI resin collars FCLJJ / CLJJ',
        'material': 'POM white for FCLJJ/CLJJ',
        'ID_free_range_mm': [3, 100, 0.5],
        'L_free_range_mm': [10, 100, 0.5],
        'disposition': 'CURRENT_ID_8P2_NOT_IN_PUBLISHED_INCREMENT; no exact bush identified.',
        'not_inferred': 'No unverified configuration code or full-fit acceptance from material name.',
    },
    {
        'id': 'misumi-thin-washer',
        'url': 'https://jp.misumi-ec.com/vona2/detail/110302283610/?rid=c24-alluser_detail_3_110302283610',
        'support_url': 'https://jp.misumi-ec.com/ec/incadlibrary/detail/000223.html',
        'tolerance_catalog_url': 'https://jp.misumi-ec.com/archive/pdf/fa/2018/18-33.pdf',
        'title': 'MISUMI SWSPS ultrathin resin washers',
        'candidate_code': 'SWSPS16-8-0.25',
        'code_status': 'Catalog row combination; live configured SKU not verified.',
        'material': 'Polyslider nylon resin',
        'nominal_mm': {'OD': 16, 'ID': 8, 't': 0.25},
        'thickness_bounds_mm_from_archived_catalog': [0.225, 0.275],
        'radial_tolerances_verified': False,
        'disposition': 'CANDIDATE_ONLY; preserves thickness but ID8 differs from current ID8.4. ID clearance cannot be accepted without current drawing tolerance.',
    },
]

checks = {
    'misumi_spmss_config_within_published_domain': sources[0]['conditions_satisfied'],
    'spmss_against_nominal_bush_diametral_clearance_mm': [round(8.2-8.0, 6), round(8.2-7.9, 6)],
    'spmss_against_nominal_seat_diametral_clearance_mm': [round(8.3-8.0, 6), round(8.3-7.9, 6)],
    'accu_permitted_max_OD_minus_nominal_bush_ID_mm': round(8.5-8.2, 6),
    'accu_permitted_max_OD_minus_nominal_seat_ID_mm': round(8.5-8.3, 6),
    'igus_nominal_length_change_mm': 9-11,
    'CAD_bush_hole_minus_igus_max_housing_mm': round(12.2-12.018, 6),
    'spmss_min_OD_below_igus_recommended_shaft_min_mm': round(7.964-7.9, 6),
    'two_igus_washers_nominal_added_stack_mm': 2*(0.5-0.25),
    'nominal_only_warning': 'These comparisons use ideal current CAD dimensions; they do not supply printer tolerances, load capacity, friction or physical fit.',
}

report = {
    'status': 'ONE_NOMINAL_MATCH_CATALOG_CONFIGURATION_LOCKED_AXIS_ASSEMBLY_NOT_RELEASED',
    'created_utc': datetime.now(timezone.utc).isoformat(),
    'scope': 'Input trigger spacer, rotating bush and two thrust washers only; read-only supplier and local-evidence review.',
    'source_sha256': before,
    'local_source_lines': {
        'cad/cable-trigger-input.scad': [[119,120],[207,210],[241,253],[303,306],[346,347]],
        'docs/cable-trigger-input.md': [[11,11]],
        'output/current-assembly-package/cable-hardware/hardware.json': [[430,505]],
    },
    'local_items': local_items,
    'official_sources': sources,
    'calculated_comparisons': checks,
    'live_website_limitation': {'site': 'jp.misumi-ec.com', 'observed_by': 'Chrome page via Computer Use',
        'observed_page': 'https://jp.misumi-ec.com/vona2/detail/110411266569/',
        'displayed_maintenance_interval': '2026/9/27 10:00 - 9/28 08:00 (site display; no timezone asserted)',
        'effect': 'Catalog indexed evidence available; no final live configuration/price/leadtime/regional sale confirmation.'},
    'next_actions': [
        {'priority': 1, 'action': 'Use SPMSS-D8-V4.3-L15 as a tolerance-defined supplier candidate; recheck live configuration when available, and consume 7.9..8.0/4.3..4.4/14.98..15.02 in assembly budget.',
         'requires_CAD_change_now': False},
        {'priority': 2, 'action': 'Choose a bush with defined material and installed tolerances before altering the lever hole. Current 12.2 hole is not the catalog 12.000..12.018 steel pressfit housing. Do not pair the SPMSS full shaft tolerance with igus shaft range as already validated.',
         'requires_selection_or_tolerance_document': True},
        {'priority': 3, 'action': 'Obtain current radial tolerances for the t0.25 SWSPS lead or exact ID8.4/OD16 washer. Do not substitute two t0.5 igus rings: they consume the entire nominal 0.5 axial float.',
         'requires_selection_or_tolerance_document': True},
    ],
    'open_fields': ['actual purchase/owned stock', 'bush exact model/material/installed tolerance', 'washer exact radial size/tolerance and supplier model', 'shaft bearing finish/roundness', 'stack and PETG fit acceptance', 'lubrication/material compatibility under actual use'],
    'CAD_modified': False, 'purchased': False, 'cart_modified': False, 'manufacturer_contacted': False,
    'manufacturing_release': False, 'physical_acceptance': False,
}
after = {p: sha(ROOT / p) for p in FILES}
assert before == after, 'Local source changed during review generation'
report['sources_stable'] = True
report['evidence_sha256'] = {str(p.relative_to(OUT)):sha(p) for p in sorted((OUT/'evidence').glob('*')) if p.is_file()}
report['script_sha256'] = sha(__file__)
(OUT/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({'status':report['status'], 'sources_stable':True, 'report_sha256':sha(OUT/'report.json')}, indent=2))

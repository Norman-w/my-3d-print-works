#!/usr/bin/env python3
"""Source-bound cable hardware increment; no CAD edit/export, purchase or print.

This is an intentionally narrow extractor for the present audited module grammar.
Numeric lists are read from SCAD. Each fixed construction is asserted before its
audited BOM mapping is applied. Unsupported source changes fail closed.
"""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import argparse, ast, hashlib, json, math, re

ROOT=Path(__file__).resolve().parents[1]
OUT=None
AXIS_SUPPLIER="output/current-axis-circlip-reference/alternate-supplier/report.json"
AXIS_RING="output/current-axis-eclip-reference/ring/report.json"
AXIS_BUSH="output/current-axis-retention-review/report.json"
AXIS_THRUST="output/current-axis-fit-selection/supplier/report.json"
AXIS_TAIL="output/current-axis-pin-retention/supplier/report.json"
NATIVE_DIR="output/cable-eclip-adoption/20260927T151752917841Z/cad-review/runs/20260927T152453184055Z"
PREVIOUS_BOM="output/current-assembly-package/cable-hardware/hardware.json"
CI='cad/cable-trigger-input.scad'
CO='cad/cable-output-interface.scad'
CRR='cad/cable-route-retention.scad'
CT='cad/cable-trigger-system.scad'
SH='cad/feeder-support-harness.scad'
CR='cad/cable-housing-route.scad'
CSE='cad/cable-scene-export.scad'
DOC='docs/cable-hardware-evidence.md'
WASH='docs/cable-washer-retention-review.md'
AUDITED_CAD_SHA={
    CI:'cf2dc90ecea43e0bb5bf3b6fe68f9cf7adb8d47145b4b15577e5dd40f1679d8d',
    CO:'6acd8783a2c4d865b824acabd6e2f5da446f544ea1431363bbfd50c61b2ca566',
    CRR:'26dd6865899162e94702b09428eeef627d10598c1bfe4ef90bb3b3be770f10c3',
    CT:'004c9050f34fe497db26d2c5e66e3cceefdb1cda0231e3d0f7e85d79f07a6254',
    SH:'7dc29833a648600dae69bab1f666d8d3ca1999a66493dec843d37afc6da9e9b8',
    CR:'b5b335abe0b6fa4790c1331ad849c36827c2ef39711eaaf60e655ebd0d82cfaa',
    CSE:'f13b272bed1b9f0928d75f0897615c898d85ba1b986a73872cce2c736be0b42b'}
seen={};texts={};items=[];sites=[];occurrences=[]

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def source(p):
    p=str(p);path=ROOT/p;h=sha(path)
    if p in seen:assert seen[p]==h,('Source changed',p)
    seen[p]=h
    if p not in texts:texts[p]=path.read_text()
    return texts[p]
def ev(p,needle):
    s=source(p);start=s.find(needle)
    assert start>=0 and s.find(needle,start+len(needle))<0,('Missing/ambiguous source evidence',p,needle)
    return {'file':p,'line':s.count('\n',0,start)+1,
        'end_line':s.count('\n',0,start+len(needle))+1,'sha256':seen[p],'excerpt':needle}
def value(p,name):
    s=source(p);m=re.search(r'^'+re.escape(name)+r'\s*=\s*(.*?);',s,re.M)
    assert m,(p,name)
    return ast.literal_eval(m[1])
def require(p,*snippets):return [ev(p,n)for n in snippets]
def module_ev(p,name):
    s=source(p);m=re.search(r'module\s+'+re.escape(name)+r'\([^\n]*\)\s*\{',s)
    assert m,(p,name)
    return ev(p,m[0])
def full_module_ev(p,name):
    """Capture the whole audited module, including nested CSG and calls."""
    s=source(p);m=re.search(r'module\s+'+re.escape(name)+r'\([^\n]*\)\s*\{',s)
    assert m,(p,name)
    # Mask strings/comments without changing offsets before brace counting.
    masked=re.sub(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*[\s\S]*?\*/',lambda x:' '*len(x[0]),s)
    depth=1;end=m.end()
    while depth:
        assert end<len(s),(p,name,'unclosed module')
        depth+=(masked[end]=='{')-(masked[end]=='}');end+=1
    return ev(p,s[m.start():end])
def axis_bom():
    """The adopted table permits only literals, lists and top-level constants."""
    s=source(CI);m=re.search(r'function ci_axis_bom\(\)=([\s\S]*?);',s);assert m
    def walk(node):
        if isinstance(node,ast.List):return [walk(x) for x in node.elts]
        if isinstance(node,ast.Constant):return node.value
        if isinstance(node,ast.Name):
            if node.id in ('true','false'):return node.id=='true'
            return value(CI,node.id)
        raise AssertionError(('Unsupported axis BOM expression',ast.dump(node)))
    return walk(ast.parse(m[1].strip(),mode='eval').body),ev(CI,m[0])
def report_field_ev(p,key):
    source(p)
    return ev(p,'"'+key+'":')
def same_numeric_tree(a,b):
    if isinstance(a,bool) or isinstance(b,bool):return type(a)==type(b) and a==b
    if isinstance(a,(float,int)) and isinstance(b,(float,int)):return abs(a-b)<=1e-9
    if isinstance(a,list) and isinstance(b,list):return len(a)==len(b) and all(same_numeric_tree(x,y) for x,y in zip(a,b))
    return a==b
def spec(id,label,nominal,category='separate_purchase_root',manufacturer=None,open_fields=None):
    d={'item_id':id,'name_zh':label,'nominal':nominal,'procurement_category':category,
        'procurement_state':'candidate_not_confirmed_purchased','manufacturer_evidence':manufacturer or [],
        'open_fields':open_fields or []}
    items.append(d);return id
def site(id,module,frame,datum,evidence):
    d={'installation_id':id,'module':module,'coordinate_frame':frame,'datum':datum,'source_evidence':evidence}
    sites.append(d);return id
def add(site_id,item_id,evidence,status='new',parent=None):
    n=sum(r['installation_id']==site_id and r['item_id']==item_id for r in occurrences)+1
    occurrences.append({'occurrence_id':f'{site_id}/{item_id}/{n}','installation_id':site_id,'item_id':item_id,
        'quantity':1,'change':status,'parent_occurrence_id':parent,'source_evidence':evidence})
    return occurrences[-1]['occurrence_id']
def fnum(x):return str(x).replace('-','minus').replace('.','p')
def human_spec(it):
    n=it['nominal']
    if 'shaft_diameter_mm'in n:return f"{n['part']}；轴Ø{n['shaft_diameter_mm']}，头下至槽近壁{n['L_to_groove_near_wall_mm']}"
    if 'AF_mm'in n and 'length_mm'in n:return f"六角对边{n['AF_mm']} / 内Ø{n['ID_mm']} / 长{n['length_mm']}；机加工POM-C"
    if 'underhead_length_mm'in n:
        drive='驱动待明确'if n.get('socket_AF_mm')is None else f"内六角{n['socket_AF_mm']}"
        return f"头Ø{n['head_diameter_mm']}×{n['head_height_mm']}，{drive}"
    if 'AF_mm'in n:return f"对边{n['AF_mm']}，厚{n['height_mm']}"
    if 'OD_mm'in n and 'ID_mm'in n:
        s=f"外Ø{n['OD_mm']} / 内Ø{n['ID_mm']} / "+(f"长{n['length_mm']}"if 'length_mm'in n else f"厚{n['thickness_mm']}")
        if it['item_id']=='m4-capture-washer':s+='；Type A无倒角金属，极限尺寸见JSON'
        if 'part'in n:s+=f"；{n['part']}"
        return s
    return ''

def main():
    global OUT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root',type=Path,default=ROOT/'output/current-assembly-package/cable-hardware-current/runs')
    args=parser.parse_args()
    output_root=args.output_root.resolve()
    assert output_root.is_relative_to(ROOT), 'Evidence output must remain in this repository'
    OUT=output_root/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    # A run always gets a new directory; never overwrite historical evidence.
    OUT.mkdir(parents=True,exist_ok=False)
    source(str(Path(__file__).relative_to(ROOT)))
    for p in [CI,CO,CRR,CT,SH,CR,CSE,DOC,WASH,'docs/cable-trigger-input.md',AXIS_SUPPLIER,AXIS_RING,AXIS_BUSH,AXIS_THRUST,AXIS_TAIL]:source(p)
    assert all(seen[p]==h for p,h in AUDITED_CAD_SHA.items()),'Audited CAD changed: re-audit complete hardware modules before counting; do not silently accept added calls.'
    axis_rows,axis_bom_ev=axis_bom()
    assert [r[:4] for r in axis_rows]==[
        ['axis-pin-kit','HCDG8-30',1,'purchase-root-kit'],
        ['axis-supplied-clip','NETW7',1,'nonadditive-member-of-axis-pin-kit'],
        ['axis-tail-washer','HRDW-M8-A2',2,'separate-purchase'],
        ['axis-bush','machined-unfilled-POM-C',1,'machined-part-not-PETG-print'],
        ['axis-thrust-washer','SWSPS16-10-.25',2,'separate-purchase']]
    axis_full_modules=[full_module_ev(CI,n) for n in [
        'ci_mount_hardware_cad','ci_local_terminal_fasteners','ci_local_other_fixed_hardware',
        'ci_local_adjuster','ci_local_ferrule','ci_bush_hex_2d','ci_local_bush_zero','ci_local_axis_ring',
        'ci_local_axis_pin','ci_local_tail_washers','ci_local_thrust_washers',
        'ci_local_fixed_axis_hardware','ci_local_fixed_hardware','ci_local_bush',
        'ci_local_other_moving_hardware','ci_local_moving_hardware',
        'ci_fixed_hardware','ci_moving_hardware','ci_hardware','ci_local_eclip_space']]
    pin_supplier=json.loads(source(AXIS_SUPPLIER))['selected_candidate']
    assert pin_supplier['part']=='HCDG8-30' and pin_supplier['included_retaining_ring']['part']=='NETW7'
    assert pin_supplier['included_retaining_ring']['quantity']==1
    thrust_supplier=next(w for w in json.loads(source(AXIS_THRUST))['washers'] if w['nominal_mm']['ID']==10)
    tail_supplier=json.loads(source(AXIS_TAIL))['standard_washer']
    bush_requirements=json.loads(source(AXIS_BUSH))['design_requirements_not_supplier_facts']
    assert value(CI,'ci_origin')==[75,-85,5]
    assert value(CI,'ci_axis_tail_washer_od_id_t')==[15,8.5,1.6]
    assert value(CI,'ci_axis_thrust_od_id_t')==[16,10,.25]
    assert [value(CI,k) for k in ['ci_bush_af','ci_bush_id','ci_bush_length']]==[12,8.2,11]
    native_report=json.loads(source(NATIVE_DIR+'/report.json'))
    assert native_report['status']=='PASS' and native_report['sources_stable']
    for p,h in native_report['source_sha256'].items():
        source(p);assert seen[p]==h,('Native source changed',p)
    native_record=json.loads(source(NATIVE_DIR+'/scene-contract-decoded.json'))
    source(native_record['source_echo'])
    assert seen[native_record['source_echo']]==native_record['source_echo_sha256']
    native_ci=native_record['scene_contract']['ci']
    assert native_ci['axis_bom_columns']==['id','part','quantity','accounting','nominal']
    assert same_numeric_tree(axis_rows,native_ci['axis_bom']), 'Native/source axis BOM mismatch'
    # Existing manufacturer artifacts only. No new web query or procurement action.
    for name in ['03096-14','03096-25','03096-30','03096-35']:
        for suffix in ['-drawing.png','-assets.json']:
            p=f'output/cable-hardware-evidence/{name}{suffix}';seen[p]=sha(ROOT/p)
    p='output/cable-washer-retention-review/brighton-best-din125-flat-washers.pdf';seen[p]=sha(ROOT/p)
    evidence_adjuster=[ev(DOC,'## 调节器 03096-30-0306X24')]
    evidence_ferrule=[ev(DOC,'## 端套 03096-25-0350')]
    evidence_nipple=[ev(DOC,'## 压丝端头 03096-35-03180507')]
    evidence_kit=[ev(DOC,'## 完整拉索 03096-14 与球形端头'),ev(DOC,'完整套件列出 03096-15 钢丝及固定端件、03096-20 护套及内管、03096-25 端套、03096-30 调节器、03096-35 压丝端头及 07212-106 六角螺母。')]
    evidence_m6=[ev(WASH,'M6 支座使用 norelem 名义候选：`07300-106` A2 平垫圈，ID6.4/OD12/t1.6；`07212-106` A2 薄螺母，M6、SW10、H3.2，DIN439。')]
    common_open=['supplier_SKU','thread_pitch_if_not_explicitly_marked','material_and_strength_grade','manufacturing_tolerance','tightening_torque_and_locking']
    for d,L,count in [(4,60,4),(3,30,3),(3,8,2),(3,16,6),(3,25,4)]:
        spec(f'm{d}x{L}-socket',f'M{d}×{L}圆柱头内六角螺钉',{'thread_nominal':f'M{d}','underhead_length_mm':L,
            'head_diameter_mm':7 if d==4 else 5.5,'head_height_mm':4 if d==4 else 3,
            'socket_AF_mm':3 if d==4 else 2.5},open_fields=common_open)
    spec('m3x16-output-cap-fastener','输出盖M3×16螺钉（驱动型式未在该源明确）',
        {'thread_nominal':'M3','underhead_length_mm':16,'head_diameter_mm':5.5,'head_height_mm':3,
            'drive':None,'socket_AF_mm':None},open_fields=common_open+['actual_drive_type_and_size'])
    spec('m3-nut','M3六角螺母',{'thread_nominal':'M3','AF_mm':5.5,'height_mm':2.4},open_fields=common_open)
    spec('m4-nut','M4六角螺母',{'thread_nominal':'M4','AF_mm':7,'height_mm':3.2},open_fields=common_open)
    spec('m3-flat-washer','M3平垫片',{'OD_mm':7,'ID_mm':3.2,'thickness_mm':.5},open_fields=['supplier_SKU','material','hardness','tolerances'])
    spec('m4-flat-washer','M4普通安装平垫片',{'OD_mm':9,'ID_mm':4.3,'thickness_mm':.8},open_fields=['supplier_SKU','material','hardness','tolerances'])
    spec('m4-capture-washer','输出端头专用M4金属保持垫圈',{'standard_family':'DIN125 Part1 TypeA','OD_mm':9,'ID_mm':4.3,'thickness_mm':.8,
        'OD_limits_mm':[value(CO,'co_ret_od_min'),value(CO,'co_ret_od')],
        'ID_limits_mm':[value(CO,'co_ret_id'),value(CO,'co_ret_id_max')],
        'thickness_limits_mm':[value(CO,'co_ret_t_min'),value(CO,'co_ret_t_max')],
        'edge_requirement':'Type A unchamfered metal; do not silently substitute plastic/chamfered type'},
        manufacturer=[ev(WASH,'M4 保持垫圈的**名义尺寸与极限尺寸共同来自 Brighton-Best 2026 DIN 125 Part 1 Type A PDS**，不是把另一家公差归给 norelem。')],
        open_fields=['purchased_SKU','metal_grade_hardness_finish','actual_tolerance_and_load_capacity'])
    evidence_pin=[report_field_ev(AXIS_SUPPLIER,'selected_candidate'),axis_bom_ev]
    spec('input-axis-pin','输入主轴带槽销（套件中的销）',{
        'part':'HCDG8-30','shaft_diameter_mm':8,'L_to_groove_near_wall_mm':30,
        'shaft_diameter_limits_mm':pin_supplier['shaft_D_mm'],'L_limits_mm':pin_supplier['L_mm'],
        'head_diameter_mm':12,'head_height_mm':2,'tail_from_groove_near_wall_mm':3,
        'groove_width_limits_mm':pin_supplier['M_groove_width_mm'],
        'groove_root_diameter_limits_mm':pin_supplier['d_groove_root_d_mm'],
        'material':pin_supplier['material'],'surface':pin_supplier['surface'],
        'model_reference_values':{'shaft_diameter_mm':value(CI,'ci_axis_pin_D'),
            'L_to_groove_near_wall_mm':value(CI,'ci_axis_pin_L'),'axial_display_shift_mm':value(CI,'ci_axis_pin_q'),
            'groove_width_mm':value(CI,'ci_axis_pin_groove_M'),'groove_root_diameter_mm':value(CI,'ci_axis_pin_groove_d')},
        'includes':'one supplied NETW7; purchase root input-axis-pin-kit'},
        'included_member_of_axis_pin_kit',evidence_pin,
        ['actual_stock_or_purchase','head_diameter_and_tail_tolerances','root_envelope_acceptance','actual_retention_load'])
    spec('input-axis-eclip','销随附NETW7 E型卡簧（不另买）',{
        'part':'NETW7','type':'E','nominal_size':7,'material':'spring steel',
        'included_with':'HCDG8-30','actual_installed_CAD_solid_available':False,
        'display_space_is_not_part_geometry':True},'included_member_of_axis_pin_kit',
        evidence_pin+[ev(AXIS_RING,'"status": "OFFICIAL_DIMENSION_REFERENCE_FOUND_INSTALLED_SWEEP_AND_TOOL_FIT_NOT_CLOSED"')],
        ['actual_installed_outline_and_full_seating','installation_removal_tool','load_and_reuse_requirements'])
    spec('tail-washer-m8','输入轴尾侧M8平垫圈',{
        'part':'HRDW-M8-A2','standard':'DIN433','OD_mm':15,'ID_mm':8.5,'thickness_mm':1.6,
        'ID_limits_mm':tail_supplier['id_mm'],'thickness_limits_mm':tail_supplier['thickness_mm'],
        'OD_tolerance_mm':tail_supplier['od_tolerance_mm'],'material':tail_supplier['material'],
        'layout':'two at tail; none under head'},manufacturer=[report_field_ev(AXIS_TAIL,'standard_washer'),axis_bom_ev],
        open_fields=['actual_purchase','OD_tolerance_flatness','installed_stack_and_retention_load'])
    spec('replaceable-bush','输入轴机加工六角POM-C轴套',{
        'part':'machined-unfilled-POM-C','AF_mm':12,'ID_mm':8.2,'length_mm':11,
        'material':'unfilled machined POM-C','design_acceptance_bounds_not_supplier_guarantee':bush_requirements,
        'is_PETG_printed_part':False},manufacturer=[report_field_ev(AXIS_BUSH,'design_requirements_not_supplier_facts'),axis_bom_ev],
        open_fields=['supplier_grade_and_machining_route','finished_part_dimensional_acceptance','lubrication_and_wear'])
    spec('thrust-washer','输入轴ID10推力垫片',{
        'part':value(CI,'ci_axis_thrust_part'),'OD_mm':16,'ID_mm':10,'thickness_mm':.25,
        'material':thrust_supplier['material'],'catalogue_bounds_mm':thrust_supplier['bounds_mm'],
        'evidence_status':thrust_supplier['code_status']},manufacturer=[report_field_ev(AXIS_THRUST,'washers'),axis_bom_ev],
        open_fields=['actual_SKU_configuration_and_purchase','current_radial_drawing_revision','actual_fit_and_wear'])
    spec('m6-adjuster','M6拉索调节器',{'part':'03096-30-0306X24','thread_nominal':'M6','thread_length_mm':24,'total_length_mm':34,
        'head_AF_mm':8,'head_length_mm':10,'housing_inlet_diameter_mm':7,'inlet_straight_depth_mm':8.5,'wire_bore_mm':3,
        'material':'nickel-plated brass'},'kit_eligible_member',evidence_adjuster,
        ['kit_included_quantity','nose_cone_dimensions','thread_runout','actual_ferrule_bearing_depth','purchased_tolerances'])
    spec('m6-thin-nut','M6薄螺母',{'part':value(CI,'ci_adjuster_nut_part'),'thread_nominal':'M6','AF_mm':10,'height_mm':value(CI,'ci_adjuster_nut_t'),
        'material_candidate':'A2','standard':'DIN439 / ISO4035'},'kit_eligible_member',evidence_m6,['kit_included_quantity','purchased_tolerances','torque_and_locking'])
    spec('m6-flat-washer','M6平垫片',{'part':value(CI,'ci_adjuster_washer_part'),'OD_mm':12,'ID_mm':6.4,'thickness_mm':value(CI,'ci_adjuster_washer_t'),
        'material_candidate':'A2','standard':'ISO7089'},manufacturer=evidence_m6,open_fields=['purchased_SKU_tolerances'])
    spec('cable-ferrule','拉索护套端套',{'part':'03096-25-0350','OD_mm':value(CO,'co_ferrule_d'),'length_mm':value(CO,'co_ferrule_l'),
        'housing_bore_mm':value(CO,'co_ferrule_bore_d'),'housing_bore_straight_depth_mm':value(CO,'co_ferrule_bore_l'),
        'wire_bore_mm':value(CO,'co_ferrule_wire_d'),'material':'brass, blue passivated'},'kit_eligible_member',evidence_ferrule,
        ['kit_included_quantity','nose_chamfer','crimp_deformation','actual_seating_depth'])
    spec('output-nipple-assembly','带原厂紧定螺钉的输出压丝端头',{'part':'03096-35-03180507','body_OD_mm':value(CO,'co_nipple_d'),
        'body_length_mm':value(CO,'co_nipple_l'),'wire_cross_bore_mm':1.8,'cross_bore_offset_from_screw_end_mm':3.5,
        'material':'nickel-plated brass','includes':'one factory M4 slotted clamping screw'},'kit_eligible_member',evidence_nipple,
        ['kit_included_quantity','grub_screw_length_and_protrusion','slot_width_depth','tightening_torque','wire_holding_force'])
    spec('factory-m4-grub','压丝端头内含M4一字紧定螺钉',{'thread_nominal':'M4','drive':'slotted','length_mm':None},
        'nonadditive_component_of_nipple',evidence_nipple,['length','protrusion','slot_width_depth','torque'])
    spec('core-with-fixed-ball','带出厂固定球端的连续钢芯',{'family':'03096-15','wire_diameter_mm':value(CI,'ci_wire_d'),
        'fixed_ball_diameter_mm':value(CI,'ci_ball_d'),'material':'stainless steel 1.4401','length_mm':None},'kit_eligible_member',evidence_kit,
        ['selected_length','length_datum','actual_cut_permission_and_end_budget','bare_wire_bending_endurance'])
    spec('integral-ball-end','钢芯出厂固定球端（不单买）',{'diameter_mm':value(CI,'ci_ball_d')},'nonadditive_component_of_core',evidence_kit,['factory_attachment_strength'])
    spec('housing-with-liner','连续护套及内管',{'family':'03096-20','OD_mm':5,'length_mm':None,'minimum_bend_radius_mm':65,
        'material':'plastic-coated steel housing','load_mode':'compression only'},'kit_eligible_member',evidence_kit,
        ['selected_length','cutting_and_end_preparation_permission','liner_dimensions_material','actual_end_seating'])

    # Baseline four bolts and washers are replaced; four original nuts remain.
    replacement_ev=require(CT,'difference(){la_fixed_hardware();union(){sh_bolts();sh_nuts();}}','    sh_nuts();')
    old_ev=require(SH,'    sh_y_cyl(x,z,-54.8,20,4);','    difference(){sh_y_cyl(x,z,-54.8,.8,9);sh_y_cyl(x,z,-54.9,1,4.3);}',
        'module sh_nuts(){for(x=sh_bolt_x,z=sh_bolt_z)difference(){\n    sh_y_hex(x,z,sh_nut_y,3.2,7);')
    mount_ev=require(CI,'module ci_mount_hardware_cad(){for(x=[-16,16],z=[-60,3]){',' ci_ycyl(x,z,-94.8,60,4);',
        ' difference(){ci_ycyl(x,z,-98.8,4,7);ci_yhex(x,z,-98.9,2.1,3);}',
        ' difference(){ci_ycyl(x,z,-94.8,.8,9);ci_ycyl(x,z,-94.9,1,4.3);}')
    assert value(SH,'sh_bolt_x')==[-16,16]and value(SH,'sh_bolt_z')==[-60,3]
    for x in value(SH,'sh_bolt_x'):
        for z in value(SH,'sh_bolt_z'):
            k=site(f'input-host-x{fnum(x)}-z{fnum(z)}','ci_mount_hardware_cad + ct_original_fixed_hardware','feeder CAD',
                {'axis':'Y','x':x,'z':z,'new_underhead_y':-94.8,'retained_nut_y':value(SH,'sh_nut_y')},mount_ev+replacement_ev+old_ev)
            add(k,'m4x60-socket',mount_ev,'replacement_new');add(k,'m4-flat-washer',mount_ev,'replacement_new')
            add(k,'m4-nut',old_ev+replacement_ev,'retained_from_baseline')
    axis=site('input-axis','ci_local_fixed_axis_hardware / ci_local_moving_hardware','input local',
        {'x':0,'y':0,'axis':'Z','pin_is_floating_not_fixed_against_rotation':True},axis_full_modules+[axis_bom_ev])
    add(axis,'input-axis-pin',[full_module_ev(CI,'ci_local_axis_pin'),axis_bom_ev])
    # The ring is a real supplied member. No fictitious shape is counted from its
    # conservative clearance-space mesh. No parent_occurrence_id: physical quantity
    # must remain one, while procurement is grouped by the separate kit root.
    add(axis,'input-axis-eclip',[axis_bom_ev]+evidence_pin)
    add(axis,'replaceable-bush',[full_module_ev(CI,'ci_local_bush_zero'),full_module_ev(CI,'ci_local_bush')])
    assert value(CI,'ci_axis_tail_washer_z')==[-15.2,-13.6]
    for z in value(CI,'ci_axis_tail_washer_z'):
        k=site(f'input-axis-tail-z{fnum(z)}','ci_local_tail_washers','input local',
            {'x':0,'y':0,'z_start':z,'layout':'tail side'},[full_module_ev(CI,'ci_local_tail_washers'),axis_bom_ev])
        add(k,'tail-washer-m8',sites[-1]['source_evidence'])
    assert value(CI,'ci_axis_thrust_z')==[-3.75,7.5]
    for z in value(CI,'ci_axis_thrust_z'):
        k=site(f'input-axis-thrust-z{fnum(z)}','ci_local_thrust_washers','input local',{'x':0,'y':0,'z_start':z},[full_module_ev(CI,'ci_local_thrust_washers'),axis_bom_ev])
        add(k,'thrust-washer',sites[-1]['source_evidence'])
    ce=require(CI,'  ci_zbolt(p[0],p[1],14.5,30,3,5.5,3,2.5);','  ci_zring(p[0],p[1],14,.5,7,3.2);','  difference(){ci_zhex(p[0],p[1],-11.4,2.4,5.5);ci_zcyl(p[0],p[1],-11.5,2.6,3.1);}')
    for x,y in value(CI,'ci_cheek_posts'):
        k=site(f'input-cover-x{fnum(x)}-y{fnum(y)}','ci_local_fixed_hardware','input local',{'x':x,'y':y,'axis':'Z','underhead_z':14.5},ce)
        for it in ['m3x30-socket','m3-flat-washer','m3-nut']:add(k,it,ce)
    se=require(CI,' ci_xcyl(-24,2,sx-30,30,3);',' difference(){ci_xcyl(-24,2,sx-33,3,5.5);',' for(x=[-35,-29])difference(){',
        '  translate([x,-24,2])rotate([0,90,0])rotate([0,0,30])cylinder(h=2.4,d=5.5/cos(30),$fn=6);')
    k=site('input-adjustable-stop','ci_local_fixed_hardware','input local',{'axis':'X','y':-24,'z':2,'screw_tip':'ci_stop_tip(); adjustable','nut_x_starts':[-35,-29]},se)
    add(k,'m3x30-socket',se)
    for _ in range(2):add(k,'m3-nut',se)
    te=require(CI,' ci_zbolt(p[0],p[1],4.5,8,3,5.5,3,2.5);',' difference(){ci_zhex(p[0],p[1],-3,2.4,5.5);ci_zcyl(p[0],p[1],-3.1,2.6,3.1);}')
    for x,y in value(CI,'ci_cap_bolts'):
        k=site(f'input-terminal-cap-x{fnum(x)}-y{fnum(y)}','ci_local_terminal_fasteners','rotating input local at u=0',{'x':x,'y':y,'axis':'Z','underhead_z':4.5},te)
        add(k,'m3x8-socket',te);add(k,'m3-nut',te)

    ae=require(CI,' ci_local_adjuster(delta);ci_local_ferrule(delta);',' for(x=ci_adjuster_nut_x)ci_xnut(x,10,ci_adjuster_nut_t,6.1);',
        ' for(x=ci_adjuster_washer_x)ci_xring(x,ci_adjuster_washer_t,12,6.4);',
        ' union(){ci_xhex(60,2,-63,10,8);ci_xcyl(60,2,-53,24,6);}')
    k=site('input-housing-seat','ci_local_fixed_hardware / ci_local_adjuster / ci_local_ferrule','input local',
        {'axis':'X','y':60,'z':2,'nut_x_starts':value(CI,'ci_adjuster_nut_x'),'washer_x_starts':value(CI,'ci_adjuster_washer_x'),'ferrule_bearing_datum':None},ae)
    add(k,'m6-adjuster',ae);add(k,'cable-ferrule',require(CI,'module ci_local_ferrule(delta=ci_delta){translate([delta,0,0])difference(){'))
    for _ in value(CI,'ci_adjuster_nut_x'):add(k,'m6-thin-nut',ae)
    for _ in value(CI,'ci_adjuster_washer_x'):add(k,'m6-flat-washer',ae)
    oe=require(CO,'    co_zwasher(co_stop_z-co_m6_washer_t);','    co_zwasher(co_stop_z+co_plate_t);',
        '    co_znut(co_stop_z-co_m6_washer_t-co_m6_nut_t);','    co_znut(co_stop_z+co_plate_t+co_m6_washer_t);')
    assert value(CO,'co_adjuster_thread_l')==24 and value(CO,'co_adjuster_total_l')==34
    assert value(CO,'co_m6_washer_t')==value(CI,'ci_adjuster_washer_t')and value(CO,'co_m6_nut_t')==value(CI,'ci_adjuster_nut_t')
    k=site('output-housing-seat','co_adjuster_hardware / co_ferrule_reference','feeder CAD',{'x':value(CO,'co_x'),'y':value(CO,'co_y'),'axis':'Z','outer_port_z':111,'ferrule_bearing_datum':None},oe)
    add(k,'m6-adjuster',[module_ev(CO,'co_adjuster_hardware')]);add(k,'cable-ferrule',[module_ev(CO,'co_ferrule_reference')])
    for _ in range(2):add(k,'m6-flat-washer',oe);add(k,'m6-thin-nut',oe)
    ne=require(CO,'    co_nipple(0);','    co_retaining_washer();','    co_ycyl(co_x,co_z,co_y+co_wire_d/2,39-(co_y+co_wire_d/2),4);')
    k=site('output-wire-terminal','co_terminal_hardware','feeder CAD at t=0; translates +Z 20t',{'x':value(CO,'co_x'),'wire_y':value(CO,'co_y'),'wire_center_z':value(CO,'co_z'),'body_axis':'Y','body_y_start':32},ne)
    parent=add(k,'output-nipple-assembly',ne);add(k,'factory-m4-grub',ne,parent=parent);add(k,'m4-capture-washer',ne)
    oe=require(CO,'        co_ycyl(x,co_cap_screw_z,27.7,16,3);','        co_ycyl(x,co_cap_screw_z,43.7,3,5.5);',
        '        difference(){co_ycyl(x,co_cap_screw_z,43.2,.5,7);co_ycyl(x,co_cap_screw_z,43.18,.54,3.2);}',
        '        difference(){co_yhex(x,co_cap_screw_z,28.2,2.4,5.5);co_ycyl(x,co_cap_screw_z,28.18,2.44,3.2);}')
    for x in value(CO,'co_cap_screws'):
        k=site(f'output-terminal-cap-x{fnum(x)}','co_terminal_hardware','feeder CAD at t=0; translates +Z 20t',{'x':x,'z':value(CO,'co_cap_screw_z'),'axis':'Y','underhead_y':43.7},oe)
        for it in ['m3x16-output-cap-fastener','m3-flat-washer','m3-nut']:add(k,it,oe)
    re_=require(CRR,'    translate([0,0,-length])cylinder(h=length,d=3,$fn=crr_fn);',
        '    difference(){cylinder(h=3,d=5.5,$fn=crr_fn);translate([0,0,1.3])cylinder(h=1.72,d=2.5/cos(30),$fn=6);}')
    re_+=require(CRR,'module crr_washer(p,z){translate([p[0],p[1],z])difference(){cylinder(h=.5,d=7,$fn=crr_fn);translate([0,0,-crr_eps])cylinder(h=.5+2*crr_eps,d=3.2,$fn=crr_fn);}}',
        'module crr_nut(p,z){difference(){crr_zhex(p,z,2.4,5.5);translate([p[0],p[1],z-crr_eps])cylinder(h=2.4+2*crr_eps,d=3.01,$fn=crr_fn);}}')
    clamp_ev=re_+require(CRR,'    for(x=crr_mount_x)for(y=crr_mount_stations){crr_washer([x,y],99.3);crr_bolt([x,y],99.8,25);crr_nut([x,y],78.9);}')
    for x in value(CRR,'crr_mount_x'):
        for y in value(CRR,'crr_mount_stations'):
            k=site(f'route-platform-x{fnum(x)}-y{fnum(y)}','crr_hardware','feeder CAD',{'x':x,'y':y,'axis':'Z','underhead_z':99.8},clamp_ev)
            for it in ['m3x25-socket','m3-flat-washer','m3-nut']:add(k,it,clamp_ev)
    cap_ev=re_+require(CRR,'    crr_basis()for(p=crr_bolt_points()){crr_washer(p,5);crr_bolt(p,5.5,16);crr_nut(p,-6.4);}',
        'function crr_bolt_points()=[for(a=crr_fastener_angles)for(r=crr_fastener_radii)[r*cos(a),r*sin(a),0]];')
    for a in value(CRR,'crr_fastener_angles'):
        for r in value(CRR,'crr_fastener_radii'):
            k=site(f'route-arc-angle{a}-radius{r}','crr_hardware','third-arc local U,V,N via crr_basis()',
                {'angle_deg':a,'radius_mm':r,'xy_mm':[r*math.cos(math.radians(a)),r*math.sin(math.radians(a))],'axis':'N','underhead_N':5.5},cap_ev)
            for it in ['m3x16-socket','m3-flat-washer','m3-nut']:add(k,it,cap_ev)
    wire_ev=require(CI,'module ci_local_cable(u=ci_u,delta=ci_delta){',' translate(ci_terminal)sphere(d=5);ci_local_terminal_fasteners();')+require(CO,'module co_wire(t=0){')+require(CSE,'    difference(){cr_wire();union(){ci_cable(0);co_wire(0);}}')
    k=site('continuous-cable','ci_local_cable + co_wire + cr_wire / cr_housing','continuous routed assembly',
        {'core_segments_are_one_physical_core':True,'fixed_ball_at_input':True,'cut_length_mm':None},wire_ev)
    parent=add(k,'core-with-fixed-ball',wire_ev);add(k,'integral-ball-end',wire_ev,parent=parent)
    add(k,'housing-with-liner',[ev(CR,'// Purchased flexible housing, NOT a printable part.')]+evidence_kit)

    counts=Counter(o['item_id']for o in occurrences if o['change']!='retained_from_baseline')
    expected={'m4x60-socket':4,'m3x30-socket':3,'m3x8-socket':2,'m3x16-socket':6,'m3x16-output-cap-fastener':2,'m3x25-socket':4,
        'm3-nut':18,'m3-flat-washer':14,'m4-flat-washer':4,'m4-capture-washer':1,'input-axis-pin':1,'input-axis-eclip':1,'tail-washer-m8':2,
        'replaceable-bush':1,'thrust-washer':2,'m6-adjuster':2,'m6-thin-nut':4,'m6-flat-washer':4,'cable-ferrule':2,
        'output-nipple-assembly':1,'factory-m4-grub':1,'core-with-fixed-ball':1,'integral-ball-end':1,'housing-with-liner':1}
    assert counts==expected,(counts,expected)
    previous=json.loads(source(PREVIOUS_BOM))
    previous_counts={i['item_id']:i['assembly_required_new_quantity'] for i in previous['items']}
    expected_delta={'m4x35-socket':-1,'steel-distance-tube':-1,'m4-flat-washer':-2,'m4-nut':-1,
        'input-axis-pin':1,'input-axis-eclip':1,'tail-washer-m8':2}
    count_delta={k:counts[k]-previous_counts.get(k,0) for k in set(counts)|set(previous_counts)
        if counts[k]!=previous_counts.get(k,0)}
    assert count_delta==expected_delta,(count_delta,expected_delta)
    assert len({r['installation_id']for r in sites})==len(sites)
    assert len({r['occurrence_id']for r in occurrences})==len(occurrences)
    itemmap={r['item_id']:r for r in items}
    for o in occurrences:
        assert o['item_id']in itemmap and any(s['installation_id']==o['installation_id']for s in sites)
        if o['parent_occurrence_id']:assert o['parent_occurrence_id']in{o['occurrence_id']for o in occurrences}
    for it in items:
        it['assembly_required_new_quantity']=counts[it['item_id']]
        it['retained_quantity']=sum(o['item_id']==it['item_id']and o['change']=='retained_from_baseline'for o in occurrences)
        it['installation_ids']=[o['installation_id']for o in occurrences if o['item_id']==it['item_id']]
        it['additional_purchase_quantity']=None
        it['purchase_quantity_note']='Assembly requirement only; owned stock and purchase choice unverified. Kit-member shortfall additionally needs verified kit contents.'
    root_rows=[{'purchase_root_id':r['item_id'],'assembly_new_requirement':r['assembly_required_new_quantity'],'purchase_quantity':None}
        for r in items if r['procurement_category']=='separate_purchase_root']
    root_rows.append({'purchase_root_id':'complete-cable-assembly','assembly_requirement':1,'purchase_quantity':None,
        'candidate_family':'norelem 03096-14','candidate_length_SKU':None,
        'exclusive_options':['one suitable complete kit plus only independently verified shortages','equivalent separately sourced member set; no complete kit counted simultaneously'],
        'kit_member_required_quantities':{r['item_id']:r['assembly_required_new_quantity']for r in items if r['procurement_category']=='kit_eligible_member'},
        'kit_included_quantities':None,'shortfall_quantities':None,'source_evidence':evidence_kit})
    root_rows.append({'purchase_root_id':'input-axis-pin-kit','assembly_requirement':1,'purchase_quantity':None,
        'candidate_family':'MISUMI HCDG8-30 with supplied NETW7','candidate_part':'HCDG8-30',
        'kit_member_required_quantities':{'input-axis-pin':1,'input-axis-eclip':1},
        'kit_included_quantities':{'input-axis-pin':1,'input-axis-eclip':1},
        'shortfall_quantities':{'input-axis-pin':0,'input-axis-eclip':0},
        'note':'One catalogue kit is the purchase accounting root; actual owned stock/purchase unverified. Ring remains one physical installed member, never an additional ring order.',
        'source_evidence':evidence_pin})
    assert not any(r['purchase_root_id']in ['factory-m4-grub','integral-ball-end','core-with-fixed-ball','input-axis-pin','input-axis-eclip']for r in root_rows)
    stable=all(sha(ROOT/k)==v for k,v in seen.items());assert stable
    report={'status':'CABLE_INCREMENT_SOURCE_COUNTED_PROCUREMENT_AND_PHYSICAL_OPEN','created_utc':datetime.now(timezone.utc).isoformat(),
        'scope':'Cable hardware increment only. Existing feeder/spin hardware and spring are excluded except four retained host nuts and the explicit bolt/washer replacement. No source edit, new manufacturer search, procurement, slicing or printing.',
        'source_sha256':seen,'sources_stable':stable,'quantity_is_not_strength_or_purchase_proof':True,
        'axis_contract':{'source_table':axis_rows,'source_evidence':axis_bom_ev,
            'full_audited_hardware_modules':axis_full_modules,'native_contract_file':NATIVE_DIR+'/scene-contract-decoded.json',
            'native_axis_bom_matches_source_with_tolerance_mm':1e-9,
            'adopted_axis_fields':{k:v for k,v in native_ci.items() if k.startswith(('axis_','bush_'))},
            'ring_is_required_but_no_actual_shape_mesh':True,
            'supplier_evidence_reuse_scope':'Only selected pin/ring, tail-washer table, ID10 thrust-washer table and POM design requirements are reused. Historical reports embedded CAD hashes and old axis/cotter conclusions are not current-source validation.'},
        'difference_from_previous_cable_increment':{'historical_report':PREVIOUS_BOM,
            'count_delta':dict(sorted(count_delta.items())),
            'same_count_specification_changes':['replaceable-bush: round OD12 unspecified material -> machined unfilled POM-C AF12, ID8.2, L11',
                'thrust-washer: ID8.4 unspecified material -> SWSPS16-10-.25 catalogue nylon, ID10'],
            'all_other_item_counts_unchanged':True,'old_records_overwritten':False},
        'items':items,'installation_sites':sites,'installed_occurrences':occurrences,'procurement_roots_not_additive_with_members':root_rows,
        'replacement_delta':{'positions_CAD_XZ':[[x,z]for x in value(SH,'sh_bolt_x')for z in value(SH,'sh_bolt_z')],
            'remove_from_old_BOM':[{'item':'M4x20 socket head D7 H4','quantity':4},{'item':'M4 flat washer OD9 ID4.3 t0.8 at old Y-54.8','quantity':4}],
            'add_to_current_BOM':[{'item_id':'m4x60-socket','quantity':4},{'item_id':'m4-flat-washer','quantity':4}],
            'retain_from_old_BOM':[{'item_id':'m4-nut','quantity':4,'nominal':'M4 SW7 H3.2'}],
            'reuse_old_washers_for_new_positions':'Possible only after actual part suitability check; CAD moves/replaces the washer instances and does not leave old washers stacked in place. No extra four retained washers may be counted.',
            'source_evidence':replacement_ev+old_ev+mount_ev},
        'non_double_count_rules':['ci_cable, co_wire and cr_wire are displayed segments of one continuous core, not three purchased wires.',
            'The Ø5 input ball is the core factory end, not another purchase.',
            'The M4 slotted clamping screw is included in the nipple assembly; no assumed-length extra grub screw is ordered.',
            'The housing inner liner belongs to housing-with-liner; it is not a second standalone hose.',
            'Complete-kit root and its steel core/ball/housing/ferrules/adjusters/nipple/M6-nut members are alternative accounting levels, not additive purchase lines.',
            'Manufacturer component-category list does not establish included quantities; required two adjusters/two ferrules/four M6 nuts must not be assumed fully covered by one kit.',
            'HCDG8-30 and supplied NETW7 each have one physical occurrence; input-axis-pin-kit is the only purchase root for that pair. The E-clip clearance-space mesh is not another component.',
            'The special capture washer remains separate from the four ordinary M4 host mounting washers; there are no ordinary M4 axis washers in this adopted axis.'],
        'open_items':[{'id':'output-m3-drive-envelope','detail':'Output cap source models M3x16 shaft and D5.5 H3 head without a drive recess or explicit drive designation; two output screws remain a distinct extraction row. Current assembly-selection layer can independently choose DIN912/ISO4762 and its tool; this extractor does not infer a recess from a cylinder or invalidate that explicit selection.'},
            {'id':'kit-contents-and-length','detail':'No selected/owned kit SKU or verified per-kit component counts; no final core/housing cut length. Stored1000/1200 catalog option is not an installation cut list.'},
            {'id':'axis-part-and-tool-acceptance','detail':'HCDG8-30 catalogue pair includes NETW7; engineering adoption is not actual seating/retention-load/tool acceptance. E-clip R10 and Z budget are engineering requirements, not guaranteed installed ring CAD. No central M4 bolt/nut/distance tube remains. POM-C bush is a machined design requirement, not a PETG print or supplied item; thrust washer is a catalogue ID10 configuration, not purchased stock.'},
            {'id':'ordinary-fastener-supply','detail':'Nominal CAD sizes do not select vendor, thread engagement quality, grade, torque or locking. No unrecorded manufacturer proof is invented.'},
            {'id':'seating-and-clamp','detail':'Ferrule bearing depth, crimp details, nipple screw length/drive/torque and wire holding force remain open. Modeled tail8 mm below nipple center /5.5 mm outside body is an installation maximum, not supplier minimum tail.'}],
        'not_in_increment':['original feeder return spring and its endpoint hardware','all unchanged feeder fasteners','spin head and hold-fork hardware','printed parts','lubricants and tools'],
        'checks':{'all_expected_new_counts_match':True,'unique_installation_and_occurrence_ids':True,'no_kit_children_in_additive_purchase_roots':True,
            'retained_m4_nuts_exactly_four':sum(o['change']=='retained_from_baseline'for o in occurrences)==4,
            'new_axis_matches_native_bom':True,'non_axis_counts_unchanged_from_history':True,
            'no_old_axis_tube_M4_bolt_or_M4_nut_occurrences':counts['steel-distance-tube']==counts['m4x35-socket']==counts['m4-nut']==0,
            'all_sources_stable':stable},
        'physical_acceptance':False,'purchased':False,'sent_to_printer':False}
    (OUT/'hardware.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    lines=['# 当前拉索五金增量','',
        '这是当前源的安装需要量，不是采购订单、强度证明或实物装配放行。逐安装位、模块、源码行与SHA见 [hardware.json](hardware.json)。未修改CAD或旧冻结报告。','',
        '**旧件替换：四颗M4×20及原四片安装垫片移除，改为四颗M4×60及四片新位置垫片；原四颗M4螺母保留。** 不叠装两组螺钉或两层安装垫片。旧垫片若要用于新位置，需确认实际规格，数量账仍只记四片。','',
        '| 独立五金 | 源中名义规格（mm） | 新安装需要量 |','|---|---|---:|']
    for it in items:
        if it['procurement_category']=='separate_purchase_root':lines.append(f"| {it['name_zh']} | {human_spec(it)} | {it['assembly_required_new_quantity']} |")
    lines+=['','M3×30合计3颗：主盖2、可调止挡1。M3×16合计8颗：输出端盖2、第三弯导向盖6；前者提取源未明确驱动型式，保留独立行，装配包可依据独立选型合并。M3螺母18颗；新增M4螺母为0，原背梁4颗保留。普通M4垫片4片仅用于长栓安装；输出专用捕获垫圈另1片，后者有Type A金属边与公差要求。','',
        '**新轴采购根：HCDG8-30套件1套，含销1根及NETW7卡簧1件。** 两者在实物安装表各计1；卡簧不重复下单。尾侧HRDW-M8-A2垫圈2片另计，头侧没有该垫圈。轴套为机加工无填充POM-C六角AF12、内孔8.2、长11；不是圆OD12套，也不是PETG打印件。两片推力垫片为SWSPS16-10-.25，内孔10。','',
        '销的订购名义尺寸是D8、头下至槽近壁L30；模型采用的D7.9905/L30.05是公差中点显示值，不是另一个订购规格。随附卡簧有物料身份，当前R10包络只是安装空间要求，没有用圆盘伪造实际E环实体。','',
        '| 完整拉索装配的成员 | 实际装配需要量 |','|---|---:|']
    for it in items:
        if it['procurement_category']=='kit_eligible_member':lines.append(f"| {it['name_zh']} | {it['assembly_required_new_quantity']} |")
    lines+=['','拉索根组件仅计1套。norelem 03096-14列出的钢芯、护套、端套、调节器、端头及薄螺母是套件成员，**不能再把完整kit与这些成员全量相加采购**。实际需要2个调节器、2个端套、4颗M6薄螺母；现有厂家证据未列每套各自件数，所以随货覆盖和补件数量均未定。M6平垫片4片另列。','',
        '钢芯分成输入/路线/输出显示仍只有1根；Ø5球头是其出厂固定端，不单买。输出端头的M4一字紧定螺钉是端头子组件，不另猜长度采购。护套包含内管。1000/1200只是保存的目录长度选项，不是已选SKU或最终裁切长度。','',
        '旧主轴5件已撤下：定距管1、M4×35螺栓1、普通M4轴垫片2、M4轴螺母1；新加销/随附环/尾垫共4件。轴套和推力片数量不变但规格已换。脚本断言其余每类拉索五金数量与历史提取一致，历史报告未覆盖。','',
        '实际卡簧完整入槽、工具末段可达性、保持载荷及真实打印尺寸仍需正式组件验收。POM-C牌号/加工来源尚未选定；推力片目录尺寸的历史径向图版与实购状态仍保留限制。普通螺钉强度等级、未明示螺距、扭矩和防松不由名义包络证明。输出两颗M3的驱动可在独立选型层落实，这里仅保留源事实。','',
        '新主体、扳机和主盖不能直接继承旧版三件的切片制造绑定；本报告只提取五金，不出新打印盘。','',
        f'厂家依据仅复用 [既有拉索原图证据]({ROOT}/docs/cable-hardware-evidence.md) 与 [既有垫圈证据]({ROOT}/docs/cable-washer-retention-review.md)。未新采购、联网搜图、切片或打印。底部送料、原回位弹簧、旋转头、工具和润滑不属于这份增量。','',
        f'新增轴依据：[原厂销与随附环]({ROOT}/{AXIS_SUPPLIER})、[尾垫供应表（仅standard_washer字段）]({ROOT}/{AXIS_TAIL})、[POM加工要求]({ROOT}/{AXIS_BUSH})、[ID10推力片表]({ROOT}/{AXIS_THRUST})。历史文档中的旧轴场景结论不移植到当前轴。原生合同与完整模块片段一并收入hardware.json。','',
        '复跑：','```sh','python3 -B scripts/extract_current_cable_hardware.py','```','']
    (OUT/'README.md').write_text('\n'.join(lines))
    print(json.dumps({'directory':str(OUT.relative_to(ROOT)),'status':report['status'],'sites':len(sites),'occurrence_records_including_nonadditive_children_and_retained':len(occurrences),
        'checks':report['checks'],'source_count':len(seen),'new_quantities':dict(counts),'hardware_json_sha256':sha(OUT/'hardware.json')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()

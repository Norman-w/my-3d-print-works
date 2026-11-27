#!/usr/bin/env python3
"""Source-bound cable hardware increment; no CAD edit/export, purchase or print.

This is an intentionally narrow extractor for the present audited module grammar.
Numeric lists are read from SCAD. Each fixed construction is asserted before its
audited BOM mapping is applied. Unsupported source changes fail closed.
"""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import ast, hashlib, json, math, re

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
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
    CI:'e243be6b39956ae2ac28bda58c8f3d92bcf4e9a04b28818d8b37d65dea276d07',
    CO:'6acd8783a2c4d865b824acabd6e2f5da446f544ea1431363bbfd50c61b2ca566',
    CRR:'26dd6865899162e94702b09428eeef627d10598c1bfe4ef90bb3b3be770f10c3',
    CT:'004c9050f34fe497db26d2c5e66e3cceefdb1cda0231e3d0f7e85d79f07a6254',
    SH:'7dc29833a648600dae69bab1f666d8d3ca1999a66493dec843d37afc6da9e9b8',
    CR:'5f7aa2f1c5ee59f0b90833ea8b9265c1fe96cf00420faf6991872c87085897f1',
    CSE:'c756235f815ba7c62d484792856654d950e87943733e75fa86eefdc4c08229c4'}
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
    source(str(Path(__file__).relative_to(ROOT)))
    for p in [CI,CO,CRR,CT,SH,CR,CSE,DOC,WASH,'docs/cable-trigger-input.md']:source(p)
    assert all(seen[p]==h for p,h in AUDITED_CAD_SHA.items()),'Audited CAD changed: re-audit complete hardware modules before counting; do not silently accept added calls.'
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
    for d,L,count in [(4,60,4),(4,35,1),(3,30,3),(3,8,2),(3,16,6),(3,25,4)]:
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
    spec('steel-distance-tube','主轴钢定距管',{'OD_mm':8,'ID_mm':4.3,'length_mm':15},open_fields=['supplier_or_machining_route','steel_grade','length_face_and_diameter_tolerances'])
    spec('replaceable-bush','主轴可换轴套',{'OD_mm':12,'ID_mm':8.2,'length_mm':11},open_fields=['material','supplier_or_machining_route','fit_tolerances','lubrication_compatibility'])
    spec('thrust-washer','主轴推力垫片',{'OD_mm':16,'ID_mm':8.4,'thickness_mm':.25},open_fields=['material','supplier_SKU','thickness_tolerance','lubrication_compatibility'])
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

    # Replacement: executable parent composition overrides the stale washer comment.
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
    axis=site('input-axis','ci_local_fixed_hardware / ci_local_moving_hardware','input local',{'x':0,'y':0,'axis':'Z'},[module_ev(CI,'ci_local_fixed_hardware'),module_ev(CI,'ci_local_moving_hardware')])
    for item,needle in [('steel-distance-tube',' ci_zring(0,0,-5.5,15,8,4.3);'),('m4x35-socket',' ci_zbolt(0,0,14.8,35,4,7,4,3);'),
        ('m4-flat-washer',' ci_zring(0,0,14,.8,9,4.3);'),('m4-flat-washer',' ci_zring(0,0,-12.8,.8,9,4.3);'),
        ('m4-nut',' difference(){ci_zhex(0,0,-16,3.2,7);ci_zcyl(0,0,-16.1,3.4,4.1);}'),('replaceable-bush',' ci_zring(0,0,-3.5,11,12,8.2);')]:add(axis,item,require(CI,needle))
    for z in [-3.75,7.5]:
        k=site(f'input-axis-thrust-z{fnum(z)}','ci_local_fixed_hardware','input local',{'x':0,'y':0,'z_start':z},require(CI,' for(z=[-3.75,7.5])ci_zring(0,0,z,.25,16,8.4);'))
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
    wire_ev=require(CI,'module ci_local_cable(u=ci_u,delta=ci_delta){',' ci_zring(0,0,-3.5,11,12,8.2);\n translate(ci_terminal)sphere(d=5);')+require(CO,'module co_wire(t=0){')+require(CSE,'    difference(){cr_wire();union(){ci_cable(0);co_wire(0);}}')
    k=site('continuous-cable','ci_local_cable + co_wire + cr_wire / cr_housing','continuous routed assembly',
        {'core_segments_are_one_physical_core':True,'fixed_ball_at_input':True,'cut_length_mm':None},wire_ev)
    parent=add(k,'core-with-fixed-ball',wire_ev);add(k,'integral-ball-end',wire_ev,parent=parent)
    add(k,'housing-with-liner',[ev(CR,'// Purchased flexible housing, NOT a printable part.')]+evidence_kit)

    counts=Counter(o['item_id']for o in occurrences if o['change']!='retained_from_baseline')
    expected={'m4x60-socket':4,'m4x35-socket':1,'m3x30-socket':3,'m3x8-socket':2,'m3x16-socket':6,'m3x16-output-cap-fastener':2,'m3x25-socket':4,
        'm3-nut':18,'m4-nut':1,'m3-flat-washer':14,'m4-flat-washer':6,'m4-capture-washer':1,'steel-distance-tube':1,
        'replaceable-bush':1,'thrust-washer':2,'m6-adjuster':2,'m6-thin-nut':4,'m6-flat-washer':4,'cable-ferrule':2,
        'output-nipple-assembly':1,'factory-m4-grub':1,'core-with-fixed-ball':1,'integral-ball-end':1,'housing-with-liner':1}
    assert counts==expected,(counts,expected)
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
    assert not any(r['purchase_root_id']in ['factory-m4-grub','integral-ball-end','core-with-fixed-ball']for r in root_rows)
    stable=all(sha(ROOT/k)==v for k,v in seen.items());assert stable
    report={'status':'CABLE_INCREMENT_SOURCE_COUNTED_PROCUREMENT_AND_PHYSICAL_OPEN','created_utc':datetime.now(timezone.utc).isoformat(),
        'scope':'Cable hardware increment only. Existing feeder/spin hardware and spring are excluded except four retained host nuts and the explicit bolt/washer replacement. No source edit, new manufacturer search, procurement, slicing or printing.',
        'source_sha256':seen,'sources_stable':stable,'quantity_is_not_strength_or_purchase_proof':True,
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
            'The special capture washer remains a separate specification row even though its nominal dimensions equal the six ordinary M4 mounting/axis washers.'],
        'open_items':[{'id':'stale-host-washer-comment','detail':'ci_mount_hardware_cad comment says host washers remain, but executable ct_original_fixed_hardware removes sh_bolts including its four washers; current input documentation agrees replacement. Counting follows composition, CAD comment not edited.',
                'evidence':require(CI,' // Original nuts/host washers remain in parent. THESE replace old screws.')+replacement_ev+old_ev},
            {'id':'output-m3-drive-envelope','detail':'Output cap source models M3x16 shaft and D5.5 H3 head without a drive recess or explicit drive designation; two output screws are therefore a separate row with drive/AF unknown, not silently merged with the six explicitly socket-head route screws. Verify intended/supplied drive; do not infer it from a solid cylinder.'},
            {'id':'kit-contents-and-length','detail':'No selected/owned kit SKU or verified per-kit component counts; no final core/housing cut length. Stored1000/1200 catalog option is not an installation cut list.'},
            {'id':'axis-parts-supply','detail':'Steel tube dimensions are specified, but source/grade/tolerances are open. Bush and thrust washer materials and sourcing are not specified.'},
            {'id':'ordinary-fastener-supply','detail':'Nominal CAD sizes do not select vendor, thread engagement quality, grade, torque or locking. No unrecorded manufacturer proof is invented.'},
            {'id':'seating-and-clamp','detail':'Ferrule bearing depth, crimp details, nipple screw length/drive/torque and wire holding force remain open. Modeled tail8 mm below nipple center /5.5 mm outside body is an installation maximum, not supplier minimum tail.'}],
        'not_in_increment':['original feeder return spring and its endpoint hardware','all unchanged feeder fasteners','spin head and hold-fork hardware','printed parts','lubricants and tools'],
        'checks':{'all_expected_new_counts_match':True,'unique_installation_and_occurrence_ids':True,'no_kit_children_in_additive_purchase_roots':True,
            'retained_m4_nuts_exactly_four':sum(o['change']=='retained_from_baseline'for o in occurrences)==4,'all_sources_stable':stable},
        'physical_acceptance':False,'purchased':False,'sent_to_printer':False}
    (OUT/'hardware.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    lines=['# 当前拉索五金增量','',
        f'这是当前源的安装需要量，不是采购订单、强度证明或实物装配放行。所有新增件仍为候选，未确认已购；逐安装位、模块、源码行与SHA见 [hardware.json]({OUT}/hardware.json)。未修改CAD或旧冻结报告。','',
        '**旧件替换：四颗M4×20及原四片安装垫片移除，改为四颗M4×60及四片新位置垫片；原四颗M4螺母保留。** 不叠装两组螺钉或两层安装垫片。旧垫片若要用于新位置，需确认实际规格，数量账仍只记四片。','',
        '| 独立五金 | 源中名义规格（mm） | 新安装需要量 |','|---|---|---:|']
    for it in items:
        if it['procurement_category']=='separate_purchase_root':lines.append(f"| {it['name_zh']} | {human_spec(it)} | {it['assembly_required_new_quantity']} |")
    lines+=['','M3×30合计3颗：主盖2、可调止挡1。M3×16合计8颗：输出端盖2、第三弯导向盖6；前者未明确驱动型式，暂分两行，不静默合为同SKU。M3螺母18颗；主轴另需新增M4螺母1颗，不能与保留的原4颗混淆。普通M4垫片6片＝安装4＋主轴2，专用捕获垫圈另1片，虽名义相同但后者有Type A金属边与公差要求。','',
        '| 完整拉索装配的成员 | 实际装配需要量 |','|---|---:|']
    for it in items:
        if it['procurement_category']=='kit_eligible_member':lines.append(f"| {it['name_zh']} | {it['assembly_required_new_quantity']} |")
    lines+=['','拉索根组件仅计1套。norelem 03096-14列出的钢芯、护套、端套、调节器、端头及薄螺母是套件成员，**不能再把完整kit与这些成员全量相加采购**。实际需要2个调节器、2个端套、4颗M6薄螺母；现有厂家证据未列每套各自件数，所以随货覆盖和补件数量均未定。M6平垫片4片另列。','',
        '钢芯分成输入/路线/输出显示仍只有1根；Ø5球头是其出厂固定端，不单买。输出端头的M4一字紧定螺钉是端头子组件，不另猜长度采购。护套包含内管。1000/1200只是保存的目录长度选项，不是已选SKU或最终裁切长度。','',
        '输入主轴钢定距管、可换轴套和推力垫片各自的实际材质/公差/来源仍需落实；尤其轴套及推力垫片材质未指定。普通螺钉强度等级、螺距未明示之处、紧固扭矩、防松和真实供货规格均未由名义包络证明。输出两颗M3头部仅画了外形，内六角驱动没有在该模块切出，不能当实际工具匹配证据。','',
        '源注释冲突保留：输入安装模块写“旧垫片保留”，但可执行父组合减去的sh_bolts包含原垫片；本清单按实际组合和当前输入文档记为替换，未修改原注释。','',
        f'厂家依据仅复用 [既有拉索原图证据]({ROOT}/docs/cable-hardware-evidence.md) 与 [既有垫圈证据]({ROOT}/docs/cable-washer-retention-review.md)。未新采购、联网搜图、切片或打印。底部送料、原回位弹簧、旋转头、工具和润滑不属于这份增量。','',
        '复跑：','```sh','/Applications/FreeCAD.app/Contents/Resources/bin/python -B output/current-assembly-package/cable-hardware/extract.py','```','']
    (OUT/'README.md').write_text('\n'.join(lines))
    print(json.dumps({'status':report['status'],'sites':len(sites),'occurrence_records_including_nonadditive_children_and_retained':len(occurrences),
        'checks':report['checks'],'source_count':len(seen),'new_quantities':dict(counts),'hardware_json_sha256':sha(OUT/'hardware.json')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()

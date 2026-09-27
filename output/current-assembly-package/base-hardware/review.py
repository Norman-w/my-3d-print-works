#!/usr/bin/env python3
"""Read-only physical fastener inventory from current module call sites.

No old BOM quantities drive enumeration. The old JSON is read only AFTER all
installation records are built, as a comparison. A screw's primitive head and
shaft count as ONE item. Working/held modes share physical item IDs.
"""
from pathlib import Path
import ast, collections, hashlib, json, math, re
from datetime import datetime, timezone

OUT=Path(__file__).resolve().parent; ROOT=OUT.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def clean(s):return re.sub(r'//[^\n]*','',re.sub(r'/\*.*?\*/','',s,flags=re.S))
def module(path,name):
    raw=(ROOT/path).read_text();s=clean(raw)
    m=re.search(r'\bmodule\s+'+name+r'\s*\([^)]*\)\s*\{',s)
    assert m,(path,name);i=m.end();level=1
    while level:
        level+=(s[i]=='{')-(s[i]=='}');i+=1
    start=raw.index('module '+name+'(')
    return {'file':path,'line':raw[:start].count('\n')+1,'module':name,
      'body':s[m.end():i-1].strip(),'source_sha256':sha(ROOT/path)}
MODULES={}
def source(path,name):
    k=path+':'+name
    if k not in MODULES:MODULES[k]=module(path,name)
    return k
def check(path,name,substring):
    k=source(path,name)
    assert re.sub(r'\s+','',substring) in re.sub(r'\s+','',MODULES[k]['body']),(name,substring)
    return k
def recurse(paths):
    seen=set();ordered=[]
    def read(p):
        p=p.resolve()
        if p in seen:return
        seen.add(p)
        for q in re.findall(r'\b(?:include|use)\s*<([^>]+)>',clean(p.read_text())):read(p.parent/q)
        ordered.append(p)
    for p in paths:read(ROOT/p)
    return ordered
class Params:
    def __init__(self,roots):
        self.files=recurse(roots);self.expr={};self.values={};self.used={}
        for p in self.files:
            raw=clean(p.read_text())
            for m in re.finditer(r'^\s*(\w+)\s*=\s*([^;]+);',raw,re.M):self.expr[m[1]]=(m[2],p)
    def get(self,k):
        if k not in self.values:
            e,p=self.expr[k];self.values[k]=self.node(ast.parse(e,mode='eval').body)
            self.used[k]={'value':self.values[k],'expression':e,'source':str(p.relative_to(ROOT))}
        return self.values[k]
    def node(self,n):
        if isinstance(n,ast.Constant):return n.value
        if isinstance(n,ast.Name):return self.get(n.id)
        if isinstance(n,ast.List):return [self.node(v)for v in n.elts]
        if isinstance(n,ast.UnaryOp):return -self.node(n.operand)if isinstance(n.op,ast.USub)else self.node(n.operand)
        if isinstance(n,ast.Subscript):return self.node(n.value)[self.node(n.slice)]
        if isinstance(n,ast.BinOp):
            a,b=self.node(n.left),self.node(n.right)
            if isinstance(n.op,ast.Add):return a+b
            if isinstance(n.op,ast.Sub):return a-b
            if isinstance(n.op,ast.Mult):return a*b
            if isinstance(n.op,ast.Div):return a/b
        if isinstance(n,ast.Call):
            a=[self.node(x)for x in n.args]
            if n.func.id=='sin':return math.sin(math.radians(a[0]))
            if n.func.id=='cos':return math.cos(math.radians(a[0]))
            if n.func.id=='sqrt':return math.sqrt(a[0])
            if n.func.id=='max':return max(a)
        raise ValueError(ast.dump(n))

F=Params(['cad/launcher-final-assembly.scad']);S=Params(['cad/spin-complete-hardware.scad'])
f=F.get;s=S.get
specs={}
def spec(k,description,dimensions,selection='dimension-envelope candidate; supplier/material/thread tolerance unselected',old=None):
    specs[k]={'id':k,'description':description,'dimensions_mm':dimensions,'selection_status':selection,
      'purchased':False,'printable':False,'legacy_feeder_id':old}
for d,l,qtydummy in [(3,12,0),(3,16,0),(3,20,0),(4,20,0),(4,30,0),(3,10,0),(3,45,0),(4,16,0)]:
    spec(f'M{d}x{l}-socket',f'M{d}×{l} 圆柱头内六角',{'thread_nominal_d':d,'length_under_head':l,'head_d':5.5 if d==3 else 7,'head_h':3 if d==3 else 4,'hex_key':2.5 if d==3 else 3},old=f'M{d}x{l}'if(d,l)in[(3,12),(3,16),(3,20),(4,20),(4,30)]else None)
spec('M3x10-countersunk-DIN7991','DIN7991 M3×10 90°沉头内六角',{'thread_nominal_d':3,'length_total_including_head':10,'head_d':6,'head_h':1.7,'hex_key':2},'Named standard/dimensions previously selected; no new supplier or stock validation')
for d,af,h in [(2,4,1.6),(3,5.5,2.4),(4,7,3.2)]:
    spec(f'M{d}-nut',f'M{d} 六角螺母 AF{af}×{h}',{'thread_nominal_d':d,'across_flats':af,'thickness':h},old=f'M{d}-nut')
for k,d,od,h,old in [('M3-washer-7x0.5',3.2,7,.5,'M3-washer'),('M4-washer-9x0.8',4.3,9,.8,'M4-washer9'),('M4-washer-12x0.8',4.3,12,.8,'M4-washer12'),('M4-washer-8x0.5',4.3,8,.5,'M4-washer8')]:
    spec(k,f'平垫 ID{d}/OD{od}×{h}',{'ID':d,'OD':od,'thickness':h},old=old)
specs['M4-washer-12x0.8']['selection_status']='Exact dimensional candidate; not interchangeable with arbitrary DIN9021'
specs['M4-washer-8x0.5']['selection_status']='DIN433/ISO7092 size; earlier Accu HRDW-M4-A2 candidate; no new stock validation'
spec('follower-07534-04X12','norelem 07534-04X12 随动肩销',{'shoulder_d':4,'shoulder_length':12,'thread_d':3,'thread_length':7,'head_d':7,'head_h':3,'hex_key':2},'Named catalog candidate; diameter tolerance and actual form remain unresolved',old='follower-shoulder')
spec('M2x4-flat-set','M2×4 平端紧定螺钉，DIN913尺寸',{'thread_d':2,'length':4,'hex_key':.9,'tip_nominal_d':1},old='M2x4-set')
spec('pin-D3x6','Ø3×6 平头定位销',{'diameter':3,'length':6},old='seam-pin')
spec('M4-threaded-rod-100','M4×100 全牙杆',{'thread_d':4,'length':100},old='M4-rod100')
for fixed,L in [(True,16),(False,10)]:
    spec('return-shoulder-'+('fixed'if fixed else'moving'),f'MISUMI HDMSB4-{L}-F9-M3',{'shoulder_d':4,'shoulder_length':L,'thread_d':3,'thread_length':9,'head_d':7,'head_h':3},'Named MISUMI candidate; no new supplier/stock/fit validation',old='return-shoulder-'+('fixed'if fixed else'moving'))
spec('return-spring','Lee Spring LEM063CA 03 M 拉伸弹簧',{'OD':f('rs_spring_od'),'wire_d':f('rs_wire'),'free_inside_loop_length':f('rs_spring_L0')},'Named catalog candidate; F0=1.67N,k=.25N/mm; not actual return acceptance',old='return-spring')
spec('M2.5x20-socket','Bossard BN610/1422898 M2.5×20全牙圆柱头',{'thread_d':2.5,'length_under_head':20,'head_d_max':4.5,'head_h_max':2.5,'hex_key':2},'Previously selected catalog candidate, A2; native CAD retains larger D5/H3 reference envelope',old='M2_5x20')
spec('M2.5-nut','Bossard BN628/1241427 M2.5 六角螺母',{'thread_d':2.5,'across_flats':5,'thickness_max':2},'Previously selected DIN934 catalog candidate, A2; no new procurement',old='M2_5-nut')
spec('M2.5-washer','Bossard BN715/1777491 M2.5 平垫',{'ID':2.7,'OD':6,'thickness_nominal':.5},'Previously selected steel 140HV zinc-plated candidate; thickness tolerance not established',old='M2_5-washer')
spec('M4x25-DIN464-knob','DIN464 M4×25 预压手拧件',{'thread_d':4,'length_under_shoulder':25,'head_d':16,'shoulder_d':8,'head_total_h':9.5,'rim_h':3.5},'ELESA+GANTER dimensional candidate; not an arbitrary printed knob')
spec('spin-spring','Lee Spring LC016DE10M 压缩弹簧',{'OD':s('sh_spring_candidate_od'),'wire_d':s('sh_spring_candidate_wire'),'free_length':s('sh_spring_candidate_free_length'),'solid_height':s('sh_spring_candidate_solid_height')},'Catalog initial candidate; k=.14N/mm; physical preload/rotation open')

items=[]
def add(scope,site,role,k,anchor,axis,src,motion='fixed',modes=None,notes=None):
    assert k in specs
    items.append({'instance_id':scope+'/'+site+'/'+role,'scope':scope,'site_id':site,'role':role,'spec_id':k,'quantity':1,
      'coordinate_system':'feeder CAD'if scope=='feeder-base38'else'spin-head local CAD before whole-scene mounting',
      'anchor_mm':anchor,'anchor_definition':'source cylinder base / nut or washer near face; bolt shaft base unless site notes say otherwise',
      'axis':axis,'motion':motion,'source_modules':src,'installed_modes':modes or(['base']if scope=='feeder-base38'else['work','held']),
      'notes':notes or[]})
def fs(site,role,k,pos,axis,src,**kw):add('feeder-base38',site,role,k,pos,axis,src,**kw)
def ss(site,role,k,pos,axis,src,**kw):add('spin10',site,role,k,pos,axis,src,**kw)

# Authoritative roots; legacy visual helpers are deliberately NOT included.
la=check('cad/launcher-final-assembly.scad','la_fixed_hardware','cg_old_hardware(false);')
lm=check('cad/launcher-final-assembly.scad','la_moving_hardware','ps_original_pins(t);ps_added_hardware(t);rs_endpoint_hardware(false,t);')
show=check('cad/launcher-final-assembly.scad','la_show','rs_spring(la_t);')
oldroot=check('cad/feeder-cam-guide-revision.scad','cg_old_hardware','if(include_caps)feeder_cap_hardware();')
check('cad/feeder-cam-guide-revision.scad','cg_old_hardware','for(side=[-1,1],g=[0,-gate_spacing])scale([side,1,1])revision_hardware_local(g,.9);')
check('cad/feeder-complete-hardware.scad','fh_added_hardware','fh_seam_bolts();fh_seam_nuts();fh_mount_nuts();')
check('cad/outlet-retention.scad','or_hardware','or_rod_hardware();or_split_hardware();')
check('cad/inlet-retention-final.scad','ir_hardware','ir_clamp_hardware(closure);ir_anchor_hardware();')
source('cad/feeder-frame-y-guide.scad','yg_cap_hardware_local')

# Shell seam: 2 Y positions x 4 Z stations, each a bolt and nut.
sb=source('cad/feeder-complete-hardware.scad','fh_seam_bolts');sn=source('cad/feeder-complete-hardware.scad','fh_seam_nuts')
for y in [-f('fh_seam_y'),f('fh_seam_y')]:
 for z in f('fh_seam_z'):
    site=f'shell-seam/y{y:g}-z{z:g}'
    fs(site,'bolt','M3x12-socket',[f('fh_seam_head_under_x')-12,y,z],[1,0,0],[la,sb])
    fs(site,'nut','M3-nut',[f('fh_seam_nut_x'),y,z],[1,0,0],[la,sn])
# Side supports: current cap clearance modifies printed parts only.
mb=source('cad/feeder-supports.scad','feeder_mount_hardware');mn=source('cad/feeder-complete-hardware.scad','fh_mount_nuts')
for side in [-1,1]:
 for z in f('support_mount_z'):
    site=f'support-mount/side{side}-z{z:g}'
    fs(site,'bolt','M3x12-socket',[side*32,f('support_mount_y'),z],[side,0,0],[la,oldroot,mb])
    fs(site,'washer','M3-washer-7x0.5',[side*43.5,f('support_mount_y'),z],[side,0,0],[la,oldroot,mb],notes=['Native display uses a solid OD7/.5 disk overlapping the screw; ID3.2 is the retained dimensional selection, not a separate through-hole rendered here.'])
    fs(site,'nut','M3-nut',[side*f('fh_mount_nut_x'),f('fh_mount_y'),z],[side,0,0],[la,mn])
# Four radial carrier gibs: jack screw + two nuts + washer; 2 cover screws,
# each with one washer/nut. All positions independently expanded per gate.
rev=source('cad/feeder-guide-revision.scad','revision_hardware_local')
rearface=f('revision_front_retracted')+.9-f('revision_contact_depth')-f('revision_web_depth')
for side in [-1,1]:
 for g in [0,-f('gate_spacing')]:
    x=side*f('revision_jack_x');site=f'carrier-Y/side{side}-gate{g:g}/jack'
    fs(site,'bolt','M3x16-socket',[x,rearface-16,g],[0,1,0],[la,oldroot,rev])
    for role,y in [('captured-nut',f('revision_keeper_front_y')-f('nut_depth')),('locknut',f('revision_keeper_back_y')-.5-2.4)]:fs(site,role,'M3-nut',[x,y,g],[0,1,0],[la,oldroot,rev])
    fs(site,'washer','M3-washer-7x0.5',[x,f('revision_keeper_back_y')-.5,g],[0,1,0],[la,oldroot,rev])
    for dz in [-f('revision_keeper_bolt_z'),f('revision_keeper_bolt_z')]:
       site=f'carrier-Y/side{side}-gate{g:g}/keeper{dz:g}'
       fs(site,'bolt','M3x12-socket',[x,f('revision_keeper_back_y')-.5,g+dz],[0,1,0],[la,oldroot,rev])
       fs(site,'washer','M3-washer-7x0.5',[x,f('revision_keeper_back_y')-.5,g+dz],[0,1,0],[la,oldroot,rev])
       fs(site,'nut','M3-nut',[x,f('revision_boss_front_y')-f('nut_depth'),g+dz],[0,1,0],[la,oldroot,rev])
# Current common X guide: two cover stations, two jack stations.
cg=source('cad/feeder-cam-guide-revision.scad','cg_new_hardware')
for z in f('cg_mount_z'):
    site=f'frame-X/cover-z{z:g}';y=f('cg_mount_y');under=f('cg_cover_outer_x')+f('cg_washer_h')
    fs(site,'bolt','M3x16-socket',[under-f('cg_mount_length'),y,z],[1,0,0],[la,cg])
    fs(site,'washer','M3-washer-7x0.5',[f('cg_cover_outer_x'),y,z],[1,0,0],[la,cg])
    fs(site,'nut','M3-nut',[f('cg_mount_nut_x')+f('nut_depth')-f('cg_nut_h'),y,z],[1,0,0],[la,cg])
cg_bands=[[f('support_guide_z0'),f('support_cap_screw_z')[0]-3.1],[f('support_cap_screw_z')[1]+3.1,f('support_guide_z1')]]
check('cad/feeder-cam-guide-revision.scad','cg_new_hardware','for(z=cg_jack_z)')
back=f('cg_front_retracted')-f('cg_setting')+f('cg_tooth_length')+f('cg_spine_thickness')
for z in [sum(b)/2 for b in cg_bands]:
    site=f'frame-X/jack-z{z:g}';y=f('cg_jack_y')
    fs(site,'bolt','M3x16-socket',[back,y,z],[1,0,0],[la,cg])
    fs(site,'washer','M3-washer-7x0.5',[f('cg_cover_outer_x'),y,z],[1,0,0],[la,cg])
    for role,x in [('captured-nut',f('cg_case_face_x')+f('nut_depth')-f('cg_nut_h')),('locknut',f('cg_cover_outer_x')+f('cg_washer_h'))]:fs(site,role,'M3-nut',[x,y,z],[1,0,0],[la,cg])
# Current common Y guide REPLACES the old 4 cap fasteners, not additive.
yg=source('cad/feeder-frame-y-guide.scad','yg_station_hardware_local');ygr=source('cad/feeder-frame-y-guide.scad','yg_hardware')
for side in [-1,1]:
 for z in f('support_cap_screw_z'):
    site=f'frame-Y/side{side}/cover-z{z:g}';x=side*f('support_cap_screw_x')
    fs(site,'bolt','M3x20-socket',[x,f('yg_cap_top')+.5-f('yg_mount_length'),z],[0,1,0],[la,ygr,yg])
    fs(site,'washer','M3-washer-7x0.5',[x,f('yg_cap_top'),z],[0,1,0],[la,ygr,yg])
    fs(site,'nut','M3-nut',[x,18.1,z],[0,1,0],[la,ygr,yg])
 for z in [sum(b)/2 for b in f('yg_bands')]:
    site=f'frame-Y/side{side}/jack-z{z:g}';x=side*f('yg_jack_x');tip=f('yg_face')+f('yg_spine_back')
    assert f('yg_pitch')==0 and f('yg_gib_dz')==0
    fs(site,'bolt','M3x16-socket',[x,tip,z],[0,1,0],[la,ygr,yg])
    fs(site,'washer','M3-washer-7x0.5',[x,f('yg_lock_top'),z],[0,1,0],[la,ygr,yg])
    for role,y in [('captured-nut',f('yg_nut_y')),('locknut',f('yg_lock_top')+.5)]:fs(site,role,'M3-nut',[x,y,z],[0,1,0],[la,ygr,yg])
# Four V followers: shaft/nut retained once, plus one M2 set screw and nut.
ps=source('cad/feeder-pin-seat-revision.scad','ps_original_pins');pa=source('cad/feeder-pin-seat-revision.scad','ps_added_hardware')
source('cad/feeder-pin-seat-revision.scad','ps_jack_local');source('cad/feeder-pin-seat-revision.scad','ps_nut_local')
cp=source('cad/cam-study.scad','cam_pin_local');cn=source('cad/cam-study.scad','cam_follower_nut')
for side in [-1,1]:
 for rear in [False,True]:
    r=f('finger_open_center_r')if rear else f('finger_closed_center_r');z=-f('gate_spacing')if rear else 0;site=f'follower/side{side}-'+('rear'if rear else'front');motion=f'gate radial cam_gate_r(rear={rear},t); listed at t=0'
    fs(site,'shoulder','follower-07534-04X12',[side*(r+f('cam_follower_offset')),f('cam_pin_start_y'),z],[0,1,0],[lm,ps,cp],motion=motion)
    fs(site,'shoulder-nut','M3-nut',[side*(r+f('cam_follower_offset')),-f('cam_carrier_width')/2+.2,z],[0,1,0],[lm,ps,cn],motion=motion)
    fs(site,'V-jack','M2x4-flat-set',[side*(r+f('ps_block_back')),f('ps_jack_y'),z],[side,0,0],[lm,pa],motion=motion)
    fs(site,'V-nut','M2-nut',[side*(r+f('ps_nut_x0')),f('ps_jack_y'),z],[side,0,0],[lm,pa],motion=motion)
# Seam registration pins.
sp=source('cad/feeder-seam-candidate.scad','seam_pins')
for i,(y,z) in enumerate(zip(f('seam_locator_y'),f('seam_locator_z'))):fs(f'seam-locator/{i}','pin','pin-D3x6',[-f('seam_hole_depth'),y,z],[1,0,0],[la,sp])
# Original harness bolts AND washers are an explicit later replacement group.
hb=source('cad/feeder-support-harness.scad','sh_bolts');hn=source('cad/feeder-support-harness.scad','sh_nuts')
for x in f('sh_bolt_x'):
 for z in f('sh_bolt_z'):
    site=f'beam-host/x{x:g}-z{z:g}'
    fs(site,'bolt','M4x20-socket',[x,-54.8,z],[0,1,0],[la,hb],notes=['Cable system removes sh_bolts(): replace this bolt with input module M4x60.'])
    fs(site,'washer','M4-washer-9x0.8',[x,-54.8,z],[0,1,0],[la,hb],notes=['Contained in sh_bolts(), therefore removed with that module; cable increment supplies its new head washer once.'])
    fs(site,'nut','M4-nut',[x,f('sh_nut_y'),z],[0,1,0],[la,hn],notes=['Retain existing nut in cable adoption; do not add a second nut at the same site.'])
# Outlet: 2 full-thread rods, four clamped levels per rod; 4 split bolts.
orr=source('cad/outlet-retention.scad','or_rod_hardware');ors=source('cad/outlet-retention.scad','or_split_hardware')
for y in [-f('or_rod_y'),f('or_rod_y')]:
    site=f'outlet/rod-y{y:g}';fs(site,'rod','M4-threaded-rod-100',[0,y,f('or_rod_z0')],[0,0,1],[la,orr])
    levels=[f('or_capture_z0')-f('or_washer_t'),f('or_capture_z1'),f('or_clamp_z0')-f('or_washer_t'),f('or_clamp_z1')]
    for i,z in enumerate(levels):
       fs(site,f'washer-{i}','M4-washer-12x0.8',[0,y,z],[0,0,1],[la,orr])
       nz=z-f('or_m4_nut_h')if i%2==0 else z+f('or_washer_t')
       fs(site,f'nut-{i}','M4-nut',[0,y,nz],[0,0,1],[la,orr])
for k,z in enumerate(f('or_closure_z')):
 for y in [-f('or_closure_y'),f('or_closure_y')]:
    site=f'outlet/split{k}-y{y:g}';face=f('or_ear_outer_x')
    fs(site,'bolt','M4x30-socket',[face+f('or_washer_t')-30,y,z],[1,0,0],[la,ors])
    fs(site,'washer','M4-washer-12x0.8',[face,y,z],[1,0,0],[la,ors])
    fs(site,'nut','M4-nut',[-face+.2,y,z],[1,0,0],[la,ors])
# Real spring endpoints, each shoulder bolt, 2 small M4 washers, M3 washer/nut.
rs=source('cad/feeder-return-spring.scad','rs_endpoint_hardware');rp=source('cad/feeder-return-spring.scad','rs_pin');rw=source('cad/feeder-return-spring.scad','rs_washer')
for fixed in [True,False]:
    site='return/'+('fixed'if fixed else'moving');z=f('rs_fixed_z')if fixed else f('rs_moving_z');seat=18.5 if fixed else 24.5;motion='fixed'if fixed else'frame translation [0,0,20*t]'
    fs(site,'shoulder','return-shoulder-'+('fixed'if fixed else'moving'),[f('rs_x'),seat-f('rs_thread_length'),z],[0,1,0],[la if fixed else lm,rs,rp],motion=motion)
    for i,y in enumerate([f('rs_spacer_end_y'),f('rs_head_y')-.5]):fs(site,f'eye-washer-{i}','M4-washer-8x0.5',[f('rs_x'),y,z],[0,1,0],[rs,rw],motion=motion)
    fs(site,'bearing-washer','M3-washer-7x0.5',[f('rs_x'),18 if fixed else 24,z],[0,1,0],[rs],motion=motion)
    fs(site,'nut','M3-nut',[f('rs_x'),(14 if fixed else 20)-f('rs_nut_h'),z],[0,1,0],[rs],motion=motion)
fs('return','spring','return-spring',[f('rs_x'),f('rs_y'),f('rs_fixed_z')],[0,0,1],[show,source('cad/feeder-return-spring.scad','rs_spring')],motion='deformable spring reference; fixed/moving eye endpoints; one physical spring')
# New inlet hardware is included once by la_fixed_hardware.
ic=source('cad/inlet-retention-final.scad','ir_clamp_hardware');ian=source('cad/inlet-retention-final.scad','ir_anchor_hardware');im=source('cad/inlet-retention-final.scad','ir_m4_nuts')
for x in [-f('ir_ear_x'),f('ir_ear_x')]:
    site=f'inlet/clamp-x{x:g}';z=f('ir_z')
    fs(site,'bolt','M4x30-socket',[x,12.8-30,z],[0,1,0],[la,ic])
    fs(site,'washer','M4-washer-12x0.8',[x,12,z],[0,1,0],[la,ic])
    fs(site,'nut','M4-nut',[x,-11.6,z],[0,1,0],[la,ic,im])
for x in [-f('ir_key_x'),f('ir_key_x')]:
    site=f'inlet/anchor-x{x:g}';z=f('ir_key_z')
    fs(site,'bolt','M2.5x20-socket',[x,-57.5,z],[0,1,0],[la,ian],notes=['CAD head D5/H3 remains conservative to previously selected Bossard D4.5/H2.5 maxima; do not call the two representations identical.'])
    for i,y in enumerate([-57.5,-42]):fs(site,f'washer-{i}','M2.5-washer',[x,y,z],[0,1,0],[la,ian])
    fs(site,'nut','M2.5-nut',[x,-41.5,z],[0,1,0],[la,ian])

# Spin complete hardware: use the full hardware library, NOT both old visual
# hardware_reference()/added_nuts() and the full library simultaneously.
sr=source('cad/spin-complete-hardware.scad','sch_hardware')
check('cad/spin-complete-hardware.scad','sch_latch_hardware','sch_x_nut(sh_latch_nut_x+.3,0,sh_latch_bolt_z);if(held)')
for group,stations in [('cover',[(y,z)for y in[-18,18]for z in[27,61]]),('cage',[(y,43)for y in[-11,11]])]:
    sm=source('cad/spin-complete-hardware.scad',f'sch_{group}_hardware')
    for y,z in stations:
       site=f'{group}/y{y:g}-z{z:g}'
       ss(site,'bolt','M3x12-socket',[47,y,z],[1,0,0],[sr,sm]);ss(site,'nut','M3-nut',[49.3,y,z],[1,0,0],[sr,sm])
sm=source('cad/spin-complete-hardware.scad','sch_guide_hardware')
for z in [20,66]:
    site=f'opposite-guide/z{z}'
    ss(site,'bolt','M3x10-socket',[-31-s('sh_opposite_washer_t')+s('sh_opposite_screw_length'),0,z],[-1,0,0],[sr,sm])
    ss(site,'washer','M3-washer-7x0.5',[-31-s('sh_opposite_washer_t'),0,z],[1,0,0],[sr,sm])
    ss(site,'nut','M3-nut',[s('sh_opposite_nut_x'),0,z],[1,0,0],[sr,sm])
sm=source('cad/spin-complete-hardware.scad','sch_keeper_hardware')
for y in [-7,7]:
    site=f'pad-keeper/y{y}';motion='spin carriage translation [float,0,0]; reference float=0'
    ss(site,'bolt','M3x10-countersunk-DIN7991',[26.75,y,s('sh_keeper_head_top')-10],[0,0,1],[sr,sm],motion=motion)
    ss(site,'nut','M3-nut',[26.75,y,57.1],[0,0,1],[sr,sm],motion=motion)
sm=source('cad/spin-complete-hardware.scad','sch_pull_hardware')
ss('pull-cap','bolt','M3x45-socket',[s('sh_pull_cap_x')+s('sh_pull_cap_length')-45,0,s('sh_pull_z')],[1,0,0],[sr,sm],motion='spin carriage translation [float,0,0]')
ss('pull-cap','nut','M3-nut',[s('sh_pull_nut_x')+.3,0,s('sh_pull_z')],[1,0,0],[sr,sm],motion='spin carriage translation [float,0,0]')
sm=source('cad/spin-complete-hardware.scad','sch_latch_hardware')
ss('hold-fork','nut','M3-nut',[s('sh_latch_nut_x')+.3,0,s('sh_latch_bolt_z')],[1,0,0],[sr,sm],notes=['Captured nut stays in cover in BOTH modes; count once.'])
ss('hold-fork','bolt','M3x16-socket',[s('sh_latch_bolt_seat_x')+s('sh_latch_washer_t')-16,0,s('sh_latch_bolt_z')],[1,0,0],[sr,sm],modes=['held'],notes=['Only installed with hold fork after pulling clear, stop air and empty balls; stored off the working assembly.'])
ss('hold-fork','washer','M3-washer-7x0.5',[s('sh_latch_bolt_seat_x'),0,s('sh_latch_bolt_z')],[1,0,0],[sr,sm],modes=['held'])
sm=source('cad/spin-complete-hardware.scad','sch_clamp_hardware')
ss('PC-clamp','bolt','M4x16-socket',[-34,-11,-13],[0,1,0],[sr,sm]);ss('PC-clamp','nut','M4-nut',[-34,-6.9,-13],[0,1,0],[sr,sm])
sm=source('cad/spin-complete-hardware.scad','sch_preload_hardware');tip=s('sh_spring_seat_front_x')+s('sh_spring_seat_thickness')
ss('preload','knob','M4x25-DIN464-knob',[tip,0,43],[1,0,0],[sr,sm],motion='assembly preload -p along X; reference p=0')
ss('preload','captured-nut','M4-nut',[55.8,0,43],[1,0,0],[sr,sm]);ss('preload','locknut','M4-nut',[65,0,43],[1,0,0],[sr,sm])
ss('pad-force','spring','spin-spring',[s('sh_carrier_back_x'),0,43],[1,0,0],[source('cad/spin-complete-hardware.scad','sch_spring')],motion='one deformable compression spring between moving carriage and adjustable seat')

assert len({i['instance_id']for i in items})==len(items)
def totals(scope=None,mode=None):return dict(sorted(collections.Counter(i['spec_id']for i in items if (scope is None or i['scope']==scope)and(mode is None or mode in i['installed_modes'])).items()))
base=totals('feeder-base38');work=totals('spin10','work');held=totals('spin10','held')
# Comparison only, AFTER independently expanding all current installation sites.
old=json.loads((ROOT/'output/manufacturing/feeder-hardware-bom.json').read_text());oldqty={i['id']:i['quantity']for i in old['items']}
aliases={'M2x4-set':'M2x4','M4-washer9':'M4-washer','M4-rod100':'M4x100'}
oldids=set(oldqty)
comparison=[]
for k,q in base.items():
    oid=specs[k]['legacy_feeder_id'];candidates=[oid,aliases.get(oid)]
    oid=next((a for a in candidates if a in oldqty),None)
    comparison.append({'spec_id':k,'source_enumerated_quantity':q,'legacy_id':oid,'legacy_quantity':oldqty.get(oid),'equal':q==oldqty.get(oid)})
    if oid:oldids.remove(oid)
assert len(base)==22 and sum(base.values())==195
assert sum(work.values())==31 and sum(held.values())==33
assert not oldids and all(x['equal']for x in comparison)
files=set(F.files+S.files)|{ROOT/'docs/final-feeder-hardware.md',ROOT/'docs/spin-complete-hardware.md',ROOT/'output/manufacturing/feeder-hardware-bom.json',Path(__file__)}
hashes={str(p.relative_to(ROOT)):sha(p)for p in sorted(files)}
substitutions={'remove_in_cable_adoption':[i['instance_id']for i in items if i['scope']=='feeder-base38'and i['site_id'].startswith('beam-host/')and i['role']in['bolt','washer']],
 'retain_in_cable_adoption':[i['instance_id']for i in items if i['scope']=='feeder-base38'and i['site_id'].startswith('beam-host/')and i['role']=='nut'],
 'reason':'Cable system subtracts entire sh_bolts (four M4x20 and four OD9/.8 washers), retains sh_nuts, then adds one set of input M4x60/washer hardware. Do not subtract or add the four retained nuts again.'}
result={'schema_version':1,'status':'CURRENT_BASE_SOURCE_INSTALLATION_INVENTORY',
 'created_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':hashes,'source_stable':all(sha(ROOT/k)==v for k,v in hashes.items()),
 'method':'Human-reviewed current module call graph, source-derived loop dimensions, physical-item enumeration. No hardware mesh component counting, no old BOM quantity seeding.',
 'entry_points':{'feeder':['la_fixed_hardware()','la_moving_hardware(t=0)','la_show()->rs_spring(t=0)'],
 'spin':['sch_hardware(all,float=0,preload=0,held=false/true)','sch_spring(float=0,preload=0)']},
 'physical_inventory_modes':{'base_feeder_count':sum(base.values()),'spin_work_count':sum(work.values()),'spin_held_count':sum(held.values()),
 'base_plus_spin_work':sum(base.values())+sum(work.values()),'base_plus_spin_held':sum(base.values())+sum(held.values()),'kit_union_unique_items':len(items),
 'warning':'195 is feeder before cable replacement. Work and held totals are alternate installed states, not additive. Kit union contains the two removable held-only items once.'},
 'specifications':specs,'instances':items,'summary':{'feeder_base38':base,'spin_work':work,'spin_held':held},
 'cable_adoption_hand_off':substitutions,'legacy_comparison':comparison,'legacy_unmatched_ids':sorted(oldids),
 'legacy_source_hash_comparison':{k:sha(ROOT/k)==h for k,h in old['source_sha256'].items()},
 'exclusions':['Old feeder_cap_hardware omitted by cg_old_hardware(false); replacement yg_hardware counted once.',
 'Do not add rp_hardware, revision_followers, feeder_support_moving or other standalone visual assembly hardware a second time.',
 'Spin full sch_hardware supersedes partial hardware_reference/pull_hardware/added_nuts visual sets; never union their BOMs.',
 'Fastener holes, pocket hexagons, insertion sweeps, tool envelopes, nut feeds and fault-control copies are not purchased parts.',
 'Printed return spacers, integral spin guide pins, printed pull cap/fork/seat and TPU pad are in the printed inventory, not metal counts.',
 'No spares, existing blower/PC/hose/Y fitting or supplier packaging multipliers included.'],
 'other_materials_not_in_piece_total':[{'name':'inlet soft liners','quantity':2,'status':'3mm nominal reference; material/hardness/actual fit unknown'},
 {'name':'strain-relief textile strap','quantity':None,'status':'20mm nominal width, length/buckle unresolved'},
 {'name':'SCS2700 LM and Scotch70 sealing materials','quantity':None,'status':'existing process references, amounts unknown; not load-retention fasteners'}],
 'limitations':['No new procurement, external lookup, geometry export, slicing or physical verification.',
 'Named standards/catalog numbers are previously documented candidates, not evidence of purchase/stock/tolerance acceptance.',
 'Some early CAD washer references are solid disks; documented nominal bores are retained as dimensional selections, not falsely claimed as rendered through-holes.',
 'Inlet M2.5 source comment says SKU not frozen and source head is D5/H3; current docs select a smaller Bossard D4.5/H2.5 max candidate. Both source envelope and selection are retained separately.'],
 'manufacturing_release':False,'physical_acceptance':False,'purchased':False,'cad_modified':False}
(OUT/'inventory.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
(OUT/'source-modules.json').write_text(json.dumps({'source_sha256':hashes,'parameters':{'feeder':F.used,'spin':S.used},'modules':MODULES},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'counts':result['physical_inventory_modes'],'line_counts':[len(base),len(work),len(held)],'legacy_comparison_all_equal':all(x['equal']for x in comparison),'unmatched_legacy':sorted(oldids),'source_stable':result['source_stable']},ensure_ascii=False,indent=2))

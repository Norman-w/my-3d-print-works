"""Export the SCAD mold contract, validate solids and sampled extraction paths."""
from pathlib import Path
import json,subprocess,shutil,importlib.util,hashlib,re
import numpy as np
HERE=Path(__file__).resolve().parent; CAD=HERE.parent
OUT=CAD/'exports/guard-casting-mold-v2'; OUT.mkdir(parents=True,exist_ok=True)
WEB=CAD/'preview/guard-mold-v2'; (WEB/'models').mkdir(parents=True,exist_ok=True)
spec=importlib.util.spec_from_file_location('mesh_io',CAD/'perpendicular-u-joint-guard-v1.17-load-path/build.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
text=(HERE/'mold.scad').read_text()
def param(name): return float(re.search(r'\b'+name+r'=([-\d.]+);',text)[1])
BX=param('BX');BY=param('BY');Z0=param('Z0');Z1=param('Z1');DROP=param('CORE_DROP')
NAMES={'left':'① 左外模 · −X','right':'② 右外模 · +X','lid':'③ 顶盖与圆孔芯 · +Z','upper':'④ 上梁芯 · 快插销定位','lower':'⑤ 组合芯 · 宽肩止挡 / 防反插','back':'⑥ 后端芯 · 宽肩止挡 / 防反插','pin':'⑦ 快插定位销 · 先拔出','product':'PU成品 · v1.19阴刻版'}
COLORS={'left':'#48a8dd','right':'#6383ed','lid':'#a877df','upper':'#eeb750','lower':'#4dbda6','back':'#f08eae','pin':'#c9e65b','product':'#ec7956'}
def write_ascii(s,path):
    mesh=s.to_mesh64();v=mesh.vert_properties[:,:3];f=mesh.tri_verts
    with path.open('w') as out:
        out.write('solid mold_mm\n')
        for face in f:
            pts=v[face];n=np.cross(pts[1]-pts[0],pts[2]-pts[0]);n/=max(np.linalg.norm(n),1e-30)
            out.write('facet normal '+' '.join(format(x,'.17g') for x in n)+'\nouter loop\n')
            for p in pts:out.write('vertex '+' '.join(format(x,'.17g') for x in p)+'\n')
            out.write('endloop\nendfacet\n')
        out.write('endsolid mold_mm\n')
def main():
    solids={};records=[]
    for key in NAMES:
        path=OUT/f'{key}.stl'
        subprocess.run([shutil.which('openscad'),'--backend=Manifold','--export-format=binstl','-D',f'FEATURE="{key}"','-o',str(path),str(HERE/'mold.scad')],check=True,stdout=subprocess.DEVNULL)
        s=b.load(path)
        if key not in ('product','upper','pin'):
            # Repeat the same cavity subtraction in double precision: OpenSCAD's
            # single-precision mesh export can retain coplanar sliver wedges.
            source=b.load(CAD/'exports/perpendicular-u-joint-v1.19-engraved-logo/guard-v1.19.stl')
            s=(s-source).set_tolerance(.00001).simplify(.00001)
        pieces=[p for p in s.decompose() if abs(p.volume())>1e-6]
        assert len(pieces)==1,(key,len(pieces))
        s=pieces[0]
        if key=='upper':s=b.export_precision(s)
        solids[key]=s
        write_ascii(s,path)
        shutil.copy2(path,WEB/'models'/path.name)
        records.append({'id':key,'volume_mm3':s.volume(),'bounds_mm':s.bounding_box(),'components':len(s.decompose()),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    overlaps=[]
    keys=list(solids)
    for i,a in enumerate(keys):
        for c in keys[i+1:]:
            volume=abs((solids[a]^solids[c]).volume())
            if volume>.02:overlaps.append({'a':a,'b':c,'mm3':volume})
    # Validate actual path order with the casting kept rigid; elastomer flex is NOT used to hide interference.
    pos={k:np.zeros(3) for k in keys};paths=[]
    sequence=[('pin',[0,0,30]),('pin',[40,0,0]),('lid',[0,0,90]),('lower',[0,160,0]),('back',[0,-110,0]),('left',[-90,0,0]),('right',[190,0,0]),('upper',[0,0,-DROP]),('upper',[120,0,0])]
    for moving,delta in sequence:
        delta=np.array(delta,dtype=float);length=np.linalg.norm(delta)
        distances=sorted(set([0,*np.arange(.05,min(2,length)+.001,.05),*np.arange(2.5,length,.5),length]))
        peak=0;pair=None;at=0
        for dist in distances:
            shifted=solids[moving].translate(pos[moving]+delta*dist/length)
            for other in keys:
                if other==moving:continue
                # AABB test avoids unnecessary mesh Booleans after disengagement.
                aa=np.array(shifted.bounding_box());bb=np.array(solids[other].bounding_box())+np.tile(pos[other],2)
                if np.any(aa[:3]>=bb[3:]-1e-7) or np.any(bb[:3]>=aa[3:]-1e-7):continue
                v=abs((shifted^solids[other].translate(pos[other])).volume())
                if v>peak:peak,pair,at=v,other,dist
        paths.append({'part':moving,'delta_mm':delta.tolist(),'max_overlap_mm3':peak,'with':pair,'at_distance_mm':at,'samples':len(distances)})
        print('PATH',paths[-1],flush=True);pos[moving]+=delta
    report={'source':'mold.scad','source_sha256':hashlib.sha256((HERE/'mold.scad').read_bytes()).hexdigest(),'original_product_sha256':hashlib.sha256((CAD/'exports/perpendicular-u-joint-v1.19-engraved-logo/guard-v1.19.stl').read_bytes()).hexdigest(),'product_sha256':records[-1]['sha256'],'units':'mm','nominal_clearance_mm':0,'material_shrinkage_compensation':'not_established','stock_size_mm':[BX,BY,Z1-Z0],'parts':records,'closed_overlaps':overlaps,'sampled_paths':paths,'sample_step_near_start_mm':.05,'sample_step_after_2mm':.5,'continuous_sweep_proven':False,'physical_release_and_sealing':'not_tested','elastic_strip_required':{'parts':['left','right'],'feature':'lower-arm convex end chamfers','maximum_nominal_radial_undercut_mm':.6,'material':'flexible cast PU only; not suitable for rigid resin without redesign'}}
    (HERE/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    shutil.copy2(HERE/'validation.json',WEB/'validation.json')
    create_manifest(records)
    assert not overlaps,overlaps
    rigid_clear=[x for x in paths if x['part'] not in ('left','right')]
    assert max(x['max_overlap_mm3'] for x in rigid_clear)<.02,'Core extraction collision; repair mold before delivery'
    # Existing lower-arm convex end bevels need up to 0.6mm elastic stripping.
    # This is deliberately NOT labelled a collision-free rigid demold.
    assert max(x['max_overlap_mm3'] for x in paths if x['part'] in ('left','right'))<25
def band_paths():
    w=param('SHOULDER_THICK');x=param('BAND_X');z=param('BAND_Z')
    by=BY/2;bx=BX/2;sz=param('SPLIT_Z');back_min=-4
    result=[]
    for xx in [-x,x]:
        result.append({'label':'纵向压盖 / 端肩皮筋','points':[[xx,-by-.5,Z0+.5],[xx,by+w-.5,Z0+.5],[xx,by+w-.5,sz+.5],[xx,by+.5,sz+.5],[xx,by+.5,Z1-.5],[xx,-by-.5,Z1-.5],[xx,-by-.5,sz+.5],[xx,-by-w+.5,sz+.5],[xx,-by-w+.5,back_min-.5],[xx,-by-.5,back_min-.5]]})
    ex=param('SHOULDER_HALF_X')-.5
    result.append({'label':'横向合紧外模皮筋','points':[[-bx+.5,-by-.5,z],[-ex,-by-w+.5,z],[ex,-by-w+.5,z],[bx-.5,-by-.5,z],[bx-.5,by+.5,z],[ex,by+w-.5,z],[-ex,by+w-.5,z],[-bx+.5,by+.5,z]]})
    return result
def create_manifest(records):
    ident={'position':[0,0,0],'rotation':[0,0,0]}
    frames=[{'id':'world','label':'夹具合模系统 · X上梁 / Y下脚 / Z向上','parentFrameId':None,'kind':'fixed','localTransform':ident}]
    # Upper insert needs two chained frames to lower before its sideways draw.
    config=[('pin-lift',[0,0,1],30,'world'),('pin',[1,0,0],40,'pin-lift'),('lid',[0,0,1],90,'world'),('left',[-1,0,0],90,'world'),('right',[1,0,0],190,'world'),('lower',[0,1,0],160,'world'),('back',[0,-1,0],110,'world'),('upper-drop',[0,0,-1],DROP,'world'),('upper',[1,0,0],120,'upper-drop')]
    for key,axis,travel,parent in config:frames.append({'id':key,'label':NAMES.get(key,'快插销上拔' if key=='pin-lift' else '上梁芯下降避让'),'parentFrameId':parent,'kind':'prismatic','axis':axis,'range':[0,travel],'defaultValue':0,'localTransform':ident})
    parts=[]
    for r in records:
        k=r['id'];parts.append({'id':k,'name':NAMES[k],'source':{'kind':'scad','file':'../../guard-casting-mold-v1/mold.scad','selector':f'FEATURE="{k}"'},'file':f'models/{k}.stl','geometrySpace':'local','role':'diagnostic' if k=='product' else 'printed','color':COLORS[k],'opacity':1,'instances':[{'id':k+'-instance','name':NAMES[k],'parentFrameId':'world' if k=='product' else k,'localTransform':ident,'explosion':[0,0,0]}]})
    values={k:0 for k,_,_,_ in config};stages=[]
    def add(k,label):stages.append({'id':k,'label':label,'values':dict(values)})
    add('closed','▣ 定位到位 / 绑带合模')
    values['pin-lift']=30;add('pin-lifted','① ↑ 拔快插销')
    values['pin']=40;add('pin-out','② → 放开快插销')
    values['lid']=90;add('lid-off','③ ↑ 提起定位顶盖')
    values['lower']=160;add('lower-out','④ ↗ 抽出绿色组合芯')
    values['back']=110;add('back-out','⑤ ↙ 抽出粉色后端芯')
    values.update(left=90,right=190);add('shells-off','⑥ ↔ 分开定位外模')
    values['upper-drop']=DROP;add('upper-lowered','⑦ ↓ 上梁芯下降 1 mm')
    values['upper']=120;add('released','⑧ → 抽出上梁芯 / 释放')
    manifest={'schemaVersion':1,'title':'围挡卡 · 定位合模 v2','ui':{'persistPanelState':True,'showSearch':False,'showGroups':False},'assembly':{'coordinateSystem':{'units':'mm','handedness':'right','up':'z'},'rootFrameId':'world','frames':frames},'parts':parts,'stages':stages,'playback':{'sequence':[s['id'] for s in stages],'secondsPerTransition':2.5,'loop':False},'views':[{'id':'iso','label':'◈ 等轴','direction':[1,-1, .8]},{'id':'product','label':'⬡ 成品','direction':[1,-1,.8],'focusInstanceIds':['product-instance']}],'extensions':{'mechanical_status':'located_nominal_draft_design','location':{'integral_guides':6,'separate_pull_pins':1,'radial_clearance_mm':param('RADIAL_CLEARANCE'),'shoulder_thickness_mm':param('SHOULDER_THICK'),'band_width_mm':param('BAND_WIDTH')},'clamping_axes':['X','Y','Z'],'shrinkage':'material_not_selected','validation':'./validation.json','bands':band_paths(),'inspections':[{'id':'back','label':'◉ 粉芯定位近看','values':dict(stages[0]['values'],back=6),'focusInstanceIds':['back-instance'],'direction':[.8,1,.6],'visibleInstances':['back-instance','left-instance','right-instance'],'note':'粉芯暂向外退6mm以显示销孔；浇注时宽肩必须贴合端面。'}]}}
    (WEB/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()

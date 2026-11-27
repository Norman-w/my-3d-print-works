"""Seven named, rigidly posed mold parts; X1C/PETG, offline preparation only."""
from pathlib import Path
import sys,json,hashlib,tempfile,subprocess,zipfile,shutil,re,ast,itertools
import xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent;CAD=HERE.parent;sys.path.insert(0,str(CAD))
from build_print_platter import load_binary_stl,rotation_matrix_xyz,transform_triangles,transform_bounds
SRC=CAD/'exports/guard-casting-mold-v2'
OUT=CAD/'print-packages/guard-mold-v2-X1C-PETG';OUT.mkdir(parents=True,exist_ok=True)
BAMBU='/Applications/BambuStudio.app/Contents/MacOS/BambuStudio'
TEMPLATE=CAD/'print-packages/barrier-clip-v1.15-6x-black-PETG/barrier-clip-v1.15-6x-upright-black-PETG.3mf'
C='http://schemas.microsoft.com/3dmanufacturing/core/2015/02';P='http://schemas.microsoft.com/3dmanufacturing/production/2015/06'
# Lower-left placement refers to the rotated mesh bbox, not the original axes.
PLAN=[('left',(0,-90,0),(12,40),'01-left-shell-cavity-up'),('right',(0,90,0),(87.7,40),'02-right-shell-cavity-up'),('lid',(180,0,0),(163.4,40),'03-lid-pins-up'),('lower',(-90,0,0),(12,160),'04-green-core-shoulder-down'),('back',(90,0,0),(103,160),'05-pink-core-shoulder-down'),('upper',(0,0,0),(103,209),'06-yellow-core-flat'),('pin',(180,0,0),(216,170),'07-pull-pin-head-down')]
# Row 1 is 63.7 + 12 + 63.7 + 12 + 84 = 235.4mm. Keep >=8.6mm bed edge.
# User's seven parts only; the reference casting is intentionally excluded.
def write_ascii(path,triangles):
 with path.open('w') as f:
  f.write('solid mold_print_mm\n')
  for t in triangles:
   f.write('facet normal '+' '.join(format(v,'.17g') for v in t[:3])+'\nouter loop\n')
   for j in (3,6,9):f.write('vertex '+' '.join(format(v,'.17g') for v in t[j:j+3])+'\n')
   f.write('endloop\nendfacet\n')
  f.write('endsolid mold_print_mm\n')
def run(args,log):
 r=subprocess.run(args,capture_output=True,text=True);log.write_text(r.stdout+'\n'+r.stderr)
 if r.returncode:raise RuntimeError(f'{log}: exit {r.returncode}\n'+r.stdout[-2000:]+r.stderr[-1000:])
def protected_regions(key):
 source=(HERE/'mold.scad').read_text()
 def n(k):return float(re.search(r'\b'+k+r'=([-\d.]+);',source)[1])
 def points(k):return ast.literal_eval(re.search(r'\b'+k+r'=(\[.*?\]);',source)[1])
 r=n('GUIDE_D')/2+n('RADIAL_CLEARANCE')+1
 by=n('BY')/2;sz=n('SPLIT_Z');depth=n('GUIDE_DEPTH')+n('HOLE_EXTRA_DEPTH')
 regions=[]
 def add(label,lo,hi):regions.append({'label':label,'source_min_mm':lo,'source_max_mm':hi})
 if key in ('left','right'):
  sign=-1 if key=='left' else 1
  for x,z in points('BACK_GUIDES'):
   if x*sign>0:add('rear blind locator socket',[x-r,-by-1,z-r],[x+r,-by+depth+1,z+r])
  for x,z in points('FRONT_GUIDES'):
   if x*sign>0:add('front blind locator socket',[x-r,by-depth-1,z-r],[x+r,by+1,z+r])
  for x,y in points('LID_GUIDES'):
   if x*sign>0:add('lid blind locator socket',[x-r,y-r,sz-depth-1],[x+r,y+r,sz+1])
  if key=='right':add('pull-pin alignment bore',[n('PULL_X')-r,n('PULL_Y')-r,n('PULL_TIP_Z')-1.6],[n('PULL_X')+r,n('PULL_Y')+r,sz+1])
 if key=='lid':add('lettering and upright core pins',[-43,-52,22.5],[43,52,31.5])
 if key in ('lower','back'):
  for x,z in points('FRONT_GUIDES' if key=='lower' else 'BACK_GUIDES'):
   if key=='lower':add('upright integral guide pin',[x-r,by-depth-1,z-r],[x+r,by+.3,z+r])
   else:add('upright integral guide pin',[x-r,-by-.3,z-r],[x+r,-by+depth+1,z+r])
 return regions

def add_blocker(root,model,files,item,region,record,block_id):
 # Official Bambu ModelVolumeType SUPPORT_BLOCKER, not printable geometry.
 obj=root.find(f"{{{C}}}resources/{{{C}}}object[@id='{item.get('objectid')}']")
 components=obj.find(f'{{{C}}}components');path=components[0].get('{'+P+'}path').lstrip('/')
 resource=ET.fromstring(files[path]);resources=resource.find(f'{{{C}}}resources')
 meshobj=ET.SubElement(resources,'{'+C+'}object',{'id':str(block_id),'type':'model'})
 mesh=ET.SubElement(meshobj,'{'+C+'}mesh');verts=ET.SubElement(mesh,'{'+C+'}vertices');tris=ET.SubElement(mesh,'{'+C+'}triangles')
 matrix=rotation_matrix_xyz(*record['rotation_xyz_deg']);shift=record['normalized_translation_mm'];lo=region['source_min_mm'];hi=region['source_max_mm']
 corners=list(itertools.product(*zip(lo,hi)))
 vv=[[sum(matrix[i][j]*p[j] for j in range(3))+shift[i] for i in range(3)] for p in corners]
 for v in vv:ET.SubElement(verts,'{'+C+'}vertex',dict(zip('xyz',map(str,v))))
 # Vertices use binary corner order (000,001,010,011,100,101,110,111).
 faces=[(0,2,3),(0,3,1),(4,5,7),(4,7,6),(0,1,5),(0,5,4),(2,6,7),(2,7,3),(0,4,6),(0,6,2),(1,3,7),(1,7,5)]
 for f in faces:ET.SubElement(tris,'{'+C+'}triangle',dict(zip(('v1','v2','v3'),map(str,f))))
 ET.SubElement(components,'{'+C+'}component',{'{'+P+'}path':'/'+path,'objectid':str(block_id),'transform':'1 0 0 0 1 0 0 0 1 0 0 0'})
 meta=model.find(f"object[@id='{item.get('objectid')}']");part=ET.SubElement(meta,'part',{'id':str(block_id),'subtype':'support_blocker'})
 ET.SubElement(part,'metadata',{'key':'name','value':'Protect '+region['label']})
 ET.SubElement(part,'metadata',{'key':'matrix','value':'1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1'})
 ET.SubElement(part,'mesh_stat',{'face_count':'12','edges_fixed':'0','degenerate_facets':'0','facets_removed':'0','facets_reversed':'0','backwards_edges':'0'})
 files[path]=ET.tostring(resource,encoding='utf-8',xml_declaration=True)
 region['normalized_min_mm']=[min(v[i] for v in vv) for i in range(3)];region['normalized_max_mm']=[max(v[i] for v in vv) for i in range(3)];region['part_id']=block_id

def main():
 validation=json.loads((HERE/'validation.json').read_text());expected={x['id']:x['sha256'] for x in validation['parts']}
 with zipfile.ZipFile(TEMPLATE) as z:cfg=json.loads(z.read('Metadata/project_settings.config'))
 cfg.update({'print_settings_id':'Guard mold v2 X1C PETG 0.20mm 4 walls 20pct','filament_colour':['#000000'],'layer_height':'0.2','initial_layer_print_height':'0.2','wall_loops':'4','top_shell_layers':'6','bottom_shell_layers':'6','sparse_infill_density':'20%','sparse_infill_pattern':'gyroid','wall_generator':'arachne','enable_support':'1','support_type':'tree(auto)','support_on_build_plate_only':'0','support_threshold_angle':'45','support_top_z_distance':'0.24','support_bottom_z_distance':'0.24','support_object_xy_distance':'0.4','support_remove_small_overhang':'1','brim_type':'outer_only','brim_width':'3','brim_object_gap':'0.15','enable_prime_tower':'0'})
 records=[];posed=[]
 for k,angles,xy,name in PLAN:
  source=SRC/f'{k}.stl';sha=hashlib.sha256(source.read_bytes()).hexdigest();assert sha==expected[k],k
  mesh=load_binary_stl(source);matrix=rotation_matrix_xyz(*angles);lo,hi=transform_bounds(mesh.bounds,matrix)
  size=[hi[i]-lo[i] for i in range(3)];shift=[-v for v in lo]
  path=OUT/f'{name}.stl';write_ascii(path,transform_triangles(mesh.triangles,matrix,tuple(shift)));posed.append(path)
  assert xy[0]>=8 and xy[1]>=8 and xy[0]+size[0]<=248 and xy[1]+size[1]<=248
  records.append({'id':k,'name':name,'source_sha256':sha,'rotation_xyz_deg':angles,'normalized_translation_mm':shift,'size_mm':size,'bed_min_xy_mm':xy,'posed_stl':path.name,'scale':1})
 for i,a in enumerate(records):
  for b in records[i+1:]:
   gap=max(max(a['bed_min_xy_mm'][j]-b['bed_min_xy_mm'][j]-b['size_mm'][j],b['bed_min_xy_mm'][j]-a['bed_min_xy_mm'][j]-a['size_mm'][j]) for j in (0,1))
   assert gap>=11.9,(a['id'],b['id'],gap)
 editable=OUT/'guard-mold-v2-7parts-X1C-PETG.3mf';sliced=OUT/'guard-mold-v2-7parts-X1C-PETG.gcode.3mf'
 with tempfile.TemporaryDirectory(prefix='guard-mold-plate-') as tmp:
  tmp=Path(tmp);seed=tmp/'seed.3mf'
  run([BAMBU,'--datadir',str(tmp/'seed-data'),'--arrange','0','--orient','0','--avoid-extrusion-cali-region','--export-3mf',str(seed),*map(str,posed)],OUT/'seed.log')
  with zipfile.ZipFile(seed) as z:
   root=ET.fromstring(z.read('3D/3dmodel.model'));model=ET.fromstring(z.read('Metadata/model_settings.config'));files={n:z.read(n) for n in z.namelist()}
  ET.register_namespace('',C);ET.register_namespace('p',P)
  items=root.findall(f'{{{C}}}build/{{{C}}}item');assert len(items)==7
  plates=model.findall('plate');assert len(plates)==1,'Seed unexpectedly spans plates'
  for item,r in zip(items,records):
   pose=item.get('transform').split();assert [float(v) for v in pose[:9]]==[1,0,0,0,1,0,0,0,1]
   # Account for any component-local import translation emitted by Bambu.
   obj=root.find(f"{{{C}}}resources/{{{C}}}object[@id='{item.get('objectid')}']")
   comp=obj.find(f'{{{C}}}components/{{{C}}}component');cm=[float(v) for v in comp.get('transform').split()]
   assert cm[:9]==[1,0,0,0,1,0,0,0,1]
   ref=comp.get('{'+P+'}path').lstrip('/')
   with zipfile.ZipFile(seed) as z:body=ET.fromstring(z.read(ref))
   vertices=[[float(v.get(a)) for a in 'xyz'] for v in body.findall('.//{'+C+'}vertex')]
   lo=[min(v[j] for v in vertices)+cm[9+j] for j in range(3)]
   pose[9:]=[str(r['bed_min_xy_mm'][0]-lo[0]),str(r['bed_min_xy_mm'][1]-lo[1]),str(-lo[2])];item.set('transform',' '.join(pose));r['object_id']=item.get('objectid')
  block_id=1000
  for item,r in zip(items,records):
   r['support_blockers']=protected_regions(r['id'])
   for region in r['support_blockers']:
    block_id+=1;add_blocker(root,model,files,item,region,r,block_id)
   if r['id'] in ('pin','upper'):
    cfg_obj=model.find(f"object[@id='{item.get('objectid')}']")
    ET.SubElement(cfg_obj,'metadata',{'key':'enable_support','value':'0'})
  for a in list(model.findall('assemble')):model.remove(a)
  with zipfile.ZipFile(seed) as z,zipfile.ZipFile(editable,'w',zipfile.ZIP_DEFLATED) as out:
   replaced={'3D/3dmodel.model','Metadata/model_settings.config','Metadata/project_settings.config','Metadata/filament_sequence.json','Metadata/slice_info.config'}
   for info in z.infolist():
    if info.filename not in replaced:out.writestr(info,files[info.filename])
   out.writestr('3D/3dmodel.model',ET.tostring(root,encoding='utf-8',xml_declaration=True));out.writestr('Metadata/model_settings.config',ET.tostring(model,encoding='utf-8',xml_declaration=True));out.writestr('Metadata/project_settings.config',json.dumps(cfg));out.writestr('Metadata/filament_sequence.json',json.dumps({'plate_1':{'nozzle_sequence':[0],'optimal_assignment':[0],'sequence':[1]}}))
  run([BAMBU,'--datadir',str(tmp/'slice-data'),'--arrange','0','--orient','0','--slice','0','--mstpp','600','--export-3mf',str(sliced),str(editable)],OUT/'slice.log')
 with zipfile.ZipFile(sliced) as z:
  assert [n for n in z.namelist() if n.endswith('.gcode')]==['Metadata/plate_1.gcode']
  for name in ['Metadata/plate_1.png','Metadata/top_1.png']:
   if name in z.namelist():(OUT/Path(name).name).write_bytes(z.read(name))
 report={'mold_revision':'v2','quantity':7,'plate_count':1,'printer':'X1 Carbon 0.4mm','filament':'Generic PETG black','wall_loops':4,'infill':'20% gyroid','layer_height_mm':.2,'supports':'automatic tree, model bases allowed, 0.24mm top gap','brim_width_mm':3,'objects':records,'editable_3mf':editable.name,'sliced_3mf':sliced.name,'printer_sent':False,'printer_started':False}
 (OUT/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

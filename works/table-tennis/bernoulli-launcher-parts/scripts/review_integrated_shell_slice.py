#!/usr/bin/env python3
"""Offline integrated half-shell slicing; never modifies CAD/shared presets."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
import zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/print-review/integrated-shells'
CONFIG=ROOT/'output/print-review/config'
IDENTITY=ROOT/'output/feeder-integrated-candidate/report.json'
BAMBU='/Applications/BambuStudio.app/Contents/MacOS/BambuStudio'
FIELDS=['machine_start_gcode','machine_end_gcode','time_lapse_gcode','change_filament_gcode','layer_change_gcode']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')

def slice_part(part,orientation,support):
    identity=json.loads(IDENTITY.read_text());item=next(v for v in identity['parts']if v['name']==part)
    stl=ROOT/item['path']
    if sha(stl)!=item['sha256']:raise RuntimeError('Integrated report/input STL mismatch')
    source_before={p:sha(ROOT/p)for p in identity['source_sha256']}
    if source_before != identity['source_sha256']: raise RuntimeError('Current source differs from integrated report')
    folder=OUT/f'{part}-{orientation}-{support}'
    folder.mkdir(parents=True,exist_ok=True)
    shared_before={n:sha(CONFIG/(n+'.json'))for n in ['machine','process','filament']}
    for n in ['machine','filament']:shutil.copy2(CONFIG/(n+'.json'),folder/(n+'.json'))
    proc=json.loads((CONFIG/'process.json').read_text())
    proc.update(enable_support='1'if support=='supported'else'0',
        support_type='tree(auto)',support_on_build_plate_only='1')
    dump(folder/'process.json',proc)
    rotations={'inlet-down':[],'outlet-down':['--rotate-x','180'],
        'seam-down':['--rotate-y','-90'if part=='positive-half'else'90']}[orientation]
    cmd=[BAMBU,'--datadir',str(folder/'app-data'),'--load-settings',
        str(folder/'machine.json')+';'+str(folder/'process.json'),'--load-filaments',str(folder/'filament.json'),
        '--orient','0',*rotations,'--arrange','1','--ensure-on-bed','--slice','0',
        '--export-3mf','shell-slice-review.3mf','--outputdir',str(folder),str(stl)]
    report={'part':part,'orientation':orientation,'supports':support,'command':cmd,
        'input':item,'integrated_report_sha256':sha(IDENTITY),'source_sha256_at_start':source_before,
        'shared_profile_sha256':shared_before,'local_profile_sha256':{n:sha(folder/(n+'.json'))for n in ['machine','process','filament']},
        'assumptions':{'machine':'X1C .4','material':'Generic PETG, brand unconfirmed',
            'plate':'Textured PEI analysis assumption; only PEI confirmed',
            'layer_height':.2,'wall_loops':4,'infill':'25%','support_type':'tree(auto), build plate only'},
        'no_print_sent':True,'physical_acceptance':False}
    dump(folder/'invocation.json',report)
    for name in ['result.json','plate_1.gcode','shell-slice-review.3mf']:(folder/name).unlink(missing_ok=True)
    p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    (folder/'bambu-cli.log').write_text(p.stdout+p.stderr)
    report['return_code']=p.returncode
    if (folder/'result.json').exists():report['native_result']=json.loads((folder/'result.json').read_text())
    report['input_and_cad_stable']=sha(stl)==item['sha256']and all(sha(ROOT/p)==h for p,h in source_before.items())
    report['shared_profiles_untouched']=all(sha(CONFIG/(n+'.json'))==h for n,h in shared_before.items())
    report['artifact_sha256']={n:sha(folder/n)for n in ['plate_1.gcode','shell-slice-review.3mf']if(folder/n).exists()}
    if (folder/'plate_1.gcode').exists():
        g=(folder/'plate_1.gcode').read_text();layer=g.index('; CHANGE_LAYER')
        heats=re.findall(r'^M10[49]\b[^\n;]*?\bS([-+\d.]+)',g[:layer],re.M)
        report['last_temperature_before_first_layer_c']=float(heats[-1])if heats else None
    if (folder/'shell-slice-review.3mf').exists():
        with zipfile.ZipFile(folder/'shell-slice-review.3mf')as z:
            (folder/'plate-preview.png').write_bytes(z.read('Metadata/plate_1.png'))
    dump(folder/'invocation.json',report)
    print(json.dumps({k:report.get(k)for k in ['part','orientation','supports','return_code','input_and_cad_stable','last_temperature_before_first_layer_c']},indent=2))
    if 'native_result'in report:
        for p in report['native_result'].get('sliced_plates',[]):print(json.dumps({k:p.get(k)for k in ['warning_message','total_predication','filaments','objects']},indent=2))
    return report['return_code']

def read_mesh(path):
 b=path.read_bytes();n=struct.unpack_from('<I',b,80)[0]
 if len(b)==84+n*50:return np.frombuffer(b,dtype=np.dtype([('n','<f4',3),('v','<f4',(3,3)),('a','<u2')]),offset=84)['v'].astype(float)
 return np.array(re.findall(rb'vertex\s+([-+eE.0-9]+)\s+([-+eE.0-9]+)\s+([-+eE.0-9]+)',b),float).reshape(-1,3,3)

def mesh_links(t):
 links=collections.defaultdict(lambda:collections.defaultdict(set));edges=collections.Counter()
 for tri in t:
  v=[tuple(np.round(p,7))for p in tri]
  for i in range(3):
   c,a,b=v[i],v[(i+1)%3],v[(i+2)%3];links[c][a].add(b);links[c][b].add(a);edges[tuple(sorted((c,a)))]+=1
 faults=[]
 for p,g in links.items():
  seen=set();fans=0
  for v in g:
   if v in seen:continue
   fans+=1;todo=[v]
   while todo:
    c=todo.pop()
    if c in seen:continue
    seen.add(c);todo.extend(g[c]-seen)
  if fans!=1 or any(len(v)!=2 for v in g.values()):faults.append({'point':list(p),'fans':fans,'non_degree_two':sum(len(v)!=2 for v in g.values())})
 return {'vertex_count':len(links),'vertex_link_faults':faults,'non_two_face_edges':sum(n!=2 for n in edges.values()),'weld_decimals':7}

def paths(path):
 x=y=z=0.;feature='';width=.42;layer=None;lh=.2;relative=True;last_e=0
 for line in path.open():
  if line.startswith('; Z_HEIGHT:'):layer=float(line.split(':')[1])
  elif line.startswith('; LAYER_HEIGHT:'):lh=float(line.split(':')[1])
  elif line.startswith('; FEATURE:'):feature=line.split(':',1)[1].strip()
  elif line.startswith('; LINE_WIDTH:'):width=float(line.split(':')[1])
  code=line.split(';')[0].strip()
  if code=='M83':relative=True
  elif code=='M82':relative=False
  elif code.startswith('G92'):
   m=re.search(r'\bE([-+\d.]+)',code)
   if m:last_e=float(m.group(1))
  m=re.match(r'^(G[0123])\b',code)
  if not m:continue
  v={k:float(n)for k,n in re.findall(r'([XYZEFIJK])([-+\d.]+)',code)}
  nx,ny,nz=v.get('X',x),v.get('Y',y),v.get('Z',z)
  extrude=v.get('E',0)if relative else v.get('E',last_e)-last_e
  if 'E'in v:last_e=v['E']if not relative else last_e+v['E']
  if layer is not None and extrude>0 and (nx!=x or ny!=y):
   is_support=feature.startswith('Support')
   # Finer support sampling bounds a missing point by .05 mm; additionally
   # cap arc angle so its chord sagitta stays below .00125 mm.
   step=.1 if is_support else 1.
   if m[1]in ['G2','G3']:
    cx,cy=x+v.get('I',0),y+v.get('J',0);r=math.hypot(x-cx,y-cy)
    a0=math.atan2(y-cy,x-cx);a1=math.atan2(ny-cy,nx-cx)
    da=(a1-a0)%(2*math.pi)if m[1]=='G3'else-((a0-a1)%(2*math.pi))
    if abs(da)<1e-10:da=2*math.pi if m[1]=='G3'else-2*math.pi
    n=max(2,math.ceil(abs(da)*r/step),math.ceil(abs(da)/.1))
    pts=np.array([[cx+r*math.cos(a0+da*i/n),cy+r*math.sin(a0+da*i/n),z+(nz-z)*i/n]for i in range(n+1)])
   else:
    n=max(1,math.ceil(math.dist((x,y,z),(nx,ny,nz))/step))
    pts=np.linspace([x,y,z],[nx,ny,nz],n+1)
   yield layer,lh,feature,width,pts
  x,y,z=nx,ny,nz

def bounds(q):return [q.min(axis=0).tolist(),q.max(axis=0).tolist()]if len(q)else None

def transform(folder):
 with zipfile.ZipFile(folder/'shell-slice-review.3mf')as z:
  ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'};main=ET.fromstring(z.read('3D/3dmodel.model'));s=ET.fromstring(z.read('Metadata/model_settings.config'))
  meta={x.attrib.get('key'):x.attrib.get('value')for x in s.findall('./object/part/metadata')};o=np.array([float(meta['source_offset_'+a])for a in 'xyz']);c=list(map(float,main.find('./m:resources/m:object/m:components/m:component',ns).attrib['transform'].split()));b=list(map(float,main.find('./m:build/m:item',ns).attrib['transform'].split()));R=np.array(c[:9]).reshape(3,3).T
 assert np.allclose(np.array(b[:9]).reshape(3,3),np.eye(3))
 header=(folder/'plate_1.gcode').read_text();raw=re.search(r'^; extruder_offset = ([^\n]+)',header,re.M).group(1).split(',')[0];e=np.array([*map(float,raw.split('x')),0.])
 return R,-R@o+np.array(c[9:])+np.array(b[9:])-e,{'component':c,'build':b,'source_offset':o.tolist(),'extruder_offset':e.tolist()}

def clipped_triangle_in_box(triangle, lower, upper):
    polygon = [point.copy() for point in triangle]
    for axis in range(3):
        for boundary, direction in [(lower[axis], 1), (upper[axis], -1)]:
            if not polygon:
                return False
            result = []
            for a, b in zip(polygon, polygon[1:] + polygon[:1]):
                da = direction * (a[axis] - boundary)
                db = direction * (b[axis] - boundary)
                if da >= 0:
                    result.append(a)
                if (da >= 0) != (db >= 0):
                    result.append(a + (b-a) * da / (da-db))
            polygon = result
    return bool(polygon)


def removal_corridors(triangles, support_points, sign):
    evidence = []
    for center_z in [-60, 3]:
        for dz in [-2, 0, 2]:
            inner_x = 14 if dz == 0 else 16
            lower = np.array([inner_x if sign > 0 else -32, -38.3, center_z+dz-1.])
            upper = np.array([32 if sign > 0 else -inner_x, -36.3, center_z+dz+1.])
            candidates = triangles[((triangles.max(axis=1) >= lower).all(axis=1)) & ((triangles.min(axis=1) <= upper).all(axis=1))]
            hits = sum(clipped_triangle_in_box(triangle, lower, upper) for triangle in candidates)
            support = ((support_points >= lower).all(axis=1) & (support_points <= upper).all(axis=1))
            evidence.append({'nut_center_Z': center_z, 'offset_Z': dz,
                'tool_envelope_mm': [2, 2], 'box_min': lower.tolist(), 'box_max': upper.tolist(),
                'actual_STL_triangle_intersections': hits, 'support_samples_reached': int(support.sum()),
                'scope': 'Straight open-side 2x2 mm rectangular pick-tip corridor; not a removal-force test.'})
    # Positive control deliberately crosses the solid front ear web.
    lower = np.array([10 if sign > 0 else -22, -46, -64])
    upper = np.array([22 if sign > 0 else -10, -44, -63])
    control = sum(clipped_triangle_in_box(triangle, lower, upper) for triangle in triangles)
    return {'corridors': evidence, 'solid_web_positive_control_triangle_hits': control,
        'all_clear': all(v['actual_STL_triangle_intersections'] == 0 for v in evidence),
        'each_nut_has_reachable_support': all(any(v['nut_center_Z'] == zz and v['support_samples_reached'] for v in evidence) for zz in [-60,3])}


def review(folder,root,sha,dump):
 inv=__import__('json').loads((folder/'invocation.json').read_text());sgn=1 if inv['part']=='positive-half'else-1
 assert inv['orientation']=='inlet-down','Detailed proof currently scoped to inlet-down orientation'
 mesh=root/inv['input']['path'];assert sha(mesh)==inv['input']['sha256'];t=read_mesh(mesh);links=mesh_links(t)
 R,shift,mapping=transform(folder);assert np.allclose(R,np.eye(3),atol=1e-12)
 faces={xx:unary_union([Polygon(v[:,1:])for v in t[(abs(t[:,:,0]-xx)<1e-5).all(axis=1)]if abs(np.cross(v[1,1:]-v[0,1:],v[2,1:]-v[0,1:]))>1e-9])for xx in ([0,-.2]if sgn<0 else[0])}
 hits={str(k):[]for k in faces};support=[];swidth=[];heights=[];plots=collections.defaultdict(list);counts=collections.Counter();bridge_lengths=[]
 # Model-layer examples chosen to cross ports, screw seats, ears and flange.
 plotz=[-93,-86,-77,-60,-46,-28,3,16,37,44]
 for layer,lh,feature,width,p in paths(folder/'plate_1.gcode'):
  counts[feature]+=1;q=(p-shift)@R
  if feature.startswith('Support'):
   assert np.ptp(q[:,2])<1e-7,'Nonplanar support extrusion needs separate review'
   support.append(q);swidth.append(np.full(len(q),width));heights.append(np.full(len(q),lh))
   for xx,face in faces.items():
    if q[:,0].min()>xx+width/2+.002 or q[:,0].max()<xx-width/2-.002:continue
    foot=LineString(q[:,:2]).buffer(width/2+.002,quad_segs=24)
    crossing=foot.intersection(LineString([(xx,-100),(xx,100)]))
    if crossing.is_empty:continue
    gs=list(crossing.geoms)if hasattr(crossing,'geoms')else[crossing]
    for g in gs:
     ylo,yhi=g.bounds[1],g.bounds[3]
     actual=face.intersection(box(ylo,q[0,2]-lh,yhi,q[0,2]))
     if actual.area>1e-8:hits[str(xx)].append({'support_z_top':float(q[0,2]),'layer_height':lh,'YZ_patch_area_mm2':actual.area,'patch_bounds_YZ':list(actual.bounds),'feature':feature})
  if feature=='Bridge':bridge_lengths.append(float(np.linalg.norm(np.diff(q,axis=0),axis=1).sum()))
  for z in plotz:
   if abs(q[0,2]-(z+.2))<1e-5:plots[z].append((feature,q))
 q=np.concatenate(support);width=np.concatenate(swidth);lh=np.concatenate(heights);r=np.hypot(q[:,0],q[:,1]);z=q[:,2];m=width/2+.052
 def stats(sel):return {'sample_count':int(sel.sum()),'bounds_mm':bounds(q[sel])}
 zlo=z-lh;zhi=z
 # Cylinder/taper bounds deliberately over-cover the actual polygonal void.
 # Inward inner radius uses cos(pi/72) for the faceted wall; outer radius uses
 # circumscribed radius. Choose min/max over the entire deposited layer.
 zs=np.stack([zlo,zhi,np.clip(-80,zlo,zhi),np.clip(24,zlo,zhi)],axis=1)
 inn=np.interp(zs,[-98,-80,24,42],[24.7,23.5,23.5,24.7]).min(axis=1)*math.cos(math.pi/72)
 out=np.interp(zs,[-98,-80,24,42],[22.7,32,32,22.7]).max(axis=1)
 cavity=(zhi>=-98)&(zlo<=42)&(sgn*q[:,0]>=-m)&(r>=inn-m)&(r<=out+m)
 cavities={name:stats(cavity&(zhi>=lo)&(zlo<=hi))for name,lo,hi in [('inlet_transition',-98,-80),('straight_bypass',-80,24),('outlet_transition',24,42)]}
 # Conservative known-feature cylinders and bounding boxes; hits flag support
 # requiring access review, not exact support/model intersection.
 apertures=[]
 for yy in [-40,40]:
  for zz in [-72,-46,-10,16]:
   sel=(abs(q[:,0])<=7+m)&(sgn*q[:,0]>=-m)&(np.hypot(q[:,1]-yy,z-.1-zz)<=3.58+m+.1)
   apertures.append({'kind':'M3_split_bolt_head_or_nut','center_YZ':[yy,zz],'access':'Open X end; through bore leads to split plane before assembly',**stats(sel)})
 for zz in [-45,16]:
  sel=(sgn*q[:,0]>=31.5-m)&(sgn*q[:,0]<=35.5+m)&(np.hypot(q[:,1]+14,z-.1-zz)<=3.58+m+.1)
  apertures.append({'kind':'M3_side_blind_nut','center_XYZ':[sgn*35.5,-14,zz],'access':'Outer X face; <=4 mm depth, before mechanism covers',**stats(sel)})
 for yy,zz in [(40,-59),(-40,3)]:
  sel=(sgn*q[:,0]>=-m)&(sgn*q[:,0]<=3.2+m)&(np.hypot(q[:,1]-yy,z-.1-zz)<=2.1+m+.1)
  apertures.append({'kind':'locator_blind','center_YZ':[yy,zz],'access':'Split face, <=3.2 mm deep before closure',**stats(sel)})
 for zz in [-60,3]:
  sel=(abs(q[:,0]-sgn*16)<=6+m)&(q[:,1]>=-39-m)&(q[:,1]<=-35.6+m)&(abs(z-.1-zz)<=4.25+m+.1)
  apertures.append({'kind':'M4_ear_nut_entry','center_XZ':[sgn*16,zz],'access':'Outward X side feed, Y[-39,-35.6], Z center +/-4.25; remove before nut and beam',**stats(sel)})
  bore=(q[:,1]>=-48-m)&(q[:,1]<=-39+m)&(np.hypot(q[:,0]-sgn*16,z-.1-zz)<=2.25+m+.1)
  apertures.append({'kind':'M4_ear_front_bore','center_XZ':[sgn*16,zz],'access':'Y=-48 bolt face to side-fed nut pocket',**stats(bore)})
 boreid=np.interp(z,[-98,-80,24,42],[22.7,21.25,21.25,22.7]);ball=(zhi>=-98)&(zlo<=42)&(sgn*q[:,0]>=-m)&(r<=boreid+m)
 ports=[]
 for zz in [-89,33]:
  for angle in ([45,-45]if sgn>0 else[135,225]):
   a=math.radians(angle);cross=-q[:,0]*math.sin(a)+q[:,1]*math.cos(a);along=q[:,0]*math.cos(a)+q[:,1]*math.sin(a)
   sel=(abs(cross)<4+m)&(abs(z-.1-zz)<5.5+m+.1)&(along>=20-m)&(along<=25+m)
   ports.append({'center_Z':zz,'angle_deg':angle,**stats(sel)})
 os.environ.setdefault('MPLCONFIGDIR',str(folder/'matplotlib-config'))
 os.environ.setdefault('XDG_CACHE_HOME',str(folder/'cache'))
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.collections import LineCollection
 fig,axs=plt.subplots(2,5,figsize=(19,9),layout='constrained')
 for ax,zz in zip(axs.flat,plotz):
  groups=collections.defaultdict(list)
  for feature,p in plots[zz]:groups['Support'if feature.startswith('Support')else'Object'].append(np.stack([p[:-1,:2],p[1:,:2]],axis=1))
  for key,color in [('Object','#1d668b'),('Support','#d57918')]:
   if groups[key]:ax.add_collection(LineCollection(np.concatenate(groups[key]),colors=color,linewidths=.5))
  ax.set_xlim(-18 if sgn>0 else-58,58 if sgn>0 else 18);ax.set_ylim(-70,74);ax.set_aspect('equal');ax.set_title(f'Assembly Z top {zz+.2:g} mm');ax.set_xlabel('X / mm');ax.set_ylabel('Y / mm')
 fig.suptitle(f'{inv["part"]}: actual extrusion paths — model blue, supports orange');fig.savefig(folder/'layer-paths.png',dpi=150);plt.close(fig)
 # Critical exact plane footprints, using actual deposited Z slab, not a sphere.
 report={'part':inv['part'],'orientation':inv['orientation'],'input_stl_sha256':sha(mesh),'gcode_sha256':sha(folder/'plate_1.gcode'),'project_3mf_sha256':sha(folder/'shell-slice-review.3mf'),'mesh_topology':links,'mapping':{'R':R.tolist(),'shift':shift.tolist(),**mapping},'feature_path_counts':dict(counts),'support_sample_count':len(q),'support_bounds_mm':bounds(q),'max_sample_spacing_mm':.1,'sample_radius_margin_mm':.052,'curve_footprint_extra_mm':.002,'cavities':cavities,'ports':ports,'open_ball_channel':stats(ball),'split_plane_support_footprint_intersections':hits,'apertures':apertures,'max_single_bridge_command_path_mm':max(bridge_lengths),'limits':['Input STL checks do not prove all possible mesh self-intersections.','Support samples expanded by half declared width + .052; Z slab uses emitted layer height. Arc/chord check additionally caps angular step at .1 rad.','Face intersection uses actual coplanar STL triangles and buffered support footprints; possible microscopic extrusion swelling, printer error and PETG adhesion are not modelled.','A bridge command length is not an unsupported span, and no measured bridge strength is inferred.','Open feature access is reviewed before installation of all pins, nuts, guides and beam; no printed removal force or debris test completed.'],'sent_to_printer':False}
 report['M4_removal_tool_corridors'] = removal_corridors(t, q, sgn)
 machine = __import__('json').loads((folder/'machine.json').read_text())
 template_root = Path('/Applications/BambuStudio.app/Contents/Resources/profiles/BBL/machine')
 report['official_machine_template_fields'] = {field: machine[field] == __import__('json').loads((template_root/f'Bambu Lab X1 Carbon 0.4 nozzle template {field}.json').read_text())[field] for field in FIELDS}
 current_identity = __import__('json').loads(IDENTITY.read_text())
 report['current_input_and_source_identity'] = {
     'STL_matches_current_integrated_report': sha(mesh) == next(v['sha256'] for v in current_identity['parts'] if v['name'] == inv['part']),
     'all_sources_match_slice_start': all(sha(root/p) == h for p,h in inv['source_sha256_at_start'].items()),
     'slice_start_sources_match_integrated_report': inv['source_sha256_at_start'] == current_identity['source_sha256'],
     'shared_presets_unchanged': all(sha(CONFIG/(n+'.json')) == h for n,h in inv['shared_profile_sha256'].items())}
 report['review_script_sha256'] = sha(Path(__file__))
 report['checks'] = {
     'input_and_source_identity_current': all(report['current_input_and_source_identity'].values()),
     'mesh_edges_and_vertex_links_closed': not links['vertex_link_faults'] and links['non_two_face_edges'] == 0,
     'no_support_in_closed_air_paths': not any(v['sample_count'] for v in cavities.values()),
     'no_support_in_transition_windows': not any(v['sample_count'] for v in ports),
     'no_support_in_ball_channel': report['open_ball_channel']['sample_count'] == 0,
     'no_support_footprint_on_split_faces_or_groove_floor': not any(hits.values()),
     'M3_locator_and_M4_front_bores_support_free': not any(v['sample_count'] for v in apertures if v['kind'] != 'M4_ear_nut_entry'),
     'M4_side_access_tool_corridors_clear_and_reach_support': report['M4_removal_tool_corridors']['all_clear'] and report['M4_removal_tool_corridors']['each_nut_has_reachable_support'],
     'tool_collision_positive_control_detected': report['M4_removal_tool_corridors']['solid_web_positive_control_triangle_hits'] > 0,
     'five_official_machine_fields_match': all(report['official_machine_template_fields'].values()),
     'native_slice_success_no_warning': inv['return_code'] == 0 and inv['native_result']['return_code'] == 0 and not inv['native_result']['sliced_plates'][0]['warning_message'],
     'initial_heater_setpoint_255': inv['last_temperature_before_first_layer_c'] == 255}
 report['status'] = 'BOUNDED_OFFLINE_SUPPORT_ACCESS_PASS_PHYSICAL_OPEN' if all(report['checks'].values()) else 'REVIEW_FLAGGED'
 dump(folder/'toolpath-review.json',report)
 print(__import__('json').dumps({k:report[k] for k in ['part','status','checks','M4_removal_tool_corridors']},indent=2))
 return 0 if all(report['checks'].values()) else 1

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('part', choices=['positive-half', 'negative-half'])
    parser.add_argument('--orientation', choices=['inlet-down', 'outlet-down', 'seam-down'], default='inlet-down')
    parser.add_argument('--support', choices=['supported', 'unsupported'], default='supported')
    parser.add_argument('--review', action='store_true', help='Review existing slice with FreeCAD Python numpy/shapely runtime; do not re-slice')
    args = parser.parse_args()
    if args.review:
        global np, Polygon, LineString, box, unary_union, shapely, collections, os, struct
        import collections, os, struct
        import numpy as np
        import shapely
        from shapely.geometry import Polygon, LineString, box
        from shapely.ops import unary_union
        return review(OUT/f'{args.part}-{args.orientation}-{args.support}', ROOT, sha, dump)
    return slice_part(args.part, args.orientation, args.support)

if __name__ == '__main__':
    raise SystemExit(main())

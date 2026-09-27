"""Read-only classification of first-layer support outside pocket-only contract.
Does not reslice, alter mechanical geometry, or overwrite the original strict review.
"""
from pathlib import Path
import json, zipfile, xml.etree.ElementTree as ET, math, os
import review_support_paths as s
B=Path(__file__).resolve().parent
F=B/'slices/20260927T092019389929Z'
O=B/'first-layer-island-review';O.mkdir(exist_ok=True)
os.environ.setdefault('MPLCONFIGDIR',str(O/'mpl'))
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

def components(g):
 if g.is_empty:return []
 if g.geom_type=='Polygon':return [g]
 return [a for q in g.geoms for a in components(q)]

def main(part):
 f=F/part;reportfile=f/'support-path-review/report.json';r=json.loads(reportfile.read_text());inv=json.loads((f/'invocation.json').read_text())
 assert all(s.sha(f/n)==h for n,h in r['artifact_sha256'].items())
 assert s.sha(f/'support-input.3mf')==inv['input3mf_sha256']
 assert inv['returncode']==0 and inv['source_stable']
 M=r['mapping'];I=s.np.linalg.inv(s.np.array(M['local_to_command']));E=s.np.eye(4);E[:3,3]=-s.np.array(M['extruder_offset_from_gcode'])
 with zipfile.ZipFile(f/'slice-review.3mf')as z:
  cfg=ET.fromstring(z.read('Metadata/model_settings.config'));normal=next(n for n in cfg.findall('./object/part')if n.attrib['subtype']=='normal_part');main=ET.fromstring(z.read('3D/3dmodel.model'));c=next(c for c in main.findall('./m:resources/m:object/m:components/m:component',s.NS)if c.attrib['objectid']==normal.attrib['id']);file=next(v for k,v in c.attrib.items()if k.endswith('}path')).lstrip('/');v,t=s.getmesh(z,file,c.attrib['objectid']);v=s.p.affine(v,I@E@s.np.array(M['build'])@s.np.array(M['normal_component']));tri=v[t]
  assert s.sha(f/'plate_1.gcode')==__import__('hashlib').sha256(z.read('Metadata/plate_1.gcode')).hexdigest()
 # Projection of every nonzero projected triangle of actual native normal part.
 # This is the complete solid projection, not just the first-layer contour.
 proj=s.unary_union([s.Polygon(a[:,:2])for a in tri if abs(s.np.cross(a[1,:2]-a[0,:2],a[2,:2]-a[0,:2]))>1e-12])
 bad={x['line']for x in r['support_outside_selected_extraction_cavities']};rows=[];others=[];brim=[];first_model=[];badrows=[]
 for e in s.p.extrusion_paths((f/'plate_1.gcode').open()):
  if not(e.feature.startswith('Support')or(e.layer<=.100001 and (s.model(e.feature)or e.feature=='Brim'))):continue
  q=s.p.affine(e.points,I);path=s.LineString(q[:,:2]);fp=path.buffer(e.width/2+s.ERROR,quad_segs=32);row=dict(line=e.line,feature=e.feature,print_top=e.layer,width=e.width,height=e.height,xy=q[:,:2],local_z=sorted([q[0,2],q[0,2]-inv['pocket_contract']['growth']*e.height]),fp=fp)
  if e.line in bad:badrows.append(row)
  elif e.feature.startswith('Support'):others.append(row)
  elif e.feature=='Brim':brim.append(row)
  else:first_model.append(row)
 assert len(badrows)==len(bad) and all(e['print_top']==.1 for e in badrows)
 outside=s.unary_union([q['fp']for q in badrows]);other=s.unary_union([q['fp']for q in others]);bf=s.unary_union([q['fp']for q in brim]);fm=s.unary_union([q['fp']for q in first_model])
 # Revised per-pocket classification excludes only proved exterior-bed islands;
 # the old pocket-only report stays unchanged. Use actual 72-facet circular hole.
 cavities=[]
 for j,c in enumerate(inv['pocket_contract']['centres']):
  opening=s.shape(c,'hex')if inv['pocket_contract']['opening'].startswith('hex')else s.Polygon([(c[0]+3.1*math.cos(2*math.pi*k/72),c[1]+3.1*math.sin(2*math.pi*k/72))for k in range(72)])
  rr=[q for q in others if min(range(2),key=lambda i:q['fp'].distance(s.Point(inv['pocket_contract']['centres'][i])))==j];fp=s.unary_union([q['fp']for q in rr]);entry=min(inv['pocket_contract']['z'])if inv['pocket_contract']['growth']>0 else max(inv['pocket_contract']['z']);lo,hi=sorted([entry,inv['pocket_contract']['contact']]);axial=all(q['local_z'][0]>=lo-1e-5 and q['local_z'][1]<=hi+1e-5 for q in rr)
  cavities.append(dict(pocket=j,opening='source hex AF5.8'if inv['pocket_contract']['opening'].startswith('hex')else'source 72-facet D6.2 polygon',path_count=len(rr),outside_area_mm2=fp.difference(opening).area,min_margin_mm=fp.distance(opening.boundary),all_remaining_support_contained=opening.covers(fp)and axial))
 isolated=outside.distance(other)>0;results=[]
 for c in components(outside):
  matched=[e for e in badrows if c.intersects(e['fp'])]
  results.append(dict(lines=[e['line']for e in matched],local_xy_bounds=list(c.bounds),bead_projection_area_mm2=c.area,print_z_range=[min(e['print_top']-e['height']for e in matched),max(e['print_top']for e in matched)],normal_full_projection_overlap_mm2=c.intersection(proj).area,normal_full_projection_gap_mm=c.distance(proj),other_support_any_height_projection_gap_mm=c.distance(other),first_layer_model_bead_overlap_mm2=c.intersection(fm).area,first_layer_model_bead_gap_mm=c.distance(fm),first_layer_brim_overlap_mm2=c.intersection(bf).area,first_layer_brim_gap_mm=c.distance(bf),classification='EXTERIOR_BED_ISLAND_WITH_BRIM_CONTACT'if c.intersection(proj).is_empty and c.distance(other)>0 else'UNRESOLVED'))
 assert all(x['classification']=='EXTERIOR_BED_ISLAND_WITH_BRIM_CONTACT'for x in results)
 fig,axes=plt.subplots(1,2,figsize=(11,6),layout='constrained')
 for ax,c in zip(axes,inv['pocket_contract']['centres']):
  for pg in components(proj):ax.fill(*pg.exterior.xy,color='#d1dfe4',alpha=.7)
  for q in brim:ax.plot(*q['xy'].T,color='#999',lw=.6)
  for q in others:
   if q['print_top']==.1:ax.plot(*q['xy'].T,color='#ce7324',lw=1)
  for pg in components(outside):ax.fill(*pg.exterior.xy,color='#d43364',alpha=.85)
  ax.set_xlim(c[0]-8,c[0]+8);ax.set_ylim(c[1]-8,c[1]+8);ax.set_aspect('equal');ax.grid(alpha=.15);ax.set_xlabel('Input local X / mm');ax.set_ylabel('Input local Y / mm')
 fig.suptitle(part+' — exterior first-layer support islands\nGray-blue: complete model projection; pink: full bead islands; gray: first-layer brim; orange: other support')
 fig.savefig(O/(part+'.png'),dpi=170);plt.close(fig)
 prior=json.loads((B/'slices/20260927T091647165443Z'/part/'invocation.json').read_text())
 result=dict(part=part,status='EXTERIOR_BED_ISLANDS_CLASSIFIED_POCKET_SUPPORT_SEPARATE',strict_original_pocket_only_pass=r['all_support_localized'],original_report=str(reportfile),original_report_sha256=s.sha(reportfile),native_source=dict(folder=str(f),input3mf_sha256=inv['input3mf_sha256'],native_returncode=inv['returncode'],obj_cached_cnt=inv['native_result']['sliced_plates'][0]['obj_cached_cnt'],input_differs_from_trial2=inv['input3mf_sha256']!=prior['input3mf_sha256'],gcode_identical_to_trial2=inv['artifacts']['plate_1.gcode']==prior['artifacts']['plate_1.gcode'],artifacts=r['artifact_sha256']),islands=results,all_remaining_support_contained=all(x['all_remaining_support_contained']for x in cavities),cavities=cavities,removal_routes=['Remove the model from the PEI bed; the exterior islands have no model anywhere above their complete nominal footprint, and no other support connection. Peel or clear these exterior residues together with the brim before the next print; their nominal brim overlap is recorded, so they are not assumed to be loose.','After model removal, remove only the interior shallow-pocket supports through their original reverse-build opening before hardware assembly.'],limits=['Full declared bead width/height plus 0.00325 mm XY path-discretization budget are used; no relaxed collision threshold.','Nominal geometry classifies bed-only pieces; actual PETG adhesion, removal force, grasping, support scars and shoulder bearing condition remain unverified.','Strict original pocket-only contract failure is preserved and is not relabelled as contained.','The source cap opening is 72-facet; remaining support is rechecked against that polygon rather than a 720-sided approximation.'],script_sha256=s.sha(__file__),manufacturing_release=False,sent_to_printer=False)
 s.dump(O/(part+'.json'),result);return result
results=[main(n)for n in ['cable-input-lever','cable-input-terminal-cap']]
s.dump(O/'report.json',dict(status='ALTERNATE_BED_CLEANING_ROUTE_NOMINALLY_CLASSIFIED',parts=results,manufacturing_release=False,sent_to_printer=False))
print(json.dumps([{k:v for k,v in r.items()if k in ['part','strict_original_pocket_only_pass','all_remaining_support_contained','islands']}for r in results],indent=2))

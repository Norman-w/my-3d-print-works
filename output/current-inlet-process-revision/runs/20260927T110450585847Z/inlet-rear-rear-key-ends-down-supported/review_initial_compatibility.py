#!/usr/bin/env python3
"""Candidate-3-only read-only provenance audit; no slicing/CAD change/release."""
from pathlib import Path
import sys,json,math,hashlib,importlib.util,re,copy
from decimal import Decimal
import numpy as np
from shapely.geometry import LineString,MultiPoint
from shapely.ops import unary_union
F=Path(__file__).resolve().parent
ROOT=next(p for p in F.parents if (p/'cad/inlet-retention-final.scad').exists())
sys.path[:0]=[str(ROOT/'analysis'),str(ROOT/'scripts')]
import cable_input_slice_review as g
sp=importlib.util.spec_from_file_location('sw',ROOT/'output/current-manufacturing/inlet-support-closure/sweep_review.py');sw=importlib.util.module_from_spec(sp);sp.loader.exec_module(sw)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
rel=lambda p:str(Path(p).resolve().relative_to(ROOT))
hit=json.loads((F/'hit-localization.json').read_text());code=F/'plate_1.gcode';raw=code.read_text().splitlines()
objs,settings,embedded_sha,unit=sw.reuse.archive_models(F/'slice-review.3mf')
assert len(objs)==1 and embedded_sha==sha(code) and unit=='millimeter'
obj=next(iter(objs.values()));M=np.array(obj['mapping']['current_cad_to_gcode_command']);assert np.array_equal(M,np.array(hit['cad_to_gcode']))
source_row=next(r for r in hit['rows'] if r['print_top_z']==19.6);face=source_row['stl_faces'][0];tri=g.affine(np.array(face['cad_vertices']),M)
# Locate the very same CAD facet in the archived normal mesh, with numerical error reported.
v=obj['vertices'][obj['faces']];target=np.array(face['cad_vertices']);err=np.max(np.min(np.max(np.abs(v[:,:,None,:]-target[None,None,:,:]),axis=3),axis=2),axis=1);k=int(np.argmin(err));assert k==90 and err[k]<1e-6
R=list(g.extrusion_paths(code.open()));byline={r.line:r for r in R}
P=lambda r:LineString(r.points[:,:2]).buffer((r.width/2+.002)/math.cos(math.pi/128),quad_segs=32)
support=[byline[n] for n in (164898,164899)];S=unary_union([P(r)for r in support]);J=S.intersection(MultiPoint(sw.clip_below(tri,19.6)[:,:2]).convex_hull)
assert abs(J.area-source_row['stl_area_mm2'])<1e-12
arch_tri=g.affine(v[k],M);arch_J=S.intersection(MultiPoint(sw.clip_below(arch_tri,19.6)[:,:2]).convex_hull)
# Exact text provenance for comments and last commanded Z at every reviewed line.
meta={};state={};previous_z=None;last_z=None
for n,text in enumerate(raw,1):
 for prefix in ['; Z_HEIGHT:','; LAYER_HEIGHT:','; LINE_WIDTH:','; FEATURE:']:
  if text.startswith(prefix):
   if prefix=='; Z_HEIGHT:':
    state['previous_layer_Z_HEIGHT']=previous_z;previous_z={'line':n,'text':text,'value':text.split(':',1)[1].strip()}
   state[prefix]={'line':n,'text':text,'value':text.split(':',1)[1].strip()}
 cmd=text.split(';',1)[0].strip()
 if re.match(r'^G[0123](?: |$)',cmd) and (m:=re.search(r'(?:^| )Z([-+.0-9eE]+)',cmd)):
  state['last_Z_command']={'line':n,'text':text,'value':m.group(1)}
 if n in byline:meta[n]=copy.deepcopy(state)
def rec(r):
 m=meta[r.line];top=Decimal(str(float(r.points[:,2].max())));height=Decimal(m['; LAYER_HEIGHT:']['value']);prev=m.get('previous_layer_Z_HEIGHT');decl=Decimal(m['; Z_HEIGHT:']['value']);delta=decl-Decimal(prev['value']) if prev else None
 return {'line':r.line,'text':raw[r.line-1],'feature':r.feature,'width':r.width,'points':r.points.tolist(),'declared_height_text':str(height),'recorded_prism_bottom_decimal':str(top-height),'top_Z_decimal':str(top),'preceding_layer_Z_delta_decimal':str(delta)if delta is not None else None,'height_minus_Z_delta_decimal':str(height-delta)if delta is not None else None,'metadata':m}
models=[r for r in R if r.feature not in sw.SKIP and r.feature not in ['Brim','Skirt']and not r.feature.startswith('Support')]
near=[]
for r in models:
 rad=(r.width/2+.002)/math.cos(math.pi/128);lo=r.points[:,:2].min(0)-rad;hi=r.points[:,:2].max(0)+rad
 if hi[0]<J.bounds[0]-2 or lo[0]>J.bounds[2]+2 or hi[1]<J.bounds[1]-2 or lo[1]>J.bounds[3]+2:continue
 near.append((r,P(r)))
# All actual model records whose full stated-height prism could overlap either witness support slab.
contact_records=[];positive=[];nearest_stages=[]
for r,p in near:
 for s in support:
  sm=rec(s);rm=rec(r)
  dz=min(Decimal(sm['top_Z_decimal']),Decimal(rm['top_Z_decimal']))-max(Decimal(sm['recorded_prism_bottom_decimal']),Decimal(rm['recorded_prism_bottom_decimal']))
  if dz>=0 and not p.intersection(P(s)).is_empty:
   pair={'support_line':s.line,'model':rm,'vertical_overlap_decimal':str(dz),'projected_area_mm2':p.intersection(P(s)).area,'in_tri90_contact_region_area_mm2':p.intersection(J).area}
   contact_records.append(pair)
   if dz>0 and pair['projected_area_mm2']>0:positive.append(pair)
for name,predicate in [('printed_before_witness_support',lambda r:r.line<164898),('same_19_6_layer_model',lambda r:r.layer==19.6),('all_model_whose_actual_bottom_at_or_below_support_top',lambda r:Decimal(rec(r)['recorded_prism_bottom_decimal'])<=Decimal('19.6'))]:
 candidates=[(p.distance(J),r,p)for r,p in near if predicate(r)];dist,r,p=min(candidates,key=lambda x:x[0]);nearest_stages.append({'stage':name,'distance_mm':dist,'model':rec(r),'intersection_area_mm2':p.intersection(J).area})
xyhits=[(r,p.intersection(J).area)for r,p in near if not p.intersection(J).is_empty];first=min(xyhits,key=lambda x:x[0].line)
firstlayer=first[0].layer;layer_hits=[(r,p)for r,p in near if r.layer==firstlayer and not p.intersection(J).is_empty]
covered=unary_union([p for r,p in layer_hits]);layer_report={'first_intersecting_model_record':rec(first[0]),'first_layer':firstlayer,'first_layer_hit_records':[{'record':rec(r),'area_mm2':p.intersection(J).area}for r,p in layer_hits],'contact_region_not_covered_after_first_layer_area_mm2':J.difference(covered).area}
# Preserve the five strict pairs; show exact emitted text causing bottom/top compatibility.
boundaries=[]
for row in hit['rows']:
 pairs=[p for p in row['pairs']if p['model_actual_slab_reached_by_sweep']]
 if not pairs:continue
 details=[]
 for pair in pairs:
  s=rec(byline[pair['support_line']]);m=rec(byline[pair['model_line']]);overlap=Decimal(s['top_Z_decimal'])-Decimal(m['recorded_prism_bottom_decimal']);plane_contact=Decimal(s['top_Z_decimal'])-Decimal(m['metadata']['previous_layer_Z_HEIGHT']['value'])
  details.append({'support':s,'model':m,'stated_height_bottom_overlap_decimal_mm':str(overlap),'previous_commanded_layer_plane_overlap_decimal_mm':str(plane_contact),'original_pair_area_mm2':pair['area_mm2'],'classification':'exact_boundary_in_commanded_layer_planes; stated_height_text_retained'})
 boundaries.append({'support_print_Z':row['print_top_z'],'pairs':details,'original_strict_model_hit_retained':True})
inputs=[F/'slice-review.3mf',code,F/'hit-localization.json',F/'hit-localization.md',F/'whole-support-sweep/report.json',F/'current-review.json',ROOT/'output/current-manufacturing/inlet-support-closure/sweep_review.py',ROOT/'analysis/cable_input_slice_review.py',Path(__file__)]
report={'status':'INITIAL_COMPATIBILITY_ORIGIN_LOCALIZED_NOT_A_MANUFACTURING_RELEASE','scope':'Candidate 3, only original tri90 source-surface hit and five actual-model boundary hits. Historical strict results remain untouched.','source_hashes':{rel(p):sha(p)for p in inputs},'archive_evidence':{'normal_objects':len(objs),'embedded_gcode_equals_external':True,'units':unit,'mapping':obj['mapping'],'archived_triangle_index_matching_tri90':k,'triangle_max_coordinate_error_mm':float(err[k]),'archived_triangle_cad_vertices':v[k].tolist(),'comparison_note':'Saved normal mesh has a measured 4.7547e-7 mm decimal-centering difference from binary source triangle; correspondence is not claimed byte-exact. Original source ROI remains unchanged for comparison.','mesh_repair_stats':obj['repair_stats']},'tri90':{'cad_vertices':face['cad_vertices'],'print_vertices':tri.tolist(),'contact_region_bounds_print_xy':list(J.bounds),'contact_region_area_mm2':J.area,'archived_normal_mesh_contact_area_mm2':arch_J.area,'archived_normal_mesh_contact_bounds_print_xy':list(arch_J.bounds),'support_witnesses':[rec(r)for r in support],'all_model_records_examined':len(models),'local_model_records_retained':len(near),'actual_stated_prism_contact_pairs':contact_records,'actual_positive_volume_pair_count':len(positive),'nearest_model_stages':nearest_stages,'first_future_model_cover':layer_report,'source_surface_height_range_at_initial_hit_mm':[min(x['source_face_print_z_range_over_xy_hit'][0]for x in face['support_witnesses']),max(x['source_face_print_z_range_over_xy_hit'][1]for x in face['support_witnesses'])],'interpretation':'The continuous archived source facet occupies part of the 19.6 support prism, but no emitted actual-model stated-height prism occupies that witness support region at the same height. The footprint first receives actual-model paths in layer19.8. This is source-surface versus FDM staircase approximation, not a measured plastic collision.'},'five_boundary_hits':boundaries,'method':'Same circumscribed width/2+.002 footprint retained; full record-specific stated-height prisms. Decimal arithmetic uses original LAYER_HEIGHT and commanded Z text to distinguish decimal metadata from machine layer planes; no epsilon removes original contact. No physical bead envelope is inferred as exact.','limits':['Actual PETG cross sections, extrusion sag, adhesion and detachment force are not observed.','The .018900 mm nominal same-layer gap is a numerical path gap, not a manufacturing clearance guarantee.','The five original closed-set contacts remain failures under their original stated-height interpretation; commanded layer planes explain origin without declaring them separated.','This finite provenance audit does not decide adoption, validate all support removal, or certify the other55 instances.'],'manufacturing_release':False,'physical_acceptance':False,'sent_to_printer':False}
(F/'initial-compatibility-origin.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'positive_volume_pairs':len(positive),'all_contact_pairs':len(contact_records),'first_model_line':first[0].line,'first_layer':firstlayer,'uncovered_area_after_first_layer':layer_report['contact_region_not_covered_after_first_layer_area_mm2'],'nearest':[(n['stage'],n['model']['line'],n['distance_mm'])for n in nearest_stages],'boundaries':[(b['support_print_Z'],len(b['pairs']))for b in boundaries]}))

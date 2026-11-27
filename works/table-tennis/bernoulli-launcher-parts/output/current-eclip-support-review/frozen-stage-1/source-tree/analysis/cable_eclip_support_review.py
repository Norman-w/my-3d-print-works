#!/usr/bin/env python3
"""Read-only support/underlay review of new E-clip input slices.

Consumes the independent artifact review and actual G-code. Never slices, edits
CAD, or sends a print. Run with FreeCAD Python and --folder native-slice-folder.
"""
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import argparse, hashlib, json, math, os, sys
import numpy as np
from shapely.geometry import Polygon, Point, LineString, box
from shapely.ops import unary_union

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'analysis'))
import cable_input_slice_review as parser
import cable_eclip_slice_artifacts as artifact

SOURCE_SHA='cf2dc90ecea43e0bb5bf3b6fe68f9cf7adb8d47145b4b15577e5dd40f1679d8d'
ERROR=parser.ARC_ERROR+parser.BUFFER_ERROR
TOL=1e-7

def path(p):
 p=Path(p);return p if p.is_absolute() else ROOT/p
def sha(p):return hashlib.sha256(path(p).read_bytes()).hexdigest()
def rel(p):return str(path(p).resolve().relative_to(ROOT))
def dump(p,d):path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2,default=lambda x:x.item() if isinstance(x,np.generic) else str(x))+'\n')
def shapes(g,kind='Polygon'):
 if g.is_empty:return []
 if g.geom_type==kind:return [g]
 return [a for q in getattr(g,'geoms',[]) for a in shapes(q,kind)]
def model(f):return f not in {'Custom','Flush','Brim','Skirt','Undefined','Prime tower','Prime tower infill',''} and not f.startswith('Support')
def fp(rows):return unary_union([r['footprint'] for r in rows])
def hexagon(c,af):return Polygon([(c[0]+af/math.sqrt(3)*math.cos(math.pi/6+k*math.pi/3),c[1]+af/math.sqrt(3)*math.sin(math.pi/6+k*math.pi/3)) for k in range(6)])
def clip_below(t,z):
 result=[]
 for i in range(len(t)):
  a=t[i-1];b=t[i];ia=a[2]<=z;ib=b[2]<=z
  if ia!=ib:result.append(a+(b-a)*(z-a[2])/(b[2]-a[2]))
  if ib:result.append(b)
 return np.array(result)
def projected_surface_below(tri,z):
 # For a closed solid, any occupied vertical ray below z meets its lower
 # boundary below z. This projection therefore bounds a continuous -Z sweep.
 ps=[]
 for t in tri:
  if t[:,2].min()>z+1e-9:continue
  q=clip_below(t,z)
  if len(q)>=3:
   g=Polygon(q[:,:2])
   if g.area>1e-12:ps.append(g)
 return unary_union(ps)
def underside(tri,z):
 n=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
 sel=(np.max(np.abs(tri[:,:,2]-z),axis=1)<2e-5)&(n[:,2]<-1e-10)
 p=unary_union([Polygon(t[:,:2]) for t in tri[sel]])
 return p,int(np.count_nonzero(sel))
def gap_entries(row,roi,under,cache=None):
 # Positive XY bead overlap is deliberately distinguished from direct support.
 # No buffer expansion of underlay is called a guaranteed contact margin.
 if cache is None:reach=under.buffer(row['width']/2,quad_segs=32)
 else:
  if row['width'] not in cache:cache[row['width']]=under.buffer(row['width']/2,quad_segs=32)
  reach=cache[row['width']]
 outside=row['path'].intersection(roi).difference(reach)
 results=[]
 for g in shapes(outside,'LineString'):
  if g.length<=.005:continue
  a,b=np.array(g.coords[0]),np.array(g.coords[-1]);chord=float(np.linalg.norm(b-a))
  straight=abs(g.length-chord)<1e-6
  ds=[row['path'].project(Point(v)) for v in [a,b]]
  before=ds[0]>.05 and reach.covers(row['path'].interpolate(ds[0]-.05))
  after=ds[1]<row['path'].length-.05 and reach.covers(row['path'].interpolate(ds[1]+.05))
  results.append({'line':row['line'],'feature':row['feature'],'path_length_mm':g.length,
   'endpoint_chord_mm':chord,'is_straight_interval':straight,'local_xy_bounds':list(g.bounds),
   'first_xy':a.tolist(),'last_xy':b.tolist(),'preceding_0p05mm_command_sample_overlaps_underlay':before,
   'following_0p05mm_command_sample_overlaps_underlay':after,
   'both_samples_anchor':before and after})
 return results

def underlay_review(name,roi,contact,rows,support,M):
 roof=float((M@np.array([0,0,contact,1]))[2])
 # Include neighbouring previous-layer beads outside the new roof itself.
 # They can anchor a command that only just crosses the ROI boundary.
 window=roi.buffer(2)
 close=[r for r in rows if model(r['feature']) and r['footprint'].intersects(window)]
 target=min((r['top'] for r in close if r['top']>roof+1e-5),default=None)
 if target is None:return {'name':name,'status':'NO_FIRST_MODEL_LAYER_FOUND','contact_local_z':contact},None
 current=[r for r in close if abs(r['top']-target)<1e-6 and r['footprint'].intersects(roi)]
 previous_top=max((r['top'] for r in close if r['top']<=roof+1e-5),default=None)
 previous=[r for r in close if previous_top is not None and abs(r['top']-previous_top)<1e-6]
 relevant=[r for r in support if r['feature']=='Support interface' and r['top']<=roof+1e-5 and r['footprint'].intersects(window)]
 st=max((r['top'] for r in relevant),default=None)
 sr=[r for r in relevant if st is not None and abs(r['top']-st)<1e-6]
 first_line=min(r['line'] for r in current)
 prior_support=[r for r in sr if r['line']<first_line]
 pf=fp(previous);sf=fp(prior_support);initial=pf.union(sf)
 # The first pass uses only strictly previous-layer/model or previously emitted
 # support interface. The separate pass records lateral overlap with earlier
 # same-layer beads; later commands can never retroactively support the first.
 fixed_gaps=[];earlier=[];first=None;reach_cache={}
 for r in sorted(current,key=lambda q:q['line']):
  gaps=gap_entries(r,roi,initial,reach_cache);fixed_gaps+=gaps
  clipped=r['path'].intersection(roi)
  if first is None and clipped.length>.005:
   overlap=r['footprint'].intersection(roi).intersection(initial).area
   ordered=initial.union(fp(earlier));og=gap_entries(r,roi,ordered)
   first={'line':r['line'],'feature':r['feature'],'command_length_mm':r['path'].length,
    'clipped_centerline_length_mm':clipped.length,'prior_projected_bead_overlap_area_mm2':overlap,
    'no_prior_projected_overlap':overlap<=1e-10,'local_xy':r['xy'].tolist(),
    'prior_overlap_scope':'Above two fields concern only the bead portion inside this new-roof ROI, not the complete command.',
    'complete_command_prior_projected_overlap_area_mm2':r['footprint'].intersection(initial).area,
    'complete_command_without_prior_projection_overlap':r['footprint'].intersection(initial).area<=1e-10,
    'unbacked_intervals':gaps,'earlier_same_layer_command_count':len(earlier),
    'unbacked_intervals_also_allowing_only_preceding_same_layer_lateral_overlap':og}
  if first is None:earlier.append(r)
 def stats(gs):return {'count':len(gs),'max_curved_or_straight_path_mm':max((x['path_length_mm'] for x in gs),default=0),
  'max_true_straight_interval_mm':max((x['path_length_mm'] for x in gs if x['is_straight_interval']),default=0),
  'straight_intervals_with_both_end_samples':sum(x['is_straight_interval'] and x['both_samples_anchor'] for x in gs),
  'intervals':gs}
 result={'name':name,'status':'ACTUAL_PRECEDING_UNDERLAY_RECORDED' if prior_support else 'NO_PRECEDING_SUPPORT_INTERFACE_IN_ROI',
  'contact_local_z':contact,'contact_print_z':roof,'roi_area_mm2':roi.area,'roi_local_xy_bounds':list(roi.bounds),
  'first_model_print_z':target,'previous_model_print_z':previous_top,'last_interface_print_z':st,
  'nominal_vertical_contact_gap_mm':None if st is None else roof-st,
  'all_top_interface_emitted_before_first_model':len(prior_support)==len(sr),
  'top_interface_path_count':len(prior_support),'top_interface_area_under_roi_mm2':sf.intersection(roi).area,
  'previous_model_area_under_roi_mm2':pf.intersection(roi).area,
  'model_first_layer_path_count':len(current),'first_affected_command':first,
  'neighbouring_underlay_search_margin_mm':2,
  'without_previous_model_or_interface_overlap':stats(fixed_gaps),
  'same_layer_lateral_overlap_scope':'First affected command only; subsequent gap statistics conservatively omit all same-layer beads.',
  'interpretation':'Projected underlay across recorded air gap is process evidence, not bonded support. Same-layer overlap is lateral contact only. Curved command length is not a free straight bridge span.'}
 return result,(name,roi,previous,prior_support,current)

def main(folder):
 folder=path(folder).resolve(); inv=json.loads((folder/'invocation.json').read_text()); ar=json.loads((folder/'artifact-review.json').read_text())
 assert inv['status']=='SLICE_GENERATED_REVIEW_REQUIRED'
 assert ar['status']=='CURRENT_ECLIP_SLICE_ARTIFACT_IDENTITY_PASS' and ar['sources_and_artifacts_stable']
 assert inv['source_sha256_at_start']['cad/cable-trigger-input.scad']==SOURCE_SHA
 assert inv['part'] in {'cable-input-body','cable-input-lever','cable-input-cover'}
 evidence=dict(ar['evidence_sha256'])
 for p in [__file__,folder/'artifact-review.json']:evidence[rel(p)]=sha(p)
 for p,h in evidence.items():assert sha(p)==h,('Stale support-review evidence',p)
 M=np.array(ar['input_local_to_command']);I=np.linalg.inv(M);growth=ar['placement']['build_growth_local_z']
 assert abs(abs(M[2,2])-1)<1e-8 and np.max(np.abs(M[2,:2]))<1e-8
 archive=artifact.reader.read3mf(folder/'slice-review.3mf');normal=next(x for x in archive['parts'] if x['subtype']=='normal_part')
 E=np.eye(4);E[:3,3]=-np.array(ar['placement']['extruder_offset'])
 verts=parser.affine(normal['world_vertices'],I@E);tri=verts[normal['triangles']]
 source_tri=artifact.slicer.read_stl(path(inv['input']['file']))
 source_tri=parser.affine(source_tri,I@np.array(ar['placement']['cad_to_command']))
 out=ROOT/'output/current-eclip-support-review'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')/inv['part'];out.mkdir(parents=True)
 project=archive['project'];cfg=inv['pocket_contract'];roi_list=[]
 if cfg:
  assert growth==1 and cfg['growth']==1
  for j,c in enumerate(cfg['centres']):
   opening=hexagon(c,5.8);roi_list.append((f'M3_shoulder_{j+1}',opening.difference(Point(c).buffer(1.7,quad_segs=72)),cfg['contact']))
 if inv['part']=='cable-input-body':
  all_bottom,nfaces=underside(source_tri,-9)
  all_native_bottom,_=underside(tri,-9)
  # The two M3 shoulders share Z=-9 but are independent small faces. Do not
  # count their support as underlay of the large displaced mounting backplate.
  bottom=max(shapes(all_bottom),key=lambda g:g.area)
  native_bottom=max(shapes(all_native_bottom),key=lambda g:g.area)
  assert 4000<bottom.area<5000,('Unexpected current backplate underside',bottom.area)
  roi_list.append(('backplate_bottom',bottom,-9))
 else:bottom=None;nfaces=0;native_bottom=None
 maxroof=max((float((M@np.array([0,0,r[2],1]))[2]) for r in roi_list),default=0)
 rows=[];support=[];brim=[];first_model=[];counts=Counter();height_modes=defaultdict(set)
 for r in parser.extrusion_paths((folder/'plate_1.gcode').open()):
  counts[r.feature]+=1
  if not(r.feature.startswith('Support') or (model(r.feature) and r.layer<=maxroof+.21) or (r.feature=='Brim' and r.layer<=.100001)):continue
  assert np.max(np.abs(r.points[:,2]-r.layer))<1e-4,('Nonplanar or wrong-layer extrusion',r.line)
  q=parser.affine(r.points,I);ln=LineString(q[:,:2]);top=float(q[0,2]);zrange=sorted([top,top-growth*r.height]);foot=ln.buffer(r.width/2+ERROR,quad_segs=32)
  row={'line':r.line,'feature':r.feature,'top':r.layer,'height':r.height,'width':r.width,'xy':q[:,:2],
   'path':ln,'footprint':foot,'local_z':zrange,'nominal_footprint':ln.buffer(r.width/2,quad_segs=32)}
  rows.append(row);height_modes[r.feature].add(r.height)
  if r.feature.startswith('Support'):support.append(row)
  elif r.feature=='Brim':brim.append(row)
  elif model(r.feature) and r.layer<=.100001:first_model.append(row)
 # Underlay must not be overstated by inflating its radius. Use nominal declared
 # widths for the underlay calculation; the inflated footprint is only cleanup.
 under_rows=[dict(r,footprint=r['nominal_footprint']) for r in rows]
 under_support=[r for r in under_rows if r['feature'].startswith('Support')]
 findings=[];plotdata=[]
 for name,roi,z in roi_list:
  result,plot_item=underlay_review(name,roi,z,under_rows,under_support,M);findings.append(result)
  if plot_item:plotdata.append(plot_item)
 full_projection=projected_surface_below(tri,float(tri[:,:,2].max()+1))
 pockets=[];outside=[]
 if cfg:
  for j,c in enumerate(cfg['centres']):
   opening=hexagon(c,5.8);selected=[]
   for r in support:
    if r['footprint'].distance(Point(c))<4:
     selected.append(r)
   allfp=fp(selected);lo,hi=sorted(cfg['z'])
   bad=[r for r in selected if not opening.covers(r['footprint']) or r['local_z'][0]<lo-1e-5 or r['local_z'][1]>cfg['contact']+1e-5]
   outside.extend(bad)
   pockets.append({'index':j,'center_local_xy':c,'path_count':len(selected),'outside_path_lines':[r['line'] for r in bad],
    'complete_support_projection_outside_opening_mm2':allfp.difference(opening).area,
    'strict_all_selected_paths_in_original_shallow_hex':not bad,
    'opening':'exact AF5.8 hexagon; unchanged metal bearing shoulder'})
 # Only isolated exterior first-layer fragments may use a separate bed-cleaning
 # route. Whole normal-mesh projection includes geometry at every later height.
 bad_by_line={r['line']:r for r in outside};badrows=list(bad_by_line.values());other=[r for r in support if r['line'] not in bad_by_line]
 outside_fp=fp(badrows);other_fp=fp(other);brim_fp=fp(brim);first_model_fp=fp(first_model);islands=[];island_lines=set()
 for island in shapes(outside_fp):
  matched=[r for r in badrows if r['footprint'].intersects(island)]
  no_model=island.intersection(full_projection).area<1e-12
  is_bed=all(abs(r['top']-.1)<1e-6 for r in matched)
  separate=island.distance(other_fp)>0
  status='EXTERIOR_BED_RESIDUE_CLEAR_AFTER_PART_LIFT' if no_model and is_bed and separate else 'NOT_PROVEN_EXTERIOR_BED_ISLAND'
  if status.startswith('EXTERIOR'):island_lines.update(r['line'] for r in matched)
  islands.append({'classification':status,'lines':[r['line'] for r in matched],
   'local_xy_bounds':list(island.bounds),'height_range_print':[min(r['top']-r['height'] for r in matched),max(r['top'] for r in matched)],
   'whole_model_projection_overlap_mm2':island.intersection(full_projection).area,
   'whole_model_projection_gap_mm':island.distance(full_projection),'other_support_projection_gap_mm':island.distance(other_fp),
   'first_layer_model_bead_overlap_mm2':island.intersection(first_model_fp).area,'brim_overlap_mm2':island.intersection(brim_fp).area})
 # Continuous reverse-build extraction against actual normal mesh. This is a
 # conservative nominal full-bead XY envelope; no contact tolerance is erased.
 # For body/lever, every support slab sweeps toward local -Z to below the part.
 sweep=[]
 if support:
  assert growth==1
  per_top=defaultdict(list)
  for r in support:per_top[round(r['local_z'][1],6)].append(r)
  for z,rs in sorted(per_top.items()):
   obstacle=projected_surface_below(tri,z)
   swept=fp(rs);hit=swept.intersection(obstacle)
   if hit.area>1e-10:
    detail=[{'line':r['line'],'area_mm2':r['footprint'].intersection(obstacle).area,'bounds':list(r['footprint'].intersection(obstacle).bounds)} for r in rs if r['footprint'].intersection(obstacle).area>1e-10]
   else:detail=[]
   sweep.append({'support_top_local_z':z,'path_count':len(rs),'swept_projection_source_overlap_mm2':hit.area,
    'projected_contact_empty':hit.is_empty,'minimum_projected_clearance_mm':swept.distance(obstacle),
    'overlap_path_count':len(detail),'overlap_paths':detail,
    'method':'Actual normal-part boundary clipped below support upper slab plane, projected to XY; full bead projection translated continuously toward -localZ.'})
 remaining_bad=sorted(set(bad_by_line)-island_lines)
 for j,p in enumerate(pockets):p['unclassified_outside_lines_after_independent_bed_route']=[x for x in p['outside_path_lines'] if x not in island_lines]
 cleanup_clear=all(x['projected_contact_empty'] for x in sweep)
 plot(out,inv['part'],plotdata,support,full_projection,islands)
 result={'status':'ACTUAL_SUPPORT_UNDERLAY_AND_REVERSE_BUILD_REVIEW','part':inv['part'],'slice_folder':rel(folder),
  'created_utc':datetime.now(timezone.utc).isoformat(),'mapping':ar['input_local_to_command'],'resolved_process':ar['resolved_process'],
  'path_features':dict(counts),'support_paths':len(support),'feature_layer_height_metadata':{k:sorted(v) for k,v in height_modes.items()},
  'support_clearance_numeric_XY_padding_mm':ERROR,'underlay_uses_nominal_declared_bead_width':True,
  'underside_source':None if bottom is None else {'local_z':-9,'CAD_Y':-94,'print_height_mm':3,'downward_triangle_count_all_coplanar_regions':nfaces,
   'all_coplanar_down_faces_area_mm2':all_bottom.area,'component_areas_mm2':sorted([g.area for g in shapes(all_bottom)],reverse=True),
   'selection':'largest connected underside only; two small M3 shoulders are separate ROIs',
   'projected_area_mm2':bottom.area,'native_projected_area_mm2':native_bottom.area},
  'underlay':findings,'pocket_cleanup':pockets,'external_islands':islands,
  'unclassified_pocket_outside_lines':remaining_bad,'continuous_reverse_build_sweep':sweep,
  'nominal_reverse_build_sweep_clear':cleanup_clear,
  'removal_routes':['Lift part off PEI before support cleanup; do not install hardware first.',
    'Shallow M3-pocket supports exit through the original rear hex openings along -localZ.',
    'Body underside support exits directly away from the open rear/backplate side along -localZ; no need to push through M4 or M6 bores.',
    'Only separately classified exterior first-layer islands are bed residues; clear them with their contacting brim after lifting the part.'],
  'evidence_sha256':evidence,'sources_and_artifacts_stable':all(sha(p)==h for p,h in evidence.items()),
  'limits':['Declared nozzle-bead width/height is a nominal process model, not a scan of PETG.',
    '0.2 mm air-gap support does not guarantee bridge flatness, reliable release, removal force, grip/tool space, bearing cleanliness or strength.',
    'Curve path length is not free straight span; lateral overlap with earlier same-layer extrusion is reported separately from previous-layer support.',
    'This bounded review covers emitted support cleanup and the named first-roof ROIs, not every overhang, hole or production qualification.',
    'Positive nominal support-sweep overlap is preserved for interpretation; no automatic clipping of support beads to intended enforcers.'],
  'manufacturing_release':False,'physical_acceptance':False,'sent_to_printer':False}
 assert result['sources_and_artifacts_stable'];dump(out/'report.json',result)
 lines=['# 当前 E 型卡簧输入件支撑与承托审查','',f'对象：`{inv["part"]}`。实际切片：`{rel(folder)}`。详见 [report.json](report.json)、[承托图](underlay.png) 与 [清理投影图](cleanup.png)。','',f'实际支撑路径 {len(support)} 条；按完整名义珠体沿反生长方向连续扫掠，当前几何结果：{"空交" if cleanup_clear else "检出交叠，保留待解释"}。此结果不证明PETG剥离力或承面完整性。','', '| 区域 | 接触面/打印高度 | 末层支撑 | 空隙 | 无先前投影搭接的最长直线区间 |','|---|---|---|---|---|']
 for r in findings:
  lines.append(f'| {r["name"]} | {r["contact_local_z"]}/{r.get("contact_print_z")} | {r.get("last_interface_print_z")} | {r.get("nominal_vertical_contact_gap_mm")} | {r.get("without_previous_model_or_interface_overlap",{}).get("max_true_straight_interval_mm")} |')
 lines+=['','先前模型与支撑只用当时已打印的路径；另列同层先前线条的侧向搭接，不把后来线条倒算作首道支承。最长曲线路径与真实直线区间分开，均不是材料强度或挠度结果。','',f'螺母窝严格范围外、尚未归为独立床面残料的路径：{remaining_bad}。床面岛分类核了全高度模型投影、其他支撑及Brim，不假定它们要从螺母孔拔出。','', '清理顺序：取下正式零件，再从背面开放处移除支撑和浅窝支撑，最后清床面残料；五金尚不装入。源结构、孔径与金属承面未改，也没有试片。','', '制造及实物验收仍为 false。']
 (out/'README.md').write_text('\n'.join(lines)+'\n')
 print(json.dumps({'folder':rel(out),'part':inv['part'],'support_paths':len(support),'reverse_sweep_clear':cleanup_clear,'unclassified_pocket_lines':remaining_bad,'report_sha256':sha(out/'report.json')},ensure_ascii=False),flush=True)
 return result

def plot(out,part,plots,support,projection,islands):
 os.environ.setdefault('MPLCONFIGDIR',str(out/'mpl'));import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.collections import LineCollection
 if not plots:
  fig,ax=plt.subplots(figsize=(8,5));ax.text(.5,.5,'No support requested or emitted\nFeature review is separate',ha='center');ax.axis('off')
 else:
  fig,axs=plt.subplots(len(plots),3,figsize=(14,4.5*len(plots)),squeeze=False,layout='constrained')
  for i,(name,roi,prev,inter,current) in enumerate(plots):
   for j,rr in enumerate([prev,inter,current]):
    ax=axs[i,j];a,b,c,d=roi.bounds;pad=max(1,(c-a)*.06);ax.set_xlim(a-pad,c+pad);ax.set_ylim(b-pad,d+pad);ax.set_aspect('equal');ax.grid(alpha=.15)
    ax.set_title(name+' / '+['previous model','preceding top interface','first roof model'][j]);ax.set_xlabel('local X / mm');ax.set_ylabel('local Y / mm')
    for pg in shapes(roi):ax.plot(*pg.exterior.xy,color='#ad4173',lw=.6)
    if j==2:
     for pg in shapes(fp(inter)):ax.fill(*pg.exterior.xy,color='#e5ac65',alpha=.5)
    for r in rr:ax.add_collection(LineCollection([r['xy']],colors='#c57626' if r['feature'].startswith('Support') else '#166787',linewidths=.6 if name=='backplate_bottom' else 1))
  fig.suptitle(part+' — actual G-code order and projected underlay; air gap retained')
 fig.savefig(out/'underlay.png',dpi=155);plt.close(fig)
 fig,ax=plt.subplots(figsize=(10,8),layout='constrained')
 for pg in shapes(projection):
  ax.fill(*pg.exterior.xy,color='#d2dee3',alpha=.7)
  for ring in pg.interiors:ax.fill(*ring.xy,color='white')
 for pg in shapes(fp(support)):ax.fill(*pg.exterior.xy,color='#dd8738',alpha=.7)
 for island in islands:
  a,b,c,d=island['local_xy_bounds'];ax.plot([a,c,c,a,a],[b,b,d,d,b],color='#b42158',lw=1)
 ax.set_aspect('equal');ax.grid(alpha=.2);ax.set_xlabel('local X / mm');ax.set_ylabel('local Y / mm')
 ax.set_title(part+' — nominal cleanup projection\nGray: full model at any height; orange: all support; red: pocket-boundary exceptions\nReverse-build clearance is checked per height, not inferred from this projection.')
 fig.savefig(out/'cleanup.png',dpi=155);plt.close(fig)

if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--folder',type=Path,required=True);main(ap.parse_args().folder)

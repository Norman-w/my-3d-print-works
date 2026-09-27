#!/usr/bin/env python3
"""Bounded emitted-layer audit for the isolated input-body seat candidate.

Read-only: no CAD changes, slicing, or print submission. All dimensions below
refer to the frozen candidate whose two bottom-plane edits are recorded in its
invocation. Compare --folder invocations rather than assuming the layer phase.
"""
from pathlib import Path
import argparse,collections,hashlib,json,math,os,sys
import numpy as np
from shapely.geometry import LineString,Point,box
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'analysis'))
import cable_input_slice_review as h
ERROR=h.ARC_ERROR+h.BUFFER_ERROR
NONMODEL={'Custom','Brim','Skirt','Prime tower','Prime tower infill','Flush','Undefined',''}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def model(f):return f not in NONMODEL and not f.startswith('Support')
def path(p):
 p=Path(p);return p if p.is_absolute()else ROOT/p

def footprint(rows,extra):
 return unary_union([LineString(r['xy']).buffer(max(.00001,r['width']/2+extra),resolution=32)for r in rows if model(r['feature'])])
def radius(rows):
 values=[LineString(r['xy']).distance(Point(0,0))-r['width']/2-ERROR for r in rows if model(r['feature'])]
 return min(values,default=None)

def run(folder):
 folder=folder.resolve();inv=json.loads((folder/'invocation.json').read_text());assert inv['part']=='cable-input-body';assert inv.get('diagnostic_candidate'),'Only explicit candidate invocations supported'
 proofpath=path(inv['diagnostic_candidate']['geometry_review']);proof=json.loads(proofpath.read_text());assert sha(proofpath)==inv['diagnostic_candidate']['geometry_review_sha256'];assert proof['candidate_exactly_two_bottom_edits_after_namespace_normalization']
 command_to_local,mapping=h.slice_mapping(folder,inv);local_to_command=np.linalg.inv(command_to_local);assert abs(local_to_command[2,3]-12)<1e-7, 'Bed must be local Z -12'
 out=folder/'body-seat-layer-review';out.mkdir(exist_ok=True)
 layers=collections.defaultdict(lambda:dict(axis=[],nut=[],all_counts=collections.Counter(),heights=set()))
 windows=[(5.8,8.4),(16.2,17.6)];previous_layer=0.;last_layer=None;layer_pitch={}
 with (folder/'plate_1.gcode').open()as file:
  for r in h.extrusion_paths(file):
   if r.layer!=last_layer:
    previous_layer=last_layer if last_layer is not None else 0.;last_layer=r.layer;layer_pitch[round(r.layer,6)]=r.layer-previous_layer
   if not any(lo-1e-6<=r.layer<=hi+1e-6 for lo,hi in windows):continue
   if not np.allclose(r.points[:,2],r.layer,atol=1e-5):raise ValueError('Nonplanar toolpath needs separate audit')
   z=round(r.layer,6);q=h.affine(r.points,command_to_local);row={'xy':q[:,:2],'width':r.width,'feature':r.feature,'line':r.line,'height':r.height};item=layers[z];item['heights'].add(r.height);item['all_counts'][r.feature]+=1
   # Retain complete command segments crossing either ROI; do not clip arcs.
   lo=q[:,:2].min(0)-r.width/2-ERROR;hi=q[:,:2].max(0)+r.width/2+ERROR
   if (hi>=[-6,-6]).all()and(lo<=[6,6]).all():item['axis'].append(row)
   if (hi>=[-39,-28]).all()and(lo<=[-32,-20]).all():item['nut'].append(row)
 axis_ring=Point(0,0).buffer(3.8,resolution=128).difference(Point(0,0).buffer(2.7,resolution=128))
 nut_probe=box(-37.5,-25,-33.5,-23)
 axes=[];nuts=[]
 for z,item in sorted(layers.items()):
  lh=layer_pitch[z];basic={'layer_top_print_mm':z,'layer_bottom_print_mm':round(z-lh,8),'layer_pitch_mm':lh,'declared_bead_heights_on_layer_mm':sorted(item['heights']),'top_local_z_mm':z-12}
  if 5.8-1e-6<=z<=8.4+1e-6:
   rows=item['axis'];low=footprint(rows,-ERROR);high=footprint(rows,ERROR);clear=radius(rows)
   axes.append({**basic,'minimum_clear_radius_lower_mm':clear,'minimum_clear_diameter_lower_mm':None if clear is None else 2*clear,'bearing_probe_annulus_r_mm':[2.7,3.8],'bearing_probe_area_mm2':axis_ring.area,'bead_area_in_annulus_lower_mm2':axis_ring.intersection(low).area,'bead_area_in_annulus_upper_mm2':axis_ring.intersection(high).area,'features':dict(collections.Counter(r['feature']for r in rows))})
  if 16.2-1e-6<=z<=17.6+1e-6:
   rows=item['nut'];low=footprint(rows,-ERROR);high=footprint(rows,ERROR);free=nut_probe.difference(high)
   nearest=min((LineString(r['xy']).distance(Point(-35.5,-24))-r['width']/2-ERROR for r in rows if model(r['feature'])),default=None)
   nuts.append({**basic,'witness_rectangle_local_xy':[[-37.5,-25],[-33.5,-23]],'probe_area_mm2':nut_probe.area,'bead_area_in_probe_lower_mm2':nut_probe.intersection(low).area,'bead_area_in_probe_upper_mm2':nut_probe.intersection(high).area,'free_probe_area_lower_mm2':free.area,'central_inscribed_clear_radius_lower_mm':nearest,'features':dict(collections.Counter(r['feature']for r in rows))})
 # Opening onset defines a floor at that layer's bottom, not at nozzle top.
 expanded=[r for r in axes if r['minimum_clear_radius_lower_mm']is not None and r['minimum_clear_radius_lower_mm']>3.8 and r['layer_top_print_mm']<8.1]
 assert expanded,'No resolved sleeve recess transition in selected window'
 first=expanded[0];floor=first['layer_bottom_print_mm'];prior=[r for r in axes if r['layer_top_print_mm']<=floor+1e-6];assert prior
 last=prior[-1];assert last['minimum_clear_radius_lower_mm']<3 and last['bead_area_in_annulus_lower_mm2']>0,'Transition not bracketed by emitted bearing material'
 closed=[r for r in nuts if r['bead_area_in_probe_lower_mm2']>nut_probe.area*.5];assert closed,'No resolved nut roof material in selected window'
 firstroof=closed[0];roof=firstroof['layer_bottom_print_mm'];priorroof=[r for r in nuts if r['layer_top_print_mm']<=roof+1e-6];assert priorroof and priorroof[-1]['bead_area_in_probe_upper_mm2']<1e-8,'Nut witness not clear immediately below roof'
 roof_rows=[r for r in layers[firstroof['layer_top_print_mm']]['nut'] if model(r['feature']) and LineString(r['xy']).buffer(r['width']/2+ERROR,resolution=32).intersects(nut_probe)]
 roof_bottoms=[firstroof['layer_top_print_mm']-r['height'] for r in roof_rows];assert roof_bottoms
 assert max(abs(v-roof)for v in roof_bottoms)<.00001,'Roof bead height differs materially from layer phase; slab-specific review required'
 findings={'axis_sleeve_nominal_floor_print_mm':6.5,'axis_sleeve_emitted_floor_print_mm':floor,'axis_floor_error_mm':round(floor-6.5,8),'axis_nominal_floor_local_z_mm':-5.5,'axis_first_expanded_layer_top_mm':first['layer_top_print_mm'],'axis_first_expanded_clear_diameter_lower_mm':first['minimum_clear_diameter_lower_mm'],'axis_preceding_layer_top_mm':last['layer_top_print_mm'],'axis_preceding_clear_diameter_lower_mm':last['minimum_clear_diameter_lower_mm'],'stop_nut_nominal_roof_print_mm':16.9,'stop_nut_emitted_roof_underside_print_mm':roof,'stop_nut_roof_error_mm':round(roof-16.9,8),'stop_nut_declared_bead_bottom_range_mm':[min(roof_bottoms),max(roof_bottoms)],'stop_nut_first_roof_layer_top_mm':firstroof['layer_top_print_mm'],'stop_nut_preceding_clear_witness_mm2':priorroof[-1]['free_probe_area_lower_mm2']}
 os.environ.setdefault('MPLCONFIGDIR',str(out/'mpl'));import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
 from matplotlib.collections import LineCollection
 from matplotlib.patches import Circle,Rectangle
 levelsaxis=sorted(set([last['layer_top_print_mm'],first['layer_top_print_mm'],next((r['layer_top_print_mm']for r in axes if r['layer_top_print_mm']>first['layer_top_print_mm']),first['layer_top_print_mm'])]))
 levelsnut=sorted(set([priorroof[-1]['layer_top_print_mm'],firstroof['layer_top_print_mm'],next((r['layer_top_print_mm']for r in nuts if r['layer_top_print_mm']>firstroof['layer_top_print_mm']),firstroof['layer_top_print_mm'])]))
 fig,axs=plt.subplots(2,3,figsize=(15,9),layout='constrained');colors={'Outer wall':'#145879','Inner wall':'#459ab0','Top surface':'#609b36','Bridge':'#dd7827','Bottom surface':'#80ac48','Internal solid infill':'#8cb487'}
 for line,(feature,levels)in enumerate([('axis',levelsaxis),('nut',levelsnut)]):
  for ax,z in zip(axs[line],levels):
   center=[0,0]if feature=='axis'else[-35.5,-24];lim=5 if feature=='axis' else 4
   ax.set_xlim(center[0]-lim,center[0]+lim);ax.set_ylim(center[1]-lim,center[1]+lim);ax.set_aspect('equal');ax.grid(alpha=.18);ax.set_title(f'{feature}: print top {z:g}, bottom {z-layer_pitch[z]:g} mm');ax.set_xlabel('Input local X / mm');ax.set_ylabel('Input local Y / mm')
 fig.canvas.draw()
 for line,(feature,levels)in enumerate([('axis',levelsaxis),('nut',levelsnut)]):
  for ax,z in zip(axs[line],levels):
   scale=(ax.transData.transform([1,0])-ax.transData.transform([0,0]))[0]*72/fig.dpi
   for r in layers[z][feature]:
    if not model(r['feature']):continue
    ax.add_collection(LineCollection([r['xy']],colors=colors.get(r['feature'],'#7a8085'),linewidths=r['width']*scale,capstyle='round'))
   if feature=='axis':
    for radiusv in [2.25,4.15]:ax.add_patch(Circle((0,0),radiusv,fill=False,color='#b94c94',ls=':',lw=1))
   else:ax.add_patch(Rectangle((-37.5,-25),4,2,fill=False,color='#b94c94',ls=':',lw=1))
 fig.suptitle('Actual emitted bead paths near sleeve floor and stop-nut roof | nominal boundaries in magenta');fig.savefig(out/'seat-transition-layers.png',dpi=160);plt.close(fig)
 result={'status':'NOMINAL_DATUM_LEVELS_MATCH_EMITTED_SLABS'if abs(findings['axis_floor_error_mm'])<1e-6 and abs(findings['stop_nut_roof_error_mm'])<1e-6 else'LAYER_QUANTIZATION_DATUM_SHIFT','part':inv['part'],'diagnostic_candidate_only':True,'mapping':mapping,'findings':findings,'axis_layers':axes,'stop_nut_layers':nuts,'error_envelope_mm':ERROR,'source_sha256_at_start':inv['source_sha256_at_start'],'artifact_sha256':{n:sha(folder/n)for n in ['invocation.json','plate_1.gcode','slice-review.3mf']},'proof_file':str(proofpath.relative_to(ROOT)),'proof_sha256':sha(proofpath),'script_sha256':sha(__file__),'parser_sha256':sha(ROOT/'analysis/cable_input_slice_review.py'),'limitations':['Datum comes from positive extrusion slab boundaries and bracketed change in clear opening, not nominal layer counts or nozzle top alone.','Radius is a conservative inscribed empty disk from declared bead widths plus arc/buffer uncertainty; it is not printed PETG fit.','Nut roof uses the interior local-X [-37.5,-33.5], Y[-25,-23] witness. Adjacent-layer freedom of this witness is not full nut chamber, insertion path, bridge sag or surface finish acceptance.','No assumption of adequate sleeve preload, strength, creep or real return behavior.','Candidate remains isolated; no canonical source or published inventory is adopted by this review.'],'manufacturing_release':False,'physical_acceptance':False,'sent_to_printer':False}
 dump(out/'report.json',result);print(json.dumps({'folder':str(folder.relative_to(ROOT)),'status':result['status'],'findings':findings},ensure_ascii=False,indent=2));return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--folder',type=Path,required=True);args=p.parse_args();run(args.folder)

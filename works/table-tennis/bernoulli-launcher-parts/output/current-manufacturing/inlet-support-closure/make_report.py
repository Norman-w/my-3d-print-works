#!/usr/bin/env python3
"""Freeze bounded evidence and readable sequence; deliberately retain pending."""
from pathlib import Path
import json,hashlib,importlib.util,sys,os
import numpy as np
P=Path(__file__).resolve().parent;ROOT=P.parents[2];sys.path[:0]=[str(ROOT/'analysis'),str(ROOT/'scripts')]
from cable_input_slice_review import extrusion_paths,affine
from review_cable_slice import read_stl
F=ROOT/'output/current-manufacturing/feeder-new/runs/20260927T094300899015Z/inlet-rear-anchor-z-down-supported'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rel(p):return str(Path(p).relative_to(ROOT))
def load(p):return json.loads(Path(p).read_text())
def dump(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def main():
 original=load(P/'original-sweep/report.json');alternative=load(P/'alternative-sweep/report.json');partition=load(P/'original-partition/report.json');nose=load(P/'nose-access.json');old=load(F/'current-review.json');stl=ROOT/old['instances'][0]['input']['file'];M=np.array(old['instances'][0]['actual_mapping']['current_cad_to_gcode_command']);tri=read_stl(stl)
 os.environ['MPLCONFIGDIR']=str(P/'matplotlib-config');import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
 from matplotlib.collections import LineCollection,PolyCollection
 paths=[]
 for r in extrusion_paths((F/'plate_1.gcode').open()):
  if r.feature.startswith('Support'):paths.append(affine(r.points,np.linalg.inv(M)))
 fig,axs=plt.subplots(1,3,figsize=(15,6),layout='constrained')
 for ax,kind,x,w,zrange in zip(axs,['M4','M2_5','strap'],[-43,-10.5,-20.5],[8,4,4],[[-124,-106],[-150,-138],[-141,-129]]):
  ts=tri[(tri[:,:,0].max(1)>=x-w)&(tri[:,:,0].min(1)<=x+w)]
  ax.add_collection(PolyCollection(ts[:,:,[1,2]],facecolors='#7ea5b7',edgecolors='#346579',linewidths=.2,alpha=.32))
  selected=[p for p in paths if p[:,0].max()>=x-w and p[:,0].min()<=x+w]
  seg=np.concatenate([np.stack([q[:-1,[1,2]],q[1:,[1,2]]],axis=1)for q in selected]);ax.add_collection(LineCollection(seg,colors='#d9841e',linewidths=.4,alpha=.7))
  cuts=[r for r in nose['windows']if r['id'].startswith(kind)and r['id'].endswith('-1')]
  for r in cuts:
   lo,hi=r['lo'],r['hi'];ax.add_patch(plt.Rectangle((lo[1],lo[2]),hi[1]-lo[1],hi[2]-lo[2],color='#9653a9',fill=False,lw=1.5));ax.plot([lo[1],hi[1]],[r['cut_plane_CAD_Z']]*2,'--',color='#9653a9',lw=1)
  ylim=(-31,1)if kind=='M4'else(-66,-27)
  ax.set_xlim(*ylim);ax.set_ylim(*zrange);ax.set_aspect('equal');ax.set_title(f'{kind}, CAD X band {x-w:g}..{x+w:g}');ax.set_xlabel('CAD Y / mm');ax.set_ylabel('CAD Z / mm')
  yy=zrange[1]-2;ax.annotate('trimmed head exits -Y',xy=(ylim[0]+1,yy),xytext=(ylim[0]+12,yy),fontsize=8,arrowprops={'arrowstyle':'->'},ha='left')
 fig.suptitle('Actual support (orange), part projection (blue), declared cutter-nose space (purple)\nX-band projections, not tool certification; mirrored right-hand operation is separately checked')
 fig.savefig(P/'cut-access-sections.png',dpi=160);plt.close(fig)
 actual_clear=all(r['clear_actual_model']for r in partition['rows']);assert actual_clear
 # Disambiguate, never erase, the exact current-STL key-bottom counterexample.
 failure=partition['blocked_slabs'];assert len(failure)==1
 key_tri=tri[(abs(tri[:,:,2]+152.60000610351562)<1e-10).all(1)]
 contact={'raw_partition_status':partition['status'],'raw_failure':failure,'source_key_floor_CAD_Z':-152.60000610351562,'source_key_floor_print_Z':3.399993896484375,'support_top_print_Z':3.4,'max_axial_overlap_mm':3.4-3.399993896484375,'projected_overlap_area_mm2':failure[0]['stl_hit_area'],'overlap_volume_upper_mm3':failure[0]['stl_hit_area']*(3.4-3.399993896484375),'flat_source_triangle_count':len(key_tri),'actual_model_gcode_overlap':False,'interpretation':'The exact STL has a 6.103515625e-6 mm key-bottom overlap with the nominal support upper slab, caused by the stored -152.6000061035 coordinate versus the emitted 3.4 layer. It is not silently removed by an epsilon. The actual emitted model envelope is clear. Physical interface release is still unverified; this microscopic source/layer discrepancy is not evidence of a mechanically locked branch.'}
 dump(P/'key-bottom-boundary.json',contact)
 altfolder=ROOT/alternative['slice_folder'];altr=load(altfolder/'current-review.json')
 sourcefiles=[F/'current-review.json',F/'invocation.json',F/'slice-review.3mf',F/'plate_1.gcode',stl,ROOT/'cad/inlet-retention-final.scad',ROOT/'output/current-manufacturing/feeder-new/report.json',ROOT/'output/current-manufacturing/feeder-new/mapping.json']
 evidence=[P/'README.md',P/'original-sweep/report.json',P/'alternative-sweep/report.json',P/'original-partition/report.json',P/'nose-access.json',P/'key-bottom-boundary.json',altfolder/'current-review.json',P/'original-partition/branch-map.png',P/'cut-access-sections.png']
 report={'schema':'inlet-support-closure-v1','status':'INLET_REAR_BOUNDED_REMOVAL_SEQUENCE_DOCUMENTED_PENDING_TOOL_FINISH','instance_id':'feeder/inlet-rear','current_stl_sha256':sha(stl),'slice_folder':rel(F),'selected_3mf':rel(F/'slice-review.3mf'),'selected_3mf_sha256':sha(F/'slice-review.3mf'),'gcode':rel(F/'plate_1.gcode'),'gcode_sha256':sha(F/'plate_1.gcode'),'plate_quantity':1,'needs_reslice':False,'pending_review':True,'process_status':'CURRENT_SLICE_REVIEW_FLAGGED','reason':'The original current slice is valid. Six obstructing cavity branches have actual locations, accessible finite cutter-nose windows, and a concrete proposed sequence. Once these regions are removed, all remaining external-tree slabs have a clear continuous -CAD Z sweep against actual emitted model material. Complete mouth trimming/grasp/jaw motion for the 2.9 mm holes and 3 mm slots is not certified; do not infer this from small pick or nose clearance.','old_report':rel(ROOT/'output/current-manufacturing/feeder-new/report.json'),'old_report_sha256':sha(ROOT/'output/current-manufacturing/feeder-new/report.json'),'evidence':[{'path':rel(p),'sha256':sha(p)}for p in evidence],'original_and_sources_unchanged':{rel(p):sha(p)for p in sourcefiles},'original_support_records':original['support_record_count'],'original_whole_down_sweep_blocked_slabs':original['blocked_slabs'],'alternate':{'folder':rel(altfolder),'current_stl_same_sha':alternative['source_stl_sha256']==sha(stl),'all_native_identity_profile_bed_feature_checks_pass':all(altr['checks'].values()),'support_records':alternative['support_record_count'],'whole_down_sweep_blocked_slabs':alternative['blocked_slabs'],'adopted':False,'reason':'One alternate split-face-down slice retained as a counterexample. Automatic supports still flare after holes and wrap behind the collar; no advantage sufficient to replace original.'},'partition_regions':partition['regions'],'remaining_external_tree':{'actual_model_sweep_clear':actual_clear,'reviewed_slab_intervals':partition['remaining_slabs'],'exact_source_boundary_issue':contact},'nose_windows':{'count':len(nose['windows']),'all_source_and_actual_model_clear':all(r['nominal_nose_space_clear']for r in nose['windows']),'all_intersect_real_support':all(r['support_commands']for r in nose['windows']),'not_a_purchased_tool_qualification':True},'not_proven':['A complete commercially specified cutter/jaw/handle closing sweep at each flush mouth.','Grasp and fragment size at the M2.5 and textile-slot support caps; the outer tree does not pass bodily through those openings.','Same-PETG adhesion/separation force, debris, dimensional accuracy, bearing-face condition, material strength.'],'no_further_slice_or_geometry_change_in_this_review':True,'manufacturing_release':False,'physical_acceptance':False,'sent_to_printer':False,'report_builder_sha256':sha(__file__)}
 dump(P/'report.json',report)
 mapping={k:report[k]for k in ['instance_id','current_stl_sha256','slice_folder','selected_3mf','selected_3mf_sha256','gcode','gcode_sha256','plate_quantity','needs_reslice','pending_review','process_status','reason']};mapping.update(report_file=rel(P/'report.json'),report_sha256=sha(P/'report.json'));dump(P/'mapping.json',[mapping]);print(report['status'],sha(P/'report.json'))
if __name__=='__main__':main()

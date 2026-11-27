#!/usr/bin/env python3
"""Read native G-code rear-key deposition, preserving time order and support gap.
No slicing or CAD mutation. Refuses to overwrite an existing output report.
"""
from pathlib import Path
import argparse, collections, hashlib, importlib.util, json, math, re, sys
import numpy as np
from shapely.geometry import LineString, Polygon, box
from shapely.ops import nearest_points, unary_union
ROOT=Path(__file__).resolve().parents[2]
DEFAULT=ROOT/'output/current-inlet-process-revision/runs/20260927T104831129053Z'
sys.path.insert(0,str(ROOT/'analysis'))
import cable_input_slice_review as g
spec=importlib.util.spec_from_file_location('binding',ROOT/'output/current-manufacturing/input-process/bind_current_input_process.py')
binding=importlib.util.module_from_spec(spec);spec.loader.exec_module(binding)
SKIP={'Custom','Flush','Prime tower','Prime tower infill','Undefined','','Brim','Skirt'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rel(p):
    try:return str(Path(p).resolve().relative_to(ROOT))
    except ValueError:return str(Path(p).resolve())
def lines(geometry):
    if geometry.is_empty:return []
    if geometry.geom_type=='LineString':return [geometry]
    return [p for p in getattr(geometry,'geoms',[]) if p.geom_type=='LineString']
def spans(path,mask):
    ss=lines(path.difference(mask))
    return {'max_gap_mm':max([q.length for q in ss]or[0]),'sum_gap_mm':sum(q.length for q in ss),'gaps':[{'length_mm':q.length,'xy_bounds':list(q.bounds)}for q in ss]}
def analyze(folder):
    folder=Path(folder).resolve();code=folder/'plate_1.gcode';inv=json.loads((folder/'invocation.json').read_text())
    assert inv['return_code']==0 and inv['native_result']['return_code']==0
    assert sha(code)==inv['artifact_sha256']['plate_1.gcode']
    assert sha(folder/'slice-review.3mf')==inv['artifact_sha256']['slice-review.3mf']
    archive=binding.read3mf(folder/'slice-review.3mf');assert archive['archived_gcode_sha']==sha(code)
    normals=[p for p in archive['parts'] if p['subtype']=='normal_part'];assert len(normals)==1
    n=normals[0];offset=np.array([float(n['meta']['source_offset_'+a])for a in 'xyz'])
    raw=re.search(r'^; extruder_offset = ([^\n]+)',code.read_text(),re.M).group(1).split(',');assert len(raw)==1
    E=np.eye(4);E[:3,3]=-np.array([*map(float,raw[0].split('x')),0.])
    U=np.eye(4);U[:3,3]=-offset;M=E@archive['build']@n['component']@U;inverse=np.linalg.inv(M)
    assert np.allclose(M[:3,:3],np.eye(3)), 'This bounded review requires original +CAD Z build.'
    assert archive['project']['layer_height']=='0.1' and archive['project']['initial_layer_print_height']=='0.1'
    regionfile=folder/'regional-review.json'
    if regionfile.exists():assert np.allclose(M,np.array(json.loads(regionfile.read_text())['source_to_command']))
    roi=unary_union([box(x-3,-55,x+3,-40)for x in [-10.5,10.5]])
    keys={x:box(x-1.3,-53.8,x+1.3,-48.4)for x in [-10.5,10.5]};rec=[]
    for r in g.extrusion_paths(code.open()):
        if r.feature in SKIP or not 12<=r.layer<=16.0:continue
        points=g.affine(r.points,inverse);line=LineString(points[:,:2]);foot=line.buffer(r.width/2,quad_segs=32)
        if not foot.intersects(roi):continue
        rec.append(dict(line=r.line,stroke=r.stroke,z=round(float(points[0,2]),6),print_z=r.layer,height=r.height,bottom=float(points[:,2].min()-r.height),feature=r.feature,width=r.width,points=points,line2d=line,foot=foot,model=not r.feature.startswith('Support')))
    model=[r for r in rec if r['model']];sup=[r for r in rec if not r['model']]
    first={x:min(r['print_z']for r in model if r['print_z']>14.3 and r['foot'].intersection(keys[x]).area>0)for x in keys}
    rows=[];nearest=[]
    for r in model:
        for x,k in keys.items():
            if r['print_z']<first[x]-.00001 or r['print_z']>first[x]+.30001:continue
            clipped=r['foot'].intersection(k);cl=r['line2d'].intersection(k)
            if clipped.area==0:continue
            prev=[q for q in model if q['line']<r['line'] and abs(q['z']-round(r['z']-.1,6))<1e-5]
            earlier=[q for q in model if q['line']<r['line'] and abs(q['z']-r['z'])<1e-5]
            supports=[q for q in sup if q['line']<r['line'] and -1e-5<=r['bottom']-q['z']<=.20001]
            pm=unary_union([q['foot']for q in prev]);em=unary_union([q['foot']for q in earlier]);sm=unary_union([q['foot']for q in supports])
            witness=unary_union([pm,em,sm]).buffer(max(0,r['width']/2-.00325),quad_segs=32)
            sr=[dict(line=q['line'],feature=q['feature'],print_top_z=q['print_z'],vertical_gap_to_model_bottom_mm=r['bottom']-q['z'],nominal_xy_overlap_area_mm2=clipped.intersection(q['foot']).area)for q in supports if clipped.intersection(q['foot']).area>0]
            er=[dict(line=q['line'],feature=q['feature'],nominal_xy_overlap_area_mm2=clipped.intersection(q['foot']).area)for q in earlier if clipped.intersection(q['foot']).area>0]
            row=dict(side_x=x,line=r['line'],stroke=r['stroke'],feature=r['feature'],print_z=r['print_z'],cad_z_slab=[r['bottom'],r['z']],width_mm=r['width'],cad_path=r['points'].tolist(),rear_key_bead_area_mm2=clipped.area,
                previous_model_overlap_area_mm2=clipped.intersection(pm).area,earlier_same_layer_model_overlap_area_mm2=clipped.intersection(em).area,support_projection_within_0p2_gap_overlap_area_mm2=clipped.intersection(sm).area,
                rear_key_centerline_length_mm=cl.length,centerline_only_previous_model=spans(cl,pm),centerline_previous_model_or_support_projection=spans(cl,unary_union([pm,sm])),
                bead_overlap_witness_using_previous_same_layer_support=spans(cl,witness),earlier_same_layer_witnesses=er,retained_support_witnesses=sr)
            rows.append(row)
            if abs(r['print_z']-first[x])<1e-5 and not any(t['side_x']==x for t in nearest):
                rr=[]
                for z in sorted({q['print_z']for q in sup if -.00001<=r['print_z']-r['height']-q['print_z']<=.60001}):
                    choices=[q for q in sup if q['line']<r['line'] and abs(q['print_z']-z)<1e-5]
                    if not choices:continue
                    q=min(choices,key=lambda q:clipped.distance(q['foot']));pa,pb=nearest_points(clipped,q['foot'])
                    rr.append(dict(support_line=q['line'],support_feature=q['feature'],support_print_top_z=z,vertical_gap_to_model_bottom_mm=r['bottom']-q['z'],nominal_xy_bead_distance_mm=clipped.distance(q['foot']),nearest_model_point_xy=[pa.x,pa.y],nearest_support_point_xy=[pb.x,pb.y],support_width=q['width']))
                nearest.append(dict(side_x=x,first_model_line=r['line'],rows=rr))
    summary=[]
    for x in keys:
        for z in sorted(set(r['print_z']for r in rows if r['side_x']==x)):
            rr=[r for r in rows if r['side_x']==x and r['print_z']==z]
            summary.append(dict(side_x=x,print_z=z,records=len(rr),first_line=min(r['line']for r in rr),last_line=max(r['line']for r in rr),records_with_prev_model_overlap=sum(r['previous_model_overlap_area_mm2']>0 for r in rr),records_with_earlier_same_layer_overlap=sum(r['earlier_same_layer_model_overlap_area_mm2']>0 for r in rr),records_with_support_projection_overlap_within_0p2_gap=sum(r['support_projection_within_0p2_gap_overlap_area_mm2']>0 for r in rr),max_centerline_prev_layer_gap_mm=max(r['centerline_only_previous_model']['max_gap_mm']for r in rr),max_centerline_model_or_support_projection_gap_mm=max(r['centerline_previous_model_or_support_projection']['max_gap_mm']for r in rr),max_no_witness_overlap_run_mm=max(r['bead_overlap_witness_using_previous_same_layer_support']['max_gap_mm']for r in rr)))
    sourcefiles=[code,folder/'slice-review.3mf',folder/'invocation.json',ROOT/'cad/inlet-retention-final.scad',Path(g.__file__),Path(binding.__file__),Path(__file__)]
    if regionfile.exists():sourcefiles.append(regionfile)
    return dict(status='KEY_GROWTH_PATH_EVIDENCE_NOT_MANUFACTURING_RELEASE',folder=rel(folder),scope='Actual candidate rear-key upper first deposition and next three layers only. No slicing, CAD mutation or physical print. Future same-layer paths are excluded.',inputs={rel(p):sha(p)for p in sourcefiles},mapping=M.tolist(),key_regions={str(x):list(k.bounds)for x,k in keys.items()},actual_first_upper_key_print_z_mm=first,
        method=dict(previous_layer_model='All earlier model records at current top minus0.1.',same_layer='Only model line numbers earlier than the candidate record, never later neighboring loops.',support='Earlier support tops model-bottom−0.20001 to model-bottom+0.00001; projected proximity does not bridge the actual air gap. Nearest-support table also records larger vertical gaps separately.',nominal_bead='Emitted width/2 planar buffer; parser arc sagitta <=.00125mm. The overlap-witness dilation by current width/2 minus.00325 treats actual bead width, not centerline alone.',limits='Nominal path/side-overlap witness is not material adhesion/bridge sag. Support grid is discontinuous. No-gap is not an automatic manufacturing pass; a gap is not automatically a whole-line floating claim.'),layer_summary=summary,records=rows,nearest_support_to_first_model=nearest,new_geometry_checks_run=False,manufacturing_release=False,physical_acceptance=False)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--folder',type=Path,default=DEFAULT);parser.add_argument('--output',type=Path);args=parser.parse_args()
    target=args.output or args.folder/'key-growth-review.json'
    if target.exists():raise SystemExit('Refusing to overwrite existing report: '+str(target))
    target.parent.mkdir(parents=True,exist_ok=True);result=analyze(args.folder);target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(file=str(target),sha256=sha(target),first_layers=result['actual_first_upper_key_print_z_mm'],layer_summary=result['layer_summary']),ensure_ascii=False,indent=2))
if __name__=='__main__':main()

#!/usr/bin/env python3
"""Read this frozen slice only; no CAD, slicer, or printer calls."""
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timezone
import hashlib, importlib.util, json, math, os, sys
import numpy as np
from shapely.geometry import Polygon, LineString, box
from shapely.ops import unary_union

OUT=Path(__file__).resolve().parent
ROOT=next(p for p in OUT.parents if (p/'cad/inlet-retention-final.scad').is_file())
sys.path[:0]=[str(ROOT/'analysis'),str(ROOT/'scripts')]
from cable_input_slice_review import extrusion_paths, affine, bead, IGNORED
from cable_slice_artifacts import normalization_review
from review_cable_slice import read_stl
spec=importlib.util.spec_from_file_location('reuse_archive',ROOT/'output/current-manufacturing/feeder-reuse/review.py')
reuse=importlib.util.module_from_spec(spec);spec.loader.exec_module(reuse)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
inv=json.loads((OUT/'invocation.json').read_text())
source=ROOT/inv['input']['file'];assert sha(source)==inv['input']['sha256']
for n,h in inv['artifact_sha256'].items():assert sha(OUT/n)==h
objs,config,embedded_sha,units=reuse.archive_models(OUT/'slice-review.3mf')
assert len(objs)==1 and units=='millimeter' and embedded_sha==sha(OUT/'plate_1.gcode')
obj=next(iter(objs.values()));tri=obj['vertices'][obj['faces']]
identity=normalization_review(read_stl(source),obj['vertices'],obj['faces'])
assert identity['status']=='BOUNDED_VERTEX_CONTRACTION_VERIFIED'
assert identity['source_triangles']==identity['actual_3mf_triangles'] and not identity['collapsed_source_triangle_indices']
M=np.array(obj['mapping']['current_cad_to_gcode_command']);inverse=np.linalg.inv(M)
assert np.allclose(M[:3,1],[0,0,1],atol=1e-12)
bed_y=float(tri[:,:,1].min())
bed=unary_union([Polygon(t[:,[0,2]])for t in tri if np.max(np.abs(t[:,1]-bed_y))<1e-5])
patches=sorted(list(bed.geoms),key=lambda p:tuple(p.centroid.coords)[0]) if hasattr(bed,'geoms')else[bed]
assert len(patches)==4
roi=box(-34,-158,34,-126)
records=defaultdict(list);all_features=Counter()
for r in extrusion_paths((OUT/'plate_1.gcode').open()):
    all_features[r.feature]+=1
    if r.feature in IGNORED or r.layer>12.00001:continue
    q=affine(r.points,inverse)
    assert np.ptp(q[:,1])<1e-5
    line=LineString(q[:,[0,2]])
    if not line.buffer(r.width/2+.003).intersects(roi):continue
    records[round(r.layer,5)].append({'line_no':r.line,'feature':r.feature,'width':r.width,
        'height':r.height,'cad_y_top':float(q[0,1]),'line':line,'bead':bead(line,r.width),
        'support':r.feature.startswith('Support')})
layers=sorted(records)
model_layers=[z for z in layers if any(not r['support']for r in records[z])]
first=model_layers[0];assert abs(first-.2)<1e-6
footprints={z:unary_union([r['bead']for r in records[z]if not r['support']])for z in model_layers}
key_layers=[z for z in model_layers if z<=5.8+1e-6]
assert len(key_layers)==29 and np.allclose(key_layers,np.arange(1,30)*.2,atol=1e-8)
patch_report=[]
for i,p in enumerate(patches):
    witness=[r for r in records[first]if not r['support']and r['line'].intersection(p).length>.1]
    rows=[]
    for k,z in enumerate(key_layers):
        area=footprints[z].intersection(p).area
        previous=footprints[key_layers[k-1]].intersection(footprints[z]).intersection(p).area if k else None
        rows.append({'print_z':z,'cad_y_top':records[z][0]['cad_y_top'],'model_bead_area_in_key_mm2':area,
            'previous_layer_model_overlap_in_key_mm2':previous})
    assert witness and all(r['model_bead_area_in_key_mm2']>1 for r in rows)
    assert all(r['previous_layer_model_overlap_in_key_mm2']>1 for r in rows[1:])
    patch_report.append({'key_fragment':i+1,'bed_polygon_bounds_CAD_XZ':list(p.bounds),'bed_polygon_area_mm2':p.area,
        'first_layer_print_z':first,'first_layer_slab_print_z':[first-records[first][0]['height'],first],
        'first_layer_model_Gcode_witnesses':[{'line':r['line_no'],'feature':r['feature'],'width':r['width'],
            'centerline_length_in_fragment_mm':r['line'].intersection(p).length}for r in witness],
        'all_29_key_layers_present':True,'layer_observations':rows})

voids=[]
for x in [-10.5,10.5]:
    angles=np.arange(72)*2*math.pi/72
    voids.append((f'M2p5_x{x:g}',Polygon(np.column_stack([x+1.45*np.cos(angles),-142+1.45*np.sin(angles)])),[-53.8,-42]))
for x in [-20.5,20.5]:voids.append((f'strap_x{x:g}',box(x-1.5,-153,x+1.5,-131),[-48,-42]))
void_report=[]
for name,p,(lo,hi)in voids:
    rows=[]
    for z in layers:
        # Use the actual layer centre; endpoint float32 noise is not a new roof.
        mid=records[z][0]['cad_y_top']-records[z][0]['height']/2
        if not lo<mid<hi:continue
        model=[r for r in records[z]if not r['support']]
        support=[r for r in records[z]if r['support']]
        mf=unary_union([r['bead']for r in model]);sf=unary_union([r['bead']for r in support])
        crossing=[r for r in model if r['line'].intersection(p.buffer(-.05)).length>.005]
        nominal_crossing=[r for r in model if r['line'].intersection(p).length>.005]
        rows.append({'print_z':z,'cad_y_layer_mid':mid,
            'model_bead_intersection_with_exact_nominal_void_mm2':mf.intersection(p).area,
            'model_bead_intersection_with_0p05_inset_void_mm2':mf.intersection(p.buffer(-.05)).area,
            'support_bead_intersection_with_nominal_void_mm2':sf.intersection(p).area,
            'model_centerline_crossings_of_nominal_void':[{'line':r['line_no'],'feature':r['feature'],'length_mm':r['line'].intersection(p).length}for r in nominal_crossing],
            'model_centerline_crossings_of_0p05_inset_void':[{'line':r['line_no'],'feature':r['feature'],'length_mm':r['line'].intersection(p.buffer(-.05)).length}for r in crossing]})
    assert rows
    void_report.append({'name':name,'CAD_y_range': [lo,hi],'nominal_void_area_mm2':p.area,
        'shape':'actual 72-gon Ø2.9'if name.startswith('M2')else'3 by 22 rectangular through slot',
        'reviewed_layer_count':len(rows),'print_z_range':[rows[0]['print_z'],rows[-1]['print_z']],
        'max_nominal_void_model_bead_area_mm2':max(r['model_bead_intersection_with_exact_nominal_void_mm2']for r in rows),
        'max_inset_void_model_bead_area_mm2':max(r['model_bead_intersection_with_0p05_inset_void_mm2']for r in rows),
        'max_nominal_void_support_bead_area_mm2':max(r['support_bead_intersection_with_nominal_void_mm2']for r in rows),
        'nominal_centerline_crossing_count':sum(len(r['model_centerline_crossings_of_nominal_void'])for r in rows),
        'centerline_crossing_count':sum(len(r['model_centerline_crossings_of_0p05_inset_void'])for r in rows),
        'layer_observations':rows})

os.environ.setdefault('MPLCONFIGDIR',str(OUT/'matplotlib-config'))
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,axes=plt.subplots(1,3,figsize=(15,5),sharey=True)
for ax,z in zip(axes,[.2,5.8,6.0]):
    for r in records[z]:
        x,y=r['line'].xy;ax.plot(x,y,color='#999999'if r['support']else'#005aa0',lw=.6,alpha=.65)
    for p in patches:
        x,y=p.exterior.xy;ax.plot(x,y,color='#e08e00',lw=1)
    for name,p,_ in voids:
        x,y=p.exterior.xy;ax.plot(x,y,color='#bd2542',lw=.8,ls='--')
    ax.set(xlim=(-34,34),ylim=(-158,-126),aspect='equal',xlabel='CAD X / mm',title=f'Actual layer Z={z:.1f} mm')
axes[0].set_ylabel('CAD Z / mm');fig.suptitle('Actual G-code: blue=model, gray=support; orange=4 bed patches, red=through voids')
fig.tight_layout();fig.savefig(OUT/'key-bed-start-review.png',dpi=160);plt.close(fig)
watched=[source,OUT/'invocation.json',OUT/'slice-review.3mf',OUT/'plate_1.gcode',ROOT/'cad/inlet-retention-final.scad',
    ROOT/'analysis/cable_input_slice_review.py',ROOT/'analysis/cable_slice_artifacts.py',ROOT/'output/current-manufacturing/feeder-reuse/review.py',Path(__file__)]
report={'status':'ACTUAL_FOUR_KEY_FRAGMENTS_START_ON_BED; THROUGH_VOID_PATH_SCOPE_REVIEWED',
    'created_utc':datetime.now(timezone.utc).isoformat(),'source_and_artifact_sha256':{str(p.relative_to(ROOT)):sha(p)for p in watched},
    'mapping':obj['mapping'],'normal_mesh_identity':identity,'gcode_equals_archive':True,'units':units,
    'actual_min_CAD_Y':bed_y,'actual_bed_print_z_mm':float(affine(np.array([[0,bed_y,-142]]),M)[0,2]),
    'first_model_layer_print_z':first,'four_actual_mesh_bed_components':patch_report,'through_voids':void_report,
    'image':'key-bed-start-review.png','image_sha256':sha(OUT/'key-bed-start-review.png'),
    'method':['Recovered full component/build/source-offset/nozzle mapping from actual exported 3MF, not command flags alone.',
        'Bed polygons come from coplanar actual archived mesh triangles, not ideal SCAD rectangles.',
        'Parsed actual positive extrusion G0/G1/G2/G3 with layer/feature/width; Brim, custom purge and supports are not model witnesses.',
        'All 29 model layers over the 5.8 mm key stand-off checked for each fragment and positive previous-model overlap.',
        'Full bead footprints use emitted width/2 plus 0.002 mm numerical cover; arcs sampled to sagitta <=0.00125 mm.',
        'Both exact nominal void and 0.05 mm inset diagnostics are reported. Inset is not a print tolerance or acceptance waiver.'],
    'limits':['No new CAD export or slice. No printer action.',
        'Four-fragment first-layer and layer-overlap evidence does not prove bed adhesion, interlayer strength, or full width support for every later path.',
        'The anchor plate expansion at print Z6.0 is outside the claim that key fragments begin on bed; its underside needs separate support review.',
        'No full support-removal claim, no M4-pocket bearing-surface acceptance, no physical aperture fit or cleanup guarantee.'],
    'physical_acceptance':False,'manufacturing_release':False,'sent_to_printer':False}
(OUT/'key-bed-start-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'bed':bed_y,'mapping':M.tolist(),'bed_patches':[(r['bed_polygon_bounds_CAD_XZ'],r['first_layer_model_Gcode_witnesses'][0])for r in patch_report],
    'voids':[{k:v for k,v in r.items()if k!='layer_observations'}for r in void_report]},ensure_ascii=False,indent=2))

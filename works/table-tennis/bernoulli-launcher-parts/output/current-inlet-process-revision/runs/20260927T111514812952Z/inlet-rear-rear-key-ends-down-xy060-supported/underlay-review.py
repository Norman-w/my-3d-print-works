#!/usr/bin/env python3
"""Chronological, bounded review of EXISTING inlet slice paths. Never slices."""
from pathlib import Path
from collections import defaultdict
from datetime import datetime,timezone
import hashlib,importlib.util,json,math,os,sys
import numpy as np
from shapely.geometry import Polygon,LineString,Point
from shapely.ops import unary_union,substring
OUT=Path(__file__).resolve().parent
ROOT=next(p for p in OUT.parents if (p/'cad/inlet-retention-final.scad').is_file())
sys.path[:0]=[str(ROOT/'analysis'),str(ROOT/'scripts')]
import cable_input_slice_review as g
from cable_slice_artifacts import normalization_review
from review_cable_slice import read_stl
sp=importlib.util.spec_from_file_location('archive_reuse',ROOT/'output/current-manufacturing/feeder-reuse/review.py')
reuse=importlib.util.module_from_spec(sp);sp.loader.exec_module(reuse)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
inv=json.loads((OUT/'invocation.json').read_text());src=ROOT/inv['input']['file']
assert sha(src)==inv['input']['sha256']
for n,h in inv['artifact_sha256'].items():assert sha(OUT/n)==h
objects,project,arch_sha,units=reuse.archive_models(OUT/'slice-review.3mf');assert len(objects)==1
assert arch_sha==sha(OUT/'plate_1.gcode') and units=='millimeter'
o=next(iter(objects.values()));tri=o['vertices'][o['faces']]
identity=normalization_review(read_stl(src),o['vertices'],o['faces'])
assert identity['status']=='BOUNDED_VERTEX_CONTRACTION_VERIFIED' and not identity['collapsed_source_triangle_indices']
M=np.array(o['mapping']['current_cad_to_gcode_command']);I=np.linalg.inv(M)
assert np.allclose(M[:3,1],[0,0,1],atol=1e-12)
top_gap=float(project['support_top_z_distance']);assert top_gap==.2 and float(project['support_object_xy_distance'])==.6
NUM=.002
def polys(v):return list(v.geoms)if v.geom_type=='MultiPolygon'else[v]
def lines(v):
    if v.is_empty:return[]
    if v.geom_type in ['LineString','LinearRing']:return[v]
    return [p for c in getattr(v,'geoms',[])for p in lines(c)]
def lower_faces(y):
    return unary_union([Polygon(t[:,[0,2]])for t in tri if max(abs(t[:,1]-y))<1e-5 and np.cross(t[1]-t[0],t[2]-t[0])[1]<-1e-8])
bed_y=tri[:,:,1].min();patches=polys(lower_faces(bed_y));assert len(patches)==4
anchor=lower_faces(-48);shoulders=sorted(polys(lower_faces(-8.4)),key=lambda p:p.centroid.x)
assert not anchor.is_empty and len(shoulders)==2
rois=[('anchor-expansion',anchor,-48,6.0)]+[(f'M4-shoulder-{i+1}',p,-8.4,45.6)for i,p in enumerate(shoulders)]
keep_layers={.2,5.4,5.6,5.8,6.0,45.0,45.2,45.4,45.6}
records=defaultdict(list)
SKIP=g.IGNORED|{'Flush','Undefined',''}
for r in g.extrusion_paths((OUT/'plate_1.gcode').open()):
    if r.feature in SKIP or round(r.layer,5)not in keep_layers:continue
    q=g.affine(r.points,I);line=LineString(q[:,[0,2]])
    assert np.ptp(q[:,1])<1e-5
    outer=line.buffer((r.width/2+NUM)/math.cos(math.pi/128),quad_segs=32)
    inner=line.buffer(max(0,r.width/2-NUM),quad_segs=32)
    records[round(r.layer,5)].append(dict(line=r.line,stroke=r.stroke,feature=r.feature,width=r.width,height=r.height,
        top=float(r.points[:,2].max()),bottom=float(r.points[:,2].min()-r.height),path=line,outer=outer,inner=inner,
        support=r.feature.startswith('Support')))

key=[]
for p in sorted(patches,key=lambda p:(p.centroid.x,p.centroid.y)):
    w=[r for r in records[.2]if not r['support']and r['path'].intersection(p).length>.1]
    assert w
    key.append({'bed_patch_bounds_CAD_XZ':list(p.bounds),'bed_patch_area_mm2':p.area,
        'first_model_print_z':.2,'model_witnesses':[{'line':r['line'],'feature':r['feature'],'width':r['width']}for r in w],
        'first_layer_model_bead_area_in_patch_mm2':unary_union([r['outer']for r in w]).intersection(p).area})

reports=[];plot_data=[]
for name,roi,y,target in rois:
    current=records[target];assert current
    first_line=min(r['line']for r in current)
    bottom=target-next(r['height']for r in current if not r['support'])
    prior_model=[r for z,rr in records.items()for r in rr if z<target and not r['support']and r['line']<first_line and abs(r['top']-bottom)<1e-5]
    prior_support=[r for z,rr in records.items()for r in rr if z<target and r['support']and r['line']<first_line and -1e-5<=bottom-r['top']<=top_gap+1e-5]
    modout=unary_union([r['outer']for r in prior_model]);modin=unary_union([r['inner']for r in prior_model])
    supout=unary_union([r['outer']for r in prior_support]);supin=unary_union([r['inner']for r in prior_support])
    backing_outer=unary_union([modout,supout]);backing_inner=unary_union([modin,supin])
    earlier=Polygon();rows=[];first_actual=None;unbacked_plot=[]
    for r in current:
        if r['support']:continue
        clip=r['path'].intersection(roi)
        if clip.length>.005:
            if first_actual is None:first_actual=(r,earlier)
            gaps=[]
            # Full emitted command analysed before clipping to the ROI. Thus an
            # ROI cut cannot manufacture an anchor at its artificial endpoint.
            for gap in lines(r['path'].difference(backing_outer)):
                if gap.intersection(roi).length<=.005:continue
                ends=[Point(gap.coords[0]),Point(gap.coords[-1])]
                distances=sorted([r['path'].project(p)for p in ends])
                before=substring(r['path'],max(0,distances[0]-2),distances[0])
                after=substring(r['path'],distances[1],min(r['path'].length,distances[1]+2))
                contacts=[before.intersection(backing_inner).length,after.intersection(backing_inner).length]
                lateral=[Point(p).buffer(max(0,r['width']/2-NUM),quad_segs=32).intersection(earlier).area for p in [gap.coords[0],gap.coords[-1]]]
                chord=float(np.linalg.norm(np.array(gap.coords[-1])-np.array(gap.coords[0])))
                gaps.append({'path_length_mm':gap.length,'endpoint_chord_mm':chord,'bounds_CAD_XZ':list(gap.bounds),
                    'earlier_vertical_backing_contact_length_before_after_mm':contacts,
                    'both_ends_have_preexisting_vertical_backing_along_same_command':all(v>.005 for v in contacts),
                    'previous_same_layer_lateral_endpoint_overlap_mm2':lateral,
                    'has_only_lateral_or_unestablished_anchor':not all(v>.005 for v in contacts),
                    'note':'Path length around an arc is not a free straight bridge span. Lateral contact is not a load-capacity proof.'})
                unbacked_plot.append(gap.intersection(roi))
            rows.append({'gcode_line':r['line'],'stroke':r['stroke'],'feature':r['feature'],'width_mm':r['width'],
                'complete_command_length_mm':r['path'].length,'path_length_in_new_downface_mm':clip.length,
                'centerline_length_in_existing_model_underlay_mm':clip.intersection(modin).length,
                'centerline_length_over_existing_support_with_configured_top_gap_mm':clip.intersection(supin).length,
                'current_full_bead_prior_model_overlap_lower_mm2':r['inner'].intersection(modin).intersection(roi).area,
                'current_full_bead_prior_model_overlap_upper_mm2':r['outer'].intersection(modout).intersection(roi).area,
                'current_full_bead_prior_support_overlap_lower_mm2':r['inner'].intersection(supin).intersection(roi).area,
                'current_full_bead_prior_support_overlap_upper_mm2':r['outer'].intersection(supout).intersection(roi).area,
                'start_end_bead_disk_existing_vertical_backing_overlap_lower_mm2':[Point(p).buffer(max(0,r['width']/2-NUM),quad_segs=32).intersection(backing_inner).area for p in [r['path'].coords[0],r['path'].coords[-1]]],
                'start_end_bead_disk_existing_vertical_backing_overlap_upper_mm2':[Point(p).buffer((r['width']/2+NUM)/math.cos(math.pi/128),quad_segs=32).intersection(backing_outer).area for p in [r['path'].coords[0],r['path'].coords[-1]]],
                'model_bead_overlap_with_earlier_same_layer_model_in_ROI_mm2':r['inner'].intersection(earlier).intersection(roi).area,
                'definitely_no_vertical_backing_centerline_length_mm':clip.difference(backing_outer).length,
                'current_start_has_vertical_backing':backing_inner.covers(Point(r['path'].coords[0])),
                'current_end_has_vertical_backing':backing_inner.covers(Point(r['path'].coords[-1])),
                'current_start_prior_lateral_overlap_mm2':Point(r['path'].coords[0]).buffer(max(0,r['width']/2-NUM),quad_segs=32).intersection(earlier).area,
                'unbacked_centerline_fragments':gaps})
        # This update happens only AFTER classifying this command. Later
        # commands can never support an earlier command in the report.
        earlier=unary_union([earlier,r['inner']])
    assert rows
    gaps=[v for r in rows for v in r['unbacked_centerline_fragments']]
    reports.append({'name':name,'actual_mesh_downface_CAD_Y':y,'actual_new_downface_area_mm2':roi.area,
        'actual_new_downface_bounds_CAD_XZ':list(roi.bounds),'first_layer_print_z':target,'layer_bottom':bottom,
        'prior_model_layers':sorted(set(r['top']for r in prior_model)),
        'prior_support_layer_tops_and_actual_gaps':[{'top':z,'gap_to_model_bottom':bottom-z}for z in sorted(set(r['top']for r in prior_support))],
        'underlay_lower_bound_area_on_new_downface_mm2':roi.intersection(backing_inner).area,
        'underlay_outer_bound_area_on_new_downface_mm2':roi.intersection(backing_outer).area,
        'first_relevant_command':rows[0], 'model_command_count_touching_new_downface':len(rows),
        'unbacked_fragment_count':len(gaps),
        'max_unbacked_path_length_mm':max((q['path_length_mm']for q in gaps),default=0),
        'max_unbacked_endpoint_chord_mm':max((q['endpoint_chord_mm']for q in gaps),default=0),
        'two_preexisting_vertical_end_contacts_fragment_count':sum(q['both_ends_have_preexisting_vertical_backing_along_same_command']for q in gaps),
        'commands':rows})
    plot_data.append((name,roi,modout,supout,first_actual,unbacked_plot,rows))

os.environ.setdefault('MPLCONFIGDIR',str(OUT/'underlay-matplotlib-config'))
import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
fig,axs=plt.subplots(2,3,figsize=(15,9))
def fill(ax,poly,color,alpha):
    from matplotlib.path import Path as MplPath
    from matplotlib.patches import PathPatch
    from shapely.geometry.polygon import orient
    for p in polys(poly):
        if p.geom_type=='Polygon'and not p.is_empty:
            p=orient(p,sign=1)
            vertices=[];codes=[]
            for ring in [p.exterior,*p.interiors]:
                points=list(ring.coords)
                vertices.extend(points)
                codes.extend([MplPath.MOVETO]+[MplPath.LINETO]*(len(points)-2)+[MplPath.CLOSEPOLY])
            ax.add_patch(PathPatch(MplPath(vertices,codes),facecolor=color,edgecolor='none',alpha=alpha))
for col,(name,roi,mo,so,first,gaps,rows)in enumerate(plot_data):
    for row in [0,1]:
        ax=axs[row,col];fill(ax,so,'#e0b06a',.65);fill(ax,mo,'#4291ad',.65)
        for p in polys(roi):
            ax.plot(*p.exterior.xy,color='#252525',lw=.7)
            for ring in p.interiors:ax.plot(*ring.xy,color='#252525',lw=.7)
        a,b,c,d=roi.bounds;pad=1.5;ax.set(xlim=(a-pad,c+pad),ylim=(b-pad,d+pad),aspect='equal',xlabel='CAD X / mm',ylabel='CAD Z / mm')
        ax.set_title(name+(' / first command'if row==0 else' / all unbacked centerline runs'))
    r,prior=first;fill(axs[0,col],prior,'#9c64b5',.4);axs[0,col].plot(*r['path'].xy,color='#d2222d',lw=1.6)
    axs[0,col].scatter(*r['path'].coords[0],s=24,color='#111111',zorder=5)
    for q in gaps:
        for line in lines(q):axs[1,col].plot(*line.xy,color='#d2222d',lw=.65)
fig.suptitle('Actual emitted order: tan=earlier support (.2 gap), blue=prior layer model; purple=earlier same-layer, red=current/unbacked')
fig.tight_layout();fig.savefig(OUT/'underlay-review.png',dpi=150);plt.close(fig)
watched=[src,OUT/'invocation.json',OUT/'slice-review.3mf',OUT/'plate_1.gcode',OUT/'process.json',ROOT/'cad/inlet-retention-final.scad',Path(__file__),ROOT/'analysis/cable_input_slice_review.py',ROOT/'analysis/cable_slice_artifacts.py',ROOT/'output/current-manufacturing/feeder-reuse/review.py']
report={'status':'CHRONOLOGICAL_NOMINAL_UNDERLAY_REVIEW_NOT_PRINT_ACCEPTANCE','created_utc':datetime.now(timezone.utc).isoformat(),
    'source_and_artifact_sha256':{str(p.relative_to(ROOT)):sha(p)for p in watched},'normal_mesh_identity':identity,'mapping':o['mapping'],
    'actual_support_top_gap':top_gap,'actual_support_object_xy_distance':float(project['support_object_xy_distance']),
    'four_keys_actual_first_layer':key,'surfaces':reports,'image':'underlay-review.png','image_sha256':sha(OUT/'underlay-review.png'),
    'method':['Actual 3MF lower-facing coplanar triangles define newly exposed undersides; no ideal source-box proxy.',
        'Only earlier G-code lines count as previous material; same-layer extrusion updated after evaluating each command.',
        'Previous-layer model must reach the underside. Support may be up to configured .2 mm below; this deliberate gap is reported, not erased.',
        'Backing inner/outer bounds use emitted bead half-width minus/plus .002 mm for chord/numeric representation. Outer radius is circumscribed with 128 sides.',
        'Centerline runs outside outer backing are definitely unbacked in this nominal footprint model. The ambiguous band is not claimed supported.',
        'For each missing-backing run, look at up to 2 mm of the same command on either side for already present vertical backing. Store actual contact length; .005 is numerical line-filter scale, not sufficient physical anchor length.',
        'Same-layer lateral contacts are recorded separately and never reclassified as previous-layer support. They may themselves be mechanically unestablished.',
        'A centerline outside backing can still have partial bead-width bearing. Full-bead and endpoint-disk overlaps are separately reported; zero centerline support is NOT labelled a wholly unsupported extrusion.',
        'Curved contour length is kept separate from endpoint chord; neither raw command length nor unbacked arc length is called proven straight bridge span.'],
    'limits':['No mechanical bridge strength, anchorage length, bed adhesion, PETG interface bonding or bearing strength proved.',
        'Same-layer early weak paths can influence later paths; this report does not treat lateral contact as proof of load capacity.',
        'Whole support extraction and other functional-void checks belong to separate reports. No new CAD, slicing or printer action.'],
    'manufacturing_release':False,'physical_acceptance':False,'sent_to_printer':False}
(OUT/'underlay-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'keys':len(key),'surfaces':[{k:v for k,v in r.items()if k!='commands'}for r in reports]},ensure_ascii=False,indent=2))

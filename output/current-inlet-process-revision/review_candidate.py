#!/usr/bin/env python3
"""Read exact native candidate: modifiers, four voids and local deposition.
Reports geometric underlay gaps, not PETG sag or successful bridge tests.
"""
from pathlib import Path
import collections, hashlib, importlib.util, json, math, os, re, sys
import numpy as np
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

ROOT=Path(__file__).resolve().parents[2]; OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'analysis'),str(ROOT/'scripts')]
import cable_input_slice_review as paths
import review_cable_slice as stl
spec=importlib.util.spec_from_file_location('binding',ROOT/'output/current-manufacturing/input-process/bind_current_input_process.py')
binding=importlib.util.module_from_spec(spec);spec.loader.exec_module(binding)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
dump=lambda p,d:Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
SKIP={'Custom','Flush','Prime tower','Prime tower infill','Undefined','','Brim','Skirt'}


def void_projection(kind,x,bottom,top):
    if kind=='bore':
        if top<=-143.45 or bottom>=-140.55:return Polygon()
        z=min(max(-142,bottom),top)
        dx=math.sqrt(max(0,1.45**2-(z+142)**2))
        return box(x-dx,-48,x+dx,-42)
    if top<=-153 or bottom>=-131:return Polygon()
    return box(x-1.5,-48,x+1.5,-42)


def main():
    folder=ROOT/json.loads((OUT/'latest.json').read_text())['folder']
    inv=json.loads((folder/'invocation.json').read_text());code=folder/'plate_1.gcode'
    assert inv['return_code']==0 and inv['native_result']['return_code']==0
    assert not inv['native_result']['sliced_plates'][0]['warning_message']
    assert all(sha(ROOT/p)==h for p,h in inv['source_sha256_at_start'].items())
    assert all(sha(folder/n)==h for n,h in inv['artifact_sha256'].items())
    archive=binding.read3mf(folder/'slice-review.3mf')
    assert archive['archived_gcode_sha']==sha(code)
    normals=[p for p in archive['parts'] if p['subtype']=='normal_part']
    blockers=[p for p in archive['parts'] if p['subtype']=='support_blocker']
    assert len(normals)==1 and len(blockers)==4 and len(archive['parts'])==5
    n=normals[0];offset=np.array([float(n['meta']['source_offset_'+a]) for a in 'xyz'])
    tri=stl.read_stl(ROOT/inv['inputs'][0]['file'])
    proof=binding.normalization(tri,n['vertices']+offset,n['triangles'])
    raw=re.search(r'^; extruder_offset = ([^\n]+)',code.read_text(),re.M).group(1).split(',')
    assert len(raw)==1;nozzle=np.array([*map(float,raw[0].split('x')),0.])
    E=np.eye(4);E[:3,3]=-nozzle;U=np.eye(4);U[:3,3]=-offset
    M=E@archive['build']@n['component']@U; inverse=np.linalg.inv(M)
    assert np.allclose(M[:3,:3],np.eye(3))
    blocker_checks=[]
    for b in blockers:
        expected=next(s for s in inv['blockers'] if s['name']==b['name'])
        actual=paths.bounds(paths.affine(paths.affine(b['world_vertices'],E),inverse))
        err=float(np.abs(np.array(actual)-expected['bounds']).max());assert err<.0001
        blocker_checks.append(dict(name=b['name'],cad_bounds=actual,maximum_bound_error_mm=err))
    project=archive['project'];assert project['layer_height']=='0.1' and project['initial_layer_print_height']=='0.1'
    assert project['support_type']=='tree(auto)' and project['enable_support']=='1'
    regions=[dict(id=kind+str(x),kind=kind,x=x,hits=[]) for kind,xs in [('bore',[-10.5,10.5]),('slot',[-20.5,20.5])] for x in xs]
    all_records=collections.defaultdict(list);counts=collections.Counter();key_support=[]
    for r in paths.extrusion_paths(code.open()):
        if r.feature in SKIP:continue
        p=paths.affine(r.points,inverse);bottom=float(p[:,2].min()-r.height);top=float(p[:,2].max())
        line=LineString(p[:,:2]);rad=(r.width/2+paths.ARC_ERROR+paths.BUFFER_ERROR)/math.cos(math.pi/128)
        bead=line.buffer(rad,quad_segs=32);counts[r.feature]+=1
        if r.feature.startswith('Support'):
            for region in regions:
                hit=bead.intersection(void_projection(region['kind'],region['x'],bottom,top))
                if not hit.is_empty:region['hits'].append(dict(line=r.line,feature=r.feature,z=[bottom,top],overlap_area_mm2=hit.area))
            if top>-144 and bottom<-140:
                for x in [-10.5,10.5]:
                    hit=bead.intersection(box(x-1.3,-53.8,x+1.3,-48.4))
                    if not hit.is_empty:key_support.append(dict(x=x,line=r.line,z=[bottom,top],area_mm2=hit.area))
        # Only inspect local closure bands, keeping their complete prior model layer.
        if (-142.1<=top<=-139.9) or (-131.2<=top<=-130.0):
            all_records[round(top,6)].append(dict(line=r.line,feature=r.feature,width=r.width,p=p,line2d=line,bead=bead,
                model=not r.feature.startswith('Support'),bottom=bottom,top=top,stroke=r.stroke))
    zvalues=sorted(all_records);model={z:unary_union([r['bead'] for r in all_records[z] if r['model']]) for z in zvalues}
    gaps=[];bridges=[]
    for z in zvalues:
        prev=model.get(round(z-.1,6),Polygon())
        if prev.is_empty:continue
        for r in all_records[z]:
            if not r['model']:continue
            hit_regions=[]
            for region in regions:
                # Local wall/bridge closure volume, including rear-key portion for bore.
                x=region['x']; yc=(-54,-41.5) if region['kind']=='bore' else (-48.5,-41.5)
                zc=(-141.6,-140.2) if region['kind']=='bore' else (-131.05,-130.65)
                if zc[0]<z<zc[1] and r['line2d'].intersects(box(x-1.7,yc[0],x+1.7,yc[1])):hit_regions.append(region['id'])
            if not hit_regions:continue
            row=dict(line=r['line'],feature=r['feature'],cad_top_z=z,regions=hit_regions,cad_endpoints=r['p'][[0,-1]].tolist(),path_length_mm=r['line2d'].length)
            if r['feature']=='Bridge':bridges.append(row)
            for gap in paths.underlay_runs(r['line2d'],prev):
                gaps.append({**row,**{k:v for k,v in gap.items() if k!='geometry'},'interpretation':'Centerline lacks prior-layer conservative bead footprint; endpoints touching do not prove real adhesion.'})
    os.environ['MPLCONFIGDIR']=str(OUT/'matplotlib-config')
    import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    selected=[]
    for kind in ['bore','slot']:
        candidates=[r for r in bridges if any(s.startswith(kind) for s in r['regions'])]
        selected.append(min((r['cad_top_z'] for r in candidates),default=(-140.5 if kind=='bore' else -130.9)))
    fig,axs=plt.subplots(1,2,figsize=(12,6),layout='constrained')
    for ax,kind,z in zip(axs,['bore','slot'],selected):
        x=-10.5 if kind=='bore' else -20.5
        prev=model.get(round(z-.1,6),Polygon())
        ps=[prev] if prev.geom_type=='Polygon' else list(prev.geoms) if hasattr(prev,'geoms') else []
        for p in ps:
            if p.geom_type=='Polygon':
                ax.fill(*p.exterior.xy,color='#d7e3ea')
                for ring in p.interiors:ax.fill(*ring.xy,color='white')
        for r in all_records.get(round(z,6),[]):
            color='#ec8b2c' if not r['model'] else '#ca2844' if r['feature']=='Bridge' else '#326f96'
            ax.plot(r['p'][:,0],r['p'][:,1],color=color,lw=.65)
        ax.axhline(-48.4,color='#555555',ls='--',lw=.8);ax.set_xlim(x-5,x+5);ax.set_ylim(-56,-39)
        ax.set_aspect('equal');ax.set_title(f'{kind}: CAD Z={z:g} mm');ax.set_xlabel('CAD X/mm');ax.set_ylabel('CAD Y/mm')
    fig.suptitle('Native deposition: prior model gray; current model blue; bridge red; support orange')
    fig.savefig(folder/'critical-paths.png',dpi=170);plt.close(fig)
    summary=dict(status='REGIONAL_PROCESS_CANDIDATE_REVIEWED_NOT_ADOPTED',source_stl_sha256=sha(ROOT/inv['inputs'][0]['file']),
        native_mesh_correspondence=proof,blockers=blocker_checks,source_to_command=M.tolist(),native_layer_height_mm=.1,
        regions=[dict(id=r['id'],support_record_hits=len(r['hits']),hits=r['hits']) for r in regions],
        all_four_voids_free_of_support=all(not r['hits'] for r in regions),rear_key_support_records=key_support,
        bridge_records=bridges,prior_layer_centerline_gaps=gaps,path_counts=dict(counts),
        artifacts={p:sha(folder/p) for p in ['slice-review.3mf','plate_1.gcode','invocation.json','critical-paths.png']},
        script_sha256=sha(__file__),source_hashes=inv['source_sha256_at_start'],
        limits=['A geometric prior-layer gap is not measured bridge sag, unsupported strength or adhesion.',
                'Rear-key and M4 support removal, whole-part process review and actual finish remain to be checked.',
                'Generic PETG and Textured PEI remain profile assumptions; no print or new process adoption.'],
        manufacturing_release=False,physical_acceptance=False)
    dump(folder/'regional-review.json',summary)
    print(json.dumps(dict(status=summary['status'],void_hits={r['id']:len(r['hits']) for r in regions},key_support_records=len(key_support),bridge_records=len(bridges),gap_records=len(gaps)),ensure_ascii=False),flush=True)


if __name__=='__main__':main()

#!/usr/bin/env python3
"""Conditional remaining-tree sweep for the new native regional candidate.
Four boxes are removals that still need an operation, not invented loose pieces.
"""
from pathlib import Path
import collections, hashlib, importlib.util, json, math, sys, time
import numpy as np
from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('sweep',ROOT/'output/current-manufacturing/inlet-support-closure/sweep_review.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
REGIONS=[]
for sign in [-1,1]:
    REGIONS.append(dict(id='M4_'+str(sign),lo=[sign*43-8,-25,-118.1],hi=[sign*43+8,0,-107]))
    REGIONS.append(dict(id='rear_key_'+str(sign),lo=[sign*10.5-3,-61,-146.1],hi=[sign*10.5+3,-48,-140]))


def main():
    started=time.time();f=ROOT/json.loads((OUT/'latest.json').read_text())['folder']
    review=json.loads((f/'regional-review.json').read_text());inv=json.loads((f/'invocation.json').read_text())
    assert review['all_four_voids_free_of_support']
    assert all(a.sha(f/p)==h for p,h in review['artifacts'].items())
    M=np.array(review['source_to_command']);assert np.allclose(M[:3,:3],np.eye(3))
    tri=a.g.affine(a.read_stl(ROOT/inv['inputs'][0]['file']).reshape(-1,3),M).reshape(-1,3,3)
    groups=collections.defaultdict(lambda:collections.defaultdict(list));meta=collections.defaultdict(lambda:collections.defaultdict(list))
    for r in a.g.extrusion_paths((f/'plate_1.gcode').open()):
        kind='support' if r.feature.startswith('Support') else 'model' if r.feature not in a.SKIP|{'Brim','Skirt'} else None
        if kind is None:continue
        radius=(r.width/2+.002)/math.cos(math.pi/128)
        p=LineString(r.points[:,:2]).buffer(radius,quad_segs=32);z=round(r.layer,6)
        groups[z][kind].append(p);meta[z][kind].append((float(r.points[:,2].min()-r.height),float(r.points[:,2].max()),r.line))
    for z in groups:
        for kind in groups[z]:groups[z][kind]=unary_union(groups[z][kind])
    model=[(min(v[0] for v in meta[z]['model']),groups[z]['model']) for z in sorted(groups) if 'model' in groups[z]]
    accumulated=Polygon();j=0;rows=[];removed_stats=collections.Counter()
    print('candidate grouped',len(groups),'layers',flush=True)
    for z in sorted(groups):
        if 'support' not in groups[z]:continue
        low=min(v[0] for v in meta[z]['support']);high=max(v[1] for v in meta[z]['support'])
        while j<len(model) and model[j][0]<=high+1e-10:
            accumulated=unary_union([accumulated,model[j][1]]);j+=1
        planes=[v+M[2,3] for region in REGIONS for v in [region['lo'][2],region['hi'][2]] if low<v+M[2,3]<high]
        cuts=sorted(set([low,high]+planes))
        for bottom,top in zip(cuts,cuts[1:]):
            remaining=groups[z]['support'];mid=(bottom+top)/2-M[2,3]
            for region in REGIONS:
                if region['lo'][2]<=mid<=region['hi'][2]:
                    lo,hi=np.array(region['lo'])+M[:3,3],np.array(region['hi'])+M[:3,3]
                    region2d=box(lo[0],lo[1],hi[0],hi[1]);part=remaining.intersection(region2d)
                    if not part.is_empty:removed_stats[region['id']]+=1
                    remaining=remaining.difference(region2d)
            if remaining.is_empty:continue
            mesh_hit=remaining.intersection(a.surfaces_below(tri,top));model_hit=remaining.intersection(accumulated)
            rows.append(dict(bottom=bottom,top=top,clear_stl=mesh_hit.is_empty,clear_model=model_hit.is_empty,
                stl_overlap_area_mm2=mesh_hit.area,model_overlap_area_mm2=model_hit.area,
                hit_bounds=list(unary_union([mesh_hit,model_hit]).bounds) if not mesh_hit.is_empty or not model_hit.is_empty else None))
    failed=[r for r in rows if not r['clear_stl'] or not r['clear_model']]
    report=dict(status='CONDITIONAL_REMAINING_TREE_SWEEP_CLEAR' if not failed else 'CONDITIONAL_REMAINING_TREE_HAS_HITS',
        removal_regions=REGIONS,region_slabs_with_support=dict(removed_stats),remaining_slabs=len(rows),blocked_slabs=failed,rows=rows,
        all_remaining_clear_actual_model=all(r['clear_model'] for r in rows),all_remaining_clear_exact_stl=all(r['clear_stl'] for r in rows),
        artifact_sha256={n:a.sha(f/n) for n in ['slice-review.3mf','plate_1.gcode','invocation.json','regional-review.json']},
        source_stl_sha256=inv['inputs'][0]['sha256'],script_sha256=a.sha(__file__),sweep_helper_sha256=a.sha(Path(a.__file__)),
        elapsed_s=time.time()-started,scope='Every true-height support slab after four bounded regions have already been removed; continuous -CAD Z sweep against exact current STL and all lower actual model beads. Does not prove those regions are naturally separate, cuttable or graspable, or that they can exit -Y.',
        physical_acceptance=False,manufacturing_release=False)
    a.dump(f/'exit-review.json',report)
    print(json.dumps({k:report[k] for k in ['status','remaining_slabs','all_remaining_clear_actual_model','all_remaining_clear_exact_stl','elapsed_s']},ensure_ascii=False),flush=True)
    print('blocked_slabs',len(failed),flush=True)


if __name__=='__main__':main()

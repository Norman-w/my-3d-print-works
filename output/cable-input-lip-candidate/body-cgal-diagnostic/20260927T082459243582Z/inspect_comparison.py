#!/usr/bin/env python3
"""Read-only backend comparison; never repairs or changes a mesh."""
from pathlib import Path
import collections, hashlib, importlib.util, json, math, sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / 'analysis'))
from exact_mesh import exact_area_and_links
from feeder_integration import classify
INSPECTOR = Path('/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py')
spec = importlib.util.spec_from_file_location('stl_inspector', INSPECTOR)
inspect_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inspect_module)

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def local(p):
    x,y,z=p
    return [(75-x+z-5)/math.sqrt(2),(x-75+z-5)/math.sqrt(2),y+82]
def tri_detail(tris,i):
    tri=tris[i]
    a,b,c=tri
    u=[b[k]-a[k] for k in range(3)];v=[c[k]-a[k] for k in range(3)]
    n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
    ln=math.sqrt(sum(x*x for x in n))
    return {'triangle_index':i,'cad_vertices':tri,'local_vertices':[local(p) for p in tri],
            'unit_normal_cad':[x/ln for x in n] if ln else None,'area_mm2':ln/2}
def edges(tris,tol):
    key=(lambda p:tuple(p)) if tol is None else (lambda p:inspect_module._key(p,tol))
    owners={};points={}
    for i,tri in enumerate(tris):
        keys=[key(p) for p in tri]
        for k,p in zip(keys,tri): points.setdefault(k,p)
        for a,b in ((keys[0],keys[1]),(keys[1],keys[2]),(keys[2],keys[0])):
            edge=tuple(sorted((a,b)));owners.setdefault(edge,[]).append((i,1 if (a,b)==edge else -1))
    bad=[]
    for (a,b),items in owners.items():
        if len(items)!=2 or sum(s for _,s in items)!=0:
            bad.append({'cad_endpoints':[points[a],points[b]],'local_endpoints':[local(points[a]),local(points[b])],
                        'face_count':len(items),'orientation_sum':sum(s for _,s in items),
                        'adjacent_triangles':[tri_detail(tris,i) for i,_ in items]})
    return {'coordinate_weld_tolerance_mm':tol,'edge_incidence_histogram':dict(sorted(collections.Counter(len(x) for x in owners.values()).items())),
            'bad_edges':bad}

inv=json.loads((HERE/'invocation.json').read_text())
rows={}
for name,path in [('Manifold',Path(inv['reference'])),('CGAL',HERE/'body-cgal.stl')]:
    fmt,tris=inspect_module._read_triangles(path)
    ex=exact_area_and_links(path)
    inspection=inspect_module.inspect(path,1e-6)
    component_report=classify(path)
    rows[name]={'path':str(path),'sha256':sha(path),'inspection':inspection,'exact_area_and_vertex_links':ex,
                'vertex_connected_components':component_report['components'],
                'edge_incidence_exact_float':edges(tris,None),'edge_incidence_welded_1e_6':edges(tris,1e-6)}
    rows[name]['strict_mesh_checks_pass']=bool(inspection['watertightByEdgeTopology'] and not ex['exact_zero_area_face_indices'] and not ex['non_ring_vertex_links'] and len(component_report['components'])==1)
m=rows['Manifold']['inspection'];c=rows['CGAL']['inspection']
bad=rows['Manifold']['edge_incidence_exact_float']['bad_edges']
shared_bad_owners=set.intersection(*[{t['triangle_index'] for t in e['adjacent_triangles']} for e in bad]) if bad else set()
slivers={t['triangle_index']:t for e in bad for t in e['adjacent_triangles'] if t['triangle_index'] in shared_bad_owners}
report={'scope':'Same immutable cil_body() call and same source; backend export diagnosis only. No mesh repair, geometry change, slicing, or whole-assembly rerun.',
        'invocation':inv,'source_sha256_at_inspection':sha(Path(inv['source'])),
        'parameters_sha256_at_inspection':sha(ROOT/'cad/parameters.scad'),
        'source_unchanged':sha(Path(inv['source']))==inv['source_sha256_before'],
        'parameters_unchanged':sha(ROOT/'cad/parameters.scad')==inv['include_parameters_sha256_before'],
        'reference_unchanged':sha(Path(inv['reference']))==inv['reference_sha256_before'],
        'helpers':{str(p):sha(p) for p in [Path(__file__),INSPECTOR,ROOT/'analysis/exact_mesh.py',ROOT/'analysis/feeder_integration.py']},
        'meshes':rows,'conclusion':{
            'CGAL_mesh_acceptable_for_next_validation_layer':rows['CGAL']['strict_mesh_checks_pass'],
            'source_geometry_repair_required_by_this_check':False if rows['CGAL']['strict_mesh_checks_pass'] else None,
            'Manifold_bad_edges_shared_face_indices':sorted(shared_bad_owners),
            'Manifold_shared_faces':list(slivers.values()),
            'interpretation':'The two Manifold faults share a reversed pair of coincident three-vertex triangles (1224 and 2801), each numerically near-collinear in local x=-45,z=-4. Their exported decimal areas are not exactly zero, so exact-zero-area alone does not catch them. Raw edge incidence and welded vertex links reject them. The unchanged source produces one closed manifold via CGAL, supporting a backend/export triangulation remnant diagnosis rather than a required mechanical epsilon change. This is not proof of every face set being equal or of physical manufacturability.'},
        'comparison':{
            'CGAL_minus_Manifold_volume_mm3':c['volume']-m['volume'],
            'relative_volume_delta':(c['volume']-m['volume'])/m['volume'],
            'CGAL_minus_Manifold_surface_area_mm2':c['surfaceArea']-m['surfaceArea'],
            'bounds_min_delta':[c['bounds']['min'][i]-m['bounds']['min'][i] for i in range(3)],
            'bounds_max_delta':[c['bounds']['max'][i]-m['bounds']['max'][i] for i in range(3)]},
        'limitations':['Mesh topology and bounding-box/volume agreement do not prove tolerance, structural strength, cable friction, assembly, or physical service life.','Exact areas use Fraction over exported ASCII numeric tokens. Vertex-link and standard edge checks weld at 1e-6 mm; raw exact-coordinate edge incidence is reported separately.']}
(HERE/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'source_unchanged':report['source_unchanged'],'parameters_unchanged':report['parameters_unchanged'],
 'reference_unchanged':report['reference_unchanged'],'comparison':report['comparison'],
 'meshes':{k:{'strict_pass':v['strict_mesh_checks_pass'],'triangle_count':v['inspection']['triangleCount'],
 'nonmanifold_edges':v['inspection']['nonManifoldEdgeCount'],'zero_area':len(v['exact_area_and_vertex_links']['exact_zero_area_face_indices']),
 'bad_vertex_links':len(v['exact_area_and_vertex_links']['non_ring_vertex_links']),'components':len(v['vertex_connected_components']),
 'bad_edge_exact_count':len(v['edge_incidence_exact_float']['bad_edges'])} for k,v in rows.items()}},indent=2))

"""Generate a conforming volume mesh from the validated body, not a visual field."""
from pathlib import Path
import struct,json,hashlib,os
import numpy as np
import tetgen
import manifold3d as m
HERE=Path(__file__).resolve().parent
OUT=Path(os.environ.get('CASE_DIR',HERE)).resolve();OUT.mkdir(parents=True,exist_ok=True)
SOURCE=Path(os.environ.get('SOURCE_STL',HERE.parent.parent/'exports/perpendicular-u-joint-v1.16-root-radius/guard-v1.16-body.stl')).resolve()
os.chdir(OUT) # Keep TetGen diagnostic files inside this analysis case.
data=SOURCE.read_bytes();n=struct.unpack_from('<I',data,80)[0]
points=[];faces=[];ids={}
for i in range(n):
    values=struct.unpack_from('<12f',data,84+50*i)[3:];face=[]
    for j in (0,3,6):
        p=tuple(values[j:j+3])
        if p not in ids:ids[p]=len(points);points.append(p)
        face.append(ids[p])
    faces.append(face)
original=m.Manifold(m.Mesh64(np.asarray(points,dtype=np.float64),np.asarray(faces,dtype=np.uint64)))
assert original.status()==m.Error.NoError
tolerance=float(os.environ.get('MESH_TOLERANCE','.05'))
clean=original.set_tolerance(tolerance).simplify(tolerance)
surface=clean.to_mesh64()
assert clean.status()==m.Error.NoError and len(clean.decompose())==1
snap_decimals=os.environ.get('MESH_COORD_DECIMALS')
if snap_decimals is not None:
    # Remove sub-micron STL round-trip terraces before volume meshing.
    # This is explicit analysis geometry tolerance, never a print rescale.
    v,inverse=np.unique(np.round(surface.vert_properties[:,:3],int(snap_decimals)),axis=0,return_inverse=True)
    f=inverse[surface.tri_verts]
    f=f[(f[:,0]!=f[:,1])&(f[:,0]!=f[:,2])&(f[:,1]!=f[:,2])]
    area=np.linalg.norm(np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]),axis=1)
    f=f[area>1e-10]
    _,unique_idx,duplicates=np.unique(np.sort(f,axis=1),axis=0,return_index=True,return_counts=True)
    f=f[unique_idx[duplicates%2==1]]
    snapped=m.Mesh64(v,f.astype(np.uint64));snapped.merge()
    clean=m.Manifold(snapped)
    pieces=[p for p in clean.decompose() if abs(p.volume())>1e-6]
    assert clean.status()==m.Error.NoError and len(pieces)==1,(clean.status(),len(pieces))
    clean=pieces[0]
    surface=clean.to_mesh64()
tg=tetgen.TetGen(surface.vert_properties[:,:3],surface.tri_verts)
maxvolume=float(os.environ.get('MESH_MAX_VOLUME','-1'))
nodes,elements,*_=tg.tetrahedralize(order=1,minratio=float(os.environ.get('MESH_RATIO','1.5')),mindihedral=10,opt_iterations=10,quiet=True,fixedvolume=maxvolume>0,maxvolume=maxvolume)
p=nodes[elements[:,:4]]
vol=np.linalg.det(np.stack((p[:,1]-p[:,0],p[:,2]-p[:,0],p[:,3]-p[:,0]),axis=2))/6
print('minimum absolute tetra volume',np.abs(vol).min(),flush=True)
edges=np.array([np.sum((p[:,i]-p[:,j])**2,axis=1) for i in range(4) for j in range(i)]).T
shape=12*(3*np.abs(vol))**(2/3)/edges.sum(axis=1)
# Absolute size alone rejects small, well-shaped tetrahedra at knife edges.
# Require positive Jacobians AND a dimensionless shape floor instead.
if np.min(vol)<=1e-15 or np.min(shape)<.001:
    print('tiny element diagnostic',{'nodes':len(nodes),'elements':len(elements),'minimum_shape':float(shape.min()),'tiny_volume_shape':float(shape[np.argmin(np.abs(vol))]),'tiny_volume_center':p[np.argmin(np.abs(vol))].mean(axis=0).tolist()},flush=True)
    np.savez_compressed(OUT/'mesh-diagnostic.npz',nodes=nodes,elements=elements)
assert np.min(vol)>1e-15,'Zero/inverted or numerically vanishing tetrahedron'
assert np.min(shape)>=.001,'Unacceptable sliver shape; repair/refine the surface'
np.savez_compressed(OUT/'volume-mesh.npz',nodes=nodes,elements=elements)
report={'source_sha256':hashlib.sha256(data).hexdigest(),'analysis_simplification_tolerance_mm':tolerance,'original_volume_mm3':original.volume(),'simplified_volume_mm3':clean.volume(),'nodes':len(nodes),'tetrahedra':len(elements),'volume_mm3':float(np.abs(vol).sum()),'minimum_element_volume_mm3':float(np.abs(vol).min()),'solver_run':False}
report['analysis_coordinate_snap_mm']=10**(-int(snap_decimals)) if snap_decimals is not None else None
report['minimum_mean_ratio']=float(shape.min())
report['requested_maximum_tetra_volume_mm3']=maxvolume if maxvolume>0 else None
report['mesh_acceptance']={'positive_volume_floor_mm3':1e-15,'mean_ratio_floor':.001}
(OUT/'mesh-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))

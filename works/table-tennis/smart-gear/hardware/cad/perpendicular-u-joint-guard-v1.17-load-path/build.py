"""Export native SCAD geometry, then finish all positive edges with Manifold.

Same octahedral erode/dilate opening as the inherited SCAD implementation;
avoids CGAL convex-decomposition failures. No reverse-engineered mesh replaces
the parameterized structural source. Run with uv --with numpy --with manifold3d.
"""
from pathlib import Path
import hashlib,json,struct,subprocess,os
import numpy as np
import manifold3d as m

HERE=Path(__file__).resolve().parent
CAD=HERE.parent
OUT=CAD/'exports/perpendicular-u-joint-v1.17-load-path'
OUT.mkdir(parents=True,exist_ok=True)
SCAD=HERE/'load_path_guard.scad'
VERSION='1.17'

def load(path):
    data=path.read_bytes();ids={};faces=[]
    for i in range(struct.unpack_from('<I',data,80)[0]):
        values=struct.unpack_from('<12f',data,84+50*i)[3:];face=[]
        for j in (0,3,6):
            point=tuple(values[j:j+3]);ids.setdefault(point,len(ids));face.append(ids[point])
        faces.append(face)
    solid=m.Manifold(m.Mesh64(np.array(list(ids),dtype=float),np.array(faces,dtype=np.uint64)))
    assert solid.status()==m.Error.NoError,path
    return solid

def write(solid,path):
    assert solid.status()==m.Error.NoError
    mesh=solid.to_mesh64();vertices=mesh.vert_properties[:,:3];faces=mesh.tri_verts
    temporary=path.with_suffix('.tmp.stl')
    with temporary.open('wb') as f:
        f.write(b'Native SCAD / Manifold edge finishing / mm'.ljust(80,b'\0'));f.write(struct.pack('<I',len(faces)))
        for face in faces:
            p=vertices[face];normal=np.cross(p[1]-p[0],p[2]-p[0]);normal/=max(np.linalg.norm(normal),1e-30)
            f.write(struct.pack('<12fH',*normal,*p.ravel(),0))
    temporary.replace(path)

def export_precision(solid):
    # Snap at STL precision and discard only numerically collapsed triangles.
    # Accept only a closed single Manifold; a failed snap is never exported.
    mesh=solid.to_mesh64();vv=mesh.vert_properties[:,:3].astype(np.float32).astype(float)
    vv,inv=np.unique(vv,axis=0,return_inverse=True)
    mm=m.Mesh64(vv,inv[mesh.tri_verts].astype(np.uint64));mm.merge()
    rounded=m.Manifold(mm)
    assert rounded.status()==m.Error.NoError
    pieces=[p for p in rounded.decompose() if abs(p.volume())>1e-6]
    assert len(pieces)==1
    mesh=pieces[0].to_mesh64();original_v=mesh.vert_properties[:,:3]
    for decimals in (5,4,3,6):
        v,inverse=np.unique(np.round(original_v,decimals),axis=0,return_inverse=True)
        f=inverse[mesh.tri_verts]
        f=f[(f[:,0]!=f[:,1])&(f[:,0]!=f[:,2])&(f[:,1]!=f[:,2])]
        area=np.linalg.norm(np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]),axis=1)
        f=f[area>1e-10]
        _,idx,count=np.unique(np.sort(f,axis=1),axis=0,return_index=True,return_counts=True)
        f=f[idx[count%2==1]]
        candidate=m.Mesh64(v,f.astype(np.uint64));candidate.merge();result=m.Manifold(candidate)
        if result.status()!=m.Error.NoError:continue
        pieces=[p for p in result.decompose() if abs(p.volume())>1e-6]
        if len(pieces)==1:
            print('STL coordinate precision mm',10**(-decimals),flush=True)
            return pieces[0]
    raise RuntimeError('No valid closed solid at STL export precision')

def finish(raw,r):
    kernel=m.Manifold.hull_points(np.array([[r,0,0],[-r,0,0],[0,r,0],[0,-r,0],[0,0,r],[0,0,-r]]))
    envelope=m.Manifold.cube([120,120,120]).translate([-60,-60,-55])
    return raw^((envelope-(envelope-raw).minkowski_sum(kernel)).minkowski_sum(kernel))

def main():
    executable=os.environ.get('OPENSCAD','/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD')
    for feature,name in [('raw','raw-solid.stl'),('label','label.stl')]:
        subprocess.run([executable,'--backend=Manifold','--export-format=binstl','-D',f'FEATURE="{feature}"','-o',str(OUT/name),str(SCAD)],check=True)
    raw=load(OUT/'raw-solid.stl')
    bottom=m.Manifold.cube([120,120,1.5]).translate([-60,-60,-23.5])
    body=(finish(raw,.6)+(raw^bottom)).set_tolerance(.0001).simplify(.0001)
    parts=[p for p in body.decompose() if abs(p.volume())>1e-6]
    assert len(parts)==1
    body=export_precision(parts[0])
    write(body,OUT/f'guard-v{VERSION}-body.stl')
    # Finish individual glyph islands separately; the operation distributes
    # here because glyph spacing exceeds twice the 0.1 mm kernel radius.
    label=m.Manifold.batch_boolean([finish(g,.1) for g in load(OUT/'label.stl').decompose()],m.OpType.Add)
    full=(body+label).set_tolerance(.0001).simplify(.0001)
    parts=[p for p in full.decompose() if abs(p.volume())>1e-6]
    assert len(parts)==1
    full=export_precision(parts[0])
    print('components',len(body.decompose()),len(full.decompose()),flush=True)
    assert len(body.decompose())==1 and len(full.decompose())==1
    for solid,name in [(body,f'guard-v{VERSION}-body.stl'),(full,f'guard-v{VERSION}.stl')]:write(solid,OUT/name)
    report={'structural_source':str(SCAD.relative_to(CAD)),'edge_finish':'octahedral morphological opening, r=0.6 mm; lowest 1.5 mm exempt',
            'body_components':len(body.decompose()),'full_components':len(full.decompose()),'raw_volume_mm3':raw.volume(),'body_volume_mm3':body.volume(),
            'full_volume_mm3':full.volume(),'bounding_box_mm':full.bounding_box(),'bevel_addition_outside_raw_mm3':(body-raw).volume(),
            'body_sha256':hashlib.sha256((OUT/f'guard-v{VERSION}-body.stl').read_bytes()).hexdigest()}
    (OUT/'build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()

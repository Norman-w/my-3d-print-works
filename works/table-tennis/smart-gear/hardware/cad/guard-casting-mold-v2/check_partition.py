"""Check that added locator clearances/band tracks do not change the casting cavity."""
import build as design
import numpy as np,json,subprocess,shutil
b=design.b

def read(path):
    ids={};faces=[];face=[]
    for line in path.read_text().splitlines():
        f=line.split()
        if f and f[0]=='vertex':
            p=tuple(map(float,f[1:]));ids.setdefault(p,len(ids));face.append(ids[p])
            if len(face)==3:faces.append(face);face=[]
    s=b.m.Manifold(b.m.Mesh64(np.array(list(ids)),np.array(faces,dtype=np.uint64)))
    assert s.status()==b.m.Error.NoError
    return s

def solids():return {k:read(design.OUT/f'{k}.stl') for k in design.NAMES}

def main():
    s=solids();product=s.pop('product')
    stock=b.m.Manifold.cube([design.BX,design.BY,design.Z1-design.Z0]).translate([-design.BX/2,-design.BY/2,design.Z0])
    subprocess.run([shutil.which('openscad'),'--backend=Manifold','--export-format=binstl','-D','FEATURE="ports"','-o',str(design.OUT/'ports-diagnostic.stl'),str(design.HERE/'mold.scad')],check=True)
    ports=b.load(design.OUT/'ports-diagnostic.stl')
    free=stock-b.m.Manifold.batch_boolean(list(s.values()),b.m.OpType.Add)
    # Locator annuli and exterior band tracks are allowed voids, but must not
    # form a volume-connected path into the product cavity.
    cast_components=[p for p in free.decompose() if abs((p^product).volume())>1]
    assert len(cast_components)==1,len(cast_components)
    cast=cast_components[0]
    extra=cast-product-ports;missing=product-cast
    report={'cavity_components':len(cast_components),'cavity_added_outside_product_excluding_ports_mm3':abs(extra.volume()),'product_volume_missing_from_cavity_mm3':abs(missing.volume()),'product_volume_mm3':product.volume(),'external_locator_and_band_voids_mm3':free.volume()-cast.volume(),'locator_voids_connected_to_casting':False,'process_compensation':'none; nominal geometry; physical seal untested'}
    print(json.dumps(report,indent=2));(design.HERE/'partition-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    shutil.copy2(design.HERE/'partition-validation.json',design.WEB/'partition-validation.json')
    assert max(abs(extra.volume()),abs(missing.volume()))<.2,report
if __name__=='__main__':main()

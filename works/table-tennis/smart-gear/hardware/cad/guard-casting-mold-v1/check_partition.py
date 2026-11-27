"""Verify the actual exported molds cover the stock except product and ports."""
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
    return b.m.Manifold(b.m.Mesh64(np.array(list(ids)),np.array(faces,dtype=np.uint64)))

def main():
    molds=[read(design.OUT/f'{k}.stl') for k in design.NAMES if k!='product']
    product=read(design.OUT/'product.stl')
    stock=b.m.Manifold.cube([design.BX,design.BY,design.Z1-design.Z0]).translate([-design.BX/2,-design.BY/2,design.Z0])
    subprocess.run([shutil.which('openscad'),'--backend=Manifold','--export-format=binstl','-D','FEATURE="ports"','-o',str(design.OUT/'ports-diagnostic.stl'),str(design.HERE/'mold.scad')],check=True)
    ports=b.load(design.OUT/'ports-diagnostic.stl')
    remaining=stock-b.m.Manifold.batch_boolean(molds+[product,ports],b.m.OpType.Add)
    cavities=(stock-b.m.Manifold.batch_boolean(molds,b.m.OpType.Add))-(ports-product)
    extra=cavities-product;missing=product-cavities
    report={'stock_unassigned_excluding_ports_mm3':abs(remaining.volume()),'cavity_added_outside_product_excluding_ports_mm3':abs(extra.volume()),'product_volume_missing_from_cavity_mm3':abs(missing.volume()),'ports_volume_mm3':ports.volume(),'closed_casting_cavity_volume_mm3':cavities.volume(),'product_volume_mm3':product.volume(),'process_compensation':'none; nominal geometry'}
    print(json.dumps(report,indent=2));(design.HERE/'partition-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    assert max(report[k] for k in list(report)[:3])<.2,report
if __name__=='__main__':main()

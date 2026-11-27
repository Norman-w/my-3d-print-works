"""CalculiX displacement-driven, frictionless lower-foot contact experiment.
mm,N,MPa. Roof clamped: an explicit idealized upper-fixture assumption.
PETG isotropic elastic E=1500,nu=.38 is a sensitivity baseline, not a coupon fit.
"""
from pathlib import Path
import numpy as np
import json,math,os
HERE=Path(os.environ.get('CASE_DIR',Path(__file__).resolve().parent))
mesh=np.load(HERE/'volume-mesh.npz');nodes=mesh['nodes'];tet=mesh['elements'].astype(int)+1
# Abaqus/CalculiX C3D4 side numbering. Retain actual exposed facets.
local=np.array([[0,1,2],[0,3,1],[1,3,2],[2,3,0]])
faces=tet[:,local].reshape(-1,3);keys=np.sort(faces,axis=1)
_,idx,counts=np.unique(keys,axis=0,return_index=True,return_counts=True)
exposed=idx[counts==1];surface=[]
for i in exposed:
    pts=nodes[faces[i]-1]
    if np.max(np.abs(np.abs(pts[:,0])-10.9))<.08 and pts[:,2].max()<.25 and pts[:,2].min()>-22:
        surface.append((int(i//4+1),int(i%4+1)))
assert len(surface)>20
fixed=np.flatnonzero(nodes[:,2]>23.01)+1
foot=np.array([[-10,-55,-20],[10,-55,-20],[10,55,-20],[-10,55,-20],[-10,-55,0],[10,-55,0],[10,55,0],[-10,55,0]],float)
start=len(nodes)+1;footids=np.arange(start,start+8);feid=len(tet)+1
with (HERE/'contact.inp').open('w') as f:
    def line(s):f.write(s+'\n')
    line('*HEADING\nGuard v1.16 frictionless foot contact; CLAMPED ROOF approximation\n*NODE')
    for i,p in enumerate(nodes,1):line(f'{i},'+','.join(f'{v:.9g}' for v in p))
    for i,p in zip(footids,foot):line(f'{i},'+','.join(map(str,p)))
    line('*ELEMENT,TYPE=C3D4,ELSET=CLIP')
    for i,t in enumerate(tet,1):line(f'{i},'+','.join(map(str,t)))
    line('*ELEMENT,TYPE=C3D8,ELSET=FOOT');line(f'{feid},'+','.join(map(str,footids)))
    line('*NSET,NSET=FIXED')
    for i in range(0,len(fixed),12):line(','.join(map(str,fixed[i:i+12])))
    line('*NSET,NSET=FOOTNODES');line(','.join(map(str,footids)))
    line('*MATERIAL,NAME=PETG\n*ELASTIC\n1500.,0.38\n*SOLID SECTION,ELSET=CLIP,MATERIAL=PETG')
    line('*MATERIAL,NAME=STEEL\n*ELASTIC\n200000.,0.3\n*SOLID SECTION,ELSET=FOOT,MATERIAL=STEEL')
    line('*SURFACE,NAME=CLIPINNER,TYPE=ELEMENT')
    for eid,s in surface:line(f'{eid},S{s}')
    line('*SURFACE,NAME=FOOTSIDES,TYPE=ELEMENT')
    for s in range(3,7):line(f'{feid},S{s}')
    line('*SURFACE INTERACTION,NAME=CONTACTLAW\n*SURFACE BEHAVIOR,PRESSURE-OVERCLOSURE=LINEAR\n75000.,\n*CONTACT PAIR,INTERACTION=CONTACTLAW,TYPE=SURFACE TO SURFACE\nCLIPINNER,FOOTSIDES')
    line('*BOUNDARY\nFIXED,1,3,0.')
    # Six separate equilibrium targets expose zero reaction before contact,
    # then progressively load the arms. Absolute displacement values.
    angles=[float(v) for v in os.environ.get('ANGLES','.5,1.,1.4,1.6,2.,3.,4.,6.').split(',')]
    for angle in angles:
        theta=math.radians(angle);rot=np.array([[math.cos(theta),-math.sin(theta),0],[math.sin(theta),math.cos(theta),0],[0,0,1]])
        disp=foot@rot.T-foot
        line('*STEP,NLGEOM,INC=200\n*STATIC\n1.,1.,1.e-7,1.\n*BOUNDARY')
        for nid,d in zip(footids,disp):
            for axis,v in enumerate(d,1):line(f'{nid},{axis},{axis},{v:.10g}')
        line('*NODE FILE,FREQUENCY=999\nU,RF\n*EL FILE,FREQUENCY=999\nS\n*NODE PRINT,NSET=FOOTNODES,FREQUENCY=999\nU,RF\n*NODE PRINT,NSET=FIXED,TOTALS=ONLY,FREQUENCY=999\nRF\n*CONTACT PRINT,FREQUENCY=999\nCDIS,CSTR\n*END STEP')
report={'contact_facets':len(surface),'fixed_nodes':len(fixed),'clip_nodes':len(nodes),'clip_tetrahedra':len(tet),'roof_clamped_above_z_mm':23.01,'foot_nodes':footids.tolist(),'foot_initial_xyz':foot.tolist(),'angles_deg':angles,'E_MPa':1500,'nu':.38,'contact_penalty_MPa_per_mm':75000,'friction':0,'not_physical_fracture_simulation':True}
(HERE/'contact-model.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))

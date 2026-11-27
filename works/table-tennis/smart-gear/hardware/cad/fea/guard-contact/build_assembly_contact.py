"""Two contact pairs: fixed upper beam, freely rotating clip, driven lower foot.
Three Z locators suppress out-of-plane rigid-body drift only. Three weak XY
ground springs stabilize the initial contact-free planar rigid modes; their
force/torque contributions must be checked against the beam reactions.
"""
from pathlib import Path
import numpy as np,json,math,os
BASE=Path(__file__).resolve().parent
HERE=Path(os.environ.get('ASSEMBLY_DIR',BASE/'assembly'));HERE.mkdir(parents=True,exist_ok=True)
MESH_DIR=Path(os.environ.get('MESH_DIR',BASE))
mesh=np.load(MESH_DIR/'volume-mesh.npz');nodes=mesh['nodes'];tet=mesh['elements'].astype(int)+1
np.savez_compressed(HERE/'volume-mesh.npz',**mesh)
for name in ('mesh-report.json','quality-report.json'):(HERE/name).write_bytes((MESH_DIR/name).read_bytes())
local=np.array([[0,1,2],[0,3,1],[1,3,2],[2,3,0]])
faces=tet[:,local].reshape(-1,3);_,idx,cnt=np.unique(np.sort(faces,1),axis=0,return_index=True,return_counts=True)
lower=[];upper=[]
for i in idx[cnt==1]:
    p=nodes[faces[i]-1]
    if max(abs(abs(p[:,0])-10.9))<.08 and p[:,2].max()<.25 and p[:,2].min()>-22:lower.append((int(i//4+1),int(i%4+1)))
    if max(abs(abs(p[:,1])-10.5))<.08 and p[:,2].max()>.1 and p[:,2].min()<20.1:upper.append((int(i//4+1),int(i%4+1)))
assert len(lower)>20 and len(upper)>20
foot=np.array([[-10,-55,-20],[10,-55,-20],[10,55,-20],[-10,55,-20],[-10,-55,0],[10,-55,0],[10,55,0],[-10,55,0]],float)
beam=np.array([[-56,-10,0],[56,-10,0],[56,10,0],[-56,10,0],[-56,-10,20],[56,-10,20],[56,10,20],[-56,10,20]],float)
footids=np.arange(len(nodes)+1,len(nodes)+9);upperids=footids+8
roof=np.flatnonzero(nodes[:,2]>23.01)
locators=[]
for target in [[-25,-15,30],[25,-15,30],[0,15,30]]:
    locators.append(int(roof[np.argmin(np.linalg.norm(nodes[roof]-target,axis=1))]+1))
assert len(set(locators))==3
springs=[(locators[0],1),(locators[0],2),(locators[1],2)];spring_k=float(os.environ.get('STABILIZER_K','1'))
# Verify planar rigid-mode stabilization has full rank before solving.
mode_rows=[]
for nid,axis in springs:
    x,y,_=nodes[nid-1];mode_rows.append([1,0,-y] if axis==1 else [0,1,x])
assert np.linalg.matrix_rank(mode_rows)==3,'Weak supports leave a planar rigid mode'
angles=[float(v) for v in os.environ.get('ASSEMBLY_ANGLES','.5,1.4,2.2,2.6,3,3.4').split(',')]
static_increment=os.environ.get('ASSEMBLY_STATIC','1.,1.,.000001,1.')
with (HERE/'contact.inp').open('w') as f:
    def line(s):f.write(s+'\n')
    line('*HEADING\nGuard TWO-PAIR contact: fixed upper beam; free clip XY; weak stabilization\n*NODE')
    for i,p in enumerate(np.concatenate([nodes,foot,beam]),1):line(f'{i},'+','.join(f'{v:.9g}' for v in p))
    line('*ELEMENT,TYPE=C3D4,ELSET=CLIP')
    for i,t in enumerate(tet,1):line(f'{i},'+','.join(map(str,t)))
    line('*ELEMENT,TYPE=C3D8,ELSET=STEELPARTS')
    for eid,ids in [(len(tet)+1,footids),(len(tet)+2,upperids)]:line(f'{eid},'+','.join(map(str,ids)))
    for j,(nid,axis) in enumerate(springs):
        name=f'STAB{j}';line(f'*ELEMENT,TYPE=SPRING1,ELSET={name}\n{len(tet)+3+j},{nid}\n*SPRING,ELSET={name}\n{axis}\n{spring_k}')
    for name,ids in [('FOOTNODES',footids),('FIXED',upperids),('ZLOCATORS',locators)]:line(f'*NSET,NSET={name}\n'+','.join(map(str,ids)))
    line('*MATERIAL,NAME=PETG\n*ELASTIC\n1500.,.38\n*SOLID SECTION,ELSET=CLIP,MATERIAL=PETG\n*MATERIAL,NAME=STEEL\n*ELASTIC\n200000.,.3\n*SOLID SECTION,ELSET=STEELPARTS,MATERIAL=STEEL')
    for name,surface in [('CLIPLOWER',lower),('CLIPUPPER',upper)]:
        line(f'*SURFACE,NAME={name},TYPE=ELEMENT')
        for eid,face in surface:line(f'{eid},S{face}')
    for name,eid in [('FOOTSIDES',len(tet)+1),('BEAMSIDES',len(tet)+2)]:
        line(f'*SURFACE,NAME={name},TYPE=ELEMENT')
        for side in range(1,7):line(f'{eid},S{side}')
    line('*SURFACE INTERACTION,NAME=LAW\n*SURFACE BEHAVIOR,PRESSURE-OVERCLOSURE=LINEAR\n75000.,.000001')
    for a,b in [('CLIPLOWER','FOOTSIDES'),('CLIPUPPER','BEAMSIDES')]:line(f'*CONTACT PAIR,INTERACTION=LAW,TYPE=SURFACE TO SURFACE\n{a},{b}')
    line('*BOUNDARY\nFIXED,1,3,0.\nZLOCATORS,3,3,0.')
    for angle in angles:
        theta=math.radians(angle);rot=np.array([[math.cos(theta),-math.sin(theta),0],[math.sin(theta),math.cos(theta),0],[0,0,1]])
        line('*STEP,NLGEOM,INC=200\n*STATIC\n'+static_increment)
        if angle<=2.2:
            # Average element force approaches zero while the clip floats
            # through the gap. A .01 N reference bounds the absolute force
            # residual at 5e-5 N, without creating any physical restraint.
            line('*CONTROLS,PARAMETERS=FIELD\n.005,.01,.01,.01,.02,.00001,.001,.00000001')
        else:line('*CONTROLS,RESET')
        line('*BOUNDARY')
        for nid,d in zip(footids,foot@rot.T-foot):
            for axis,v in enumerate(d,1):line(f'{nid},{axis},{axis},{v:.10g}')
        line('*NODE FILE,FREQUENCY=999\nU,RF\n*EL FILE,FREQUENCY=999\nS\n*NODE PRINT,NSET=FOOTNODES,FREQUENCY=999\nU,RF\n*NODE PRINT,NSET=FIXED,FREQUENCY=999\nRF\n*CONTACT PRINT,FREQUENCY=999\nCDIS,CSTR\n*END STEP')
report={'model_type':'upper_and_lower_contact','contact_facets':len(lower),'upper_contact_facets':len(upper),'fixed_nodes':8,
 'upper_surface_facets':upper,
 'clip_nodes':len(nodes),'clip_tetrahedra':len(tet),'foot_nodes':footids.tolist(),'foot_initial_xyz':foot.tolist(),
 'upper_nodes':upperids.tolist(),'upper_initial_xyz':beam.tolist(),'vertical_locators':locators,
 'stabilizer_springs':[{'node':nid,'axis':axis,'k_N_per_mm':spring_k} for nid,axis in springs],
 'angles_deg':angles,'static_increment':static_increment,'E_MPa':1500,'nu':.38,'contact_penalty_MPa_per_mm':75000,'friction':0,
 'roof_clamped':False,'out_of_plane_locator_assumption':True,'free_gap_force_reference_N':.01,'not_physical_fracture_simulation':True}
(HERE/'contact-model.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='upper_surface_facets'}))

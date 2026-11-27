"""Export actual converged CalculiX nodal fields, never synthetic hotspots."""
from pathlib import Path
import json,re,hashlib,os
import numpy as np
BASE=Path(__file__).resolve().parent
HERE=Path(os.environ.get('CASE_DIR',BASE))
OUT=Path(os.environ.get('RESULT_DIR',BASE.parent.parent/'preview/guard-fea-results'));OUT.mkdir(parents=True,exist_ok=True)
mesh=np.load(HERE/'volume-mesh.npz');nodes=mesh['nodes'];tet=mesh['elements'].astype(int)
loc=np.array([[0,2,1],[0,1,3],[1,2,3],[2,0,3]])
faces=tet[:,loc].reshape(-1,3);keys=np.sort(faces,axis=1)
_,idx,cnt=np.unique(keys,axis=0,return_index=True,return_counts=True)
boundary=faces[idx[cnt==1]];used,inverse=np.unique(boundary,return_inverse=True)
nodes[used].astype('<f4').tofile(OUT/'positions.bin');inverse.astype('<u4').tofile(OUT/'triangles.bin')
config=json.loads((HERE/'contact-model.json').read_text());footids=np.array(config['foot_nodes'])-1
foot=np.array(config['foot_initial_xyz']);upper=np.array(config.get('upper_initial_xyz',[])).reshape(-1,3);allcoords=np.concatenate([nodes,foot,upper]);n=len(allcoords)
frames={};time=None;field=None;values=None
with (HERE/'contact.frd').open() as f:
    for line in f:
        if line.startswith('  100CL'):
            # Fixed format: time in columns 13..25, step towards end.
            parts=line.split();time=float(parts[2]);field=None
        elif line.startswith(' -4'):
            field=line.split()[1]
            if field in ('DISP','STRESS','FORC'):values=np.zeros((n,6 if field=='STRESS' else 3))
            else:values=None
        elif line.startswith(' -1') and values is not None and time is not None:
            nid=int(line[3:13])-1
            vals=[float(line[i:i+12]) for i in range(13,len(line.rstrip()),12)]
            values[nid,:min(len(vals),values.shape[1])]=vals[:values.shape[1]]
        elif line.startswith(' -3') and values is not None:
            frames.setdefault(time,{})[field]=values;values=None
result=[]
contact={};mode=None;contact_time=None
upper_facet_keys=set(map(tuple,config.get('upper_surface_facets',[])))
if not upper_facet_keys and config.get('model_type')=='upper_and_lower_contact':
    reading=False
    for line in (HERE/'contact.inp').read_text().splitlines():
        if line.startswith('*SURFACE,NAME=CLIPUPPER'):reading=True;continue
        if line.startswith('*'):reading=False
        elif reading:
            eid,side=line.split(',');upper_facet_keys.add((int(eid),int(side.lstrip('S'))))
for line in (HERE/'contact.dat').read_text().splitlines():
    if 'relative contact displacement (' in line or 'contact stress (' in line:
        mode='gap' if 'displacement' in line else 'pressure'
        contact_time=float(line.split('time')[-1]);contact.setdefault(contact_time,{'gap':[],'pressure':[],'upper_pressure_samples':0,'lower_pressure_samples':0})
    elif mode:
        parts=line.split()
        if len(parts)==5:
            try:
                value=float(parts[2]);contact[contact_time][mode].append(value)
                if mode=='pressure' and value>0:contact[contact_time]['upper_pressure_samples' if (int(parts[0]),int(parts[1])) in upper_facet_keys else 'lower_pressure_samples']+=1
            except ValueError:mode=None
        elif line.strip():mode=None
for time,fields in sorted(frames.items()):
    if abs(time-round(time))>1e-7:continue
    if not all(k in fields for k in ('DISP','STRESS','FORC')):continue
    s=fields['STRESS'][:len(nodes)];u=fields['DISP'][:len(nodes)]
    deformed=(nodes+u)[tet]
    detj=np.linalg.det(np.stack([deformed[:,1]-deformed[:,0],deformed[:,2]-deformed[:,0],deformed[:,3]-deformed[:,0]],axis=2))
    vm=np.sqrt(.5*((s[:,0]-s[:,1])**2+(s[:,1]-s[:,2])**2+(s[:,2]-s[:,0])**2)+3*np.sum(s[:,3:]**2,axis=1))
    layer=np.maximum(0,s[:,2]);rf=fields['FORC'];xyz=allcoords+fields['DISP']
    torque=np.sum(np.cross(xyz[footids],rf[footids])[:,2])/1000
    fixed=np.array(config['upper_nodes'])-1 if 'upper_nodes' in config else np.flatnonzero(nodes[:,2]>23.01)
    support_torque=np.sum(np.cross(xyz[fixed],rf[fixed])[:,2])/1000
    stabilizer_force=np.zeros_like(nodes)
    for spring in config.get('stabilizer_springs',[]):
        ni=spring['node']-1;axis=spring['axis']-1
        stabilizer_force[ni,axis]-=spring['k_N_per_mm']*u[ni,axis]
    stabilizer_torque=np.sum(np.cross(nodes+u,stabilizer_force)[:,2])/1000
    physical_torque=abs(torque+stabilizer_torque) if config.get('model_type')=='upper_and_lower_contact' else abs(torque)
    force_balance=np.sum(rf,axis=0)+stabilizer_force.sum(axis=0)
    # Keep support fixture stress in the visible field; additionally report
    # the body region below its clamped roof for first-failure screening.
    eligible=nodes[:,2]<22
    peak=int(np.argmax(np.where(eligible,vm,-1)))
    data=np.column_stack([vm[used],layer[used],u[used]])
    name=f'frame-{len(result):02}.bin';data.astype('<f4').tofile(OUT/name)
    idx=min(len(config['angles_deg'])-1,max(0,int(round(time))-1))
    contacts=contact.get(time,{'gap':[],'pressure':[]})
    result.append({'time':time,'angle_deg':config['angles_deg'][idx],
        'contact_sample_count':len(contacts['gap']),
        'upper_positive_pressure_samples':contacts.get('upper_pressure_samples',0),
        'lower_positive_pressure_samples':contacts.get('lower_pressure_samples',0),
        'max_penetration_mm':max([0]+[-v for v in contacts['gap']]),
        'max_contact_pressure_MPa':max([0]+contacts['pressure']),
        'torque_Nm':float(physical_torque),'driver_torque_Nm':float(abs(torque)),'signed_torque_Nm':float(torque),
        'equivalent_kg_at_200mm':float(physical_torque/(.2*9.80665)),
        'support_torque_Nm':float(support_torque),
        'stabilizer_torque_Nm':float(stabilizer_torque),
        'stabilizer_torque_fraction':float(abs(stabilizer_torque)/max(abs(torque),1e-6)),
        'upper_reactions_N':rf[fixed].tolist() if 'upper_nodes' in config else [],
        'foot_reactions_N':rf[footids].tolist(),
        'torque_balance_relative':float(abs(torque+support_torque+stabilizer_torque)/max(abs(torque),1e-6)),
        'net_force_N':force_balance.tolist(),
        'max_vm_body_MPa':float(vm[eligible].max()),'p99_vm_body_MPa':float(np.quantile(vm[eligible],.99)),
        'max_vm_all_MPa':float(vm.max()),'global_hotspot_xyz_mm':nodes[int(vm.argmax())].tolist(),
        'negative_or_zero_deformed_jacobians_from_frd':int(np.count_nonzero(detj<=0)),
        'minimum_deformed_detJ_from_frd_mm3':float(detj.min()),
        'max_layer_tension_body_MPa':float(layer[eligible].max()),
        'hotspot_xyz_mm':nodes[peak].tolist(),'max_displacement_mm':float(np.linalg.norm(u,axis=1).max()),
        'file':name})
assert result,'No complete converged frames in FRD'
stdout_path=HERE/'solver.stdout.log'
if not stdout_path.exists():stdout_path=HERE/'contact.log'
stdout_marker='Job finished' in stdout_path.read_text()
sta_steps={}
for line in (HERE/'contact.sta').read_text().splitlines():
    parts=line.split()
    if len(parts)==7:
        try:sta_steps[int(parts[0])]=float(parts[5])
        except ValueError:pass
sta_complete=all(sta_steps.get(i,0)>=1-1e-8 for i in range(1,len(config['angles_deg'])+1))
fresh_outputs=all((HERE/name).stat().st_mtime>=(HERE/'contact.inp').stat().st_mtime for name in ['contact.frd','contact.sta'])
complete_fields=len(result)==len(config['angles_deg'])
completion=sta_complete and complete_fields and fresh_outputs
manifest={'solver':'CalculiX 2.23','units':'mm N MPa','version':os.environ.get('MODEL_VERSION','1.16'),'node_count':len(used),
    'triangle_count':len(boundary),'positions':'positions.bin','triangles':'triangles.bin',
    'frame_layout':['von_mises_MPa','positive_sigma_zz_MPa','ux_mm','uy_mm','uz_mm'],
    'mesh_report':json.loads((HERE/'mesh-report.json').read_text()),
    'assumptions':config,'frames':result,
    'material_reference':'https://prusament.com/wp-content/uploads/2022/10/PETG_Prusament_TDS_2021_10_EN.pdf',
    'user_material':{'brand':'彩格','colour':'black','series':'not_confirmed','mechanical_parameters_calibrated':False,'official_product_reference':'https://www.cgtoner.com/productinfo/338535.html','note':'Official Basic product page lists printing settings, not measured directional strength; Prusament values remain reference only.'},
    'reference_layer_strength_range_MPa':[14,22],'reference_xy_yield_range_MPa':[45,49],
    'strength_is_reference_not_measured_for_this_filament':True,
    'solid_body_not_explicit_30_percent_infill':True,
    'mesh_quality':json.loads((HERE/'quality-report.json').read_text()) if (HERE/'quality-report.json').exists() else None,
    'solver_job_finished':completion,
    'solver_completion_evidence':{'stdout_job_finished_marker':stdout_marker,'all_STA_steps_converged_to_end':sta_complete,'all_FRD_steps_complete':complete_fields,'outputs_newer_than_input':fresh_outputs,'note':'Every STA endpoint must converge and every fresh FRD field must be complete. The stdout completion marker is supplementary; never accept a partial step.'},
    'all_requested_steps_exported':complete_fields,
    'fracture_crack_growth_simulated':False,
    'frd_sha256':hashlib.sha256((HERE/'contact.frd').read_bytes()).hexdigest()}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(result,indent=2))

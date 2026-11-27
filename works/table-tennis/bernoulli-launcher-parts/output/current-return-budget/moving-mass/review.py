#!/usr/bin/env python3
"""Density-parametric moving-solid gravity budget; never assumes measured mass."""
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
import hashlib,importlib.util,json,math,re,subprocess,sys,csv
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2]
SNAP=ROOT/'output/cable-scene-export/20260927T091627124663Z'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sys.path.insert(0,str(ROOT/'analysis'))
from cable_direct_contract import DirectPullContract,source_hashes
ip=Path('/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py')
sp=importlib.util.spec_from_file_location('inspector',ip);inspector=importlib.util.module_from_spec(sp);sp.loader.exec_module(inspector)

def stats(p):
 v=[tuple(map(float,x)) for x in re.findall(r'vertex\s+(\S+)\s+(\S+)\s+(\S+)',p.read_text())]
 assert v and len(v)%3==0
 volume=0.;moment=[0.,0.,0.]
 for i in range(0,len(v),3):
  a,b,c=v[i:i+3]
  dv=(a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0]))/6
  volume+=dv
  for k in range(3):moment[k]+=dv*(a[k]+b[k]+c[k])/4
 assert volume>0
 mesh=inspector.inspect(p,1e-6)
 assert mesh['watertightByEdgeTopology'],(p,mesh)
 assert abs(volume-mesh['volume'])<1e-5
 return {'volume_mm3':volume,'homogeneous_centroid_mm':[x/volume for x in moment],
         'max_local_XY_radius_mm':max(math.hypot(x[0],x[1]) for x in v)+1e-6,
         'vertices':len(v),'watertight_edge_topology':True}

def main():
 run=OUT/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');run.mkdir(parents=True)
 snapshot=json.loads((SNAP/'report.json').read_text());inventory=json.loads((ROOT/'docs/cable-assembly-inventory.json').read_text())
 source=dict(snapshot['source_sha256'])
 actpath=ROOT/'output/cable-actuation-v2/20260927T091604751038Z/report.json'
 selectionpath=ROOT/'output/feeder-return-spring/selection-contract.json'
 for p,h in source_hashes([OUT/'input-parts.scad'],[Path(__file__),OUT/'density-references.json',ROOT/'analysis/cable_direct_contract.py',SNAP/'report.json',actpath,selectionpath]).items():source[str(Path(p).relative_to(ROOT))]=h
 act=json.loads(actpath.read_text());spring=json.loads(selectionpath.read_text())['spring']
 source.update(act['source_sha256'])
 spring_rest=spring['initial_tension_N']+spring['rate_N_per_mm']*(act['source_contract']['spring_length_rest']-spring['free_inside_loop_length_mm'])
 assert abs(spring_rest-2.975)<1e-10 and spring['rate_N_per_mm']==.25
 assert all(sha(ROOT/p)==h for p,h in source.items())
 density=json.loads((OUT/'density-references.json').read_text())['values_g_per_cm3']
 model=DirectPullContract(inventory['scene_contract']['ci'])
 rows=[]
 # Retain only physical feeder bodies with explicitly rigid non-input motion.
 for p in snapshot['parts']:
  m=p['motion'];k=m['kind']
  if p['group']!='feeder' or k not in ['translate','radial']:continue
  assert m['input']=='stroke' and p['role'] in ['printed','purchased']
  f=ROOT/p['file'];assert sha(f)==p['sha256'];source[p['file']]=p['sha256']
  s=stats(f)
  if k=='translate':assert m['axis']==[0,0,1] and m['distance_mm']==20
  else:assert m['axis']==[1,0,0] and m['open_mm']-m['closed_mm']==5
  rows.append({'id':p['id'],'material_key':'PETG' if p['role']=='printed' else 'metal','motion':m,'geometry_file':p['file'],**s})
 def export(part):
  f=run/(part+'.stl');log=run/(part+'.log');cmd=['/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD','--hardwarnings','--export-format','asciistl','-D',f'part="{part}"','-o',str(f),str(OUT/'input-parts.scad')]
  p=subprocess.run(cmd,capture_output=True,text=True);s=p.stdout+p.stderr;log.write_text(s)
  assert p.returncode==0 and 'WARNING:' not in s and 'ERROR:' not in s,s
  r={'id':'candidate/input-'+part,'material_key':{'lever':'PETG','cap':'PETG','bush':'POM','metal':'metal'}[part],
  'motion':{'kind':'trigger-rotate','input':'stroke','coordinate':'input-local','origin':[0,0,0],'rotation_axis':[0,0,-1]},
  'geometry_file':str(f.relative_to(ROOT)),'geometry_sha256':sha(f),'command':cmd,'log_sha256':sha(log),**stats(f)}
  return r
 with ThreadPoolExecutor(max_workers=2) as pool:rows.extend(pool.map(export,['lever','cap','bush','metal']))
 def sums(kind,rear=None):
  return {mat:sum(x['volume_mm3'] for x in rows if x['material_key']==mat and x['motion']['kind']==kind and (rear is None or x['motion']['rear']==rear)) for mat in density}
 transl=sums('translate');front=sums('radial',False);rear=sums('radial',True)
 # Model-wide magnitude bound does not rely on opposite-side mass cancellation,
 # uniform infill, or a guessed centroid of a hollow print.
 radius_moment={mat:sum(x['volume_mm3']*x['max_local_XY_radius_mm'] for x in rows if x['material_key']==mat and x['motion']['kind']=='trigger-rotate') for mat in density}
 g=9.80665;force_scale=g*1e-6
 torque_coeff={k:force_scale*v for k,v in radius_moment.items()}
 trans_coeff={k:force_scale*v for k,v in transl.items()}
 radial_coeff={k:force_scale*.625*max(front[k],rear[k]) for k in density}
 Rmax=sum(density[k]*(trans_coeff[k]+radial_coeff[k]) for k in density)
 taumax=sum(density[k]*torque_coeff[k] for k in density)
 # A=R*cos(theta-phi), 0<=phi<=theta<=theta(20)<20deg, hence A>R*cos(20deg).
 assert model.state(20)['angle_deg']<20 and model.R==60
 Amin=60*math.cos(math.radians(20))
 table=[]
 for u in [0,5,8,10,12,15,20]:
  active=rear if u<8 else front if u>12 else {k:0 for k in density}
  R=sum(density[k]*force_scale*(transl[k]+.625*active[k]) for k in density)
  A=model.state(u)['effective_cable_arm_mm_per_rad'];Fs=spring_rest+spring['rate_N_per_mm']*u
  table.append({'stroke_mm':u,'output_rigid_gravity_bound_ref_N':R,'input_rigid_gravity_torque_bound_ref_Nmm':taumax,
   'input_gravity_equivalent_ref_N':taumax/A,'nominal_spring_N':Fs,
   'gravity_only_eta_threshold_ref':(taumax/A)/(Fs-R),
   'remaining_input_resistance_at_hypothetical_eta_0_6_ref_N':.6*(Fs-R)-taumax/A})
 # Include both limiting one-sided slopes at the breakpoints in the global bound.
 critical_eta=(taumax/Amin)/(spring_rest-Rmax)
 sample_mass=sum(x['volume_mm3']/1000*density[x['material_key']] for x in rows)
 checks={'local_input_shape_exported':True,'all_used_meshes_closed_by_edge_topology':all(x['watertight_edge_topology'] for x in rows),
 'conservative_arm_lower_positive':Amin>0,'reference_nominal_spring_exceeds_rigid_output_gravity':spring_rest>Rmax,
 'reference_only_zero_other_load_return_possible_at_eta_1':critical_eta<1,
 'monotone_density_sensitivity':all(v>=0 for d in [trans_coeff,radial_coeff,torque_coeff] for v in d.values())}
 # The analytic upper bound is linear in material density, not a physical
 # validation. Density*2 must double each gravitational term.
 assert abs(sum(2*density[k]*(trans_coeff[k]+radial_coeff[k]) for k in density)-2*Rmax)<1e-12
 assert all(sha(ROOT/p)==h for p,h in source.items())
 report={'status':'DENSITY_PARAMETRIC_RIGID_GRAVITY_BUDGET_ONLY','source_sha256':source,'sources_stable':True,
 'external_inspector':{'path':str(ip),'sha256':sha(ip)},'parts':rows,'checks':checks,
 'coefficients':{'output_translate_N_per_gcm3':trans_coeff,'output_active_radial_N_per_gcm3':radial_coeff,'input_Nmm_per_gcm3':torque_coeff,'conservative_input_arm_min_mm':Amin},
 'reference_density_gcm3':density,'nominal_spring_rest_force_N':spring_rest,'reference_case':{'modeled_solid_mass_g':sample_mass,'rigid_output_gravity_bound_N':Rmax,'rigid_input_gravity_bound_Nmm':taumax,'zero_friction_gravity_only_efficiency_threshold':critical_eta,'remaining_zero_pose_input_resistance_at_eta_0_6_N':.6*(spring_rest-Rmax)-taumax/Amin},
 'reference_rows':table,
 'sufficient_return_formula':'eta*(Fs_min - R_other_max - G_output - G_omitted_output) > D_other_max + (tau_other_max + G_input + G_omitted_input)/A_min + H/rho_force_min, with positive output surplus. eta must be a proved minimum, not the illustrative 0.6.',
 'scope':'Current nominal rigid output bodies plus isolated hex-bush input candidate. Rigid geometry volumes, conservative radius bound and symbolic density coefficients. Whole-stroke rigid gravity magnitudes; opposite-side cancellation not credited. Reference density case is not actual material identity or actual upper density.',
 'necessary_conditions_for_a_physical_bound':['Actual cleaned components lie inside the respective modeled solids or their mass/radius bounds are independently verified','Each material density is bounded above by the supplied rho parameter; published typical density alone does not prove this','Actual rigid motion follows the stated nominal constraint without added loose parts'],
 'excluded':['Physical spring wire mass: scene is a solid-cylinder outline, not actual coils','Flexible core and sheath deformation; static sheath may store or return force','Ball/hopper loads, air forces, friction, seal drag, hand residual load and inertia','Different material density, manufacturing oversize and moving extra hardware','Complete tolerance/error coupling and dynamic single-ball release'],
 'adopted':False,'manufacturing_release':False,'physical_acceptance':False}
 (run/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 with (run/'reference-gravity.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
 (OUT/'latest.json').write_text(json.dumps({'directory':str(run.relative_to(ROOT)),'report_sha256':sha(run/'report.json')},indent=2)+'\n')
 print(json.dumps({'run':str(run.relative_to(ROOT)),'parts':len(rows),'reference_case':report['reference_case'],'coefficients':report['coefficients'],'checks':checks},ensure_ascii=False,indent=2))
if __name__=='__main__':main()

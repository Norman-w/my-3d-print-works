from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import hashlib,json,re,subprocess
R=Path(__file__).resolve().parents[4];O=Path(__file__).resolve().parent;B=O/'frozen-baseline';EX='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD';D=O/'contract-comparison'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');D.mkdir(parents=True)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();rel=lambda p:str(Path(p).relative_to(R))
files=[R/'cad/cable-trigger-input.scad',R/'cad/cable-housing-route.scad',R/'cad/cable-scene-export.scad',Path(__file__),O/'baseline.json']
hashes={rel(p):sha(p)for p in files}
def unpack(x):
 if not isinstance(x,list):return x
 if x and x[0]=='__f12__':return x[1]+x[2]/1e6+x[3]/1e12
 return [unpack(v)for v in x]
def echo(name,text,defs=[]):
 p=D/(name+'.scad');p.write_text(text);out=D/(name+'.echo');cmd=[EX,'--hardwarnings']
 for x in defs:cmd+=['-D',x]
 cmd+=['-o',str(out),str(p)];run=subprocess.run(cmd,cwd=R,text=True,capture_output=True);log=run.stdout+run.stderr;txt=out.read_text()if out.exists()else'';(D/(name+'.log')).write_text(log)
 row={'name':name,'command':cmd,'returncode':run.returncode,'echo':rel(out),'sha256':sha(out)if out.exists()else None,'success':run.returncode==0 and not any(w in log+txt for w in ['WARNING:','ERROR:'])}
 lines=[x[len('ECHO: '):]for x in txt.splitlines()if x.startswith('ECHO: ')]
 if row['success']:
  assert len(lines)==1;row['value']=unpack(json.loads(re.sub(r'\bundef\b','null',lines[0])))
 return row
motion='echo(cc_pack([ci_spec(),[for(d=[-2,0,2])for(u=[0,10,20,22])[d,u,ci_angle(u,d),ci_path_length(ci_angle(u,d),d),ci_takeup(ci_angle(u,d),d),ci_B(ci_angle(u,d)),ci_T(ci_angle(u,d))]]]));\n'
pre=lambda root,route:'use <'+str(root/'cad/cable-trigger-input.scad')+'>\nuse <'+str(root/route)+'>\nuse <'+str(root/'cad/cable-contract-codec.scad')+'>\n'
old=echo('frozen-input',pre(B,'output/current-axis-offset-candidate/route/candidate.scad')+motion,['ci_origin=[75,-85,5]']);new=echo('adopted-input',pre(R,'cad/cable-housing-route.scad')+motion)
assert old['success']and new['success'];oldspec=dict(old['value'][0]);spec=dict(new['value'][0]);assert len(spec)==len(new['value'][0])
keys=['motion_law','stroke','origin','basis_x','basis_y','basis_z','ball_orbit_radius','fairlead_center','fairlead_core_radius','wire_terminal_local','angle_solve_deg','fairlead_extent_deg','adjuster_delta_range','mount_holes_cad','mount_plate_y','mount_rib_y','mount_bolt_underhead_y','mount_bolt_tip_y','cap_bolts_local_xy','cap_fasteners']
checks={'input_motion_12_samples_exact_precise_echo_match':old['value'][1]==new['value'][1],'retained_motion_and_global_mount_contract':all(spec[k]==oldspec[k]for k in keys),'obsolete_axis_contracts_removed':all(k not in spec for k in ['metal_sleeve_z','metal_sleeve_od_id_length','replaceable_bush_od_id_length','total_axial_float']),'axis_bom_rows':len(spec['axis_bom'])==5,'no_clip_as_real_hardware':spec['axis_clip_space_role']=='reference requirement, NOT actual installed E-ring solid','physical_acceptance_false':spec['axis_physical_acceptance']is False and spec['manufacturing_release']is False}
route_expr='cr_require_valid()echo(cc_pack([ci_install_delta(),cr_corner_shift(),cr_input_port(),cr_output_port(),cr_vertices(),cr_lines(),[for(i=[1:3])cr_arc(i)],cr_length(),cr_base_length()]));\n'
def route(d):
 tag=str(d).replace('-','minus');a=echo('frozen-route-'+tag,pre(B,'output/current-axis-offset-candidate/route/candidate.scad')+route_expr,['ci_origin=[75,-85,5]','ci_delta='+str(d)]);b=echo('adopted-route-'+tag,pre(R,'cad/cable-housing-route.scad')+route_expr,['ci_delta='+str(d)])
 return {'delta':d,'baseline':a,'adopted':b,'exact_precise_echo_match':a['success']and b['success']and a['value']==b['value']}
with ThreadPoolExecutor(max_workers=2)as pool:routes=list(pool.map(route,[-2,-1,0,1,2]))
checks['offset_candidate_routes_5_samples_match']=all(x['exact_precise_echo_match']for x in routes)
neg=[]
for label,define in [('old-origin','ci_origin=[75,-82,5]'),('old-side-run','cr_side_run=195'),('delta-outside','ci_delta=2.01')]:
 r=echo('reject-'+label,pre(R,'cad/cable-housing-route.scad')+'cr_require_valid()echo("unexpected-success");\n',[define]);r['correctly_rejected']=not r['success']and 'ERROR: Assertion' in (R/r['echo']).read_text();neg.append(r)
checks['unsupported_route_domains_rejected']=all(x['correctly_rejected']for x in neg)
checks['sources_stable']=all(sha(R/p)==h for p,h in hashes.items())
report={'status':'PRECISE_CONTRACT_AND_ROUTE_MATCH'if all(checks.values())else'REVIEW_REQUIRED','source_sha256':hashes,'checks':checks,'input':{'baseline':old,'adopted':new,'retained_keys':keys},'routes':routes,'negative_controls':neg,'scope':'Same frozen offset candidate route and direct-pull law; 12 input and 5 route numerical source checks, not full tolerance or physical proof. Route continuous-family proof remains its separately frozen source-equivalent evidence.','manufacturing_release':False,'physical_acceptance':False}
(D/'report.json').write_text(json.dumps(report,indent=2)+'\n');(O/'contract-latest.json').write_text(json.dumps({'report':rel(D/'report.json'),'sha256':sha(D/'report.json'),'status':report['status']},indent=2)+'\n');print(json.dumps({'directory':rel(D),'status':report['status'],'checks':checks},indent=2))

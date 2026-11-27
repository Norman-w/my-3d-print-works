#!/usr/bin/env python3
"""Frozen-scene host check for the isolated input-axis offset candidate.

No CAD edits. Y-axis separation covers the full non-input trigger motion.
Exact-coordinate plane tests distinguish contacts from empty Boolean results.
"""
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction as F
import argparse,hashlib,json,re,subprocess,sys,math

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2]
BIN='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
SNAP=ROOT/'output/cable-scene-export/20260927T091627124663Z/report.json'
sys.path.insert(0,str(ROOT/'analysis'))
from feeder_integration import classify
from exact_mesh import exact_area_and_links
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rel=lambda p:str(p.relative_to(ROOT))

def mesh(p):
 raw=re.findall(r'^\s*vertex\s+(\S+)\s+(\S+)\s+(\S+)\s*$',p.read_text(),re.M)
 assert raw and len(raw)%3==0
 v=[tuple(map(float,x))for x in raw]
 return {'min':[min(x[a]for x in v)for a in range(3)],'max':[max(x[a]for x in v)for a in range(3)],'triangles':len(v)//3},raw

def run(scad,name,folder,backend='Manifold'):
 source=folder/(name+'.scad');source.write_text(scad)
 target=folder/(name+'.stl');log=folder/(name+'.log')
 cmd=[BIN,'--hardwarnings','--backend',backend,'--export-format','asciistl','-D','ci_origin=[75,-85,5]','-o',str(target),str(source)]
 p=subprocess.run(cmd,capture_output=True,text=True);s=p.stdout+p.stderr;log.write_text(s)
 error='WARNING:' in s or 'ERROR:' in s
 empty='Current top level object is empty.' in s and not error
 row={'name':name,'command':cmd,'source':rel(source),'source_sha256':sha(source),'returncode':p.returncode,'log':rel(log),'log_sha256':sha(log),'native_empty':empty,'native_error_or_warning':error}
 if target.exists():row.update(file=rel(target),sha256=sha(target),bounds=mesh(target)[0])
 assert not error,row
 assert p.returncode==0 or empty,row
 return row

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--local-report',required=True);args=ap.parse_args()
 local=Path(args.local_report).resolve();lr=json.loads(local.read_text());sr=json.loads(SNAP.read_text())
 assert lr['status']=='OFFSET_SHOULDER_LOCAL_LIMITED_PASS' and lr['sources_stable']
 assert lr['design']['origin']==[75,-85,5]
 for name,want in lr['source_sha256'].items():assert sha(ROOT/name)==want,name
 sources={**lr['source_sha256'],rel(SNAP):sha(SNAP),rel(local):sha(local),rel(Path(__file__)):sha(Path(__file__))}
 for name,want in sr['source_sha256'].items():
  if name.startswith('cad/'):
   assert sha(ROOT/name)==want,name
   sources[name]=want
 for row in sr['parts']:assert sha(ROOT/row['file'])==row['sha256'],row['id']
 bycase={r['case']:r for r in lr['cases']}
 objects={};folder=OUT/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');folder.mkdir(parents=True)
 for part in ['body','cover']:
  row=bycase[part+'-0'];p=local.parent/(part+'-0.stl')
  assert row['one_closed_solid'] and sha(p)==row['stl_sha256']
  assert 'ci_origin=[75,-85,5]' in row['command']
  if part=='body':assert row['command'][row['command'].index('--backend')+1]=='CGAL'
  objects[part]={'file':rel(p),'sha256':sha(p),'bounds':mesh(p)[0],'bound_from_verified_local_report':True}
 # OpenSCAD `use` does not execute a library's top-level special-variable
 # assignment. The sweep's k=sec(180/72) requires this exact tessellation.
 pre='$fn=72;\nuse <'+str(ROOT/'cad/cable-trigger-input.scad')+'>\nuse <'+str(OUT.parent/'candidate.scad')+'>\n'
 for part,module in [('axis-sweep','offset_axis_sweep()'),('fixed-metal','offset_fixed_metal()')]:
  objects[part]=run(pre+'ci_to_cad()'+module+';\n',part,folder)
 axis=objects['axis-sweep']['bounds'];rr=6.6/math.cos(math.pi/72)
 expected={'min':[75-rr,-110.55,5-rr],'max':[75+rr,-64.25,5+rr]}
 assert all(abs(axis[end][i]-expected[end][i])<1e-9 for end in ['min','max']for i in range(3)),(axis,expected)
 excluded=[];hosts=[];broad=[];jobs=[]
 for row in sr['parts']:
  id=row['id']
  if 'cable-input-' in id or id=='feeder/cable-core-input':excluded.append({'id':id,'reason':'superseded old input instance'});continue
  if id in ['feeder/cable-housing','feeder/cable-core-route']:excluded.append({'id':id,'reason':'old route not representative; independent route candidate review'});continue
  hosts.append(row)
 for name,obj in objects.items():
  A=obj['bounds']
  for host in hosts:
   B=host['mesh']['bounds'];kind=host['motion']['kind'];id=host['id']
   gaps=[max(B['min'][a]-A['max'][a],A['min'][a]-B['max'][a])for a in range(3)]
   entry={'candidate':name,'host_id':id,'host_group':host['group'],'host_stl':host['file'],'host_sha256':host['sha256'],'host_motion':host['motion'],'axis_separations_mm':gaps}
   if kind!='fixed':
    # All retained non-input motions preserve Y; this gives continuous
    # separation even when X or Z changes. No hull of sampled poses needed.
    if kind in ['translate','radial']:assert host['motion']['axis'][1]==0
    elif kind=='spring':assert host['motion'].get('axis',[0,0,1])[1]==0
    elif kind=='output-wire':pass # same Y35.5 axis at every u, snapshot contract
    else:raise AssertionError((id,kind))
    assert gaps[1]>0,(name,id,gaps)
    entry.update(status='CONTINUOUS_Y_SEPARATION',separation_mm=gaps[1])
   elif max(gaps)>0:entry.update(status='FIXED_AABB_SEPARATION',separation_mm=max(gaps))
   else:
    entry['status']='NATIVE_INTERSECTION_REQUIRED'
    pname=name+'--'+id.replace('/','__')
    sc='intersection(){import('+json.dumps(str(ROOT/obj['file']))+');import('+json.dumps(str(ROOT/host['file']))+');}\n'
    jobs.append((entry,sc,pname))
   broad.append(entry)
 def probe(j):
  entry,sc,name=j;r=run(sc,name,folder);r.update(candidate=entry['candidate'],host_id=entry['host_id'])
  if r['native_empty']:r['classification']='NATIVE_EMPTY'
  else:
   p=ROOT/r['file'];b,raw=mesh(p)
   exact_y54=all(F(v[1])==F(-54)for v in raw)
   r['exact_all_vertices_on_Y_minus54']=exact_y54
   r['raw_geometry']=classify(p)
   if entry['candidate']=='body' and entry['host_id']=='feeder/beam-grip' and exact_y54:r['classification']='EXACT_INSTALLATION_PLANE_CONTACT_Y_MINUS54'
   elif entry['candidate']=='fixed-metal' and entry['host_id']=='feeder/hardware-fixed':
    # Do not erase nominal thread-major/minor overlaps. Require all four
    # separate components to lie at the existing nut seats, and check the
    # complement of those exact original nuts independently below.
    cs=r['raw_geometry']['components'];covered=[]
    for c in cs:
     choices=[(x,z)for x in [-16,16]for z in [-60,3]if c['bounds'][0][0]>=x-2.01 and c['bounds'][0][1]<=x+2.01 and c['bounds'][1]==[-39.0,-35.8] and c['bounds'][2][0]>=z-2.01 and c['bounds'][2][1]<=z+2.01]
     covered.append(choices)
    r['thread_component_seats']=covered
    r['classification']='DECLARED_FOUR_THREAD_ENGAGEMENTS_PENDING_COMPLEMENT_CHECK'if len(cs)==4 and all(len(x)==1 for x in covered)and len(set(x[0]for x in covered))==4 else'UNCLASSIFIED_SOLID_OR_CONTACT'
   else:r['classification']='UNCLASSIFIED_SOLID_OR_CONTACT'
  print(r['name'],r['classification'],flush=True);return r
 with ThreadPoolExecutor(max_workers=2)as pool:probes=list(pool.map(probe,jobs))
 hostfixed=next(x for x in hosts if x['id']=='feeder/hardware-fixed')
 helper='$fn=72;\nuse <'+str(ROOT/'cad/feeder-support-harness.scad')+'>\n'
 complement=run(helper+'intersection(){import('+json.dumps(str(ROOT/objects['fixed-metal']['file']))+');difference(){import('+json.dumps(str(ROOT/hostfixed['file']))+');sh_nuts();}}\n','metal-nonthread-complement',folder)
 # A deliberate +0.1 mm shift into the actual bearing face must be detected.
 beam=next(x for x in hosts if x['id']=='feeder/beam-grip')
 control=run('intersection(){translate([0,.1,0])import('+json.dumps(str(ROOT/objects['body']['file']))+');import('+json.dumps(str(ROOT/beam['file']))+');}\n','positive-bearing-face-penetration',folder)
 if not control['native_empty']:control['raw_geometry']=classify(ROOT/control['file'])
 for r in probes:
  if r['classification']=='DECLARED_FOUR_THREAD_ENGAGEMENTS_PENDING_COMPLEMENT_CHECK'and complement['native_empty']:r['classification']='DECLARED_FOUR_THREAD_ENGAGEMENTS_ONLY'
 stable=all(sha(ROOT/p)==h for p,h in sources.items())
 accepted={'NATIVE_EMPTY','EXACT_INSTALLATION_PLANE_CONTACT_Y_MINUS54','DECLARED_FOUR_THREAD_ENGAGEMENTS_ONLY'}
 good=stable and all(r['classification']in accepted for r in probes)and complement['native_empty']and not control['native_empty']and control['raw_geometry']['has_solid_or_unclassified_overlap']
 report={'status':'OFFSET_FIXED_INPUT_HOST_NOMINAL_BOUNDED_PASS'if good else'FAIL_OR_REVIEW_REQUIRED','source_sha256':sources,'sources_stable':stable,
  'origin':[75,-85,5],'local_report':rel(local),'local_report_sha256':sha(local),'scene_snapshot':rel(SNAP),'snapshot_sha256':sha(SNAP),'snapshot_instance_count':len(sr['parts']),
  'excluded_instances':excluded,'retained_scene_instances':len(hosts),'objects':objects,'broad_phase':broad,'native_probes':probes,'nonthread_complement':complement,'positive_control':control,
  'axis_envelope_tessellation':{'explicit_fn':72,'expected_global_bounds':expected,'asserted_bound_coordinates_within_mm':1e-9,'meaning':'The explicit $fn=72 matches the source sec(pi/72) radial expansion. Coordinate assertion checks export mapping, not an allowed collision tolerance.'},
  'scope':['New body/cover plus fixed hardware against source-bound non-input host meshes. Body reused only from the verified CGAL local export.','Axis envelope covers its declared coaxial all-float intervals, not arbitrary axis tilt or eccentric manufacturing error.','All retained non-input trigger motions preserve Y; positive Y gaps prove their continuous separation from these fixed input objects.','Spin parts are separate snapshot/display groups, not proof of an assembled downstream spin-head placement. All happen to be Y-separated even in their unshifted export coordinates.','Old input and old housing/core-route are explicitly excluded; revised route is owned by another report. Retention base/cap/lower remain present.','Plane contact is retained and proved by exact exported Y coordinates, never accepted merely for near-zero volume. Four M4 thread envelopes are retained and checked against the original captive nuts.'],
  'not_checked':['Input rotor continuous sweep (root/local work)','Tool corridors and maintenance sequences','New housing route','Noncoaxial pose, printed errors, force capacity, friction and physical assembly'],
  'adopted':False,'manufacturing_release':False,'physical_acceptance':False}
 (folder/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');(OUT/'latest.json').write_text(json.dumps({'directory':rel(folder),'report_sha256':sha(folder/'report.json')},indent=2)+'\n')
 print(report['status'],rel(folder),flush=True)
if __name__=='__main__':main()

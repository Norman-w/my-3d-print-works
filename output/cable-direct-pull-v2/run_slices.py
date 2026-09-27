from pathlib import Path
import sys,json,hashlib,datetime,concurrent.futures
B=Path(__file__).resolve().parent; ROOT=B.parents[1]
sys.path.insert(0,str(ROOT/'scripts'));import review_cable_slice as s
H='f76a83eeb95644bd3c856922b31da749cc47c083d688d271116f946493994588'
assert s.sha(B/'candidate.scad')==H
N=B/'runs/20260927T084134904834Z-f76a83eeb9';native=json.loads((N/'native-report.json').read_text());assert native['source_sha256_before']==native['source_sha256_after']==H
assert json.loads((N/'interpretation.json').read_text())['status']=='LOCAL_NOMINAL_CHECKS_PASS'
report_path=N/'slice-export-report.json'
parts=[]
for name in ['body','lever','terminal-cap','cover']:
 row=next(r for r in native['results']if r['name']==name); assert row['returncode']==0 and not row['warnings_or_errors']; f=Path(row['file']);assert s.sha(f)==row['sha256']
 parts.append(dict(id='feeder/cable-input-'+name,selector='cdp_'+name.replace('-','_'),file=str(f.relative_to(ROOT)),sha256=row['sha256'],role='printed',backend=row['backend']))
deps=[B/'candidate.scad',ROOT/'cad/parameters.scad',N/'native-report.json',N/'interpretation.json']+[N/(n+'.scad')for n in ['body','lever','terminal-cap','cover']]
export=dict(status='DIAGNOSTIC_CANDIDATE_EXPORT',source_sha256={str(p.relative_to(ROOT)):s.sha(p)for p in deps},parts=parts,diagnostic_candidate=dict(source=str((B/'candidate.scad').relative_to(ROOT)),source_sha256=H,purpose='Isolated direct-pull v2 Cx=-24 input adjuster delta[-2,2]; offline print diagnostics only',native_export=str(N/'native-report.json'),motion='cdp_angle(u); guide radius60/Cx-24; not u/60'),manufacturing_release=False,physical_acceptance=False)
if report_path.exists():assert json.loads(report_path.read_text())==export
else:s.dump(report_path,export)
# Reuse exact same emitted input geometry only, retaining original slice provenance.
reuses=[]
for name,stamp in [('terminal-cap','20260927T082206132152Z'),('cover','20260927T074227302558Z')]:
 part='cable-input-'+name;old=ROOT/'output/print-review/current-cable'/stamp/part;inv=json.loads((old/'invocation.json').read_text());row=next(p for p in parts if p['id']=='feeder/'+part);old_stl=ROOT/inv['input']['file'];new_stl=ROOT/row['file'];art=json.loads((old/'artifact-review.json').read_text())
 assert old_stl.read_bytes()==new_stl.read_bytes();assert inv['input']['sha256']==row['sha256'];assert inv['assumptions']['layer_height_mm']==.1 and inv['assumptions']['support']=='disabled';assert art['status']=='SLICE_ARTIFACT_IDENTITY_PASS';assert all(s.sha(ROOT/p)==h for p,h in inv['source_sha256_at_start'].items());assert all(s.sha(old/p)==h for p,h in inv['artifact_sha256'].items());assert all(s.sha(old/(p+'.json'))==h for p,h in inv['local_profile_sha256'].items())
 reuses.append(dict(part=part,current_native_stl=str(new_stl),current_native_stl_sha256=s.sha(new_stl),original_stl=str(old_stl),bytes_identical=True,original_slice_folder=str(old),evidence_sha256={p:s.sha(old/p)for p in ['invocation.json','artifact-review.json','plate_1.gcode','slice-review.3mf']},original_source_sha256=inv['source_sha256_at_start'],layer_height_mm=.1,support=False,scope='Print geometry/process evidence only; original invocation retained without altering source provenance. V2 terminal path direction is reviewed independently.'))
s.dump(B/'slice-reuse-proof.json',dict(current_candidate_sha256=H,status='BYTE_IDENTICAL_PRINT_GEOMETRY_REUSE_PROVEN',parts=reuses,manufacturing_release=False))
official=s.BAMBU.parent.parent/'Resources/profiles/BBL/machine';machine=json.loads((s.CONFIG/'machine.json').read_text());assert all(machine[f]==json.loads((official/f'Bambu Lab X1 Carbon 0.4 nozzle template {f}.json').read_text())[f]for f in s.FIELDS)
shared={n:s.sha(s.CONFIG/(n+'.json'))for n in ['machine','process','filament']}
O=B/'slices'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+H[:10]);O.mkdir(parents=True)
s.dump(O/'snapshot.json',dict(export_report=str(report_path),export_report_sha256=s.sha(report_path),source_sha256=export['source_sha256'],shared_profiles=shared,parts=['cable-input-body','cable-input-lever'],runner_sha256=s.sha(__file__),slicer_sha256=s.sha(ROOT/'scripts/review_cable_slice.py'),bambu_binary_sha256=s.sha(s.BAMBU)))
s.dump(B/'latest-slices.json',dict(folder=str(O),source_sha256=H));print('OUTPUT='+str(O),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
 results=list(pool.map(lambda p:s.run_one(p,export,report_path,O,shared,'off',.1),['cable-input-body','cable-input-lever']))
s.dump(O/'report.json',dict(status='OFFLINE_SLICES_GENERATED_REVIEW_REQUIRED'if all(r['status']=='SLICE_GENERATED_REVIEW_REQUIRED'for r in results)else'SLICE_BATCH_INCOMPLETE',parts=results,source_sha256=H,sent_to_printer=False,manufacturing_release=False))

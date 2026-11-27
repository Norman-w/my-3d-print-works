#!/usr/bin/env python3
"""Check paired measured forces. No sample set can auto-release this machine."""
import argparse,csv,hashlib,json,math,re
from pathlib import Path
from datetime import datetime
from decimal import Decimal

IDENTITY=('configuration_id','assembly_source_sha256','route_identity')
TEXT=('record_id',*IDENTITY,'spring_specimen_id','cable_specimen_id','orientation_id',
      'ball_state','air_state','spring_trace_ref','chain_trace_ref','observer','timestamp_utc')
NUMERIC=('gravity_cad_unit_x','gravity_cad_unit_y','gravity_cad_unit_z','output_u_mm',
 'output_u_uncertainty_mm','spring_force_min_N','spring_force_uncertainty_N',
 'chain_return_force_max_N','chain_force_uncertainty_N','fixture_unincluded_adverse_bound_N',
 'spring_trials','chain_trials','dwell_s','quasistatic_speed_mm_s')
NONNEG=('output_u_uncertainty_mm','spring_force_min_N','spring_force_uncertainty_N',
 'chain_force_uncertainty_N','fixture_unincluded_adverse_bound_N','dwell_s')
TRUE={'true','1','yes'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def evaluate(row,expected,base):
 errors=[];values={}
 for k in TEXT:
  if not str(row.get(k,'')).strip():errors.append('MISSING_'+k)
 for k in NUMERIC:
  try:
   x=float(row[k]);assert math.isfinite(x);values[k]=x
  except (ValueError,TypeError,KeyError,AssertionError):errors.append('INVALID_'+k)
 for k in IDENTITY:
  if not isinstance(expected.get(k),str) or not expected[k].strip():errors.append('UNBOUND_'+k)
  elif row.get(k)!=expected[k]:errors.append('MISMATCH_'+k)
 if not re.fullmatch(r'[0-9a-f]{64}',row.get('assembly_source_sha256','')):errors.append('INVALID_assembly_source_sha256')
 for k in ['core_taut','fixture_matches_spring_line']:
  if str(row.get(k,'')).lower() not in TRUE:errors.append('UNCONFIRMED_'+k)
 try:
  t=datetime.fromisoformat(row.get('timestamp_utc','').replace('Z','+00:00'))
  if t.tzinfo is None or t.utcoffset().total_seconds()!=0:errors.append('TIMESTAMP_NOT_UTC')
 except ValueError:errors.append('INVALID_timestamp_utc')
 for k in NONNEG:
  if k in values and values[k]<0:errors.append('NEGATIVE_'+k)
 for k in ['spring_trials','chain_trials']:
  if k in values and (values[k]<1 or values[k]!=int(values[k])):errors.append('INVALID_COUNT_'+k)
 for k in ['quasistatic_speed_mm_s']:
  if k in values and values[k]<=0:errors.append('NONPOSITIVE_'+k)
 if 'output_u_mm' in values and not 0<=values['output_u_mm']<=20:errors.append('OUTSIDE_REVIEWED_OUTPUT_STROKE')
 gkeys=['gravity_cad_unit_'+s for s in 'xyz']
 if all(k in values for k in gkeys) and abs(math.sqrt(sum(values[k]**2 for k in gkeys))-1)>.001:errors.append('GRAVITY_VECTOR_NOT_UNIT')
 evidence=[]
 for k in ['spring_trace_ref','chain_trace_ref']:
  p=(base/str(row.get(k,''))).resolve()
  if not p.is_file() or not p.stat().st_size:errors.append('MISSING_LOCAL_TRACE_'+k)
  else:evidence.append({'kind':k,'path':str(p),'sha256':sha(p)})
 result={'record_id':row.get('record_id'),'status':'INCOMPLETE_OR_INCONSISTENT','errors':errors,
 'evidence_files':evidence,'trace_content_reviewed':False}
 if errors:return result
 # Use exact decimal arithmetic for the declared force values, so a zero
 # boundary cannot become a positive result through binary roundoff.
 d=lambda k:Decimal(str(row[k]))
 f=d('spring_force_min_N')-d('spring_force_uncertainty_N')
 q=max(Decimal(0),d('chain_return_force_max_N')+d('chain_force_uncertainty_N'))+d('fixture_unincluded_adverse_bound_N')
 margin=f-q
 result.update(status='SAMPLE_POSITIVE_MARGIN' if margin>0 else 'SAMPLE_INSUFFICIENT_MARGIN',
  spring_lower_N=float(f),chain_upper_N=float(q),margin_N=float(margin),margin_N_exact_decimal=str(margin),output_u_mm=values['output_u_mm'],
  output_u_uncertainty_mm=values['output_u_uncertainty_mm'],
  scope='Only the supplied paired observations and their declared error bounds. No interpolation, continuous interval guarantee, dynamic release or service-life acceptance.')
 return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--csv',type=Path,required=True);p.add_argument('--configuration',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
 a=p.parse_args();expected=json.loads(a.configuration.read_text())
 schema_path=Path(__file__).resolve().parent.parent/'supplier-bounds/measurement-schema.json'
 schema=json.loads(schema_path.read_text());fields=[x['name'] for x in schema['fields']]
 assert set(fields)==set(TEXT)|set(NUMERIC)|{'core_taut','fixture_matches_spring_line'},'Assessor/schema mismatch'
 with a.csv.open(newline='') as f:
  reader=csv.DictReader(f);headers=reader.fieldnames or [];rows=list(reader)
 header_valid=len(headers)==len(set(headers)) and set(headers)==set(fields)
 results=[evaluate(r,expected,a.csv.parent) for r in rows]
 ids=[r.get('record_id') for r in rows];duplicates=sorted({x for x in ids if x and ids.count(x)>1})
 statuses={r['status'] for r in results}
 if not header_valid:status='INCOMPATIBLE_CSV_HEADER'
 elif not rows:status='NO_MEASUREMENTS'
 elif duplicates or 'INCOMPLETE_OR_INCONSISTENT' in statuses:status='INCOMPLETE_OR_INCONSISTENT'
 elif 'SAMPLE_INSUFFICIENT_MARGIN' in statuses:status='MEASURED_MARGIN_INSUFFICIENT_AT_RECORDED_CONDITION'
 else:status='RECORDED_SAMPLES_POSITIVE_ONLY'
 report={'status':status,'configuration_bound':all(isinstance(expected.get(k),str) and expected[k].strip() for k in IDENTITY),
 'record_count':len(rows),'header_matches_schema':header_valid,'duplicate_record_ids':duplicates,'results':results,
 'input_identity':{str(x.resolve()):sha(x) for x in [a.csv,a.configuration,Path(__file__),schema_path]},
 'overall_return_verified':False,'manufacturing_release':False,'physical_acceptance':False,
 'unproven':['Raw trace interpretation and calibration error bounds','Entire continuous stroke including startup and reversals','Every intended orientation, ball/air load and installed route','Cable tautness through actual release, speed, stop impact and single-ball function','Assembly geometry, strength, loosening and durability'],
 'note':'Measured whole-chain resistance already includes participating gravity and friction; do not add modeled gravity or guessed efficiency losses again.'}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'status':status,'records':len(rows),'overall_return_verified':False},ensure_ascii=False))
 return 0 if status=='RECORDED_SAMPLES_POSITIVE_ONLY' else 2
if __name__=='__main__':raise SystemExit(main())

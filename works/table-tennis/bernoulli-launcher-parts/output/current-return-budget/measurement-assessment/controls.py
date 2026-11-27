#!/usr/bin/env python3
"""Synthetic parser/boundary controls only; never physical measurements."""
from pathlib import Path
import importlib.util,tempfile,json,hashlib
sp=importlib.util.spec_from_file_location('assessor',Path(__file__).with_name('assess.py'))
m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
def main():
 with tempfile.TemporaryDirectory() as tmp:
  d=Path(tmp);(d/'synthetic.txt').write_text('Synthetic control. Not a measured force trace.\n')
  expected={'configuration_id':'SYNTHETIC_CONTROL_ONLY','assembly_source_sha256':'a'*64,'route_identity':'SYNTHETIC_ROUTE'}
  row={k:'synthetic' for k in m.TEXT};row.update({k:'0' for k in m.NUMERIC});row.update(expected)
  row.update(gravity_cad_unit_z='1',output_u_mm='10',spring_force_min_N='4',spring_force_uncertainty_N='.2',
   chain_return_force_max_N='2',chain_force_uncertainty_N='.1',fixture_unincluded_adverse_bound_N='.3',
   spring_trials='3',chain_trials='3',dwell_s='2',quasistatic_speed_mm_s='1',core_taut='true',fixture_matches_spring_line='true',
   spring_trace_ref='synthetic.txt',chain_trace_ref='synthetic.txt',timestamp_utc='2026-09-27T00:00:00Z')
  checks={};r=m.evaluate(row,expected,d);checks['positive_arithmetic_only']=r['status']=='SAMPLE_POSITIVE_MARGIN' and abs(r['margin_N']-1.4)<1e-12 and not r['trace_content_reviewed']
  x={**row,'spring_force_min_N':'2.5','spring_force_uncertainty_N':'.1'};checks['zero_margin_not_pass']=m.evaluate(x,expected,d)['status']=='SAMPLE_INSUFFICIENT_MARGIN'
  for name,patch in [('nan',{'spring_force_min_N':'nan'}),('negative_uncertainty',{'chain_force_uncertainty_N':'-.1'}),('slack_core',{'core_taut':'false'}),('wrong_configuration',{'configuration_id':'other'}),('missing_trace',{'chain_trace_ref':'missing.txt'}),('unbound_identity',{})]:
   e={} if name=='unbound_identity' else expected
   checks[name]=m.evaluate({**row,**patch},e,d)['status']=='INCOMPLETE_OR_INCONSISTENT'
  assert all(checks.values()),checks
  r={'status':'SYNTHETIC_ASSESSOR_CONTROLS_PASS','checks':checks,'scope':'Arithmetic and rejection controls, not tests on the mechanism','physical_measurement_count':0,'source_sha256':{str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path(__file__).with_name('assess.py')]}}
  Path(__file__).with_name('controls-report.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps(r['checks']))
if __name__=='__main__':main()

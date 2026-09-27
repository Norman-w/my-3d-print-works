#!/usr/bin/env python3
"""Export the explicitly listed baseline parts, without releasing manufacture.

The adjustable-guide alternative and unselected components are separate. Nothing
is arranged/sliced or submitted to a printer by this command.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/candidate-parts'
OPENSCAD='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
INSPECTOR=Path('/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py')
sys.path.insert(0,str(ROOT/'analysis'))
from feeder_integration import classify

def sources():
    # This is the BASELINE inventory. An unrelated alternative's edits must
    # not invalidate its meshes or imply that the alternative was included.
    inventory_path=ROOT/'docs/candidate-bom.json'
    inventory=json.loads(inventory_path.read_text())
    paths={inventory_path,Path(__file__).resolve()}
    pending=[ROOT/item['source'] for item in inventory['printed']]
    while pending:
        source=pending.pop().resolve()
        if source in paths: continue
        source.relative_to(ROOT)  # All current CAD dependencies are local.
        paths.add(source)
        for name in re.findall(r'\b(?:include|use)\s*<([^>]+)>',source.read_text()):
            pending.append(source.parent/name)
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    inventory=json.loads((ROOT/'docs/candidate-bom.json').read_text())
    spec=importlib.util.spec_from_file_location('mesh_inspector',INSPECTOR)
    inspector=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inspector)
    initial=sources()
    rows=[]
    for item in inventory['printed']:
        value=item['selector'].split('=',1)[1].strip('"').replace('_','-')
        filename=f'{item["id"].lower()}-{Path(item["source"]).stem}-{value}.stl'
        target=OUT/filename
        target.unlink(missing_ok=True)
        command=[OPENSCAD,'--hardwarnings','--backend','Manifold','--export-format','asciistl',
                 '-D',item['selector'],'-o',str(target),str(ROOT/item['source'])]
        result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
        log=result.stdout+result.stderr
        (OUT/(target.stem+'.log')).write_text(log)
        if result.returncode or 'WARNING:' in log or 'ERROR:' in log: raise RuntimeError(log)
        mesh=inspector.inspect(target,1e-6)
        components=classify(target)['components']
        ok=mesh['watertightByEdgeTopology'] and len(components)==1
        rows.append({**item,'artifact':str(target.relative_to(ROOT)),
                     'artifact_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
                     'mesh':mesh,'shared_vertex_components':len(components),
                     'mesh_checks_pass':ok})
        print(item['id'],ok,mesh['bounds']['size'])
    stable=initial==sources()
    passed=stable and all(row['mesh_checks_pass'] for row in rows)
    report={'status':'BASELINE_MESH_EXPORTS_ONLY_UNRELEASED' if passed else 'EXPORT_FAILED_OR_STALE',
            'source_sha256':initial,'sources_stable':stable,'parts':rows,
            'unique_part_files':len(rows),'listed_print_quantity':sum(row['quantity'] for row in rows),
            'units':'mm by source convention; STL carries no units',
            'orientation':'Assembly coordinates retained; no approved print-bed orientation',
            'includes_adjustable_guide_alternative':False,
            'unselected_components':inventory['unselected'],
            'physical_acceptance':'OPEN','manufacturing_release':False}
    target=ROOT/'output/analysis/candidate-inventory.json'
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(report['status'],target)
    return 0 if passed else 1

if __name__=='__main__': sys.exit(main())

"""Read coordinate contracts from an invocation's SHA-bound frozen inventory.

Never substitute today's inventory for a historical slice. Legacy low precision
echoes use the explicit known 45-degree coordinate family and source identity.
"""
from pathlib import Path
import copy, hashlib, json, math, re
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
LEGACY_INPUT_SHA='01d2b74807dd584a6dfe855fa36b9ef11929df49453812943dfd080756f98e84'
LEGACY_ROUTE_SHA='0dbe838a2a1d91f6bd3f73d3e2f6b7dfa51bcac1d97810fe4976585d72e60a66'
FROZEN_INVENTORIES=[ROOT/'output/cable-scene-export'/v/'inventory.json' for v in
                    ['20260927T071458613482Z','20260927T091627124663Z']]
def path(p):
    p=Path(p);return p if p.is_absolute() else ROOT/p
def sha(p):return hashlib.sha256(path(p).read_bytes()).hexdigest()

def frozen_scene(inv):
    report_path=path(inv['export_report'])
    if sha(report_path)!=inv['export_report_sha256']:
        raise ValueError('Invocation export-report identity changed')
    report=json.loads(report_path.read_text())
    source=inv.get('input') or inv.get('input_stl')
    matched=[r for r in report['parts'] if r.get('sha256')==source['sha256'] and r['id']=='feeder/'+inv['part']]
    if len(matched)!=1:
        raise ValueError('Slice input is not a unique instance of its frozen export')
    if report['status']=='CURRENT_SCENE_EXPORT_PASS':
        if not matched[0]['passed']:raise ValueError('Slice instance export did not pass')
    elif report['status']=='DIAGNOSTIC_CANDIDATE_EXPORT':
        candidate=report['diagnostic_candidate']
        if sha(candidate['source'])!=candidate['source_sha256']:
            raise ValueError('Frozen diagnostic candidate source changed')
    else:raise ValueError('Unsupported export state for a slice coordinate contract')
    expected=report.get('inventory_sha256') or report['source_sha256'].get('docs/cable-assembly-inventory.json')
    candidates=[report_path.parent/'inventory.json',*FROZEN_INVENTORIES]
    candidates=[p for p in candidates if p.is_file() and sha(p)==expected]
    if not candidates:raise ValueError('No SHA-bound frozen scene inventory; current inventory is not a substitute')
    inventory_path=candidates[0];inventory=json.loads(inventory_path.read_text())
    scene=copy.deepcopy(inventory['scene_contract'])
    scene['_slice_source_sha256']=report['source_sha256']
    # Only recover sqrt(.5) from a known frozen source, or that exact expression
    # in a hash-matching live source. Unknown near-45-degree axes are not snapped.
    s=math.sqrt(.5);exact=[[-s,0,s],[s,0,s],[0,1,0]]
    input_sha=report['source_sha256'].get('cad/cable-trigger-input.scad')
    input_path=ROOT/'cad/cable-trigger-input.scad'
    exact_basis=input_sha==LEGACY_INPUT_SHA or (input_path.is_file() and sha(input_path)==input_sha
        and bool(re.search(r'\bci_s\s*=\s*sqrt\(\s*\.5\s*\)\s*;',input_path.read_text())))
    if exact_basis:
        for key,value in zip(['basis_x','basis_y','basis_z'],exact):
            if not np.allclose(scene['ci'][key],value,rtol=0,atol=1e-6):
                raise ValueError('Coordinate basis disagrees with its source sqrt(.5) expression')
            scene['ci'][key]=value
    source_hashes=inv.get('source_sha256_at_start',{})
    mismatches=[name for name,h in source_hashes.items() if not path(name).is_file() or sha(name)!=h]
    evidence={'export_report':str(report_path),'export_report_sha256':sha(report_path),
        'frozen_inventory':str(inventory_path),'frozen_inventory_sha256':sha(inventory_path),
        'coordinate_source':'invocation-bound frozen inventory',
        'basis_precision_adapter':'verified source sqrt(.5) expression' if exact_basis else 'frozen numeric basis without snapping',
        'input_cad_sha256':report['source_sha256'].get('cad/cable-trigger-input.scad'),
        'current_whole_source_matches_historical':not mismatches,'historical_live_source_mismatches':mismatches,
        'scope':'Historical source drift is recorded, not rewritten or relabelled current. Slice artifacts still need identity checks.'}
    return scene,evidence

def input_matrix(scene):
    ci=scene['ci'];matrix=np.eye(4)
    matrix[:3,:3]=np.array([ci['basis_x'],ci['basis_y'],ci['basis_z']]).T
    matrix[:3,3]=ci['origin']
    if not np.isfinite(matrix).all() or not np.allclose(matrix[:3,:3].T@matrix[:3,:3],np.eye(3),atol=1e-10):
        raise ValueError('Invalid frozen input coordinate contract')
    return matrix

def input_point(p,scene):
    m=input_matrix(scene);return np.asarray(p)@m[:3,:3].T+m[:3,3]

def route_frame(scene):
    ci,cr=scene['ci'],scene['cr']
    # All currently supported families keep their third bend fixed. Recover
    # its analytic frame from source scalar datums, not rounded arc ECHO points.
    legacy=scene.get('_slice_source_sha256',{}).get('cad/cable-housing-route.scad')==LEGACY_ROUTE_SHA
    if any(key not in cr for key in ['nominal_side_run','nominal_input_run','nominal_apex_z']) and not legacy:
        raise ValueError('Missing route datums without the exact frozen legacy source identity')
    side=cr.get('nominal_side_run',195)
    radius=cr['arc_radius'];run=cr.get('nominal_input_run',100);apex_z=cr.get('nominal_apex_z',400)
    delta=ci.get('adjuster_delta',0)
    local=[ci['adjuster_overall_x'][0]-delta,ci['adjuster_seat_local'][1],ci['wire_z']]
    p=input_point(local,scene);q=np.array(cr['output_port'],float)
    previous=p-run*np.array(ci['basis_x'])+[0,side,0]
    apex=np.array([q[0],q[1],apex_z]);incoming=apex-previous;incoming/=np.linalg.norm(incoming)
    outgoing=q-apex;outgoing/=np.linalg.norm(outgoing);cosine=float(incoming@outgoing)
    theta=math.acos(max(-1,min(1,cosine)));normal=outgoing-incoming*cosine;normal/=np.linalg.norm(normal)
    centre=apex-incoming*radius*math.tan(theta/2)+normal*radius
    U,V=-normal,incoming
    return centre,U,V,np.cross(U,V),theta

def legacy_scene():
    """Compatibility default for old helper callers, bound to frozen source SHA."""
    p=FROZEN_INVENTORIES[0];inv=json.loads(p.read_text())
    report=json.loads((p.parent/'report.json').read_text())
    expected=report['inventory_sha256']
    if sha(p)!=expected or report['source_sha256']['cad/cable-trigger-input.scad']!=LEGACY_INPUT_SHA:
        raise ValueError('Legacy coordinate fixture identity changed')
    scene=copy.deepcopy(inv['scene_contract']);s=math.sqrt(.5)
    scene['_slice_source_sha256']=report['source_sha256']
    scene['ci'].update(basis_x=[-s,0,s],basis_y=[s,0,s],basis_z=[0,1,0])
    return scene

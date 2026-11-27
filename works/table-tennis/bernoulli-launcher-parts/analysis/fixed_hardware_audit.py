#!/usr/bin/env python3
"""Bounded keeper repair and actual-STL support/seam hardware audit.

No arbitrary small-volume waiver. An empty CSG result is required unless every
triangle lies on an explicitly named seating plane and volume is <1e-7 mm3.
The untouched root use-only baseline is preserved, not silently overwritten.
"""
from pathlib import Path
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
import re
import shutil
import struct
import subprocess
import sys
from feeder_integration import classify

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/fixed-hardware-audit'
EXE='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
CAD=ROOT/'cad/feeder-hardware-clearance.scad'
SPEC=importlib.util.spec_from_file_location('mesh_inspect','/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py')
MESH=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(MESH)

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def rel(path):return str(path.relative_to(ROOT))
def sources():
    pending=[CAD,ROOT/'cad/review-launcher-baseline33.scad',ROOT/'cad/feeder-frame-y-guide.scad'];seen=set()
    while pending:
        p=pending.pop().resolve()
        if p in seen:continue
        seen.add(p)
        pending.extend(p.parent/x for x in re.findall(r'\b(?:include|use)\s*<([^>]+)>',p.read_text()))
    seen.update([Path(__file__).resolve(),ROOT/'analysis/feeder_integration.py'])
    return {rel(p):sha(p) for p in sorted(seen)}

PRE='''include <../../cad/parameters.scad>
use <../../cad/feeder-hardware-clearance.scad>
use <../../cad/feeder-guide-revision.scad>
use <../../cad/feeder-supports.scad>
use <../../cad/feeder-body.scad>
use <../../cad/feeder-complete-hardware.scad>
use <../../cad/review-launcher-baseline33.scad>
use <../../cad/feeder-frame-y-guide.scad>
module audit_shafts(){
 for(y=[-40,40],z=[-72,-46,-10,16])
  translate([-8.2,y,z])rotate([0,90,0])cylinder(h=12,d=3,$fn=64);
 for(s=[-1,1],z=[-45,16])scale([s,1,1])
  translate([32,-14,z])rotate([0,90,0])cylinder(h=12,d=3,$fn=64);
}
module audit_bosses(){difference(){union(){body_split_bosses();body_mount_bosses();}
 body_split_fastener_cuts();body_side_cuts();}}
module audit_protected(){
 // Keep the three holes and full outer washer bearing footprints unchanged.
 for(z=[-10,0,10])translate([51,-17.51,z])rotate([-90,0,0])cylinder(h=4.02,d=7,$fn=72);
 // Both positive rear gib stroke stops remain exactly the old geometry.
 translate([45.9,-13.51,-6.6])cube([9.2,3,13.2]);
}
module audit_hex_key_drivers(){
 for(s=[-1,1],z=[-45,16])scale([s,1,1])
  hc_x_cylinder(47.05,-14,z,45,3/cos(180/72));
}
module audit_mount_withdrawal(){
 for(s=[-1,1])scale([s,1,1])hc_mount_sweep_local(false,0,35);
}
'''

def run(name,code,expected='empty',planes=(),prefix=PRE):
    scad=OUT/(name+'.scad');stl=OUT/(name+'.stl');stl.unlink(missing_ok=True)
    scad.write_text(prefix+code+'\n')
    cmd=[EXE,'--hardwarnings','--backend','CGAL','--export-format','asciistl','-o',str(stl),str(scad)]
    p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True);log=p.stdout+p.stderr
    (OUT/(name+'.log')).write_text(log)
    empty=not stl.exists() and 'Current top level object is empty' in log
    if 'ERROR:' in log or (p.returncode and not empty):raise RuntimeError(name+': '+log)
    info=classify(stl) if stl.exists() else {'triangle_count':0,'components':[]}
    points=[tuple(map(float,m)) for m in re.findall(r'^\s*vertex\s+(\S+)\s+(\S+)\s+(\S+)',stl.read_text(),re.M)] if stl.exists() else []
    # No arbitrary near-planar solid gets a pass. Exact named seating face only.
    contact=bool(points) and bool(planes) and all(any(abs(v[a]-value)<1e-8 for a,value in planes) for v in points)
    volume=sum(x['volume_mm3'] for x in info['components'])
    contact=contact and volume<1e-7
    warnings=[s for s in log.splitlines() if 'WARNING:' in s]
    # A mixed face/solid intersection must become an explicit failed case,
    # rather than aborting before the report records the solid obstruction.
    known=['EXPORT-WARNING: Exported object may not be a valid 2-manifold and may need repair',
           'WARNING: Object may not be a valid 2-manifold and may need repair!']
    if any(s not in known for s in warnings):raise RuntimeError(name+': '+log)
    solid=bool(points) and not contact
    passed=(not points or contact) if expected=='empty' else solid
    row={'id':name,'expected':expected,'passed':passed,'file':rel(stl) if stl.exists() else None,
         'command':cmd,'named_contact_planes':list(planes),'named_contact_only':contact,
         'warnings':warnings,
         'solid_or_unclassified':solid,'volume_mm3':volume,**info}
    if stl.exists():row['sha256']=sha(stl)
    print(name,passed,round(volume,9),flush=True)
    return row

def exact_topology(path):
    _,tris=MESH._read_triangles(path);links={};bad=[]
    for n,t in enumerate(tris):
        tri=[tuple(Fraction(v) for v in p) for p in t]
        a,b,c=tri;u=[b[k]-a[k] for k in range(3)];v=[c[k]-a[k] for k in range(3)]
        if not any([u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]):bad.append(n)
        # STL vertices are compared at their exact decoded values, no welding.
        for j,p in enumerate(t):
            q,r=t[(j+1)%3],t[(j+2)%3];g=links.setdefault(p,{})
            g.setdefault(q,set()).add(r);g.setdefault(r,set()).add(q)
    faults=[]
    for p,g in links.items():
        todo=[next(iter(g))];seen=set()
        while todo:
            q=todo.pop()
            if q not in seen:seen.add(q);todo.extend(g[q]-seen)
        if len(seen)!=len(g) or any(len(x)!=2 for x in g.values()):faults.append(p)
    return {'exact_zero_area_faces':bad,'non_ring_vertex_links':faults}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    before=sources();base=OUT/'baseline-inventory.json';inputs=OUT/'baseline-stls'
    # Preserve the original 33 meshes so a later integrated release cannot
    # silently change the baseline or make this bounded audit unreproducible.
    if not base.exists():
        current=ROOT/'output/launcher-final/report.json';inv=json.loads(current.read_text())
        inputs.mkdir(exist_ok=True)
        for r in inv['parts']:
            if r['role']=='printed':
                assert sha(ROOT/r['file'])==r['sha256']
                shutil.copyfile(ROOT/r['file'],inputs/Path(r['file']).name)
        shutil.copyfile(current,base)
    inv=json.loads(base.read_text());parts=[dict(r) for r in inv['parts'] if r['role']=='printed']
    for r in parts:
        r['original_file']=r['file'];r['file']=rel(inputs/Path(r['file']).name)
    identities={r['file']:sha(ROOT/r['file']) for r in parts}
    assert all(identities[r['file']]==r['sha256'] for r in parts),'Baseline STL identity mismatch'
    preserved={}
    for ext in ['scad','stl','json']:
        original=ROOT/f'output/launcher-fixed-hardware-audit/baseline.{ext}'
        copy=OUT/f'original-use-only-baseline.{ext}';shutil.copyfile(original,copy)
        preserved[rel(copy)]=sha(copy)
    rows=[];exports=[]
    for rear,label in [(False,'front'),(True,'rear')]:
        b=str(rear).lower();g=-28.5 if rear else 0
        old='revision_keeper_local();';new=f'hc_keeper_local({b});'
        mount=f'hc_mount_sweep_local({b},0,0);'
        sweep=f'hc_mount_sweep_local({b},20,0);'
        driver=f'translate([0,0,{-g}])intersection(){{hc_mount_drivers();translate([0,-100,-100])cube([100,200,200]);}}'
        for name,body,expected,planes in [
            ('old-mounted',f'intersection(){{{old}{mount}}}','solid',()),
            ('new-mounted',f'intersection(){{{new}{mount}}}','empty',()),
            ('old-removal',f'intersection(){{{old}{sweep}}}','solid',()),
            ('new-removal',f'intersection(){{{new}{sweep}}}','empty',()),
            ('driver',f'intersection(){{{new}{driver}}}','empty',()),
            ('wrong-screw-removal',f'intersection(){{{new}hc_mount_sweep_local({b},0,35);}}','solid',()),
            ('protected-seats',f'difference(){{intersection(){{{old}audit_protected();}}{new}}}','empty',()),
            ('own-hardware',f'intersection(){{{new}revision_hardware_local(0,.9);}}','empty',[(1,-17.5)]),
        ]:rows.append(run(label+'-'+name,body,expected,planes))
        e=run('keeper-'+label,new,'solid');p=ROOT/e['file'];mesh=MESH.inspect(p,1e-6);top=exact_topology(p)
        e['mesh']=mesh;e['topology']=top;e['component_count']=len(e['components'])
        e['passed']=e['passed'] and mesh['watertightByEdgeTopology'] and len(e['components'])==1 and not top['exact_zero_area_faces'] and not top['non_ring_vertex_links']
        reimp=run('keeper-'+label+'-reimport','intersection(){import('+json.dumps(p.name)+');cube([1000,1000,1000],center=true);}','solid',prefix='')
        e['boolean_reimport']=reimp;e['passed'] &= reimp['passed'];exports.append(e)
    # Prove the local continuous-sweep hardware is the source hardware, not a
    # self-consistent copy that accidentally omitted a flange/washer.
    helper='union(){for(s=[-1,1],z=[-45,16])scale([s,1,1])hc_mount_one_local(z);}'
    for name,a,b in [('source-minus-reference','feeder_mount_hardware();',helper),('reference-minus-source',helper,'feeder_mount_hardware();')]:
        rows.append(run(name,f'difference(){{{a}{b}}}'))
    rows.append(run('boss-shafts-default-facets','intersection(){audit_bosses();audit_shafts();}','solid',prefix=PRE+'$fn=0;\n'))
    rows.append(run('boss-shafts-explicit72','intersection(){audit_bosses();audit_shafts();}'))
    hosts='union(){'+''.join('import('+json.dumps(str(ROOT/r['file']))+');' for r in parts if r['family'] in ('positive-half','negative-half'))+'}'
    rows.append(run('actual-host-stls-shafts','intersection(){'+hosts+'audit_shafts();}'))
    # All 33 meshes participate: strictly separated AABBs are proven disjoint;
    # every other part receives a true CSG. This avoids an unnecessary whole
    # machine union and keeps the responsible body visible in the evidence.
    broad=[]
    for kind,tool,rad,x0,x1,expected in [
        ('oversize-driver-control','hc_mount_drivers();',2.11,47.05,92.05,'solid'),
        ('hex-key-driver','audit_hex_key_drivers();',1.51,47.05,92.05,'empty'),
        ('mount-screw-withdrawal-keepers-removed','audit_mount_withdrawal();',3.5,32,82,'empty')]:
        boxes=[[[x0,x1] if s>0 else [-x1,-x0],[-14-rad,-14+rad],[z-rad,z+rad]] for s in [-1,1] for z in [-45,16]]
        candidates=[];separated=[]
        for r in parts:
            if r['family']=='y-keeper':continue
            _,tris=MESH._read_triangles(ROOT/r['file']);lo,hi=MESH._bounds(tris)
            if any(all(hi[k]>=box[k][0] and lo[k]<=box[k][1] for k in range(3)) for box in boxes):candidates.append(r)
            else:separated.append(r['id'])
        imports='union(){'+('hc_keepers();' if kind!='mount-screw-withdrawal-keepers-removed' else '')+''.join('import('+json.dumps(str(ROOT/r['file']))+');' for r in candidates)+'}'
        planes=[(0,43.5),(0,-43.5)] if kind=='mount-screw-withdrawal-keepers-removed' else []
        rows.append(run('actual-33-'+kind,'intersection(){'+imports+tool+'}',expected,planes))
        broad.append({'case':kind,'aabb_candidates':[r['id'] for r in candidates],'strictly_separated':separated,
                      'keeper_handling':'removed' if kind=='mount-screw-withdrawal-keepers-removed' else 'replaced by current wrapper','tool_boxes_mm':boxes})
    # Source-independent old actual keeper mesh reproduces the genuine defect.
    keeperimports='union(){'+''.join('import('+json.dumps(str(ROOT/r['file']))+');' for r in parts if r['family']=='y-keeper')+'}'
    rows.append(run('actual-old-keeper-stls-mounts','intersection(){'+keeperimports+'feeder_mount_hardware();}','solid'))
    stable=before==sources() and all(sha(ROOT/p)==h for p,h in identities.items())
    good=stable and all(x['passed'] for x in rows+exports)
    report={'status':'LOCAL_KEEPER_REPAIR_AND_DIAGNOSTIC_AUDIT_PASS' if good else 'FAIL_OR_STALE',
      'source_sha256':before,'sources_stable':stable,'baseline_inventory_sha256':sha(base),
      'actual_print_stl_sha256':identities,'preserved_root_counterexample':preserved,
      'exports':exports,'cases':rows,'broad_phase':broad,
      'faceting_diagnosis':{'default_d3_4_hex_apothem_mm':1.7*math.cos(math.pi/6),'shaft_radius_mm':1.5,
         'actual_fn72_hole_apothem_mm':1.7*math.cos(math.pi/72),'physical_hole_change':False},
      'assembly_order':['Seat support nuts before installing side supports.',
        'Fit the four existing M3 support mounting screws and washers.',
        'Move each revised keeper from -Y onto its fixed bosses, then fit its own screws and jack.',
        'Use a straight 2.5 mm hex key; its 2.887 mm circumscribed diameter is contained in the tested 3.0 mm cylindrical approach envelope.',
        'For mount screw/washer removal, remove keeper screws and translate keeper at least 20 mm toward -Y first.'],
      'scope':['Only the keeper/mount interaction and the facet-entrypoint false positives are closed here.',
        'Continuous 20 mm straight keeper withdrawal against installed support screws is tested as swept cylinders.',
        'The 4.2 mm driver fails at the original keeper mounting bosses and is a retained positive control; use the tested 3.0 mm envelope for a 2.5 mm straight hex key.',
        'Old left cap screw interference is repaired by the independent new Y guide, not by this wrapper.',
        'Final new Y guide integration, as-printed fit, strength, preload and service-tool selection remain separate.'],
      'physical_acceptance':'OPEN'}
    (OUT/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(report['status'],flush=True)
    return 0 if good else 1

def support_service():
    """Only the added support service slot; no unrelated full-machine rerun."""
    OUT.mkdir(parents=True,exist_ok=True);before=sources();rows=[];exports=[];sections=[]
    # Preserved pre-service counterexamples and repaired keeper evidence.
    old_report=json.loads((OUT/'report.json').read_text())
    previous_keeper={r['id']:r['sha256'] for r in old_report['exports']}
    prior={rel(OUT/'report.json'):sha(OUT/'report.json')}
    for name in ['actual-33-stls-revised-keepers-driver','actual-33-mount-screw-withdrawal-keepers-removed']:
        p=OUT/(name+'.stl');prior[rel(p)]=sha(p)
    for side,label in [(1,'right'),(-1,'left')]:
        old=f'yg_{label}_support();';new=f'hc_support_clearance({side}){{{old}}}'
        rows.append(run('service-'+label+'-old-insertion',f'intersection(){{{old}audit_mount_withdrawal();}}','solid',[(0,side*43.5)]))
        rows.append(run('service-'+label+'-new-insertion',f'intersection(){{{new}audit_mount_withdrawal();}}','empty',[(0,side*43.5)]))
        rows.append(run('service-'+label+'-driver',f'intersection(){{{new}hc_mount_drivers();}}'))
        protected=f'''scale([{side},1,1])union(){{
          translate([0,-100,-100])cube([43.5,200,200]);
          translate([0,-10.24,-100])cube([100,150,200]);
        }}'''
        rows.append(run('service-'+label+'-protected-datums-nuts',f'difference(){{intersection(){{{old}{protected}}}{new}}}'))
        wings=f'''scale([{side},1,1])for(z=[10,-gate_spacing-10],x=[47.7,52.9])
          translate([x,-13.5,z-1.6])cube([1.4,4.89,3.2]);'''
        rows.append(run('service-'+label+'-continuous-load-wings',f'difference(){{union(){{{wings}}}{new}}}'))
        e=run('service-'+label+'-support',new,'solid');p=ROOT/e['file']
        e['mesh']=MESH.inspect(p,1e-6);e['topology']=exact_topology(p);e['component_count']=len(e['components'])
        e['passed'] &= e['mesh']['watertightByEdgeTopology'] and e['component_count']==1 and not e['topology']['exact_zero_area_faces'] and not e['topology']['non_ring_vertex_links']
        e['boolean_reimport']=run('service-'+label+'-reimport','intersection(){import('+json.dumps(p.name)+');cube([1000,1000,1000],center=true);}','solid',prefix='')
        e['passed'] &= e['boolean_reimport']['passed'];exports.append(e)
        for z,name in [(10,'front'),(-38.5,'rear')]:
            case=run('service-'+label+'-'+name+'-bearing-slice',f'intersection(){{{new}scale([{side},1,1])support_y_hole(51,{z},-13.49,.02,9);}}','solid')
            case['average_section_mm2']=case['volume_mm3']/.02
            case['interpretation']='Actual 0.02 mm slab average, not minimum area or stress acceptance.'
            sections.append(case)
    # The new child wrapper does not alter either already-checked keeper.
    for rear,label in [(False,'front'),(True,'rear')]:
        row=run('service-keeper-'+label,f'hc_keeper_local({str(rear).lower()});','solid')
        row['same_sha_as_pre_service_keeper']=row['sha256']==previous_keeper['keeper-'+label]
        row['passed'] &= row['same_sha_as_pre_service_keeper'];rows.append(row)
    stable=before==sources();passed=stable and all(x['passed'] for x in rows+exports+sections)
    report={'status':'KEEPER_AND_FIXED_SUPPORT_SERVICE_REPAIR_PASS' if passed else 'SERVICE_REPAIR_FAIL_OR_STALE',
       'source_sha256':before,'sources_stable':stable,'prior_evidence_sha256':prior,
       'cases':rows,'exports':exports,'bearing_slices':sections,
       'api':['hc_keepers() replaces the four original keeper instances.',
              'hc_support_clearance(1) yg_right_support();',
              'hc_support_clearance(-1) yg_left_support();'],
       'geometry_contract':{'service_cut_d_mm':7.5,'service_cut_x_local_mm':[47.05,92.05],
          'service_cut_y_max_mm':-10.25,'keeper_nut_seat_y_min_mm':-8.6,
          'nut_seat_separation_mm':1.65,'untouched_mount_spine_x_max_mm':43.5,
          'verified_solid_wings_per_mount_boss':2,'wing_size_xyz_mm':[1.4,4.89,3.2],
          'combined_wing_section_mm2':8.96,
          'front_local_lip_bore_gap_mm':6-math.sqrt(3.75**2-.5**2)-1.7},
       'decision':'Use local subtractive service slots; retain the four original mounting screws/washers/nuts. Reversed fasteners would change the captive seat and require a separate nut-wrench entry.',
       'assembly_order':['Load captured support nuts before fitting the side support.',
          'Insert the original M3 screws and washers along ±X through the new fixed-boss service corridors.',
          'Fit the revised keeper from -Y and then fit its own screws/jack.',
          'For complete support screw removal, first remove the keeper, then draw the support screw/washer out along ±X.'],
       'scope':['Continuous 35 mm screw/washer translation against the combined new Y support and service wrapper is checked.',
          'Guide/front/nut material and the main mounting spine remain unchanged by exact difference checks.',
          'Two full 1.4 x 3.2 mm solid wings per affected keeper boss remain continuously through 4.89 mm in Y; the locally thin upper lip is not the sole load path.',
          'The approximately 0.583 mm local lip is not assigned load-bearing capacity. No strength or print dimensional acceptance follows from section area.',
          'Only changed supports are rechecked here. Root integration owns the complete new machine and final export.',
          'No CAD outside the clearance library was changed; no printing or device operation occurred.'],
       'physical_acceptance':'OPEN'}
    target=OUT/'service-report.json';target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(report['status'],flush=True);return 0 if passed else 1

if __name__=='__main__':sys.exit(support_service() if '--support-service-only' in sys.argv else main())

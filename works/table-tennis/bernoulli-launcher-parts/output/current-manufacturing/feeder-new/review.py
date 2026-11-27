#!/usr/bin/env python3
"""Actual-archive and bounded toolpath audit; writes only feeder-new results."""
from pathlib import Path
import argparse, collections, csv, hashlib, importlib.util, io, json, math, os, sys
import numpy as np
from shapely.geometry import LineString, MultiPoint, Polygon, box
from shapely.ops import unary_union

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'analysis'),str(ROOT/'scripts')]
import cable_input_slice_review as g
import review_integrated_shell_slice as shell
from cable_slice_artifacts import normalization_review
from review_cable_slice import read_stl
from cable_structural_slice_review import inside
spec=importlib.util.spec_from_file_location('reuse_archive',ROOT/'output/current-manufacturing/feeder-reuse/review.py')
reuse=importlib.util.module_from_spec(spec);spec.loader.exec_module(reuse)
shell.np=np
NONPRINT={'Custom','Flush','Prime tower','Prime tower infill','Undefined',''}
NONMODEL=NONPRINT|{'Brim','Skirt'}
ERR=.002 # > parser arc sagitta .00125; circumscribe polygonal bead buffers below

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def rel(p):return str(Path(p).resolve().relative_to(ROOT))
def bbox(p):return [p.min(0).tolist(),p.max(0).tolist()]if len(p)else None
def corners(lo,hi):return np.array([[x,y,z]for x in [lo[0],hi[0]]for y in [lo[1],hi[1]]for z in [lo[2],hi[2]]])

def features(row):
    family=row['family'];side=-1 if 'left' in row['instance_id'] else 1
    result=[]
    def add(name,lo,hi,kind='functional_void',note='',pick=False):
        result.append(dict(name=name,lo=list(lo),hi=list(hi),kind=kind,note=note,pick=pick))
    def yy(name,x,z,y0,y1,w=.7,note=''):
        add(name,[x-w,y0,z-w],[x+w,y1,z+w],note=note,pick=True)
    if family in ['left-support','right-support']:
        for z in [0,-28.5]:
            add(f'carrier_channel_{z}',[43.9 if side>0 else -57.7,-4.4,z-3.9],[57.7 if side>0 else -43.9,4.4,z+3.9],note='Open -Y before gib/keeper; trees must be clipped into pieces.')
            for dz in [(-4.1,-2.5),(2.5,4.1)]:
                add(f'carrier_Y_datum_{z}_{dz}',[44.4 if side>0 else -57.2,4.48,z+dz[0]],[57.2 if side>0 else -44.4,4.52,z+dz[1]],'datum')
            for x in [47,51,55]:yy(f'carrier_pick_{z}_{x}',side*x,z,-25,3,1,'2x2 mm rectangular pick section; nominal access only, no grip/force claim.')
        for z0,z1 in [(-33.5,-27.5),(-2.5,3.5)]:
            add(f'frame_Y20_datum_{z0}',[53.6 if side>0 else -58.4,19.98,z0+.1],[58.4 if side>0 else -53.6,20.02,z1-.1],'datum')
        for z in [-29,-1]:yy(f'cap_M3_from_plus_Y_{z}',side*62.75,z,16.1,33,.7,'1.4x1.4 mm pick enters from +Y; stops 0.1 mm before nominal Y16 blind floor. The old Y14 start wrongly crossed intact floor material.')
        if side>0:add('X54_master_datum',[53.98,21.05,-34.9],[54.02,23.95,4.9],'datum')
    elif family=='y-cap':
        add('open_gib_nut_pockets',[53.35 if side>0 else -60.65,24.15,-33.65],[60.65 if side>0 else -53.35,31.15,3.65],note='Open -Y/upward in this pose; no support allowed in working pocket.')
        for x,z in [(55.5,-30),(55.5,.5),(62.75,-29),(62.75,-1)]:
            # Jack lower station is mean(-33.5,-27.5)=-30.5.
            if x==55.5 and z==-30:z=-30.5
            yy(f'M3_core_{x}_{z}',side*x,z,23,40,.65,'1.3x1.3 mm core; not full fastener-fit proof.')
    elif family=='frame-y-gib':
        for z0,z1 in [(-33.5,-27.5),(-2.5,3.5)]:
            add(f'work_tooth_{z0}',[54.3 if side>0 else -57.7,24.08,z0+.1],[57.7 if side>0 else -54.3,24.12,z1-.1],'datum')
    elif family=='y-keeper':
        z=-28.5 if 'rear' in row['instance_id'] else 0
        for dz in [-10,0,10]:yy(f'M3_core_{dz}',side*51,z+dz,-19,-9,.65,'Vertical core; nut pocket opens upward, inspect mouth before hardware.')
    elif family in ['inlet-rear','inlet-front']:
        rear=family=='inlet-rear'
        for x in [-43,43]:yy(f'M4_core_{x}',x,-112,-25 if rear else -1,0 if rear else 16,1,'2x2 mm through core; horizontal hole roof remains a bridge, fit not certified.')
        add('hose_throat_central_core',[-18,-20 if rear else 1.3,-122.8],[18,-1.3 if rear else 20,-101.2],note='Central open part of ID61 throat only, not complete curved liner surface.')
        if rear:
            for x in [-43,43]:yy(f'M4_nut_mouth_pick_{x}',x,-112,-25,-8.5,2,'4x4 mm rear-open pick envelope into AF7.4 nut mouth.')
            for x in [-10.5,10.5]:yy(f'M2_5_anchor_core_{x}',x,-142,-61,-39,.6,'1.2x1.2 mm axial core, keys/anchor through-hole; clean before hose/beam.')
            for x in [-20.5,20.5]:
                for z in [-148,-142,-136]:
                    add(f'strap_slot_pick_{x}_{z}',[x-.6,-60,z-.8],[x+.6,-40,z+.8],note='1.2x1.6 mm pick from -Y in each open 3mm textile slot, three stations only.',pick=True)
            add('collar_underside',[-49,-37,-123.1],[49,-1.1,-122.9],'external_support',note='Open split ring and ear undersides; clip external branches before assembly.')
            add('key_undersides',[-12,-54,-152.7],[12,-47.9,-152.5],'external_support',note='Exposed rear keys; avoid bearing-face damage during branch removal.')
    elif family=='inlet-backplate':
        for x in [-10.5,10.5]:yy(f'M2_5_core_{x}',x,-142,-59,-52,.6,'1.2x1.2 mm vertical core, direct from either face.')
    return result


def review(folder):
    inv=json.loads((folder/'invocation.json').read_text());family=inv['family']
    models,project,gcodehash,units=reuse.archive_models(folder/'slice-review.3mf')
    before={rel(folder/n):sha(folder/n)for n in ['invocation.json','slice-review.3mf','plate_1.gcode','machine.json','process.json','filament.json']}
    native=inv['native_result'];warnings=[p.get('warning_message','')for p in native['sliced_plates']]
    checks={'native_success':inv['return_code']==native['return_code']==0,'native_warning_empty':not any(warnings),
        'actual_quantity':len(models)==len(inv['inputs']),
        'actual_gcode_identity':gcodehash==sha(folder/'plate_1.gcode')==inv['artifact_sha256']['plate_1.gcode'],
        '3mf_identity':sha(folder/'slice-review.3mf')==inv['artifact_sha256']['slice-review.3mf'],
        'profile_identity':all(sha(folder/(n+'.json'))==h for n,h in inv['local_profile_sha256'].items()),
        'sources_current':all(sha(ROOT/p)==h for p,h in inv['source_sha256_at_start'].items()),
        'shared_profiles_untouched':inv['shared_profiles_untouched'],
        'actual_X1C_04_PETG':project.get('printer_model')=='Bambu Lab X1 Carbon'and project.get('nozzle_diameter')==['0.4']and project.get('filament_type')==['PETG'],
        'actual_process':project.get('layer_height')=='0.2'and project.get('wall_loops')=='4'and project.get('sparse_infill_density')=='25%',
        'support_mode_matches':project.get('enable_support')==('1'if inv['supports']=='supported'else'0'),
        'units_mm':units=='millimeter','no_scale_or_reflection':True,'intended_face_to_bed':True,'mesh_correspondence':True}
    R0=reuse.intended_rotation(inv['command']);states=[];items=[]
    for row in inv['inputs']:
        key=Path(row['file']).stem;obj=models[key];tri=read_stl(ROOT/row['file']);identity=normalization_review(tri,obj['vertices'],obj['faces'])
        sourceok=sha(ROOT/row['file'])==row['sha256'];nomeshrep=all(int(obj['repair_stats'].get(k,0))==0 for k in reuse.REPAIR_KEYS)
        identityok=sourceok and identity['status']=='BOUNDED_VERTEX_CONTRACTION_VERIFIED'and not identity['collapsed_source_triangle_indices']and len(tri)==len(obj['faces'])and nomeshrep
        M=np.array(obj['mapping']['current_cad_to_gcode_command']);R=M[:3,:3]
        checks['no_scale_or_reflection'] &=bool(np.max(abs(R.T@R-np.eye(3)))<1e-7 and abs(np.linalg.det(R)-1)<1e-7)
        checks['intended_face_to_bed'] &=bool(np.max(abs(R.T@[0,0,1]-R0.T@[0,0,1]))<1e-7)
        checks['mesh_correspondence'] &=identityok
        state=dict(instance_id=row['instance_id'],input=row,actual_mapping=obj['mapping'],normal_mesh=identity,
            no_reported_repairs=nomeshrep,source_identity=sourceok,identity_pass=identityok,features=[])
        for f in features(row):
            f=dict(f,instance_id=row['instance_id'],support_commands=0,model_commands=0,support_lines=[],model_lines=[])
            co=g.affine(corners(f['lo'],f['hi']),M);f['_poly']=MultiPoint(co[:,:2]).convex_hull;f['_z']=[float(co[:,2].min()),float(co[:,2].max())];f['_xy']=np.array(f['_poly'].bounds)
            if f['pick']:
                lo,hi=np.array(f['lo']),np.array(f['hi']);cand=tri[(tri.max(1)>=lo).all(1)&(tri.min(1)<=hi).all(1)]
                f['nominal_mesh_triangle_hits']=sum(shell.clipped_triangle_in_box(t,lo,hi)for t in cand)
                f['nominal_pick_center_inside_solid']=bool(inside((lo+hi)/2,tri))
                f['nominal_pick_clear']=not f['nominal_mesh_triangle_hits']and not f['nominal_pick_center_inside_solid']
            state['features'].append(f);items.append(f)
        states.append(state)
    machine=json.loads((folder/'machine.json').read_text());area=Polygon([list(map(float,v.split('x')))for v in machine['printable_area']]);excluded=Polygon([list(map(float,v.split('x')))for v in machine['bed_exclude_area']]);height=float(machine['printable_height'])
    counts=collections.Counter();violations=[];first=[];plotgroups=collections.defaultdict(list);supportrecords=[];bridges=[]
    allbbox=np.array([[math.inf]*3,[-math.inf]*3]);maxz=max(np.array(g.affine(read_stl(ROOT/s['input']['file']).reshape(-1,3),np.array(s['actual_mapping']['current_cad_to_gcode_command'])))[:,2].max()for s in states)
    selected=sorted(set([.2]+[round(max(.2,maxz*v)/.2)*.2 for v in [.15,.35,.6,.8,.98]]))
    for rec in g.extrusion_paths((folder/'plate_1.gcode').open()):
        counts[rec.feature]+=1
        if rec.feature in NONPRINT:continue
        support=rec.feature.startswith('Support');model=not support and rec.feature not in NONMODEL
        rr=(rec.width/2+ERR)/math.cos(math.pi/128)
        lo=rec.points.min(0)-[rr,rr,rec.height];hi=rec.points.max(0)+[rr,rr,0];allbbox[0]=np.minimum(allbbox[0],lo);allbbox[1]=np.maximum(allbbox[1],hi)
        line=None;foot=None
        def footprint():
            nonlocal line,foot
            if foot is None:
                line=LineString(rec.points[:,:2]);foot=line.buffer(rr,quad_segs=32)
            return foot
        if lo[0]<0 or lo[1]<0 or hi[0]>256 or hi[1]>256 or lo[2]<-1e-5 or hi[2]>height or (box(lo[0],lo[1],hi[0],hi[1]).intersects(excluded)and footprint().intersects(excluded)):
            violations.append(dict(line=rec.line,feature=rec.feature,bounds=[lo.tolist(),hi.tolist()]))
        if model and abs(rec.layer-.2)<1e-6:first.append(footprint())
        if model or support:
            if any(abs(rec.layer-z)<1e-6 for z in selected):plotgroups[round(rec.layer,6)].append((rec.feature,rec.points[:,:2]))
            for f in items:
                if model and not f['pick']:continue
                zlo,zhi=f['_z'];b=f['_xy']
                if hi[2]<zlo or lo[2]>zhi or hi[0]<b[0]or lo[0]>b[2]or hi[1]<b[1]or lo[1]>b[3]:continue
                if footprint().intersects(f['_poly']):
                    key='support'if support else'model';f[key+'_commands']+=1
                    if len(f[key+'_lines'])<16:f[key+'_lines'].append(rec.line)
        if support:supportrecords.append((rec.line,rec.layer,rec.height,rec.width,rec.points))
        if model and rec.feature=='Bridge':bridges.append({'line':rec.line,'layer':rec.layer,'path_length_mm':float(np.linalg.norm(np.diff(rec.points,axis=0),axis=1).sum()),'endpoint_chord_mm':float(np.linalg.norm(rec.points[-1]-rec.points[0]))})
    exact=[]
    # Resolve only the known narrow X54 master face using full actual STL triangles,
    # not by suppressing coarse corner flags or shaving contact layers.
    if family=='right-support':
        state=states[0];tri=read_stl(ROOT/state['input']['file']);M=np.array(state['actual_mapping']['current_cad_to_gcode_command']);invM=np.linalg.inv(M)
        face=unary_union([Polygon(t[:,1:])for t in tri[(abs(tri[:,:,0]-54)<1e-6).all(1)]if Polygon(t[:,1:]).area>1e-10]).intersection(box(21,-35,24,5));hits=[]
        for ln,layer,lh,width,pp in supportrecords:
            a=g.affine(pp,invM);b=g.affine(pp-[0,0,lh],invM)
            if min(a[:,0].min(),b[:,0].min())>54+1e-7 or max(a[:,0].max(),b[:,0].max())<54-1e-7:continue
            hit=LineString(a[:,1:]).buffer((width/2+ERR)/math.cos(math.pi/128),quad_segs=32).intersection(face)
            if hit.area>1e-8:hits.append({'line':ln,'area_mm2':hit.area,'bounds':list(hit.bounds)})
        exact.append({'datum':'X54 actual source triangles','support_intersections':hits,'positive_control_mm2':face.intersection(box(21.5,-34,22.5,-33)).area})
    for f in items:
        del f['_poly'];del f['_z'];del f['_xy']
    checks['bed_model_brim_support_bounds']=not violations
    if inv['supports']=='unsupported':checks['no_unrequested_support']=not supportrecords
    process_open=[]
    for state in states:
        for f in state['features']:
            if f['kind']=='datum'and f['support_commands']:
                if f['name']=='X54_master_datum'and exact and not exact[0]['support_intersections']:continue
                process_open.append({'instance':state['instance_id'],'feature':f['name'],'reason':'Support bead/slab intersects the declared working-datum band; cleaning/face preservation not closed.'})
            if f['pick']and(not f['nominal_pick_clear']or f['model_commands']):
                process_open.append({'instance':state['instance_id'],'feature':f['name'],'reason':'Declared pick core is not proved clear of both current STL and actual model bead/slab envelope.'})
            if f['name']=='open_gib_nut_pockets'and f['support_commands']:
                process_open.append({'instance':state['instance_id'],'feature':f['name'],'reason':'Actual support reaches the cap working pocket; removal and face condition need further review.'})
    # Source-corridor access is a local pick-tip condition, not proof that an
    # entire connected support tree can be pulled out or that same-PETG releases.
    if family=='inlet-rear':
        process_open.append({'instance':states[0]['instance_id'],'feature':'whole_external_tree','reason':'Local M4/M2.5/strap pick corridors are checked, but every connected tree branch under the collar/keys has not been given a complete cut-and-extraction sequence.'})
    figpath=folder/'layer-path-review.png'
    os.environ['MPLCONFIGDIR']=str(OUT/'matplotlib-config')
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    fig,axs=plt.subplots(2,3,figsize=(12,8),layout='constrained')
    for ax,z in zip(axs.flat,selected):
        for sup,col in [(False,'#2479a0'),(True,'#d88316')]:
            seg=[np.stack([p[:-1],p[1:]],axis=1)for feat,p in plotgroups[round(z,6)]if feat.startswith('Support')==sup]
            if seg:ax.add_collection(LineCollection(np.concatenate(seg),colors=col,linewidths=.45))
        ax.set_xlim(allbbox[0,0]-3,allbbox[1,0]+3);ax.set_ylim(allbbox[0,1]-3,allbbox[1,1]+3);ax.set_aspect('equal');ax.set_title(f'Z = {z:g} mm')
    fig.suptitle(f'{family}: actual model (blue), support (orange); nominal path review')
    fig.savefig(figpath,dpi=150);plt.close(fig)
    stable=all(sha(ROOT/p)==h for p,h in before.items())
    result={'family':family,'slice_folder':rel(folder),'quantity':len(states),'status':'BOUNDED_PATH_CHECKS_PASS_PHYSICAL_OPEN'if all(checks.values())and not process_open else'CURRENT_SLICE_REVIEW_FLAGGED',
        'checks':checks,'warnings':warnings,'sources_and_artifacts_stable':stable,'source_sha256_at_slice':inv['source_sha256_at_start'],'artifacts':before,
        'instances':states,'auditor_sha256':sha(__file__),'auditor_source':rel(__file__),'support_path_records':len(supportrecords),'feature_counts':dict(counts),'extrusion_bounds':allbbox.tolist(),
        'bed_violations':violations,'first_model_layer_footprint_mm2':float(unary_union(first).area),
        'bridge_paths':bridges,'exact_datum_checks':exact,'pending_review':process_open,'layer_image':rel(figpath),
        'resolved_process':{k:project.get(k)for k in ['printer_model','nozzle_diameter','filament_type','filament_settings_id','curr_bed_type','layer_height','wall_loops','sparse_infill_density','enable_support','support_type','support_top_z_distance','support_object_xy_distance']},
        'method':'Actual G-code positive extrusion with .00125 mm maximum arc sagitta, width/2+.002 mm circumscribed footprint and full layer slab; explicit 3MF affine maps. Feature box intersections are conservative. Core checks are finite declared pick paths, not entire-hole dimensional acceptance. Exact X54 face disambiguates only that specific datum.',
        'limits':['No physical support separation/grip/debris or dimensional/strength proof.','Bridge path length is not unsupported span.','Open channels require clipping tree branches before gibs, nuts, keeper, hose or host installation.','Textured PEI and Generic PETG remain analysis assumptions.'],
        'manufacturing_release':False,'physical_acceptance':False,'sent_to_printer':False}
    dump(folder/'current-review.json',result)
    print(json.dumps({'family':family,'status':result['status'],'failed_checks':[k for k,v in checks.items()if not v],'pending':len(process_open),'support':len(supportrecords)},ensure_ascii=False),flush=True)
    return result


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path);ap.add_argument('--families',nargs='*');args=ap.parse_args()
    run=args.run or ROOT/json.loads((OUT/'latest.json').read_text())['run']
    s=json.loads((run/'slice-report.json').read_text());reports=[]
    for f in s['folders']:
        folder=ROOT/f;family=json.loads((folder/'invocation.json').read_text())['family']
        reports.append(review(folder)if args.families is None or family in args.families else json.loads((folder/'current-review.json').read_text()))
    rows=[]
    for r in reports:
        f=ROOT/r['slice_folder']
        for state in r['instances']:
            p=[x for x in r['pending_review']if x['instance']==state['instance_id']]
            okay=all(r['checks'].values())and state['identity_pass']and r['sources_and_artifacts_stable']
            rows.append({'instance_id':state['instance_id'],'current_stl_sha256':state['input']['sha256'],
                'slice_folder':r['slice_folder'],'selected_3mf':rel(f/'slice-review.3mf'),'selected_3mf_sha256':sha(f/'slice-review.3mf'),'gcode':rel(f/'plate_1.gcode'),'gcode_sha256':sha(f/'plate_1.gcode'),
                'plate_quantity':r['quantity'],'identity_status':'CURRENT_STL_ACTUAL_3MF_FACE_BIJECTION'if state['identity_pass']else'ACTUAL_MESH_FLAGGED',
                'process_status':'BOUNDED_PATH_CHECKS_PASS_PHYSICAL_OPEN'if okay and not p else'CURRENT_SLICE_REVIEW_FLAGGED',
                'needs_reslice':not okay,'pending_review':bool(p),'reason':'Fresh current slice and bounded artifact/path checks completed; physical acceptance remains open.'if okay and not p else'; '.join(x['feature']+': '+x['reason']for x in p)if okay else'Artifact/native/bed/actual mesh check failed; see detailed report.',
                'old_report':None,'current_review':rel(f/'current-review.json'),'current_review_sha256':sha(f/'current-review.json')})
    report={'status':'CURRENT_13_INSTANCE_OFFLINE_REVIEW_COMPLETE_WITH_EXPLICIT_LIMITS','slice_run':rel(run),
        'counts':{'instances':len(rows),'plates':len(reports),'current_artifact_checks_pass':sum(not x['needs_reslice']for x in rows),'bounded_path_pass':sum(not x['needs_reslice']and not x['pending_review']for x in rows),'pending_review':sum(x['pending_review']for x in rows),'needs_reslice':sum(x['needs_reslice']for x in rows)},
        'mapping':rows,'plate_reports':[{'path':rel(ROOT/r['slice_folder']/'current-review.json'),'sha256':sha(ROOT/r['slice_folder']/'current-review.json')}for r in reports],
        'script_sha256':sha(__file__),'slice_script_sha256':sha(OUT/'slice.py'),'parser_sha256':sha(ROOT/'analysis/cable_input_slice_review.py'),
        'manufacturing_release':False,'physical_acceptance':False,'sent_to_printer':False}
    for d in [run,OUT]:dump(d/'report.json',report)
    # External mapping points into the frozen report. The report's internal
    # rows do not hash their own containing document (no circular identity).
    mapped=[dict(row,report_file=rel(run/'report.json'),report_sha256=sha(run/'report.json'))for row in rows]
    fields=['instance_id','current_stl_sha256','slice_folder','selected_3mf','selected_3mf_sha256','gcode','gcode_sha256','plate_quantity','identity_status','process_status','needs_reslice','pending_review','report_file','report_sha256','reason']
    buf=io.StringIO();w=csv.DictWriter(buf,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(mapped)
    for d in [run,OUT]:dump(d/'mapping.json',mapped);(d/'mapping.csv').write_text(buf.getvalue())
    print(json.dumps(report['counts']),flush=True)

if __name__=='__main__':main()

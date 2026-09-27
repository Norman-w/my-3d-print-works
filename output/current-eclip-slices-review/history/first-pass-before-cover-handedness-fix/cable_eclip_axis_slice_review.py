#!/usr/bin/env python3
"""Read emitted beads for the adopted Eclip input geometry; never slice or print.

Use FreeCAD Python, --folder ACTUAL_SLICE --output NEW_REVIEW_DIRECTORY.
The root artifact audit must exist and pass first. This reviewer intentionally
does not reuse the historical wrapped-wire or isolated lip-candidate ROIs.
"""
from pathlib import Path
import argparse, collections, datetime, hashlib, json, math, os, sys
import numpy as np
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'analysis'))
import cable_input_slice_review as parser
from cable_slice_contract import frozen_scene, input_matrix

SOURCE_SHA = 'cf2dc90ecea43e0bb5bf3b6fe68f9cf7adb8d47145b4b15577e5dd40f1679d8d'
ERROR = parser.ARC_ERROR + parser.BUFFER_ERROR
Z_EPS = 1e-6  # The declared mating plane is not a positive-thickness solid.
IGNORED = {'Custom', 'Prime tower', 'Prime tower infill', 'Flush', 'Undefined', ''}
ANCILLARY = {'Brim', 'Skirt'}

def path(p):
    p=Path(p); return p if p.is_absolute() else ROOT/p
def sha(p): return hashlib.sha256(path(p).read_bytes()).hexdigest()
def rel(p): return str(path(p).resolve().relative_to(ROOT))
def load(p): return json.loads(path(p).read_text())
def dump(p,v): Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def model(f): return f not in IGNORED|ANCILLARY and not f.startswith('Support')
def category(f): return 'support' if f.startswith('Support') else ('model' if model(f) else 'ancillary')
def close(a,b): return bool(np.allclose(a,b,atol=1e-8,rtol=0))
def full_hex(center,af):
    r=af/math.sqrt(3)
    return Polygon([(center[0]+r*math.cos(math.pi/6+k*math.pi/3),
                     center[1]+r*math.sin(math.pi/6+k*math.pi/3)) for k in range(6)])
def footprint(rows):
    # Circumscribed round polygon prevents the polygonal buffer itself from
    # under-covering the declared bead disk; chord error is separately added.
    return unary_union([r['line'].buffer((r['width']/2+ERROR)/math.cos(math.pi/96),
                                        resolution=24) for r in rows])

def validate_contract(ci):
    assert ci['motion_law']=='fixed-guide-direct-pull-v2'
    for name,val in [('origin',[75,-85,5]),('axis_bore_d',8.3),
        ('axis_root_relief_d_z',[9.2,[11.3,14.3]]),('bush_socket_af',12.4),
        ('fairlead_center',[-24,0,2]),('fairlead_core_radius',60),
        ('wire_terminal_local',[0,60,2]),('wire_d',1.5)]:
        if name=='axis_root_relief_d_z':
            assert close(ci[name][0],val[0]) and close(ci[name][1],val[1]),name
        else: assert close(ci[name],val),name
    assert ci['axis_design']=='HCDG8-30-grooved-pin-with-supplied-NETW7'

def wire_pose(u,ci):
    """Current CAD analytic tangent law, then rotate back into printed lever."""
    assert ci['input_u_domain'][0]<=u<=ci['input_u_domain'][1]
    R=ci['fairlead_core_radius']; B_R=ci['ball_orbit_radius']
    C=np.asarray(ci['fairlead_center'][:2]); P=np.asarray(ci['wire_terminal_local'][:2])
    def at(a):
        B=np.array([B_R*math.sin(a),B_R*math.cos(a)])
        v=B-C; d=float(np.linalg.norm(v)); assert d>=R
        phi=max(0., math.atan2(v[0],v[1])-math.acos(R/d))
        T=C+R*np.array([math.sin(phi),math.cos(phi)])
        length=ci['axial_leadin']+R*phi+math.sqrt(d*d-R*R)
        return phi,T,length
    rest=at(0)[2];lo,hi=map(math.radians,ci['angle_solve_deg'])
    assert at(lo)[2]-rest<=u+1e-8 and at(hi)[2]-rest>=u-1e-8
    for _ in range(48):
        a=(lo+hi)/2
        if at(a)[2]-rest<u:lo=a
        else:hi=a
    a=(lo+hi)/2; phi,T,L=at(a)
    rot=np.array([[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]])
    end=rot@T; length=float(np.linalg.norm(end-P)); near=P+(end-P)*min(12/length,1)
    return {'u_mm':u,'angle_deg':math.degrees(a),'guide_phi_deg':math.degrees(phi),
        'takeup_residual_mm':L-rest-u,'segment_length_mm':min(12.,length),
        'from_local':[*P,ci['wire_z']],'to_local':[*near,ci['wire_z']],
        'line':LineString([P,near])}

def envelope(name,zrange,shape,radius=0.,kind='prism',center_z=None):
    return {'name':name,'local_z_interval_mm':list(zrange),'shape':shape,'radius_mm':radius,
            'kind':kind,'center_z':center_z,'results':{c:{'minimum_bead_clearance_lower_mm':None,
                'possible_intrusion_commands':0,'examples':[],'closest_command':None}
                for c in ['model','support','ancillary']}}

def check_envelope(e,r):
    overlap=min(e['local_z_interval_mm'][1],r['zhi'])-max(e['local_z_interval_mm'][0],r['zlo'])
    if overlap<=Z_EPS:return
    rad=e['radius_mm']
    if e['kind'] in ['sphere','capsule']:
        dz=max(r['zlo']-e['center_z'],e['center_z']-r['zhi'],0)
        rad=math.sqrt(max(0,rad*rad-dz*dz))
    gap=r['line'].distance(e['shape'])-rad-r['width']/2-ERROR
    result=e['results'][r['category']]
    detail={'gcode_line':r['gcode_line'],'print_top_mm':r['top'],
            'local_z_slab_mm':[r['zlo'],r['zhi']],'feature':r['feature']}
    if result['minimum_bead_clearance_lower_mm'] is None or gap<result['minimum_bead_clearance_lower_mm']:
        result['minimum_bead_clearance_lower_mm']=gap; result['closest_command']=detail
    if gap<0:
        result['possible_intrusion_commands']+=1
        if len(result['examples'])<6:result['examples'].append({**detail,'clearance_lower_mm':gap})

def envelope_specs(part,ci):
    specs=[]; holes=[]; balls=[]
    def hole(name,c,z,nominal,metal):
        holes.append({'name':name,'center_local_xy':list(c),'local_z_interval_mm':z,
            'nominal_diameter_mm':nominal,'required_nominal_metal_diameter_mm':metal,'layers':[]})
        specs.append(envelope(name+'_metal',z,Point(c),metal/2))
    if part.endswith('body'):
        hole('body_through_axis',(0,0),[-12,-4],ci['axis_bore_d'],dict(ci['axis_pin_catalog_bounds'])['shaft_g6_d'][1])
        for i,c in enumerate([[-30,20],[74,20]]):
            hole('body_M3_'+str(i),c,[-12,8],3.4,3)
            specs.append(envelope('body_M3_nut_'+str(i),[-11.4,-9],full_hex(c,5.5)))
    elif part.endswith('cover'):
        hole('cover_main_axis',(0,0),[8,11.3],ci['axis_bore_d'],dict(ci['axis_pin_catalog_bounds'])['shaft_g6_d'][1])
        hole('cover_root_relief',(0,0),[11.3,14],ci['axis_root_relief_d_z'][0],9)
        specs[-1]['requirement_scope']='D9 is an engineering receiving bound, not a verified supplier root contour'
        for i,c in enumerate([[-30,20],[74,20]]):
            hole('cover_M3_'+str(i),c,[8,14],3.4,3)
            specs.append(envelope('cover_square_key_'+str(i),[8,9.5],box(c[0]-4,c[1]-4,c[0]+4,c[1]+4)))
    else:
        assert part.endswith('lever')
        af=dict(ci['bush_acceptance_requirements'])['AF'][1]
        specs.append(envelope('POM_full_hex_AF12_rotation30',[-3.5,7.5],full_hex((0,0),af)))
        for i,c in enumerate(ci['cap_bolts_local_xy']):
            hole('lever_M3_'+str(i),c,[-3.5,3.1],3.4,3)
            specs.append(envelope('lever_M3_nut_'+str(i),[-3,-.6],full_hex(c,5.5)))
        z=ci['wire_z']; br=ci['ball_d_candidate']/2; P=ci['wire_terminal_local'][:2]
        specs.append(envelope('terminal_ball_D5',[z-br,z+br],Point(P),br,'sphere',z))
        for u in [0,10,20,22]:
            w=wire_pose(u,ci); wr=ci['wire_d']/2
            e=envelope('wire_first12_u'+str(u),[z-wr,z+wr],w.pop('line'),wr,'capsule',z)
            e['motion']=w; specs.append(e); balls.append(w)
    return specs,holes,balls

def downface_review(part,faces,records,local_command,process):
    result=[]
    support_gap=float(process.get('support_top_z_distance') or 0)
    for d in faces:
        # Faces are extracted with +growth Z. XY coordinates remain local XY.
        plane=d['source_z']; poly=d['polygon']; growth=1 if not part.endswith('cover') else -1
        localz=plane*growth; printz=float((local_command@np.array([0,0,localz,1]))[2])
        nearby=[r for r in records if r['top']<=printz+.45 and r['top']>=printz-support_gap-.45
                and r['line'].distance(poly)<=r['width']/2+ERROR]
        above=[r for r in nearby if r['category']=='model' and r['top']>printz+Z_EPS]
        if not above:
            result.append({'name':d['name'],'source_local_z':localz,'nominal_print_plane_mm':printz,
                'area_mm2':d['area_mm2'],'status':'NO_MODEL_PATH_ABOVE_SOURCE_FACE'}); continue
        firsttop=min(r['top'] for r in above)
        first=[r for r in above if abs(r['top']-firsttop)<Z_EPS]
        previous_model=[r for r in nearby if r['category']=='model' and r['top']<firsttop-Z_EPS]
        prevtop=max((r['top'] for r in previous_model),default=None)
        previous_model=[r for r in previous_model if prevtop is not None and abs(r['top']-prevtop)<Z_EPS]
        support=[r for r in nearby if r['category']=='support' and r['top']<=printz+Z_EPS
                 and r['top']>=printz-support_gap-.15]
        prior=footprint(previous_model); support_poly=footprint(support); first_poly=footprint(first)
        missing=poly.difference(prior.union(support_poly))
        gaps=[]
        for r in first:
            intersection=r['line'].intersection(poly)
            if intersection.is_empty:continue
            for g in parser.lines_of(intersection.difference(prior.union(support_poly))):
                if g.length>.005:gaps.append(float(g.length))
        result.append({'name':d['name'],'source_local_z':localz,'nominal_print_plane_mm':printz,
            'area_mm2':d['area_mm2'],'bounds_local_xy':list(poly.bounds),
            'first_model_layer_top_mm':firsttop,'first_model_declared_slab_heights_mm':sorted(set(r['height']for r in first)),
            'previous_model_layer_top_mm':prevtop,'support_layer_tops_mm':sorted(set(r['top']for r in support)),
            'nearest_support_top_gap_from_plane_mm':printz-max((r['top']for r in support),default=printz) if support else None,
            'first_layer_bead_projection_area_on_face_mm2':first_poly.intersection(poly).area,
            'previous_model_projection_area_on_face_mm2':prior.intersection(poly).area,
            'support_projection_area_on_face_mm2':support_poly.intersection(poly).area,
            'face_area_without_model_or_selected_support_projection_mm2':missing.area,
            'longest_first_path_fragment_without_projected_underlay_mm':max(gaps,default=0),
            'first_model_features':dict(collections.Counter(r['feature']for r in first)),
            'status':'PROJECTED_UNDERLAY_MEASURED_NOT_STRENGTH_OR_CLEANUP_PASS'})
    return result

def run(folder,out):
    folder=path(folder).resolve(); out=path(out).resolve(); out.mkdir(parents=True,exist_ok=True)
    artifact=load(folder/'artifact-review.json'); inv=load(folder/'invocation.json')
    assert artifact['status']=='CURRENT_ECLIP_SLICE_ARTIFACT_IDENTITY_PASS' and artifact['sources_and_artifacts_stable']
    evidence=dict(artifact['evidence_sha256'])
    for p,h in evidence.items(): assert sha(p)==h,'Changed bound evidence: '+p
    for p in [__file__,folder/'artifact-review.json',ROOT/'analysis/cable_input_slice_review.py',ROOT/'analysis/cable_slice_contract.py']:
        evidence[rel(p)]=sha(p)
    scene,contract=frozen_scene(inv); ci=scene['ci']; validate_contract(ci)
    assert contract['input_cad_sha256']==SOURCE_SHA
    part=inv['part']; assert part==artifact['part']
    assert part in ['cable-input-body','cable-input-lever','cable-input-cover']
    matrix=np.asarray(artifact['input_local_to_command'],dtype=float); inverse=np.linalg.inv(matrix)
    growth=1 if part!='cable-input-cover' else -1
    assert close(matrix[2,:3],[0,0,growth]); assert close(matrix[:3,:3].T@matrix[:3,:3],np.eye(3))
    assert np.linalg.det(matrix[:3,:3])>0
    specs,holes,wires=envelope_specs(part,ci)
    cad_to_growth=np.linalg.inv(input_matrix(scene));cad_to_growth[2,:]*=growth
    faces=parser.downward_planar_faces(path(inv['input']['file']),cad_to_growth)
    records=[]; counts=collections.Counter(); layers=collections.defaultdict(list)
    for r in parser.extrusion_paths((folder/'plate_1.gcode').open()):
        counts[r.feature]+=1
        if r.feature in IGNORED:continue
        q=parser.affine(r.points,inverse)
        if np.ptp(q[:,2])>1e-5:raise ValueError('Non-planar emitted bead needs separate review')
        shift=inverse[:3,:3]@np.array([0,0,-r.height]); zlo,zhi=sorted([float(q[0,2]),float(q[0,2]+shift[2])])
        row={'line':LineString(q[:,:2]),'xy':q[:,:2],'zlo':zlo,'zhi':zhi,'width':r.width,
             'height':r.height,'top':round(r.layer,6),'gcode_line':r.line,'feature':r.feature,'category':category(r.feature)}
        records.append(row); layers[row['top']].append(row)
        for e in specs:check_envelope(e,row)
    for h in holes:
        for z,rows in sorted(layers.items()):
            chosen=[r for r in rows if r['category']=='model' and min(h['local_z_interval_mm'][1],r['zhi'])-max(h['local_z_interval_mm'][0],r['zlo'])>Z_EPS]
            if not chosen:continue
            radius=min(r['line'].distance(Point(h['center_local_xy']))-r['width']/2-ERROR for r in chosen)
            h['layers'].append({'print_top_mm':z,'clear_diameter_lower_mm':2*radius,
                'local_z_slab_mm':[min(r['zlo']for r in chosen),max(r['zhi']for r in chosen)]})
        h['minimum_clear_diameter_lower_mm']=min((r['clear_diameter_lower_mm']for r in h['layers']),default=None)
    down=downface_review(part,faces,records,matrix,artifact['resolved_process'])
    # Exact layer-side witnesses for thrust/bearing planes. This reports
    # emitted material and positions only, not real flatness or simultaneous contact.
    planes={'cable-input-body':[-12,-9,-4],'cable-input-lever':[-3.5,-.6,3.1,7.5],
            'cable-input-cover':[14,11.3,9.7,8]}[part]
    plane_rows=[]
    for z in planes:
        pz=float((matrix@np.array([0,0,z,1]))[2])
        plane_rows.append({'local_z':z,'nominal_print_z':pz,
            'model_print_tops_near_plane':sorted({r['top']for r in records if r['category']=='model' and abs(r['top']-pz)<.151}),
            'scope':'Layer schedule witness only; not face flatness, bearing area, strength or real axial play.'})
    plot_paths(out,part,layers,matrix,down,wires)
    for e in specs:
        shape=e.pop('shape')
        e['required_xy_geometry']={'type':shape.geom_type,'coordinates':list(shape.exterior.coords) if shape.geom_type=='Polygon' else list(shape.coords)}
    flags=[e['name']+': '+c+' possible bead-envelope intersection' for e in specs for c,v in e['results'].items()if v['possible_intrusion_commands']]
    result={'status':'BOUNDED_ECLIP_AXIS_PATH_REVIEW','part':part,'slice_folder':rel(folder),
        'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':SOURCE_SHA,
        'frozen_scene_contract':contract,'input_local_to_command':matrix.tolist(),
        'bead_xy_error_bound_mm':ERROR,'feature_counts':dict(counts),'envelopes':specs,
        'axis_and_fastener_holes':holes,'downward_faces':down,'layer_plane_witnesses':plane_rows,'flags':flags,
        'support_cleanup':{'status':'REQUIRES_PHYSICAL_REMOVAL_EVIDENCE','scope':
            'Compare below-source-face support projections; access from the build-plate side before any hardware assembly. This does not certify removal forces, trapped islands, damage, or post-cleanup surface dimensions.'},
        'limits':['All coordinates derive from frozen current ci and actual 3MF transform proved by the separate artifact audit.',
            'Declared line width and height form conservative slabs; positive clearance only bounds these commanded paths, not PETG shrinkage, sag, seams or tolerances.',
            'Negative lower clearance flags a possible overlap of an over-covering slab, not proven physical interference.',
            'Four wire poses are discrete nominal samples; only the first12mm from the ball in the current lever frame are reviewed.',
            'Underlay union includes nearby support projections across the declared air gap; area coverage is neither continuous physical contact nor bridge/strength/cleanup acceptance.',
            'The body remaining lateral stop/M6/host-bolt channels are reviewed separately by the root agent.',
            'POM material, pin root contour, actual ring/tool access and assembled axial tolerances remain separate acceptance gates.'],
        'evidence_sha256':evidence,'sources_and_artifacts_stable':all(sha(p)==h for p,h in evidence.items()),
        'manufacturing_release':False,'physical_acceptance':False,'sent_to_printer':False}
    assert result['sources_and_artifacts_stable']
    result['images_sha256']={rel(p):sha(p)for p in out.glob('*.png')}
    dump(out/'report.json',result)
    (out/'README.md').write_text('# Current Eclip actual path review\n\n'+part+' — bounded commanded-bead evidence, no manufacturing release.\n\n'+
        'Source: `'+SOURCE_SHA+'`; actual slice: `'+rel(folder)+'`.\n\n'+
        'Features: central axis/root relief or full AF12 POM hex, current M3 hardware; lever adds D5 ball and D1.5 first12mm core at u0/10/20/22. All source downward faces are checked for model/support projection below their first layer.\n\n'+
        ('Flags:\n\n'+'\n'.join('- '+f for f in flags) if flags else 'No possible required-metal/core overlap was found within the declared bead-envelope model.')+
        '\n\n`report.json` retains every layer measurement, underlay area and evidence SHA. `key-layers.png` shows actual emitted paths. Support projection does not prove removable support or a sound first suspended layer; ring tooling and physical dimensions remain open.\n')
    print(json.dumps({'part':part,'report':rel(out/'report.json'),'flags':flags,
        'downfaces':[{k:x.get(k)for k in ['source_local_z','area_mm2','support_projection_area_on_face_mm2',
            'longest_first_path_fragment_without_projected_underlay_mm']} for x in down]},ensure_ascii=False))
    return result

def plot_paths(out,part,layers,matrix,down,wires):
    os.environ.setdefault('MPLCONFIGDIR',str(out/'mpl'));import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    desired={'cable-input-body':[.1,2.7,3.0,3.1,7.9,8.0],
             'cable-input-lever':[.1,2.9,3.0,5.5,6.6,11.0],
             'cable-input-cover':[.1,2.7,2.8,4.3,4.4,6.0]}[part]
    chosen=[min(layers,key=lambda z:abs(z-p))for p in desired]
    fig,axs=plt.subplots(2,3,figsize=(15,10),layout='constrained')
    for ax,z in zip(axs.flat,chosen):
        if part.endswith('body'):ax.set_xlim(-45,95);ax.set_ylim(-130,35)
        elif part.endswith('cover'):ax.set_xlim(-14,14);ax.set_ylim(-14,14)
        else:ax.set_xlim(-17,17);ax.set_ylim(-15,76)
        ax.set_aspect('equal');ax.grid(alpha=.15);ax.set_title('Commanded print Z '+str(z)+' mm')
        ax.set_xlabel('Input local X / mm');ax.set_ylabel('Input local Y / mm')
    fig.canvas.draw()
    for ax,z in zip(axs.flat,chosen):
        scale=(ax.transData.transform([1,0])-ax.transData.transform([0,0]))[0]*72/fig.dpi
        for r in layers[z]:
            color='#da8e25' if r['category']=='support' else ('#2687a5' if r['category']=='model' else '#aaa')
            ax.add_collection(LineCollection([r['xy']],colors=color,linewidths=r['width']*scale,capstyle='round'))
        if part.endswith('lever'):
            for w in wires:
                a,b=w['from_local'],w['to_local'];ax.plot([a[0],b[0]],[a[1],b[1]],':',color='#ac287a',lw=.7)
    fig.suptitle(part+' actual emitted paths: blue=model, orange=support; no physical print acceptance')
    fig.savefig(out/'key-layers.png',dpi=150);plt.close(fig)

def selftest():
    ci=load('output/cable-scene-export/20260927T153058669616Z/inventory.json')['scene_contract']['ci']
    validate_contract(ci)
    ws=[wire_pose(u,ci)for u in [0,10,20,22]]
    assert close(ws[0]['to_local'],[-12,60,2])
    assert abs(ws[2]['angle_deg']-ci['angle_full_deg'])<1e-8
    assert all(abs(w['takeup_residual_mm'])<1e-10 for w in ws)
    assert full_hex((0,0),12).bounds[2]>5.99 and full_hex((0,0),12).bounds[3]>6.9
    e=envelope('roof',[-3,-.6],full_hex((0,0),5.5))
    r={'line':LineString([[-1,0],[1,0]]),'zlo':-.6,'zhi':-.5,'width':.42,
       'category':'model','gcode_line':1,'top':3.,'feature':'Bridge'}
    check_envelope(e,r); assert e['results']['model']['minimum_bead_clearance_lower_mm'] is None
    r['zlo']=-.7;check_envelope(e,r);assert e['results']['model']['possible_intrusion_commands']==1
    print(json.dumps({'selftest':'PASS','motion_samples':[{k:v for k,v in w.items()if k!='line'}for w in ws]},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder');p.add_argument('--output');p.add_argument('--self-test',action='store_true')
    args=p.parse_args()
    if args.self_test:selftest()
    else:
        if not args.folder or not args.output:p.error('--folder and --output are required')
        run(args.folder,args.output)

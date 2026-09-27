#!/usr/bin/env python3
"""Bounded native G-code review of four flat cable parts; never slices or prints.

Reuses the repository G-code parser, composes both recorded rigid transforms,
and measures declared bead footprints at actual emitted layers. The result is
nominal toolpath evidence, not printed dimensional or load acceptance.
"""
from pathlib import Path
import argparse, collections, hashlib, json, math, re, sys, zipfile
import xml.etree.ElementTree as ET
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Circle
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import review_integrated_shell_slice as shell
shell.np = np
PARTS = ['cable-input-cover', 'cable-output-cap', 'cable-route-cap', 'cable-route-lower']
NONMODEL = {'Custom', 'Flush', 'Brim', 'Skirt', 'Undefined', ''}
# Existing parser samples model arcs at <=1 mm and <=0.1 rad. The largest
# possible chord sagitta at their crossover is <0.0125 mm; round up here.
ARC_BOUND = .013


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p, d): Path(p).write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
def apply(M, p):
    p = np.asarray(p, float)
    return p @ M[:3, :3].T + M[:3, 3]
def affine(s):
    v = np.array(list(map(float, s.split())))
    a = np.eye(4); a[:3, :3] = v[:9].reshape(3, 3).T; a[:3, 3] = v[9:]
    return a

def mapping(folder, inv):
    ns = {'m': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
    with zipfile.ZipFile(folder / 'slice-review.3mf') as z:
        main = ET.fromstring(z.read('3D/3dmodel.model'))
        cfg = ET.fromstring(z.read('Metadata/model_settings.config'))
        objects = {o.attrib['id']: o for o in main.findall('./m:resources/m:object', ns)}
        builds = main.findall('./m:build/m:item', ns)
        assert len(builds) == 1, 'Single review instance required'
        b = builds[0]; oid = b.attrib['objectid']
        comps = objects[oid].findall('./m:components/m:component', ns)
        assert len(comps) == 1, 'Single component required'
        c = comps[0]
        part = next(o for o in cfg.findall('./object') if o.attrib['id'] == oid).find('./part')
        meta = {m.attrib['key']: m.attrib.get('value') for m in part.findall('./metadata')}
        offset = np.array([float(meta['source_offset_' + a]) for a in 'xyz'])
        C, B = affine(c.attrib['transform']), affine(b.attrib['transform'])
        S = np.eye(4); S[:3, 3] = -offset
        raw = re.search(r'^; extruder_offset = ([^\n]+)', (folder / 'plate_1.gcode').read_text(), re.M).group(1).split(',')[0]
        e = np.array([*map(float, raw.split('x')), 0.])
        E = np.eye(4); E[:3, 3] = -e
        oriented_to_command = E @ B @ C @ S
        assert np.allclose(oriented_to_command[2], [0,0,1,0], atol=1e-8), 'Arrange changed the reviewed build axis or bed plane'
        original = np.array(inv['cad_to_oriented'])
        combined = oriented_to_command @ original
        assert np.allclose(combined[:3, :3].T @ combined[:3, :3], np.eye(3), atol=1e-8)
        return combined, {'cad_to_oriented': original.tolist(), 'component': C.tolist(),
            'build': B.tolist(), 'source_offset': offset.tolist(), 'extruder_offset': e.tolist(),
            'oriented_to_command': oriented_to_command.tolist(), 'cad_to_command': combined.tolist(),
            'part_metadata': meta, 'mesh_stat': part.find('./mesh_stat').attrib}


def ci(p):
    x, y, z = p; s = math.sqrt(.5)
    return np.array([75+s*(-x+y), -82+z, 5+s*(x+y)])


def route_frame():
    # Same analytic contract as cr_vertices/cr_arc(3), with no rounded echo data.
    p = ci([-63, 60, 2]); q = np.array([-58., 35.5, 111.])
    a = p + 100*np.array([math.sqrt(.5), 0, -math.sqrt(.5)])
    prev = a + [0, 195, 0]; apex = np.array([q[0], q[1], 400.])
    incoming = apex-prev; incoming /= np.linalg.norm(incoming)
    outgoing = q-apex; outgoing /= np.linalg.norm(outgoing)
    c = np.dot(incoming, outgoing); theta = math.acos(c)
    normal = outgoing-incoming*c; normal /= np.linalg.norm(normal)
    A = apex-incoming*75*math.tan(theta/2)
    C = A + normal*75
    U, V = -normal, incoming
    return C, U, V, np.cross(U, V), theta


def specifications(part):
    holes, planes = [], []
    def hole(name, xyz, radius, end_radius=None, plane=None, polygon=None):
        holes.append(dict(name=name, center_cad=np.array(xyz, float), radius=radius,
                          end_radius=end_radius or radius, plane=plane, polygon_cad=polygon))
    if part == 'cable-output-cap':
        hole('M4 screw exit / washer recess', [-58, 43.2, 14.7], 3, 4.9, 3.3)
        for x in [-62.5, -51]: hole('M3 through at X'+str(x), [x,43.2,26], 1.7)
        planes = [('washer bearing Y39.9', 3.3)]
        levels = [.1, 3.3, 3.4, 4]
    elif part == 'cable-input-cover':
        hole('Axis bore / metal sleeve recess', ci([0,0,14]), 2.25, 4.15, 4.5)
        for x in [-30, 74]:
            polygon = np.array([ci([x+dx,20+dy,14]) for dx,dy in [(-4.2,-4.2),(4.2,-4.2),(4.2,4.2),(-4.2,4.2)]])
            hole('M3 / square seat x'+str(x), ci([x,20,14]), 1.7, 4.2, 4.3, polygon)
        planes = [('square seat local Z9.7',4.3),('sleeve seat local Z9.5',4.5)]
        levels = [.2,4.2,4.4,4.6,6]
    elif part == 'cable-route-lower':
        for x in [-73,-43]:
            for y in [-12,12]:
                r=5.8/(2*math.cos(math.pi/6))
                polygon = np.array([[x+r*math.cos(a),y+r*math.sin(a),84.7] for a in np.arange(6)*math.pi/3+math.pi/6])
                hole(f'M3 / hex seat {x},{y}', [x,y,84.7], 1.75, 2.9, 3.4, polygon)
        planes = [('nut bearing Z81.3',3.4)]
        levels = [.2,3.4,3.6,6.2]
    else:
        C,U,V,N,theta = route_frame()
        for a in [10,70,137]:
            for r in [63,87]:
                p=C+r*(math.cos(math.radians(a))*U+math.sin(math.radians(a))*V)+5*N
                hole(f'M3 a{a} r{r}',p,1.75)
        planes = [('groove onset local N3.1',1.9)]
        levels = [.2,1.8,2.0,2.2,5]
    return holes, planes, levels


def model(feature): return feature not in NONMODEL and not feature.startswith('Support')
def min_clear_radius(records, center, restrict=None):
    smallest = math.inf
    for rec in records:
        if not model(rec['feature']): continue
        if restrict and rec['feature'] not in restrict: continue
        p = rec['points'][:,:2]; a, d = p[:-1], np.diff(p,axis=0)
        denom = (d*d).sum(axis=1); good = denom > 1e-16
        if not good.any(): continue
        a,d,denom = a[good],d[good],denom[good]
        u=np.clip(((center-a)*d).sum(axis=1)/denom,0,1)
        dist=np.linalg.norm(a+d*u[:,None]-center,axis=1).min()
        smallest=min(smallest,float(dist-rec['width']/2-ARC_BOUND))
    return smallest

def footprint(records, predicate=model, extra=0):
    polys=[LineString(r['points'][:,:2]).buffer(r['width']/2+extra, resolution=8)
           for r in records if predicate(r['feature'])]
    return unary_union(polys)


def plotting(folder, out, part, levels, layers, holes, M, planes, groove=None):
    colors={'Outer wall':'#124c6d','Inner wall':'#3e8da5','Top surface':'#5c9a3d',
      'Bottom surface':'#599245','Bridge':'#d35b28','Sparse infill':'#a7b7bf',
      'Internal solid infill':'#94b989','Gap infill':'#9264a0','Support':'#d21d50','Support interface':'#d21d50'}
    levels=sorted(set(min(layers,key=lambda z:abs(z-v)) for v in levels))
    fig,axes=plt.subplots(2,3,figsize=(15,10),squeeze=False)
    allpts=np.concatenate([r['points'][:,:2]for rows in layers.values()for r in rows if model(r['feature'])])
    lo,hi=allpts.min(0)-2,allpts.max(0)+2
    for ax,z in zip(axes.flat,levels):
        ax.set_xlim(lo[0],hi[0]);ax.set_ylim(lo[1],hi[1]);ax.set_aspect('equal');ax.grid(alpha=.15)
        ax.set_xlabel('G-code X / mm');ax.set_ylabel('G-code Y / mm')
        ax.set_title(f'Layer top {z:g} mm | h={layers[z][0]["height"]:g}',fontsize=10)
    for ax in list(axes.flat)[len(levels):]:ax.axis('off')
    fig.suptitle(part+' | actual positive-extrusion bead paths\nBlue walls; green surfaces; orange Bridge; magenta nominal openings / groove centre',fontsize=12)
    fig.tight_layout(rect=[0,0,.99,.94]);fig.canvas.draw()
    for ax,z in zip(axes.flat,levels):
        scale=ax.transData.transform([1,0])[0]-ax.transData.transform([0,0])[0]
        for rec in layers[z]:
            f=rec['feature']
            if f in NONMODEL:continue
            p=rec['points'][:,:2]
            lc=LineCollection([p],colors=colors.get(f,'#59656b'),linewidths=rec['width']*scale*72/fig.dpi,
                              alpha=.9,capstyle='round',rasterized=True)
            ax.add_collection(lc)
        for hole in holes:
            c=apply(M,hole['center_cad'])[:2]
            radius=hole['end_radius'] if hole['plane'] is not None and z>hole['plane']+.01 else hole['radius']
            ax.add_patch(Circle(c,radius,fill=False,edgecolor='#bd3079',linestyle=':',lw=.65))
        if groove is not None:
            g=apply(M,groove)[:,:2];ax.plot(g[:,0],g[:,1],':',color='#bd3079',lw=.6)
    fig.savefig(out/'key-layers.png',dpi=180);plt.close(fig)
    # Detail at the most consequential pocket before/after its layer transition.
    if any(h['plane'] is not None for h in holes):
        first=holes[0];plane=first['plane'];c=apply(M,first['center_cad'])[:2]
        threshold=(first['radius']+first['end_radius'])/2
        opened=[z for z in sorted(layers)if min_clear_radius(layers[z],c)>threshold]
        select=sorted(set([max(z for z in layers if z<=plane+1e-6),
          min(z for z in layers if z>plane+1e-6)]+opened[:1]))
        fig,axs=plt.subplots(1,len(select),figsize=(5*len(select),5),squeeze=False)
        for ax,z in zip(axs.flat,select):
            lim=first['end_radius']+2
            ax.set_xlim(c[0]-lim,c[0]+lim);ax.set_ylim(c[1]-lim,c[1]+lim);ax.set_aspect('equal')
            ax.set_title(f'{first["name"]}\nLayer top {z:g} mm; nominal seat {plane:g} mm',fontsize=10)
            ax.grid(alpha=.18)
            ax.set_xlabel('G-code X / mm');ax.set_ylabel('G-code Y / mm')
        fig.tight_layout();fig.canvas.draw()
        for ax,z in zip(axs.flat,select):
            scale=ax.transData.transform([1,0])[0]-ax.transData.transform([0,0])[0]
            for r in layers[z]:
                if r['feature']in NONMODEL:continue
                if np.any(r['points'][:,:2].min(0)>c+lim+1) or np.any(r['points'][:,:2].max(0)<c-lim-1):continue
                ax.add_collection(LineCollection([r['points'][:,:2]],colors=colors.get(r['feature'],'#59656b'),
                  linewidths=r['width']*scale*72/fig.dpi,capstyle='round'))
            for rad in [first['radius'],first['end_radius']]:ax.add_patch(Circle(c,rad,fill=False,color='#bd3079',linestyle=':',lw=.8))
        fig.savefig(out/'critical-seat.png',dpi=180);plt.close(fig)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--folder',type=Path,required=True)
    args=parser.parse_args();folder=args.folder.resolve();inv=json.loads((folder/'invocation.json').read_text())
    assert inv['part']in PARTS and inv['status']=='SLICE_GENERATED_REVIEW_REQUIRED'
    expected=inv['source_sha256_at_start']
    assert all(sha(ROOT/p)==h for p,h in expected.items()),'Source snapshot drift'
    assert sha(ROOT/inv['input']['file'])==inv['input']['sha256']
    assert sha(inv['oriented']['file'])==inv['oriented']['sha256']
    for n,h in inv['artifact_sha256'].items():assert sha(folder/n)==h
    out=folder/'flat-path-review';out.mkdir(exist_ok=True)
    M,mapdata=mapping(folder,inv);holes,planes,levels=specifications(inv['part'])
    repair_flags={k:v for k,v in mapdata['mesh_stat'].items()if k!='face_count'and int(v)!=0}
    assert not repair_flags, '3MF contains mesh repair flags'
    layers=collections.defaultdict(list);counts=collections.Counter();widths=collections.defaultdict(list)
    for z,lh,feature,width,p in shell.paths(folder/'plate_1.gcode'):
        if abs(p[:,2].max()-z)>1e-5 or abs(p[:,2].min()-z)>1e-5:
            if model(feature) or feature.startswith('Support'):raise AssertionError('Nonplanar deposition requires separate review')
        layers[round(z,6)].append({'height':lh,'feature':feature,'width':width,'points':p})
        counts[feature]+=1;widths[feature].append(width)
    holes_out=[]
    for h in holes:
        center=apply(M,h['center_cad'])[:2];per=[]
        for z,rows in sorted(layers.items()):
            if not any(model(r['feature'])for r in rows):continue
            clear=min_clear_radius(rows,center)
            per.append({'layer_top_mm':z,'layer_bottom_mm':z-rows[0]['height'],
                        'inscribed_clear_radius_lower_bound_mm':clear})
        initial_core=h['radius']-.2
        result={'name':h['name'],'center_cad':h['center_cad'].tolist(),'command_xy':center.tolist(),
                'nominal_through_radius':h['radius'],'nominal_recess_inscribed_radius':h['end_radius'],
                'nominal_seat_print_height':h['plane'],'inset_through_core_radius':initial_core,
                'inset_through_core_clear_all_layers':all(r['inscribed_clear_radius_lower_bound_mm']>=initial_core for r in per),
                'min_inscribed_clear_radius_lower_bound_mm':min(r['inscribed_clear_radius_lower_bound_mm']for r in per),
                'layers':per}
        if h['plane']is not None:
            threshold=(h['radius']+h['end_radius'])/2
            opened=[r for r in per if r['inscribed_clear_radius_lower_bound_mm']>threshold]
            transition=opened[0]if opened else None
            result['first_recess_layer']=transition
            result['actual_toolpath_seat_height_mm']=transition['layer_bottom_mm']if transition else None
            result['seat_height_delta_mm']=transition['layer_bottom_mm']-h['plane']if transition else None
            # Final layer is the outward opening. Evaluate its exact polygon
            # (or circular nominal cross section), eroded by 0.2 mm only.
            nominal=Polygon(apply(M,h['polygon_cad'])[:,:2]) if h['polygon_cad']is not None else Point(center).buffer(h['end_radius'],resolution=96)
            safe=nominal.buffer(-.2)
            fp=footprint(layers[max(layers)],extra=ARC_BOUND)
            result['final_recess_inset_0p2_model_bead_overlap_mm2']=safe.intersection(fp).area
        holes_out.append(result)
    support_count=sum(v for k,v in counts.items()if k.startswith('Support'))
    C,U,V,N,theta=route_frame()
    controls={'cable-input-cover':ci([8,0,14]),'cable-output-cap':np.array([-58,43.2,22]),
              'cable-route-cap':C+75*U+5*N,'cable-route-lower':np.array([-73,-40,84.7])}
    control=apply(M,controls[inv['part']])
    control_radius=min_clear_radius(layers[min(layers)],control[:2])
    assert control_radius<.1,'Known first-layer solid failed deposition positive control'
    plane_out=[{'name':name,'nominal_print_height_mm':h,
                'nearest_emitted_top_mm':min(layers,key=lambda z:abs(z-h)),
                'nearest_top_error_mm':min(abs(z-h)for z in layers)}for name,h in planes]
    extra={};groove=None
    if inv['part']=='cable-output-cap':
        c=apply(M,holes[0]['center_cad'])[:2];z=min(layers,key=lambda z:abs(z-3.3))
        annulus=Point(c).buffer(4.7,resolution=96).difference(Point(c).buffer(3.2,resolution=96))
        fp=footprint(layers[z])
        extra['bearing_annulus_path_coverage']={'layer_top_mm':z,'nominal_annulus_radii_mm':[3.2,4.7],
          'covered_area_fraction':annulus.intersection(fp).area/annulus.area,
          'note':'Declared-width round footprint union on critical surface, excluding a 0.2 mm edge band; not solid volume or load strength.'}
    if inv['part']=='cable-route-cap':
        C,U,V,N,theta=route_frame();steps=math.ceil(math.degrees(theta)/2)
        local=np.array([[75,-15,0]]+[[75*math.cos(a),75*math.sin(a),0]for a in np.linspace(0,theta,steps+1)])
        groove=C+local[:,0,None]*U+local[:,1,None]*V
        groove=np.vstack([groove,[-58,35.5,126]])
        cmd=apply(M,groove)
        assert np.ptp(cmd[:,2])<1e-6
        gline=LineString(cmd[:,:2]);z=max(layers)
        core=gline.buffer(2.65,resolution=24)
        fp=footprint(layers[z],extra=ARC_BOUND)
        extra['groove_final_opening']={'layer_top_mm':z,'nominal_half_groove_radius_mm':3.1,
          'tested_continuous_centerline_tube_radius_mm':2.65,'model_bead_overlap_mm2':core.intersection(fp).area,
          'method':'Continuous polyline tube over full source-derived groove, including inlet and outlet; 0.45 mm inward guard permits faceting and layer contour sampling.',
          'groove_centerline_cad':groove.tolist(),'last_layer_model_feature_counts':dict(collections.Counter(r['feature']for r in layers[z]if model(r['feature'])))}
        # Check the full nominal OD5 housing half-envelope, not only its final
        # visible slot. At each deposited layer use its closest height to the
        # housing axis, conservatively testing the whole declared bead slab.
        axis_z=float(cmd[0,2]);housing=[]
        for z,rows in sorted(layers.items()):
            lower=z-next(r['height']for r in rows if model(r['feature']))
            dz=max(lower-axis_z,axis_z-z,0.)
            if dz>=2.5:continue
            radius=math.sqrt(2.5**2-dz**2)
            region=gline.buffer(radius,resolution=24)
            hit=region.intersection(footprint(rows,extra=ARC_BOUND)).area
            housing.append({'layer_bottom_mm':lower,'layer_top_mm':z,
                            'housing_xy_radius_mm':radius,'model_bead_overlap_mm2':hit})
        extra['groove_nominal_OD5_housing_clearance']={'all_layer_slabs_clear':all(r['model_bead_overlap_mm2']<1e-5 for r in housing),
            'method':'Continuous route centre polyline; full emitted layer slabs; nominal OD5 envelope and bead width plus chord bound.',
            'layers':housing}
    plotting(folder,out,inv['part'],levels,layers,holes,M,planes,groove)
    flags=[]
    for h in holes_out:
        if not h['inset_through_core_clear_all_layers']:flags.append(h['name']+': inset through-core bead intrusion')
        if h.get('final_recess_inset_0p2_model_bead_overlap_mm2',0)>1e-5:flags.append(h['name']+': final inset recess bead intrusion')
        if abs(h.get('seat_height_delta_mm')or 0)>.051:flags.append(h['name']+': seat layer quantization exceeds 0.05 mm')
    if extra.get('groove_final_opening',{}).get('model_bead_overlap_mm2',0)>1e-5:flags.append('Final inset groove bead intrusion')
    if not extra.get('groove_nominal_OD5_housing_clearance',{}).get('all_layer_slabs_clear',True):flags.append('Nominal OD5 housing overlaps a declared model bead slab')
    if support_count:flags.append('Support paths exist: further extraction review required')
    report={'status':'BOUNDED_TOOLPATH_REVIEW_FLAGS'if flags else'BOUNDED_TOOLPATH_REVIEW_NO_NEW_FLAGS',
      'part':inv['part'],'scope':'Actual emitted G-code layers and declared bead envelopes for specified openings only.',
      'flags':flags,'mapping':mapdata,'input_sha256':inv['input']['sha256'],
      'oriented_sha256':inv['oriented']['sha256'],'gcode_sha256':sha(folder/'plate_1.gcode'),
      '3mf_sha256':sha(folder/'slice-review.3mf'),'invocation_sha256':sha(folder/'invocation.json'),
      'script_sha256':sha(__file__),'parser_sha256':sha(ROOT/'scripts/review_integrated_shell_slice.py'),
      'source_sha256_at_review':expected,'layer_count':len(layers),'layer_tops_mm':sorted(layers),
      'emitted_layer_steps_mm':sorted(set(round(v,6)for v in np.diff([0]+sorted(layers)))),
      'declared_path_heights_mm':sorted(set(r['height']for rows in layers.values()for r in rows if model(r['feature'])or r['feature'].startswith('Support'))),
      'declared_path_heights_by_feature_mm':{f:sorted(set(r['height']for rows in layers.values()for r in rows if r['feature']==f))for f in counts},
      'height_interpretation':'Emitted layer steps measure consecutive Z tops. Native Bridge paths declare a 0.4 mm bead height even on 0.1/0.2 mm layers; this is recorded separately and is not a 0.4 mm layer-step failure.',
      'positive_extrusion_path_counts':dict(counts),
      'declared_line_width_ranges_mm':{k:[min(v),max(v)]for k,v in widths.items()},
      'support_path_count':support_count,'critical_planes':plane_out,'openings':holes_out,**extra,
      'solid_positive_control':{'cad_point':controls[inv['part']].tolist(),'command_point':control.tolist(),
          'layer_top_mm':min(layers),'signed_clear_radius_bound_mm':control_radius,
          'detected_material_within_0p1_mm':control_radius<.1},
      'source_geometry_support_logic':'The four scoped parts have prismatic outer footprints in the specified build direction. Internal pockets open upward and widen with build height; their recesses create no downward closed pocket roof. Native Bridge labels remain in some solid roofs over sparse infill, and are not treated as evidence of blocked pocket support.',
      'evidence_images':[str(p.relative_to(ROOT))for p in sorted(out.glob('*.png'))],
      'limits':['A round declared-width bead footprint plus 0.013 mm chord bound is a digital nominal envelope, not measured extrusion.',
      '0.2 mm eroded opening checks are conservative core checks, not a promise of full nominal hole size.',
      'Bridge feature labels can refer to roofs over sparse infill; neither feature count nor command length proves unsupported span.',
      'First-layer expansion, seams, PETG dimensions, removal force, creep and load strength are not established by this review.',
      'No CAD, shared profile or slicer output was modified; no test coupon or print submission.'],
      'manufacturing_release':False,'physical_acceptance':False,'sent_to_printer':False}
    dump(out/'report.json',report)
    lines=[f'# {inv["part"]}: actual path review','',f'Status: {report["status"]}. This is an offline path review, not manufacturing release.','',
      f'{len(layers)} emitted layers; Z steps {report["emitted_layer_steps_mm"]} mm; support paths {support_count}.','',
      '| Opening | Nominal seat height | Emitted seat height | Delta | Minimum clear radius bound |',
      '|---|---:|---:|---:|---:|']
    for h in holes_out:
        lines.append(f'| {h["name"]} | {h.get("nominal_seat_print_height")} | {h.get("actual_toolpath_seat_height_mm")} | {h.get("seat_height_delta_mm")} | {h["min_inscribed_clear_radius_lower_bound_mm"]:.3f} |')
    lines+=['','Flags: '+('; '.join(flags)if flags else'none within the defined probes'),'',
      'Numerical details, source identities, transforms, per-layer results and evidence images are in report.json. The remaining physical limits are explicit there.']
    (out/'review.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'part':inv['part'],'status':report['status'],'flags':flags,'support_path_count':support_count,
      'report':str(out/'report.json')},ensure_ascii=False))

if __name__=='__main__':main()

#!/usr/bin/env python3
"""Bounded model-extrusion review of existing shell G-code. No slicing or CAD edits.

Run with /Applications/FreeCAD.app/Contents/Resources/bin/python.
The constant-width XY swept-disk / full-layer-height model is a declared digital
occupancy envelope, not measured PETG geometry.
"""
from pathlib import Path
import collections
import hashlib
import importlib.util
import json
import math
import os
import re
import xml.etree.ElementTree as ET
import zipfile
import numpy as np
from shapely.geometry import Polygon, LineString, box, Point
from shapely.ops import unary_union

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/print-review/shell-critical-features'
SLICE=ROOT/'output/print-review/integrated-shells'
ERROR=.003
MODEL_FEATURES={'Inner wall','Outer wall','Gap infill','Overhang wall','Bridge','Internal solid infill','Sparse infill','Floating vertical shell','Top surface'}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def dump(path,value):path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
def polygons(g):return list(g.geoms)if g.geom_type=='MultiPolygon'else[g]if g.geom_type=='Polygon'else[]
def lines(g):return list(g.geoms)if hasattr(g,'geoms')else[g]

def mapping(folder):
    with zipfile.ZipFile(folder/'shell-slice-review.3mf')as z:
        ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
        m=ET.fromstring(z.read('3D/3dmodel.model'));s=ET.fromstring(z.read('Metadata/model_settings.config'))
        meta={v.attrib.get('key'):v.attrib.get('value')for v in s.findall('./object/part/metadata')}
        offset=np.array([float(meta['source_offset_'+a])for a in 'xyz'])
        component=np.array(list(map(float,m.find('./m:resources/m:object/m:components/m:component',ns).attrib['transform'].split())))
        build=np.array(list(map(float,m.find('./m:build/m:item',ns).attrib['transform'].split())))
    rotation=component[:9].reshape(3,3).T
    assert np.allclose(rotation,np.eye(3))and np.allclose(build[:9].reshape(3,3),np.eye(3))
    header=(folder/'plate_1.gcode').read_text();raw=re.search(r'^; extruder_offset = ([^\n]+)',header,re.M).group(1).split(',')[0]
    nozzle=np.array([*map(float,raw.split('x')),0.])
    shift=-rotation@offset+component[9:]+build[9:]-nozzle
    return shift,{'component':component.tolist(),'build':build.tolist(),'source_offset':offset.tolist(),'extruder_offset':nozzle.tolist(),'command_minus_shift_equals_assembly':shift.tolist()}

def model_paths(path,shift,side):
    x=y=z=0.;relative=True;last_e=0.;feature='';width=.42;layer=None;lh=.2
    for line_number,line in enumerate(path.open(),1):
        if line.startswith('; Z_HEIGHT:'):layer=float(line.split(':')[1])
        elif line.startswith('; LAYER_HEIGHT:'):lh=float(line.split(':')[1])
        elif line.startswith('; FEATURE:'):feature=line.split(':',1)[1].strip()
        elif line.startswith('; LINE_WIDTH:'):width=float(line.split(':')[1])
        code=line.split(';')[0].strip()
        if code=='M83':relative=True
        elif code=='M82':relative=False
        elif code.startswith('G92'):
            m=re.search(r'\bE([-+\d.]+)',code)
            if m:last_e=float(m.group(1))
        command=re.match(r'^(G[0123])\b',code)
        if not command:continue
        value={k:float(v)for k,v in re.findall(r'([XYZEFIJK])([-+\d.]+)',code)}
        nx,ny,nz=value.get('X',x),value.get('Y',y),value.get('Z',z)
        amount=value.get('E',0)if relative else value.get('E',last_e)-last_e
        if'E'in value:last_e=last_e+value['E']if relative else value['E']
        az=nz-shift[2]
        relevant=(-125.5<az<68.5)if side<0 else(-62<az<-56 or .0<az<6)
        if layer is not None and amount>0 and (nx!=x or ny!=y)and feature in MODEL_FEATURES and relevant:
            assert abs(nz-z)<1e-7,'Nonplanar model extrusion requires a different volume model'
            if command[1]in ['G2','G3']:
                cx,cy=x+value.get('I',0),y+value.get('J',0);radius=math.hypot(x-cx,y-cy)
                a0=math.atan2(y-cy,x-cx);a1=math.atan2(ny-cy,nx-cx)
                da=(a1-a0)%(2*math.pi)if command[1]=='G3'else-((a0-a1)%(2*math.pi))
                if abs(da)<1e-12:da=2*math.pi if command[1]=='G3'else-2*math.pi
                max_angle=2*math.acos(max(-1.,1-.0002/max(radius,.0002)))
                n=max(2,math.ceil(abs(da)/max_angle))
                points=np.array([[cx+radius*math.cos(a0+da*i/n),cy+radius*math.sin(a0+da*i/n)]for i in range(n+1)])
            else:points=np.array([[x,y],[nx,ny]])
            points-=shift[:2];points[:,0]*=side
            if points[:,0].min()<4.5+width/2 and points[:,0].max()>-.5-width/2:
                yield {'z_top':round(az,7),'height':lh,'feature':feature,'width':width,'points':points,'line':line_number}
        x,y,z=nx,ny,nz

def floor_shapes(mesh,plane):
    raw=mesh.read_bytes()
    triples=re.findall(rb'vertex\s+([-+eE.0-9]+)\s+([-+eE.0-9]+)\s+([-+eE.0-9]+)',raw)
    if triples:t=np.array(triples,float).reshape(-1,3,3)
    else:
        import struct
        n=struct.unpack_from('<I',raw,80)[0]
        t=np.frombuffer(raw,dtype=np.dtype([('n','<f4',3),('v','<f4',(3,3)),('a','<u2')]),offset=84,count=n)['v'].astype(float)
    selected=t[(abs(t[:,:,0]-plane)<1e-5).all(axis=1)]
    return unary_union([Polygon(v[:,1:])for v in selected if abs(np.cross(v[1,1:]-v[0,1:],v[2,1:]-v[0,1:]))>1e-10])

def horizontal_interval(shape,z):
    cross=shape.intersection(LineString([(-100,z),(100,z)]))
    if cross.is_empty:return None
    # Each feature is convex. Its Z-section is a single interval (or a point).
    return cross.bounds[0],cross.bounds[2]

def core_interval(shape,lo,hi):
    a=horizontal_interval(shape,lo);b=horizontal_interval(shape,hi)
    if a is None or b is None:return None
    lower=max(a[0],b[0]);upper=min(a[1],b[1])
    return(lower,upper)if upper>lower+1e-8 else None

def externally_connected_void(occupancy,roi):
    free=roi.difference(occupancy)
    left=LineString([(roi.bounds[0],roi.bounds[1]),(roi.bounds[0],roi.bounds[3])])
    return unary_union([p for p in polygons(free)if p.intersection(left).length>1e-8])

def line_width(free,depth,ylo,yhi):
    return free.intersection(LineString([(depth,ylo),(depth,yhi)])).length

def depth_from_mouth(free,y,depth):
    cut=free.intersection(LineString([(0,y),(depth,y)]))
    return max([g.bounds[2]for g in lines(cut)if not g.is_empty and g.bounds[0]<1e-7]+[0.])

def inspect_layer(feature,layer):
    z=layer['z_top'];lo=z-layer['height'];shape=feature['shape'];depth=feature['depth']
    core=core_interval(shape,lo,z)
    if core is None:return{'z_bottom':lo,'z_top':z,'status':'CAP_OR_PARTIAL_LAYER_NO_FULL_HEIGHT_CORE'}
    ylo,yhi=core;roi=box(-.5,ylo-.5,depth+.5,yhi+.5);probe=box(0,ylo,depth,yhi)
    free_lower=externally_connected_void(layer['upper'],roi)
    free_upper=externally_connected_void(layer['lower'],roi)
    a=probe.intersection(free_lower);b=probe.intersection(free_upper)
    depths=[.05,.10,.15]if feature['kind']=='groove'else[.10,1.6,3.0]
    return {'z_bottom':lo,'z_top':z,'status':'CONNECTED_CORE_RETAINED'if a.area>1e-8 else'NO_RESOLVED_CONNECTED_CORE',
        'nominal_full_layer_y_interval':list(core),'nominal_core_width_mm':yhi-ylo,'nominal_core_area_mm2':probe.area,
        'connected_clear_area_lower_mm2':a.area,'connected_clear_area_upper_mm2':b.area,
        'center_Y_continuous_depth_lower_mm':depth_from_mouth(free_lower,(ylo+yhi)/2,depth),
        'center_Y_continuous_depth_upper_mm':depth_from_mouth(free_upper,(ylo+yhi)/2,depth),
        'clear_widths_mm':{str(d):{'lower':line_width(free_lower,d,ylo,yhi),'upper':line_width(free_upper,d,ylo,yhi)}for d in depths},
        'bridge_or_overhang_commands_near_feature':sum(1 for v in layer['paths']if v['feature']in ['Bridge','Overhang wall']and LineString(v['points']).buffer(v['width']/2+ERROR).intersects(probe))}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    # Failure controls check subtraction and access, rather than just constants.
    test_roi=box(-.5,-1,1.5,1)
    test_probe=box(0,-.4,1,.4)
    empty_control=externally_connected_void(Polygon(),test_roi).intersection(test_probe).area
    blocked_control=externally_connected_void(box(-.1,-2,.1,2),test_roi).intersection(test_probe).area
    assert abs(empty_control-test_probe.area)<1e-10 and blocked_control==0
    os.environ['MPLCONFIGDIR']=str(OUT/'matplotlib-config');os.environ['XDG_CACHE_HOME']=str(OUT/'cache')
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as Patch
    identity=json.loads((ROOT/'output/feeder-integrated-candidate/report.json').read_text())
    report={'status':'RUNNING','method':{'geometry':'Constant declared-width disk swept along each positive-E model G0/G1/G2/G3 path, extruded over emitted full layer height. Physical deposited-bead shape is not measured.',
        'arc_max_chord_error_mm':.0002,'lower_upper_radius_adjustment_mm':ERROR,'buffer_quadrant_segments':64,'endpoint_rule':'Full-height nominal core is the intersection of the convex nominal floor shape at both layer boundaries; cap layers with empty core are kept separate.',
        'empty_space_rule':'Subtract all model-extrusion footprints; retain only free components connected to exterior at local inward coordinate u=-0.5. u=side*assembly X.'},'controls':{'empty_model_keeps_probe_area_mm2':empty_control,'mouth_spanning_barrier_removes_connected_probe_area_mm2':blocked_control},'parts':[],'sent_to_printer':False,'resliced':False,'cad_changed':False}
    for name,side in [('negative-half',-1),('positive-half',1)]:
        folder=SLICE/(name+'-inlet-down-supported');shift,map_info=mapping(folder)
        item=next(v for v in identity['parts']if v['name']==name);mesh=ROOT/item['path'];assert sha(mesh)==item['sha256']
        previous=json.loads((folder/'toolpath-review.json').read_text())
        assert sha(folder/'plate_1.gcode')==previous['gcode_sha256']
        assert sha(mesh)==previous['input_stl_sha256'],'G-code audit and current STL identities differ'
        assert sha(folder/'shell-slice-review.3mf')==previous['project_3mf_sha256']
        features=[]
        if side<0:
            groove_floor=floor_shapes(mesh,-.2)
            for i,p in enumerate(sorted(polygons(groove_floor),key=lambda p:(p.centroid.y,p.centroid.x))):
                features.append({'id':f'groove_{i+1:02d}','kind':'groove','depth':.2,'shape':p})
            assert len(features)==10
        locator=floor_shapes(mesh,side*3.2)
        for i,(yy,zz)in enumerate([(40,-59),(-40,3)]):
            shape=locator.intersection(box(yy-4,zz-4,yy+4,zz+4));assert shape.area>6
            features.append({'id':f'locator_{i+1}','kind':'capsule_locator'if side>0 and i==1 else'round_locator','depth':3.2,'shape':shape})
        grouped=collections.defaultdict(list)
        for p in model_paths(folder/'plate_1.gcode',shift,side):grouped[p['z_top']].append(p)
        layers={}
        for z,paths in grouped.items():
            low=[];high=[]
            for p in paths:
                line=LineString(p['points']);low.append(line.buffer(max(.00001,p['width']/2-ERROR),quad_segs=64));high.append(line.buffer(p['width']/2+ERROR,quad_segs=64))
            layers[z]={'z_top':z,'height':paths[0]['height'],'lower':unary_union(low),'upper':unary_union(high),'paths':paths}
        outlet_refill=[]
        if side<0:
            # Actual integrated STL/paths, compared with the seam candidate's
            # current Z45..68 source contract. Do not pretend the missing CAD
            # interval was removed by slicing.
            for yy in [-26.75,26.75]:
                floor_area=groove_floor.intersection(box(yy-.4,45,yy+.4,48)).area
                samples=[]
                probe=box(.01,yy-.35,.19,yy+.35)
                for z,layer in layers.items():
                    if z-layer['height']>=45.4-1e-7 and z<=48+1e-7:
                        samples.append({'z_bottom':z-layer['height'],'z_top':z,
                            'interior_probe_area_mm2':probe.area,
                            'covered_by_lower_occupancy_fraction':probe.intersection(layer['lower']).area/probe.area,
                            'exterior_connected_clear_area_under_upper_occupancy_mm2':externally_connected_void(layer['upper'],box(-.5,yy-.8,.7,yy+.8)).intersection(probe).area})
                outlet_refill.append({'center_Y':yy,'expected_seam_candidate_extent_Z':[45,68],
                    'actual_integrated_floor_extent_Z':list(next(p.bounds[1::2] for p in polygons(groove_floor) if p.bounds[1]>44 and abs(p.centroid.x-yy)<.1)),
                    'floor_area_in_Z45_to48_mm2':floor_area,'probe_U_range':[.01,.19],
                    'probe_Y_range':[yy-.35,yy+.35],'layers':samples,
                    'all_interior_probes_occupied_even_in_lower_envelope':all(v['covered_by_lower_occupancy_fraction']>1-1e-8 for v in samples)})
        summaries=[]
        if len(features)>2:fig,axs=plt.subplots(3,4,figsize=(17,12),layout='constrained')
        else:fig,axs=plt.subplots(1,2,figsize=(10,6),layout='constrained')
        axes=iter(np.asarray(axs).flat)
        for feature in features:
            shape=feature['shape'];rows=[]
            assert shape.convex_hull.difference(shape).area<1e-8,'Full-height endpoint rule requires a convex nominal feature'
            for z,layer in sorted(layers.items()):
                if z>shape.bounds[1]+1e-8 and z-layer['height']<shape.bounds[3]-1e-8:rows.append(inspect_layer(feature,layer))
            resolved=[r for r in rows if r['status']!='CAP_OR_PARTIAL_LAYER_NO_FULL_HEIGHT_CORE']
            assert resolved,'No full-height core layers inspected'
            middle=(shape.bounds[1]+shape.bounds[3])/2
            representative=min(resolved,key=lambda r:abs((r['z_bottom']+r['z_top'])/2-middle))
            summary={'id':feature['id'],'kind':feature['kind'],'nominal_floor_bounds_YZ':list(shape.bounds),'nominal_floor_area_mm2':shape.area,'nominal_depth_mm':feature['depth'],
                'full_core_layer_count':len(resolved),'cap_or_partial_layer_count':len(rows)-len(resolved),'unresolved_full_core_layers':sum(r['status']=='NO_RESOLVED_CONNECTED_CORE'for r in resolved),
                'minimum_center_Y_depth_lower_mm':min(r['center_Y_continuous_depth_lower_mm']for r in resolved),
                'minimum_clear_area_fraction_lower':min(r['connected_clear_area_lower_mm2']/r['nominal_core_area_mm2']for r in resolved),
                'representative':representative,'layers':rows}
            summaries.append(summary)
            ax=next(axes);layer=layers[representative['z_top']];core=representative['nominal_full_layer_y_interval'];center=sum(core)/2;dep=feature['depth']
            for occ,color,alpha in [(layer['lower'],'#4b94bd',.9),(layer['upper'].difference(layer['lower']),'#ecae3a',.95)]:
                for p in polygons(occ.intersection(box(-.4,core[0]-.6,dep+.55,core[1]+.6))):
                    ax.add_patch(Patch(np.asarray(p.exterior.coords),facecolor=color,edgecolor='none',alpha=alpha))
                    # Cut-outs in footprint polygons are rendered white.
                    for hole in p.interiors:ax.add_patch(Patch(np.asarray(hole.coords),facecolor='white',edgecolor='none'))
            probe=box(0,core[0],dep,core[1]);ax.plot(*probe.exterior.xy,color='#b9354b',linewidth=1.1,linestyle='--')
            ax.set_xlim(-.25,dep+.4);ax.set_ylim(core[0]-.4,core[1]+.4);ax.set_xlabel('Inward u = side × X / mm');ax.set_ylabel('Assembly Y / mm');ax.set_title(f'{feature["id"]} / {feature["kind"]}\nZ [{representative["z_bottom"]:g}, {representative["z_top"]:g}]');ax.set_aspect('equal')
        for ax in axes:ax.axis('off')
        fig.suptitle(f'{name}: actual model extrusion footprint; blue occupied, amber numerical envelope, white clear\nDashed red: nominal full-height core, not measured printed dimensions')
        fig.savefig(OUT/f'{name}-sections.png',dpi=160);plt.close(fig)
        report['parts'].append({'name':name,'input_stl_sha256':sha(mesh),'gcode_sha256':sha(folder/'plate_1.gcode'),'3mf_sha256':sha(folder/'shell-slice-review.3mf'),'mapping':map_info,'features':summaries,'outlet_groove_refill':outlet_refill,'all_full_core_layers_retain_some_connected_void':all(v['unresolved_full_core_layers']==0 for v in summaries)})
    report['source_sha256']={'analysis/shell_critical_features.py':sha(Path(__file__)),'cad/feeder-seam-candidate.scad':sha(ROOT/'cad/feeder-seam-candidate.scad'),'cad/parameters.scad':sha(ROOT/'cad/parameters.scad'),'cad/outlet-retention.scad':sha(ROOT/'cad/outlet-retention.scad'),'cad/feeder-integrated-candidate.scad':sha(ROOT/'cad/feeder-integrated-candidate.scad')}
    report['status']='EXISTING_FEATURES_RETAINED_OUTLET_CAD_REFILL_RECORDED_PHYSICAL_OPEN' if all(p['all_full_core_layers_retain_some_connected_void']for p in report['parts']) else 'EXTRUSION_OBSTRUCTION_OR_UNRESOLVED_CORE'
    report['limits']=['A footprint intersects a nominal cavity only within the declared-width/full-height envelope; this is not a measured PETG plug or a proof of actual dimension.',
        'Cap/partial layers do not have a positive full-height nominal core and are not counted as blocked interior layers.',
        'Digital retention of some connected void does not imply nominal groove width/depth or pin insertion fit.',
        'No print, re-slice, CAD edit, shrinkage/flow calibration, pressure or sealing experiment was performed.']
    dump(OUT/'report.json',report)
    print(json.dumps({'status':report['status'],'parts':[{'name':p['name'],'features':[{k:v[k]for k in ['id','kind','full_core_layer_count','unresolved_full_core_layers','minimum_center_Y_depth_lower_mm','minimum_clear_area_fraction_lower']}for v in p['features']]}for p in report['parts']]},indent=2))

if __name__=='__main__':main()

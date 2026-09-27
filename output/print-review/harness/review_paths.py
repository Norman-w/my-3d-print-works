#!/usr/bin/env python3
"""Bounded G-code review of feature-labelled extrusion, including arc samples."""
from pathlib import Path
import collections
import hashlib
import json
import math
import os
import re
import xml.etree.ElementTree as ET
import zipfile
import numpy as np
os.environ.setdefault('MPLCONFIGDIR',str(Path(__file__).resolve().parent/'matplotlib-config'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def bounds(p):return [[float(p[:,i].min()),float(p[:,i].max())]for i in range(3)]if len(p)else None

def parse(path):
    x=y=z=0.;layer=None;feature='';width=.42;paths=[];arc_count=0;relative=True;last_e=0
    for line in path.read_text().splitlines():
        if line.startswith('; Z_HEIGHT:'):layer=float(line.split(':')[1])
        elif line.startswith('; FEATURE:'):feature=line.split(':',1)[1].strip()
        elif line.startswith('; LINE_WIDTH:'):width=float(line.split(':')[1])
        code=line.split(';')[0].strip()
        if code=='M83':relative=True
        elif code=='M82':relative=False
        elif code.startswith('G92'):
            m=re.search(r'\bE([-+\d.]+)',code)
            if m:last_e=float(m.group(1))
        m=re.match(r'^(G[0123])\b',code)
        if not m:continue
        v={k:float(n)for k,n in re.findall(r'([XYZEFIJK])([-+\d.]+)',code)}
        nx,ny,nz=v.get('X',x),v.get('Y',y),v.get('Z',z)
        extrude=v.get('E',0)if relative else v.get('E',last_e)-last_e
        if 'E'in v:last_e=v['E']if not relative else last_e+v['E']
        if layer is not None and extrude>0 and (nx!=x or ny!=y):
            if m[1]in ['G2','G3']:
                cx,cy=x+v.get('I',0),y+v.get('J',0);r=math.hypot(x-cx,y-cy)
                a0=math.atan2(y-cy,x-cx);a1=math.atan2(ny-cy,nx-cx)
                da=(a1-a0)%(2*math.pi)if m[1]=='G3'else-((a0-a1)%(2*math.pi))
                if abs(da)<1e-10:da=2*math.pi if m[1]=='G3'else-2*math.pi
                n=max(2,math.ceil(abs(da)*r/.2))
                pts=np.array([[cx+r*math.cos(a0+da*i/n),cy+r*math.sin(a0+da*i/n),z+(nz-z)*i/n]for i in range(n+1)])
                arc_count+=1
            else:
                n=max(1,math.ceil(math.dist((x,y,z),(nx,ny,nz))/.2))
                pts=np.linspace([x,y,z],[nx,ny,nz],n+1)
            paths.append((layer,feature,width,pts))
        x,y,z=nx,ny,nz
    return paths,arc_count

def main():
    invocation=json.loads((OUT/'supported/invocation.json').read_text())
    mesh=ROOT/invocation['input_stl'];gcode=OUT/'supported/plate_1.gcode'
    project=OUT/'supported/harness-supported-slice-review.3mf'
    with zipfile.ZipFile(project)as archive:
        main_xml=ET.fromstring(archive.read('3D/3dmodel.model'))
        settings=ET.fromstring(archive.read('Metadata/model_settings.config'))
        part=settings.find('./object/part')
        meta={x.attrib.get('key'):x.attrib.get('value')for x in part.findall('metadata')if'key'in x.attrib}
        ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
        item=list(map(float,main_xml.find('./m:build/m:item',ns).attrib['transform'].split()))
        component=list(map(float,main_xml.find('./m:resources/m:object/m:components/m:component',ns).attrib['transform'].split()))
        offset=np.array([float(meta['source_offset_'+a])for a in 'xyz'])
        R=np.array(component[:9]).reshape(3,3).T
        C=np.array(component[9:]);B=np.array(item[9:])
        assert np.allclose(np.array(item[:9]).reshape(3,3),np.eye(3))
        assert np.allclose(R,[[1,0,0],[0,0,-1],[0,1,0]],atol=1e-12)
        model_shift=-R@offset+C+B
        (OUT/'supported/plate-native.png').write_bytes(archive.read('Metadata/plate_1.png'))
    header=gcode.read_text()
    raw_offset=re.search(r'^; extruder_offset = ([^\n]+)',header,re.M).group(1).split(',')[0]
    extruder_offset=np.array([*map(float,raw_offset.split('x')),0.])
    # The G-code commands compensate the active nozzle's 0x2 offset. Applying
    # only the 3MF transform would shift every reconstructed hole by 2 mm.
    shift=model_shift-extruder_offset
    paths,arc_count=parse(gcode)
    support=[p for p in paths if p[1]in ['Support','Support interface']]
    support_pts=np.concatenate([p[3]for p in support]);assembly=(support_pts-shift)@R
    # Every sampled extrusion point is expanded by max declared half-width and
    # 0.2 mm sample spacing, making a deliberately conservative intrusion test.
    margin=max(p[2]for p in support)/2+.2
    # Print Z is the TOP of a deposited .2 mm layer; line width expands XY,
    # not Z. Support ending at print Z8.8 is below the part underside Z9.
    within_depth=(assembly[:,1]>=-54-1e-7)&(assembly[:,1]-.2<=-48+1e-7)
    holes=[]
    for x in [-16,16]:
        for z in [-60,3]:
            radial=np.hypot(assembly[:,0]-x,assembly[:,2]-z)
            candidates=assembly[within_depth&(radial<2.25+margin)]
            holes.append({'axis_XZ':[x,z],'conservative_support_sample_count':len(candidates),
                          'candidate_bounds':bounds(candidates)})
    slots=[]
    for x in [-10.5,10.5]:
        mask=within_depth&(np.abs(assembly[:,0]-x)<1.5+margin)&(assembly[:,2]>-153-margin)&(assembly[:,2]<-131+margin)
        q=assembly[mask];slots.append({'center_X':x,'conservative_support_sample_count':len(q),'candidate_bounds':bounds(q)})
    u=(assembly[:,0]>-15)&(assembly[:,0]<15)&(assembly[:,1]>-62)&(assembly[:,1]<-54)&(assembly[:,2]>-156)&(assembly[:,2]<-66)
    regions={'open_strap_channel':{'samples':int(u.sum()),'bounds':bounds(assembly[u]),
        'removal_access':'Open toward -Y between X=-15,+15 flanges; external opening 30 mm. Remove support in pieces, not as one trapped solid.'}}
    layers=[.2,1.2,4.8,8.8,9.2,12,15,17.2]
    fig,axs=plt.subplots(2,4,figsize=(17,8.5),layout='constrained')
    for ax,height in zip(axs.flat,layers):
        chunks=collections.defaultdict(list)
        for h,feature,width,pts in paths:
            if abs(h-height)<1e-5:
                xy=pts[:,:2];key='Support'if feature.startswith('Support')else'Object'
                chunks[key].append(np.stack([xy[:-1],xy[1:]],axis=1))
        for key,color in [('Support','#d78323'),('Object','#235885')]:
            if chunks[key]:ax.add_collection(LineCollection(np.concatenate(chunks[key]),colors=color,linewidths=.35))
        ax.set_xlim(66,190);ax.set_ylim(28,228);ax.set_aspect('equal');ax.set_title(f'Z = {height:.1f} mm');ax.set_xlabel('Command X / mm');ax.set_ylabel('Command Y / mm')
    fig.suptitle('Harness actual G-code: object blue, support orange; X+90 orientation',fontsize=14)
    fig.savefig(OUT/'layer-paths.png',dpi=170);plt.close(fig)
    # Inspect mid-depth model contours around each vertical hole/slot, preserving
    # actual paths rather than inferring that source apertures survived slicing.
    mids=[p for p in paths if abs(p[0]-12)<1e-5 and p[1]=='Outer wall']
    q=(np.concatenate([p[3]for p in mids])-shift)@R
    features=[]
    for x in [-16,16]:
        for z in [-60,3]:
            rr=np.hypot(q[:,0]-x,q[:,2]-z);sel=rr<3
            features.append({'kind':'M4_hole','axis_XZ':[x,z],
                'outer_wall_samples_near_hole':int(sel.sum()),
                'hole_contour_centerline_radius_bounds_mm':[float(rr[sel].min()),float(rr[sel].max())]if sel.any()else None})
    for x in [-10.5,10.5]:
        sel=(np.abs(q[:,0]-x)<2.5)&(q[:,2]>-154)&(q[:,2]<-130)
        features.append({'kind':'strap_slot','center_X':x,'outer_wall_samples':int(sel.sum()),'bounds':bounds(q[sel])})
    native=invocation['native_result']['sliced_plates'][0]
    filament=json.loads((OUT/'supported/filament.json').read_text())
    target_initial=float(filament['nozzle_temperature_initial_layer'][0])
    layer_start=header.index('; CHANGE_LAYER')
    heat=[{'offset':m.start(),'command':m[0].strip(),'target_c':float(m[1])}
        for m in re.finditer(r'^M10[49]\b[^\n;]*?\bS([-+\d.]+)[^\n]*',header,re.M)]
    before_layer=[r for r in heat if r['offset']<layer_start]
    last_initial=before_layer[-1]['target_c']if before_layer else None
    machine=json.loads((OUT/'supported/machine.json').read_text())
    templates=[]
    template_root=Path('/Applications/BambuStudio.app/Contents/Resources/profiles/BBL/machine')
    for field in ['machine_start_gcode','machine_end_gcode','time_lapse_gcode','change_filament_gcode','layer_change_gcode']:
        f=template_root/f'Bambu Lab X1 Carbon 0.4 nozzle template {field}.json'
        original=json.loads(f.read_text())[field]
        templates.append({'field':field,'official_source':str(f),'source_sha256':sha(f),
            'loaded_field_exactly_matches_official_template':machine.get(field)==original})
    temperature_audit={'filament_initial_target_c':target_initial,'last_setpoint_before_first_model_layer_c':last_initial,
        'all_executed_file_heater_commands':heat,'official_template_fields':templates,
        'scope':'File commands inspected only; no printer was connected or physically executed.'}
    checks={'native_slice_success':invocation['process_exit_code']==0 and invocation['native_result']['return_code']==0,
        'no_native_warning':not native['warning_message'],
        'initial_temperature_command_matches_filament':last_initial==target_initial,
        'five_machine_template_fields_resolved':all(t['loaded_field_exactly_matches_official_template']for t in templates),
        'support_paths_exist':bool(support),'known_open_channel_support_detected':bool(u.any()),
        'no_support_in_four_hole_depths':all(v['conservative_support_sample_count']==0 for v in holes),
        'no_support_in_two_slot_depths':all(v['conservative_support_sample_count']==0 for v in slots),
        'six_opening_contours_represented_at_mid_depth':all(v.get('outer_wall_samples_near_hole',v.get('outer_wall_samples',0))>0 for v in features)}
    report={'status':'SUPPORTED_OFFLINE_SLICE_REVIEW_PHYSICAL_OPEN'if all(checks.values())else'REVIEW_FLAGGED',
       'checks':checks,
       'temperature_audit':temperature_audit,
       'source_sha256':invocation['cad_sha256'],'input_stl_sha256':sha(mesh),
       'gcode_sha256':sha(gcode),'project_3mf_sha256':sha(project),
       'coordinate_mapping':{'source_offset':offset.tolist(),'component_transform_3mf':component,
          'build_transform_3mf':item,'active_extruder_offset_mm':extruder_offset.tolist(),
          'Gcode_xyz_equals_R_times_assembly_plus_shift':{'R':R.tolist(),'shift':shift.tolist()},
          'inverse':'assembly X=Gcode X-96.49999, Y=Gcode Z-63, Z=62-Gcode Y'},
       'extruding_path_count':len(paths),'support_path_count':len(support),'arc_commands_sampled':arc_count,
       'max_sample_spacing_mm':.2,'support_probe_expansion_mm':margin,'support_bounds_assembly':bounds(assembly),
       'hole_support_checks':holes,'slot_support_checks':slots,'regions':regions,
       'mid_depth_outer_wall_features':features,'layer_path_figure':'layer-paths.png',
       'estimated_total_seconds':native['total_predication'],'estimated_total_grams':native['filaments'][0]['total_used_g'],
       'native_main_filament_counter_grams':native['filaments'][0]['main_used_g'],
       'warnings':native['warning_message'],'sent_to_printer':False,'physical_support_removal_validated':False,
       'limits':['Arc/line samples are conservatively expanded; candidate counts are not actual interference volumes.',
          'The underside U-channel is open to the bed side. Real PETG separation, residue and surface damage are not proven.',
          'Model paths around apertures only prove slicer representation; printed diameters, strap insertion and fastener fit remain untested.',
          'Only this one harness part was sliced; shell and root outlet integration excluded.',
          'Fixed XZ layer planes favor in-plane arm/beam continuity; Y-directed bolt preload still loads across layers. No strength value inferred.']}
    (OUT/'toolpath-review.json').write_text(json.dumps(report,indent=2)+'\n')
    summary={'status':report['status'],'cad_geometry_changed':False,
        'source_sha256':report['source_sha256'],'input_stl_sha256':report['input_stl_sha256'],
        'checks':checks,'gcode_sha256':report['gcode_sha256'],
        'project_3mf_sha256':report['project_3mf_sha256'],
        'analysis_file_sha256':{name:sha(OUT/name)for name in
            ['slice_harness.py','review_paths.py','toolpath-review.json','profile-origin-source-identity.json']},
        'template_expansion_failure_archive':'before-template-expansion/',
        'local_fix':'Five official X1C templates expanded into harness-owned machine copies; shared config untouched by this task.',
        'initial_attempt':{'sandbox_process_exit_code':-6,'native_result_missing':True,
            'later_same_command_completed':True,'cause_not_diagnosed':True},
        'sent_to_printer':False,'print_ready':False}
    (OUT/'review-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:report[k]for k in ['status','hole_support_checks','slot_support_checks','regions','mid_depth_outer_wall_features']},indent=2))
    return 0 if all(checks.values())else 1

if __name__=='__main__':raise SystemExit(main())

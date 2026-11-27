#!/usr/bin/env python3
"""Read-only reuse audit; never invokes a slicer or submits a print job."""
from pathlib import Path
from datetime import datetime, timezone
import collections, hashlib, json, math, re, sys, zipfile
import xml.etree.ElementTree as ET
import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT/'scripts'), str(ROOT/'analysis')]
from review_hold_fork_slice import stl_faces, FIELDS
import review_integrated_shell_slice as paths_reader
paths_reader.np = np
INV = ROOT/'docs/cable-assembly-inventory.json'
EXPORT = ROOT/'output/cable-scene-export/20260927T091627124663Z/report.json'
OLD = ROOT/'output/print-review/final-spin/report.json'
ACCESS = ROOT/'output/print-review/spin-head/support-access-review.json'
TOL = 1e-5  # Existing re-centering/export serialization bound, not a fit budget.
ROTATIONS = dict(body=0, carriage=-90, pad=-90, **{'pad-keeper':0,
    'opposite-guide':-90, 'cover':-90, 'spring-cage':-90,
    'spring-seat':90, 'pull-cap':-90, 'hold-fork':-90})
NS = {'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
PN = '{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}'
seen = {}

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def record(p):
    p=Path(p); key=str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)
    value=sha(p); seen.setdefault(key,value); return value
def read_json(p): record(p); return json.loads(Path(p).read_text())
def dump(p,x): Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def canon(f):
    a=tuple(map(int,f)); return min(a,a[1:]+a[:1],a[2:]+a[:2])
def compare(a,b):
    av,ai=np.unique(a.reshape(-1,3),axis=0,return_inverse=True)
    bv,bi=np.unique(b.reshape(-1,3),axis=0,return_inverse=True)
    dist,idx=cKDTree(bv).query(av); rev=cKDTree(av).query(bv)[0]
    bij=len(av)==len(bv)==len(set(idx.tolist()))
    faces=collections.Counter(canon(f)for f in idx[ai.reshape(-1,3)])==collections.Counter(canon(f)for f in bi.reshape(-1,3))
    def vol(t): return float(np.einsum('ij,ij->i',t[:,0],np.cross(t[:,1],t[:,2])).sum()/6)
    return {'passed':bool(bij and faces and len(a)==len(b) and max(dist.max(),rev.max())<=TOL),
        'source_triangles':len(a),'target_triangles':len(b),'source_vertices':len(av),'target_vertices':len(bv),
        'vertex_bijection':bij,'directed_triangle_multiset_equal':faces,
        'maximum_bidirectional_vertex_displacement_mm':float(max(dist.max(),rev.max())),
        'numeric_serialization_bound_mm':TOL,'source_signed_volume_mm3':vol(a),'target_signed_volume_mm3':vol(b),
        'bounds_delta_mm':[(a.min((0,1))-b.min((0,1))).tolist(),(a.max((0,1))-b.max((0,1))).tolist()],
        'meaning':'Same oriented triangulation under bijective bounded vertex serialization; not byte identity or measured manufacturing tolerance.'}
def matrix(s):
    a=np.array(list(map(float,s.split()))); assert len(a)==12
    M=np.eye(4);M[:3,:3]=a[:9].reshape(3,3).T;M[:3,3]=a[9:];return M
def scalar_setting(s,k):
    v=s[k];return v[0] if isinstance(v,list) else v
def segment_hits_box(a,b,lo,hi):
    delta=b-a; left=0.; right=1.
    for k in range(3):
        if abs(delta[k])<1e-12:
            if a[k]<lo[k] or a[k]>hi[k]:return False
        else:
            x,y=(lo[k]-a[k])/delta[k],(hi[k]-a[k])/delta[k]
            left=max(left,min(x,y));right=min(right,max(x,y))
            if left>right:return False
    return True
def mesh_from_archive(p):
    record(p)
    with zipfile.ZipFile(p) as z:
        main=ET.fromstring(z.read('3D/3dmodel.model')); assert main.attrib['unit']=='millimeter'
        roots=main.findall('./m:resources/m:object',NS); items=main.findall('./m:build/m:item',NS)
        assert len(roots)==len(items)==1 and items[0].attrib.get('printable','1')=='1'
        components=roots[0].findall('./m:components/m:component',NS);assert len(components)==1
        component=components[0];sub=ET.fromstring(z.read(component.attrib[PN+'path'].lstrip('/')))
        obj=sub.find('./m:resources/m:object',NS);assert obj.attrib['id']==component.attrib['objectid']
        assert len(sub.findall('./m:resources/m:object',NS))==1
        v=np.array([[float(n.attrib[a])for a in 'xyz']for n in obj.findall('./m:mesh/m:vertices/m:vertex',NS)])
        f=np.array([[int(n.attrib[a])for a in ['v1','v2','v3']]for n in obj.findall('./m:mesh/m:triangles/m:triangle',NS)])
        model=ET.fromstring(z.read('Metadata/model_settings.config'))
        normal=model.findall('./object/part');assert len(normal)==1 and normal[0].attrib['subtype']=='normal_part'
        assert len(model.findall('./plate'))==1
        md={n.attrib['key']:n.attrib.get('value')for n in normal[0].findall('metadata')if 'key'in n.attrib}
        offset=np.array([float(md['source_offset_'+a])for a in 'xyz'])
        C=matrix(component.attrib['transform']);B=matrix(items[0].attrib['transform'])
        settings=json.loads(z.read('Metadata/project_settings.config'))
        raw_gcode=z.read('Metadata/plate_1.gcode')
        tool=np.array([*map(float,scalar_setting(settings,'extruder_offset').split('x')),0.])
        source_to_command=B@C;source_to_command[:3,3]-=source_to_command[:3,:3]@offset+tool
        facts={'normal_mesh_count':1,'printable_build_instances':len(items),'source_file':md['source_file'],
            'source_offset_mm':offset.tolist(),'component_matrix':C.tolist(),'build_matrix':B.tolist(),
            'tool_offset_mm':tool.tolist(),'source_to_gcode_matrix':source_to_command.tolist(),
            'mesh_stat':normal[0].find('mesh_stat').attrib,
            'mesh_bounds_on_plate_mm':[((v@C[:3,:3].T+C[:3,3])@B[:3,:3].T+B[:3,3]).min(0).tolist(),
                                       ((v@C[:3,:3].T+C[:3,3])@B[:3,:3].T+B[:3,3]).max(0).tolist()],
            'application':next(n.text for n in main.findall('m:metadata',NS)if n.attrib.get('name')=='Application')}
        return (v+offset)[f],facts,settings,raw_gcode

FEATURE_NOTES={
 'body':'Inherited exact-artifact review: axial passage, radial service window, two opposite nuts and four cover-nut side slots; eight explicit tool corridors. This is not a final bore-diameter measurement.',
 'carriage':'Whole oriented mesh preserves dovetail, guide posts and keeper/pull-nut cavities. Actual G-code has no support; bridge commands remain. No previously recorded layer-by-layer gauge of these holes/dovetail is claimed.',
 'pad':'Whole oriented mesh preserves working ramp and axial dovetail. Selected TPU95A HF, 100% concentric, 230/35 C; rejected rectilinear variant excluded. Adhesion, friction, wear and flexible dovetail fit remain physical.',
 'pad-keeper':'Whole oriented mesh preserves the two true 90-degree countersinks. Z62 underside down, upward open holes; no support. No previously recorded actual-path DIN7991 head-envelope fit is claimed.',
 'opposite-guide':'Whole oriented mesh preserves curved guide and M3 mounting holes. External flange down, no support; actual bore/ball friction remains unmeasured.',
 'cover':'Inherited exact-artifact review: central underside, M4 side-nut slot and retaining-fork nut slot; three explicit tool corridors. Guide-hole printed size is not certified.',
 'spring-cage':'Inherited exact-artifact review: 6x6 axial corridor and two 2x2 ear-nut corridors. Clean separately before assembly; no support fracture or spring force proof.',
 'spring-seat':'Whole oriented mesh preserves full disk and pilot. Disk down and pilot upward; no support. No printed spring-seat or material strength acceptance.',
 'pull-cap':'Whole oriented mesh preserves coaxial open M3 bore. Axis vertical, no support. No actual printed bore or retention-strength acceptance.',
 'hold-fork':'Whole oriented mesh preserves downward open fork slot, M3 retainer bore and cord eye. Axis vertical, no support. No physical retention or layer-strength acceptance.'}

def main():
    record(__file__)
    for p in ['scripts/review_hold_fork_slice.py','scripts/review_integrated_shell_slice.py','analysis/spin_slice_support.py','docs/final-spin-print.md']:
        record(ROOT/p)
    inventory=read_json(INV);export=read_json(EXPORT);old=read_json(OLD);access=read_json(ACCESS)
    er={p['id']:p for p in export['parts']};orows={p['part']:p for p in old['parts']};selected={p['id']:p for p in old['selected_plates']}
    irows=[p for p in inventory['parts']if p['role']=='printed'and p['group']in ['spin','hold']]
    assert len(irows)==10 and len({p['id']for p in irows})==10
    rows=[]
    for ip in irows:
        iid=ip['id'];name=iid.split('/')[1];ep=er[iid];op=orows[name];plate=selected['spin-'+name]
        folder=(ROOT/plate['three_mf_path']).parent;inv=read_json(folder/'invocation.json');native=read_json(folder/'result.json')
        previous=read_json(folder/'review.json');current_path=ROOT/ep['file'];old_path=ROOT/inv['input']
        a=np.array(stl_faces(current_path));b=np.array(stl_faces(old_path));current_sha=record(current_path);old_sha=record(old_path)
        embedded,mapping,settings,gcode_bytes=mesh_from_archive(ROOT/plate['three_mf_path'])
        current_to_old=compare(a,b);old_to_embedded=compare(b,embedded);current_to_embedded=compare(a,embedded)
        gpath=folder/'plate_1.gcode';gsha=record(gpath);g=gpath.read_text();first=g.index('; CHANGE_LAYER')
        recorded_artifacts={k:record(folder/k)==h for k,h in op['artifact_sha256'].items()}
        private={k:record(folder/(k+'.json'))==v for k,v in inv['private_profiles'].items()}
        cad={k:record(ROOT/k)==v for k,v in inv['cad_sha256'].items()}
        profile_sources={k:record(Path(k))==v for k,v in inv['profile_sources'].items()}
        checks={'current_export_stl_hash':current_sha==ep['sha256'],'current_export_passed':ep['passed'],
            'inventory_row_agrees':all(ip[k]==ep[k]for k in ['id','role','group','definitions','material']),
            'old_stl_hash_matches_invocation_and_selected_plate':old_sha==inv['input_sha256']==op['input_sha256']==plate['inputs'][0]['sha256'],
            'selected_3mf_hash':record(ROOT/plate['three_mf_path'])==plate['three_mf_sha256'],
            'old_report_artifact_hashes':all(recorded_artifacts.values()),
            'external_gcode_equals_embedded':hashlib.sha256(gcode_bytes).hexdigest()==gsha,
            'current_vs_original_mesh':current_to_old['passed'],'original_vs_actual_normal_mesh':old_to_embedded['passed'],
            'current_vs_actual_normal_mesh':current_to_embedded['passed'],
            'exact_face_counts':len(a)==len(embedded)==int(mapping['mesh_stat']['face_count'])==native['sliced_plates'][0]['triangle_count'],
            'mesh_repair_fields_zero':all(int(v)==0 for k,v in mapping['mesh_stat'].items()if k!='face_count'),
            'spin_authority_source_hash_unchanged':all(cad.values()),'one_instance_required_one_instance_on_plate':mapping['printable_build_instances']==1}
        theta=math.radians(ROTATIONS[name]);R=np.array([[math.cos(theta),0,math.sin(theta)],[0,1,0],[-math.sin(theta),0,math.cos(theta)]])
        actual=np.array(mapping['source_to_gcode_matrix'])[:3,:3]
        component_R=np.array(mapping['component_matrix'])[:3,:3]
        build_R=np.array(mapping['build_matrix'])[:3,:3]
        # --arrange may rotate an already oriented object about plate Z.
        # Preserve and check this actual transform instead of assuming identity.
        checks['explicit_component_orientation_matches']=bool(np.max(abs(component_R-R))<1e-12)
        checks['build_rotation_is_rigid_and_keeps_print_Z']=bool(np.max(abs(build_R.T@build_R-np.eye(3)))<2e-9
            and abs(np.linalg.det(build_R)-1)<2e-9 and np.max(abs(build_R[2]-[0,0,1]))<1e-12)
        mapping['arrangement_rotation_about_print_Z_degrees']=math.degrees(math.atan2(build_R[1,0],build_R[0,0]))
        target=230 if name=='pad'else 255;bed=35 if name=='pad'else 70
        waits=[float(n)for n in re.findall(r'^M109\b[^\n;]*?\bS([-+\d.]+)',g[:first],re.M)]
        bwaits=[float(n)for n in re.findall(r'^M190\b[^\n;]*?\bS([-+\d.]+)',g[:first],re.M)]
        warnings=[p.get('warning_message')for p in native['sliced_plates']if p.get('warning_message')]
        filament=read_json(folder/'filament.json');machine=read_json(folder/'machine.json')
        expected={'printer_model':'Bambu Lab X1 Carbon','printer_variant':'0.4','nozzle_diameter':'0.4',
            'filament_type':'TPU'if name=='pad'else'PETG','layer_height':'0.2','initial_layer_print_height':'0.2','wall_loops':'4',
            'sparse_infill_density':'100%'if name=='pad'else'25%','sparse_infill_pattern':'concentric'if name=='pad'else'grid',
            'curr_bed_type':'Textured PEI Plate','nozzle_temperature':str(target),'nozzle_temperature_initial_layer':str(target),
            'textured_plate_temp':str(bed),'textured_plate_temp_initial_layer':str(bed),'enable_support':'1'if name in ['body','cover','spring-cage']else'0'}
        process_checks={'native_return_zero':inv['returncode']==0 and native['return_code']==0,'no_native_warnings':not warnings,
            'recorded_private_profiles_unchanged':all(private.values()),'TPU_official_profile_chain_unchanged':all(profile_sources.values()),
            'resolved_3mf_settings':all(str(scalar_setting(settings,k))==v for k,v in expected.items()),
            'first_layer_actual_M109':bool(waits)and waits[-1]==target,'first_layer_actual_M190':bool(bwaits)and bwaits[-1]==bed,
            'actual_3mf_start_end_etc_templates_equal_recorded_machine':all(settings[k]==machine[k]for k in FIELDS),
            'original_template_checks_passed':all(op['template_matches'].values()),
            'TPU95A_HF_profile_name_and_vendor':name!='pad'or(filament['name']=='Spin pad TPU95A HF offline'and scalar_setting(settings,'filament_vendor')=='Bambu Lab')}
        corridors=[];prior_access=next((p for p in access['parts']if p['part']==name),None)
        if prior_access:
            for c in prior_access['corridors']:
                corridors.append({'name':c['name'],'lo':c['lo'],'hi':c['hi'],'model_bead_hits':0})
        M=np.array(mapping['source_to_gcode_matrix']);inverse=np.linalg.inv(M[:3,:3])
        counts=collections.Counter();first_features=collections.Counter();lo=np.full(3,np.inf);hi=-lo.copy();maxwidth=0.;maxheight=0.;firstz=None
        for z,h,feature,width,pts in paths_reader.paths(gpath):
            counts[feature]+=1;maxwidth=max(maxwidth,width);maxheight=max(maxheight,h)
            if firstz is None:firstz=z
            if abs(z-firstz)<1e-8:first_features[feature]+=1
            deposited=pts+np.array(mapping['tool_offset_mm'])
            # The shared parser samples MODEL arc paths with step <=1mm and
            # angle <=.1rad. Max sagitta <=.0125mm (support uses .1mm step).
            radius=width/2+.0125
            lo=np.minimum(lo,deposited.min(0)-[radius,radius,h]);hi=np.maximum(hi,deposited.max(0)+[radius,radius,0])
            if corridors and not feature.startswith('Support')and feature not in ['Brim','Skirt','Custom']:
                q=(pts-M[:3,3])@inverse.T
                corners=np.array([[x,y,dz]for x in [-radius,radius]for y in [-radius,radius]for dz in [-h,0]])@inverse.T
                low=corners.min(0);high=corners.max(0);qlo=q.min(0);qhi=q.max(0)
                for c in corridors:
                    clo=np.array(c['lo'])-high;chi=np.array(c['hi'])-low
                    if (qhi<clo).any()or(qlo>chi).any():continue
                    if any(segment_hits_box(a,b,clo,chi)for a,b in zip(q[:-1],q[1:])):c['model_bead_hits']+=1
        process_checks['actual_feature_path_counts_match_previous_review']=dict(counts)==op['feature_segment_counts']
        process_checks['deposited_bounds_inside_256x256x250']=bool((lo>=-1e-4).all()and(hi<=[256,256,250]).all())
        process_checks['deposited_bounds_clear_X1C_excluded_corner']=bool(lo[0]>18 or lo[1]>28)
        inherited=None
        if name in ['body','cover','spring-cage']:
            ar=next(p for p in access['parts']if p['part']==name)
            old_mapping=np.load(folder/'support-paths.npz')
            mapping_difference=float(np.max(abs(old_mapping['rotation']-actual)))
            inherited={'evidence_path':str(ACCESS.relative_to(ROOT)),'evidence_hash':record(ACCESS),
                'hash_matches_final_report':record(ACCESS)==old['support_access_review']['sha256'],
                'source_stl_hash_matches':ar['input_stl_sha256']==old_sha,'gcode_hash_matches':ar['gcode_sha256']==gsha,
                'support_path_hash_matches':record(folder/'support-paths.npz')==ar['support_path_sha256'],
                'all_named_corridors_clear_in_stl':ar['all_corridors_clear_in_stl'],
                'previous_claim_all_named_corridors_clear_of_declared_model_beads':ar['all_corridors_clear_of_declared_model_beads'],
                'prior_mapping_max_matrix_difference':mapping_difference,
                'previous_mapping_complete':mapping_difference<2e-9,
                'corridors':ar['corridors'],'scope':'STL-side prior corridor evidence is reusable by unchanged geometry. Path-side evidence is independently recomputed here with full build×component transform and .0125mm model arc sagitta bound; old spring-cage mapping omitted build rotation.'}
            process_checks['unchanged_support_artifact_and_STL_corridor_evidence']=all(inherited[k]for k in ['hash_matches_final_report','source_stl_hash_matches','gcode_hash_matches','support_path_hash_matches','all_named_corridors_clear_in_stl'])
            process_checks['recomputed_full_transform_support_access_clear']=all(c['model_bead_hits']==0 for c in corridors)
        else:process_checks['seven_unsupported_parts_have_no_support_paths']=not any(k.startswith('Support')for k in counts)
        identity=all(checks.values());process=all(process_checks.values())
        row={'instance_id':iid,'name':ip['name'],'quantity_required':1,'quantity_in_selected_3mf':1,
            'current_stl_path':ep['file'],'current_stl_sha256':current_sha,'slice_folder':str(folder.relative_to(ROOT)),
            'old_report':str(OLD.relative_to(ROOT)),'selected_3mf':plate['three_mf_path'],'selected_3mf_sha256':plate['three_mf_sha256'],
            'gcode_sha256':gsha,'identity_status':'BOUNDED_SERIALIZATION_SAME_ORIENTED_MESH'if identity else'REVIEW_FLAGGED',
            'process_status':'RECORDED_OFFLINE_PROCESS_REUSABLE_PHYSICAL_OPEN'if process else'REVIEW_FLAGGED',
            'needs_reslice':not(identity and process),
            'reason':'Current geometry matches original and actual normal mesh with full oriented face identity; same selected G-code, configuration and bounded prior support evidence.'if identity and process else str({**{k:v for k,v in checks.items()if not v},**{k:v for k,v in process_checks.items()if not v}}),
            'checks':checks,'process_checks':process_checks,'byte_identity_current_vs_old':current_sha==old_sha,
            'current_to_original':current_to_old,'original_to_normal_mesh':old_to_embedded,'current_to_normal_mesh':current_to_embedded,
            'orientation':{'rotation_y_degrees':ROTATIONS[name],'description':op['orientation'],**mapping},
            'material':ip['material'],'resolved_settings':{k:settings[k]for k in expected},'native_warnings':warnings,
            'private_profile_hash_matches':private,'spin_source_hash_matches':cad,'TPU_profile_source_hash_matches':profile_sources,
            'actual_Gcode':{'first_layer_M109_C':waits[-1],'first_layer_M190_C':bwaits[-1],'first_layer_Z':firstz,
                'first_layer_features':dict(first_features),'feature_path_counts':dict(counts),'bead_bounds_on_plate_mm':[lo.tolist(),hi.tolist()],
                'max_line_width_mm':maxwidth,'max_layer_height_mm':maxheight,
                'scope':'All positive XY extrusion paths after first declared layer, including support/brim if present; startup purge is outside this model-path audit.'},
            'key_features':FEATURE_NOTES[name],'bounded_support_access':inherited,
            'support_corridor_full_transform_recheck':{'corridors':corridors,'model_arc_sagitta_bound_mm':.0125,
                'method':'Transform model command paths and complete asymmetric layer-thick square beads into source coordinates. Test conservative AABB-expanded named corridors against every chord. Preserves 3MF build rotation and tool offset.'}if corridors else None,
            'physical_acceptance':False,'sent_to_printer':False}
        rows.append(row);print(iid,row['identity_status'],row['process_status'],flush=True)
    stable=all(sha(ROOT/k if not k.startswith('/')else Path(k))==h for k,h in seen.items())
    tetra=np.array([[[0,0,0],[1,0,0],[0,1,0]],[[0,0,0],[0,0,1],[1,0,0]],[[0,0,0],[0,1,0],[0,0,1]],[[1,0,0],[0,0,1],[0,1,0]]],float)
    negative={'same_permuted_face_order_passes':compare(tetra,tetra[::-1])['passed'],
        'reversed_winding_rejected':not compare(tetra,tetra[:,::-1])['passed'],
        'missing_triangle_rejected':not compare(tetra,tetra[:-1])['passed'],
        '0_01mm_geometric_change_rejected':not compare(tetra,tetra+[.01,0,0])['passed']}
    report={'status':'TEN_SPIN_SELECTED_SLICES_REUSABLE_DIGITAL_SCOPE_PHYSICAL_OPEN'if stable and all(negative.values())and not any(r['needs_reslice']for r in rows)else'REVIEW_FLAGGED',
        'checked_at_UTC':datetime.now(timezone.utc).isoformat(),'rows':rows,'count':len(rows),'printed_instances':sum(r['quantity_required']for r in rows),
        'sources_stable':stable,'input_sha256':seen,'comparison_self_checks':negative,
        'scope':'Reuse of the ten selected offline slices for unchanged current spin/hold printed geometry; no new slicing or printing.',
        'open_limits':['Textured PEI is an analysis assumption; user confirmed PEI, not surface texture.',
            'Nominal CAD and actual slice reuse do not certify printed hole sizes, fit, layer strength, support break force, adhesion, friction or spin.',
            'Seven no-support parts preserve key features by complete mesh identity; this audit does not invent missing per-feature layer-envelope fit certification.',
            'TPU95A HF pad must use the selected separate TPU plate and appropriate external feed; no printer action was performed.'],
        'manufacturing_release':False,'physical_acceptance':False,'sent_to_printer':False}
    dump(OUT/'report.json',report)
    print(report['status'],flush=True)
    return 0 if report['status'].startswith('TEN_')else 1
if __name__=='__main__':raise SystemExit(main())

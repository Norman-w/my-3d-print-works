#!/usr/bin/env python3
"""Reproduce one saved inward pose identity; no search, CSG, or global bound.

Standard library only. All geometry sources recorded by the verified witness
must still match. Terms describe ONE pose and are not independent worst cases.
"""
from pathlib import Path
import hashlib
import json
import math
import re

ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/'output/guide-revision/tolerance/report.json'
OUTPUT=ROOT/'output/analysis/guide-witness-decomposition.json'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def add(a,b): return [x+y for x,y in zip(a,b)]
def sub(a,b): return [x-y for x,y in zip(a,b)]
def mul(a,v): return [sum(x*y for x,y in zip(row,v)) for row in a]
def transpose(a): return list(zip(*a))
def scale(k,v): return [k*x for x in v]


def rotation(v):
    a,b,c=v
    ca,sa,cb,sb,cc,sc=math.cos(a),math.sin(a),math.cos(b),math.sin(b),math.cos(c),math.sin(c)
    return [[cc*cb,cc*sb*sa-sc*ca,cc*sb*ca+sc*sa],
            [sc*cb,sc*sb*sa+cc*ca,sc*sb*ca-cc*sa],[-sb,cb*sa,cb*ca]]


def literal(source,key):
    values=re.findall(rf'^\s*{re.escape(key)}\s*=\s*([-+0-9.]+)\s*;',source,re.M)
    if len(values)!=1: raise ValueError(f'No unique scalar {key}')
    return float(values[0])


def main():
    report_hash=sha(INPUT);r=json.loads(INPUT.read_text())
    expected=r['source_sha256']
    checked={name:sha(ROOT/name) for name in expected}
    if checked!=expected: raise RuntimeError('Witness sources changed; do not reuse this pose as verified.')
    w=next(x for x in r['csg_witnesses'] if x['name']=='inward')
    if not w['pose_csg_verified']: raise RuntimeError('Input pose is not CSG verified.')
    if sha(ROOT/w['source']['path'])!=w['source']['sha256']:
        raise RuntimeError('Saved CSG pose source changed.')
    p={}
    for path,keys in [
        ('cad/parameters.scad',['finger_closed_center_r','finger_open_center_r',
            'cam_stroke','gate_overlap_fraction','radial_print_clearance','fastener_d','nut_depth','nut_af']),
        ('cad/cam-study.scad',['cam_follower_offset','cam_pin_d','cam_carrier_width',
            'cam_pin_shoulder_start_y','cam_pin_shoulder_end_y','cam_plate_y','cam_plate_thickness'])]:
        s=(ROOT/path).read_text()
        p.update({key:literal(s,key) for key in keys})
    q=w['variables'];u=w['stroke_mm'];overlap=p['gate_overlap_fraction']
    start=p['cam_stroke']*(1+overlap)/2
    slope=(p['finger_open_center_r']-p['finger_closed_center_r'])/(p['cam_stroke']*(1-overlap)/2)
    assert start<u<p['cam_stroke'],'Identity currently describes an interior front ramp pose.'
    nominal=p['finger_closed_center_r']+slope*(u-start)
    center=[0,0,u];tip=add([nominal,0,0],q[:3])
    carrier=rotation(q[3:6]);frame=rotation(q[10:13]);ft=[q[8],q[9],0]
    offset=p['cam_follower_offset']
    pin_base=add(tip,mul(carrier,[offset+q[6],0,q[7]]))
    carrier_axis=[row[1] for row in carrier]
    base_cam=add(center,mul(transpose(frame),sub(sub(pin_base,center),ft)))
    axis_cam=mul(transpose(frame),carrier_axis)
    faces=[]
    explanations={
        'slot_line_residual':'本位姿销轴在凸轮坐标面的 x+slope*z 偏离槽中心线；为含有限厚度/倾斜的已保存位姿值，不是另取槽的独立最坏量。',
        'frame_x_translation':'公共凸轮架在固定轴向导向中的 X 平移。',
        'pin_installation_x':'肩销/捕获螺母成组在载体中的 X 安装偏心，经载体旋转投影；充分预紧后应视为固定装配误差，不是自动发生的滑移。',
        'carrier_offset_rotation':'名义20 mm载体到销中心偏距的 X 投影变化，小的反向抵消项。',
        'pin_installation_z_projection':'销的局部 Z 安装偏心投影到世界 X；本反例近零。',
        'shoulder_axis_lever':'载体姿态使肩销轴从载体中心平面到本凸轮面的 X 坐标改变；销与载体共用旋转，不是销独立摇摆。',
        'tip_z_times_slope':'载体/球头 Z 偏移经0.625槽斜率转为 X 定位差。',
        'cam_z_coordinate_coupling':'销交点的凸轮坐标 Z 相对球头世界 Z 的变化，经槽斜率转为 X；本反例主要来自公共架绕X转角。',
        'frame_x_rotation_projection':'完整三维坐标变换的 X 修正；保留此项使恒等式不依赖框架另两转角恰好为零。'}
    for y in [p['cam_plate_y'],p['cam_plate_y']+p['cam_plate_thickness']]:
        lam=(y-base_cam[1])/axis_cam[1]
        point=add(base_cam,scale(lam,axis_cam));world=add(pin_base,scale(lam,carrier_axis))
        values={
            'slot_line_residual':point[0]+slope*point[2]-(nominal+offset),
            'frame_x_translation':q[8],
            'pin_installation_x':-carrier[0][0]*q[6],
            'carrier_offset_rotation':-offset*(carrier[0][0]-1),
            'pin_installation_z_projection':-carrier[0][2]*q[7],
            'shoulder_axis_lever':-lam*carrier_axis[0],
            'tip_z_times_slope':-slope*q[2],
            'cam_z_coordinate_coupling':-slope*(point[2]-q[2]),
            'frame_x_rotation_projection':world[0]-q[8]-point[0]}
        total=sum(values.values());error=total-q[0]
        assert abs(error)<1e-10,(y,error)
        faces.append({'cam_local_y_mm':y,'pin_axis_point_cam_xyz_mm':point,
            'terms':[{'key':key,'x_contribution_mm':value,'meaning':explanations[key]}
                     for key,value in values.items()],
            'reconstructed_tip_x_offset_mm':total,'identity_residual_mm':error})
    nut_top=-p['cam_carrier_width']/2+p['nut_depth']
    result={'status':'VERIFIED_POSE_IDENTITY_REPRODUCED_NOT_A_BOUND',
        'source_and_artifact_sha256':{
            str(INPUT.relative_to(ROOT)):report_hash,
            str(Path(__file__).resolve().relative_to(ROOT)):sha(Path(__file__)),
            w['source']['path']:w['source']['sha256']},
        'input_report':str(INPUT.relative_to(ROOT)),'input_report_sha256':report_hash,
        'source_sha256':checked,'script_sha256':sha(Path(__file__)),
        'saved_pose_source':w['source'],'witness_name':'inward','stroke_mm':u,
        'witness_variables':q,'tip_x_offset_mm':q[0],'front_ramp_slope':slope,
        'carrier_euler_degrees':[math.degrees(x) for x in q[3:6]],
        'frame_euler_degrees':[math.degrees(x) for x in q[10:13]],
        'faces':faces,'primary_decomposition_face_y_mm':p['cam_plate_y'],
        'seated_joint_geometry':{
            'shoulder_seat_local_y_mm':p['cam_pin_shoulder_start_y'],
            'nut_loaded_face_local_y_mm':nut_top,
            'clamped_carrier_web_axial_thickness_mm':p['cam_pin_shoulder_start_y']-nut_top,
            'nominal_shoulder_bearing_radial_land_mm':(p['cam_pin_d']-p['fastener_d'])/2,
            'head_to_nominal_cam_far_face_gap_mm':p['cam_pin_shoulder_end_y']-p['cam_plate_y']-p['cam_plate_thickness'],
            'thread_clearance_radial_mm':(p['fastener_d']-3)/2,
            'captured_nut_flat_clearance_each_side_mm':(p['nut_af']-5.5)/2,
            'target_nut_local_y_start_mm':-p['cam_carrier_width']/2+.2,
            'other_three_display_nuts_gap_to_pocket_floor_mm':.1},
        'preload_interpretation':[
            'The modeled shoulder is axially seated and its orientation is rigidly tied to the carrier. No independent pin tilt or Y sliding variable exists.',
            'The target nut face is seated at the real pocket floor. Shoulder/nut preload clamps the carrier web, not the cam plate; nominal head-to-cam clearance is 0.75 mm.',
            'Pin XZ offset can be fixed by tightening at an eccentric installation position. Tightening does not establish centering in the loose round hole/hex pocket.',
            'The two published inward/outward poses use different pin installation offsets; their separation is not measured dynamic backlash of one tightened assembly.',
            'No preload, friction coefficient, bearing-pressure, shoulder-fillet fit, PETG relaxation or slip-load proof is present. These require real hardware and seat/fit measurements.',
            'The other three nuts retain display placements 0.1 mm short of their floors; the target witness has the seated nut. A future fully-tightened assembly review must distinguish this.'],
        'limits':['Exact algebraic decomposition of ONE saved CSG-verified pose; terms are coupled, not independent worst-case tolerances.',
            'Neither a certified global bound nor a dynamically reachable loaded trajectory is proven.',
            'Setting an installation term to zero or subtracting it from the witness does not certify the remainder.',
            'No optimization, CSG, source edit or physical measurement was run by this script.']}
    assert sha(INPUT)==report_hash
    assert all(sha(ROOT/name)==digest for name,digest in checked.items())
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(result['status'])
    print(json.dumps({'tip_x_offset_mm':q[0],'decomposition_at_y8_mm':
        {row['key']:row['x_contribution_mm'] for row in faces[0]['terms']},
        'identity_residual_mm':faces[0]['identity_residual_mm']},indent=2))


if __name__=='__main__':main()

#!/usr/bin/env python3
"""Bounded rigid-clearance study; run with FreeCAD bundled Python (numpy/scipy).

This intentionally distinguishes an optimized feasible model witness from a
certified global bound or a whole-assembly collision-checked counterexample.
"""
from pathlib import Path
import itertools
import json
import math
import hashlib
import re
import subprocess
import sys
import numpy as np
from scipy.optimize import minimize

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/analysis'

def rotation(v):
    a,b,c=v
    ca,sa,cb,sb,cc,sc=np.cos(a),np.sin(a),np.cos(b),np.sin(b),np.cos(c),np.sin(c)
    return np.array([[cc*cb,cc*sb*sa-sc*ca,cc*sb*ca+sc*sa],
                     [sc*cb,sc*sb*sa+cc*ca,sc*sb*ca-cc*sa],
                     [-sb,cb*sa,cb*ca]])

def literal(source,key):
    found=re.findall(rf'^\s*{re.escape(key)}\s*=\s*([-+0-9.]+)\s*;',source,re.M)
    if len(found)!=1:raise ValueError(f'Expected literal {key}')
    return float(found[0])

def load():
    files=['cad/parameters.scad','cad/cam-study.scad','cad/feeder-supports.scad','cad/feeder-body.scad','analysis/feeder_integration.py']
    sources={f:(ROOT/f).read_text() for f in files}
    p={}
    for src,keys in [
        (files[0],['finger_tip_radius','finger_closed_center_r','finger_open_center_r','cam_stroke','gate_spacing','gate_overlap_fraction','radial_print_clearance','fastener_d','nut_af','$fn']),
        (files[1],['cam_follower_offset','cam_pin_d','cam_pin_thread_d','cam_pin_shoulder_start_y','cam_pin_start_y','cam_plate_y','cam_plate_thickness','cam_carrier_inner_offset','cam_carrier_length','cam_carrier_width','cam_carrier_axial']),
        (files[2],['support_radial_clearance','support_axial_clearance','support_radial_y1','support_rail_x0','support_rail_x1','support_rail_y0','support_rail_y1','support_guide_z0','support_guide_z1'])]:
        p.update({k:literal(sources[src],k) for k in keys})
    # These actual CAD contracts must be reviewed if their topology changes.
    body=re.sub(r'\s+','',sources[files[3]])
    assert 'side==1?23.5:-33.5' in body and 'cylinder(h=10,r=finger_tip_radius+radial_print_clearance)' in body
    cam=re.sub(r'\s+','',sources[files[1]])
    assert 'cylinder(h=2.4,d=5.5/cos(30),$fn=6)' in cam
    return p,sources

class ClearanceModel:
    """One +X front follower; rigid shoulder seated flush in carrier.

    Variables: carrier tip xyz offset(3), carrier XYZ Euler(3), shoulder local
    xz offset(2), carriage xy translation(2), carriage XYZ Euler(3).
    Frame rotates about the translated CAD origin (0,0,u) with explicit xy
    translation. Its actual CAD-origin Z coordinate remains exactly u.
    """
    def __init__(self,p,u=17):
        self.p=p;self.u=u
        self.slope=(p['finger_open_center_r']-p['finger_closed_center_r'])/(p['cam_stroke']*(1-p['gate_overlap_fraction'])/2)
        self.r=p['finger_closed_center_r']+self.slope*(u-p['cam_stroke']*(1+p['gate_overlap_fraction'])/2)
        self.center=np.array([0.,0.,u])
        self.vertices=np.array(list(itertools.product([p['cam_carrier_inner_offset'],p['cam_carrier_inner_offset']+p['cam_carrier_length']],[-p['cam_carrier_width']/2,p['cam_carrier_width']/2],[-p['cam_carrier_axial']/2,p['cam_carrier_axial']/2])))
        self.normal=np.array([1.,0,self.slope]);self.normal/=np.linalg.norm(self.normal)
        self.bounds=[(-2,2),(-1,1),(-1,1)]+[(-.08,.08)]*3+[(-.25,.25)]*2+[(-.5,.5)]*2+[(-.02,.02)]*3

    def transform(self,q):
        tip=np.array([self.r,0.,0.])+q[:3]
        rc=rotation(q[3:6]);rf=rotation(q[10:13]);ft=np.array([q[8],q[9],0.])
        return tip,rc,rf,ft

    def constraints(self,q,grouped=False):
        p=self.p;tip,rc,rf,ft=self.transform(q);groups={}
        # Restrictive full-box surrogate: even carrier corners outside the
        # fixed guide's X extent must fit its YZ rectangle. Thus feasible
        # solutions do not exploit removed front/back service windows.
        vs=tip+self.vertices@rc.T
        groups['carrier_rectangle']=np.concatenate([p['cam_carrier_width']/2+p['support_radial_clearance']-np.abs(vs[:,1]),p['cam_carrier_axial']/2+p['support_radial_clearance']-np.abs(vs[:,2])])
        # Complete D5.5 outer body boss at x31.5..33.5. Bounding the ellipse by
        # its circumcircle is restrictive, not a claim of exact tightness.
        rod=[]
        axis=rc[:,0]
        for x in [31.5,33.5]:
            center=tip+(x-tip[0])/axis[0]*axis
            # The current body bore uses $fn=72: use its inscribed radius,
            # not a smooth D5.5 circle, for a conservative feasible witness.
            rod.append((p['finger_tip_radius']+p['radial_print_clearance'])*math.cos(math.pi/p['$fn'])-np.linalg.norm(center[1:])-p['finger_tip_radius']/abs(axis[0]))
        groups['outer_round_rod_bore']=np.array(rod)
        # Inner guide only sees a spherical cap for the selected outward ramp
        # search when tip x >23.5. For deeper positions use a deliberately
        # restrictive extension of the rod cylinder through guide walls.
        if tip[0]>23.5:
            cap=math.sqrt(max(0,p['finger_tip_radius']**2-(tip[0]-23.5)**2))
            inner=[p['finger_tip_radius']+p['radial_print_clearance']-np.linalg.norm(tip[1:])-cap]
        else:
            inner=[]
            for x in [21.0,23.5]:
                center=tip+(x-tip[0])/axis[0]*axis
                inner.append(p['finger_tip_radius']+p['radial_print_clearance']-np.linalg.norm(center[1:])-p['finger_tip_radius']/abs(axis[0]))
        groups['inner_guide_cap_or_rod']=np.array(inner)
        # A seated parallel shoulder axis also passes the tighter M3 hole and
        # a same-orientation captured nut; the latter has three real flats.
        offset=q[6:8]
        groups['thread_hole']=np.array([(p['fastener_d']-p['cam_pin_thread_d'])/2-np.linalg.norm(offset)])
        normals=np.array([[math.cos(a),math.sin(a)] for a in np.deg2rad([30,90,150])])
        groups['captured_nut_flats']=(p['nut_af']-5.5)/2-np.abs(normals@offset)
        # Exact projected four rail corners at each end of both fixed guides.
        vals=[]
        for side in [-1,1]:
            for x,y in itertools.product([side*p['support_rail_x0'],side*p['support_rail_x1']],[p['support_rail_y0'],p['support_rail_y1']]):
                base=np.array([x,y,0.]);a=self.center+rf@(base-self.center)+ft
                for z in [p['support_guide_z0'],p['support_guide_z1']]:
                    point=a+(z-a[2])/rf[2,2]*rf[:,2]
                    target=side*(p['support_rail_x0']+p['support_rail_x1'])/2
                    vals.extend([(p['support_rail_x1']-p['support_rail_x0'])/2+p['support_axial_clearance']-abs(point[0]-target),(p['support_rail_y1']-p['support_rail_y0'])/2+p['support_axial_clearance']-abs(point[1]-(p['support_rail_y0']+p['support_rail_y1'])/2)])
        groups['two_axial_rails']=np.array(vals)
        # Cylinder/straight slot fit at BOTH plate faces, including the ellipse
        # produced by a tilted pin. A single mid-plane point is insufficient.
        base=tip+rc@np.array([p['cam_follower_offset']+q[6],0,q[7]])
        # The fixed front housing window is another real pin guide. It cannot
        # be omitted merely because the larger carrier fits its rectangle.
        window=[]
        world_axis=rc[:,1]
        for y in [p['cam_carrier_width']/2+p['support_radial_clearance'],p['support_radial_y1']]:
            center=base+(y-base[1])/world_axis[1]*world_axis
            zsupport=p['cam_pin_d']/2*math.sqrt(1+(world_axis[2]/world_axis[1])**2)
            xsupport=p['cam_pin_d']/2*math.sqrt(1+(world_axis[0]/world_axis[1])**2)
            window.extend([p['cam_pin_d']/2+p['radial_print_clearance']-abs(center[2])-zsupport,
                center[0]-xsupport-(p['finger_closed_center_r']+p['cam_follower_offset']-p['cam_pin_d']/2-p['radial_print_clearance'])])
        groups['fixed_front_shoulder_window']=np.array(window)
        tail=[]
        for y in [p['cam_pin_start_y'],-p['cam_carrier_width']/2-p['support_radial_clearance']]:
            center=base+(y-base[1])/world_axis[1]*world_axis
            tail.append(p['fastener_d']/2-abs(center[2])-p['cam_pin_thread_d']/2*math.sqrt(1+(world_axis[2]/world_axis[1])**2))
        groups['fixed_back_thread_window']=np.array(tail)
        base_cam=self.center+rf.T@(base-self.center-ft)
        pin_axis=rf.T@rc[:,1]
        support=p['cam_pin_d']/2*math.sqrt(1+(np.dot(self.normal,pin_axis)/pin_axis[1])**2)
        vals=[]
        for y in [p['cam_plate_y'],p['cam_plate_y']+p['cam_plate_thickness']]:
            point=base_cam+(y-base_cam[1])/pin_axis[1]*pin_axis
            distance=np.dot(self.normal,point-np.array([self.r+p['cam_follower_offset'],0.,0.]))
            vals.append(p['cam_pin_d']/2+p['radial_print_clearance']-support-abs(distance))
        groups['finite_thickness_slot']=np.array(vals)
        if grouped:return groups
        return np.concatenate(list(groups.values()))

    def solve(self,seed,sign=1):
        return minimize(lambda q:-sign*q[0],seed,method='SLSQP',bounds=self.bounds,constraints=[{'type':'ineq','fun':self.constraints}],options={'maxiter':700,'ftol':1e-11})

def main():
    p,sources=load();rng=np.random.default_rng(240924);model=ClearanceModel(p)
    results=[]
    for i in range(14):
        seed=np.zeros(13)
        if i:seed[3:6]=rng.uniform(-.01,.01,3);seed[10:13]=rng.uniform(-.002,.002,3)
        solved=model.solve(seed)
        q=solved.x;groups=model.constraints(q,True);violation=min(float(min(v)) for v in groups.values())
        results.append({'success':bool(solved.success),'min_margin':violation,'radial_tip_error':float(q[0]),'variables':q.tolist(),'iterations':int(solved.nit),'constraint_minima':{k:float(min(v)) for k,v in groups.items()}})
    feasible=[r for r in results if r['min_margin']>=-1e-7]
    best=max(feasible,key=lambda r:r['radial_tip_error']) if feasible else None
    report={'status':'LOCAL_RIGID_CONSTRAINT_STUDY_NOT_GLOBAL_PROOF','source_sha256':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in sources.items()},'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'stroke_mm':model.u,'nominal_front_tip_r':model.r,'parameter_snapshot':p,'best':best,'runs':results,'global_bound':None,'whole_assembly_counterexample_verified':False}
    OUT.mkdir(exist_ok=True,parents=True);(OUT/'feeder-tolerance.json').write_text(json.dumps(report,indent=2)+'\n')
    if '--verify-csg' in sys.argv and best:
        # Back away from mathematical contact to avoid mistaking polygonal
        # cylinders/roundoff for a feasible smooth-solid witness.
        q=np.array(best['variables'])*.995
        tip,rc,rf,ft=model.transform(q)
        def matrix(r,t):
            m=np.eye(4);m[:3,:3]=r;m[:3,3]=t;return m.tolist()
        frame=matrix(rf,model.center+ft-rf@model.center)
        carrier=matrix(rc,tip)
        src='''feeder_support_library_mode=true;
include <../../cad/feeder-supports.scad>
use <../../cad/feeder-body.scad>
probe_kind="fixed";
module moved_frame(){multmatrix(FRAME) feeder_carriage(T);}
module moved_carrier(){multmatrix(CARRIER) cam_finger_local();}
module moved_pin(){multmatrix(CARRIER) translate(PINSHIFT) cam_pin_local();}
module moved_nut(){multmatrix(CARRIER) translate(NUTSHIFT)
 rotate([-90,0,0]) difference(){cylinder(h=2.4,d=5.5/cos(30),$fn=6);
 translate([0,0,-.02]) cylinder(h=2.44,d=3,$fn=32);}}
module followers(){moved_carrier();moved_pin();moved_nut();
 for(side=[-1,1],rear=[false,true])if(!(side==1&&!rear)){
 cam_finger(side,rear,T);cam_pin(side,rear,T,0);cam_follower_nut(side,rear,T);}}
module fixed(){feeder_body_full();feeder_support_fixed();feeder_cap_hardware();feeder_mount_hardware();}
if(probe_kind=="fixed")intersection(){fixed();union(){moved_frame();followers();}}
else if(probe_kind=="cam")intersection(){moved_frame();followers();}
else if(probe_kind=="seat")intersection(){moved_carrier();union(){moved_pin();moved_nut();}}
else if(probe_kind=="view"){color([.6,.65,.68,.16])feeder_body_full();
 color([.72,.72,.72])feeder_support_fixed();color([.1,.4,.8])moved_frame();
 color([1,.4,.1])followers();}
'''
        src=src.replace('FRAME',json.dumps(frame)).replace('CARRIER',json.dumps(carrier)).replace('PINSHIFT',json.dumps([p['cam_follower_offset']+q[6],0,float(q[7])])).replace('NUTSHIFT',json.dumps([p['cam_follower_offset']+q[6],-p['cam_carrier_width']/2+.2,float(q[7])])).replace('T)',f'{model.u/p["cam_stroke"]})').replace(',T,',f',{model.u/p["cam_stroke"]},')
        path=OUT/'feeder-tolerance-witness.scad';path.write_text(src)
        from feeder_integration import classify
        probes=[]
        for kind in ['fixed','cam','seat']:
            target=OUT/f'feeder-tolerance-{kind}.stl';target.unlink(missing_ok=True)
            cmd=['/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD','--render','--backend','Manifold','--export-format','asciistl','-D',f'probe_kind="{kind}"','-o',str(target),str(path)]
            result=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
            (OUT/f'feeder-tolerance-{kind}.log').write_text(result.stdout+result.stderr)
            if target.exists():checked=classify(target)
            elif 'Current top level object is empty' in result.stderr:checked={'has_solid_or_unclassified_overlap':False,'triangle_count':0,'components':[]}
            else:checked={'has_solid_or_unclassified_overlap':True,'error':result.stderr[-2000:]}
            probes.append({'name':kind,'exit_code':result.returncode,**checked})
        stable=all(hashlib.sha256((ROOT/k).read_bytes()).hexdigest()==h for k,h in report['source_sha256'].items())
        origin=np.array(frame)@np.array([0.,0.,model.u,1.])
        assert abs(origin[2]-model.u)<1e-10
        path_start=np.zeros(13);path_start[6:8]=q[6:8]
        path_start[0]=-q[6];path_start[2]=-q[7]
        path_margins=[float(min(model.constraints(path_start+a*(q-path_start)))) for a in np.linspace(0,1,101)]
        witness={'variables':q.tolist(),'radial_tip_error':float(q[0]),'analytic_min_margin':float(min(model.constraints(q))),'constraint_minima':{k:float(min(v)) for k,v in model.constraints(q,True).items()},'frame_transform':frame,'carrier_transform':carrier,'actual_cam_origin_xyz':origin[:3].tolist(),'probes':probes,'source_stable':stable,'fixed_pin_offset_path_samples':101,'fixed_pin_offset_path_min_margin':min(path_margins),'path_scope':'Analytic constraint samples only; not a continuous CSG path certificate.'}
        verified=stable and q[0]>1 and witness['analytic_min_margin']>=0 and not any(p['has_solid_or_unclassified_overlap'] for p in probes)
        report.update({'status':'RIGID_CSG_COUNTEREXAMPLE_VERIFIED' if verified else 'CANDIDATE_WITNESS_REJECTED_OR_UNCLASSIFIED','whole_assembly_counterexample_verified':bool(verified),'witness':witness})
        report['artifact_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [path,*[OUT/f'feeder-tolerance-{kind}.log' for kind in ['fixed','cam','seat']]]}
        report['limits']=['A feasible rigid CAD configuration is a lower bound on the worst error, not a global maximum.','Other three followers retain their nominal poses in the actual CSG check.','The verified excess over 1mm is small; this rejects a claimed guarantee, not a prediction of actual double feeding.','No print/profile/assembly-position error, elastic deformation, wear, airflow, friction or spring force is added.','The shoulder and captured nut are seated; a loose screw creates a different and potentially larger uncertainty.','Finite interpolation samples do not prove a continuous loaded actuation trajectory.']
        (OUT/'feeder-tolerance.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({'status':report['status'],'verified_error_mm':float(q[0]),'minimum_model_clearance_mm':witness['analytic_min_margin'],'actual_cam_origin_z':float(origin[2]),'sources_stable':stable},indent=2))
    else:print(json.dumps(best,indent=2))

if __name__=='__main__':main()

#!/usr/bin/env python3
"""Current cam X-guide rigid-pose audit. A verified witness is a LOWER bound.

Run using FreeCAD bundled Python for numpy/scipy. Does not edit shared CAD.
The inherited carrier slab is restrictive; local maxima cannot certify a
physical/global upper bound. The actual X datum/gib contact regions are used.
"""
from pathlib import Path
import argparse
import hashlib
import itertools
import json
import math
import subprocess
import sys

import numpy as np
import feeder_tolerance as base
from guide_revision_tolerance import RevisedModel, transform_matrix
from feeder_integration import classify

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/cam-guide-error-bound'
SCAD='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'


class CurrentModel(RevisedModel):
    def __init__(self,p,rev,cg,u,side=1,rear=False):
        super().__init__(p,rev,u)
        self.cg=cg;self.side=side;self.rear=rear
        self.g=-p['gate_spacing']if rear else 0.
        end=p['cam_stroke']*(1-p['gate_overlap_fraction'])/2
        start=p['cam_stroke']-end
        m=(p['finger_open_center_r']-p['finger_closed_center_r'])/end
        if rear:
            self.r=p['finger_open_center_r']-m*min(u,end)
            self.slope=-m if u<end else 0.
        else:
            self.r=p['finger_closed_center_r']+m*max(0,u-start)
            self.slope=m if u>start else 0.
        self.normal=np.array([side,0.,self.slope]);self.normal/=np.linalg.norm(self.normal)
        self.bounds=self.bounds+[(-cg['gib_axial_float_limit'],cg['gib_axial_float_limit'])]
        self.bits=np.array(list(itertools.product([0,1],repeat=3)))
        self.rail_edges=[(a,b)for a,b in itertools.combinations(range(8),2)
                         if sum(self.bits[a]!=self.bits[b])==1]

    def world(self,q):
        tip,rc,rf,ft=self.transform(q)
        mirror=np.diag([self.side,1.,1.])
        return mirror@tip+np.array([0.,0.,self.g]),mirror@rc,rf,ft

    def rail_corners_at(self,q,side,z0,z1):
        _,_,rf,ft=self.transform(q);p=self.p
        out=[]
        for ix,iy,iz in self.bits:
            a=self.center+rf@(np.array([
                side*p[['support_rail_x0','support_rail_x1'][ix]],
                p[['support_rail_y0','support_rail_y1'][iy]],0.])-self.center)+ft
            z=[z0,z1][iz]
            out.append(a+(z-a[2])/rf[2,2]*rf[:,2])
        return np.array(out)

    def clipped_rail(self,q,z0,z1):
        v=self.rail_corners_at(q,1,z0,z1)
        y0,y1=self.cg['contact_y']
        pts=[x for x in v if y0<=x[1]<=y1]
        for a,b in self.rail_edges:
            for y in [y0,y1]:
                dy=v[b,1]-v[a,1]
                if abs(dy)>1e-12:
                    f=(y-v[a,1])/dy
                    if 0<=f<=1:pts.append(v[a]+f*(v[b]-v[a]))
        if not pts:raise ValueError('Rail left contact Y region; outside retained study branch')
        return np.asarray(pts)

    def constraints(self,q,grouped=False):
        groups=super().constraints(q,True)
        p=self.p;cg=self.cg
        # Replace old right X walls: new outer windows removed portions of them.
        # The unchanged left X walls and both rail Y end faces remain active.
        rails=[]
        for side in [-1,1]:
            vs=self.rail_corners_at(q,side,p['support_guide_z0'],p['support_guide_z1'])
            rails.extend(2+p['support_axial_clearance']-abs(vs[:,1]-22))
            if side==-1:rails.extend(2+p['support_axial_clearance']-abs(vs[:,0]+56))
        groups['two_axial_rails']=np.asarray(rails)
        inner=self.clipped_rail(q,*cg['guide_z'])
        groups['right_continuous_x_datum']=[float(min(inner[:,0]-cg['datum_x']))]
        for i,band in enumerate(cg['active_contact_z']):
            outer=self.clipped_rail(q,band[0]+q[13],band[1]+q[13])
            groups[f'right_x_gib_band_{i}']=[float(min(cg['front_x']-outer[:,0]))]
        # Pin is seated relative to its carrier, not independently tilted.
        tip,rc,rf,ft=self.world(q)
        pin=tip+rc@np.array([p['cam_follower_offset']+q[6],0,q[7]])
        point0=self.center+rf.T@(pin-self.center-ft)
        axis=rf.T@rc[:,1]
        support=p['cam_pin_d']/2*math.sqrt(1+(np.dot(self.normal,axis)/axis[1])**2)
        slot=[]
        for y in [p['cam_plate_y'],p['cam_plate_y']+p['cam_plate_thickness']]:
            point=point0+(y-point0[1])/axis[1]*axis
            distance=np.dot(self.normal,point-np.array([self.side*(self.r+p['cam_follower_offset']),0.,self.g]))
            slot.append(p['cam_pin_d']/2+p['radial_print_clearance']-support-abs(distance))
        groups['finite_thickness_slot']=np.asarray(slot)
        return groups if grouped else np.concatenate(list(groups.values()))


def verify(model,q,name):
    tip,rc,rf,ft=model.world(q)
    fm=transform_matrix(rf,model.center+ft-rf@model.center)
    cm=transform_matrix(rc,tip)
    p=model.p;t=model.u/p['cam_stroke']
    pin=[p['cam_follower_offset']+q[6],0,q[7]]
    nut=[pin[0],-p['cam_carrier_width']/2+.2,q[7]]
    source='''cg_library_mode=true;
include <../../cad/feeder-cam-guide-revision.scad>
probe_kind="fixed";
t=__T__;
module moved_frame(){multmatrix(__FRAME__) feeder_carriage(t);}
module moved_carrier(){multmatrix(__CARRIER__)cam_finger_local();}
module moved_pin(){multmatrix(__CARRIER__)translate(__PIN__)cam_pin_local();}
module moved_nut(){multmatrix(__CARRIER__)translate(__NUT__)
 rotate([-90,0,0])difference(){cylinder(h=2.4,d=5.5/cos(30),$fn=6);
 translate([0,0,-.02])cylinder(h=2.44,d=3,$fn=32);}}
module followers(){moved_carrier();moved_pin();moved_nut();
 for(side=[-1,1],rear=[false,true])if(!(side==__SIDE__&&rear==__REAR__)){
 cam_finger(side,rear,t);cam_pin(side,rear,t,0);cam_follower_nut(side,rear,t);}}
module fixed(){cg_body();cg_fixed();cg_gib(dz=__DZ__);revision_gibs();
 cg_old_hardware();cg_new_hardware();}
if(probe_kind=="fixed")intersection(){fixed();union(){moved_frame();followers();}}
else if(probe_kind=="cam")intersection(){moved_frame();followers();}
else if(probe_kind=="seat")intersection(){moved_carrier();union(){moved_pin();moved_nut();}}
else if(probe_kind=="control")intersection(){cg_fixed();cg_gib(dz=.22);}
else assert(false,"unknown probe");
'''
    for key,val in [('T',t),('FRAME',fm),('CARRIER',cm),('PIN',pin),('NUT',nut),
                    ('SIDE',model.side),('REAR',model.rear),('DZ',q[13])]:
        source=source.replace('__'+key+'__',json.dumps(val))
    path=OUT/f'{name}.scad';path.write_text(source)
    probes=[]
    for kind in ['fixed','cam','seat','control']:
        target=OUT/f'{name}-{kind}.stl';target.unlink(missing_ok=True)
        result=subprocess.run([SCAD,'--render','--backend','Manifold','--export-format','asciistl',
            '-D',f'probe_kind="{kind}"','-o',str(target),str(path)],capture_output=True,text=True)
        log=result.stdout+result.stderr;(OUT/f'{name}-{kind}.log').write_text(log)
        if 'WARNING:'in log or 'ERROR:'in log:raise RuntimeError(log[-1500:])
        if target.exists():row=classify(target)
        elif 'Current top level object is empty'in log:row={'components':[],'has_solid_or_unclassified_overlap':False}
        else:raise RuntimeError(log[-1500:])
        row.update(name=kind,expected_overlap=kind=='control')
        row['passed']=row['expected_overlap']==row['has_solid_or_unclassified_overlap'];probes.append(row)
    groups=model.constraints(q,True);margin=min(float(min(v))for v in groups.values())
    return {'name':name,'side':model.side,'rear':model.rear,'stroke_mm':model.u,
        'variables':q.tolist(),'radial_tip_error_mm':float(q[0]),
        'world_tip_x_error_mm':float(model.side*q[0]),'frame_matrix':fm,'carrier_matrix':cm,
        'constraint_minima':{k:float(min(v))for k,v in groups.items()},
        'analytic_minimum_margin_mm':margin,'pose_csg_verified':margin>=-1e-9 and all(r['passed']for r in probes),
        'probes':probes,'source':{'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--verify-csg',action='store_true')
    parser.add_argument('--quick',action='store_true');args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);p,sources=base.load()
    cg_report=json.loads((ROOT/'output/feeder-cam-guide-revision/report.json').read_text())
    for name,digest in cg_report['source_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('Stale cam guide: '+name)
        sources[name]=(ROOT/name).read_text()
    revsrc=(ROOT/'cad/feeder-guide-revision.scad').read_text()
    rev={k:base.literal(revsrc,k)for k in ['revision_x0','revision_x1','revision_datum_y',
        'revision_front_retracted','revision_setting','revision_bias_y']}
    for name in ['analysis/feeder_tolerance.py','analysis/guide_revision_tolerance.py',
                 'analysis/cam_guide_error_bound.py']:
        sources[name]=(ROOT/name).read_text()
    hashes={k:hashlib.sha256(v.encode()).hexdigest()for k,v in sources.items()}
    cg=cg_report['dimensions'];rows=[];candidates=[]
    for side,rear in itertools.product([1,-1],[False,True]):
        us=([14.,17.,19.]if not rear else[1.,3.,6.])if args.quick else(
            [2.,6.,10.,14.,17.,19.]if not rear else[1.,3.,6.,10.,14.,19.])
        for u in us:
            model=CurrentModel(p,rev,cg,u,side,rear)
            for sign in [1,-1]:
                seed=np.zeros(14);seed[8]=.05;seed[1]=-.0002
                result=model.solve(seed,sign);q=result.x
                margin=float(min(model.constraints(q)))
                row={'side':side,'rear':rear,'stroke_mm':u,'direction':sign,
                    'solver_success':bool(result.success),'iterations':int(result.nit),
                    'radial_tip_error_mm':float(q[0]),'minimum_margin_mm':margin,'variables':q.tolist()}
                rows.append(row)
                if result.success and margin>=-1e-7:candidates.append((model,q))
                print(f'{side:+d} {"rear"if rear else"front"} u={u:g} sign={sign:+d}: {q[0]:.9f} margin={margin:.3g}',flush=True)
    witnesses=[]
    if args.verify_csg:
        for side,rear in itertools.product([1,-1],[False,True]):
            selected=[(m,q)for m,q in candidates if m.side==side and m.rear==rear]
            if not selected:continue
            for sign in [1,-1]:
                m,q=max(selected,key=lambda a:sign*a[1][0]);seed=np.zeros(14);seed[8]=.05;seed[1]=-.0002
                q=seed+.995*(q-seed);q[1]-=.0002
                name=f'{"right"if side==1 else"left"}-{"rear"if rear else"front"}-{"out"if sign==1 else"in"}'
                w=verify(m,q,name);witnesses.append(w)
                print('CSG',name,w['pose_csg_verified'],w['radial_tip_error_mm'],flush=True)
    stable=all(hashlib.sha256((ROOT/k).read_bytes()).hexdigest()==h for k,h in hashes.items())
    verified=[abs(w['radial_tip_error_mm'])for w in witnesses if w['pose_csg_verified']]
    report={'status':'LOCAL_SEARCH_WITH_VERIFIED_RIGID_POSES_NOT_GLOBAL_BOUND'if stable and verified else'LOCAL_SEARCH_ONLY_OR_REJECTED',
        'source_sha256':hashes,'sources_stable':stable,'cam_guide_dimensions':cg,
        'search_count':len(rows),'local_searches':rows,'witnesses':witnesses,
        'worst_error_lower_bound_mm':max(verified)if verified else None,
        'certified_global_upper_bound_mm':None,'full_gate_error_budget_passed':False,
        'limits':['Actual right rail is clipped to the datum/gib Y/Z contact regions before X inequalities are imposed.',
            'Carrier whole-box/narrow-slab inherited constraints are restrictive: they support feasible witnesses, not upper bounds.',
            'Each target is optimized separately; CSG retains all four fingers and the other three nominal poses.',
            'Pin and nut installation offsets are static seated-joint eccentricity; pin axis is rigidly tied to carrier.',
            'Scalar parallel gib setting .9 and axial float +/- .2 are included; differential jack skew is not.',
            'Local optimization and sampled strokes do not establish a global or dynamically reachable bound.',
            'Print error, part deformation, preload/friction and spring return remain outside this rigid-pose study.']}
    (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:report[k]for k in ['status','worst_error_lower_bound_mm','certified_global_upper_bound_mm']},indent=2))
    return 0 if stable else 1

if __name__=='__main__':raise SystemExit(main())

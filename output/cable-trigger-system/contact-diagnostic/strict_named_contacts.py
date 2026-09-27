#!/usr/bin/env python3
"""Exact, fixture-specific contact evidence; never modifies a CAD verdict.

All decimal coordinates are rational. No epsilon, welding, snapping or small
volume exemption is used. Each plane has an explicit source-derived rectangle
envelope. A per-plane oriented boundary-chain equality proves that opposite
projected surfaces cover the same finite region, even with different diagonals.
"""
from collections import defaultdict
from fractions import Fraction as F
from pathlib import Path
import argparse
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PLANES = [
    dict(name='Y=-54', axis=1, value=F(-54), axes=(0,2), rectangles=[
        (-22,-10,-66,9), (10,22,-66,9), (-22,22,-33,-27),
        (-24,-20,-50,-20), (20,24,-50,-20), (2,18,22,28)]),
    dict(name='Z=-66', axis=2, value=F(-66), axes=(0,1), rectangles=[
        (-18,-15,-62,-54), (15,18,-62,-54)]),
]

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def sub(a,b): return tuple(x-y for x,y in zip(a,b))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def area2(poly):
    return sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(poly,poly[1:]+poly[:1]))

def read_stl(p):
    text=p.read_text()
    nums=r'([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)'
    blocks=re.findall(r'facet\s+normal.*?endfacet',text,re.S)
    triangles=[]
    for block in blocks:
        vertices=re.findall(r'\bvertex\s+'+nums+r'\s+'+nums+r'\s+'+nums,block)
        if len(vertices)!=3: raise ValueError('Malformed ASCII facet')
        triangles.append(tuple(tuple(F(x) for x in row) for row in vertices))
    if not triangles: raise ValueError('No triangle facets; empty CSG needs separate execution evidence')
    if len(re.findall(r'\bvertex\b',text))!=3*len(triangles):
        raise ValueError('Unparsed vertex data')
    return triangles

def clip(poly,axis,value,less):
    """Exact Sutherland-Hodgman clipping to one closed half-plane."""
    if not poly: return []
    result=[]
    inside=lambda p:p[axis]<=value if less else p[axis]>=value
    for a,b in zip(poly[-1:]+poly[:-1],poly):
        ia,ib=inside(a),inside(b)
        if ia!=ib:
            t=(value-a[axis])/(b[axis]-a[axis])
            result.append(tuple(a[k]+t*(b[k]-a[k]) for k in (0,1)))
        if ib: result.append(b)
    return result if len(result)>=3 and area2(result)!=0 else []

def outside_rectangle(poly,rect):
    lo0,hi0,lo1,hi1=map(F,rect);remaining=poly;outside=[]
    for axis,value,less in [(0,lo0,False),(0,hi0,True),(1,lo1,False),(1,hi1,True)]:
        rejected=clip(remaining,axis,value,not less)
        if rejected: outside.append(rejected)
        remaining=clip(remaining,axis,value,less)
        if not remaining: break
    return outside

def inside_domain(triangle,rectangles):
    remainder=[list(triangle)]
    for rect in rectangles:
        remainder=[piece for p in remainder for piece in outside_rectangle(p,rect)]
        if not remainder: return True
    return False

def add_edge(lines,a,b):
    """Canonical rational line plus an oriented interval on that line."""
    if a==b: raise ValueError('Zero-length edge')
    A=a[1]-b[1];B=b[0]-a[0];C=a[0]*b[1]-b[0]*a[1]
    scale=A if A else B
    key=(A/scale,B/scale,C/scale)
    axis=0 if a[0]!=b[0] else 1
    lo,hi=sorted((a[axis],b[axis]));sign=1 if b[axis]>a[axis] else -1
    lines[key][lo]+=sign;lines[key][hi]-=sign

def check(triangles):
    # One fixed plane per axis prevents a six-plane finite box whitelist.
    assert len({p['axis'] for p in PLANES})==len(PLANES)<=3
    groups={p['name']:[] for p in PLANES};off=[];degenerate=[];outside=[]
    volume6=F(0)
    for i,t in enumerate(triangles):
        a,b,c=t;volume6+=dot(a,cross(b,c))
        if not any(cross(sub(b,a),sub(c,a))): degenerate.append(i);continue
        matches=[p for p in PLANES if all(v[p['axis']]==p['value'] for v in t)]
        if len(matches)!=1: off.append(i);continue
        plane=matches[0];q=[tuple(v[k] for k in plane['axes']) for v in t]
        if not inside_domain(q,plane['rectangles']): outside.append(i)
        groups[plane['name']].append(q)
    boundaries={}
    for name,triangles2d in groups.items():
        lines=defaultdict(lambda:defaultdict(int))
        for t in triangles2d:
            for a,b in zip(t,t[1:]+t[:1]): add_edge(lines,a,b)
        faults=[]
        for line,events in lines.items():
            balance=0;points=sorted(events)
            for j,x in enumerate(points):
                balance+=events[x]
                if j+1<len(points) and balance:
                    faults.append(dict(line=list(map(str,line)), interval=[str(x),str(points[j+1])],signed_multiplicity=balance))
            assert balance==0
        boundaries[name]=dict(triangles=len(triangles2d), unmatched_intervals=len(faults),first_failures=faults[:8])
    passed=bool(triangles) and not (off or degenerate or outside) and volume6==0 and all(not x['unmatched_intervals'] for x in boundaries.values())
    return dict(status='EXACT_NAMED_CONTACT_SURFACES' if passed else 'REJECTED_OR_UNRESOLVED',passed=passed,
        triangle_count=len(triangles),off_plane_triangles=off,zero_area_triangles=degenerate,
        outside_source_envelopes=outside,exact_signed_volume_mm3=str(volume6/6),plane_boundaries=boundaries)

def self_tests():
    def P(x,y,z):return tuple(map(F,(x,y,z)))
    # Both sides have different rectangle diagonals, not duplicate triangles.
    a,b,c,d=P(-18,-54,-66),P(-15,-54,-66),P(-15,-54,-60),P(-18,-54,-60)
    e,f=P(-18,-62,-66),P(-15,-62,-66)
    contact=[(a,b,c),(a,c,d),(a,d,b),(b,d,c),
             (a,e,f),(a,f,b),(a,b,e),(b,f,e)]
    thin=P(-18,-54-F('1e-14'),-60)
    wedge=[(a,c,b),(a,b,thin),(b,c,thin),(c,a,thin)]
    off_domain=P(100,-54,100)
    tests=[('two_joined_planes_opposite_different_diagonals',contact,True),
           ('open_triangle_only',[(a,b,c)],False),
           ('two_open_planes',[(a,b,c),(a,e,f)],False),
           ('one_contact_face_missing',contact[:-1],False),
           ('closed_tetrahedron_1e_minus_14_thick',wedge,False),
           ('mixed_vertex_planes_triangle',[(c,e,b)],False),
           ('paired_faces_outside_source_domain',[(a,b,off_domain),(a,off_domain,b)],False),
           ('zero_area_triangle',[(a,a,b)],False)]
    rows=[]
    for name,triangles,expected in tests:
        result=check(triangles);result.update(name=name,expected=expected)
        assert result['passed']==expected,name
        rows.append(result)
    return rows

def main():
    parser=argparse.ArgumentParser();parser.add_argument('files',nargs='*',type=Path);args=parser.parse_args()
    tests=self_tests();rows=[]
    for p in args.files:
        row=check(read_stl(p));row.update(file=str(p),sha256=sha(p));rows.append(row)
    reference=ROOT/'output/cable-trigger-system/20260927T055340003531Z/report.json'
    reference_report=json.loads(reference.read_text())
    result=dict(status='DIAGNOSTIC_ONLY_NO_EXISTING_VERDICT_MODIFIED',script_sha256=sha(Path(__file__)),
        contract={'planes':PLANES,'source':'cad/cable-trigger-input.scad ci_mount_cad_blank and cad/feeder-support-harness.scad sh_beam_blank',
                  'reference_report':str(reference),'reference_report_sha256':sha(reference),
                  'reference_source_sha256':{k:v for k,v in reference_report['source_sha256'].items()
                                            if k.endswith(('cable-trigger-input.scad','feeder-support-harness.scad'))},
                  'domain_scope':'Source rectangle contact envelopes only; drilled holes are not asserted occupied.',
                  'no_epsilon_or_volume_waiver':True},self_tests=tests,results=rows,
        limits=['Acceptance proves only a finite two-sided sheet in the named contact envelopes.',
                'It is not a closed solid, printable mesh, strength result, or full collision certificate.',
                'STL identity and stable matching source snapshot are additional mandatory conditions.',
                'A floating-point thin wedge cannot be distinguished from a real thin wedge from STL alone; both are rejected.'])
    (OUT/'strict-named-contact-report.json').write_text(json.dumps(result,indent=2,default=str)+'\n')
    print(json.dumps({'self_tests':len(tests),'all_self_tests_passed':True,
        'results':[{'file':r['file'],'status':r['status'],'off_plane':len(r['off_plane_triangles']),
                    'outside_domain':len(r['outside_source_envelopes']),
                    'boundary_faults':sum(x['unmatched_intervals'] for x in r['plane_boundaries'].values())} for r in rows]},indent=2))

if __name__=='__main__':main()

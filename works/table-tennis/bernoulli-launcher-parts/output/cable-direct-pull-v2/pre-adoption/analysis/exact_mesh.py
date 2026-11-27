"""Exact triangle-area and welded vertex-link review for exported STL files."""
from fractions import Fraction
import re
import struct


def exact_area_and_links(path):
    raw=path.read_bytes()
    binary=len(raw)>=84 and 84+50*struct.unpack_from('<I',raw,80)[0]==len(raw)
    if binary:
        matches=[]
        for i in range(struct.unpack_from('<I',raw,80)[0]):
            row=struct.unpack_from('<12f',raw,84+50*i)
            matches.extend(row[j:j+3]for j in (3,6,9))
    else:matches=re.findall(r'^\s*vertex\s+(\S+)\s+(\S+)\s+(\S+)\s*$',raw.decode(),re.M)
    if not matches or len(matches)%3:raise ValueError('Invalid STL triangle data')
    bad=[];links={}
    for i in range(0,len(matches),3):
        tri=[tuple(Fraction(s) for s in v)for v in matches[i:i+3]]
        a,b,c=tri;u=[b[k]-a[k]for k in range(3)];v=[c[k]-a[k]for k in range(3)]
        if not any((u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])):bad.append(i//3)
        rounded=[tuple(round(float(s),6)for s in point)for point in tri]
        for j,p in enumerate(rounded):
            q,r=rounded[(j+1)%3],rounded[(j+2)%3]
            graph=links.setdefault(p,{})
            graph.setdefault(q,set()).add(r);graph.setdefault(r,set()).add(q)
    faults=[]
    for point,graph in links.items():
        pending=[next(iter(graph))];seen=set()
        while pending:
            v=pending.pop()
            if v not in seen:seen.add(v);pending.extend(graph[v]-seen)
        if len(seen)!=len(graph) or any(len(v)!=2 for v in graph.values()):faults.append(point)
    return {'format':'binary'if binary else'ascii','exact_zero_area_face_indices':bad,'non_ring_vertex_links':faults,'vertex_count':len(links)}

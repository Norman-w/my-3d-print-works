from pathlib import Path
import json,re,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
O=Path(__file__).resolve().parent
R=Path(json.loads((O/'latest-run.json').read_text())['folder'])
def triangles(name):
 t=np.array(re.findall(rb'vertex\s+([-+eE.0-9]+)\s+([-+eE.0-9]+)\s+([-+eE.0-9]+)',(R/(name+'.stl')).read_bytes()),float).reshape(-1,3,3)
 x,y,z=t[:,:,0],t[:,:,1],t[:,:,2];q=math.sqrt(.5)
 return np.stack([q*(-x+75+z-5),q*(x-75+z-5),y+82],axis=2)
def angle(u):
 lo,hi=0,math.radians(30)
 for _ in range(60):
  a=(lo+hi)/2;x=60*math.sin(a)+28.8;y=60*math.cos(a);d=math.hypot(x,y);p=max(0,math.atan2(x,y)-math.acos(60/d));l=.2+60*p+math.sqrt(d*d-3600)-29
  if l<u:lo=a
  else:hi=a
 return (lo+hi)/2
def rotate(t,a):
 c,s=math.cos(a),math.sin(a);return t@np.array([[c,-s,0],[s,c,0],[0,0,1]])
def cable(u):
 a=angle(u);b=np.array([60*math.sin(a),60*math.cos(a),2]);d=math.hypot(b[0]+28.8,b[1]);p=max(0,math.atan2(b[0]+28.8,b[1])-math.acos(60/d));v=np.linspace(0,p,90)
 return np.vstack([[-39,60,2],[-29,60,2],np.column_stack([-28.8+60*np.sin(v),60*np.cos(v),np.full_like(v,2)]),b])
body=triangles('body');lever=triangles('lever');cap=triangles('terminal-cap');cover=triangles('cover')
fig=plt.figure(figsize=(13,9),layout='constrained')
for i,u in enumerate([0,20]):
 ax=fig.add_subplot(2,2,i+1)
 for t,c,alpha in [(body,'#97bcc9',1),(rotate(lever,angle(u)),'#e7a244',1),(rotate(cap,angle(u)),'#f1cb80',.45)]:
  idx=np.argsort(t[:,:,2].mean(1));ax.add_collection(PolyCollection(t[idx,:,:2],facecolors=c,edgecolors='none',alpha=alpha))
 path=cable(u);ax.plot(path[:,0],path[:,1],color='#008b51',lw=2.3)
 ax.scatter(path[-1,0],path[-1,1],s=95,c='#838b90',zorder=8)
 ax.set(xlim=(-49,35),ylim=(40,76),aspect='equal',xlabel='Local X / mm',ylabel='Local Y / mm',title=f'Actual mesh top view, u={u} mm; cap translucent')
 ax.grid(alpha=.2)
ax=fig.add_subplot(2,2,3,projection='3d')
for t,c,al in [(body,'#97bcc9',.8),(lever,'#e7a244',1),(cap,'#f1cb80',1)]:
 ax.add_collection3d(Poly3DCollection(t,facecolors=c,edgecolors=c,linewidth=0,alpha=al,shade=True))
ax.set(xlim=(-65,75),ylim=(-112,76),zlim=(-15,20),xlabel='X',ylabel='Y',zlabel='Z',title='Fixed body + direct lever + screw cap')
ax.set_box_aspect((140,188,35));ax.view_init(elev=38,azim=-70)
ax=fig.add_subplot(2,2,4,projection='3d')
ax.add_collection3d(Poly3DCollection(lever,facecolors='#e7a244',edgecolors='#e7a244',linewidth=0,shade=True))
ct=cap.copy();ct[:,:,2]+=18
ax.add_collection3d(Poly3DCollection(ct,facecolors='#f1cb80',edgecolors='#f1cb80',linewidth=0,shade=True))
for x,y in [(2,54),(2,66)]:ax.plot([x,x],[y,y],[3.1,22.5],color='#56636d',ls='--')
ax.set(xlim=(-12,12),ylim=(45,75),zlim=(-5,30),xlabel='X',ylabel='Y',zlabel='Z',title='Terminal cap opens +Z after main cover removal')
ax.set_box_aspect((24,30,35));ax.view_init(elev=29,azim=-66)
fig.suptitle('491ded7714 diagnostic only | actual native STL + analytic R60 path',fontsize=14)
fig.savefig(R/'candidate-views.png',dpi=145)
print(R/'candidate-views.png')

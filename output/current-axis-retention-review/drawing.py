from pathlib import Path
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Circle,Rectangle
P=Path(__file__).resolve().parent
fig=plt.figure(figsize=(11.7,8.3));gs=fig.add_gridspec(2,2,height_ratios=[1,1.1]);a=fig.add_subplot(gs[0,0]);b=fig.add_subplot(gs[0,1]);c=fig.add_subplot(gs[1,:]);c.axis('off')
r=12/math.sqrt(3);v=[(r*math.cos(math.radians(30+60*k)),r*math.sin(math.radians(30+60*k)))for k in range(6)]
a.add_patch(Polygon(v,fc='#e4c390',ec='black'));a.add_patch(Circle((0,0),4.1,fc='white',ec='black'));a.axhline(0,color='#777',lw=.5,ls='-.');a.axvline(0,color='#777',lw=.5,ls='-.');a.annotate('',xy=(-6,-8),xytext=(6,-8),arrowprops={'arrowstyle':'<->'});a.text(0,-8.6,'AF 12.00  +0 / -0.03',ha='center',fontsize=11);a.text(0,0,'BORE\nD8.20 +0.05 / 0',ha='center',va='center',fontsize=10);a.set_xlim(-10,10);a.set_ylim(-10,9);a.set_aspect('equal');a.axis('off');a.set_title('End view / six-flat form retention')
b.add_patch(Rectangle((0,-6),11,12,fc='#e4c390',ec='black'));b.add_patch(Rectangle((0,-4.1),11,8.2,fc='white',ec='black'));b.axhline(0,color='#777',lw=.5,ls='-.');b.annotate('',xy=(0,-8),xytext=(11,-8),arrowprops={'arrowstyle':'<->'});b.text(5.5,-8.6,'11.00 +0 / -0.03',ha='center',fontsize=11);b.text(5.5,0,'Through bore\n0.10 max inner edge break',ha='center',va='center',fontsize=10);b.set_xlim(-4.5,15.5);b.set_ylim(-10,9);b.set_aspect('equal');b.axis('off');b.set_title('Side section / dimensions in mm')
notes='''DESIGN REQUIREMENTS - NOT A SUPPLIER CATALOGUE OR RELEASED PURCHASE DRAWING

Material: unfilled POM-C, machined. Commercial grade and supplier not selected.
AF: 11.97..12.00; bore: 8.20..8.25; overall length (including face extremes): 10.97..11.00.
Bore axis position relative to six-flat centre: diameter 0.05 maximum.
Bore cylindricity: 0.02 maximum; end parallelism: 0.02 maximum.
End-face perpendicularity to bore axis: 0.03 maximum.
Outer edge break: 0.05 maximum; bore edge break: 0.10 maximum; no sharp burrs.
For the conservative area budget, all bore-face void lies inside the centred R4.25 envelope.

PETG rotor socket: AF12.4 CAD; finished acceptance window AF12.2..12.6 is a DESIGN LIMIT,
not an assumed printer capability. No interference fit, adhesive or extra retention screw.
Both existing thrust washers required: catalogue candidate OD15.5..16, ID10..10.5, t0.225..0.275.
Material/finish, friction, life, washer flex and coupled axis/rotor geometry remain unqualified.
Do not print the POM bush or supplier washer STL as a substitute for the specified component.'''
c.text(.02,.96,notes,va='top',fontfamily='monospace',fontsize=9.8,linespacing=1.45)
fig.suptitle('Hexagonal replaceable input bush - isolated design candidate',fontsize=16,y=.985);fig.tight_layout(rect=[0,0,1,.965]);fig.savefig(P/'pom-hex-bush-drawing.png',dpi=170);fig.savefig(P/'pom-hex-bush-drawing.pdf')

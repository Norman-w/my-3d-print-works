#!/usr/bin/env python3
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Circle,Wedge
import numpy as np
OUT=Path(__file__).resolve().parent
fig=plt.figure(figsize=(13,9.2),layout='constrained')
gs=fig.add_gridspec(2,2,height_ratios=[1,1.15],width_ratios=[1.4,1])
ax=fig.add_subplot(gs[0,0]);top=fig.add_subplot(gs[0,1]);note=fig.add_subplot(gs[1,:]);note.axis('off')
ax.set_title('A-A SECTION — cup mouth faces shoulder (+ input Z)',loc='left',fontsize=12)
p=.525;T=3;r=.625
pts=np.array([[-6,0],[-4.015,0],[-4.015,p],[-3.425,p],[-3.425,p+r],[-3.225,p+r],[-3.225,T],[-6,T]])
for poly in [pts,pts*np.array([-1,1])]:ax.add_patch(Polygon(poly,facecolor='#dbe5e9',edgecolor='#253440',hatch='///',linewidth=1.3))
ax.axvline(0,color='#65707b',ls='-.',lw=.7)
for x in [-3.993,3.993]:ax.plot([x,x],[-.7,p-.05],color='#2875bd',ls='--',lw=1.2)
for s in [-1,1]:ax.plot([s*3.5,s*3.9],[p,p],color='#e4a128',lw=5,solid_capstyle='butt')
def dim(x,y0,y1,label,dx=0):
 ax.annotate('',(x,y0),(x,y1),arrowprops={'arrowstyle':'<->','lw':.8});ax.text(x+dx,(y0+y1)/2,label,ha='right'if dx<=0 else'left',va='center',fontsize=10)
dim(-6.6,0,T,'T 2.95–3.05',-.1)
ax.annotate('C: mouth / plastic capture face',(-5,0),(-2,-1),arrowprops={'arrowstyle':'->'},fontsize=9)
ax.annotate('B: metal shoulder seat\np = 0.50–0.55 from C',(3.7,p),(4.9,-.7),arrowprops={'arrowstyle':'->'},fontsize=9)
ax.annotate('Root relief\n0.60–0.65 deep from B',(3.425,.95),(5,1.2),arrowprops={'arrowstyle':'->'},fontsize=9,bbox={'facecolor':'white','edgecolor':'none','alpha':.95,'pad':1})
ax.annotate('D: nut seat',(-4.5,T),(-2,3.9),arrowprops={'arrowstyle':'->'},fontsize=10)
ax.text(0,1.9,'Through Ø6.40–6.50',ha='center',fontsize=10)
ax.text(0,.2,'Pilot Ø8.02–8.04',ha='center',fontsize=10)
ax.text(0,.93,'Relief Ø6.80–6.88',ha='center',fontsize=10)
ax.set_xlim(-10,10);ax.set_ylim(4.6,-1.4);ax.set_aspect('equal');ax.axis('off')
top.set_title('SHOULDER-SIDE VIEW',loc='left',fontsize=12)
for rr,ls in [(6,'-'),(4.015,'-'),(3.425,'--'),(3.225,'--')]:top.add_patch(Circle((0,0),rr,fill=False,lw=1.3 if ls=='-'else.8,ls=ls,color='#253440'))
top.add_patch(Wedge((0,0),3.9,0,360,width=.4,facecolor='#e4a128',alpha=.45))
top.axhline(0,color='#65707b',ls='-.',lw=.7);top.axvline(0,color='#65707b',ls='-.',lw=.7)
top.annotate('OD Ø11.95–12.00',(4.5,4),(-6,7),arrowprops={'arrowstyle':'->'},fontsize=10)
top.text(0,-7.2,'Gold: guaranteed projected seat Ø7.0–7.8',ha='center',fontsize=10)
top.set(xlim=(-8,8),ylim=(-8,8),aspect='equal');top.axis('off')
left='''CW-01  —  MACHINING REQUIREMENT / NOT A PURCHASED PART
Material: machined SUS304; strength and torque not qualified.
Nominal solid thickness 3.00; minimum web below relief = 1.75 mm.

Datum A: pilot bore axis. Datum B: pilot floor / metal seat.
C: cup mouth (plastic capture). D: rear nut face.
Relief, through-bore and OD position: cylindrical zone Ø0.02 to A.
B flatness ≤0.005; B perpendicularity to A ≤0.005.
C/D flatness ≤0.005; parallelism to B ≤0.01.
Functional sizes include form; surface finish Ra1.6 or better.

Pilot mouth lead-in depth ≤0.05; pilot-floor inside R≤0.05.
Root hole: finished Ø6.88 maximum includes all deburring.
No burr or tool radius may consume the gold shoulder annulus.'''
right='''REQUIRED MATCHED SHAFT / SEATING CONDITIONS
Last 0.60 before tail shoulder: continuous Ø7.986–7.995 pilot.
Outer shoulder-edge break ≤0.05; shaft face flat/perpendicular
to the g6 axis each ≤0.005. These are NEW acceptance requests.
Fully seated assembly tilt ≤0.2°; a short pilot alone cannot
exclude every tilted edge-only seating condition.

e ≤ 0.027 + 0.010 + 2.60 tan(0.2°) = 0.04608 < 0.050.
The matched shaft tail/root envelope must also be confirmed.

CAPTURE / CLAMP CHAIN — DO NOT USE OLD FLAT-WASHER STACK
Captured metal span = shoulder length L minus pilot depth p.
L=27±0.05 → 26.40–26.55; nominal shell span26 → float0.40–0.55.
Shoulder-to-nut thickness T−p = 2.40–2.55.
Seat area ≥9.299 mm² is geometric; no allowable load assigned.'''
note.text(0,1,left,va='top',fontsize=10.5,linespacing=1.55,fontfamily='DejaVu Sans')
note.text(.53,1,right,va='top',fontsize=10.5,linespacing=1.55,fontfamily='DejaVu Sans')
fig.suptitle('CW-01  Centering cup washer — isolated candidate — millimetres',fontsize=17,fontweight='bold')
fig.text(.5,.012,'2026-09-27 | Dimensions govern; not to scale. No production CAD, machining order or print release.',ha='center',fontsize=9)
fig.savefig(OUT/'machining-drawing.png',dpi=170)
fig.savefig(OUT/'machining-drawing.pdf')

#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,math,re,subprocess
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from shapely.geometry import Point,Polygon,box
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hexagon(af):return Polygon([(af/math.sqrt(3)*math.cos(math.radians(30+60*k)),af/math.sqrt(3)*math.sin(math.radians(30+60*k)))for k in range(6)])
def disk(r):return Point(0,0).buffer(r,quad_segs=2048)
def lens(r,R,e):
 if e<=R-r:return math.pi*r*r
 return r*r*math.acos((e*e+r*r-R*R)/(2*e*r))+R*R*math.acos((e*e+R*R-r*r)/(2*e*R))-.5*math.sqrt((-e+r+R)*(e+r-R)*(e-r+R)*(e+r+R))
# Lower-envelope end-face shapes include worst specified stock and both edge breaks.
hexface=hexagon(11.97-2*.05)
dface=disk(11.97/2-.05).intersection(box(-20,-20,5.47-.05,20))
r_bore_face=8.25/2+.10+.025;rw_i=10.5/2;rw_o=15.5/2
areas=[]
for name,face in [('hex',hexface),('single-flat-D',dface)]:
 for e in [1.3,1.475,1.5]:
  guaranteed_outer=face.intersection(disk(rw_o-e))
  # Washer OD covers this centered crop at every offset <=e.
  # Its central void can remove no more than disk(ID/2) minus its overlap
  # with the bush bore; the bore/void overlap is smallest at offset=e.
  lower=guaranteed_outer.area-math.pi*r_bore_face**2-math.pi*rw_i**2+lens(r_bore_face,rw_i,e)
  areas.append({'shape':name,'eccentricity_bound_mm':e,'washer_OD_min':15.5,'washer_ID_max':10.5,'end_face_shape_area':face.area,'guaranteed_outer_overlap_area':guaranteed_outer.area,'bore_end_radius_max':r_bore_face,'bore_hole_lens_area_lower':lens(r_bore_face,rw_i,e),'positive_bearing_area_lower_bound_mm2':lower,'method':'Analytic circle-lens subtraction and inscribed polygon crop. Lower bound for all offset directions and magnitudes <=e, not a sampled minimum or strength claim.'})
 assert min(a['positive_bearing_area_lower_bound_mm2']for a in areas if a['shape']==name)>0
old=disk(6.1);hs=hexagon(12.4);ds=disk(6.2).intersection(box(-20,-20,5.7,20))
# Check prospective part source identities and locked supplier facts only.
files=[ROOT/'cad/cable-trigger-input.scad',ROOT/'cad/parameters.scad',ROOT/'output/current-axis-fit-selection/supplier/report.json',ROOT/'output/current-axis-supply-review/report.json',OUT/'candidate.scad',Path(__file__)]
sources={str(p.relative_to(ROOT)):sha(p)for p in files}
report={'status':'HEX_POSITIVE_RETENTION_SELECTED_FOR_ISOLATED_CANDIDATE_NOT_RELEASED','created_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':sources,
 'source_basis':'Current formal rotor and separate supplier reports; main axle hardware is not adopted or supplied by this candidate.',
 'design_requirements_not_supplier_facts':{'material':'unfilled machined POM-C; grade/supplier unselected','AF':[11.97,12],'ID':[8.20,8.25],'length':[10.97,11],'bore_cylindricity_max':.02,'bore_to_hex_center_position_diameter_max':.05,'end_parallelism_max':.02,'end_perpendicularity_to_bore_max':.03,'outer_edge_break_max':.05,'inner_edge_break_max':.1,'socket_AF_CAD':12.4,'finished_socket_acceptance_AF':[12.2,12.6],'acceptance_status':'Design acceptance bounds, not a claim that FDM reaches them; no disposable test coupon required.'},
 'shape_comparison':{'hex':{'retention':'six flats, existing washer capture','min_bulk_wall':11.97/2-8.25/2-.025,'min_end_face_wall':(11.97/2-.05)-(8.25/2+.1+.025),'nominal_hub_min_radial_wall':12-(12.4/math.sqrt(3)),'material_removed_from_old_hole_area':hs.difference(old).area,'material_added_to_old_hole_area':old.difference(hs).area},'single_flat_D':{'outer_D_design':[11.97,12],'flat_distance_design':[5.47,5.5],'socket_outer_D':12.4,'socket_flat_distance':5.7,'min_bulk_wall':5.47-8.25/2-.025,'min_end_face_wall':5.47-.05-(8.25/2+.1+.025),'material_removed_from_old_hole_area':ds.difference(old).area,'material_added_to_old_hole_area':old.difference(ds).area,'required_CSG':'Union a solid plug overlapping the old bore rim, then cut new D opening; difference-only on existing Ø12.2 hole cannot add its key.'}},
 'washer_bounds_from_supplier_report':{'part':'SWSPS16-10-.25','OD':[15.5,16],'ID':[10,10.5],'t':[.225,.275],'status':'catalogue combination; archived radial drawing not current revision certificate; not purchased'},
 'eccentricity':{'washer_to_7p9_shaft':1.3,'shaft_to_bush_bore_max':.175,'sum_before_bore_position':1.475,'bore_position_radius_max':.025,'conservative_sum':1.5,'definition':'1.3 alone does not cover bore/shaft clearance or bore-to-hex position. Add .175 and .025. Bore end void is also conservatively enclosed in a centered R4.25 disk; this deliberately over-bounds position twice for the area lower bound.'},
 'bearing_area_bounds':areas,
 'axial_capture':{'planar_min_bush_width_after_outer_edge_break_hex':11.87,'planar_min_bush_width_after_outer_edge_break_D':11.97/2-.05+5.47-.05,'washer_max_aperture':10.5,'interpretation':'Each planar end section is wider than washer aperture; positive partial bearing persists for stated offset. This does not prove tilt escape, washer flex/strength or arbitrary pose; two cheeks, axle and assembled washers required.'},
 'internal_stack':{'housing_nominal':12,'rotor_nominal':11,'bush_max':11,'two_washer_t':[.45,.55],'unloaded_axial_gap_if_ideal_print':[.45,.55],'bush_independent_axial_float_if_centered_and_min_length':.03,'warning':'POM length tolerance is not a tolerance for PETG rotor/cavity. If bush shorter it may float between washers; no press-fit or adhesive required.'},
 'scope':['Hex key prevents bush rotation relative to lever after small clearance backlash; no shaft-to-housing antirotation implied.','Axle may rotate in fixed PETG support bores; they remain potential sliding interfaces.','Existing two thrust washers trap bush only when assembled between cheeks; removing cover releases the stack for bench service.','No final bearing material/grade, lubrication, friction, wear, side-M3 load, nut torque or supplier purchase accepted.'],
 'CAD_modified':'isolated output candidate only','production_CAD_modified':False,'manufacturing_release':False,'physical_acceptance':False}
(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
fig,ax=plt.subplots(1,2,figsize=(10,4.5))
for a,name,outer,socket in [(ax[0],'Hex AF12 / socket AF12.4',hexagon(12),hs),(ax[1],'D12 + flat5.5 / socket D12.4 + flat5.7',disk(6).intersection(box(-20,-20,5.5,20)),ds)]:
 for poly,color,alpha,label in [(disk(12),'#e5e7eb',1,'Rotor hub OD24'),(socket,'#fff',1,'Socket'),(outer,'#e7ba75',.95,'POM bush')]:
  x,y=poly.exterior.xy;a.fill(x,y,c=color,alpha=alpha,ec='#444',lw=.8,label=label)
 for rad,color,style,label in [(4.1,'white','-','Bore D8.2'),(6.1,'#cf4038','--','Old hole D12.2')]:
  x,y=disk(rad).exterior.xy
  if color=='white':a.fill(x,y,c=color,ec='#333')
  else:a.plot(x,y,color=color,ls=style,lw=1,label=label)
 a.set_aspect('equal');a.set_xlim(-8,8);a.set_ylim(-8,8);a.set_title(name,fontsize=10);a.set_xlabel('local X (mm)');a.grid(alpha=.15)
ax[0].set_ylabel('local Y (mm)');fig.suptitle('Retention shape comparison; source design, not printed or machined acceptance',fontsize=11);fig.tight_layout();fig.savefig(OUT/'profile-comparison.png',dpi=170)
print(json.dumps({'areas':areas,'shape_comparison':report['shape_comparison'],'report_sha256':sha(OUT/'report.json')},ensure_ascii=False,indent=2))

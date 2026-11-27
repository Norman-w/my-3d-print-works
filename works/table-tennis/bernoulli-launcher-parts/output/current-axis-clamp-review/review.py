#!/usr/bin/env python3
"""Read-only source-derived axis clamp audit. No CSG, redesign or FEA claim."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,math,re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
SRC=ROOT/'cad/cable-trigger-input.scad';text=SRC.read_text()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rel(p):return str(Path(p).resolve().relative_to(ROOT))
def snippet(literal):
 assert text.count(literal)==1,(literal,text.count(literal))
 return {'file':rel(SRC),'line':text[:text.index(literal)].count('\n')+1,'literal':literal}
anchors=[
 'ci_axis_body_z=[-12,-4];','ci_axis_lever_z=[-3.5,7.5];','ci_axis_cover_z=[8,14];','ci_axis_sleeve_z=[-5.5,9.5];',
 'ci_zcyl(0,0,-5.5,1.6,8.3);','ci_zcyl(0,0,7.9,1.6,8.3);','ci_zcyl(0,0,-13,28,4.5);','ci_zcyl(0,0,7,8+sweep,4.5);',
 'ci_zring(0,0,-5.5,15,8,4.3);','for(z=[-3.75,7.5])ci_zring(0,0,z,.25,16,8.4);',
 'ci_zbolt(0,0,14.8,35,4,7,4,3);','ci_zring(0,0,14,.8,9,4.3);','ci_zring(0,0,-12.8,.8,9,4.3);',
 'difference(){ci_zhex(0,0,-16,3.2,7);ci_zcyl(0,0,-16.1,3.4,4.1);}',
 'for(p=ci_cheek_posts){ci_zcyl(p[0],p[1],-12,20,14);',
 'translate([p[0]-4,p[1]-4,7.9])cube([8,8,1.6]);',
 'translate([p[0]-4.2,p[1]-4.2,7.9])cube([8.4,8.4,1.8]);',
 'ci_zbolt(p[0],p[1],14.5,30,3,5.5,3,2.5);',
 'ci_zring(0,0,-3.5,11,12,8.2);',
]
evidence=[snippet(s)for s in anchors]
watch=[SRC,ROOT/'cad/parameters.scad',ROOT/'output/current-axis-supply-review/report.json',ROOT/'output/current-axis-supply-review/README.md',ROOT/'output/current-assembly-package/runs/20260927T122149439656Z/hardware.csv']
sources={rel(p):sha(p)for p in watch}
faces=[
 ('rear nut',-16,-12.8,'metal; M4 SW7 H3.2'),('rear outer washer',-12.8,-12,'metal; OD9 ID4.3 t.8'),
 ('body between outer washer and sleeve seat',-12,-5.5,'PETG; axial thickness 6.5, central through bore D4.5'),
 ('metal sleeve',-5.5,9.5,'OD8 ID4.3 L15'),('cover between sleeve seat and outer washer',9.5,14,'PETG; axial thickness 4.5, central through bore D4.5'),
 ('front outer washer',14,14.8,'metal; OD9 ID4.3 t.8'),('screw head',14.8,18.8,'M4x35 underhead; OD7 H4'),
 ('rotating lever and bush',-3.5,7.5,'11 mm; bush OD12 ID8.2'),('rear thrust washer',-3.75,-3.5,'OD16 ID8.4 t.25'),('front thrust washer',7.5,7.75,'OD16 ID8.4 t.25'),
]
lengths=[]
for L in [14.98,15,15.02]:
 gap=15-L
 lengths.append({'sleeve_length':L,'seat_distance_with_columns_closed':15,'gap_positive_interference_negative':gap,'if_seated_in_rear_pocket_front_end_z':-5.5+L,'first_contacts':('Both cheek-column stop faces at z8 can close while sleeve has total .02 end gap; sleeve may float or touch either single seat.'if L<15 else 'Sleeve seats and cheek-column stop faces can nominally close simultaneously.'if L==15 else 'Rear-seated sleeve contacts cover roof .02 before cheek-column stop faces close; cover lift .02 or deformation required.'),'not_inferred':'No preload/deflection/friction/jamming value is calculated.'})
proposal={
 'status':'ROOT_PROPOSED_UNIMPLEMENTED_CONCEPT',
 'sleeve_z':[-12.2,14.2],'nominal_L':26.4,'conditional_L_bounds':[26.38,26.42],
 'length_tolerance_status':'Uses the same +/-0.02 only as a calculation input; no new supplier configuration verification here.',
 'required_changes':['Body and cover center bores become through D8.3; old blind seats removed.','Move rear washer to z[-13,-12.2], front washer to [14.2,15.0], screw underhead to15.0 and nut to[-16.2,-13]. Retain hardware dimensions. Old hardware positions would overlap sleeve ends by .2 each.'],
 'metal_clamp_path':'head -> front washer -> entire sleeve -> rear washer -> nut; PETG bypassed only if actual sleeve length exceeds actual closed housing outer-face span.',
 'remaining_M4x35_tip_z':-20,'nut_lower_z':-16.2,'nominal_tip_beyond_nut':3.8,
 'total_axial_float_metal_cartridge_nominal':.4,'conditional_total_axial_float_if_housing_span26':[.38,.42],
 'capture':{'washer_OD':9,'housing_bore_D':8.3,'centered_radial_lip':.35,'sleeve_min_OD':7.9,'max_radial_eccentricity':.2,'minimum_one_side_lip_with_eccentricity_only':.15,'status':'Nominal positive capture, not tolerance/strength proof. Both washers/nut/head must remain; no positive antirotation to body is present.'},
 'moving_clearance':'Internal cavity and lever/thrust stack unchanged, so their nominal .5 total endplay remains. Axle-cartridge float is a separate .4 DOF and is not additional lever travel.',
 'housing_retention':'The two side M3 screws/columns hold the cover to the body. The center fastener clamps only its own metal cartridge in this proposal; it no longer provides center PETG preload.',
 'constraints_to_define':['Treat the cartridge as deliberately floating in rotation/axial translation, or add an explicit datum/capture/antirotation scheme. It cannot be called a fixed shaft merely because its own screw is tight.','For metal-only clamping require L_min > H_outer_max including outer-face flatness/parallelism and print tolerance; the .4 nominal clearance alone does not prove this.','Confirm washer minimum OD vs maximum through-hole and eccentricity, edge bearing under axial loads, and side-M3 cover load path.','Changed bore diameter, moved screw head/nut and service positions need current CAD interference/reuse/manufacturing identity checks before adoption. No such checks were run here.'],
}
report={
 'status':'PRINTED_END_SEATS_IN_SERIES_CONFIRMED_METAL_ONLY_CLAMP_CLAIM_NOT_SUPPORTED',
 'created_utc':datetime.now(timezone.utc).isoformat(),'method':'Source literal/coordinate audit and exact scalar arithmetic; no production CAD modification, native CSG, slice, print or FEA.',
 'source_sha256':sources,'script_sha256':sha(__file__),'source_evidence':evidence,
 'coordinate_convention':'Input local z; CAD Y = local z - 82, axis CAD X=75,Z=5.',
 'current_face_stacks':[{'part':name,'local_z':[a,b],'cad_Y':[a-82,b-82],'description':d}for name,a,b,d in faces],
 'current_primary_series_load_path':['M4x35 head underside z14.8','outer washer z14..14.8','PETG cover z9.5..14 (4.5 mm)','sleeve z-5.5..9.5 (15 mm)','PETG body z-12..-5.5 (6.5 mm)','outer washer z-12.8..-12','nut top z-12.8'],
 'current_parallel_path':'Cover -> two cheek-column contacts at z8 -> body. Their own M3x30 screws close these faces. Column keys top9.5 vs cover key-pocket roof9.7 leave .2 clearance and are not the axial stop.',
 'closed_column_seat_distance':15,'printed_axial_material_in_series':11,
 'screw':{'designation_from_source_and_BOM':'M4x35','underhead_z':14.8,'length_underhead':35,'tip_z':-20.2,'nut_lower_z':-16,'nominal_protrusion_beyond_nut':4.2,'M4x30_is_current_axis':False},
 'lever_clearance':{'inner_cavity_z':[-4,8],'gap12':12,'lever_and_bush_length':11,'two_thrust_washer_total':.5,'nominal_total_endplay':.5,'nominal_end_gap_each':.25,'not_a_tolerance_result':True},
 'seat_annulus':{'printed_through_hole_D':4.5,'sleeve_ID':4.3,'sleeve_OD':8,'nominal_contact_area_each_mm2':math.pi/4*(8**2-4.5**2),'inner_radial_overhang_of_sleeve_end_mm':.1,'status':'Most tube end rests on PETG annulus; small inner ring overhangs D4.5 through bore.'},
 'length_cases':lengths,
 'overconstraint_conclusion':'No nominal geometric solid overlap at L15. However the central sleeve/seat chain and two remote column stops redundantly set the same cover separation. L variation cannot be absorbed while insisting all three stops are rigidly closed; short tube loses the central stop, long tube needs deformation or lifted columns. This does not by itself prove the lever jams.',
 'unimplemented_through_sleeve_proposal':proposal,
 'limits':['No actual PETG dimensions, stiffness, creep, tightening torque, bearing supply tolerances or axial force are known.','No value of screw preload or loss of lever running clearance is inferred from the .02 mismatch alone.','The current BOM correctly says M4x35 for this axis; the M4x30 premise was not used.'],
 'production_CAD_changed':False,'manufacturing_release':False,'physical_acceptance':False,
}
(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
# Explanatory source-derived half section: rectangles represent nominal axial annuli,
# not a native model render or contact-stress simulation.
fig,axes=plt.subplots(2,1,figsize=(11,6),sharex=True,sharey=True)
colors={'PETG':'#d4a35d','steel':'#7c8799','bush':'#3eaf9a','thrust':'#d54b4b'}
def rect(ax,z0,z1,r0,r1,c,label=None):ax.add_patch(Rectangle((z0,r0),z1-z0,r1-r0,facecolor=colors[c],edgecolor='#243040',lw=.6,label=label))
for idx,ax in enumerate(axes):
 if idx==0:
  rect(ax,-12,-5.5,2.25,12,'PETG','PETG');rect(ax,-5.5,-4,4.15,12,'PETG');rect(ax,8,9.5,4.15,12,'PETG');rect(ax,9.5,14,2.25,12,'PETG')
  lo,hi=-5.5,9.5;rw=(-12.8,-12);fw=(14,14.8);head=14.8;nut=(-16,-12.8)
 else:
  rect(ax,-12,-4,4.15,12,'PETG','PETG');rect(ax,8,14,4.15,12,'PETG');lo,hi=-12.2,14.2;rw=(-13,-12.2);fw=(14.2,15);head=15;nut=(-16.2,-13)
 rect(ax,lo,hi,2.15,4,'steel','Sleeve / clamp hardware');rect(ax,*rw,2.15,4.5,'steel');rect(ax,*fw,2.15,4.5,'steel');rect(ax,head,head+4,0,3.5,'steel');rect(ax,*nut,2.05,3.5,'steel');rect(ax,head-35,head,0,2,'steel')
 rect(ax,-3.5,7.5,4.1,6,'bush','Bush');rect(ax,-3.5,7.5,6.1,12,'PETG')
 rect(ax,-3.75,-3.5,4.2,8,'thrust','Thrust washer');rect(ax,7.5,7.75,4.2,8,'thrust')
 for z in [-12,-5.5,-4,8,9.5,14]:ax.axvline(z,color='#222',lw=.4,ls=':')
 ax.set_ylim(0,13);ax.grid(axis='x',alpha=.2);ax.set_ylabel('Radius r (mm)')
axes[0].set_title('Current source: PETG 6.5 + sleeve 15 + PETG 4.5 in series (M4 x 35)')
axes[1].set_title('Unimplemented through-sleeve concept: metal clamp, but 0.4 mm cartridge endplay')
axes[0].legend(loc='upper center',ncol=4,fontsize=8)
axes[1].set_xlabel('Input local z (mm); source-derived half section, not native CAD / stress result')
axes[1].set_xlim(-21,20);fig.tight_layout();fig.savefig(OUT/'axis-section.png',dpi=170)
assert sources=={rel(p):sha(p)for p in watch}
print('REPORT',OUT/'report.json','SHA',sha(OUT/'report.json'))

// Isolated HCDG8-30 / supplied NETW7 E-clip candidate. Units mm.
// NOT adopted production CAD. Invoke ci_origin=[75,-85,5], explicit $fn=72.
use <../../cad/cable-trigger-input.scad>
use <../current-axis-offset-candidate/candidate.scad>
use <../current-axis-retention-review/candidate.scad>
$fn=72;
ec_part="assembly";
ec_u=0;
ec_q=.7;

module ec_body(){offset_body();}
module ec_cover(){offset_cover();}
module ec_plastics(){ec_body();ec_cover();}
module ec_ring(z,h,od,id){difference(){
 translate([0,0,z])cylinder(h=h,d=od);
 translate([0,0,z-.01])cylinder(h=h+.02,d=id);
}}

// Catalogue nominal shape, not the manufacturer's exact CAD.
// L is measured from under-head to NEAR wall of the groove; total is L+N.
// u=7.8 and n=1.5 under-head relief are REFERENCE dimensions only.
module ec_pin(q=ec_q,L=30.05,N=3,M=.95,d=7.045,D=7.9905,H=12,T=2){
 zhead=14+q;
 difference(){union(){
  translate([0,0,zhead-L-N])cylinder(h=L+N,d=D);
  translate([0,0,zhead])cylinder(h=T,d=H);
 }
  ec_ring(zhead-L-M,M,H+1,d);
  ec_ring(zhead-1.5,1.5,H+1,7.75);
 }
}
module ec_tail_washers(){for(z=[-15.2,-13.6])ec_ring(z,1.6,15,8.5);}

// A separately declared engineering SPACE BUDGET, not an actual E-clip mesh.
// Any fully installed clip and its allowed posture must remain in this volume.
// R10 and +/-1 axial overhang are acceptance requirements, not supplier values.
// Published L30..30.1, M.9..1, t.76..84, T_washers2.8..3.6, Hplastic26
// yield capture limit .4..1.54; instantaneous q is 0..that limit.
module ec_clip_space(){
 translate([0,0,-18.1])cylinder(h=4.64,r=10/cos(180/72));
}

// Coaxial sweep of shaft/head/tail washers over all declared axial floats.
// Hhead<=16 and N<=6 deliberately exceed nominal12/3; not factory tolerances.
// Head-root D9 x2.5 is an engineering acceptance bound; source root is reference.
module ec_axis_space(){
 k=1/cos(180/72);
 translate([0,0,-22.1])cylinder(h=37.64,d=8*k);
 translate([0,0,11.5])cylinder(h=4.04,d=9*k);
 translate([0,0,14])cylinder(h=3.64,d=16*k);
 ec_ring(-17.1,5.1,15*k,8.4);
}

module ec_assembly(){
 color([.13,.48,.72])ec_plastics();ar_rotor(ec_u);
 color([.73,.76,.81]){ec_pin();ec_tail_washers();offset_fixed_metal();}
 // Translucent required installation envelope; never labelled an E-clip solid.
 color([.94,.38,.12,.2])ec_clip_space();
 color([.25,.27,.29])ci_local_cable(ec_u);
}
if(ec_part=="pin")ci_to_cad()ec_pin();
else if(ec_part=="axis-space")ci_to_cad()ec_axis_space();
else if(ec_part=="clip-space")ci_to_cad()ec_clip_space();
else if(ec_part=="assembly")ci_to_cad()ec_assembly();
else if(ec_part=="local-assembly")ec_assembly();
else if(ec_part=="section")intersection(){ec_assembly();
 translate([-28,-.001,-30])cube([56,100,55]);}

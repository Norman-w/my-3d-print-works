// v3 external mechanical demolding aid, mm. Original v2 cavity unchanged.
// Jack bolts push METAL washers on neighboring mold blocks, never PU.
use <../guard-casting-mold-v2/mold.scad>;
use <../guard-casting-mold-v1/mold.scad>;
FEATURE="assembly";
BX=84; BY=102; Z0=-33.5; Z1=43; CORE_DROP=1;
module box(a,b){translate(a)cube(b-a);}
// Local +Z points from reaction face toward bolt head. M6 nut slides in sideways;
// 4mm minimum roof above nut carries axial reaction, not printed threads.
module orient(p,axis){translate(p)if(axis=="x")rotate([0,90,0])children();else if(axis=="y")rotate([-90,0,0])children();else if(axis=="-y")rotate([90,0,0])children();else children();}
module jack_cut(L){
 translate([0,0,-.1])cylinder(d=6.6,h=L+.2,$fn=40);
 translate([0,0,L-10])cylinder(d=11.95,h=5.5,$fn=6);
 translate([-6,-20,L-10])cube([12,20,5.5]);
}
module washer_cut(){translate([0,0,-1.7])cylinder(d=12.5,h=1.8,$fn=48);}
module screw(L){color("#b4bac4")union(){translate([0,0,-1.6])cylinder(d=5.9,h=L+5.6,$fn=32);translate([0,0,L+4])cylinder(d=10,h=6,$fn=32);}}
module washer(){difference(){translate([0,0,-1.6])cylinder(d=12,h=1.6,$fn=40);translate([0,0,-2])cylinder(d=6.4,h=3,$fn=32);}}
module nut(L){difference(){translate([0,0,L-10])cylinder(d=11.55,h=5.2,$fn=6);cylinder(d=6,h=L+2,$fn=32);}}
module lid_sites(){for(x=[-34,34])translate([x,25,30.2])children();}
module end_sites(s){for(x=[-29,29])orient([x,s*51,-10],s>0?"y":"-y")children();}
module side_sites(){for(y=[-27,27])orient([0,y,-45],"x")children();}
module outer_add(s){
 // Two under-base jack shoes. Kept BELOW Z=-33.5 so Y cores can withdraw
 // freely; no crossbar is allowed in the front/back core extraction corridor.
 for(y=[-27,27]){
  if(s>0){box([32,y-8,-53],[54,y+8,-20]);box([0,y-8,-53],[54,y+8,-37]);}
  else{box([-54,y-8,-53],[-32,y+8,-20]);box([-54,y-8,-53],[0,y+8,-37]);}
 }
}
module shell_v3(s){difference(){union(){located_shell(s);outer_add(s);}
 if(s>0)side_sites()jack_cut(54);else side_sites()washer_cut();
 for(x=[-34,34])if(x*s>0)translate([x,25,30.2])washer_cut();
 for(q=[-1,1])for(x=[-29,29])if(x*s>0)orient([x,q*51,-10],q>0?"y":"-y")washer_cut();
}}
module lid_v3(){difference(){located_lid();lid_sites()jack_cut(12.8);}}
module end_v3(s){difference(){union(){
 if(s>0)located_lower();else located_back();
 // Thick external nut bosses, bonded to existing broad end shoulder.
 for(x=[-29,29])box([x-9,s>0?51:-69,-19],[x+9,s>0?69:-51,-1]);
 if(s<0)box([-37,-55.5,-19],[37,-51,0]);
 }end_sites(s)jack_cut(18);}}
module upper_v3(){union(){located_upper();
 // Same YZ envelope as insert: shells can slide past this long finger handle.
 difference(){box([51.5,-10.5,0],[92,10.5,23]);box([63,-10.6,5],[84,10.6,18]);}
}}
module hardware(which){
 if(which=="lid-hw")lid_sites(){screw(12.8);nut(12.8);washer();}
 if(which=="front-hw")end_sites(1){screw(18);nut(18);washer();}
 if(which=="back-hw")end_sites(-1){screw(18);nut(18);washer();}
 if(which=="side-hw")side_sites(){screw(54);nut(54);washer();}
}
if(FEATURE=="left")shell_v3(-1);
else if(FEATURE=="right")shell_v3(1);
else if(FEATURE=="lid")lid_v3();
else if(FEATURE=="lower")end_v3(1);
else if(FEATURE=="back")end_v3(-1);
else if(FEATURE=="upper")upper_v3();
else if(FEATURE=="pin")pull_pin();
else if(FEATURE=="product")product();
else if(FEATURE=="lid-hw"||FEATURE=="front-hw"||FEATURE=="back-hw"||FEATURE=="side-hw")hardware(FEATURE);
else{color("#48a8dd",.3)shell_v3(-1);color("#6383ed",.3)shell_v3(1);color("#a877df")lid_v3();color("#4dbda6")end_v3(1);color("#f08eae")end_v3(-1);color("#eeb750")upper_v3();color("#ec7956")product();}

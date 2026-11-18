// v2: six mold blocks with positive seating, integral anti-reversal guides,
// one separate pull pin and external elastic-band tracks. mm; X upper beam,
// Y foot, Z up. The v1.19 casting cavity is unchanged.
// Local 0.6mm elastic stripping at lower arm ends is still required.
use <../guard-casting-mold-v1/mold.scad>;
FEATURE="assembly";
BX=84; BY=102; Z0=-33.5; Z1=43; SPLIT_Z=30.2;
CORE_DROP=1;
GUIDE_D=5; GUIDE_DEPTH=5; RADIAL_CLEARANCE=0.2; HOLE_EXTRA_DEPTH=0.6;
SHOULDER_THICK=4.5; SHOULDER_HALF_X=37;
BAND_WIDTH=5; BAND_DEPTH=1; BAND_X=27; BAND_Z=26;
PULL_X=34; PULL_Y=0; PULL_TIP_Z=19; PULL_HEAD_D=6.8; PULL_HEAD_HEIGHT=3.5;
// A round guide + one laterally relieved socket per interface avoids excessive
// center-distance constraint. Offsets differ between ends and are asymmetric.
LID_GUIDES=[[-34,-40],[34,36]]; // [X,Y], downward male from lid
BACK_GUIDES=[[-29,8],[29,19]]; // [X,Z], +Y male from rear flange
FRONT_GUIDES=[[-29,-18],[29,18]]; // [X,Z], -Y male from front flange
module cube_between(a,b){translate(a)cube(b-a);}
module guide(axis=[0,0,1],d=GUIDE_D,h=GUIDE_DEPTH){
    // All coordinates below explicitly rotate the Z-axis cylinder.
    if(axis==[1,0,0])rotate([0,90,0])cylinder(d=d,h=h,$fn=32);
    else if(axis==[0,1,0])rotate([-90,0,0])cylinder(d=d,h=h,$fn=32);
    else if(axis==[0,-1,0])rotate([90,0,0])cylinder(d=d,h=h,$fn=32);
    else if(axis==[0,0,-1])rotate([180,0,0])cylinder(d=d,h=h,$fn=32);
    else cylinder(d=d,h=h,$fn=32);
}
module socket(axis,relief=[0,0,0]){hull(){
    translate(-relief/2)guide(axis,GUIDE_D+2*RADIAL_CLEARANCE,GUIDE_DEPTH+HOLE_EXTRA_DEPTH);
    translate(relief/2)guide(axis,GUIDE_D+2*RADIAL_CLEARANCE,GUIDE_DEPTH+HOLE_EXTRA_DEPTH);
}}
module lid_males(){for(p=LID_GUIDES)translate([p[0],p[1],SPLIT_Z+.2])guide([0,0,-1],h=GUIDE_DEPTH+.2);}
module lid_sockets(){for(i=[0:1])let(p=LID_GUIDES[i])
    translate([p[0],p[1],SPLIT_Z+.05])socket([0,0,-1],i==1?[.6,0,0]:[0,0,0]);}
module back_males(){for(p=BACK_GUIDES)translate([p[0],-BY/2-.2,p[1]])guide([0,1,0],h=GUIDE_DEPTH+.2);}
module back_sockets(){for(i=[0:1])let(p=BACK_GUIDES[i])
    translate([p[0],-BY/2-.05,p[1]])socket([0,1,0],i==1?[.6,0,0]:[0,0,0]);}
module front_males(){for(p=FRONT_GUIDES)translate([p[0],BY/2+.2,p[1]])guide([0,-1,0],h=GUIDE_DEPTH+.2);}
module front_sockets(){for(i=[0:1])let(p=FRONT_GUIDES[i])
    translate([p[0],BY/2+.05,p[1]])socket([0,-1,0],i==1?[.6,0,0]:[0,0,0]);}
module pull_bore(){translate([PULL_X,PULL_Y,PULL_TIP_Z-.6])
    cylinder(d=GUIDE_D+2*RADIAL_CLEARANCE,h=Z1-PULL_TIP_Z+2,$fn=32);}
module band_cuts(){
    for(s=[-1,1])let(x=s*BAND_X){
        // Two YZ-plane loops: lid, base and both end shoulders.
        cube_between([x-BAND_WIDTH/2,-70,Z1-BAND_DEPTH],[x+BAND_WIDTH/2,70,Z1+1]);
        cube_between([x-BAND_WIDTH/2,-70,Z0-1],[x+BAND_WIDTH/2,70,Z0+BAND_DEPTH]);
        cube_between([x-BAND_WIDTH/2,BY/2+SHOULDER_THICK-BAND_DEPTH,Z0-1],
                     [x+BAND_WIDTH/2,BY/2+SHOULDER_THICK+1,Z1+1]);
        cube_between([x-BAND_WIDTH/2,-BY/2-SHOULDER_THICK-1,Z0-1],
                     [x+BAND_WIDTH/2,-BY/2-SHOULDER_THICK+BAND_DEPTH,Z1+1]);
    }
    // XY-plane loop above the upper-core handle: holds the shell split shut.
    for(s=[-1,1]){
        if(s>0)cube_between([BX/2-BAND_DEPTH,-70,BAND_Z-BAND_WIDTH/2],[BX/2+1,70,BAND_Z+BAND_WIDTH/2]);
        else cube_between([-BX/2-1,-70,BAND_Z-BAND_WIDTH/2],[-BX/2+BAND_DEPTH,70,BAND_Z+BAND_WIDTH/2]);
        if(s>0)cube_between([-60,BY/2+SHOULDER_THICK-BAND_DEPTH,BAND_Z-BAND_WIDTH/2],[60,BY/2+SHOULDER_THICK+1,BAND_Z+BAND_WIDTH/2]);
        else cube_between([-60,-BY/2-SHOULDER_THICK-1,BAND_Z-BAND_WIDTH/2],[60,-BY/2-SHOULDER_THICK+BAND_DEPTH,BAND_Z+BAND_WIDTH/2]);
    }
}
module located_shell(s){difference(){
    shell(s);
    // Both shells register to the spanning lid and end shoulders. No floating
    // cross-pin is placed at X=0, where the casting/cores occupy the split.
    lid_sockets();front_sockets();back_sockets();pull_bore();band_cuts();
}}
module located_lid(){difference(){union(){lid();lid_males();}pull_bore();band_cuts();}}
module located_back(){difference(){union(){
    // Trim the old grip behind the new shoulder: broad flat print base.
    intersection(){back_core();cube_between([-60,-BY/2-SHOULDER_THICK,-60],[60,70,60]);}
    // Broad shoulder physically seats against the -Y shell end; cannot overinsert.
    cube_between([-SHOULDER_HALF_X,-BY/2-SHOULDER_THICK,-4],[SHOULDER_HALF_X,-BY/2,SPLIT_Z]);
    back_males();}band_cuts();}}
module located_lower(){difference(){union(){
    intersection(){lower_core();cube_between([-60,-70,-60],[60,BY/2+SHOULDER_THICK,60]);}
    cube_between([-SHOULDER_HALF_X,BY/2,Z0],[SHOULDER_HALF_X,BY/2+SHOULDER_THICK,SPLIT_Z]);
    front_males();}band_cuts();}}
module located_upper(){difference(){upper_core();pull_bore();}}
module pull_pin(){
    // Smooth removable pin: no screw thread is relied on for location.
    // Shaft 5mm, tip Z19, seated head lower face Z43.
    translate([PULL_X,PULL_Y,PULL_TIP_Z]){
        cylinder(d1=GUIDE_D-.8,d2=GUIDE_D,h=.8,$fn=32);
        translate([0,0,.8])cylinder(d=GUIDE_D,h=Z1-PULL_TIP_Z-.8+.1,$fn=32);
        translate([0,0,Z1-PULL_TIP_Z])hull(){
            translate([0,-6,0])cylinder(d=PULL_HEAD_D,h=PULL_HEAD_HEIGHT,$fn=40);
            translate([0,6,0])cylinder(d=PULL_HEAD_D,h=PULL_HEAD_HEIGHT,$fn=40);
        }
    }
}
if(FEATURE=="left")located_shell(-1);
else if(FEATURE=="right")located_shell(1);
else if(FEATURE=="lid")located_lid();
else if(FEATURE=="upper")located_upper();
else if(FEATURE=="lower")located_lower();
else if(FEATURE=="back")located_back();
else if(FEATURE=="pin")pull_pin();
else if(FEATURE=="product")product();
else if(FEATURE=="ports")intersection(){ports();stock();}
else {color("#48a8dd",.3)located_shell(-1);color("#6383ed",.3)located_shell(1);
    color("#a877df",.5)located_lid();color("#eeb750")located_upper();
    color("#4dbda6")located_lower();color("#f08eae")located_back();
    color("#c9e65b")pull_pin();color("#ec7956")product();}

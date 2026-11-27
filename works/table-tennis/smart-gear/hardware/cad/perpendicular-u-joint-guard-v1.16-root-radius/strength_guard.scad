// mm; X upper beam, Y lower foot, Z up. X1C PETG one-piece clip.
// Side thrust -> lower arm -> R4 root -> upper wall and tapered rib.
use <../perpendicular-u-joint-guard-v1.15-tapered-unified/tapered_guard.scad>;
use <../perpendicular-u-joint-guard-v1.13-edge-safe-label/edge_safe_guard.scad>;
FEATURE="all";
ROOT_R=4;
EXTEND_Y=5;
module root_radius(r=4){
    // R4 tangent to the existing 22.8/12 ramp and horizontal arm top.
    // The corner at Y=21.5 is already filled by the ramp: fillet its toe.
    k=22.8/12;
    a=atan(k);
    cy=33.5+r*tan(a/2);
    ty=cy-r*sin(a);
    tz=.2+r-r*cos(a);
    for(sx=[-1,1])for(sy=[-1,1])scale([sx,sy,1])
    difference(){
        translate([10.9,ty-.02,.18])cube([7,cy-ty+.04,tz-.18]);
        translate([10.8,cy,.2+r])rotate([0,90,0])cylinder(r=r,h=7.2,$fn=96);
    }
}
module extended_ends(d=5){
    // Copy the original last 5 mm including the hook cross-section.
    for(sy=[-1,1])scale([1,sy,1])translate([0,d,0])intersection(){
        guard_v1_15(feature="raw");
        translate([-18,33.5-d-.02,-23.5])cube([36,d+.02,23.7]);
    }
}
module extended_ribs(d=5){
    for(sx=[-1,1])for(sy=[-1,1])scale([sx,sy,1])
    polyhedron(points=[[14.9,10.5,23],[27.9,10.5,23],
        [27.9,21.5,23],[14.9,21.5,23],[17.9,10.5,-23.5],[17.9,33.5+d,-23.5]],
        faces=[[3,2,1,0],[1,4,0],[2,5,4,1],[4,5,3,0],[5,2,3]],convexity=8);
}
module strength_raw(){union(){guard_v1_15(feature="raw");root_radius(ROOT_R);extended_ends(EXTEND_Y);extended_ribs(EXTEND_Y);}}
module strength_body(){union(){convex_edge_bevel(.6)strength_raw();intersection(){strength_raw();bottom_protection();}}}
if(FEATURE=="raw")strength_raw();
else if(FEATURE=="body")strength_body();
else if(FEATURE=="label")guard_v1_15(feature="label");
else union(){strength_body();guard_v1_15(feature="label");}

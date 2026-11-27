// 乒乓球围挡止转卡 v1.17：针对实物与接触计算共同定位的卡臂上缘开裂。
// mm. X=上梁, Y=下脚, Z=向上；PETG/X1C，一体沿-Z扣入。
// 保留内腔、D16贯通孔、房檐、文字、底面及原1.5mm扣唇。
use <../perpendicular-u-joint-guard-v1.16-root-radius/strength_guard.scad>;
use <../perpendicular-u-joint-guard-v1.15-tapered-unified/tapered_guard.scad>;
use <../perpendicular-u-joint-guard-v1.13-edge-safe-label/edge_safe_guard.scad>;
FEATURE="all";
ARM_WALL=10; // 7 -> 10, outward only: X inner face remains +/-10.9.
TOE_RADIUS=8;
assert(ARM_WALL>=7 && ARM_WALL<=12);
assert(TOE_RADIUS>0 && TOE_RADIUS<=10);
module arm_backing(w=10){
    // Ease back into the unchanged lowest band: no new ground protrusion.
    for(sx=[-1,1])for(sy=[-1,1])scale([sx,sy,1])
    translate([0,38.5,0])rotate([90,0,0])linear_extrude(height=28)
        polygon([[10.9,-22],[17.9,-22],[10.9+w,-18],[10.9+w,.2],[10.9,.2]]);
}
function toe_profile(r=8,k=.68)=
    let(a=atan(k),cy=38.5,cz=.2+r,ty=cy-r*sin(a),tz=cz-r*cos(a))
    [for(p=concat([[21.3,.18],[cy,.18]],
        [for(i=[0:32])let(t=a*i/32)[cy-r*sin(t),cz-r*cos(t)]],
        [[21.3,tz+k*(ty-21.3)]])) [round(p[0]*1000)/1000,round(p[1]*1000)/1000]];
module smooth_arm_toe(w=10,r=8){
    // Tangent R8 YZ transition; all reinforcement remains outside the fit.
    for(sx=[-1,1])for(sy=[-1,1])scale([sx,sy,1])
    translate([10.9,0,0])rotate([90,0,90])linear_extrude(height=w)
        polygon(toe_profile(r));
}
module load_path_raw(){union(){strength_raw();arm_backing(ARM_WALL);smooth_arm_toe(ARM_WALL,TOE_RADIUS);}}
// Structural geometry remains native and parametric. Build.py applies the
// identical octahedral opening in Manifold3D because OpenSCAD's CGAL Minkowski
// crashes on this arc. Direct SCAD preview is BEFORE the edge finishing step.
if(FEATURE=="label")labeled_text_blank();
else if(FEATURE=="body")assert(false,"Use build.py for the fully beveled body STL");
else if(FEATURE=="raw")load_path_raw();
else union(){load_path_raw();labeled_text_blank();}

// v1.18: close the inner peel notch with a transverse toe bridge.
// mm; X upper beam, Y lower foot, Z up. Native parametric geometry.
// The bridge is ABOVE the foot (underside Z=0, aligned with the existing ramp), not inside its fit envelope.
// Roof/eaves/bore/label and the bottom 1.5 mm hook band remain unchanged.
use <../perpendicular-u-joint-guard-v1.17-load-path/load_path_guard.scad>;
use <../perpendicular-u-joint-guard-v1.13-edge-safe-label/edge_safe_guard.scad>;
FEATURE="all";
BRIDGE_EXTRA=3; // R8 profile lifted 3 mm; minimum nominal roof is 3.2 mm before edge bevel.
module transverse_toe_bridge(){
    // Reuse the exact R8 profile. The bridge ties both 10 mm arms together
    // across X and covers the full 10 mm arm width: no thin joining neck.
    base=toe_profile(8);
    profile=[for(i=[0:len(base)-1])
        [base[i][0],i<2?0:base[i][1]+BRIDGE_EXTRA]];
    for(sy=[-1,1])scale([1,sy,1])
    translate([-20.9,0,0])rotate([90,0,90])linear_extrude(height=41.8)
        polygon(profile);
}
module toe_bridge_raw(){union(){load_path_raw();transverse_toe_bridge();}}
if(FEATURE=="label")labeled_text_blank();
else if(FEATURE=="body")assert(false,"Use build.py for the edge-finished body STL");
else if(FEATURE=="raw")toe_bridge_raw();
else union(){toe_bridge_raw();labeled_text_blank();}

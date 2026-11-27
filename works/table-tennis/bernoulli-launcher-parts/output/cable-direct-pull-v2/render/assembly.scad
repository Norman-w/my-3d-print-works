// Actual CAD local complete feeder + v2 cable assembly. No whole-blower claim.
// Only rendering colors/visibility; assembly coordinates and geometry preserved.
include </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/cable-direct-pull-v2/candidate.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/cable-direct-pull-v2/housing-route/equal-length-route.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/launcher-final-assembly.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-trigger-system.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-output-interface.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-route-retention.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-housing-route.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/feeder-return-spring.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/outlet-retention.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/inlet-retention-final.scad>
view_u=0;
view_delta=0;
assert(view_u>=0&&view_u<=20);
assert(view_delta==0,"This static rendering uses nominal delta0 equal-length route");
module complete_local_assembly(u){
 t=u/20;
 color([.50,.64,.70,.38])la_fixed_printed();
 color([.20,.43,.54]){cdp_body();co_fixed_bridge();}
 color([.35,.60,.68,.35])cdp_cover();
 color([.92,.65,.22]){cdp_lever(u);co_frame(t);co_lug_cap(t);}
 color([.98,.76,.38,.65])cdp_terminal_cap(u);
 color([.45,.67,.74])ct_original_other_moving(t);
 color([.69,.71,.72]){
  ct_original_fixed_hardware();la_moving_hardware(t);
  cdp_fixed_hardware(view_delta);cdp_moving_hardware(u);co_hardware(t);
 }
 color([.30,.75,.47])rs_spring(t);
 color([.45,.75,.84,.24]){or_pipe();ir_hose_reference();}
 color([.14,.17,.20,.9])cv_housing(view_delta);
 color([.78,.80,.82]){
  cdp_cable(u,view_delta);
  difference(){cr_wire();cdp_cable(u,view_delta);co_wire(t);}
 }
 color([.18,.49,.60])crr_base();
 color([.40,.70,.77,.45])crr_cap();
 color([.27,.39,.47])crr_lower();
 color([.7,.72,.76])crr_hardware();
}
complete_local_assembly(view_u);

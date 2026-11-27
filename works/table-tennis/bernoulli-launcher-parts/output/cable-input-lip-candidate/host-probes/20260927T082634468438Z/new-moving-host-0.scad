include </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/cable-input-lip-candidate/candidate.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/launcher-final-assembly.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-trigger-system.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-output-interface.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-route-retention.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-housing-route.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/feeder-return-spring.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/outlet-retention.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/inlet-retention-final.scad>

module other_host(t){la_fixed_printed();ct_original_other_moving(t);co_frame(t);co_lug_cap(t);ct_original_fixed_hardware();la_moving_hardware(t);co_fixed_bridge();co_hardware(t);rs_spring(t,true);cr_housing();or_pipe();ir_hose_reference();crr_base();crr_cap();crr_lower();crr_hardware();}
module growth_bound(){cil_to_cad(){cil_box(-45,-37,49,71,-12,-8);cil_box(-42,-29,-34,-18,-12,-8);cil_box(-45,-20,49,55,-12,-4);cil_guide_solid();}}
intersection(){cil_moving(0);other_host(0/20);}

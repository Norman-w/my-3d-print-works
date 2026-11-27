include </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/parameters.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/launcher-final-assembly.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-trigger-input.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-trigger-system.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-output-interface.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-route-retention.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-housing-route.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/feeder-return-spring.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/inlet-retention-final.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/outlet-retention.scad>
module growth_bound(){ci_to_cad(){ci_box(-45,-37,49,71,-12,-8);ci_box(-42,-29,-34,-18,-12,-8);}}
module external_host(t){la_fixed_printed();ci_cover();co_fixed_bridge();ct_moving_printed(t);ct_original_fixed_hardware();la_moving_hardware(t);ci_hardware(20*t);co_hardware(t);rs_spring(t);or_pipe();ir_hose_reference();cr_housing();cr_wire();crr_all();}
intersection(){growth_bound();external_host(0);}

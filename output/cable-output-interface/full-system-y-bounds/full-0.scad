use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-trigger-system.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/launcher-final-assembly.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-trigger-input.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-output-interface.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-housing-route.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/feeder-return-spring.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/outlet-retention.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/inlet-retention-final.scad>
test_t=0;
union(){ct_fixed_printed();ct_moving_printed(test_t);ct_original_fixed_hardware();la_moving_hardware(test_t);ci_hardware(20*test_t);co_hardware(test_t);rs_spring(test_t);cr_housing();cr_wire();or_pipe();ir_hose_reference();ir_pad_reference();ir_pad_reference(true);}

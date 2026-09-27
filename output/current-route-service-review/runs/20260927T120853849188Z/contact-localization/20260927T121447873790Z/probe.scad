include </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/parameters.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/current-route-service-review/runs/20260927T120853849188Z/scene-obstacles.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-route-retention.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-output-interface.scad>
kind="cap-external";
if(kind=="cap-external")intersection(){crr_cap_sweep(50);union(){rs_current_rigid();rs_nominal_flexible();}}
else if(kind=="lower-external")intersection(){crr_lower_service_sweep();rs_current_rigid();}
else if(kind=="wrong-bridge-at-60")intersection(){crr_lower(60);co_fixed_bridge();}

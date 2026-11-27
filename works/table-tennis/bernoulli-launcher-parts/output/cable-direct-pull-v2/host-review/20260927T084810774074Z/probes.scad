include </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/cable-direct-pull-v2/candidate.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/cable-direct-pull-v2/housing-route/equal-length-route.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/launcher-final-assembly.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-trigger-system.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-trigger-input.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-output-interface.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-route-retention.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-housing-route.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/feeder-return-spring.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/outlet-retention.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/inlet-retention-final.scad>
u=0;delta=0;kind="moving-host";fault=false;
assert(u==0||u==10||u==20);
assert(delta==-2||delta==0||delta==2);
module known_host(t,guide=true){
 la_fixed_printed();ct_original_other_moving(t);co_frame(t);co_lug_cap(t);
 ct_original_fixed_hardware();la_moving_hardware(t);co_fixed_bridge();co_hardware(t);
 rs_spring(t,true);or_pipe();ir_hose_reference();
 if(guide){crr_base();crr_cap();crr_lower();crr_hardware();}
}
module body_growth(){difference(){cdp_body();ci_body();}}
module nonmount_input_metal(d){cdp_to_cad()cdp_local_fixed_hardware(d);}
module local_current_input(t,d){
 cdp_body();cdp_cover();cdp_moving(20*t);cdp_fixed_hardware(d);
}
// Clear route against actual host and input metal/printed geometry, with no
// own steel core. Full 1 mm clearance would intentionally enter the third
// guide's 6.2 mm bore; that guide is tested separately with nominal OD5.
if(kind=="moving-host")union(){
 intersection(){cdp_moving(u);union(){known_host(u/20);cv_housing(delta);if(fault)cdp_lever(u);}}
 intersection(){cdp_cable(u,delta);known_host(u/20);}
}
else if(kind=="body-growth-host")intersection(){body_growth();union(){known_host(u/20);cv_housing(delta);if(fault)body_growth();}}
else if(kind=="input-fixed-metal-host")intersection(){nonmount_input_metal(delta);known_host(u/20);}
else if(kind=="route-clearance-host")intersection(){cv_envelope(delta,1,true);union(){
 known_host(u/20,false);local_current_input(u/20,delta);
 if(fault)translate(cv_arc_point(1,.5,delta,cv_shift(delta)))sphere(d=12,$fn=24);
}}
else if(kind=="route-nominal-guide")intersection(){cv_housing(delta);union(){crr_base();crr_cap();crr_lower();crr_hardware();}}
else if(kind=="cover-added")difference(){cdp_cover();ci_cover();}
else if(kind=="cover-removed")difference(){ci_cover();cdp_cover();}
else assert(false,"Unknown host review kind");

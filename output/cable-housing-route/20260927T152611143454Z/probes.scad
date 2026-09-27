use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-trigger-system.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-housing-route.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/launcher-final-assembly.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-trigger-input.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-output-interface.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/feeder-return-spring.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/outlet-retention.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/inlet-retention-final.scad>
t=0;fault=false;nominal=false;
intersection(){
    // Full-length OD envelope excludes only the two intended mating ferrules
    // and the cable's own core. Both end ferrules remain in the 1 mm interior
    // clearance test. End seating/fit is NOT certified by this route test.
    if(nominal)cr_sweep(cr_points(),
        (cr_get(ci_spec(),"housing_od")+2*cr_sagitta())/pow(cos(180/24),2));
    else cr_clearance();
    union(){ct_fixed_printed();ct_moving_printed(t);ct_original_fixed_hardware();
      la_moving_hardware(t);or_pipe();ir_hose_reference();
      if(nominal)difference(){ci_fixed_hardware();ci_ferrule();}
      else ci_fixed_hardware();
      ci_moving_hardware(20*t);
      co_terminal_hardware(t);co_adjuster_hardware();
      if(!nominal)co_ferrule_reference();
      rs_spring(t,true);
      if(fault)translate(cr_points()[floor(len(cr_points())/2)])sphere(d=10,$fn=24);
    }
}

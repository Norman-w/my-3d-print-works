include </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/cable-input-lip-candidate/candidate.scad>
intersection(){union(){cil_lever(0);cil_to_cad()translate([0,60,2])sphere(d=5);}hull(){cil_terminal_cap(0);cil_to_cad()translate([0,0,20])cil_local_terminal_cap();}}

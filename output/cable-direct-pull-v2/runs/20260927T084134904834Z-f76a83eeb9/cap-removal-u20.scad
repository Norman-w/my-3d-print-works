include </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/cable-direct-pull-v2/candidate.scad>
intersection(){union(){cdp_body();cdp_lever(20);cdp_to_cad()translate(cdp_B(cdp_angle(20)))sphere(d=5);}cdp_to_cad()rotate([0,0,-cdp_angle(20)])cdp_local_terminal_cap(20);}

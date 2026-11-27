include </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/cable-direct-pull-v2/candidate.scad>
intersection(){union(){cdp_body();cdp_lever(0);cdp_fixed_hardware(0);}cdp_to_cad()for(i=[0,1])cdp_local_adjuster_tool(i,25);}

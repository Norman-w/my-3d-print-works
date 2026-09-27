include </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/cable-direct-pull-v2/candidate.scad>
intersection(){union(){difference(){cdp_body();cdp_to_cad()cdp_guide_solid();}cdp_cover();cdp_lever(0);cdp_terminal_cap(0);}cdp_cable(0,-2);}

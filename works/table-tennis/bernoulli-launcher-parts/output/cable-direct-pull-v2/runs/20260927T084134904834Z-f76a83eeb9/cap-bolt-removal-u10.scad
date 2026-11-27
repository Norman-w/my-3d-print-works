include </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/cable-direct-pull-v2/candidate.scad>
intersection(){union(){cdp_body();cdp_lever(10);cdp_terminal_cap(10);}cdp_to_cad()rotate([0,0,-cdp_angle(10)])for(p=cdp_cap_bolts){cdp_zcyl(p[0],p[1],-3.5,8+16,3);cdp_zcyl(p[0],p[1],4.5,3+16,5.5);}}
